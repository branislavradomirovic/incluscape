import json
import streamlit as st
from config import Config
from database.db_manager import DatabaseManager
from document_processing.processors.hrba_matcher import HRBAMatcher as SpaCyHRBAMatcher
from template_matching.hrba_matcher import HRBAMatcherLLM
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.help_button import render_help_button

st.set_page_config(page_title="HRBA — SIPMT", page_icon="⚖️", layout="wide")
render_sidebar()

col1, col2 = st.columns([14, 4])
with col1:
    st.title("⚖️ HRBA — AAAQ Matcher")
with col2:
    render_help_button("⚖️ HRBA")

st.markdown(
    """
    Use the HRBA matcher to scan text for AAAQ indicators (Availability, Accessibility,
    Acceptability, Quality). Select documents from the database for batch analysis or paste text below.
    """
)

db = DatabaseManager()

# Choose matcher
mode = st.radio("Matcher", ("spaCy (fast)", "Ollama LLM (JSON)"), index=0)
use_llm = mode.startswith("Ollama")

spaCy_matcher = SpaCyHRBAMatcher()
llm_matcher = HRBAMatcherLLM()

# ------------------------------------------------------------------
# Document selector + batch analysis (moved before pasted-text per request)
# ------------------------------------------------------------------
st.markdown("### Analyze documents from database")
org_id = st.session_state.get("org_id") if "org_id" in st.session_state else db.get_or_create_organisation("Default Organisation")
docs = db.fetchall(
    "SELECT id, title, created_at FROM documents WHERE organisation_id = ? AND status = 'active' ORDER BY created_at DESC",
    (org_id,),
)

doc_options = [f"{d['id']}: {d['title']}" for d in docs]
selected = st.multiselect("Select documents to analyze", options=doc_options, default=[])

col1, col2 = st.columns(2)
with col1:
    if st.button("Analyze selected"):
        if not selected:
            st.warning("Select one or more documents to analyze.")
        else:
            results = {}
            for sel in selected:
                doc_id = int(sel.split(":", 1)[0])
                pages = db.fetchall("SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number", (doc_id,))
                texts = [p.get("content") or "" for p in pages]
                with st.spinner(f"Analyzing document {doc_id}..."):
                    if use_llm:
                        analysis = llm_matcher.get_hrba_summary(texts)
                    else:
                        analysis = []
                        for t in texts:
                            insights = spaCy_matcher.extract_hrba_insights(t)
                            analysis.extend([{"category": i["category"], "score": i["score"], "text": i["text"]} for i in insights])
                results[doc_id] = analysis

            for doc_id, analysis in results.items():
                st.subheader(f"Document {doc_id} — {len(analysis)} matches")
                st.write(analysis)

with col2:
    if st.button("Analyze all documents"):
        if not docs:
            st.info("No documents available for this organisation.")
        else:
            aggregate = {}
            for d in docs:
                doc_id = d["id"] if isinstance(d, (list, tuple)) else d["id"]
                pages = db.fetchall("SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number", (doc_id,))
                texts = [p.get("content") or "" for p in pages]
                with st.spinner(f"Analyzing document {doc_id}..."):
                    if use_llm:
                        analysis = llm_matcher.get_hrba_summary(texts)
                    else:
                        analysis = []
                        for t in texts:
                            insights = spaCy_matcher.extract_hrba_insights(t)
                            analysis.extend([{"category": i["category"], "score": i["score"], "text": i["text"]} for i in insights])
                aggregate[doc_id] = analysis

            st.write("Batch analysis complete")
            st.write(aggregate)

# Option to save results to DB
st.markdown("---")
if st.button("Save last analysis to DB"):
    try:
        # Attempt to find last results in page state by checking `results` or `aggregate` variables
        to_save = locals().get("results") or locals().get("aggregate")
        if not to_save:
            st.warning("No analysis results found to save. Run an analysis first.")
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
            st.success(f"Saved HRBA analyses for {saved_count} documents into semantic_analyses table.")
    except Exception as e:
        st.error(f"Saving to DB failed: {e}")

st.markdown("---")
st.caption(f"spaCy model: {Config.SPACY_MODEL} — Ollama base: {Config.OLLAMA_BASE_URL}")
