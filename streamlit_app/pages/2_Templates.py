import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
import streamlit as st
from database.db_manager import DatabaseManager
from template_matching.template_manager import TemplateManager
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.sidebar import render_page_disclaimer, render_sidebar
from streamlit_app.components.help_button import render_help_button

st.set_page_config(page_title="Templates — SIPMT", page_icon="📋", layout="wide")
render_sidebar()

col1, col2 = st.columns([14, 4])
with col1:
    st.title("📋 Template Manager")
with col2:
    render_help_button("📋 Templates")

db = DatabaseManager()
db.initialize()
tm = TemplateManager(db)
org_id = st.session_state.get("org_id", db.get_or_create_organisation("Default Organisation"))

tab_list, tab_new = st.tabs(["Existing Templates", "Create New Template"])

# ── List templates ──────────────────────────────────────────────────────────
with tab_list:
    templates = tm.list_templates(org_id)
    if not templates:
        st.info("No templates yet. Create one in the 'Create New Template' tab.")
    else:
        for tmpl in templates:
            with st.expander(f"📋 {tmpl['name']} (id={tmpl['id']})"):
                st.caption(tmpl.get("description", ""))
                full = tm.get_template(tmpl["id"])
                if full and full.get("fields"):
                    import pandas as pd
                    st.dataframe(
                        pd.DataFrame(full["fields"])[
                            ["field_key", "field_label", "field_type", "is_required", "extraction_hint"]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

# ── Create template ─────────────────────────────────────────────────────────
with tab_new:
    st.subheader("Define a New Report Template")
    name = st.text_input("Template name *")
    description = st.text_area("Description", height=70)

    st.markdown("**Fields** — add one row per field")
    num_fields = st.number_input("Number of fields", min_value=1, max_value=30, value=3)

    fields = []
    for i in range(int(num_fields)):
        st.markdown(f"**Field {i+1}**")
        c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 3])
        key = c1.text_input("Key", key=f"key_{i}", placeholder="e.g. target_group")
        label = c2.text_input("Label", key=f"label_{i}", placeholder="e.g. Target Group")
        ftype = c3.selectbox("Type", ["text", "number", "date", "boolean", "list", "location"], key=f"type_{i}")
        required = c4.checkbox("Required", key=f"req_{i}")
        hint = c5.text_input("Extraction hint", key=f"hint_{i}", placeholder="keywords from source docs")
        if key:
            fields.append({"key": key, "label": label or key, "type": ftype,
                           "required": required, "hint": hint})

    if st.button("💾 Save Template", type="primary"):
        if not name:
            st.error("Template name is required.")
        elif not fields:
            st.error("Add at least one field.")
        else:
            tid = tm.create_template(name, fields, org_id, description)
            st.success(f"✅ Template '{name}' created (id={tid})")
            st.rerun()

render_page_disclaimer()
