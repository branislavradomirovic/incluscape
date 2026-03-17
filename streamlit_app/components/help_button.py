import streamlit as st


def render_help_button(page_name: str) -> None:
    """
    Render a Help button in the page that links to the dedicated Help page,
    anchoring to the specific section for this page.
    
    Args:
        page_name: The emoji + name of the page (e.g., "📄 Documents", "🔎 Compliance")
    """
    st.markdown(
        """
        <style>
            section.main div[data-testid="stPageLink"] a[data-testid="stPageLink-NavLink"] {
                border: 1px solid rgba(32, 118, 106, 0.38);
                border-radius: 0.6rem;
                padding: 0.35rem 0.65rem;
                min-height: auto;
                justify-content: center;
                background: linear-gradient(135deg, rgba(232, 246, 242, 0.98), rgba(214, 235, 229, 0.98));
                font-weight: 600;
                color: rgb(20, 79, 71);
                box-shadow: 0 1px 3px rgba(32, 118, 106, 0.10);
            }
            section.main div[data-testid="stPageLink"] a[data-testid="stPageLink-NavLink"]:hover {
                border-color: rgba(32, 118, 106, 0.58);
                background: linear-gradient(135deg, rgba(220, 241, 235, 1), rgba(198, 227, 219, 1));
                box-shadow: 0 4px 10px rgba(32, 118, 106, 0.14);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)
    _, btn_col = st.columns([1, 1])
    with btn_col:
        st.page_link(
            "pages/7_Help.py",
            label="Help",
            icon="❓",
            help=f"Open full documentation for {page_name}",
        )
