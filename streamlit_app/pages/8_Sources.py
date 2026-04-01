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
from streamlit_app.i18n import enable_serbian_locale

from config import Config
from database.db_manager import DatabaseManager
from document_processing.semantic_comparison.category_matcher import CategoryMatcher
from document_processing.semantic_comparison.reference_updater import ReferenceTemplateUpdater
from document_processing.semantic_comparison.sources_catalogue import SourcesCatalogue
from streamlit_app.components.sidebar import render_page_disclaimer, render_sidebar

enable_serbian_locale(st)
st.set_page_config(page_title="Izvori – SIPMT", page_icon="🌐", layout="wide")
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
            headers={"User-Agent": "SIPMT/1.0 (+source-check)"},
            method="HEAD",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"status": "Healthy", "http": r.status, "ok": True}
    except urllib.error.HTTPError as e:
        if e.code in (405, 403):
            try:
                req2 = urllib.request.Request(
                    url,
                    headers={"User-Agent": "SIPMT/1.0 (+source-check)"},
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

tab_view, tab_add, tab_refresh = st.tabs(["📋 Svi izvori", "➕ Dodaj izvor", "🔄 Osveži i obogati"])

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
            "Filtriraj po upravnom telu",
            options=["Svi"] + known_bodies,
            default=["Svi"],
        )
    with col_probe:
        run_probe = st.button("🩺 Pokreni proveru URL dostupnosti", use_container_width=True)

    if "Svi" in body_filter or not body_filter:
        filtered = all_sources
    else:
        filtered = [s for s in all_sources if s.get("body") in body_filter]

    probe_results: dict = {}
    if run_probe:
        prog = st.progress(0, text="Proveravam URL adrese…")
        for i, src in enumerate(filtered):
            probe_results[src.get("source_url", "")] = _probe(src.get("source_url", ""))
            prog.progress((i + 1) / max(len(filtered), 1), text=f"Provereno {i+1}/{len(filtered)}")
        prog.empty()
        healthy = sum(1 for v in probe_results.values() if v["ok"])
        st.info(f"Provera završena — ispravno: {healthy}/{len(probe_results)}.")

    for body in sorted({s.get("body", "Other") for s in filtered}):
        body_entries = [s for s in filtered if s.get("body", "Other") == body]
        with st.expander(f"**{body}** — {len(body_entries)} izvor(a)", expanded=False):
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
                        f"<small>_(nema URL-a)_</small>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    toggle_label = "Onemogući" if enabled else "Omogući"
                    if url and st.button(toggle_label, key=f"toggle_{url}", use_container_width=True):
                        catalogue.set_enabled(url, not enabled)
                        st.rerun()
                with c3:
                    if url and st.button("Ukloni", key=f"remove_{url}", use_container_width=True):
                        if st.session_state.get(f"confirm_remove_{url}"):
                            catalogue.remove_source(url)
                            st.success(f"Uklonjeno: {src.get('name')}")
                            st.rerun()
                        else:
                            st.session_state[f"confirm_remove_{url}"] = True
                            st.warning("Kliknite ponovo na Ukloni za potvrdu.")

    st.markdown("---")
    if st.button("📥 Sinhronizuj aktivne izvore u bazu (kreira nedostajuće šablone)", use_container_width=True):
        n = catalogue.sync_to_db(db)
        matcher.seed_database()
        st.success(f"Sinhronizovano {n} stavki kataloga u bazu.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Add a new source
# ══════════════════════════════════════════════════════════════════════════════
with tab_add:
    st.subheader("Dodaj novi referentni izvor")
    st.caption(
        "Unesite upravno telo, kategoriju i zvanični URL. "
        "Nakon čuvanja, koristite **Osveži i obogati** da preuzmete i izdvojite zahteve usklađenosti."
    )

    with st.form("add_source_form"):
        body_opt = catalogue.known_bodies() + ["Drugo (novo telo)"]
        selected_body = st.selectbox("Upravno telo", options=body_opt)
        custom_body = ""
        if selected_body == "Drugo (novo telo)":
            custom_body = st.text_input("Naziv novog tela (npr. UNICEF, Afrička unija, …)")
        body_val = custom_body.strip() if selected_body == "Drugo (novo telo)" else selected_body

        CATEGORIES = [
            "Policies", "Reports", "Monitoring", "Questionnaire",
            "Instructions", "Forms", "Guideline", "Resolution", "Directive", "Other",
        ]
        category_val = st.selectbox("Kategorija", options=CATEGORIES)
        name_val = st.text_input("Kratak naziv", placeholder="npr. UNICEF sažetak konvencije o pravima deteta")
        url_val = st.text_input("Zvanični URL izvora", placeholder="https://…")
        file_hint_val = st.text_input(
            "Predlog putanje fajla (opciono)",
            placeholder="unicef/child_rights.json",
            help="Relativna putanja unutar reference_templates/ gde će JSON biti sačuvan.",
        )
        submitted = st.form_submit_button("Sačuvaj u katalog")

    if submitted:
        missing = []
        if not body_val:
            missing.append("Upravno telo")
        if not name_val.strip():
            missing.append("Naziv")
        if not url_val.strip():
            missing.append("URL izvora")
        if missing:
            st.error(f"Nedostaju obavezna polja: {', '.join(missing)}")
        elif catalogue.find(url_val.strip()):
            st.warning("Ovaj URL već postoji u katalogu.")
        else:
            entry = catalogue.add_source(
                body=body_val,
                name=name_val.strip(),
                source_url=url_val.strip(),
                category=category_val,
                file_hint=file_hint_val.strip(),
            )
            st.success(f"Dodat je izvor **{entry['name']}** [{body_val}] u katalog.")
            st.info("Pređite na karticu **Osveži i obogati** da preuzmete i obradite ovaj izvor.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Refresh and LLM enrich
# ══════════════════════════════════════════════════════════════════════════════
with tab_refresh:
    st.subheader(f"Preuzmi izvore sa interneta · Obogati pomoću modela {provider_label}")
    st.caption(
        "Python preuzima svaki zvanični URL sa interneta i uklanja HTML sadržaj u običan tekst. "
        f"Zatim **{provider_label}** (lokalno pokrenut) čita taj tekst i izdvaja ključne sekcije, "
        "zahteve usklađenosti i ključne reči. Korisnički dokumenti ne napuštaju vašu mašinu."
    )

    catalogue.reload()
    known_bodies = catalogue.known_bodies()

    col_bodies, col_opts = st.columns([3, 1])
    with col_bodies:
        selected_bodies = st.multiselect(
            "Tela za osvežavanje",
            options=known_bodies,
            default=[b for b in ["UN", "UNESCO", "EU", "OECD"] if b in known_bodies],
        )
    with col_opts:
        do_enrich = st.checkbox(
            f"Obogati pomoću modela {provider_label}",
            value=True,
            help=(
                "Nakon preuzimanja stranice izvora, pošalji izdvojeni tekst lokalnom LLM modelu "
                "radi izdvajanja ključnih sekcija, zahteva i ključnih reči."
            ),
        )

    st.info(
        f"**Tok podataka:**  \n"
        f"1. Python → internet → preuzima zvanični URL  \n"
        f"2. Uklanjanje HTML-a → običan tekst (ostaje lokalno)  \n"
        f"3. {'→ ' + provider_label + ' (lokalni model) → izdvajanje zahteva usklađenosti' if do_enrich else '→ samo hash ažuriranje (bez LLM poziva)'}  \n"
        f"4. Rezultati se čuvaju u lokalnoj SQLite bazi"
    )

    if st.button(
        f"🔄 Osveži izvore: {', '.join(selected_bodies) if selected_bodies else 'sve'}"
        + (f" + obogaćivanje modelom {provider_label}" if do_enrich else ""),
        use_container_width=True,
        type="primary",
    ):
        if not selected_bodies:
            st.warning("Izaberite najmanje jedno upravno telo za osvežavanje.")
        else:
            # Make sure catalogue entries are in the DB first
            catalogue.sync_to_db(db)
            matcher.seed_database()

            with st.spinner(f"Preuzimam izvore i pokrećem obogaćivanje modelom {provider_label}…"):
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
                f"Osvežavanje završeno — ažurirano: **{updated}**, neizmenjeno: **{unchanged}**, "
                f"greške izvora: **{len(errors)}**"
                + (f", obogaćeno modelom {provider_label}: **{enriched}**" if do_enrich else "")
                + "."
            )

            if errors:
                with st.expander("⚠️ Greške pri preuzimanju izvora", expanded=True):
                    for r in errors:
                        st.markdown(f"- **[{r.get('body')}] {r.get('name')}**: {r.get('error')}")

            if enrich_errors:
                with st.expander(f"⚠️ Upozorenja za obogaćivanje modelom {provider_label}", expanded=False):
                    for r in enrich_errors:
                        st.markdown(f"- **[{r.get('body')}] {r.get('name')}**: {r.get('llm_error')}")

            # Summary table
            rows = []
            for r in results:
                rows.append({
                    "Telo": r.get("body", ""),
                    "Naziv": r.get("name", ""),
                    "Status": r.get("status", "error" if r.get("error") else "—"),
                    "Ažurirano": "✅" if r.get("updated") else "—",
                    f"Obogaćeno ({provider_label})": "✅" if r.get("llm_enriched") else ("⚠️" if r.get("llm_error") else "—"),
                    "Greška": (r.get("error") or "")[:80],
                })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Trenutni pregled šablona u bazi")
    db_templates = db.get_reference_templates()
    if db_templates:
        snap = []
        for t in db_templates:
            snap.append({
                "Telo": t.get("body", ""),
                "Kategorija": t.get("category", ""),
                "Naziv": t.get("name", ""),
                "Verzija": t.get("version", ""),
                "URL izvora": (t.get("source_url") or "")[:60],
                "Poslednja provera": _fmt_ts(t.get("source_last_checked")),
                "Aktivan": "✅" if t.get("is_active") else "⚫",
            })
        st.dataframe(pd.DataFrame(snap), use_container_width=True, hide_index=True)
    else:
        st.info("U bazi još nema šablona. Koristite iznad opcije **Sinhronizuj** ili **Osveži**.")

render_page_disclaimer()
