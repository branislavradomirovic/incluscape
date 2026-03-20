import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json
import time
import urllib.error
import urllib.request
from datetime import datetime

import pandas as pd
import streamlit as st

from config import Config
from database.db_manager import DatabaseManager
from document_processing.semantic_comparison.category_matcher import CategoryMatcher
from document_processing.semantic_comparison.reference_updater import ReferenceTemplateUpdater
from document_processing.semantic_comparison.sources_catalogue import SourcesCatalogue
from streamlit_app.components.sidebar import render_sidebar

st.set_page_config(page_title="Sources – INCLUSCAPE", page_icon="🌐", layout="wide")
render_sidebar()

st.title("🌐 Reference Sources Catalogue")
st.caption(
    "Manage the official external reference documents used to check compliance. "
    "Sources are fetched from the internet by Python, then enriched locally by Ollama "
    "(or Gemini when configured). No API sends your documents to the internet."
)

db = DatabaseManager()
db.initialize()
catalogue = SourcesCatalogue(db=db)
matcher = CategoryMatcher(db=db)
updater = ReferenceTemplateUpdater(db=db)
provider = Config.SEMANTIC_LLM_PROVIDER.lower()
provider_label = "Ollama" if provider == "ollama" else "Gemini"


# ── helpers ────────────────────────────────────────────────────────────────────

def _probe(url: str, timeout: int = 12) -> dict:
    if not url:
        return {"status": "No URL", "http": "-", "ok": False}
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "INCLUSCAPE/1.0 (+source-check)"},
            method="HEAD",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"status": "Healthy", "http": r.status, "ok": True}
    except urllib.error.HTTPError as e:
        if e.code in (405, 403):
            try:
                req2 = urllib.request.Request(
                    url,
                    headers={"User-Agent": "INCLUSCAPE/1.0 (+source-check)"},
                    method="GET",
                )
                with urllib.request.urlopen(req2, timeout=timeout) as r:
                    return {"status": "Healthy (GET)", "http": r.status, "ok": True}
            except Exception:
                pass
        return {"status": f"HTTP {e.code}", "http": e.code, "ok": False}
    except Exception as exc:
        return {"status": f"Error: {exc}", "http": "-", "ok": False}


def _fmt_ts(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)[:19] if str(value) else "—"


# ── tabs ───────────────────────────────────────────────────────────────────────

