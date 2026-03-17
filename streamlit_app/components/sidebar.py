import streamlit as st


# ── Navigation definition ──────────────────────────────────────────────────
_NAV = [
    ("🏠", "Home",       "app.py"),
    ("📄", "Documents",  "pages/1_Documents.py"),
    ("📋", "Templates",  "pages/2_Templates.py"),
    ("📊", "Reports",    "pages/3_Reports.py"),
    ("🔍", "Changes",    "pages/4_Changes.py"),
    ("🗺️", "Map",        "pages/5_Map.py"),
    ("🔎", "Compliance", "pages/6_Compliance.py"),
    ("❓", "Help",       "pages/7_Help.py"),
]

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
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("## 🌍 INCLUSCAPE")
        st.markdown("*Social Inclusion Document Analyzer*")
        st.markdown("---")

        st.markdown("### Navigation")
        for icon, label, page in _NAV:
            st.page_link(page, label=f"{icon}  {label}")

        st.markdown("---")

        st.markdown("### 📚 Help & Resources")
        
        # Link to dedicated Help page
        col1, col2 = st.columns([2, 1])
        with col1:
            st.page_link("pages/7_Help.py", label="📖 Full Documentation", icon="❓")
        
        # Quick reference in expander
        with st.expander("⚡ Quick Guide", expanded=False):
            st.markdown("**Navigation quick tips:**")
            st.markdown("")
            for section, description in _HELP.items():
                st.markdown(f"**{section}** — {description}")
                st.markdown("")
