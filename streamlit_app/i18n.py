from __future__ import annotations

from typing import Any, Callable


_EXACT = {
    "Home": "Početna",
    "Documents": "Dokumenti",
    "Templates": "Šabloni",
    "Reports": "Izveštaji",
    "Changes": "Izmene",
    "Map": "Mapa",
    "Compliance": "Usklađenost",
    "Sources": "Izvori",
    "Help": "Pomoć",
    "Navigation": "Navigacija",
    "Help & Resources": "Pomoć i resursi",
    "Quick Guide": "Brzi vodič",
    "Full Documentation": "Kompletna dokumentacija",
    "Disclaimer": "Odricanje od odgovornosti",
    "Select document": "Izaberite dokument",
    "Select source documents": "Izaberite izvorne dokumente",
    "Select report template": "Izaberite šablon izveštaja",
    "Report name": "Naziv izveštaja",
    "Generate Report": "Generiši izveštaj",
    "Extracted Values": "Izdvojene vrednosti",
    "Generated Reports": "Generisani izveštaji",
    "Executive Summary": "Izvršni sažetak",
    "Refresh health": "Osveži status",
    "Document": "Dokument",
    "Document Category": "Kategorija dokumenta",
    "Reference template": "Referentni šablon",
    "Reference source": "Referentni izvor",
    "Run Compliance Analysis": "Pokreni analizu usklađenosti",
    "Analyze selected": "Analiziraj izabrano",
    "Analyze all documents": "Analiziraj sve dokumente",
    "Save last analysis to DB": "Sačuvaj poslednju analizu u bazu",
    "Export CSV": "Izvezi CSV",
    "Raw entries": "Sirovi zapisi",
    "Location list": "Lista lokacija",
    "Extraction summary": "Sažetak izdvajanja",
    "Force re-extract selected documents": "Prinudno ponovo izdvoji izabrane dokumente",
    "Extract & Map Locations": "Izdvoji i mapiraj lokacije",
    "Matcher": "Uparivač",
    "spaCy (fast)": "spaCy (brzo)",
    "Ollama LLM (JSON)": "Ollama LLM (JSON)",
}

