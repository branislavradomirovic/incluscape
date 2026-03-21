import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import tempfile
from datetime import datetime
import streamlit as st
import pandas as pd
from config import Config
from database.db_manager import DatabaseManager
from document_processing.pipeline import DocumentProcessingPipeline
from utils.file_handler import FileHandler
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.help_button import render_help_button

st.set_page_config(page_title="Documents — SIPMT", page_icon="📄", layout="wide")
render_sidebar()

col1, col2 = st.columns([14, 4])
with col1:
    st.title("📄 Document Management")
with col2:
    render_help_button("📄 Documents")

_MAX_BYTES = 20 * 1024 * 1024  # 20 MB hard limit per file

db = DatabaseManager()
db.initialize()
file_handler = FileHandler(Config.UPLOAD_FOLDER)
pipeline = DocumentProcessingPipeline(enable_ocr=Config.ENABLE_OCR)
org_id = st.session_state.get("org_id", db.get_or_create_organisation("Default Organisation"))


def _fmt_size(b):
    if not b:
        return "—"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b / 1024 / 1024:.1f} MB"


def _fmt_date(val):
    if not val:
        return "—"
    return str(val)[:10]


# ── Upload ──────────────────────────────────────────────────────────────────
with st.expander("📤 Upload New Documents", expanded=True):
    uploaded_files = st.file_uploader(
        "Choose files (PDF, DOCX, XLSX) — max 20 MB each",
        type=Config.ALLOWED_EXTENSIONS,
        accept_multiple_files=True,
    )
    doc_type = st.selectbox("Document category", Config.DOCUMENT_CATEGORIES)

    if uploaded_files and st.button("Process & Save", type="primary", use_container_width=True):
        progress = st.progress(0)
        for i, uf in enumerate(uploaded_files):

            # ── Size guard (before writing anything to disk) ──
            file_bytes = bytes(uf.getbuffer())
            size = len(file_bytes)
            if size > _MAX_BYTES:
                st.warning(
                    f"⚠️ **{uf.name}** is {size / 1024 / 1024:.1f} MB — "
                    "exceeds the 20 MB limit. Skipped."
                )
                progress.progress((i + 1) / len(uploaded_files))
                continue

            with st.spinner(f"Processing {uf.name}…"):
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=Path(uf.name).suffix,
                    dir=Config.TEMP_FOLDER,
                ) as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name

                try:
                    # ── Duplicate guard ──
                    file_hash = file_handler.hash_file(tmp_path)
                    from change_tracking.version_manager import VersionManager
                    if VersionManager(db).is_duplicate(file_hash, org_id):
                        st.warning(f"⚠️ **{uf.name}** already exists (same content). Skipped.")
                    else:
                        proc = pipeline.process(tmp_path)
                        result = proc["result"]

                        if Config.STORE_FILES_IN_DB:
                            stored_path = f"db://documents/{file_hash}/{Path(uf.name).name}"
                            file_size_value = size
                        else:
                            stored_path = file_handler.save(tmp_path, subfolder=str(org_id))
                            file_size_value = Path(stored_path).stat().st_size

                        doc_id = db.save_document({
                            "organisation_id": org_id,
                            "title": Path(uf.name).stem,
                            "document_type": doc_type,
                            "file_name": uf.name,
                            "file_path": stored_path,
                            "file_size": file_size_value,
                            "mime_type": uf.type or None,
                            "file_hash": proc["file_hash"],
                            "status": "active" if not proc["error"] else "error",
                            "processed_at": datetime.utcnow().isoformat(timespec="seconds"),
                        })
                        if Config.STORE_FILES_IN_DB:
                            db.save_document_blob(doc_id, file_bytes, uf.type or None)

                        if result:
                            for page in result.pages:
                                db.insert("document_pages", {
                                    "document_id": doc_id,
                                    "page_number": page.page_number,
                                    "content": page.content,
                                    "page_type": page.page_type,
                                    "word_count": page.word_count,
                                })
                            for ent in proc["entities"]:
                                ent["document_id"] = doc_id
                            db.save_entities(proc["entities"])
                            st.success(
                                f"✅ **{uf.name}** — {result.page_count} page(s), "
                                f"{len(proc['entities'])} entities extracted."
                            )
                        else:
                            st.error(f"❌ {uf.name}: {proc['error']}")
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            progress.progress((i + 1) / len(uploaded_files))
        st.rerun()

# ── Document Library ─────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📚 Document Library")

docs = db.fetchall(
    "SELECT id, title, document_type, file_name, file_path, file_size, status, created_at "
    "FROM documents WHERE organisation_id = ? AND status != 'archived' "
    "ORDER BY created_at DESC",
    (org_id,),
)

if not docs:
    st.info("No documents uploaded yet.")
    st.stop()

display_df = pd.DataFrame([{
    "Title":    d["title"],
    "Category": d["document_type"],
    "File":     d["file_name"],
    "Size":     _fmt_size(d["file_size"]),
    "Status":   d["status"].capitalize(),
    "Uploaded": _fmt_date(d["created_at"]),
} for d in docs])
st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── Select document for preview / delete ─────────────────────────────────────
st.markdown("---")
doc_options = {
    f"{d['title']}  [{d['document_type']}]  ·  {_fmt_date(d['created_at'])}": d["id"]
    for d in docs
}
selected_label = st.selectbox(
    "Select document to preview or delete",
    list(doc_options.keys()),
)
selected_id = doc_options[selected_label]
sel = next(d for d in docs if d["id"] == selected_id)

