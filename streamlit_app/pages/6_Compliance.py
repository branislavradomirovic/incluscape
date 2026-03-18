import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
import re
import time
from datetime import date, datetime
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import Config
from database.db_manager import DatabaseManager
from document_processing.semantic_comparison.category_matcher import CategoryMatcher
from document_processing.semantic_comparison.compliance_checker import ComplianceChecker
from document_processing.semantic_comparison.reference_updater import ReferenceTemplateUpdater
from streamlit_app.components.help_button import render_help_button
from streamlit_app.components.sidebar import render_sidebar


st.set_page_config(page_title="Compliance - INCLUSCAPE", page_icon="🔎", layout="wide")
render_sidebar()

col1, col2 = st.columns([14, 4])
with col1:
    st.title("🔎 Semantic Compliance Analysis")
with col2:
    render_help_button("🔎 Compliance")


db = DatabaseManager()
db.initialize()
org_id = st.session_state.get("org_id", db.get_or_create_organisation("Default Organisation"))
provider = Config.SEMANTIC_LLM_PROVIDER.lower()

if not Config.ENABLE_SEMANTIC_ANALYSIS:
    st.info("Semantic analysis is disabled. Set ENABLE_SEMANTIC_ANALYSIS=True in .env.")
    st.stop()

if provider not in {"gemini", "ollama"}:
    st.error("Unsupported semantic provider. Set SEMANTIC_LLM_PROVIDER=gemini or ollama.")
    st.stop()

if provider == "gemini" and not Config.GEMINI_API_KEY:
    st.warning("Gemini API key not configured. Set GEMINI_API_KEY in .env.")
    st.stop()


@st.cache_resource
def get_checker():
    _db = DatabaseManager()
    matcher = CategoryMatcher(db=_db)
    matcher.seed_database()
    return ComplianceChecker(db=_db, matcher=matcher)


checker = get_checker()


def run_llm_health_check() -> dict:
    analyzer = checker.matcher.analyzer
    started = time.time()
    probe = analyzer.classify_document("Accessibility policy health check probe text.")
    elapsed = time.time() - started
    return {
        "ok": "error" not in probe,
        "latency": elapsed,
        "error": probe.get("error", ""),
        "model": getattr(analyzer, "model_name", "unknown"),
        "provider": getattr(analyzer, "provider", provider),
    }


def _tokenize(text: str) -> set:
    limited_text = (text or "")[:Config.COMPLIANCE_TOKENIZE_CHAR_LIMIT]
    return {t for t in re.findall(r"\b\w+\b", limited_text.lower()) if len(t) > 2}


def _coverage_score(items, doc_tokens: set) -> float:
    if not items:
        return 0.0
    matched = 0
    for item in items:
        item_tokens = _tokenize(str(item))
        if item_tokens and (item_tokens & doc_tokens):
            matched += 1
    return matched / max(len(items), 1)


def _score_reference_template(template: dict, doc_tokens: set, detected_body: str, detected_category: str) -> dict:
    kw_score = _coverage_score(template.get("keywords", []), doc_tokens)
    req_score = _coverage_score(template.get("key_requirements", []), doc_tokens)
    sec_score = _coverage_score(template.get("key_sections", []), doc_tokens)

    bonus = 0.0
    if (template.get("body") or "").lower() == (detected_body or "").lower():
        bonus += 0.15
    if (template.get("category") or "").lower() == (detected_category or "").lower():
        bonus += 0.10

    total = min(1.0, kw_score * 0.45 + req_score * 0.35 + sec_score * 0.20 + bonus)
    return {
        "template": template,
        "score": total,
        "keyword_coverage": kw_score,
        "requirements_coverage": req_score,
        "sections_coverage": sec_score,
    }


def _select_reference_candidates(templates: list, detected_body: str, detected_category: str, max_candidates: int = 120) -> list:
    exact = [
        t for t in templates
        if (t.get("body") or "").lower() == (detected_body or "").lower()
        and (t.get("category") or "").lower() == (detected_category or "").lower()
    ]
    same_body = [t for t in templates if (t.get("body") or "").lower() == (detected_body or "").lower()]
    same_category = [t for t in templates if (t.get("category") or "").lower() == (detected_category or "").lower()]

    seen = set()
    ordered = []
    for group in (exact, same_body, same_category, templates):
        for t in group:
            key = t.get("id") or f"{t.get('body', '')}|{t.get('category', '')}|{t.get('name', '')}"
            if key not in seen:
                seen.add(key)
                ordered.append(t)
            if len(ordered) >= max_candidates:
                return ordered
    return ordered


def _build_executive_summary(result: dict, elapsed: float) -> str:
    score = result.get("compliance_score") or 0.0
    missing = len(result.get("missing_elements") or [])
    partial = len(result.get("partial_elements") or [])
    present = len(result.get("present_elements") or [])
    top_recs = result.get("recommendations") or []

    if score >= 0.75:
        rating = "High alignment"
    elif score >= 0.50:
        rating = "Moderate alignment"
    else:
        rating = "Low alignment"

    lines = [
        f"Overall assessment: **{rating}** with compliance score **{score:.0%}** (analysis time {elapsed:.2f}s).",
        f"Coverage snapshot: **{present} present**, **{missing} missing**, **{partial} partial** elements.",
    ]
    top_strengths = (result.get("strengths") or result.get("present_elements") or [])[:3]
    top_gaps = (result.get("gaps") or result.get("missing_elements") or [])[:3]
    if top_strengths:
        lines.append("Top strengths: " + "; ".join(top_strengths))
    if top_gaps:
        lines.append("Top gaps: " + "; ".join(top_gaps))
    if top_recs:
        lines.append("Priority actions: " + "; ".join(top_recs[:3]))
    else:
        lines.append("Priority actions: Continue monitoring and maintain current controls.")
    return "\n\n".join(lines)


