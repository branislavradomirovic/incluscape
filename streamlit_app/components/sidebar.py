import streamlit as st
from pathlib import Path
from streamlit_app.i18n import enable_serbian_locale


enable_serbian_locale(st)


# ── Navigation definition ──────────────────────────────────────────────────
_NAV = [
    ("🏠", "Početna",       "app.py"),
    ("📄", "Dokumenti",     "pages/1_Documents.py"),
    ("📋", "Šabloni",       "pages/2_Templates.py"),
    ("📊", "Izveštaji",     "pages/3_Reports.py"),
    ("🔍", "Izmene",        "pages/4_Changes.py"),
    ("🗺️", "Mapa",          "pages/5_Map.py"),
    ("🔎", "Usklađenost",   "pages/6_Compliance.py"),
    ("🌐", "Izvori",        "pages/8_Sources.py"),
    ("⚖️", "HRBA uparivanje", "pages/9_HRBA_match.py"),
    ("🧾", "HRBA uvidi",      "pages/10_HRBA_Insights.py"),
    ("❓", "Pomoć",          "pages/7_Help.py"),
]

_LOGO_PATH = Path(__file__).resolve().parents[2] / "assets" / "SIPMT_LOGO.png"

# ── Help descriptions ──────────────────────────────────────────────────────
_HELP = {
    "🏠 Početna": (
        "Pregledna kontrolna tabla sa metrikama i mapom obuhvata. "
        "Na jednom mestu vidite broj dokumenata, šablona, izveštaja i izmena."
    ),
    "📄 Dokumenti": (
        "Otpremite (PDF/DOCX/XLSX), kategorizujte i upravljajte izvornim dokumentima. "
        "Maksimalna veličina je 20 MB po fajlu. Sistem izdvaja tekst, tabele, entitete i lokacije."
    ),
    "📋 Šabloni": (
        "Definišite višekratne šablone polja za izdvajanje podataka. "
        "Podesite nazive polja, tipove (tekst/broj/datum/boolean/lista/lokacija) i prioritete."
    ),
    "📊 Izveštaji": (
        "Generišite strukturisane izveštaje uparivanjem šablona sa dokumentima. "
        "Sistem izdvaja vrednosti, dodeljuje nivo pouzdanosti i čuva rezultate."
    ),
    "🔍 Izmene": (
        "Pratite i vizualizujte razlike između verzija dokumenata. "
        "Pregledajte šta je dodato, uklonjeno ili izmenjeno, uporedo."
    ),
    "🗺️ Mapa": (
        "Interaktivna geoprostorna vizualizacija. "
        "Istražite lokacije izdvojene iz dokumenata na OpenStreetMap mapi."
    ),
    "🔎 Usklađenost": (
        "Semantička analiza prema međunarodnim referentnim okvirima (UN, UNESCO, EU). "
        "Pokreću je Gemini ili Ollama modeli. Dobijate ocenu usklađenosti i preporuke."
    ),
    "🌐 Izvori": (
        "Upravljajte zvaničnim spoljnim URL izvorima i osvežavajte referentni repozitorijum. "
        "Python preuzima stranice izvora, a zatim Ollama/Gemini lokalno obogaćuje zahteve."
    ),
    "❓ Pomoć": (
        "Kompletna dokumentacija svih funkcionalnosti. "
        "Detaljna uputstva, saveti, najbolje prakse i referenca konfiguracije."
    ),
}

_DISCLAIMER_TEXT = (
    "Odricanje od odgovornosti: Ova aplikacija, koju je razvila kompanija Opus Labs d.o.o. Novi Sad, "
    "koristi generativnu veštačku inteligenciju (Ollama) radi predloga i analize podataka. Prikazani uvidi "
    "služe isključivo u informativne svrhe i ne predstavljaju profesionalni, pravni, bezbednosni ili drugi "
    "stručni savet. Bez garancije: izlazi AI sistema su probabilistički i mogu biti netačni ili pristrasni. "
    "Ljudski nadzor: alat je pomoćno sredstvo i ne zamenjuje ljudsku procenu i odgovornost. Odgovornost: "
    "korišćenje aplikacije je na sopstveni rizik korisnika. Opus Labs d.o.o. ne snosi odgovornost za "
    "operativne greške ili finansijske gubitke nastale njenom upotrebom."
)


def render_sidebar() -> None:
    """Render custom sidebar navigation and help section on every page."""

    # Hide Streamlit's auto-generated page navigation
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"] { display: none; }
            .block-container { padding-top: 2.5rem; }
            [data-testid="stSidebar"] .block-container { padding-top: 0.05rem !important; }

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
        # Render the logo with Streamlit's native image widget for better
        # cross-version reliability inside the sidebar.
        st.markdown("<div style='margin-top:-0.95rem;'></div>", unsafe_allow_html=True)
        if _LOGO_PATH.exists():
            st.image(str(_LOGO_PATH), use_container_width=True)

        st.markdown("### Navigacija")
        for icon, label, page in _NAV:
            st.page_link(page, label=f"{icon}  {label}")

        st.markdown("---")

        st.markdown("### 📚 Pomoć i resursi")

        st.page_link("pages/7_Help.py", label="📖 Dokumentacija", icon="❓")
        
        # Quick reference in expander
        with st.expander("⚡ Brzi vodič", expanded=False):
            st.markdown("**Brzi saveti za navigaciju:**")
            st.markdown("")
            for section, description in _HELP.items():
                st.markdown(f"**{section}** — {description}")
                st.markdown("")


def render_page_disclaimer() -> None:
    st.markdown("---")
    st.markdown(
        f"""
        <div style="
            margin-top: 0.25rem;
            padding: 0.85rem 1rem;
            border: 1px solid rgba(100, 116, 139, 0.22);
            border-radius: 0.5rem;
            background: rgba(248, 250, 252, 0.96);
            color: rgb(71, 85, 105);
            font-size: 0.84rem;
            line-height: 1.55;
        ">
            <strong>Odricanje od odgovornosti</strong><br>
            {_DISCLAIMER_TEXT}
        </div>
        """,
        unsafe_allow_html=True,
    )
