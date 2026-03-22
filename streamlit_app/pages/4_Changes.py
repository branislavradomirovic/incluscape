import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager
from change_tracking.change_detector import ChangeDetector
from change_tracking.version_manager import VersionManager
from streamlit_app.components.sidebar import render_page_disclaimer, render_sidebar
from streamlit_app.components.help_button import render_help_button

st.set_page_config(page_title="Change Monitor — SIPMT", page_icon="🔍", layout="wide")
render_sidebar()

col1, col2 = st.columns([14, 4])
with col1:
    st.title("🔍 Change Monitor")
with col2:
    render_help_button("🔍 Changes")

db = DatabaseManager()
db.initialize()
cd = ChangeDetector(db)
vm = VersionManager(db)
org_id = st.session_state.get("org_id", db.get_or_create_organisation("Default Organisation"))

# ── List all detected changes ───────────────────────────────────────────────
st.subheader("Recent Changes")
changes = db.fetchall(
    "SELECT dc.id, d.title AS document, dc.change_type, dc.impact_level, "
    "       dc.diff_summary, dc.detected_at "
    "FROM document_changes dc "
    "JOIN documents d ON d.id = dc.document_id "
    "WHERE d.organisation_id = ? "
    "ORDER BY dc.detected_at DESC LIMIT 100",
    (org_id,),
)
if not changes:
    st.info("No changes detected yet. Upload a new version of an existing document to see changes.")
else:
    IMPACT_COLOUR = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
    rows = []
    for c in changes:
        icon = IMPACT_COLOUR.get(c["impact_level"], "⚪")
        summary = {}
        if c["diff_summary"]:
            try:
                summary = json.loads(c["diff_summary"])
            except Exception:
                pass
        rows.append({
            "Document": c["document"],
            "Type": c["change_type"],
            "Impact": f"{icon} {c['impact_level']}",
            "Change %": summary.get("change_percentage", "—"),
            "Added lines": summary.get("added_lines", "—"),
            "Removed lines": summary.get("removed_lines", "—"),
            "Detected at": c["detected_at"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Compare two documents ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("Compare Two Document Versions")

docs = db.fetchall(
    "SELECT id, title, version, created_at FROM documents "
    "WHERE organisation_id = ? ORDER BY title, version",
    (org_id,),
)
if len(docs) < 2:
    st.info("Upload at least two documents to compare.")
else:
    doc_labels = {f"{d['title']} v{d['version']} (id={d['id']})": d["id"] for d in docs}
    col1, col2 = st.columns(2)
    old_label = col1.selectbox("Old version", list(doc_labels.keys()), key="old_doc")
    new_label = col2.selectbox("New version", list(doc_labels.keys()), key="new_doc")
    old_id = doc_labels[old_label]
    new_id = doc_labels[new_label]

    if st.button("Compare", type="primary"):
        def get_text(doc_id):
            pages = db.fetchall(
                "SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number",
                (doc_id,),
            )
            return "\n\n".join(p["content"] for p in pages if p["content"])

        old_text = get_text(old_id)
        new_text = get_text(new_id)
        if not old_text or not new_text:
            st.error("One or both documents have no extracted text.")
        else:
            result = cd.compare(old_text, new_text)
            st.metric("Change percentage", f"{result['change_percentage']}%")
            c1, c2, c3 = st.columns(3)
            c1.metric("Added lines", result["added_lines"])
            c2.metric("Removed lines", result["removed_lines"])
            c3.metric("Impact level", result["impact_level"].upper())
            with st.expander("Diff snippet"):
                st.code(result["diff_snippet"], language="diff")

render_page_disclaimer()
