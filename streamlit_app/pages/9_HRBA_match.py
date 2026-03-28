import json
import time
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_app.i18n import enable_serbian_locale
from config import Config
from database.db_manager import DatabaseManager
from document_processing.processors.hrba_matcher import HRBAMatcher as SpaCyHRBAMatcher
from template_matching.hrba_matcher import HRBAMatcherLLM
from streamlit_app.components.sidebar import render_page_disclaimer, render_sidebar
from streamlit_app.components.help_button import render_help_button

enable_serbian_locale(st)
st.set_page_config(page_title="HRBA uparivanje — SIPMT", page_icon="⚖️", layout="wide")
render_sidebar()

col1, col2 = st.columns([14, 4])
with col1:
    st.title("⚖️ HRBA — AAAQ Matcher")
with col2:
    render_help_button("⚖️ HRBA")

st.markdown(
    """
    Koristite HRBA uparivač za analizu teksta kroz AAAQ indikatore (Availability, Accessibility,
    Acceptability, Quality). Izaberite dokumente iz baze za grupnu analizu.
    """
)

db = DatabaseManager()

# Choose matcher
mode = st.radio("Matcher", ("spaCy (fast)", "Ollama LLM (JSON)"), index=0)
use_llm = mode.startswith("Ollama")

spaCy_matcher = SpaCyHRBAMatcher()
llm_matcher = HRBAMatcherLLM()

AAAQ_KEYS = ("availability", "accessibility", "acceptability", "quality")


def infer_top_hrba_match(item):
    if not isinstance(item, dict):
        return None, None

    if item.get("category") is not None or item.get("score") is not None:
        category = item.get("category")
        try:
            score = float(item.get("score")) if item.get("score") is not None else None
        except Exception:
            score = None
        return category, score

    best_key = None
    best_score = None
    for key in AAAQ_KEYS:
        value = item.get(key)
        try:
            numeric = float(value)
        except Exception:
            continue
        if best_score is None or numeric > best_score:
            best_key = key
            best_score = numeric
    return best_key, best_score


def normalize_analysis_rows(parsed):
    if not isinstance(parsed, list):
        return None

    rows = []
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue

        if any(key in item for key in AAAQ_KEYS):
            source_text = item.get("original_text") or item.get("text") or ""
            justification = item.get("justification")
            for key in AAAQ_KEYS:
                try:
                    score = float(item.get(key)) if item.get(key) is not None else None
                except Exception:
                    score = None
                rows.append({
                    "Segment": f"Seg {index + 1}",
                    "Category": key,
                    "Score": score,
                    "Text": source_text,
                    "Justification": justification,
                })
        else:
            rows.append({
                "Segment": f"Seg {index + 1}",
                "Category": item.get("category"),
                "Score": item.get("score"),
                "Text": item.get("text") or item.get("original_text"),
                "Justification": item.get("justification"),
            })

    if not rows:
        return None

    frame = pd.DataFrame(rows)
    preferred = [column for column in ("Segment", "Category", "Score", "Text", "Justification") if column in frame.columns]
    return frame[preferred]


