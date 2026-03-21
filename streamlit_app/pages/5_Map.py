import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st
from config import Config
from database.db_manager import DatabaseManager
from geospatial.location_extractor import LocationExtractor
from geospatial.geocoder import Geocoder
from geospatial.map_generator import MapGenerator
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.help_button import render_help_button

st.set_page_config(page_title="Map — SIPMT", page_icon="🗺️", layout="wide")
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

_LOCATION_TABLE_COLUMNS = [
    "place_name",
    "location_type",
    "geocoded",
    "latitude",
    "longitude",
    "context",
]


if "map_last_locations" not in st.session_state:
    st.session_state["map_last_locations"] = []
if "map_last_extraction_stats" not in st.session_state:
    st.session_state["map_last_extraction_stats"] = []
if "map_last_selected_ids" not in st.session_state:
    st.session_state["map_last_selected_ids"] = []
if "map_last_signature" not in st.session_state:
    st.session_state["map_last_signature"] = None


def _build_locations_table_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "place_name": row.get("place_name", ""),
            "location_type": row.get("location_type", "general"),
            "geocoded": row.get("geocoded", 0),
            "latitude": row.get("latitude"),
            "longitude": row.get("longitude"),
            "context": row.get("context", ""),
        }
        for row in rows
    ]


def _get_document_text(document_id: int) -> str:
    pages = db.fetchall(
        "SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number",
        (document_id,),
    )
    return "\n".join(p["content"] for p in pages if p.get("content"))


def _extract_locations_for_document(document_id: int, force_reextract: bool) -> tuple[list[dict], dict]:
    if force_reextract:
        db.execute("DELETE FROM locations WHERE document_id = ?", (document_id,))
        saved = []
    else:
        saved = db.fetchall("SELECT * FROM locations WHERE document_id = ?", (document_id,))

    if saved:
        if Config.ENABLE_GEOCODING:
            for row in saved:
                if row.get("latitude") is None or row.get("longitude") is None or not row.get("geocoded"):
                    lat, lon = geocoder.geocode(row.get("place_name", ""))
                    if lat is None:
                        continue
                    row["latitude"] = lat
                    row["longitude"] = lon
                    row["geocoded"] = 1
                    if row.get("id"):
                        db.update(
                            "locations",
                            {"latitude": lat, "longitude": lon, "geocoded": 1},
                            "id = ?",
                            (row["id"],),
                        )
        return saved, {
            "document_id": document_id,
            "source": "saved",
            "text_chars": None,
            "locations": len(saved),
            "geocoded": sum(1 for row in saved if row.get("latitude") is not None),
        }

    text = _get_document_text(document_id)
    locations = le.extract_from_text(text, document_id=document_id)
    locations = geocoder.geocode_batch(locations)
    for loc in locations:
        loc_id = db.insert("locations", loc)
        loc["id"] = loc_id

    return locations, {
        "document_id": document_id,
        "source": "fresh" if force_reextract else "new",
        "text_chars": len(text),
        "locations": len(locations),
        "geocoded": sum(1 for row in locations if row.get("latitude") is not None),
    }


def _build_doc_stats_rows(extraction_stats: list[dict], documents_by_id: dict[int, dict]) -> list[dict]:
    rows = []
    for stat in extraction_stats:
        doc = documents_by_id.get(stat["document_id"], {})
        rows.append({
            "Document ID": stat["document_id"],
            "Document": doc.get("title", f"Document {stat['document_id']}"),
            "Type": doc.get("document_type", ""),
            "Source": stat.get("source", ""),
            "Text chars": stat.get("text_chars") if stat.get("text_chars") is not None else "-",
            "Locations": stat.get("locations", 0),
            "Geocoded": stat.get("geocoded", 0),
        })
    return rows


def _render_diagnostics(documents: list[dict], selected_ids: list[int]) -> None:
    diagnostics = le.get_diagnostics()
    saved_count_row = db.fetchone("SELECT COUNT(*) AS count FROM locations") or {"count": 0}
    selected_types = sorted({
        doc.get("document_type", "")
        for doc in documents
        if doc.get("id") in selected_ids
    })

    metric_cols = st.columns(4)
    metric_cols[0].metric("Active docs", len(documents))
    metric_cols[1].metric("Selected docs", len(selected_ids))
    metric_cols[2].metric("Saved locations", int(saved_count_row.get("count", 0)))
    metric_cols[3].metric("Geocoding", "On" if Config.ENABLE_GEOCODING else "Off")

    if not diagnostics["spacy_ready"]:
        st.warning(
            f"spaCy location model unavailable: {diagnostics['spacy_model']} | {diagnostics['spacy_error'][:220]}"
        )
    else:
        st.success(f"spaCy location model ready: {diagnostics['spacy_model']}")

    with st.expander("Extraction diagnostics", expanded=False):
        st.dataframe(
            pd.DataFrame([
                {"Check": "spaCy model", "Value": diagnostics["spacy_model"]},
                {"Check": "spaCy ready", "Value": "Yes" if diagnostics["spacy_ready"] else "No"},
                {"Check": "Rule patterns", "Value": diagnostics["rule_patterns"]},
                {"Check": "Known places", "Value": diagnostics["known_places"]},
                {"Check": "Selected types", "Value": ", ".join(selected_types) if selected_types else "-"},
            ]),
            use_container_width=True,
            hide_index=True,
        )


