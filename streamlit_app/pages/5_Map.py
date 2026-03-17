import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from database.db_manager import DatabaseManager
from geospatial.location_extractor import LocationExtractor
from geospatial.geocoder import Geocoder
from geospatial.map_generator import MapGenerator
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.help_button import render_help_button

st.set_page_config(page_title="Map — INCLUSCAPE", page_icon="🗺️", layout="wide")
render_sidebar()

col1, col2 = st.columns([14, 4])
with col1:
    st.title("🗺️ Geospatial View")
with col2:
    render_help_button("🗺️ Map")

db = DatabaseManager()
db.initialize()
org_id = st.session_state.get("org_id", db.get_or_create_organisation("Default Organisation"))

le = LocationExtractor()
geocoder = Geocoder()
mapper = MapGenerator()

# ── Extract locations from selected documents ───────────────────────────────
docs = db.fetchall(
    "SELECT id, title FROM documents WHERE organisation_id = ? AND status = 'active'",
    (org_id,),
)
doc_labels = {f"{d['title']} (id={d['id']})": d["id"] for d in docs}

selected = st.multiselect(
    "Select documents to extract locations from",
    list(doc_labels.keys()),
    default=list(doc_labels.keys())[:5],
)

if st.button("🔍 Extract & Map Locations", type="primary") and selected:
    all_locations: list[dict] = []
    for label in selected:
        doc_id = doc_labels[label]
        # Check for already-saved locations
        saved = db.fetchall(
            "SELECT * FROM locations WHERE document_id = ?", (doc_id,)
        )
        if saved:
            all_locations.extend(saved)
        else:
            pages = db.fetchall(
                "SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number",
                (doc_id,),
            )
            text = "\n".join(p["content"] for p in pages if p["content"])
            locs = le.extract_from_text(text, document_id=doc_id)
            locs = geocoder.geocode_batch(locs)
            for loc in locs:
                loc_id = db.insert("locations", loc)
                loc["id"] = loc_id
            all_locations.extend(locs)

    st.info(f"Found **{len(all_locations)}** location mentions.")

    geocoded = [l for l in all_locations if l.get("latitude")]
    if geocoded:
        try:
            from streamlit_folium import st_folium
            m = mapper.build_map(geocoded)
            st_folium(m, use_container_width=True, height=550)
        except ImportError:
            st.warning(
                "`streamlit-folium` not installed. Run `pip install streamlit-folium`."
            )
    else:
        st.warning(
            "No geocoded locations to display. "
            "Enable `ENABLE_GEOCODING=True` in .env and re-run."
        )

    # Table view
    st.subheader("Location list")
    import pandas as pd
    st.dataframe(
        pd.DataFrame(all_locations)[
            ["place_name", "location_type", "geocoded", "latitude", "longitude", "context"]
        ],
        use_container_width=True,
        hide_index=True,
    )