def clean_preview_text(value, limit=240):
    if not value:
        return ""
    text = " ".join(str(value).replace("\n", " ").replace("\r", " ").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def build_sparkline(values):
    ticks = "▁▂▃▄▅▆▇█"
    cleaned = []
    for value in values:
        try:
            cleaned.append(float(value))
        except Exception:
            continue
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        cleaned = cleaned * 2
    low = min(cleaned)
    high = max(cleaned)
    if high <= low:
        return ticks[3] * min(len(cleaned), 12)
    spark = []
    for value in cleaned[-12:]:
        idx = int(round(((value - low) / (high - low)) * (len(ticks) - 1)))
        idx = max(0, min(len(ticks) - 1, idx))
        spark.append(ticks[idx])
    return "".join(spark)


def extract_aaaq_scores(item):
    if not isinstance(item, dict):
        return {}
    scores = {}
    for key in AAAQ_KEYS:
        try:
            value = item.get(key)
            if value is not None:
                scores[key] = float(value)
        except Exception:
            continue
    return scores


def build_hrba_executive_summary(parsed, seg_meta=None):
    if not isinstance(parsed, list):
        return ""

    scored_items = []
    justification_count = 0
    top_category_counts = {key: 0 for key in AAAQ_KEYS}

    for item in parsed:
        if not isinstance(item, dict):
            continue
        scores = extract_aaaq_scores(item)
        if scores:
            scored_items.append(scores)
        if item.get("justification"):
            justification_count += 1
        category, _score = infer_top_hrba_match(item)
        if category in top_category_counts:
            top_category_counts[category] += 1

    if not scored_items:
        return ""

    avg_scores = {
        key: sum(scores.get(key, 0.0) for scores in scored_items) / len(scored_items)
        for key in AAAQ_KEYS
    }
    lead_category = max(avg_scores, key=avg_scores.get)
    lead_score = avg_scores[lead_category]
    avg_confidence = sum(max(scores.values()) for scores in scored_items) / len(scored_items)
    total_segments = len(seg_meta or []) or len(scored_items)
    completed_segments = (
        sum(1 for meta in (seg_meta or []) if (meta.get("status") or "") == "done")
        if seg_meta else len(scored_items)
    )
    represented = [key.capitalize() for key, count in top_category_counts.items() if count > 0]

    lines = [
        f"Overall AAAQ signal: **{lead_category.capitalize()}** leads with average score **{lead_score:.0%}**.",
        f"Coverage snapshot: **{completed_segments}/{total_segments}** segments completed, **{len(scored_items)}** structured Ollama outputs, average top-signal confidence **{avg_confidence:.0%}**.",
    ]
    if represented:
        lines.append("Detected categories across the document: " + ", ".join(represented) + ".")
    if justification_count:
        lines.append(f"Generated justifications for **{justification_count}** segment(s), providing an explainable trace for the strongest detected signals.")
    return "\n\n".join(lines)


def compute_hrba_xai_metrics(parsed, seg_meta=None):
    if not isinstance(parsed, list):
        return None

    scored_items = []
    justification_count = 0
    top_category_counts = {key: 0 for key in AAAQ_KEYS}

    for item in parsed:
        if not isinstance(item, dict):
            continue
        scores = extract_aaaq_scores(item)
        if scores:
            scored_items.append(scores)
        if item.get("justification"):
            justification_count += 1
        category, _score = infer_top_hrba_match(item)
        if category in top_category_counts:
            top_category_counts[category] += 1

    if not scored_items:
        return None

    total_items = len(scored_items)
    avg_scores = {
        key: sum(scores.get(key, 0.0) for scores in scored_items) / total_items
        for key in AAAQ_KEYS
    }
    avg_top_confidence = sum(max(scores.values()) for scores in scored_items) / total_items
    total_segments = len(seg_meta or []) or total_items
    completed_segments = (
        sum(1 for meta in (seg_meta or []) if (meta.get("status") or "") == "done")
        if seg_meta else total_items
    )

    return {
        "segments_completed": completed_segments,
        "segment_completion": completed_segments / max(total_segments, 1),
        "structured_outputs": total_items,
        "justification_coverage": justification_count / max(total_items, 1),
        "avg_top_confidence": avg_top_confidence,
        "avg_scores": avg_scores,
        "top_category_counts": top_category_counts,
    }


def compute_hrba_shap_proxy(xai_metrics):
    if not xai_metrics:
        return {}

    avg_scores = xai_metrics.get("avg_scores") or {}
    proxy = {
        "Availability": (avg_scores.get("availability", 0.0) - 0.5) * 2,
        "Accessibility": (avg_scores.get("accessibility", 0.0) - 0.5) * 2,
        "Acceptability": (avg_scores.get("acceptability", 0.0) - 0.5) * 2,
        "Quality": (avg_scores.get("quality", 0.0) - 0.5) * 2,
        "Segment completion": (float(xai_metrics.get("segment_completion", 0.0)) - 0.5) * 1.6,
        "Justification coverage": (float(xai_metrics.get("justification_coverage", 0.0)) - 0.5) * 1.6,
        "Average confidence": (float(xai_metrics.get("avg_top_confidence", 0.0)) - 0.5) * 1.8,
    }
    return {label: max(-1.0, min(1.0, float(value))) for label, value in proxy.items()}


def render_hrba_shap_heatmap(shap_proxy, chart_key):
    if not shap_proxy:
        st.info("No SHAP proxy data available.")
        return

    labels = list(shap_proxy.keys())
    values = [float(shap_proxy[label]) for label in labels]
    figure = go.Figure(
        data=go.Heatmap(
            z=[values],
            x=labels,
            y=["Contribution"],
            zmin=-1,
            zmax=1,
            zmid=0,
            colorscale=[
                [0.0, "#b30000"],
                [0.25, "#f46d43"],
                [0.5, "#fff7bc"],
                [0.75, "#78c679"],
                [1.0, "#238443"],
            ],
            text=[[f"{value:+.2f}" for value in values]],
            texttemplate="%{text}",
            hovertemplate="%{x}<br>Contribution=%{z:.2f}<extra></extra>",
        )
    )
    figure.update_layout(height=260, margin=dict(l=10, r=10, t=35, b=10), title="SHAP-style contribution proxy")
    st.plotly_chart(figure, use_container_width=True, key=chart_key)
    st.caption("Positive values reinforce the document's AAAQ signal. This is a transparent proxy derived from structured scores, completion, and justification coverage.")


def render_hrba_ollama_summary(doc_id, parsed, seg_meta, key_prefix):
    xai_metrics = compute_hrba_xai_metrics(parsed, seg_meta)
    if not xai_metrics:
        return

    executive_summary = build_hrba_executive_summary(parsed, seg_meta)
    shap_proxy = compute_hrba_shap_proxy(xai_metrics)
    avg_scores = xai_metrics.get("avg_scores") or {}
    top_counts = xai_metrics.get("top_category_counts") or {}

    st.markdown("**Ollama izvršni sažetak**")
    if executive_summary:
        st.info(executive_summary)

    xai_col, shap_col = st.columns([1, 1])
    with xai_col:
        xai_rows = [
            {"Metric": "Segments completed", "Value": str(xai_metrics["segments_completed"])} ,
            {"Metric": "Segment completion", "Value": f"{xai_metrics['segment_completion']:.0%}"},
            {"Metric": "Structured outputs", "Value": str(xai_metrics["structured_outputs"])} ,
            {"Metric": "Justification coverage", "Value": f"{xai_metrics['justification_coverage']:.0%}"},
            {"Metric": "Average confidence", "Value": f"{xai_metrics['avg_top_confidence']:.0%}"},
            {"Metric": "Availability avg", "Value": f"{avg_scores.get('availability', 0.0):.0%}"},
            {"Metric": "Accessibility avg", "Value": f"{avg_scores.get('accessibility', 0.0):.0%}"},
            {"Metric": "Acceptability avg", "Value": f"{avg_scores.get('acceptability', 0.0):.0%}"},
            {"Metric": "Quality avg", "Value": f"{avg_scores.get('quality', 0.0):.0%}"},
        ]
        for category in AAAQ_KEYS:
            xai_rows.append({
                "Metric": f"Top category hits - {category.capitalize()}",
                "Value": str(int(top_counts.get(category, 0))),
            })
        st.dataframe(pd.DataFrame(xai_rows), use_container_width=True, hide_index=True)

    with shap_col:
        render_hrba_shap_heatmap(shap_proxy, chart_key=f"{key_prefix}_hrba_shap_{doc_id}")


def render_live_process_chart(seg_meta, radar_container, rate_container, timeline_container, active_idx=None):
    active_scores = {}
    if active_idx is not None and 0 <= active_idx < len(seg_meta):
        active_scores = seg_meta[active_idx].get("aaaq_scores") or {}

    radar_values = [active_scores.get(key, 0.0) for key in AAAQ_KEYS]
    radar_theta = [key.capitalize() for key in AAAQ_KEYS]
    radar_theta.append(radar_theta[0])
    radar_values.append(radar_values[0])

    radar_figure = go.Figure()
    radar_figure.add_trace(
        go.Scatterpolar(
            r=radar_values,
            theta=radar_theta,
            fill="toself",
            line=dict(color="#F8931F", width=3),
            fillcolor="rgba(248,147,31,0.35)",
            name="AAAQ signal",
        )
    )
    radar_figure.update_layout(
        title="Live AAAQ Signal",
        height=320,
        margin=dict(l=20, r=20, t=50, b=20),
        polar=dict(
            radialaxis=dict(range=[0, 1], tickvals=[0.25, 0.5, 0.75, 1.0], gridcolor="rgba(85,87,89,0.15)"),
            angularaxis=dict(gridcolor="rgba(85,87,89,0.08)"),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=False,
    )
    radar_container.plotly_chart(radar_figure, use_container_width=True)

    rate_events = []
    if active_idx is not None and 0 <= active_idx < len(seg_meta):
        rate_events = seg_meta[active_idx].get("chunk_history") or []

    if rate_events:
        rate_df = pd.DataFrame(rate_events)
        rate_figure = px.line(
            rate_df,
            x="elapsed",
            y="chunk_rate",
            markers=True,
            title="Live Chunk Rate",
        )
        rate_figure.update_traces(line=dict(color="#F8931F", width=3), marker=dict(size=7, color="#555759"))
        rate_figure.update_layout(height=220, margin=dict(l=20, r=20, t=50, b=20), xaxis_title="Elapsed (s)", yaxis_title="Chars/s")
        rate_container.plotly_chart(rate_figure, use_container_width=True)
    else:
        rate_container.info("Chunk-rate chart will appear after Ollama starts streaming tokens for the active segment.")

    now = time.time()
    timeline_rows = []
    for meta in seg_meta:
        start = meta.get("start")
        end = meta.get("end")
        status = meta.get("status") or "pending"
        if start is None:
            start = now
        if end is None:
            end = now if status == "generating" else start + (meta.get("duration") or 0.05)
        timeline_rows.append(
            {
                "Segment": f"Seg {meta['segment'] + 1}",
                "start": pd.to_datetime(start, unit="s"),
                "end": pd.to_datetime(end, unit="s"),
                "status": status,
            }
        )

    timeline_df = pd.DataFrame(timeline_rows)
    timeline_figure = px.timeline(
        timeline_df,
        x_start="start",
        x_end="end",
        y="Segment",
        color="status",
        color_discrete_map={"pending": "#D9D9D9", "generating": "#F8931F", "done": "#555759"},
        title="Per-Segment Throughput Timeline",
    )
    timeline_figure.update_yaxes(autorange="reversed")
    timeline_figure.update_layout(height=280, margin=dict(l=20, r=20, t=50, b=20), showlegend=False)
    timeline_container.plotly_chart(timeline_figure, use_container_width=True)


def plot_seg_meta_timeline(seg_meta, container, focus_idx=None):
    try:
        rows = []
        for m in seg_meta:
            start = m.get("start")
            end = m.get("end")
            if start is None or end is None:
                # if missing, create a tiny placeholder span so the segment appears
                if start is None and end is None:
                    now = time.time()
                    start = now
                    end = now + (m.get("duration") or 0.1)
                elif start is None:
                    start = end - (m.get("duration") or 0.1)
                elif end is None:
                    end = start + (m.get("duration") or 0.1)
            rows.append({
                "Segment": f"Seg {m['segment']+1}",
                "start": pd.to_datetime(start, unit="s"),
                "end": pd.to_datetime(end, unit="s"),
                "status": m.get("status") or "pending",
            })
        if not rows:
            container.info("Timeline will appear here as segments complete.")
            return
        tdf = pd.DataFrame(rows)
        fig = px.timeline(tdf, x_start="start", x_end="end", y="Segment", color="status")
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), height=420)
        if focus_idx is not None and 0 <= focus_idx < len(rows):
            r = rows[focus_idx]
            start = r["start"]
            end = r["end"]
            delta = (end - start) / 6 if end > start else pd.Timedelta(seconds=1)
            fig.update_layout(xaxis_range=[(start - delta), (end + delta)])
        container.plotly_chart(fig, use_container_width=True)
    except Exception:
        try:
            container.info("Unable to render timeline.")
        except Exception:
            pass

