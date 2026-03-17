import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
import time
import streamlit as st
import pandas as pd
from config import Config
from database.db_manager import DatabaseManager
from document_processing.semantic_comparison.compliance_checker import ComplianceChecker
from document_processing.semantic_comparison.category_matcher import CategoryMatcher
from document_processing.semantic_comparison.reference_updater import ReferenceTemplateUpdater
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.help_button import render_help_button

st.set_page_config(page_title="Compliance — INCLUSCAPE", page_icon="🔎", layout="wide")
render_sidebar()

col1, col2 = st.columns([20, 1])
with col1:
    st.title("🔎 Semantic Compliance Analysis")
with col2:
    render_help_button("🔎 Compliance")

db = DatabaseManager()
db.initialize()
org_id = st.session_state.get("org_id", db.get_or_create_organisation("Default Organisation"))
provider = Config.SEMANTIC_LLM_PROVIDER.lower()

if not Config.ENABLE_SEMANTIC_ANALYSIS:
    st.info(
        "Semantic analysis is disabled. "
        "Set `ENABLE_SEMANTIC_ANALYSIS=True` in your `.env` to enable it."
    )
    st.stop()

if provider not in {"gemini", "ollama"}:
    st.error(
        "Unsupported semantic provider configured. "
        "Set `SEMANTIC_LLM_PROVIDER=gemini` or `SEMANTIC_LLM_PROVIDER=ollama`."
    )
    st.stop()

if provider == "gemini" and not Config.GEMINI_API_KEY:
    st.warning(
        "**Gemini API key not configured.** "
        "Add `GEMINI_API_KEY=<your-key>` and `ENABLE_SEMANTIC_ANALYSIS=True` "
        "to your `.env` file, then restart the app.\n\n"
        "Get a free API key at [Google AI Studio](https://aistudio.google.com/app/apikey).",
    )
    st.stop()

# ── Initialise helpers ───────────────────────────────────────────────────────
@st.cache_resource
def get_checker():
    _db = DatabaseManager()
    matcher = CategoryMatcher(db=_db)
    matcher.seed_database()          # ensure reference templates are in DB
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
        "checked_at": time.time(),
    }


health_col, refresh_col = st.columns([6, 1])
with refresh_col:
    if st.button("Refresh health", use_container_width=True):
        st.session_state["llm_health"] = run_llm_health_check()

if "llm_health" not in st.session_state:
    st.session_state["llm_health"] = run_llm_health_check()

health = st.session_state["llm_health"]
with health_col:
    if health["ok"]:
        st.success(
            f"{health['provider'].upper()} health: available (model `{health['model']}`, "
            f"probe {health['latency']:.2f}s)."
        )
    else:
        st.warning(
            f"{health['provider'].upper()} health: unavailable. "
            f"Reason: {health['error'][:180]}"
        )

# ── Reference template selector ──────────────────────────────────────────────
st.markdown("---")
col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("1 · Select Document")
    docs = db.fetchall(
        "SELECT id, title, document_type FROM documents "
        "WHERE organisation_id = ? AND status = 'active' ORDER BY created_at DESC",
        (org_id,),
    )
    if not docs:
        st.info("No processed documents found. Upload documents first.")
        st.stop()

    doc_options = {f"{d['title']} [{d['document_type']}]": d["id"] for d in docs}
    selected_label = st.selectbox("Document", list(doc_options.keys()))
    document_id = doc_options[selected_label]

    st.subheader("2 · Reference Template")
    all_templates = checker.matcher.get_all_templates()
    tmpl_options = {f"🤖 Auto-detect ({provider.upper()})": None}
    tmpl_options.update({
        f"{t['body']} — {t['name']}": t
        for t in all_templates
    })
    selected_tmpl_label = st.selectbox("Reference template", list(tmpl_options.keys()))
    chosen_template = tmpl_options[selected_tmpl_label]

    if chosen_template and chosen_template.get("source_url"):
        st.caption(f"Reference source: {chosen_template.get('source_url')}")

    run_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