# ── Metadata row + delete button ──────────────────────────────────────────────
col_info, col_reprocess, col_btn = st.columns([5, 1, 1])
with col_info:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Category", sel["document_type"])
    m2.metric("Status",   sel["status"].capitalize())
    m3.metric("Size",     _fmt_size(sel["file_size"]))
    m4.metric("Uploaded", _fmt_date(sel["created_at"]))

with col_reprocess:
    st.markdown("<div style='padding-top:1.8rem'></div>", unsafe_allow_html=True)
    if st.button("🔄 Re-process", use_container_width=True, help="Re-extract text and entities from the stored file"):
        st.session_state["_reprocess"] = selected_id

with col_btn:
    st.markdown("<div style='padding-top:1.8rem'></div>", unsafe_allow_html=True)
    if st.button("🗑️ Delete", use_container_width=True):
        st.session_state["_confirm_delete"] = selected_id

# ── Re-process ────────────────────────────────────────────────────────────────
if st.session_state.get("_reprocess") == selected_id:
    import os
    file_path = sel["file_path"]
    temp_materialized_path = None
    if str(file_path).startswith("db://"):
        temp_materialized_path = db.materialize_document_for_processing(
            selected_id, sel["file_name"], Config.TEMP_FOLDER
        )
        if not temp_materialized_path:
            st.error("Stored file content is missing in database for this document.")
            st.session_state.pop("_reprocess", None)
            st.stop()
        file_path = temp_materialized_path
    elif not os.path.exists(file_path):
        # Fallback: try DB blob in case file path points to an old ephemeral location.
        temp_materialized_path = db.materialize_document_for_processing(
            selected_id, sel["file_name"], Config.TEMP_FOLDER
        )
        if temp_materialized_path:
            file_path = temp_materialized_path
        else:
            st.error(f"File not found on disk: `{file_path}`")
            st.session_state.pop("_reprocess", None)
            st.stop()

    try:
        with st.spinner(f"Re-processing {sel['file_name']}…"):
            proc = pipeline.process(file_path)
            result = proc["result"]
            if not result:
                st.error(f"Processing failed: {proc.get('error')}")
            else:
                db.execute("DELETE FROM document_pages WHERE document_id = ?", (selected_id,))
                db.execute("DELETE FROM extracted_entities WHERE document_id = ?", (selected_id,))
                for page in result.pages:
                    db.insert("document_pages", {
                        "document_id": selected_id,
                        "page_number": page.page_number,
                        "content":     page.content,
                        "page_type":   page.page_type,
                        "word_count":  page.word_count,
                    })
                entities = proc.get("entities", [])
                for ent in entities:
                    ent["document_id"] = selected_id
                db.save_entities(entities)
                st.success(
                    f"✅ Re-processed: {result.page_count} page(s), "
                    f"{len(entities)} entities extracted."
                )
    finally:
        if temp_materialized_path:
            Path(temp_materialized_path).unlink(missing_ok=True)
    st.session_state.pop("_reprocess", None)
    st.rerun()

# ── Delete confirmation ───────────────────────────────────────────────────────
if st.session_state.get("_confirm_delete") == selected_id:
    st.warning(
        f"⚠️ Delete **{sel['title']}** permanently? "
        "This will remove the file and all extracted data and cannot be undone."
    )
    c1, c2 = st.columns(2)
    if c1.button("✅ Yes, delete", type="primary", use_container_width=True):
        db.delete_document(selected_id)
        st.session_state.pop("_confirm_delete", None)
        st.success(f"'{sel['title']}' deleted.")
        st.rerun()
    if c2.button("❌ Cancel", use_container_width=True):
        st.session_state.pop("_confirm_delete", None)
        st.rerun()

# ── Text preview ──────────────────────────────────────────────────────────────
pages = db.fetchall(
    "SELECT page_number, content, word_count FROM document_pages "
    "WHERE document_id = ? ORDER BY page_number",
    (selected_id,),
)
entities = db.fetchall(
    "SELECT entity_type, entity_text, confidence FROM extracted_entities "
    "WHERE document_id = ? ORDER BY entity_type, confidence DESC",
    (selected_id,),
)

if pages:
    total_words = sum(p["word_count"] or 0 for p in pages)
    full_text = "\n\n".join(
        f"[Page {p['page_number']}]\n{p['content']}"
        for p in pages if p["content"]
    )
    with st.expander(
        f"📖 Document Text — {total_words:,} words across {len(pages)} page(s)",
        expanded=True,
    ):
        st.text_area(
            "content",
            value=full_text[:5000] + ("…" if len(full_text) > 5000 else ""),
            height=350,
            disabled=True,
            label_visibility="collapsed",
        )
else:
    st.info("No extracted text available for this document.")

if entities:
    with st.expander(f"🔍 Extracted Entities ({len(entities)})", expanded=False):
        st.dataframe(pd.DataFrame(entities), use_container_width=True, hide_index=True)