def render_seg_meta_panel(doc_id, seg_meta, key_prefix):
    if not seg_meta:
        return

    def safe_round(value, digits=3):
        try:
            if value is None or value == "":
                return None
            return round(float(value), digits)
        except Exception:
            return None

    seg_rows = []
    for m in seg_meta:
        seg_rows.append({
            "Segment": f"Seg {m['segment']+1}",
            "Status": m.get("status"),
            "Category": m.get("category"),
            "Confidence": safe_round(m.get("confidence"), 3),
            "Duration(s)": safe_round(m.get("duration"), 2),
            "Preview": (m.get("preview") or "")[:200],
        })

    analysis_container = st.container()
    with analysis_container:
        st.markdown("**Analysis**")
        st.markdown("**Generation timeline (segments)**")

        seg_options = [row["Segment"] for row in seg_rows]
        chosen = st.selectbox("Jump to segment", options=["—"] + seg_options, key=f"{key_prefix}_jump_{doc_id}")
        focus_idx = None
        if chosen and chosen != "—":
            try:
                focus_idx = seg_options.index(chosen)
            except Exception:
                focus_idx = None

        plot_seg_meta_timeline(seg_meta, st, focus_idx=focus_idx)

        st.markdown("**Document — Segments**")
        st.dataframe(pd.DataFrame(seg_rows), use_container_width=True)