_FRAGMENTS = [
    ("Social Inclusion Document Analyzer", "Analizator dokumenata socijalne inkluzije"),
    ("Document Management", "Upravljanje dokumentima"),
    ("Template Manager", "Upravljač šablonima"),
    ("Report Generator", "Generator izveštaja"),
    ("Change Monitor", "Nadzor izmena"),
    ("Geospatial View", "Geoprostorni prikaz"),
    ("Semantic Compliance Analysis", "Semantička analiza usklađenosti"),
    ("Reference Sources Catalogue", "Katalog referentnih izvora"),
    ("Saved Justifications", "Sačuvana obrazloženja"),
    ("Help & Documentation", "Pomoć i dokumentacija"),
    ("Comprehensive guide to all features", "Sveobuhvatan vodič kroz sve funkcionalnosti"),
    ("Overview Dashboard", "Pregledna kontrolna tabla"),
    ("Upload & Manage Source Files", "Otpremanje i upravljanje izvornim fajlovima"),
    ("Define Data Extraction Fields", "Definisanje polja za izdvajanje podataka"),
    ("Generate Structured Data Extracts", "Generisanje strukturisanih izvoda podataka"),
    ("Track Document Versions", "Praćenje verzija dokumenata"),
    ("Geospatial Visualization", "Geoprostorna vizualizacija"),
    ("Configuration", "Konfiguracija"),
    ("Tips & Best Practices", "Saveti i najbolje prakse"),
    ("Need More Help?", "Potrebna vam je dodatna pomoć?"),
    ("Dashboard", "Kontrolna tabla"),
    ("Metrics", "Metrike"),
    ("KPI", "KPI"),
    ("Upload", "Otpremi"),
    ("Download", "Preuzmi"),
    ("View", "Prikaži"),
    ("Preview", "Pregled"),
    ("Create", "Kreiraj"),
    ("Save", "Sačuvaj"),
    ("Cancel", "Otkaži"),
    ("Search", "Pretraga"),
    ("Filter", "Filter"),
    ("Status", "Status"),
    ("Category", "Kategorija"),
    ("Title", "Naslov"),
    ("Type", "Tip"),
    ("Field", "Polje"),
    ("Required", "Obavezno"),
    ("Optional", "Opciono"),
    ("Confidence", "Pouzdanost"),
    ("Summary", "Sažetak"),
    ("Recommendations", "Preporuke"),
    ("Present Elements", "Prisustni elementi"),
    ("Missing Elements", "Nedostajući elementi"),
    ("Strengths", "Snage"),
    ("Gaps", "Nedostaci"),
    ("Executive", "Izvršni"),
    ("Health check", "Provera statusa"),
    ("Last updated", "Poslednje ažuriranje"),
    ("Current", "Trenutno"),
    ("selected", "izabrano"),
    ("Select", "Izaberi"),
    ("Found", "Pronađeno"),
    ("No templates yet.", "Još nema šablona."),
    ("No reports generated yet.", "Još nema generisanih izveštaja."),
    ("No documents", "Nema dokumenata"),
    ("processing", "obrada"),
    ("Processing", "Obrada"),
    ("generated", "generisano"),
    ("Generated", "Generisano"),
    ("extracted", "izdvojeno"),
    ("Extracted", "Izdvojeno"),
    ("document", "dokument"),
    ("Document", "Dokument"),
    ("documents", "dokumenti"),
    ("Documents", "Dokumenti"),
    ("template", "šablon"),
    ("Template", "Šablon"),
    ("report", "izveštaj"),
    ("Report", "Izveštaj"),
    ("changes", "izmene"),
    ("Changes", "Izmene"),
    ("locations", "lokacije"),
    ("Locations", "Lokacije"),
    ("analysis", "analiza"),
    ("Analysis", "Analiza"),
    ("guidance", "smernice"),
    ("policy", "politika"),
    ("Policy", "Politika"),
    ("framework", "okvir"),
    ("Framework", "Okvir"),
    ("human rights", "ljudska prava"),
    ("Human Rights", "Ljudska prava"),
    ("social inclusion", "socijalna inkluzija"),
    ("Social Inclusion", "Socijalna inkluzija"),
    ("Upload New Documents", "Otpremi nove dokumente"),
    ("Choose files (PDF, DOCX, XLSX) — max 20 MB each", "Izaberite fajlove (PDF, DOCX, XLSX) — najviše 20 MB po fajlu"),
    ("Document category", "Kategorija dokumenta"),
    ("Process & Save", "Obradi i sačuvaj"),
    ("Document Library", "Biblioteka dokumenata"),
    ("Select document to preview or delete", "Izaberite dokument za pregled ili brisanje"),
    ("Re-process", "Ponovo obradi"),
    ("Delete", "Obriši"),
    ("No documents uploaded yet.", "Još nema otpremljenih dokumenata."),
    ("No extracted text available for this document.", "Za ovaj dokument nema izdvojenog teksta."),
    ("Extracted Entities", "Izdvojeni entiteti"),
    ("Existing Templates", "Postojeći šabloni"),
    ("Create New Template", "Kreiraj novi šablon"),
    ("Define a New Report Template", "Definišite novi šablon izveštaja"),
    ("Template name", "Naziv šablona"),
    ("Description", "Opis"),
    ("Fields", "Polja"),
    ("Number of fields", "Broj polja"),
    ("Save Template", "Sačuvaj šablon"),
    ("No templates found. Go to **Templates** to create one first.", "Nema pronađenih šablona. Idite na **Šabloni** da prvo kreirate jedan."),
    ("No processed documents available. Upload documents first.", "Nema obrađenih dokumenata. Najpre otpremite dokumente."),
    ("Extracting data and filling template", "Izdvajanje podataka i popunjavanje šablona"),
    ("Executive Summary — Documents", "Izvršni sažetak — Dokumenti"),
    ("Compare Two Document Versions", "Uporedi dve verzije dokumenta"),
    ("Recent Changes", "Nedavne izmene"),
    ("No changes detected yet.", "Još nisu detektovane izmene."),
    ("Upload at least two documents to compare.", "Otpremite najmanje dva dokumenta za poređenje."),
    ("Old version", "Stara verzija"),
    ("New version", "Nova verzija"),
    ("Compare", "Uporedi"),
    ("Diff snippet", "Isečak razlika"),
    ("Refresh geo", "Osveži geo"),
    ("Interactive Geo Map (selected document)", "Interaktivna geo mapa (izabrani dokument)"),
    ("No reports generated yet.", "Još nema generisanih izveštaja."),
    ("No active documents available for executive summary.", "Nema aktivnih dokumenata za izvršni sažetak."),
    ("Ready to run compliance analysis.", "Spremno za pokretanje analize usklađenosti."),
    ("Queued for Compliance analysis.", "Analiza usklađenosti je u redu čekanja."),
    ("Compliance live monitor", "Uživo monitor usklađenosti"),
    ("Live chunk rate", "Uživo brzina tokova"),
    ("Execution timeline", "Vremenska linija izvršavanja"),
    ("Latest runtime detail", "Najnoviji detalji izvršavanja"),
    ("Streaming preview", "Pregled toka"),
    ("No saved HRBA analyses found for the selected filters.", "Nema sačuvanih HRBA analiza za izabrane filtere."),
    ("All documents", "Svi dokumenti"),
    ("Filter by document", "Filtriraj po dokumentu"),
    ("No URL", "Nema URL-a"),
    ("Healthy", "Ispravno"),
    ("Error", "Greška"),
    ("Add Source", "Dodaj izvor"),
    ("All Sources", "Svi izvori"),
    ("Refresh & Enrich", "Osveži i obogati"),
    ("Disable", "Onemogući"),
    ("Enable", "Omogući"),
    ("Remove", "Ukloni"),
    ("Added", "Dodato"),
    ("Failed", "Neuspešno"),
    ("Success", "Uspešno"),
    ("Policies", "Politike"),
    ("Reports", "Izveštaji"),
    ("Questionnaire", "Upitnik"),
    ("Instructions", "Uputstva"),
    ("Forms", "Formulari"),
    ("Monitoring", "Monitoring"),
    ("Guideline", "Smernica"),
    ("Resolution", "Rezolucija"),
    ("Directive", "Direktiva"),
    ("Other", "Ostalo"),
    ("Default Organisation", "Podrazumevana organizacija"),
    ("No", "Ne"),
    ("Yes", "Da"),
    ("On", "Uključeno"),
    ("Off", "Isključeno"),
]


