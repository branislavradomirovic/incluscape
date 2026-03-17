import sys
from pathlib import Path

# Ensure project root is on path when running: streamlit run streamlit_app/app.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from config import Config
from utils.logger import setup_logging
from database.db_manager import DatabaseManager

# ── Bootstrap ──────────────────────────────────────────────────────────────
Config.ensure_directories()
setup_logging(Config.LOG_FILE, Config.LOG_LEVEL)

st.set_page_config(
    page_title=Config.APP_NAME,
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialise database once per session ───────────────────────────────────
@st.cache_resource
def init_db():
    db = DatabaseManager()
    db.initialize()
    return db

db = init_db()

# ── Session state defaults ─────────────────────────────────────────────────
if "org_id" not in st.session_state:
    st.session_state.org_id = db.get_or_create_organisation("Default Organisation")
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ── Home page ──────────────────────────────────────────────────────────────
st.title("🌍 INCLUSCAPE")
st.subheader("Social Inclusion Document Analyzer")

st.markdown("""
Welcome to **INCLUSCAPE** — upload your policy documents, procedure manuals, forms,
and reports, then let the system extract structured information, fill your report
templates automatically, and visualise locations on an interactive map.

---
""")

col1, col2, col3, col4 = st.columns(4)

with col1:
    doc_count = db.fetchone("SELECT COUNT(*) AS n FROM documents") or {"n": 0}
    st.metric("📄 Documents", doc_count["n"])

with col2:
    tmpl_count = db.fetchone("SELECT COUNT(*) AS n FROM report_templates") or {"n": 0}
    st.metric("📋 Templates", tmpl_count["n"])

with col3:
    rpt_count = db.fetchone("SELECT COUNT(*) AS n FROM reports") or {"n": 0}
    st.metric("📊 Reports", rpt_count["n"])

with col4:
    chg_count = db.fetchone("SELECT COUNT(*) AS n FROM document_changes") or {"n": 0}
    st.metric("🔍 Changes detected", chg_count["n"])

st.markdown("---")
st.info("Use the **sidebar** to navigate between sections.")