def build_static_seg_meta(texts):
    seg_meta = []
    now = time.time()
    for index, text in enumerate(texts):
        seg_meta.append({
            "segment": index,
            "start": now + (index * 0.1),
            "end": now + (index * 0.1) + 0.05,
            "duration": 0.05,
            "status": "done",
            "preview": (text or "")[:800],
            "category": None,
            "confidence": None,
            "confidence_history": [],
            "dimension_histories": {key: [] for key in AAAQ_KEYS},
            "chunk_history": [],
            "chunks_processed": 0,
            "tokens_processed": 0,
        })
    return seg_meta

def run_llm_summary_with_progress(doc_id, texts):
    """Run LLM matcher across a list of text segments with live progress updates.

    Returns the final list of analysis dicts for the document.
    """
    progress_panel = st.container()
    with progress_panel:
        st.subheader(f"Document {doc_id}")
        progress_bar = st.progress(0)
        status = st.empty()
        preview_block = st.container(border=True)
        with preview_block:
            st.markdown("**Live generation monitor**")
            st.caption("Structured live diagnostics for Ollama streaming: progress, confidence evolution, throughput, and active-segment state.")
            preview_kpis = st.empty()
            preview_left, preview_right = st.columns([1, 1])
            preview_table = preview_left.empty()
            preview_radar = preview_right.empty()
            preview_rate = preview_right.empty()
            preview_timeline = preview_right.empty()
            preview_detail = preview_right.empty()

    stream_texts = {i: "" for i in range(len(texts))}

    seg_meta = [{
        "segment": i,
        "start": None,
        "end": None,
        "duration": None,
        "status": "pending",
        "preview": "",
        "confidence_history": [],
        "dimension_histories": {key: [] for key in AAAQ_KEYS},
        "chunk_history": [],
        "last_chunk_elapsed": None,
        "chunks_processed": 0,
        "tokens_processed": 0,
    } for i in range(len(texts))]

    kpi_state = {
        "chunks": 0,
        "tokens": 0,
        "done": 0,
        "active_rate": 0.0,
        "avg_active_rate": 0.0,
    }

    def render_live_preview(active_idx=None):
        total_chunks = sum(int(meta.get("chunks_processed") or 0) for meta in seg_meta)
        total_tokens = sum(int(meta.get("tokens_processed") or 0) for meta in seg_meta)
        total_done = sum(1 for meta in seg_meta if (meta.get("status") or "pending") == "done")
        active_rate = 0.0
        if active_idx is not None and 0 <= active_idx < len(seg_meta):
            active_history = seg_meta[active_idx].get("chunk_history") or []
            if active_history:
                try:
                    active_rate = float(active_history[-1].get("chunk_rate") or 0.0)
                except Exception:
                    active_rate = 0.0

        active_segment_rates = []
        for meta in seg_meta:
            if (meta.get("status") or "pending") != "generating":
                continue
            history = meta.get("chunk_history") or []
            if not history:
                continue
            try:
                active_segment_rates.append(float(history[-1].get("chunk_rate") or 0.0))
            except Exception:
                continue
        avg_active_rate = (sum(active_segment_rates) / len(active_segment_rates)) if active_segment_rates else 0.0

        delta_chunks = total_chunks - int(kpi_state.get("chunks") or 0)
        delta_tokens = total_tokens - int(kpi_state.get("tokens") or 0)
        delta_done = total_done - int(kpi_state.get("done") or 0)
        delta_active_rate = active_rate - float(kpi_state.get("active_rate") or 0.0)
        delta_avg_active_rate = avg_active_rate - float(kpi_state.get("avg_active_rate") or 0.0)

        with preview_kpis.container():
            kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
            kpi_col1.metric("Chunks processed", total_chunks, delta=f"{delta_chunks:+d}", delta_color="normal")
            kpi_col2.metric("Approx. tokens", total_tokens, delta=f"{delta_tokens:+d}", delta_color="normal")
            kpi_col3.metric("Segments done", f"{total_done}/{len(seg_meta)}", delta=f"{delta_done:+d}", delta_color="normal")
            kpi_col4.metric("Active chunk rate", f"{active_rate:.1f} chars/s", delta=f"{delta_active_rate:+.1f} chars/s", delta_color="normal")
            kpi_col5.metric("Avg active rate", f"{avg_active_rate:.1f} chars/s", delta=f"{delta_avg_active_rate:+.1f} chars/s", delta_color="normal")

        kpi_state["chunks"] = total_chunks
        kpi_state["tokens"] = total_tokens
        kpi_state["done"] = total_done
        kpi_state["active_rate"] = active_rate
        kpi_state["avg_active_rate"] = avg_active_rate

        rows = []
        for meta in seg_meta:
            dimension_histories = meta.get("dimension_histories") or {}
            rows.append({
                "Segment": f"Seg {meta['segment'] + 1}",
                "Status": meta.get("status") or "pending",
                "Leading category": meta.get("category"),
                "Confidence": round(float(meta.get("confidence")), 3) if meta.get("confidence") is not None else None,
                "Avail.": build_sparkline(dimension_histories.get("availability") or []),
                "Access.": build_sparkline(dimension_histories.get("accessibility") or []),
                "Accept.": build_sparkline(dimension_histories.get("acceptability") or []),
                "Quality": build_sparkline(dimension_histories.get("quality") or []),
                "Summary": clean_preview_text(meta.get("justification") or meta.get("preview"), 120),
            })
        if rows:
            preview_height = max(360, min(900, 52 * (len(rows) + 2)))
            preview_table.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=preview_height)

        render_live_process_chart(seg_meta, preview_radar, preview_rate, preview_timeline, active_idx=active_idx)

        if active_idx is None or not (0 <= active_idx < len(seg_meta)):
            preview_detail.info("Model progress will appear here while Ollama analyzes each segment.")
            return

        meta = seg_meta[active_idx]
        source_excerpt = clean_preview_text(texts[active_idx], 300)
        justification = clean_preview_text(meta.get("justification"), 280)
        draft_message = justification or (
            "Generating structured AAAQ scores and justification. Raw token output is hidden; final structured results will appear below."
            if meta.get("status") == "generating"
            else "Awaiting model output for this segment."
        )
        category = meta.get("category") or "pending"
        confidence = meta.get("confidence")
        confidence_text = f"{float(confidence):.3f}" if confidence is not None else "-"
        preview_detail.markdown(
            "\n".join([
                "**Active segment**",
                f"Segment: Seg {active_idx + 1}",
                f"Status: {meta.get('status') or 'pending'}",
                f"Leading category: {category}",
                f"Confidence: {confidence_text}",
                f"Source excerpt: {source_excerpt or '-'}",
                f"Summary: {draft_message}",
            ])
        )

    def on_progress(seg_idx, seg_total, part, obj, elapsed, done):
        try:
            now = time.time()
            if part:
                if seg_meta[seg_idx]["start"] is None:
                    seg_meta[seg_idx]["start"] = now
                seg_meta[seg_idx]["status"] = "generating"
                stream_texts[seg_idx] += part
                seg_meta[seg_idx]["preview"] = stream_texts[seg_idx]
                if isinstance(obj, dict):
                    category, score = infer_top_hrba_match(obj)
                    if category:
                        seg_meta[seg_idx]["category"] = category
                    if score is not None:
                        seg_meta[seg_idx]["confidence"] = score
                        seg_meta[seg_idx].setdefault("confidence_history", []).append(score)
                    scores = extract_aaaq_scores(obj)
                    if scores:
                        seg_meta[seg_idx]["aaaq_scores"] = scores
                        max_score = max(scores.values()) if scores else None
                        if max_score is not None:
                            seg_meta[seg_idx].setdefault("confidence_history", []).append(max_score)
                chunk_size = len(part)
                if elapsed and chunk_size:
                    last_elapsed = seg_meta[seg_idx].get("last_chunk_elapsed")
                    delta_elapsed = float(elapsed) - float(last_elapsed) if last_elapsed is not None else float(elapsed)
                    delta_elapsed = max(delta_elapsed, 0.001)
                    seg_meta[seg_idx].setdefault("chunk_history", []).append({
                        "elapsed": round(float(elapsed), 3),
                        "chunk_rate": round(chunk_size / delta_elapsed, 3),
                        "chunk_size": chunk_size,
                    })
                    seg_meta[seg_idx]["last_chunk_elapsed"] = float(elapsed)
                    seg_meta[seg_idx]["chunks_processed"] = int(seg_meta[seg_idx].get("chunks_processed") or 0) + 1
                    seg_meta[seg_idx]["tokens_processed"] = int(seg_meta[seg_idx].get("tokens_processed") or 0) + max(1, len(part.split()))
                if isinstance(obj, dict) and obj.get("justification"):
                    seg_meta[seg_idx]["justification"] = obj.get("justification")
                if isinstance(obj, dict):
                    for key, value in extract_aaaq_scores(obj).items():
                        seg_meta[seg_idx].setdefault("dimension_histories", {}).setdefault(key, []).append(value)
                render_live_preview(seg_idx)

            if done:
                if seg_meta[seg_idx]["start"] is None:
                    seg_meta[seg_idx]["start"] = now - (elapsed or 0)
                seg_meta[seg_idx]["end"] = now
                seg_meta[seg_idx]["duration"] = elapsed or (seg_meta[seg_idx]["end"] - seg_meta[seg_idx]["start"]) if seg_meta[seg_idx]["start"] else None
                seg_meta[seg_idx]["status"] = "done"
                seg_meta[seg_idx]["preview"] = stream_texts[seg_idx]
                if isinstance(obj, dict):
                    category, score = infer_top_hrba_match(obj)
                    if category:
                        seg_meta[seg_idx]["category"] = category
                    if score is not None:
                        seg_meta[seg_idx]["confidence"] = score
                        seg_meta[seg_idx].setdefault("confidence_history", []).append(score)
                    scores = extract_aaaq_scores(obj)
                    if scores:
                        seg_meta[seg_idx]["aaaq_scores"] = scores
                        max_score = max(scores.values()) if scores else None
                        if max_score is not None:
                            seg_meta[seg_idx].setdefault("confidence_history", []).append(max_score)
                        for key, value in scores.items():
                            seg_meta[seg_idx].setdefault("dimension_histories", {}).setdefault(key, []).append(value)
                    if obj.get("justification"):
                        seg_meta[seg_idx]["justification"] = obj.get("justification")
                pct = int(((seg_idx + 1) / max(1, seg_total)) * 100)
                progress_bar.progress(pct)
                status.info(f"Segment {seg_idx+1}/{seg_total} done — {int(elapsed or seg_meta[seg_idx]['duration'] or 0)}s")
                render_live_preview(seg_idx)
        except Exception:
            pass

    render_live_preview()
    final = llm_matcher.get_hrba_summary(texts, on_progress=on_progress)

    return {"final": final, "seg_meta": seg_meta}

