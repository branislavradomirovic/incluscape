import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd
from config import Config
from database.db_manager import DatabaseManager
from geospatial.geocoder import Geocoder
from geospatial.location_extractor import LocationExtractor
from geospatial.map_generator import MapGenerator
from template_matching.template_manager import TemplateManager
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.help_button import render_help_button

st.set_page_config(page_title="Reports — SIPMT", page_icon="📊", layout="wide")
render_sidebar()

col1, col2 = st.columns([14, 4])
with col1:
    st.title("📊 Report Generator")
with col2:
    render_help_button("📊 Reports")

db = DatabaseManager()
db.initialize()
tm = TemplateManager(db)
mapper = MapGenerator()
geocoder = Geocoder()
extractor = LocationExtractor()
org_id = st.session_state.get("org_id", db.get_or_create_organisation("Default Organisation"))

_MAX_GEOCODE_PER_RUN = 40


def _ensure_document_locations_ready(document_id: int) -> dict:
    stats = {
        "extracted": 0,
        "new_geocoded": 0,
        "total_locations": 0,
        "total_geocoded": 0,
        "attempted": 0,
    }

    rows = db.fetchall(
        "SELECT id, place_name, location_type, context, latitude, longitude, geocoded FROM locations WHERE document_id = ?",
        (document_id,),
    )

    if not rows:
        pages = db.fetchall(
            "SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number",
            (document_id,),
        )
        text = "\n".join(p["content"] for p in pages if p.get("content"))
        extracted = extractor.extract_from_text(text, document_id=document_id)
        stats["extracted"] = len(extracted)
        if Config.ENABLE_GEOCODING and extracted:
            extracted = geocoder.geocode_batch(extracted)
        for loc in extracted:
            loc_id = db.insert("locations", loc)
            loc["id"] = loc_id
        rows = extracted

    if Config.ENABLE_GEOCODING:
        missing = [
            row for row in rows
            if row.get("latitude") is None or row.get("longitude") is None or not row.get("geocoded")
        ]
        unique_names = []
        seen = set()
        for row in missing:
            name = (row.get("place_name") or "").strip()
            key = name.lower()
            if not name or key in seen:
                continue
            seen.add(key)
            unique_names.append(name)

        for place_name in unique_names[:_MAX_GEOCODE_PER_RUN]:
            stats["attempted"] += 1
            lat, lon = geocoder.geocode(place_name)
            if lat is None:
                continue
            db.execute(
                """
                UPDATE locations
                SET latitude = ?, longitude = ?, geocoded = 1
                WHERE document_id = ? AND lower(place_name) = lower(?)
                """,
                (lat, lon, document_id, place_name),
            )
            stats["new_geocoded"] += 1

        rows = db.fetchall(
            "SELECT id, place_name, location_type, context, latitude, longitude, geocoded FROM locations WHERE document_id = ?",
            (document_id,),
        )

    stats["total_locations"] = len(rows)
    stats["total_geocoded"] = sum(
        1 for row in rows if row.get("latitude") is not None and row.get("longitude") is not None
    )
    return stats

# ── Select template ─────────────────────────────────────────────────────────
templates = tm.list_templates(org_id)
if not templates:
    st.warning("No templates found. Go to **Templates** to create one first.")
    st.stop()

template_options = {t["name"]: t["id"] for t in templates}
selected_tmpl_name = st.selectbox("Select report template", list(template_options.keys()))
template_id = template_options[selected_tmpl_name]

# ── Select source documents ─────────────────────────────────────────────────
docs = db.fetchall(
    "SELECT id, title, file_name, document_type FROM documents "
    "WHERE organisation_id = ? AND status = 'active' ORDER BY title",
    (org_id,),
)
if not docs:
    st.warning("No processed documents available. Upload documents first.")
    st.stop()

doc_options = {f"{d['title']} ({d['document_type']})": d["id"] for d in docs}
selected_doc_names = st.multiselect("Select source documents", list(doc_options.keys()))
selected_doc_ids = [doc_options[n] for n in selected_doc_names]

report_name = st.text_input("Report name", value=f"Report — {selected_tmpl_name}")