def _run_extraction(selected_ids: list[int], force_reextract: bool) -> None:
    all_locations: list[dict] = []
    extraction_stats: list[dict] = []
    for doc_id in selected_ids:
        locs, stats = _extract_locations_for_document(doc_id, force_reextract=force_reextract)
        extraction_stats.append(stats)
        all_locations.extend(locs)

    st.session_state["map_last_locations"] = all_locations
    st.session_state["map_last_extraction_stats"] = extraction_stats
    st.session_state["map_last_selected_ids"] = selected_ids
    st.session_state["map_last_signature"] = (tuple(sorted(selected_ids)), bool(force_reextract))

# ── Extract locations from selected documents ───────────────────────────────
docs = db.fetchall(
    "SELECT id, title, document_type FROM documents WHERE organisation_id = ? AND status = 'active' ORDER BY title",
    (org_id,),
)
docs_by_id = {d["id"]: d for d in docs}
doc_labels = {f"{d['title']} (id={d['id']})": d["id"] for d in docs}

selected = st.multiselect(
    "Select documents to extract locations from",
    list(doc_labels.keys()),
    default=list(doc_labels.keys())[:5],
    key="map_selected_documents",
)
selected_ids = [doc_labels[label] for label in selected]
force_reextract = st.checkbox(
    "Force re-extract selected documents",
    value=False,
    help="Delete saved location rows for the selected documents and rebuild them from document text.",
    key="map_force_reextract",
)

_render_diagnostics(docs, selected_ids)

if st.button("🔍 Extract & Map Locations", type="primary") and selected:
    with st.spinner("Extracting and geocoding locations..."):
        _run_extraction(selected_ids, force_reextract=force_reextract)

last_locations = st.session_state.get("map_last_locations") or []
last_stats = st.session_state.get("map_last_extraction_stats") or []
last_selected_ids = st.session_state.get("map_last_selected_ids") or []

if last_locations:
    st.info(f"Found **{len(last_locations)}** location mentions.")

    summary_rows = _build_doc_stats_rows(last_stats, docs_by_id)
    summary_df = pd.DataFrame(summary_rows)

    selected_summary_doc_id = st.session_state.get("map_selected_summary_doc_id")
    if selected_summary_doc_id is None and not summary_df.empty:
        selected_summary_doc_id = int(summary_df.iloc[0]["Document ID"])

    st.subheader("Extraction summary")
    selector_df = summary_df.copy()
    selector_df["Show on map"] = selector_df["Document ID"].astype(int) == int(selected_summary_doc_id)
    edited = st.data_editor(
        selector_df[["Show on map", "Document", "Type", "Source", "Text chars", "Locations", "Geocoded", "Document ID"]],
        use_container_width=True,
        hide_index=True,
        disabled=["Document", "Type", "Source", "Text chars", "Locations", "Geocoded", "Document ID"],
        column_config={
            "Show on map": st.column_config.CheckboxColumn(
                "Show on map",
                help="Tick one row to filter map and location list to that document.",
                default=False,
            ),
            "Document ID": None,
        },
        key="map_extraction_summary_editor",
    )
    selected_rows = edited[edited["Show on map"]]
    if not selected_rows.empty:
        selected_summary_doc_id = int(selected_rows.iloc[0]["Document ID"])
    elif not summary_df.empty:
        selected_summary_doc_id = int(summary_df.iloc[0]["Document ID"])

    st.session_state["map_selected_summary_doc_id"] = selected_summary_doc_id

    display_locations = [
        loc for loc in last_locations
        if int(loc.get("document_id") or -1) == int(selected_summary_doc_id)
    ]

    geocoded = [l for l in display_locations if l.get("latitude")]
    if geocoded:
        try:
            from streamlit_folium import st_folium
            m = mapper.build_map(geocoded)
            st_folium(
                m,
                use_container_width=True,
                height=550,
                key=f"map_view_{'_'.join(str(i) for i in last_selected_ids) or 'default'}",
            )
        except ImportError:
            st.warning(
                "`streamlit-folium` not installed. Run `pip install streamlit-folium`."
            )
    else:
        st.warning(
            "No geocoded locations to display. "
            "Enable `ENABLE_GEOCODING=true` in Streamlit Cloud Secrets (or .env locally) and re-run."
        )

    # Table view
    st.subheader("Location list")
    table_rows = _build_locations_table_rows(display_locations)
    st.dataframe(
        pd.DataFrame(table_rows, columns=_LOCATION_TABLE_COLUMNS),
        use_container_width=True,
        hide_index=True,
    )
elif selected:
    st.info("Click **Extract & Map Locations** to build or refresh the map for selected documents.")
