import sys
from pathlib import Path

# Ensure project root is on path when running: streamlit run streamlit_app/app.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from config import Config
from utils.logger import setup_logging
from database.db_manager import DatabaseManager
from geospatial.map_generator import MapGenerator
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.help_button import render_help_button

# ── Bootstrap ──────────────────────────────────────────────────────────────
Config.ensure_directories()
setup_logging(Config.LOG_FILE, Config.LOG_LEVEL)

st.set_page_config(
    page_title=Config.APP_NAME,
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar()

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
col1, col2 = st.columns([20, 1])
with col1:
    st.title("🌍 INCLUSCAPE")
with col2:
    render_help_button("🏠 Home")
st.subheader("Social Inclusion Document Analyzer")

st.markdown("""
Welcome to **INCLUSCAPE** — upload questionnaires, policies, instructions, forms,
reports, and monitoring documents, then let the system extract structured information, fill your report
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

# ── Scope map — locations from Policies documents ──────────────────────────
st.subheader("📍 Document Scope — Policy Locations")
st.caption(
    "Locations extracted from **Policies** documents. "
    "Full scope definition will be applied once document processing rules are configured."
)

policy_locations = db.fetchall(
    """
    SELECT l.place_name, l.latitude, l.longitude,
           l.location_type, l.context,
           d.title AS document_title
    FROM   locations l
    JOIN   documents d ON d.id = l.document_id
    WHERE  d.organisation_id = ?
      AND  d.document_type   = 'Policies'
      AND  l.geocoded        = 1
    """,
    (st.session_state.org_id,),
)

if policy_locations:
    try:
        from streamlit_folium import st_folium
        mapper = MapGenerator()
        m = mapper.build_map(policy_locations)
        if m:
            st_folium(m, use_container_width=True, height=420)
    except ImportError:
        st.warning("`streamlit-folium` not installed. Run `pip install streamlit-folium`.")
else:
    st.info(
        "No geocoded locations from **Policies** documents yet. "
        "Upload and process policy documents — locations will appear here automatically."
    )

st.markdown("---")
st.info("Use the **sidebar** to navigate between sections.")
