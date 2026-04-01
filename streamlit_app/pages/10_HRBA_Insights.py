import json
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
import plotly.express as px
from streamlit_app.i18n import enable_serbian_locale

from config import Config
from database.db_manager import DatabaseManager

from streamlit_app.components.sidebar import render_page_disclaimer, render_sidebar
from streamlit_app.components.help_button import render_help_button

enable_serbian_locale(st)
st.set_page_config(page_title="HRBA prikazi — SIPMT", page_icon="⚖️", layout="wide")
render_sidebar()

col1, col2 = st.columns([14, 4])
with col1:
    st.title("⚖️ HRBA Prikazi podataka — Sačuvana opravdanja")
with col2:
    render_help_button("⚖️ HRBA Prikazi")

st.markdown(
    """
    Prikaži sačuvane HRBA analize koja su generisana sa HRBA uparivanjem (spaCy or Ollama).
    Koristite filtere da bi ste selektovali dati document ili datum radi prikaza rezultata.
    """
)

db = DatabaseManager()
org_id = st.session_state.get("org_id") if "org_id" in st.session_state else db.get_or_create_organisation("Default Organisation")

# Fetch documents for organisation
docs = db.fetchall(
    "SELECT id, title FROM documents WHERE organisation_id = ? ORDER BY created_at DESC",
    (org_id,),
)
doc_map = {d["id"] if isinstance(d, dict) else d[0]: (d["title"] if isinstance(d, dict) else d[1]) for d in docs}

doc_options = ["Svi dokumenti"] + [f"{doc_id}: {title}" for doc_id, title in doc_map.items()]
selected_doc = st.selectbox("Filtriraj po dokumentu", options=doc_options)

rows = db.get_latest_hrba_analyses(limit=500, organisation_id=org_id)

records: List[Dict[str, Any]] = []
for r in rows:
    sa_id = r.get("id") if isinstance(r, dict) else r[0]
    doc_id = r.get("document_id") if isinstance(r, dict) else r[1]
    doc_title = r.get("doc_title") if isinstance(r, dict) else r[2]
    model_used = r.get("model_used") if isinstance(r, dict) else r[3]
    raw = r.get("full_response_json") if isinstance(r, dict) else r[4]
    created_at = r.get("created_at") if isinstance(r, dict) else r[5]

    # Normalize raw JSON
    parsed = None
    if not raw:
        parsed = []
    else:
        if isinstance(raw, (dict, list)):
            parsed = raw
        else:
            try:
                parsed = json.loads(raw)
            except Exception:
                # try to extract JSON substring
                text = str(raw)
                s = text.find("{")
                e = text.rfind("}")
                if s != -1 and e != -1 and e > s:
                    try:
                        parsed = json.loads(text[s : e + 1])
                    except Exception:
                        parsed = []
                else:
                    parsed = []

    # parsed can be dict or list; normalize to list of entries
    entries = []
    if isinstance(parsed, dict):
        entries = [parsed]
    elif isinstance(parsed, list):
        entries = parsed

    for ent in entries:
        if not isinstance(ent, dict):
            continue
        # Determine highest scoring category if present
        scores = {k: ent.get(k) for k in ("availability", "accessibility", "acceptability", "quality") if ent.get(k) is not None}
        if scores:
            highest = max(scores.items(), key=lambda x: float(x[1]))
            highest_category, highest_score = highest[0], float(highest[1])
        else:
            highest_category, highest_score = None, None

        justification = ent.get("justification") or ent.get("reason") or ent.get("explanation")
        original_text = ent.get("original_text") or ent.get("text") or ""

        records.append(
            {
                "analysis_id": sa_id,
                "document_id": doc_id,
                "document_title": doc_title,
                "model_used": model_used,
                "created_at": created_at,
                "original_text": original_text,
                "highest_category": highest_category,
                "highest_score": highest_score,
                "justification": justification,
                "raw_json": json.dumps(ent, ensure_ascii=False),
            }
        )

# Apply document filter
if selected_doc != "Svi dokumenti":
    sel_id = int(selected_doc.split(":", 1)[0])
    records = [r for r in records if int(r["document_id"]) == sel_id]

if not records:
    st.info("Nema sačuvanih HRBA analiza za izabrane filtere.")
else:
    df = pd.DataFrame(records)
    st.subheader(f"Sačuvana obrazloženja ({len(df)})")

    # Timeline / per-document visualization
    try:
        df["created_at_dt"] = pd.to_datetime(df["created_at"], errors="coerce")
    except Exception:
        df["created_at_dt"] = pd.to_datetime(df["created_at"], errors="coerce")

    if df["created_at_dt"].notna().any():
        timeline_df = df.copy()
        timeline_df["score_val"] = timeline_df["highest_score"].fillna(0).astype(float)
        fig = px.scatter(
            timeline_df,
            x="created_at_dt",
            y="document_title",
            color="highest_category",
            size="score_val",
            hover_data=["document_id", "justification", "highest_score"],
            title="Vremenska linija HRBA analiza",
        )
        fig.update_layout(height=360, xaxis_title="Vreme analize", yaxis_title="Dokument")
        st.plotly_chart(fig, use_container_width=True)
        # Multi-document Gantt-style view: small bars centered on analysis time
        try:
            if df["document_title"].nunique() > 1:
                md = df.copy()
                md["score_val"] = md["highest_score"].fillna(0).astype(float)
                # map score to a short duration (seconds) for visualization
                md["delta_secs"] = md["score_val"].apply(lambda s: max(5, int(s * 60)))
                md["start"] = md["created_at_dt"] - pd.to_timedelta(md["delta_secs"] / 2, unit="s")
                md["end"] = md["created_at_dt"] + pd.to_timedelta(md["delta_secs"] / 2, unit="s")
                gfig = px.timeline(
                    md,
                    x_start="start",
                    x_end="end",
                    y="document_title",
                    color="highest_category",
                    hover_data=["document_id", "original_text", "highest_score", "justification"],
                    title="Višedokumentni HRBA Gant (po analizi)",
                )
                gfig.update_yaxes(autorange="reversed")
                gfig.update_layout(height=420)
                st.plotly_chart(gfig, use_container_width=True)
        except Exception:
            pass
    st.dataframe(df[["created_at", "document_id", "document_title", "model_used", "highest_category", "highest_score", "justification"]])

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Izvezi CSV", csv, file_name="hrba_justifications.csv", mime="text/csv")

    st.markdown("---")
    st.subheader("Sirovi zapisi")
    for row in records:
        with st.expander(f"Doc {row['document_id']} — {row['highest_category']} — {row['created_at']}"):
            st.write(row["original_text"])
            st.write("Obrazloženje:")
            st.write(row.get("justification"))
            st.markdown("**Raw JSON**")
            st.json(json.loads(row["raw_json"]) if row["raw_json"] else {})

render_page_disclaimer()