with col_right:
    st.subheader("3 · External Reference Refresh")
    st.caption("Checks UNESCO/EU source URLs and versions templates when upstream policy text changes.")
    if st.button("Refresh UNESCO/EU sources", use_container_width=True):
        updater = ReferenceTemplateUpdater(db)
        refresh_results = updater.refresh_bodies(["UNESCO", "EU"])
        changed = sum(1 for r in refresh_results if r.get("updated"))
        errors = [r for r in refresh_results if r.get("error")]
        st.success(
            f"Refresh complete: {changed} updated, "
            f"{len(refresh_results) - changed - len(errors)} unchanged, {len(errors)} errors."
        )
        if errors:
            st.warning("Some sources could not be checked. Verify source URLs/network and retry.")

    st.subheader("4 · Past Analyses")
    past = checker.get_analyses(document_id)
    if past:
        df = pd.DataFrame([{
            "Date": r["created_at"],
            "Body detected": r.get("body_detected", ""),
            "Category": r.get("category_detected", ""),
            "Reference": r.get("reference_name", ""),
            "Source": r.get("source_url", ""),
            "Score": f"{r['compliance_score']:.0%}" if r.get("compliance_score") is not None else "—",
            "Model": r.get("model_used", ""),
        } for r in past])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No analyses run yet for this document.")

    st.subheader("5 · Template Version History (Admin)")
    version_rows = db.fetchall(
        """
        SELECT
            cur.body,
            cur.name,
            cur.version AS current_version,
            prev.version AS superseded_version,
            cur.source_last_checked,
            cur.change_summary,
            cur.is_active
        FROM reference_templates cur
        LEFT JOIN reference_templates prev ON prev.id = cur.supersedes_template_id
        ORDER BY cur.body, cur.name, cur.id DESC
        """
    )
    if version_rows:
        history_df = pd.DataFrame([
            {
                "Body": r.get("body", ""),
                "Template": r.get("name", ""),
                "Current version": r.get("current_version", ""),
                "Supersedes": r.get("superseded_version") or "—",
                "Last checked": str(r.get("source_last_checked") or "—")[:19],
                "Last change summary": r.get("change_summary") or "—",
                "Status": "Active" if r.get("is_active") == 1 else "Historical",
            }
            for r in version_rows
        ])
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    else:
        st.info("No reference template history available yet.")

# ── Run analysis ──────────────────────────────────────────────────────────────
if run_btn:
    pages = db.fetchall(
        "SELECT content FROM document_pages "
        "WHERE document_id = ? ORDER BY page_number",
        (document_id,),
    )
    document_text = "\n".join(p["content"] for p in pages if p["content"])

    if not document_text.strip():
        st.error("No extracted text found for this document. Re-process it first.")
    else:
        started_at = time.time()
        with st.spinner(f"Sending to {provider.upper()} for semantic analysis…"):
            result = checker.analyse(
                document_id=document_id,
                document_text=document_text,
                reference_template=chosen_template,
            )
        elapsed = time.time() - started_at

        if result.get("error"):
            st.error(f"Analysis failed: {result['error']}")
            st.info(
                "This usually means provider availability, quota/rate-limit, or local Ollama service issues. "
                "Check health banner details, then retry."
            )
        else:
            # Score badge
            score = result.get("compliance_score") or 0.0
            colour = "green" if score >= 0.7 else "orange" if score >= 0.4 else "red"
            st.markdown(
                f"### Compliance Score: "
                f"<span style='color:{colour};font-size:2rem;font-weight:bold'>"
                f"{score:.0%}</span>",
                unsafe_allow_html=True,
            )

            ref = result.get("reference_template") or {}
            st.caption(
                f"Compared against: **{ref.get('name', 'N/A')}** "
                f"({ref.get('body', '')} · {ref.get('category', '')})"
            )
            if ref.get("source_url"):
                st.markdown(f"Source reference: [Open official framework]({ref.get('source_url')})")
            st.caption(f"Analysis time: {elapsed:.2f}s")

            st.markdown(f"**Summary:** {result.get('summary', '')}")
            st.markdown("---")

            tab_gaps, tab_present, tab_rec = st.tabs(
                ["⚠️ Gaps & Missing", "✅ Present Elements", "💡 Recommendations"]
            )

            with tab_gaps:
                gaps = result.get("gaps") or []
                missing = result.get("missing_elements") or []
                partial = result.get("partial_elements") or []
                if gaps:
                    st.markdown("**Gaps:**")
                    for g in gaps:
                        st.markdown(f"- {g}")
                if missing:
                    st.markdown("**Missing required elements:**")
                    for m in missing:
                        st.markdown(f"- ❌ {m}")
                if partial:
                    st.markdown("**Partially addressed:**")
                    for p in partial:
                        st.markdown(f"- 🔶 {p}")
                if not gaps and not missing and not partial:
                    st.success("No gaps detected!")

            with tab_present:
                present = result.get("present_elements") or []
                strengths = result.get("strengths") or []
                for item in present:
                    st.markdown(f"- ✅ {item}")
                if strengths:
                    st.markdown("**Strengths:**")
                    for s in strengths:
                        st.markdown(f"- 💪 {s}")

            with tab_rec:
                recs = result.get("recommendations") or []
                if recs:
                    for i, r in enumerate(recs, 1):
                        st.markdown(f"**{i}.** {r}")
                else:
                    st.info("No specific recommendations.")