def _compute_shap_proxy(result: dict, xai_metrics: Optional[dict] = None) -> dict:
    present = len(result.get("present_elements") or [])
    strengths = len(result.get("strengths") or [])
    missing = len(result.get("missing_elements") or [])
    partial = len(result.get("partial_elements") or [])
    gaps = len(result.get("gaps") or [])
    recs = len(result.get("recommendations") or [])

    total = max(present + strengths + missing + partial + gaps + recs, 1)
    proxy = {
        "Present elements": min(1.0, present / total * 2.2),
        "Strengths": min(1.0, strengths / total * 2.2),
        "Missing elements": -min(1.0, missing / total * 2.2),
        "Partial elements": -min(1.0, partial / total * 1.8),
        "Gaps": -min(1.0, gaps / total * 2.2),
        "Recommendation pressure": -min(1.0, recs / total * 1.6),
    }

    if xai_metrics:
        proxy["Keyword coverage"] = float(xai_metrics.get("keyword_coverage", 0.0)) * 0.9
        proxy["Requirement coverage"] = float(xai_metrics.get("requirements_coverage", 0.0)) * 1.0
        proxy["Section coverage"] = float(xai_metrics.get("sections_coverage", 0.0)) * 0.8

    return {k: max(-1.0, min(1.0, float(v))) for k, v in proxy.items()}