org_id = st.session_state.get("org_id") if "org_id" in st.session_state else db.get_or_create_organisation("Default Organisation")
docs = db.fetchall(
    "SELECT id, title, created_at FROM documents WHERE organisation_id = ? AND status = 'active' ORDER BY created_at DESC",
    (org_id,),
)
doc_options = [f"{d['id']}: {d['title']}" for d in docs]
selected = st.multiselect("Izaberite dokumente za analizu", options=doc_options, default=[])

col1, col2 = st.columns(2)
analyze_selected_clicked = False
analyze_all_clicked = False
with col1:
    analyze_selected_clicked = st.button("Analiziraj izabrane")
    if analyze_selected_clicked and not selected:
        st.warning("Izaberite jedan ili više dokumenata za analizu.")

with col2:
    analyze_all_clicked = st.button("Analiziraj sve dokumente")
    if analyze_all_clicked and not docs:
        st.info("No documents available for this organisation.")

live_monitor_area = st.container()

if analyze_selected_clicked and selected:
    results = {}
    for sel in selected:
        doc_id = int(sel.split(":", 1)[0])
        pages = db.fetchall("SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number", (doc_id,))
        texts = [p.get("content") or "" for p in pages]
        with live_monitor_area:
            with st.spinner(f"Analyzing document {doc_id}..."):
                if use_llm:
                    ret = run_llm_summary_with_progress(doc_id, texts)
                    if isinstance(ret, dict) and "final" in ret:
                        final = ret["final"]
                        for a in final:
                            if isinstance(a, dict) and a.get("elapsed_seconds") and a["elapsed_seconds"] > 300:
                                st.warning("LLM generation exceeded 300s for one or more segments — results may be partial.")
                        analysis = ret
                    else:
                        analysis = ret
                else:
                    analysis = []
                    for t in texts:
                        insights = spaCy_matcher.extract_hrba_insights(t)
                        analysis.extend([{"category": i["category"], "score": i["score"], "text": i["text"]} for i in insights])
                    analysis = {"final": analysis, "seg_meta": build_static_seg_meta(texts)}
        results[doc_id] = analysis

    st.session_state['hrba_last_results'] = results
    st.success("Analiza je završena — rezultati su dostupni ispod.")

