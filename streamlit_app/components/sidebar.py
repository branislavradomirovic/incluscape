import base64
import streamlit as st
from pathlib import Path


# ── Navigation definition ──────────────────────────────────────────────────
_NAV = [
    ("🏠", "Home",       "app.py"),
    ("📄", "Documents",  "pages/1_Documents.py"),
    ("📋", "Templates",  "pages/2_Templates.py"),
    ("📊", "Reports",    "pages/3_Reports.py"),
    ("🔍", "Changes",    "pages/4_Changes.py"),
    ("🗺️", "Map",        "pages/5_Map.py"),
    ("🔎", "Compliance", "pages/6_Compliance.py"),
    ("🌐", "Sources",    "pages/8_Sources.py"),
    ("❓", "Help",       "pages/7_Help.py"),
]

_LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "SIPMT_LOGO.png"

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

            /* Nav links — button style */
            [data-testid="stPageLink"] {
                margin-top: 0.18rem;
                margin-bottom: 0.18rem;
            }
            [data-testid="stPageLink"] a {
                display: flex !important;
                align-items: center !important;
                width: 100% !important;
                padding: 0.42rem 0.75rem !important;
                border-radius: 0.4rem !important;
                border: 1px solid rgba(49, 51, 63, 0.18) !important;
                background: rgba(49, 51, 63, 0.04) !important;
                font-weight: 500 !important;
                text-decoration: none !important;
                transition: background 0.15s ease, border-color 0.15s ease;
            }
            [data-testid="stPageLink"] a:hover {
                background: rgba(49, 51, 63, 0.11) !important;
                border-color: rgba(49, 51, 63, 0.32) !important;
            }

            @media (max-width: 1400px) {
                .block-container h1 { font-size: 2.35rem; }
            }
            @media (max-width: 1100px) {
                .block-container h1 { font-size: 2.05rem; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        # Render logo + subtitle as inline HTML so margin-top pulls it
        # flush to the top regardless of Streamlit's container padding.
        logo_html = ""
        if _LOGO_PATH.exists():
            try:
                logo_b64 = base64.b64encode(_LOGO_PATH.read_bytes()).decode()
                logo_html = (
                    f'<img src="data:image/png;base64,{logo_b64}" '
                    'style="width:85%;max-width:220px;display:block;margin:0 auto;">'
                )
            except Exception:
                pass
        st.markdown(
            f"<div style='text-align:center;margin-top:-3.5rem;padding-bottom:0.5rem;'>"
            f"{logo_html}"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown("### Navigation")
        for icon, label, page in _NAV:
            st.page_link(page, label=f"{icon}  {label}")

        st.markdown("---")

        st.markdown("### 📚 Help & Resources")

        st.page_link("pages/7_Help.py", label="📖 Full Documentation", icon="❓")
        
        # Quick reference in expander
        with st.expander("⚡ Quick Guide", expanded=False):
            st.markdown("**Navigation quick tips:**")
            st.markdown("")
            for section, description in _HELP.items():
                st.markdown(f"**{section}** — {description}")
                st.markdown("")
