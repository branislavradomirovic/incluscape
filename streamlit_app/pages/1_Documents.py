import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import tempfile
import streamlit as st
from config import Config
from database.db_manager import DatabaseManager
from document_processing.pipeline import DocumentProcessingPipeline
from utils.file_handler import FileHandler

st.set_page_config(page_title="Documents — INCLUSCAPE", page_icon="📄", layout="wide")
st.title("📄 Document Management")

db = DatabaseManager()
db.initialize()
file_handler = FileHandler(Config.UPLOAD_FOLDER)
pipeline = DocumentProcessingPipeline(enable_ocr=Config.ENABLE_OCR)
org_id = st.session_state.get("org_id", db.get_or_create_organisation("Default Organisation"))

# ── Upload ──────────────────────────────────────────────────────────────────
st.subheader("Upload Documents")
uploaded_files = st.file_uploader(
    "Choose files (PDF, DOCX, XLSX)",
    type=Config.ALLOWED_EXTENSIONS,
    accept_multiple_files=True,
)
doc_type = st.selectbox(
    "Document type",
    ["policy", "procedure", "form", "report", "other"],
)

if uploaded_files and st.button("Process & Save", type="primary"):
    progress = st.progress(0)
    for i, uf in enumerate(uploaded_files):
        with st.spinner(f"Processing {uf.name}…"):
            # Save to temp location first
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=Path(uf.name).suffix,
                dir=Config.TEMP_FOLDER
            ) as tmp:
                tmp.write(uf.getbuffer())
                tmp_path = tmp.name

            # Check for duplicates
            file_hash = file_handler.hash_file(tmp_path)
            from change_tracking.version_manager import VersionManager
            vm = VersionManager(db)
            is_dup = vm.is_duplicate(file_hash, org_id)

            if is_dup:
                st.warning(f"⚠️ {uf.name} already exists (same content). Skipped.")
                Path(tmp_path).unlink(missing_ok=True)
            else:
                # Move to uploads
                stored_path = file_handler.save(tmp_path, subfolder=str(org_id))
                Path(tmp_path).unlink(missing_ok=True)

                # Run pipeline
                proc = pipeline.process(stored_path)
                result = proc["result"]

                # Save document record
                doc_id = db.save_document({
                    "organisation_id": org_id,
                    "title": Path(uf.name).stem,
                    "document_type": doc_type,
                    "file_name": uf.name,
                    "file_path": stored_path,
                    "file_size": Path(stored_path).stat().st_size,
                    "file_hash": proc["file_hash"],
                    "status": "active" if not proc["error"] else "error",
                    "processed_at": "CURRENT_TIMESTAMP",
                })

                # Save pages
                if result:
                    for page in result.pages:
                        db.insert("document_pages", {
                            "document_id": doc_id,
                            "page_number": page.page_number,
                            "content": page.content,
                            "page_type": page.page_type,
                            "word_count": page.word_count,
                        })
                    # Save entities
                    for ent in proc["entities"]:
                        ent["document_id"] = doc_id
                    db.save_entities(proc["entities"])

                    st.success(
                        f"✅ {uf.name} — {result.page_count} page(s), "
                        f"{len(proc['entities'])} entities extracted."
                    )
                else:
                    st.error(f"❌ {uf.name}: {proc['error']}")

        progress.progress((i + 1) / len(uploaded_files))

# ── Document list ───────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Document Library")
docs = db.fetchall(
    "SELECT id, title, document_type, file_name, status, created_at "
    "FROM documents WHERE organisation_id = ? ORDER BY created_at DESC",
    (org_id,),
)
if docs:
    import pandas as pd
    st.dataframe(pd.DataFrame(docs), use_container_width=True, hide_index=True)
else:
    st.info("No documents uploaded yet.")
