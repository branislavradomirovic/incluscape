import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
from database.db_manager import DatabaseManager
from template_matching.template_manager import TemplateManager

st.set_page_config(page_title="Reports — INCLUSCAPE", page_icon="📊", layout="wide")
st.title("📊 Report Generator")

db = DatabaseManager()
db.initialize()
tm = TemplateManager(db)
org_id = st.session_state.get("org_id", db.get_or_create_organisation("Default Organisation"))

# ── Select template ─────────────────────────────────────────────────────────
templates = tm.list_templates(org_id)
if not templates:
    st.warning("No templates found. Go to **Templates** to create one first.")
    st.stop()

template_options = {t["name"]: t["id"] for t in templates}
selected_tmpl_name = st.selectbox("Select report template", list(template_options.keys()))
template_id = template_options[selected_tmpl_name]

# ── Select source documents ─────────────────────────────────────────────────
docs = db.fetchall(
    "SELECT id, title, file_name, document_type FROM documents "
    "WHERE organisation_id = ? AND status = 'active' ORDER BY title",
    (org_id,),
)
if not docs:
    st.warning("No processed documents available. Upload documents first.")
    st.stop()

doc_options = {f"{d['title']} ({d['document_type']})": d["id"] for d in docs}
selected_doc_names = st.multiselect("Select source documents", list(doc_options.keys()))
selected_doc_ids = [doc_options[n] for n in selected_doc_names]

report_name = st.text_input("Report name", value=f"Report — {selected_tmpl_name}")

if st.button("🚀 Generate Report", type="primary") and selected_doc_ids:
    with st.spinner("Extracting data and filling template…"):
        # Gather full text from selected documents
        texts = []
        for doc_id in selected_doc_ids:
            pages = db.fetchall(
                "SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number",
                (doc_id,),
            )
            texts.append("\n\n".join(p["content"] for p in pages if p["content"]))

        # Fill template
        filled = tm.fill_template(template_id, texts)

        # Persist report
        report_id = db.insert("reports", {
            "organisation_id": org_id,
            "template_id": template_id,
            "name": report_name,
            "status": "complete",
        })
        for doc_id in selected_doc_ids:
            db.insert("report_sources", {"report_id": report_id, "document_id": doc_id})
        template = tm.get_template(template_id)
        for field in template["fields"]:
            fk = field["field_key"]
            if fk in filled:
                db.insert("report_values", {
                    "report_id": report_id,
                    "field_id": field["id"],
                    "raw_value": str(filled[fk]["value"] or ""),
                    "confidence": filled[fk]["confidence"],
                })

    st.success(f"✅ Report '{report_name}' generated (id={report_id})")

    # Display result
    st.markdown("---")
    st.subheader("Extracted Values")
    rows = []
    for fk, info in filled.items():
        rows.append({
            "Field": info["label"],
            "Type": info["type"],
            "Value": info["value"] or "—",
            "Confidence": f"{info['confidence']:.0%}",
            "Required": "✅" if info["required"] else "",
            "Context": (info["context"] or "")[:120],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Previous reports ────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Generated Reports")
reports = db.fetchall(
    "SELECT r.id, r.name, t.name AS template, r.status, r.created_at "
    "FROM reports r JOIN report_templates t ON t.id = r.template_id "
    "WHERE r.organisation_id = ? ORDER BY r.created_at DESC",
    (org_id,),
)
if reports:
    st.dataframe(pd.DataFrame(reports), use_container_width=True, hide_index=True)
else:
    st.info("No reports generated yet.")
