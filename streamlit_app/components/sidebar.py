import streamlit as st
from pathlib import Path


# ── Navigation definition ──────────────────────────────────────────────────
_NAV = [
    ("🏠", "Home",       "streamlit_app/app.py"),
    ("📄", "Documents",  "streamlit_app/pages/1_Documents.py"),
    ("📋", "Templates",  "streamlit_app/pages/2_Templates.py"),
    ("📊", "Reports",    "streamlit_app/pages/3_Reports.py"),
    ("🔍", "Changes",    "streamlit_app/pages/4_Changes.py"),
    ("🗺️", "Map",        "streamlit_app/pages/5_Map.py"),
    ("🔎", "Compliance", "streamlit_app/pages/6_Compliance.py"),
    ("🌐", "Sources",    "streamlit_app/pages/8_Sources.py"),
    ("❓", "Help",       "streamlit_app/pages/7_Help.py"),
]

_LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "INCLUSCAPE Logo.png"

# ── Help descriptions ──────────────────────────────────────────────────────
_HELP = {
    "🏠 Home": (
        "Overview dashboard with metrics and scope map. "
        "See total documents, templates, reports, and changes at a glance."
    ),
    "📄 Documents": (
        "Upload (PDF/DOCX/XLSX), categorize, and manage your source documents. "
        "Max 20 MB per file. System extracts text, tables, entities, and locations."
    ),
    "📋 Templates": (
        "Define reusable field templates for data extraction. "
        "Specify field names, types (text/number/date/boolean/list/location), and priorities."
    ),
    "📊 Reports": (
        "Generate structured data reports by matching templates to documents. "
        "System extracts values with confidence scores and saves results."
    ),
    "🔍 Changes": (
        "Track and visualize differences between document versions. "
        "See what was added, removed, or modified side-by-side."
    ),
    "🗺️ Map": (
        "Interactive geospatial visualization. "
        "Explore locations extracted from your documents on OpenStreetMap."
    ),
    "🔎 Compliance": (
        "Semantic analysis against international reference frameworks (UN, UNESCO, EU). "
        "Powered by Gemini or Ollama. Get compliance scores and recommendations."
    ),
    "🌐 Sources": (
        "Manage official external source URLs and refresh the reference repository. "
        "Python fetches source pages, then Ollama/Gemini enriches requirements locally."
    ),
    "❓ Help": (
        "Comprehensive documentation for all features. "
        "Detailed guides, tips, best practices, and configuration reference."
    ),
}


def render_sidebar() -> None:
    """Render custom sidebar navigation and help section on every page."""

    # Hide Streamlit's auto-generated page navigation
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"] { display: none; }
            .block-container { padding-top: 1.1rem; }
            [data-testid="stPageLink"] { margin-top: 0.08rem; margin-bottom: 0.08rem; }
            @media (max-width: 1400px) {
                .block-container h1 {
                    font-size: 2.35rem;
                }
            }
            @media (max-width: 1100px) {
                .block-container h1 {
                    font-size: 2.05rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        if _LOGO_PATH.exists():
            left, center, right = st.columns([1, 8, 1])
            with center:
                st.image(str(_LOGO_PATH), use_column_width=True)
            
        st.markdown("<div style='text-align: center; font-size: 0.95rem; margin-top: -1.4rem; margin-bottom: 0.2rem;'><i>Social Inclusion Document Analyzer</i></div>", unsafe_allow_html=True)

        st.markdown("### Navigation")
        for icon, label, page in _NAV:
            st.page_link(page, label=f"{icon}  {label}")

        st.markdown("---")

        st.markdown("### 📚 Help & Resources")
        
        # Link to dedicated Help page
        col1, col2 = st.columns([2, 1])
        with col1:
            st.page_link("streamlit_app/pages/7_Help.py", label="📖 Full Documentation", icon="❓")
        
        # Quick reference in expander
        with st.expander("⚡ Quick Guide", expanded=False):
            st.markdown("**Navigation quick tips:**")
            st.markdown("")
            for section, description in _HELP.items():
                st.markdown(f"**{section}** — {description}")
                st.markdown("")