if analyze_all_clicked and docs:
    aggregate = {}
    for d in docs:
        doc_id = d["id"] if isinstance(d, (list, tuple)) else d["id"]
        pages = db.fetchall("SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number", (doc_id,))
        texts = [p.get("content") or "" for p in pages]
        with live_monitor_area:
            with st.spinner(f"Analyzing document {doc_id}..."):
                if use_llm:
                    ret = run_llm_summary_with_progress(doc_id, texts)
                    aggregate[doc_id] = ret
                else:
                    analysis = []
                    for t in texts:
                        insights = spaCy_matcher.extract_hrba_insights(t)
                        analysis.extend([{"category": i["category"], "score": i["score"], "text": i["text"]} for i in insights])
                    aggregate[doc_id] = {"final": analysis, "seg_meta": build_static_seg_meta(texts)}

    st.write("Grupna analiza je završena")
    for doc_id, analysis in aggregate.items():
        st.markdown(f"**Document {doc_id}**")
        parsed = analysis
        seg_meta = None
        if isinstance(analysis, dict) and "seg_meta" in analysis:
            seg_meta = analysis.get("seg_meta")
            if seg_meta:
                render_seg_meta_panel(doc_id, seg_meta, "agg")
            parsed = analysis.get("final")

        render_hrba_ollama_summary(doc_id, parsed, seg_meta, "agg")

        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except Exception:
                pass

        detail_df = normalize_analysis_rows(parsed)
        if detail_df is not None:
            st.dataframe(detail_df, use_container_width=True)
        else:
            st.write(parsed)