if st.button("🚀 Generate Report", type="primary") and selected_doc_ids:
    with st.spinner("Extracting data and filling template…"):
        # Gather full text from selected documents
        texts = []
        for doc_id in selected_doc_ids:
            pages = db.fetchall(
                "SELECT content FROM document_pages WHERE document_id = ? ORDER BY page_number",
                (doc_id,),
            )
            texts.append("\n\n".join(p["content"] for p in pages if p["content"]))

        # Fill template
        filled = tm.fill_template(template_id, texts)

        # Persist report
        report_id = db.insert("reports", {
            "organisation_id": org_id,
            "template_id": template_id,
            "name": report_name,
            "status": "complete",
        })
        for doc_id in selected_doc_ids:
            db.insert("report_sources", {"report_id": report_id, "document_id": doc_id})
        template = tm.get_template(template_id)
        for field in template["fields"]:
            fk = field["field_key"]
            if fk in filled:
                db.insert("report_values", {
                    "report_id": report_id,
                    "field_id": field["id"],
                    "raw_value": str(filled[fk]["value"] or ""),
                    "confidence": filled[fk]["confidence"],
                })

    st.success(f"✅ Report '{report_name}' generated (id={report_id})")

    # Display result
    st.markdown("---")
    st.subheader("Extracted Values")
    rows = []
    for fk, info in filled.items():
        rows.append({
            "Field": info["label"],
            "Type": info["type"],
            "Value": info["value"] or "—",
            "Confidence": f"{info['confidence']:.0%}",
            "Required": "✅" if info["required"] else "",
            "Context": (info["context"] or "")[:120],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Previous reports ────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("Generated Reports")
reports = db.fetchall(
    "SELECT r.id, r.name, t.name AS template, r.status, r.created_at "
    "FROM reports r JOIN report_templates t ON t.id = r.template_id "
    "WHERE r.organisation_id = ? ORDER BY r.created_at DESC",
    (org_id,),
)
if reports:
    st.dataframe(pd.DataFrame(reports), use_container_width=True, hide_index=True)
else:
    st.info("No reports generated yet.")

st.markdown("---")
st.subheader("Executive Summary — Documents")

summary_rows = db.fetchall(
    """
    SELECT d.id,
           d.title,
           d.document_type,
           COUNT(l.id) AS location_mentions,
           SUM(CASE WHEN l.latitude IS NOT NULL AND l.longitude IS NOT NULL THEN 1 ELSE 0 END) AS geocoded_mentions
    FROM documents d
    LEFT JOIN locations l ON l.document_id = d.id
    WHERE d.organisation_id = ?
      AND d.status = 'active'
    GROUP BY d.id, d.title, d.document_type
    ORDER BY d.title
    """,
    (org_id,),
)

if summary_rows:
    summary_df = pd.DataFrame(summary_rows)
    st.dataframe(
        summary_df.rename(
            columns={
                "title": "Document",
                "document_type": "Type",
                "location_mentions": "Location mentions",
                "geocoded_mentions": "Geocoded mentions",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    selectable = [row for row in summary_rows if int(row.get("location_mentions") or 0) > 0]
    if selectable:
        selectable_by_id = {int(row["id"]): row for row in selectable}
        option_ids = list(selectable_by_id.keys())

        def _format_doc_option(doc_id: int) -> str:
            row = selectable_by_id.get(int(doc_id), {})
            return (
                f"{row.get('title', 'Document')} ({row.get('document_type', '')}) "
                f"— {int(row.get('geocoded_mentions') or 0)} geocoded"
            )

        selected_doc_id = st.selectbox(
            "Select document from Executive Summary for interactive map",
            option_ids,
            format_func=_format_doc_option,
            key="reports_geo_selected_doc_id",
        )

        prep_col, refresh_col = st.columns([4, 1])
        with refresh_col:
            refresh_geo = st.button("Refresh geo", key="reports_geo_refresh", use_container_width=True)

        last_prepared_doc = st.session_state.get("reports_geo_last_prepared_doc")
        should_prepare = bool(refresh_geo) or (last_prepared_doc != selected_doc_id)

        if should_prepare:
            with st.spinner("Preparing geospatial data for selected document..."):
                prep = _ensure_document_locations_ready(selected_doc_id)
            st.session_state["reports_geo_last_prepared_doc"] = selected_doc_id
            st.session_state["reports_geo_last_prep"] = prep
        else:
            prep = st.session_state.get("reports_geo_last_prep") or {
                "attempted": 0,
                "new_geocoded": 0,
                "total_locations": 0,
                "total_geocoded": 0,
            }

        with prep_col:
            st.caption(
                f"Geocoding attempts: {prep.get('attempted', 0)} (newly geocoded: {prep.get('new_geocoded', 0)}). "
                f"Total locations: {prep.get('total_locations', 0)} | geocoded: {prep.get('total_geocoded', 0)}"
            )

        doc_locations = db.fetchall(
            """
            SELECT place_name, location_type, context, latitude, longitude
            FROM locations
            WHERE document_id = ?
            ORDER BY place_name
            """,
            (selected_doc_id,),
        )
        geocoded_locations = [
            row for row in doc_locations
            if row.get("latitude") is not None and row.get("longitude") is not None
        ]
        if geocoded_locations:
            try:
                from streamlit_folium import st_folium

                st.markdown("**Interactive Geo Map (selected document)**")
                m = mapper.build_map(geocoded_locations)
                if m:
                    st_folium(
                        m,
                        use_container_width=True,
                        height=420,
                        key=f"reports_geo_map_{selected_doc_id}",
                    )
            except ImportError:
                st.warning("`streamlit-folium` not installed. Run `pip install streamlit-folium`.")
        else:
            if not Config.ENABLE_GEOCODING:
                st.info("Selected document has extracted locations, but geocoding is disabled (`ENABLE_GEOCODING=False`).")
            else:
                st.info(
                    "Selected document has extracted locations but still no geocoded coordinates. "
                    "Some place names may not resolve in free geocoding providers."
                )
    else:
        st.info("No documents with extracted location mentions yet.")
else:
    st.info("No active documents available for executive summary.")
