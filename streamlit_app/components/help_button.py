import streamlit as st


def render_help_button(page_name: str) -> None:
    """
    Render a Help button in the page that links to the dedicated Help page,
    anchoring to the specific section for this page.
    
    Args:
        page_name: The emoji + name of the page (e.g., "📄 Documents", "🔎 Compliance")
    """
    col1, col2, col3 = st.columns([1, 18, 1])
    with col3:
        st.page_link(
            "pages/7_Help.py",
            label="❓",
            help=f"Open full documentation for {page_name}"
        )