def tr(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    out = value
    if out in _EXACT:
        return _EXACT[out]
    for src, dst in _FRAGMENTS:
        if src in out:
            out = out.replace(src, dst)
    return out


def _wrap_with_text_translation(fn: Callable[..., Any], text_pos: int = 0, text_kw: str | None = None):
    def _wrapped(*args, **kwargs):
        args = list(args)
        if text_kw and text_kw in kwargs:
            kwargs[text_kw] = tr(kwargs[text_kw])
        elif len(args) > text_pos:
            args[text_pos] = tr(args[text_pos])
        return fn(*args, **kwargs)

    return _wrapped


def _wrap_select_like(fn: Callable[..., Any]):
    def _wrapped(*args, **kwargs):
        args = list(args)
        if args:
            args[0] = tr(args[0])
        elif "label" in kwargs:
            kwargs["label"] = tr(kwargs["label"])

        user_format = kwargs.get("format_func")

        def _fmt(x):
            base = user_format(x) if callable(user_format) else x
            return tr(str(base))

        kwargs["format_func"] = _fmt
        return fn(*args, **kwargs)

    return _wrapped


def enable_serbian_locale(st_module) -> None:
    if getattr(st_module, "_sr_locale_enabled", False):
        return

    for name in ("title", "header", "subheader", "caption", "info", "success", "warning", "error", "markdown"):
        if hasattr(st_module, name):
            setattr(st_module, name, _wrap_with_text_translation(getattr(st_module, name)))

    for name in ("button", "checkbox", "text_input", "text_area", "number_input", "file_uploader", "expander"):
        if hasattr(st_module, name):
            setattr(st_module, name, _wrap_with_text_translation(getattr(st_module, name)))

    if hasattr(st_module, "radio"):
        st_module.radio = _wrap_select_like(st_module.radio)
    if hasattr(st_module, "selectbox"):
        st_module.selectbox = _wrap_select_like(st_module.selectbox)
    if hasattr(st_module, "multiselect"):
        st_module.multiselect = _wrap_select_like(st_module.multiselect)

    if hasattr(st_module, "tabs"):
        _tabs = st_module.tabs

        def _tabs_wrapped(items, *args, **kwargs):
            if isinstance(items, (list, tuple)):
                items = [tr(str(i)) for i in items]
            return _tabs(items, *args, **kwargs)

        st_module.tabs = _tabs_wrapped

    if hasattr(st_module, "metric"):
        _metric = st_module.metric

        def _metric_wrapped(label, *args, **kwargs):
            return _metric(tr(label), *args, **kwargs)

        st_module.metric = _metric_wrapped

    if hasattr(st_module, "page_link"):
        _page_link = st_module.page_link

        def _page_link_wrapped(*args, **kwargs):
            if "label" in kwargs:
                kwargs["label"] = tr(kwargs["label"])
            return _page_link(*args, **kwargs)

        st_module.page_link = _page_link_wrapped

    if hasattr(st_module, "set_page_config"):
        _set_page_config = st_module.set_page_config

        def _set_page_config_wrapped(*args, **kwargs):
            if "page_title" in kwargs:
                kwargs["page_title"] = tr(kwargs["page_title"])
            return _set_page_config(*args, **kwargs)

        st_module.set_page_config = _set_page_config_wrapped

    st_module._sr_locale_enabled = True