tab_view, tab_add, tab_refresh = st.tabs(["📋 All Sources", "➕ Add Source", "🔄 Refresh & Enrich"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — View / manage catalogue
# ══════════════════════════════════════════════════════════════════════════════
with tab_view:
    catalogue.reload()
    all_sources = catalogue.all_sources()
    known_bodies = catalogue.known_bodies()

    col_filter, col_probe = st.columns([3, 1])
    with col_filter:
        body_filter = st.multiselect(
            "Filter by governing body",
            options=["All"] + known_bodies,
            default=["All"],
        )
    with col_probe:
        run_probe = st.button("🩺 Run URL health check", use_container_width=True)

    if "All" in body_filter or not body_filter:
        filtered = all_sources
    else:
        filtered = [s for s in all_sources if s.get("body") in body_filter]

    probe_results: dict = {}
    if run_probe:
        prog = st.progress(0, text="Probing URLs…")
        for i, src in enumerate(filtered):
            probe_results[src.get("source_url", "")] = _probe(src.get("source_url", ""))
            prog.progress((i + 1) / max(len(filtered), 1), text=f"Checked {i+1}/{len(filtered)}")
        prog.empty()
        healthy = sum(1 for v in probe_results.values() if v["ok"])
        st.info(f"Health check done — {healthy}/{len(probe_results)} healthy.")

    for body in sorted({s.get("body", "Other") for s in filtered}):
        body_entries = [s for s in filtered if s.get("body", "Other") == body]
        with st.expander(f"**{body}** — {len(body_entries)} source(s)", expanded=False):
            for src in body_entries:
                url = src.get("source_url") or ""
                enabled = src.get("enabled", True)
                probe = probe_results.get(url, {})

                c1, c2, c3 = st.columns([6, 1, 1])
                with c1:
                    status_icon = "🟢" if enabled else "⚫"
                    if probe:
                        status_icon = "✅" if probe["ok"] else "❌"
                    st.markdown(
                        f"{status_icon} **{src.get('name', '—')}** · *{src.get('category', '')}*  \n"
                        f"<small>[{url}]({url})</small>" if url else
                        f"{status_icon} **{src.get('name', '—')}** · *{src.get('category', '')}*  \n"
                        f"<small>_(no URL)_</small>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    toggle_label = "Disable" if enabled else "Enable"
                    if url and st.button(toggle_label, key=f"toggle_{url}", use_container_width=True):
                        catalogue.set_enabled(url, not enabled)
                        st.rerun()
                with c3:
                    if url and st.button("Remove", key=f"remove_{url}", use_container_width=True):
                        if st.session_state.get(f"confirm_remove_{url}"):
                            catalogue.remove_source(url)
                            st.success(f"Removed: {src.get('name')}")
                            st.rerun()
                        else:
                            st.session_state[f"confirm_remove_{url}"] = True
                            st.warning("Click Remove again to confirm.")

    st.markdown("---")
    if st.button("📥 Sync enabled sources → DB (creates missing templates)", use_container_width=True):
        n = catalogue.sync_to_db(db)
        matcher.seed_database()
        st.success(f"Synced {n} catalogue entries to the database.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Add a new source
# ══════════════════════════════════════════════════════════════════════════════
with tab_add:
    st.subheader("Add a new reference source")
    st.caption(
        "Enter the governing body, category, and official URL. "
        "After saving, use **Refresh & Enrich** to fetch and extract compliance requirements."
    )

    with st.form("add_source_form"):
        body_opt = catalogue.known_bodies() + ["Other (new body)"]
        selected_body = st.selectbox("Governing body", options=body_opt)
        custom_body = ""
        if selected_body == "Other (new body)":
            custom_body = st.text_input("New body name (e.g. UNICEF, African Union, …)")
        body_val = custom_body.strip() if selected_body == "Other (new body)" else selected_body

        CATEGORIES = [
            "Policies", "Reports", "Monitoring", "Questionnaire",
            "Instructions", "Forms", "Guideline", "Resolution", "Directive", "Other",
        ]
        category_val = st.selectbox("Category", options=CATEGORIES)
        name_val = st.text_input("Short name", placeholder="e.g. UNICEF Child Rights Convention Summary")
        url_val = st.text_input("Official source URL", placeholder="https://…")
        file_hint_val = st.text_input(
            "File hint (optional)",
            placeholder="unicef/child_rights.json",
            help="Relative path under reference_templates/ where the JSON will be stored.",
        )
        submitted = st.form_submit_button("Save to catalogue")

    if submitted:
        missing = []
        if not body_val:
            missing.append("Governing body")
        if not name_val.strip():
            missing.append("Name")
        if not url_val.strip():
            missing.append("Source URL")
        if missing:
            st.error(f"Required fields missing: {', '.join(missing)}")
        elif catalogue.find(url_val.strip()):
            st.warning("This URL is already in the catalogue.")
        else:
            entry = catalogue.add_source(
                body=body_val,
                name=name_val.strip(),
                source_url=url_val.strip(),
                category=category_val,
                file_hint=file_hint_val.strip(),
            )
            st.success(f"Added **{entry['name']}** [{body_val}] to the catalogue.")
            st.info("Go to the **Refresh & Enrich** tab to fetch and process this source.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Refresh and LLM enrich
# ══════════════════════════════════════════════════════════════════════════════
with tab_refresh:
    st.subheader(f"Fetch sources from the internet · Enrich with {provider_label}")
    st.caption(
        "Python fetches each official URL over the internet and strips HTML → plain text. "
        f"**{provider_label}** (running locally) then reads that text and extracts "
        "key sections, compliance requirements, and keywords. "
        "No user documents leave your machine."
    )

    catalogue.reload()
    known_bodies = catalogue.known_bodies()

    col_bodies, col_opts = st.columns([3, 1])
    with col_bodies:
        selected_bodies = st.multiselect(
            "Bodies to refresh",
            options=known_bodies,
            default=[b for b in ["UN", "UNESCO", "EU", "OECD"] if b in known_bodies],
        )
    with col_opts:
        do_enrich = st.checkbox(
            f"Enrich with {provider_label}",
            value=True,
            help=(
                "After fetching the source page, send the extracted text to the local LLM "
                "to extract key sections, requirements, and keywords."
            ),
        )

    st.info(
        f"**Data flow:**  \n"
        f"1. Python → internet → fetches official URL  \n"
        f"2. Strip HTML → plain text (stays local)  \n"
        f"3. {'→ ' + provider_label + ' (local model) → extracts compliance requirements' if do_enrich else '→ hash-only update (no LLM call)'}  \n"
        f"4. Results saved to local SQLite database"
    )

    if st.button(
        f"🔄 Refresh {', '.join(selected_bodies) if selected_bodies else 'all'} sources"
        + (f" + {provider_label} enrichment" if do_enrich else ""),
        use_container_width=True,
        type="primary",
    ):
        if not selected_bodies:
            st.warning("Select at least one governing body to refresh.")
        else:
            # Make sure catalogue entries are in the DB first
            catalogue.sync_to_db(db)
            matcher.seed_database()

            with st.spinner(f"Fetching sources and running {provider_label} enrichment…"):
                results = updater.refresh_bodies(
                    bodies=selected_bodies,
                    use_llm=do_enrich,
                )

            updated = sum(1 for r in results if r.get("updated"))
            unchanged = sum(1 for r in results if r.get("status") in ("unchanged", "baseline_hash_set"))
            errors = [r for r in results if r.get("error")]
            enriched = sum(1 for r in results if r.get("llm_enriched"))
            enrich_errors = [r for r in results if r.get("llm_error")]

            st.success(
                f"Refresh complete — **{updated}** updated, **{unchanged}** unchanged, "
                f"**{len(errors)}** source errors"
                + (f", **{enriched}** {provider_label}-enriched" if do_enrich else "")
                + "."
            )

            if errors:
                with st.expander("⚠️ Source fetch errors", expanded=True):
                    for r in errors:
                        st.markdown(f"- **[{r.get('body')}] {r.get('name')}**: {r.get('error')}")

            if enrich_errors:
                with st.expander(f"⚠️ {provider_label} enrichment warnings", expanded=False):
                    for r in enrich_errors:
                        st.markdown(f"- **[{r.get('body')}] {r.get('name')}**: {r.get('llm_error')}")

            # Summary table
            rows = []
            for r in results:
                rows.append({
                    "Body": r.get("body", ""),
                    "Name": r.get("name", ""),
                    "Status": r.get("status", "error" if r.get("error") else "—"),
                    "Updated": "✅" if r.get("updated") else "—",
                    f"{provider_label} enriched": "✅" if r.get("llm_enriched") else ("⚠️" if r.get("llm_error") else "—"),
                    "Error": (r.get("error") or "")[:80],
                })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Current DB template snapshot")
    db_templates = db.get_reference_templates()
    if db_templates:
        snap = []
        for t in db_templates:
            snap.append({
                "Body": t.get("body", ""),
                "Category": t.get("category", ""),
                "Name": t.get("name", ""),
                "Version": t.get("version", ""),
                "Source URL": (t.get("source_url") or "")[:60],
                "Last checked": _fmt_ts(t.get("source_last_checked")),
                "Active": "✅" if t.get("is_active") else "⚫",
            })
        st.dataframe(pd.DataFrame(snap), use_container_width=True, hide_index=True)
    else:
        st.info("No templates in database yet. Use **Sync** or **Refresh** above.")