def _render_shap_heatmap(shap_proxy: dict, chart_title: str = "SHAP-style heatmap (feature contribution proxy)") -> None:
    if not shap_proxy:
        st.info("No SHAP proxy data available.")
        return

    labels = list(shap_proxy.keys())
    values = [float(shap_proxy[k]) for k in labels]
    fig = go.Figure(
        data=go.Heatmap(
            z=[values],
            x=labels,
            y=["Contribution"],
            zmin=-1,
            zmax=1,
            colorscale=[
                [0.0, "#b30000"],
                [0.25, "#f46d43"],
                [0.5, "#fff7bc"],
                [0.75, "#78c679"],
                [1.0, "#238443"],
            ],
            zmid=0,
            text=[[f"{v:+.2f}" for v in values]],
            texttemplate="%{text}",
            hovertemplate="%{x}<br>Contribution=%{z:.2f}<extra></extra>",
        )
    )
    fig.update_layout(title=chart_title, height=260, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Positive values support compliance score; negative values reduce it. This is a transparent SHAP-style proxy, not model-internal SHAP.")


def _to_pdf_safe(text: str) -> str:
    return (text or "").encode("latin-1", "replace").decode("latin-1")


def _build_executive_pdf(
    document_label: str,
    provider_name: str,
    model_name: str,
    result: dict,
    executive_summary: str,
    reference_rows: list,
    xai_metrics: Optional[dict] = None,
    shap_proxy: Optional[dict] = None,
):
    try:
        from fpdf import FPDF
    except Exception as exc:
        return None, f"PDF dependency missing: {exc}"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _to_pdf_safe("INCLUSCAPE - Executive Compliance Brief"), ln=True)
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 6, _to_pdf_safe(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"), ln=True)
    pdf.cell(0, 6, _to_pdf_safe(f"Document: {document_label}"), ln=True)
    pdf.cell(0, 6, _to_pdf_safe(f"Provider/Model: {provider_name.upper()} / {model_name}"), ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Executive Summary", ln=True)
    pdf.set_font("Helvetica", size=10)
    for para in (executive_summary or "").split("\n\n"):
        if para.strip():
            pdf.multi_cell(0, 6, _to_pdf_safe(para.strip()), wrapmode="CHAR")
            pdf.ln(1)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Top Risks", ln=True)
    pdf.set_font("Helvetica", size=10)
    top_risks = (result.get("gaps") or []) + (result.get("missing_elements") or [])
    if top_risks:
        for idx, risk in enumerate(top_risks[:5], 1):
            pdf.multi_cell(0, 6, _to_pdf_safe(f"{idx}. {risk}"), wrapmode="CHAR")
    else:
        pdf.multi_cell(0, 6, "No critical risks detected.", wrapmode="CHAR")

    if xai_metrics or shap_proxy:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "XAI Snapshot", ln=True)
        pdf.set_font("Helvetica", size=10)
        if xai_metrics:
            pdf.multi_cell(
                0,
                6,
                _to_pdf_safe(
                    "Coverage metrics: "
                    f"Keyword {xai_metrics.get('keyword_coverage', 0.0):.0%}, "
                    f"Requirement {xai_metrics.get('requirements_coverage', 0.0):.0%}, "
                    f"Section {xai_metrics.get('sections_coverage', 0.0):.0%}."
                ),
                wrapmode="CHAR",
            )
        if shap_proxy:
            pdf.multi_cell(0, 6, "SHAP-style contribution proxy:", wrapmode="CHAR")
            for feature, score in sorted(shap_proxy.items(), key=lambda kv: abs(kv[1]), reverse=True):
                pdf.multi_cell(0, 6, _to_pdf_safe(f"- {feature}: {score:+.2f}"), wrapmode="CHAR")

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Reference Relevance Table (Top 10)", ln=True)
    pdf.set_font("Helvetica", size=9)
    for row in reference_rows[:10]:
        line = (
            f"#{row.get('Rank')} | {row.get('Reference document')} | "
            f"{row.get('Body')}/{row.get('Category')} | "
            f"Score {row.get('Relevance score')} | Used: {row.get('Used in final check')}"
        )
        pdf.multi_cell(0, 6, _to_pdf_safe(line), wrapmode="CHAR")

    raw = pdf.output(dest="S")
    if isinstance(raw, bytearray):
        raw = bytes(raw)
    elif isinstance(raw, str):
        raw = raw.encode("latin-1", "replace")
    return raw, ""


def _render_accent_section_heading(title: str, subtitle: str = "") -> None:
    subtitle_html = ""
    if subtitle:
        subtitle_html = (
            f"<div style='font-size: 0.84rem; color: rgba(20, 79, 71, 0.82); margin-top: 0.08rem;'>{subtitle}</div>"
        )
    st.markdown(
        f"""
        <div style="
            margin: 0.35rem 0 0.65rem 0;
            padding: 0.48rem 0.75rem;
            border-left: 4px solid rgb(32, 118, 106);
            background: linear-gradient(135deg, rgba(232, 246, 242, 0.90), rgba(244, 250, 248, 0.96));
            border-radius: 0.45rem;
        ">
            <div style="font-size: 1.0rem; font-weight: 700; color: rgb(20, 79, 71);">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _on_category_change() -> None:
    st.session_state.pop("compliance_selected_document", None)


def _render_ollama_tuning_diagnostics(health: dict) -> None:
    def _fmt_opt(value) -> str:
        return "auto" if value is None else str(value)

    with st.container(border=True):
        st.markdown(
            """
            <div style="
                margin-bottom: 0.55rem;
                padding: 0.45rem 0.7rem;
                border-left: 4px solid rgb(32, 118, 106);
                background: linear-gradient(135deg, rgba(232, 246, 242, 0.92), rgba(244, 250, 248, 0.96));
                border-radius: 0.45rem;
            ">
                <div style="font-size: 1.05rem; font-weight: 700; color: rgb(20, 79, 71);">⚙️ Ollama Tuning Diagnostics</div>
                <div style="font-size: 0.84rem; color: rgba(20, 79, 71, 0.82); margin-top: 0.1rem;">Active runtime options and recent timing snapshot for local tuning.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div style='font-size: 0.84rem; font-weight: 700; color: rgb(20, 79, 71); margin: 0.1rem 0 0.4rem 0;'>Runtime Options</div>",
            unsafe_allow_html=True,
        )

        runtime_rows = [
            {"Option": "Provider", "Value": provider.upper()},
            {"Option": "Model", "Value": health.get("model", "unknown")},
            {"Option": "OLLAMA_TIMEOUT_SEC", "Value": str(Config.OLLAMA_TIMEOUT_SEC)},
            {"Option": "OLLAMA_KEEP_ALIVE", "Value": str(Config.OLLAMA_KEEP_ALIVE)},
            {"Option": "OLLAMA_NUM_CTX", "Value": str(Config.OLLAMA_NUM_CTX)},
            {"Option": "OLLAMA_NUM_THREAD", "Value": _fmt_opt(Config.OLLAMA_NUM_THREAD)},
            {"Option": "OLLAMA_NUM_GPU", "Value": _fmt_opt(Config.OLLAMA_NUM_GPU)},
            {"Option": "OLLAMA_NUM_BATCH", "Value": _fmt_opt(Config.OLLAMA_NUM_BATCH)},
        ]
        st.dataframe(pd.DataFrame(runtime_rows), use_container_width=True, hide_index=True)

        last_run = st.session_state.get("compliance_last_run") or {}
        last_payload = last_run.get("payload") or {}
        last_job = last_run.get("job") or {}

        last_status = "No run yet"
        last_elapsed = "-"
        if last_run:
            if last_payload.get("ok"):
                last_status = "Success"
                try:
                    last_elapsed = f"{float(last_payload.get('elapsed_sec', 0.0)):.2f}s"
                except Exception:
                    last_elapsed = str(last_payload.get("elapsed_sec") or "-")
            else:
                last_status = "Failed"

        st.markdown(
            "<div style='font-size: 0.84rem; font-weight: 700; color: rgb(20, 79, 71); margin: 0.65rem 0 0.4rem 0;'>Last Run Snapshot</div>",
            unsafe_allow_html=True,
        )

        summary_rows = [
            {"Metric": "Last run status", "Value": last_status},
            {"Metric": "Last run elapsed", "Value": last_elapsed},
            {"Metric": "Last run document", "Value": str(last_job.get("selected_label") or "-")},
        ]
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
        st.caption("Use this box to compare settings vs latency while tuning Apple M1 performance.")




# Session state
if "compliance_last_run" not in st.session_state:
    st.session_state["compliance_last_run"] = None
if "compliance_last_run_flash" not in st.session_state:
    st.session_state["compliance_last_run_flash"] = ""
if "compliance_run_state" not in st.session_state:
    st.session_state["compliance_run_state"] = {
        "state": "idle",
        "message": "Ready to run compliance analysis.",
        "updated_at": None,
    }
if "llm_health" not in st.session_state:
    st.session_state["llm_health"] = run_llm_health_check()

health_col, health_btn_col = st.columns([6, 1])
with health_btn_col:
    if st.button("Refresh health", use_container_width=True):
        st.session_state["llm_health"] = run_llm_health_check()

health = st.session_state["llm_health"]
with health_col:
    if health["ok"]:
        st.success(f"{health['provider'].upper()} ready (model `{health['model']}`, probe {health['latency']:.2f}s).")
    else:
        st.warning(f"{health['provider'].upper()} unavailable. Reason: {health['error'][:180]}")

if provider == "ollama":
    _render_ollama_tuning_diagnostics(health)

st.markdown("---")
_render_accent_section_heading(
    "1 · Analysis Setup",
    "Choose the document scope and reference strategy before starting the analysis.",
)

docs = db.fetchall(
    "SELECT id, title, document_type FROM documents WHERE organisation_id = ? AND status = 'active' ORDER BY created_at DESC",
    (org_id,),
)
if not docs:
    st.info("No processed documents found. Upload documents first.")
    st.stop()

category_order = {name: idx for idx, name in enumerate(Config.DOCUMENT_CATEGORIES)}
available_categories = sorted({d["document_type"] for d in docs}, key=lambda c: category_order.get(c, 999))

setup_a, setup_b, setup_c = st.columns([2, 3, 3])
with setup_a:
    selected_category = st.selectbox("Document Category", available_categories, key="compliance_selected_category", on_change=_on_category_change)

filtered_docs = [d for d in docs if d.get("document_type") == selected_category]
if not filtered_docs:
    st.warning(f"No documents found for category '{selected_category}'.")
    st.stop()

doc_options = {f"{d['title']} (ID {d['id']})": d["id"] for d in filtered_docs}
doc_labels = list(doc_options.keys())
if st.session_state.get("compliance_selected_document") not in doc_labels:
    st.session_state["compliance_selected_document"] = doc_labels[0]

with setup_b:
    selected_label = st.selectbox("Document", doc_labels, key="compliance_selected_document")
    document_id = doc_options[selected_label]

all_templates = checker.matcher.get_all_templates()
tmpl_options = {f"🤖 Auto-detect ({provider.upper()})": None}
tmpl_options.update({f"{t['body']} — {t['name']}": t for t in all_templates})

with setup_c:
    selected_tmpl_label = st.selectbox("Reference template", list(tmpl_options.keys()))
    chosen_template = tmpl_options[selected_tmpl_label]
    if chosen_template and chosen_template.get("source_url"):
        st.caption(f"Reference source: {chosen_template.get('source_url')}")

run_btn = st.button("🚀 Run Compliance Analysis", type="primary", use_container_width=True)

run_state = st.session_state.get("compliance_run_state") or {}
run_state_status = str(run_state.get("state") or "idle")
run_state_message = str(run_state.get("message") or "")
run_state_updated_at = run_state.get("updated_at")
run_state_updated_label = ""
if isinstance(run_state_updated_at, (int, float)):
    run_state_updated_label = datetime.fromtimestamp(run_state_updated_at).strftime("%H:%M:%S")

status_col, status_meta_col = st.columns([9, 2])
with status_col:
    if run_state_status == "running":
        st.info(f"⏳ {run_state_message}")
    elif run_state_status == "completed":
        st.success(f"✅ {run_state_message}")
    elif run_state_status == "completed_with_warnings":
        st.warning(f"⚠️ {run_state_message}")
    elif run_state_status == "failed":
        st.error(f"❌ {run_state_message}")
    elif run_state_message:
        st.caption(run_state_message)

with status_meta_col:
    if run_state_updated_label:
        st.caption(f"Last updated at {run_state_updated_label}")

if run_btn:
    job_meta = {
        "document_id": document_id,
        "selected_label": selected_label,
        "provider": provider.upper(),
        "model": health.get("model", "unknown"),
    }
    st.session_state["compliance_run_state"] = {
        "state": "running",
        "message": f"Analysis in progress for {selected_label} using {provider.upper()} / {health.get('model', 'unknown')}...",
        "updated_at": time.time(),
    }
    with st.spinner(
        f"Running compliance analysis with {provider.upper()} / {health.get('model', 'unknown')} — this may take 1–3 minutes..."
    ):
        try:
            pages_for_run = db.fetchall(
                "SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number",
                (document_id,),
            )
            doc_text_for_run = "\n".join(p["content"] for p in pages_for_run if p.get("content"))
            if not doc_text_for_run.strip():
                st.error("No extracted text found for this document. Re-process it first.")
                st.session_state["compliance_run_state"] = {
                    "state": "failed",
                    "message": "No extracted text found for this document. Re-process it first.",
                    "updated_at": time.time(),
                }
            else:
                _started = time.time()
                _raw_result = checker.analyse(
                    document_id=document_id,
                    document_text=doc_text_for_run,
                    reference_template=chosen_template,
                )
                _result = _raw_result if isinstance(_raw_result, dict) else {
                    "error": "",
                    "summary": str(_raw_result),
                    "compliance_score": 0.0,
                    "present_elements": [],
                    "missing_elements": [],
                    "partial_elements": [],
                    "strengths": [],
                    "gaps": [],
                    "recommendations": [],
                    "reference_template": chosen_template or {},
                    "body_detected": (chosen_template or {}).get("body", "Unknown body"),
                    "category_detected": (chosen_template or {}).get("category", "Unknown category"),
                }
                _elapsed = round(time.time() - _started, 2)
                _error_text = str(_result.get("error") or "").strip() if isinstance(_result, dict) else ""
                _summary_text = str(_result.get("summary") or "").strip() if isinstance(_result, dict) else ""

                def _len_list(v):
                    return len(v) if isinstance(v, list) else 0

                _has_structured_output = (
                    bool(_summary_text)
                    or _len_list(_result.get("present_elements")) > 0
                    or _len_list(_result.get("missing_elements")) > 0
                    or _len_list(_result.get("partial_elements")) > 0
                    or _len_list(_result.get("strengths")) > 0
                    or _len_list(_result.get("gaps")) > 0
                    or _len_list(_result.get("recommendations")) > 0
                )

                st.session_state["compliance_last_run"] = {
                    "job": job_meta,
                    "payload": {
                        "ok": isinstance(_result, dict) and bool(_result),
                        "result": _result,
                        "elapsed_sec": _elapsed,
                    },
                    "finished_at": time.time(),
                }
                if _has_structured_output and not _error_text:
                    _status_state = "completed"
                    _status_msg = f"Compliance analysis completed in {_elapsed:.2f}s with structured LLM output."
                elif _has_structured_output and _error_text:
                    _status_state = "completed_with_warnings"
                    _status_msg = (
                        f"Compliance analysis completed in {_elapsed:.2f}s with partial output. "
                        f"Model warning: {_error_text[:140]}"
                    )
                else:
                    _status_state = "completed_with_warnings"
                    _status_msg = (
                        f"Compliance analysis finished in {_elapsed:.2f}s but structured LLM output is empty. "
                        "Review model warnings and raw payload below."
                    )

                st.session_state["compliance_run_state"] = {
                    "state": _status_state,
                    "message": _status_msg,
                    "updated_at": time.time(),
                }
        except Exception as _exc:
            import traceback as _tb
            st.error(f"Analysis error: {_exc}")
            st.session_state["compliance_run_state"] = {
                "state": "failed",
                "message": f"Analysis failed: {_exc}",
                "updated_at": time.time(),
            }
            with st.expander("Debug traceback"):
                st.code(_tb.format_exc())

latest_snapshot = st.session_state.get("compliance_last_run") or {}
latest_payload = latest_snapshot.get("payload") or {}
latest_result = latest_payload.get("result") if isinstance(latest_payload, dict) else None

if isinstance(latest_result, dict):
    _render_accent_section_heading(
        "Latest LLM Output Snapshot",
        "Immediate visibility of key outputs before reference/admin sections.",
    )
    snapshot_score = latest_result.get("compliance_score") or 0.0
    try:
        snapshot_score = float(snapshot_score)
    except Exception:
        snapshot_score = 0.0

    snapshot_summary = latest_result.get("summary") or ""
    snapshot_present = latest_result.get("present_elements") or []
    snapshot_missing = latest_result.get("missing_elements") or []
    snapshot_partial = latest_result.get("partial_elements") or []
    snapshot_strengths = latest_result.get("strengths") or []
    snapshot_gaps = latest_result.get("gaps") or []
    snapshot_recs = latest_result.get("recommendations") or []

    def _to_list_snapshot(value):
        if isinstance(value, list):
            return value
        if value is None:
            return []
        return [str(value)]

    snapshot_present = _to_list_snapshot(snapshot_present)
    snapshot_missing = _to_list_snapshot(snapshot_missing)
    snapshot_partial = _to_list_snapshot(snapshot_partial)
    snapshot_strengths = _to_list_snapshot(snapshot_strengths)
    snapshot_gaps = _to_list_snapshot(snapshot_gaps)
    snapshot_recs = _to_list_snapshot(snapshot_recs)

    snap_c1, snap_c2, snap_c3, snap_c4 = st.columns(4)
    snap_c1.metric("Score", f"{snapshot_score:.0%}")
    snap_c2.metric("Present", str(len(snapshot_present) if isinstance(snapshot_present, list) else 0))
    snap_c3.metric("Missing", str(len(snapshot_missing) if isinstance(snapshot_missing, list) else 0))
    snap_c4.metric("Recommendations", str(len(snapshot_recs) if isinstance(snapshot_recs, list) else 0))

    if snapshot_summary:
        st.info(snapshot_summary)
    elif latest_result.get("error"):
        st.warning(f"Model warning: {latest_result.get('error')}")
    else:
        st.warning("LLM output is available but summary text is empty; see detailed tabs below.")

    with st.expander("LLM Output - Detailed Compliance Sections", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**GAP section**")
            if snapshot_gaps:
                for item in snapshot_gaps:
                    st.markdown(f"- {item}")
            else:
                st.info("No explicit gap entries returned.")

            st.markdown("**Missing elements**")
            if snapshot_missing:
                for item in snapshot_missing:
                    st.markdown(f"- ❌ {item}")
            else:
                st.info("No missing elements returned.")

            st.markdown("**Partial elements**")
            if snapshot_partial:
                for item in snapshot_partial:
                    st.markdown(f"- 🔶 {item}")
            else:
                st.info("No partial elements returned.")

        with col_b:
            st.markdown("**Present elements**")
            if snapshot_present:
                for item in snapshot_present:
                    st.markdown(f"- ✅ {item}")
            else:
                st.info("No present elements returned.")

            st.markdown("**Strengths**")
            if snapshot_strengths:
                for item in snapshot_strengths:
                    st.markdown(f"- 💪 {item}")
            else:
                st.info("No strengths returned.")

            st.markdown("**Recommendations**")
            if snapshot_recs:
                for idx, item in enumerate(snapshot_recs, 1):
                    st.markdown(f"{idx}. {item}")
            else:
                st.info("No recommendations returned.")

        raw_payload = latest_result.get("full_response_json")
        parsed_payload = None
        if isinstance(raw_payload, str) and raw_payload.strip():
            try:
                parsed_payload = json.loads(raw_payload)
            except Exception:
                parsed_payload = {"raw": raw_payload}
        elif isinstance(raw_payload, dict):
            parsed_payload = raw_payload

        if parsed_payload:
            st.markdown("**Raw model payload**")
            st.json(parsed_payload, expanded=False)

_render_accent_section_heading(
    "2 · Reference & Admin Tools",
    "Refresh framework sources and review prior analyses for the selected document.",
)

with st.expander("Show Tools", expanded=False):
    if st.button("Refresh all reference sources", use_container_width=True):
        checker.matcher.seed_database()
        updater = ReferenceTemplateUpdater(db)
        refresh_results = updater.refresh_bodies()
        changed = sum(1 for r in refresh_results if r.get("updated"))
        errors = [r for r in refresh_results if r.get("error")]
        st.success(f"Refresh complete: {changed} updated, {len(refresh_results) - changed - len(errors)} unchanged, {len(errors)} errors.")

    st.markdown("---")
    st.markdown("**External reference documents for selected category**")
    external_refs = [
        t for t in (all_templates or [])
        if (t.get("category") or "").strip().lower() == (selected_category or "").strip().lower()
    ]
    if external_refs:
        refs_df = pd.DataFrame([
            {
                "Name": t.get("name", ""),
                "Body": t.get("body", ""),
                "Category": t.get("category", ""),
                "Last refresh": t.get("source_last_checked") or t.get("created_at") or "-",
                "Version": t.get("version", "-"),
                "URL": t.get("source_url", ""),
            }
            for t in external_refs
        ])
        refs_df = refs_df.sort_values(by=["Body", "Name"], kind="stable")
        st.dataframe(refs_df, use_container_width=True, hide_index=True)
    else:
        st.info(f"No external reference templates are attached to '{selected_category}' yet.")

    st.markdown("---")
    st.markdown("**Past analyses for selected document**")
    past = checker.get_analyses(document_id)
    if past:
        df = pd.DataFrame([
            {
                "Date": r["created_at"],
                "Body detected": r.get("body_detected", ""),
                "Category": r.get("category_detected", ""),
                "Reference": r.get("reference_name", ""),
                "Source": r.get("source_url", ""),
                "Score": f"{r['compliance_score']:.0%}" if r.get("compliance_score") is not None else "-",
            }
            for r in past
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No analyses run yet for this document.")

latest_saved_analysis = past[0] if past else None


last_run = st.session_state.get("compliance_last_run")
if last_run:
    _res_hdr, _res_clr = st.columns([10, 2])
    with _res_clr:
        if st.button("🗑 Clear results", use_container_width=True):
            st.session_state["compliance_last_run"] = None
            st.session_state["compliance_run_state"] = {
                "state": "idle",
                "message": "Ready to run compliance analysis.",
                "updated_at": time.time(),
            }
            st.rerun()

    payload = last_run.get("payload") or {}
    job = last_run.get("job") or {}

    if not payload.get("ok"):
        st.warning(f"Analysis returned warnings: {payload.get('error', 'Unknown worker status')}")

    try:
            result = payload.get("result") or {}
            if not isinstance(result, dict):
                result = {"summary": str(result), "compliance_score": 0.0}

            def _as_list(value):
                if isinstance(value, list):
                    return value
                if value is None:
                    return []
                return [str(value)]

            try:
                _score = float(result.get("compliance_score") or 0.0)
            except Exception:
                _score = 0.0
            result["compliance_score"] = max(0.0, min(1.0, _score))

            for _k in ("present_elements", "missing_elements", "partial_elements", "strengths", "gaps", "recommendations"):
                result[_k] = _as_list(result.get(_k))

            if not isinstance(result.get("summary"), str):
                result["summary"] = str(result.get("summary") or "")

            has_structured_output = any([
                bool(result.get("summary", "").strip()),
                bool(result.get("present_elements")),
                bool(result.get("missing_elements")),
                bool(result.get("partial_elements")),
                bool(result.get("strengths")),
                bool(result.get("gaps")),
                bool(result.get("recommendations")),
            ])

            if not has_structured_output:
                st.error(
                    "LLM analysis returned an empty structured payload. "
                    "The run completed, but no usable compliance fields were produced."
                )
                if result.get("error"):
                    st.caption(f"Model error detail: {result.get('error')}")

            try:
                worker_elapsed = float(payload.get("elapsed_sec") or 0.0)
            except Exception:
                worker_elapsed = 0.0

            pages = db.fetchall("SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number", (job.get("document_id", document_id),))
            document_text = "\n".join(p["content"] for p in pages if p.get("content"))

            ref = result.get("reference_template") or {}
            detected_body = result.get("body_detected") or "Unknown body"
            detected_category = result.get("category_detected") or "Unknown category"

            doc_tokens = _tokenize(document_text)
            candidate_templates = _select_reference_candidates(all_templates, detected_body, detected_category)
            scored_refs = sorted(
                [_score_reference_template(t, doc_tokens, detected_body, detected_category) for t in candidate_templates],
                key=lambda x: x["score"],
                reverse=True,
            )[:10]

            current_ref_id = ref.get("id")
            reference_rows = []
            for idx, item in enumerate(scored_refs, 1):
                tmpl = item["template"]
                is_used = (current_ref_id is not None and tmpl.get("id") == current_ref_id) or (
                    ref.get("name") and tmpl.get("name") == ref.get("name")
                )
                reference_rows.append({
                    "Rank": idx,
                    "Reference document": tmpl.get("name", ""),
                    "Body": tmpl.get("body", ""),
                    "Category": tmpl.get("category", ""),
                    "Relevance score": f"{item['score']:.0%}",
                    "Keyword": f"{item['keyword_coverage']:.0%}",
                    "Requirements": f"{item['requirements_coverage']:.0%}",
                    "Sections": f"{item['sections_coverage']:.0%}",
                    "Used in final check": "Yes" if is_used else "No",
                })

            xai_template = ref if ref else {
                "body": detected_body,
                "category": detected_category,
                "name": "Auto-detected template context",
                "keywords": [],
                "key_requirements": (result.get("missing_elements") or []) + (result.get("present_elements") or []),
                "key_sections": [],
            }
            xai_metrics = _score_reference_template(xai_template, doc_tokens, detected_body, detected_category)
            shap_proxy = _compute_shap_proxy(result, xai_metrics)

            if result.get("error"):
                st.warning(f"Model returned warning: {result.get('error')}")

            executive_summary = _build_executive_summary(result, worker_elapsed)
            pdf_bytes, pdf_error = _build_executive_pdf(
                document_label=job.get("selected_label") or selected_label,
                provider_name=provider,
                model_name=health.get("model", "unknown"),
                result=result,
                executive_summary=executive_summary,
                reference_rows=reference_rows,
                xai_metrics=xai_metrics,
                shap_proxy=shap_proxy,
            )

            st.subheader("3 · Analysis Results")
            st.info(executive_summary)
            st.caption(f"Background worker time: {worker_elapsed:.2f}s")

            with st.expander("Executive Summary - Full Detail", expanded=True):
                st.markdown("**Top strengths**")
                for item in (result.get("strengths") or result.get("present_elements") or [])[:8]:
                    st.markdown(f"- {item}")
                st.markdown("**Top gaps / risks**")
                for item in ((result.get("gaps") or []) + (result.get("missing_elements") or []))[:8]:
                    st.markdown(f"- {item}")
                st.markdown("**Priority recommendations**")
                for idx, item in enumerate((result.get("recommendations") or [])[:8], 1):
                    st.markdown(f"{idx}. {item}")

            if pdf_error:
                st.warning(pdf_error)
            elif pdf_bytes:
                filename = f"executive_compliance_brief_{job.get('document_id', document_id)}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
                st.download_button("📄 Download Executive PDF", data=pdf_bytes, file_name=filename, mime="application/pdf", use_container_width=True)

            st.markdown("**Detailed breakdown**")
            score = float(result.get("compliance_score") or 0.0)
            colour = "green" if score >= 0.7 else "orange" if score >= 0.4 else "red"
            st.markdown(
                f"### Compliance Score: <span style='color:{colour};font-size:2rem;font-weight:bold'>{score:.0%}</span>",
                unsafe_allow_html=True,
            )

            if ref.get("name"):
                st.caption(f"Compared against: **{ref.get('name')}** ({ref.get('body', detected_body)} · {ref.get('category', detected_category)})")
            else:
                st.caption(f"Compared against: **No exact template matched** (Detected: {detected_body} · {detected_category})")
            if ref.get("source_url"):
                st.markdown(f"Source reference: [Open official framework]({ref.get('source_url')})")

            st.markdown(f"**Model summary:** {result.get('summary', '')}")
            st.caption("Tabs below provide the full executive detail pack for stakeholder review.")
            st.markdown("---")

            tab_gaps, tab_present, tab_rec, tab_xai, tab_ref = st.tabs(
                ["⚠️ Gaps & Missing", "✅ Present Elements", "💡 Recommendations", "🧠 XAI", "📚 Reference"]
            )

            with tab_gaps:
                gaps_items = (result.get("gaps") or []) + (result.get("missing_elements") or []) + (result.get("partial_elements") or [])
                if gaps_items:
                    for g in (result.get("gaps") or []):
                        st.markdown(f"- {g}")
                    for m in (result.get("missing_elements") or []):
                        st.markdown(f"- ❌ {m}")
                    for p_el in (result.get("partial_elements") or []):
                        st.markdown(f"- 🔶 {p_el}")
                else:
                    st.info("No gaps or missing elements detected.")

            with tab_present:
                present_items = (result.get("present_elements") or []) + (result.get("strengths") or [])
                if present_items:
                    for item in (result.get("present_elements") or []):
                        st.markdown(f"- ✅ {item}")
                    for s in (result.get("strengths") or []):
                        st.markdown(f"- 💪 {s}")
                else:
                    st.info("No present elements recorded.")

            with tab_rec:
                recs = result.get("recommendations") or []
                if recs:
                    for i, rec in enumerate(recs, 1):
                        st.markdown(f"**{i}.** {rec}")
                else:
                    st.info("No specific recommendations.")

            with tab_xai:
                metrics_df = pd.DataFrame([
                    {"Metric": "LLM Provider", "Value": provider.upper()},
                    {"Metric": "LLM Model", "Value": health.get("model", "unknown")},
                    {"Metric": "Detected Body", "Value": detected_body},
                    {"Metric": "Detected Category", "Value": detected_category},
                    {"Metric": "Compliance Score", "Value": f"{score:.0%}"},
                    {"Metric": "Keyword coverage", "Value": f"{xai_metrics['keyword_coverage']:.0%}"},
                    {"Metric": "Requirement coverage", "Value": f"{xai_metrics['requirements_coverage']:.0%}"},
                    {"Metric": "Section coverage", "Value": f"{xai_metrics['sections_coverage']:.0%}"},
                    {"Metric": "Worker elapsed", "Value": f"{worker_elapsed:.2f}s"},
                ])
                st.dataframe(metrics_df, use_container_width=True, hide_index=True)
                st.caption("XAI breakdown: coverage scores show how many reference template keywords/requirements/sections appear in the document.")
                _render_shap_heatmap(shap_proxy)

            with tab_ref:
                if reference_rows:
                    st.dataframe(pd.DataFrame(reference_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("No reference templates scored.")

            with st.expander("Show LLM reasoning trace", expanded=True):
                st.caption("Step-by-step execution trace with evidence used to derive compliance output.")
                trace_rows = [
                    {
                        "Step": "1. Input assembly",
                        "Evidence": f"Document pages loaded: {len(pages)} | Token sample size: {len(doc_tokens)}"
                    },
                    {
                        "Step": "2. Template routing",
                        "Evidence": f"Detected body/category: {detected_body} / {detected_category} | Candidate templates: {len(candidate_templates)}"
                    },
                    {
                        "Step": "3. LLM comparison",
                        "Evidence": f"Provider/model: {provider.upper()} / {health.get('model', 'unknown')} | Worker time: {worker_elapsed:.2f}s"
                    },
                    {
                        "Step": "4. Element extraction",
                        "Evidence": f"Present: {len(result.get('present_elements') or [])}, Missing: {len(result.get('missing_elements') or [])}, Partial: {len(result.get('partial_elements') or [])}"
                    },
                    {
                        "Step": "5. Final scoring",
                        "Evidence": f"Compliance score: {score:.0%} | Gaps: {len(result.get('gaps') or [])} | Recommendations: {len(result.get('recommendations') or [])}"
                    },
                ]
                st.dataframe(pd.DataFrame(trace_rows), use_container_width=True, hide_index=True)

                st.markdown("**Top reference evidence used by scorer**")
                if reference_rows:
                    st.dataframe(pd.DataFrame(reference_rows[:5]), use_container_width=True, hide_index=True)
                else:
                    st.info("No reference evidence rows available.")

                raw_payload = result.get("full_response_json")
                parsed_payload = None
                if isinstance(raw_payload, str) and raw_payload.strip():
                    try:
                        parsed_payload = json.loads(raw_payload)
                    except Exception:
                        parsed_payload = {"raw": raw_payload}
                elif isinstance(raw_payload, dict):
                    parsed_payload = raw_payload

                if parsed_payload:
                    st.markdown("**Raw model payload (classification + comparison)**")
                    st.json(parsed_payload, expanded=True)
                else:
                    st.info("Raw model payload is not available for this run.")

    except Exception as _render_exc:
        import traceback as _tb
        st.error(f"Error displaying results: {_render_exc}")
        with st.expander("Debug: full traceback"):
            st.code(_tb.format_exc())
elif latest_saved_analysis:
    # Fallback: always show the newest persisted analysis from DB after refreshes.
    st.subheader("3 · Analysis Results")
    st.info(
        f"Loaded latest saved analysis from history ({latest_saved_analysis.get('created_at', '-')}). "
        "Run a new analysis to refresh these details."
    )
    saved_score = latest_saved_analysis.get("compliance_score") or 0.0
    saved_colour = "green" if saved_score >= 0.7 else "orange" if saved_score >= 0.4 else "red"
    st.markdown(
        f"### Compliance Score: <span style='color:{saved_colour};font-size:2rem;font-weight:bold'>{saved_score:.0%}</span>",
        unsafe_allow_html=True,
    )

    saved_missing = latest_saved_analysis.get("missing_elements") or []
    saved_partial = latest_saved_analysis.get("partial_elements") or []
    saved_present = latest_saved_analysis.get("present_elements") or []
    saved_strengths = latest_saved_analysis.get("strengths") or []
    saved_recs = latest_saved_analysis.get("recommendations") or []
    saved_gaps = latest_saved_analysis.get("gaps") or []
    saved_summary = latest_saved_analysis.get("summary") or ""

    # Ensure PDF export is available also for history/fallback results.
    saved_result_for_pdf = {
        "compliance_score": saved_score,
        "present_elements": saved_present,
        "missing_elements": saved_missing,
        "partial_elements": saved_partial,
        "strengths": saved_strengths,
        "gaps": saved_gaps,
        "recommendations": saved_recs,
        "summary": saved_summary,
    }
    saved_exec_summary = _build_executive_summary(saved_result_for_pdf, 0.0)
    saved_total = max(len(saved_present) + len(saved_missing) + len(saved_partial), 1)
    saved_xai_metrics = {
        "keyword_coverage": len(saved_present) / saved_total,
        "requirements_coverage": max(0.0, 1.0 - (len(saved_missing) / saved_total)),
        "sections_coverage": max(0.0, 1.0 - (len(saved_partial) / saved_total)),
    }
    saved_shap_proxy = _compute_shap_proxy(saved_result_for_pdf, saved_xai_metrics)
    saved_pdf_bytes, saved_pdf_error = _build_executive_pdf(
        document_label=selected_label,
        provider_name=provider,
        model_name=latest_saved_analysis.get("model_used") or health.get("model", "unknown"),
        result=saved_result_for_pdf,
        executive_summary=saved_exec_summary,
        reference_rows=[],
        xai_metrics=saved_xai_metrics,
        shap_proxy=saved_shap_proxy,
    )

    if saved_pdf_error:
        st.warning(saved_pdf_error)
    elif saved_pdf_bytes:
        saved_filename = (
            f"executive_compliance_brief_{document_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        st.download_button(
            "📄 Download Executive PDF",
            data=saved_pdf_bytes,
            file_name=saved_filename,
            mime="application/pdf",
            use_container_width=True,
        )

    if saved_summary:
        st.markdown(f"**Model summary:** {saved_summary}")

    def _to_list_saved(value):
        if isinstance(value, list):
            return value
        if value is None:
            return []
        return [str(value)]

    saved_present = _to_list_saved(saved_present)
    saved_missing = _to_list_saved(saved_missing)
    saved_partial = _to_list_saved(saved_partial)
    saved_strengths = _to_list_saved(saved_strengths)
    saved_gaps = _to_list_saved(saved_gaps)
    saved_recs = _to_list_saved(saved_recs)

    with st.expander("LLM Output - Detailed Compliance Sections", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**GAP section**")
            if saved_gaps:
                for item in saved_gaps:
                    st.markdown(f"- {item}")
            else:
                st.info("No explicit gap entries returned.")

            st.markdown("**Missing elements**")
            if saved_missing:
                for item in saved_missing:
                    st.markdown(f"- ❌ {item}")
            else:
                st.info("No missing elements returned.")

            st.markdown("**Partial elements**")
            if saved_partial:
                for item in saved_partial:
                    st.markdown(f"- 🔶 {item}")
            else:
                st.info("No partial elements returned.")

        with col_b:
            st.markdown("**Present elements**")
            if saved_present:
                for item in saved_present:
                    st.markdown(f"- ✅ {item}")
            else:
                st.info("No present elements returned.")

            st.markdown("**Strengths**")
            if saved_strengths:
                for item in saved_strengths:
                    st.markdown(f"- 💪 {item}")
            else:
                st.info("No strengths returned.")

            st.markdown("**Recommendations**")
            if saved_recs:
                for idx, item in enumerate(saved_recs, 1):
                    st.markdown(f"{idx}. {item}")
            else:
                st.info("No recommendations returned.")

        saved_raw_payload = latest_saved_analysis.get("full_response_json")
        saved_parsed_payload = None
        if isinstance(saved_raw_payload, str) and saved_raw_payload.strip():
            try:
                saved_parsed_payload = json.loads(saved_raw_payload)
            except Exception:
                saved_parsed_payload = {"raw": saved_raw_payload}
        elif isinstance(saved_raw_payload, dict):
            saved_parsed_payload = saved_raw_payload

        if saved_parsed_payload:
            st.markdown("**Raw model payload**")
            st.json(saved_parsed_payload, expanded=False)

    with st.expander("Executive Summary - Full Detail", expanded=True):
        st.markdown("**Top strengths**")
        for item in (saved_strengths or saved_present)[:8]:
            st.markdown(f"- {item}")
        st.markdown("**Top gaps / risks**")
        for item in (saved_gaps + saved_missing)[:8]:
            st.markdown(f"- {item}")
        st.markdown("**Priority recommendations**")
        for idx, item in enumerate(saved_recs[:8], 1):
            st.markdown(f"{idx}. {item}")

    tab_gaps, tab_present, tab_rec, tab_xai = st.tabs(
        ["⚠️ Gaps & Missing", "✅ Present Elements", "💡 Recommendations", "🧠 XAI"]
    )

    with tab_gaps:
        if saved_gaps or saved_missing or saved_partial:
            for g in saved_gaps:
                st.markdown(f"- {g}")
            for m in saved_missing:
                st.markdown(f"- ❌ {m}")
            for p_el in saved_partial:
                st.markdown(f"- 🔶 {p_el}")
        else:
            st.info("No gaps or missing elements detected.")

    with tab_present:
        if saved_present or saved_strengths:
            for item in saved_present:
                st.markdown(f"- ✅ {item}")
            for s in saved_strengths:
                st.markdown(f"- 💪 {s}")
        else:
            st.info("No present elements recorded.")

    with tab_rec:
        if saved_recs:
            for i, rec in enumerate(saved_recs, 1):
                st.markdown(f"**{i}.** {rec}")
        else:
            st.info("No specific recommendations.")

    with tab_xai:
        xai_df = pd.DataFrame([
            {"Metric": "LLM Provider", "Value": provider.upper()},
            {"Metric": "Model", "Value": latest_saved_analysis.get("model_used", "unknown")},
            {"Metric": "Detected Body", "Value": latest_saved_analysis.get("body_detected", "Unknown body")},
            {"Metric": "Detected Category", "Value": latest_saved_analysis.get("category_detected", "Unknown category")},
            {"Metric": "Compliance Score", "Value": f"{saved_score:.0%}"},
            {"Metric": "Present elements", "Value": str(len(saved_present))},
            {"Metric": "Missing elements", "Value": str(len(saved_missing))},
            {"Metric": "Partial elements", "Value": str(len(saved_partial))},
            {"Metric": "Keyword coverage (proxy)", "Value": f"{saved_xai_metrics['keyword_coverage']:.0%}"},
            {"Metric": "Requirement coverage (proxy)", "Value": f"{saved_xai_metrics['requirements_coverage']:.0%}"},
            {"Metric": "Section coverage (proxy)", "Value": f"{saved_xai_metrics['sections_coverage']:.0%}"},
        ])
        st.dataframe(xai_df, use_container_width=True, hide_index=True)
        st.caption("This XAI view explains outcome composition using detected category/body and element counts.")
        _render_shap_heatmap(saved_shap_proxy)