# Full-width rendering of last 'Analyze selected' results stored in session state
if st.session_state.get('hrba_last_results'):
    results = st.session_state.get('hrba_last_results')
    st.markdown("---")
    st.header("Rezultati analize")
    for doc_id, analysis in results.items():
        st.subheader(f"Document {doc_id} — {len(analysis['final']) if isinstance(analysis, dict) and 'final' in analysis else (len(analysis) if isinstance(analysis, (list, dict)) else 0)} matches")
        parsed = analysis
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except Exception:
                pass

        seg_meta = None
        if isinstance(analysis, dict) and 'seg_meta' in analysis:
            seg_meta = analysis.get('seg_meta')
        if seg_meta:
            render_seg_meta_panel(doc_id, seg_meta, "final")

        # If analysis was returned as a dict, extract the final payload for normal rendering
        if isinstance(analysis, dict) and 'final' in analysis:
            parsed = analysis['final']

        render_hrba_ollama_summary(doc_id, parsed, seg_meta, "final")

        detail_df = normalize_analysis_rows(parsed)
        if detail_df is not None:
            st.dataframe(detail_df, use_container_width=True)
        else:
            st.write(parsed)

# Option to save results to DB
st.markdown("---")
if st.button("Sačuvaj poslednju analizu u bazu"):
    try:
        # Attempt to find last results in page state by checking `results` or `aggregate` variables
        to_save = locals().get("results") or locals().get("aggregate")
        if not to_save:
            st.warning("Nema rezultata analize za čuvanje. Najpre pokrenite analizu.")
        else:
            saved_count = 0
            for doc_id, analysis in to_save.items():
                payload = {
                    "document_id": int(doc_id),
                    "model_used": llm_matcher.model if use_llm else Config.SPACY_MODEL,
                    "summary": json.dumps(analysis, ensure_ascii=False),
                    "full_response_json": json.dumps(analysis, ensure_ascii=False),
                }
                db.insert("semantic_analyses", payload)
                saved_count += 1
            st.success(f"Sačuvane su HRBA analize za {saved_count} dokumenata u tabelu semantic_analyses.")
    except Exception as e:
        st.error(f"Čuvanje u bazu nije uspelo: {e}")

st.markdown("---")
st.caption(f"spaCy model: {Config.SPACY_MODEL} — Ollama base: {Config.OLLAMA_BASE_URL}")
render_page_disclaimer()
