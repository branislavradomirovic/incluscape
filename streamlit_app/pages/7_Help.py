import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from streamlit_app.i18n import enable_serbian_locale
from streamlit_app.components.sidebar import render_page_disclaimer, render_sidebar


enable_serbian_locale(st)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HELP_IMAGE_ROOTS = [
   PROJECT_ROOT / "assets" / "help",
   PROJECT_ROOT / "assets",
   PROJECT_ROOT / "landing_page_assets",
]

VISUAL_CALLOUTS = {
   "Početna": {
      "focus": "Prikaz glavnog ekrana sa KPI karticama i mapom obuhvata.",
      "highlights": [
         "KPI kartice na vrhu sumiraju trenutno stanje radnog prostora: dokumente, šablone, izveštaje i otkrivene promene.",
         "Panel geografske pokrivenosti ispod pokazuje gde su koncentrisane izvučene lokacije i da li kontrolna tabla koristi samo podatke iz politika ili rezervne geokodirane podatke.",
         "Ovaj ekran je najbrže mesto za potvrdu da su unos, izveštavanje i geografska ekstrakcija svi popunjeni.",
      ],
   },
   "Dokumenti": {
      "focus": "Tok rada za učitavanje i biblioteku dokumenata",
      "highlights": [
         "Kontrole za učitavanje su ulazna tačka za nove PDF, Word fajlove i tabele.",
         "Biblioteka dokumenata ispod učitavača je operativna lista gde korisnici pregledaju naslove, tip dokumenta, stanje obrade i dostupne akcije.",
         "Ova snimka ekrana je namenjena da pokaže i unos i upravljanje nakon obrade u jednom okviru.",
      ],
   },
   "Šabloni": {
      "focus": "Izrada šablona",
      "highlights": [
         "Glavni obrazac definiše naziv šablona i šemu ekstrakcije na koju se oslanjaju izveštaji.",
         "Redovi polja predstavljaju tačnu strukturu koju SIPMT pokušava da popuni iz učitanih dokumenata.",
         "Ovaj ekran je referentni prikaz kako se kreira šema izveštaja pre nego što ekstrakcija počne.",
      ],
   },
   "Izveštaji": {
      "focus": "Tok generisanja izveštaja",
      "highlights": [
         "Gornji selektori određuju koji šablon i koji dokumenti se koriste za pokretanje ekstrakcije.",
         "Region rezultata prikazuje izvučene vrednosti, signale poverenja i generisane izlaze izveštaja nakon završetka obrade.",
         "Ova slika treba da pomogne korisnicima da povežu postavke izveštaja sa sačuvanim/generisanim izlazima koji se pojavljuju niže na stranici.",
      ],
   },
   "Promene": {
      "focus": "Pregled upoređivanja verzija",
      "highlights": [
         "Unosi nedavnih promena sumiraju koje revizije dokumenata su otkrivene i kada su sačuvane.",
         "Vidžet za upoređivanje je mesto gde se dve verzije postavljaju jedna pored druge kako bi se pregledale dodatke, brisanja i izmene.",
         "Ova snimka ekrana naglašava trag revizije i detaljan tok rada sa razlikama zajedno.",
      ],
   },
   "Map": {
      "focus": "Geospatial exploration",
      "highlights": [
         "Mapa sama po sebi je primarni vidžet, prikazujući geokodirane lokacije izvučene iz dokumenata.",
         "Pomoćni paneli, kao što su rezime ekstrakcije i lista lokacija, objašnjavaju šta je pronađeno i iz kojih dokumenata potiče.",
         "Ova slika treba da orijentiše korisnike kako prema vizuelnoj mapi, tako i prema osnovnim zapisima o izvučenim lokacijama.",
      ],
   },
   "KPI & Grafikoni": {
      "focus": "Tumačenje metrika",
      "highlights": [
         "Snimak ekrana povezuje objašnjenja KPI sa stvarnim prikazom kontrolne table kako bi korisnici mogli vizuelno da identifikuju svaku karticu metrike.",
         "Takođe pokazuje gde se region mape/šema nalazi u odnosu na numeričke kartice sažetka.",
         "Koristite ovaj poziv kada objašnjavate šta kontrolna tabla broji i odakle ti podaci dolaze.",
      ],
   },
   "Izvori": {
      "focus": "Upravljanje referentnim izvorima",
      "highlights": [
         "Katalog prikazuje trenutno upravljane izvore grupisane po telu, kategoriji i statusu osvežavanja.",
         "Vidžeti za kreiranje i osvežavanje izvora određuju kako se eksterni standardi preuzimaju i transformišu u interne referentne šablone.",
         "Ova snimka ekrana treba da učini vidljivim tok upravljanja materijalom za usklađenost na prvi pogled.",
      ],
   },
   "Usaglašenost": {
      "focus": "Radna površina za semantičku analizu",
      "highlights": [
         "Kontrole za izbor provajdera, dokumenata i referentnog šablona definišu konfiguraciju pokretanja analize.",
         "Sumarni izveštaji i grafikoni objašnjavaju kako konačni rezultat usklađivanja, tako i dokaze iza njega.",
         "Ova slika je namenjena da pokaže ceo put od kontrola postavki do izlaza analize u jednom vizuelnom prikazu.",
      ],
   },
   "HRBA": {
      "focus": "AAAQ usklađivanje tok rada",
      "highlights": [
         "Centralni prikaz pokazuje proces AAAQ usklađivanja na nivou dokumenata i sve generisane rezultate ili ocene.",
         "Paneli za uživo prikaz ili vremensku liniju otkrivaju kako je odabrani model proizveo rezultat tokom vremena.",
         "Ova snimka ekrana treba da pomogne korisnicima da razumeju da je HRBA i alat za analizu i tok rada za prikupljanje dokaza.",
      ],
   },
   "HRBA Prikazi": {
      "focus": "Pregled sačuvane analize",
      "highlights": [
         "Tabela sačuvanih opravdanja je istorijski zapis prethodno sačuvanih HRBA nalaza.",
         "Sekcija sirovih unosa pruža vidljivost na nivou revizije u sačuvane podatke i objašnjenja.",
         "Ovaj prikaz je dizajniran za pregled i praćenje dokaza, a ne za generisanje nove analize.",
      ],
   },
   "Developer & Admin": {
      "focus": "Operativne kontrole",
      "highlights": [
         "Ovaj odeljak je operativna referenca za promenljive okruženja, korake za rešavanje problema i komande za održavanje.",
         "Povezani snimak ekrana treba da pomogne administratorima da povežu pisana uputstva za postavljanje sa vidljivim administratorskim interfejsom.",
         "Koristite ga prilikom uvođenja održavalaca ili dijagnostikovanja problema sa implementacijom i konfiguracijom u toku rada.",
      ],
   },
}


def _resolve_help_image(*candidates: str) -> Optional[Path]:
   for root in HELP_IMAGE_ROOTS:
      for candidate in candidates:
         image_path = root / candidate
         if image_path.exists():
            return image_path
   return None


def render_help_screenshot(section_name: str, caption: str, *candidates: str) -> None:
   image_path = _resolve_help_image(*candidates)

   # Try to find a localized callout: exact match, english->serbian map, or case-insensitive
   callout = VISUAL_CALLOUTS.get(section_name)
   if callout is None:
      EN_TO_SR = {
         "Home": "Početna",
         "Documents": "Dokumenti",
         "Templates": "Šabloni",
         "Reports": "Izveštaji",
         "Changes": "Promene",
         "Map": "Map",
         "Sources": "Izvori",
         "Compliance": "Compliance",
         "HRBA": "HRBA",
         "HRBA Insights": "HRBA Prikazi",
         "Documents": "Dokumenti",
      }
      mapped = EN_TO_SR.get(section_name)
      if mapped:
         callout = VISUAL_CALLOUTS.get(mapped)
      else:
         # fallback: case-insensitive search through keys
         for k in VISUAL_CALLOUTS.keys():
            if k.lower() == section_name.lower():
               callout = VISUAL_CALLOUTS.get(k)
               break

   left_col, right_col = st.columns([2, 1], gap="large")
   with left_col:
      if image_path:
         st.image(str(image_path), use_container_width=True, caption=caption)
      else:
         joined_candidates = ", ".join(candidates)
         st.info(
            f"Slika ekrana za '{section_name}' će se pojaviti ovde kada se doda kao jedan od: {joined_candidates}."
         )

   with right_col:
      focus_label = callout.get("focus", "Fokus ekrana") if callout else "Fokus ekrana"
      highlights = callout.get("highlights", []) if callout else []
      st.markdown("### Vizuelni fokus")
      st.markdown(f"**Primarni fokus:** {focus_label}")
      if highlights:
         st.markdown("**Na šta obratiti pažnju**")
         for item in highlights:
            st.markdown(f"- {item}")
      st.markdown("**Kako koristiti ovaj snimak**")
      st.markdown(
         "1. Povežite elemente na snimku sa opisima u tekstualnom delu sekcije."
         "  \n2. Obratite pažnju na oblasti označene kao ključne za verifikaciju podataka."
         "  \n3. Ako slika nije dostupna, koristite kratki opis iznad da brzo locirate kontrolu u aplikaciji."
      )
   st.markdown("---")

st.set_page_config(page_title="Pomoć — SIPMT", page_icon="❓", layout="wide")
render_sidebar()

st.title("❓ Pomoć i dokumentacija")
st.markdown("Kompletan vodič kroz funkcionalnosti sistema SIPMT")
st.caption(
   "Ova stranica može prikazati žive snimke ekrana iz repozitorijuma. "
   "Postavite slike sekcija u assets/help, assets ili landing_page_assets i one će se automatski učitati."
)
st.markdown("---")

# Serbian-first help content (shown to users). Legacy English content below is skipped.
st.caption("Snimci ekrana se automatski učitavaju iz assets/help, assets ili landing_page_assets.")

with st.expander("🏠 Početna", expanded=True):
   render_help_screenshot(
      "Home",
      "Prikaz početne stranice sa KPI karticama i mapom obuhvata.",
      "home.png",
      "dashboard.png",
      "Dashboard.png",
   )
   st.markdown(
      """
- **Početna** daje brz pregled sistema: dokumenti, šabloni, izveštaji i izmene.
- Mapa prikazuje geokodirane lokacije izdvojene iz obrađenih dokumenata.
- Koristite ovu stranicu za brzu proveru stanja pre detaljne analize.
"""
   )

with st.expander("📄 Dokumenti"):
   render_help_screenshot(
      "Documents",
      "Stranica Dokumenti sa otpremanjem fajlova i rezultatima obrade.",
      "documents.png",
      "Documents.png",
      "page_documents.png",
   )
   st.markdown(
      """
- Otpremanje PDF/DOCX/XLSX fajlova (do 20 MB po fajlu).
- Kategorizacija i obrada sadržaja sa izdvajanje teksta, entiteta i lokacija.
- Pregled biblioteke, ponovno procesiranje i bezbedno brisanje dokumenata.
"""
   )

with st.expander("📋 Šabloni"):
   render_help_screenshot(
      "Templates",
      "Definisanje šablona polja za automatsko izdvajanje podataka.",
      "templates.png",
      "Templates.png",
      "page_templates.png",
   )
   st.markdown(
      """
- Kreiranje šablona sa poljima i tipovima podataka.
- Obeležavanje obaveznih i opcionalnih polja.
- Hint-ovi za ekstrakciju radi boljeg uparivanja sa sadržajem dokumenta.
"""
   )

with st.expander("📊 Izveštaji"):
   render_help_screenshot(
      "Reports",
      "Generisanje izveštaja na osnovu šablona i izabranih dokumenata.",
      "reports.png",
      "Reports.png",
      "page_reports.png",
   )
   st.markdown(
      """
- Izbor šablona i izvornih dokumenata.
- Automatsko popunjavanje vrednosti i prikaz nivoa pouzdanosti.
- Čuvanje rezultata u bazi i dalji pregled istorije izveštaja.
"""
   )

with st.expander("🔍 Izmene"):
   render_help_screenshot(
      "Changes",
      "Poređenje verzija dokumenata i prikaz detektovanih razlika.",
      "changes.png",
      "Changes.png",
      "page_changes.png",
   )
   st.markdown(
      """
- Praćenje razlika između starih i novih verzija dokumenata.
- Prikaz procenta promene, dodatih i uklonjenih linija.
- Korisno za audit trag i kontrolu izmena.
"""
   )

with st.expander("🗺️ Mapa"):
   render_help_screenshot(
      "Map",
      "Interaktivna mapa lokacija izdvojenih iz dokumenata.",
      "map.png",
      "Map.png",
      "page_map.png",
   )
   st.markdown(
      """
- Vizualizacija geokodiranih lokacija na mapi.
- Filtriranje po dokumentu i pregled konteksta u tabeli.
- Za prikaz koordinata potrebno je uključeno geokodiranje.
"""
   )

with st.expander("🔎 Usklađenost"):
   render_help_screenshot(
      "Compliance",
      "Semantička analiza dokumenta prema referentnim okvirima.",
      "compliance.png",
      "Compliance.png",
      "page_compliance.png",
   )
   st.markdown(
      """
- Izaberite dokument i referentni šablon.
- Pokrenite analizu (Gemini ili Ollama).
- Dobijate skor usklađenosti, praznine i preporuke.
"""
   )

with st.expander("🌐 Izvori"):
   render_help_screenshot(
      "Sources",
      "Katalog referentnih izvora i kontrole za osvežavanje.",
      "sources.png",
      "Sources.png",
      "page_sources.png",
   )
   st.markdown(
      """
- Upravljanje zvaničnim URL izvorima.
- Osvežavanje i obogaćivanje referenci.
- Pregled aktivnih šablona koji se koriste u analizi usklađenosti.
"""
   )

with st.expander("⚖️ HRBA uparivanje"):
   render_help_screenshot(
      "HRBA",
      "AAAQ analiza i tok obrade po segmentima.",
      "hrba.png",
      "HRBA.png",
      "page_hrba.png",
   )
   st.markdown(
      """
- Analiza dostupnosti, pristupačnosti, prihvatljivosti i kvaliteta (AAAQ).
- Režimi rada: spaCy (brže) i Ollama LLM (dublja analiza).
- Rezultati se mogu sačuvati i kasnije pregledati.
"""
   )

with st.expander("🧾 HRBA uvidi"):
   render_help_screenshot(
      "HRBA Insights",
      "Pregled sačuvanih HRBA analiza i obrazloženja.",
      "hrba_insights.png",
      "HRBA_Insights.png",
      "page_hrba_insights.png",
   )
   st.markdown(
      """
- Filtriranje i pregled sačuvanih HRBA nalaza.
- Izvoz rezultata u CSV.
- Revizija sirovih JSON zapisa.
"""
   )

st.markdown("---")
with st.expander("⚙️ Konfiguracija", expanded=False):
   st.markdown(
      """
- `ENABLE_SEMANTIC_ANALYSIS`, `SEMANTIC_LLM_PROVIDER`
- `GEMINI_API_KEY`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- `ENABLE_GEOCODING`
- `DATABASE_URL` / `DATABASE_PATH`
"""
   )

st.markdown("---")
with st.expander("💡 Saveti za korišćenje", expanded=False):
   st.markdown(
      """
- Koristite jasna imena dokumenata i verzija.
- Proveravajte polja sa niskom pouzdanošću.
- Redovno osvežavajte referentne izvore.
- Za sporiji model povećajte timeout ili koristite manji model.
"""
   )

render_page_disclaimer()
st.stop()

# ──────────────────────────────────────────────────────────────────────────
# HOME
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🏠 **Početak** — Početni Glavni Prikaz", expanded=True):
   render_help_screenshot(
      "Početna",
      "Trenutni prikaz kontrolne table sa KPI karticama i geografskim opsegom.",
      "home.png",
      "dashboard.png",
      "Dashboard.png",
   )
   st.markdown("""
   **Početna** stranica je glavna stranica koja prikazuje vaš radni prostor, pružajući pregled metrika i uvid u vaše podatke.

    #### Glavne funkcije:

    **📊 Pregled metrika**
    - **Dokumenti**: Ukupan broj učitanih dokumenata u sistemu
    - **Šabloni**: Broj definisanih šablona izveštaja
    - **Izveštaji**: Broj generisanih izveštaja iz kombinacija šablona i dokumenata
    - **Promene otkrivene**: Broj instanci promena otkrivenih upoređivanjem verzija dokumenata

    **📍 Mapa obuhvata dokumenata**
    - Prikazuje interaktivnu mapu svih geografskih lokacija izvučenih iz **Policies** dokumenata
    - Pomaže vam da vizualizujete geografski obuhvat vašeg okvira politika
    - Zahteva da dokumenti budu obrađeni sa omogućenom ekstrakcijom lokacija
    - Lokacije su geokodirane (ako je `ENABLE_GEOCODING=True` u `.env`) i označene na OpenStreetMap sloju

    #### Kada koristiti:
    - Kada prvi put otvorite SIPMT da biste videli statistiku radnog prostora
    - Da biste razumeli geografski obuhvat vaših politika
    - Kao brzu proveru da li se dokumenti obrađuju
    """)

# ──────────────────────────────────────────────────────────────────────────
# DOKUMENTA
# ──────────────────────────────────────────────────────────────────────────
with st.expander("📄 **Dokumenta** — Upload & Upravljanje Izvornim Fajlovima"):
   render_help_screenshot(
      "Dokumenta",
      "Stranica dokumenta — Prikaz stranice sa kontrolama za upload, opcijama kategorizacije i rezultatima obrade.",
      "documents.png",
      "Documents.png",
      "page_documents.png",
   )
   st.markdown("""
    The **Dokumenta** stranica je mesto gde možete da učitate i upravljate svim vašim izvornim fajlovima.
    
    #### Podržani formati fajlova:
    - **PDF** — Skenirani dokumenti, dokumenti politika, izveštaji (sa ili bez ugrađenog teksta)
    - **DOCX** — Microsoft Word dokumenti, obrasci, uputstva
    - **XLSX** — Excel tabele, podaci, monitoring podaci

    #### Veličina fajla i ograničenja:
    - **Maksimalna veličina po fajlu**: 20 MB
    - **Višestruki upload**: Možete učitati više fajlova odjednom
    - **Detekcija duplikata**: Fajlovi sa identičnim sadržajem se automatski označavaju i mogu biti preskočeni

    #### Koraci obrade:
    1. **Upload**: Izaberite jedan ili više fajlova sa vašeg računara
    2. **Kategorizacija**: Dodelite svaki fajl jednoj od šest vrsta dokumenata:
       - **Upitnik** — Ankete, obrasci za prikupljanje podataka
       - **Policies** — Zvanični okviri politika, smernice
       - **Instructions** — Uputstva, operativni priručnici
       - **Forms** — Šabloni, obrasci za prijavu, obrasci za usklađenost
       - **Reports** — Izveštaji o praćenju, izveštaji o proceni, evaluacije
       - **Monitoring** — Dokumenti za kontinuirano praćenje, kontrolne table, KPI izveštaji
    3. **Extract**: Sistem automatski izvlači:
       - **Text** — Sav tekstualni sadržaj iz dokumenata
       - **Tables** — Struktuirani podaci formatirani kao CSV
       - **Named Entities** — Ljudi, organizacije, lokacije identifikovani putem NLP
       - **Locations** — Geografska imena mesta (države, gradovi, regioni)
    4. **Store**: Procesirani sadržaj se čuva u bazi podataka za analizu

    #### Napredne funkcije:
    - **Re-process dugme**: Za starije dokumente koji nisu u potpunosti obrađeni, ponovo pokrenite ceo pipeline
    - **Pregled izvlačenog teksta**: Kliknite na "View" pored dokumenta da biste videli izvlačeni sadržaj
    - **Brisanje**: Uklonite dokumente koje više ne trebate (soft delete)

    #### Kada koristiti:
    - Kada dodajete nove dokumente za analizu
    - Da biste pripremili dokumente za generisanje izveštaja ili proveru usklađenosti
    - Kada ažurirate obim podataka sa novim verzijama politika
    """)

# ──────────────────────────────────────────────────────────────────────────
# ŠABLONI
# ──────────────────────────────────────────────────────────────────────────
with st.expander("📋 **Šabloni** — Definišite polja za ekstrakciju podataka"):
   render_help_screenshot(
      "Templates",
      "Stranica Šablona — Prikaz stranice sa poljima obrasca i uređivačem šeme ekstrakcije.",
      "templates.png",
      "Templates.png",
      "page_templates.png",
   )
   st.markdown("""
    The **Šabloni** stranica omogućava kreiranje ponovo upotrebljivih definicija polja za automatsku ekstrakciju podataka.
    
    #### Šta je Šablon?
    A **Šablon izveštaja** je strukturisana specifikacija informacija koje želite da izdvojite iz dokumenata:
    - A **naziv** that describes what the template captures (e.g., "Social Inclusion Indicators", "Health Policy Compliance Check")
    - A **skup polja**, each with:
      - **Naziv polja** — A descriptive label (e.g., "Target Population", "Implementation Date")
      - **Tip polja** — The data type SIPMT will look for:
        - **Tekst** — Free-form text fields (e.g., description, summary)
        - **Broj** — Numeric values (e.g., budget amount, percentage)
        - **Datum** — Calendar dates (e.g., effective date, review date)
        - **Boolean** — Yes/No fields (e.g., "Is monitoring required?")
        - **Lista** — Comma-separated or bulleted values (e.g., stakeholder names)
        - **Lokacija** — Place names, regions, countries
      - **Opis** (optional) — Context to help the extractor
      - **Prioritet** — Whether field is Required or Optional

    #### Proces podudaranja šablona:
    Kada kreirate šablon, SIPMT koristi **fuzzy matching** da automatski pronađe odgovarajuće vrednosti u dokumentima:
    1. Naziv polja se upoređuje sa izvlačenim tekstom iz dokumenta
    2. Semantički analizator (Gemini ili Ollama) pomaže u tumačenju namere
    3. Podudarne vrednosti se automatski popunjavaju u generisanim izveštajima

    #### Kreiranje šablona:
    1. Kliknite **"kreiraj novi šablon"**
    2. Unesite naziv šablona
    3. Dodajte polja koristeći tabelu:
       - Navedite naziv polja, tip, opis
       - Obeležite kao Obavezno/Neobavezno
    4. Kliknite "Sačuvaj šablon"

    #### Slučajevi upotrebe:
    - Definišite polja za različite tipove dokumenata (politike, izveštaji, upitnici)
    - Kreirajte šablone specifične za institucije za doslednu ekstrakciju podataka
    - Omogućite standardizovano izveštavanje preko više dokumenata

    #### Kada koristiti:
    - Kada dodajete nove dokumente za analizu
    - Da biste pripremili dokumente za generisanje izveštaja ili proveru usklađenosti
    - Kada ažurirate obim podataka sa novim verzijama politika
    """)

# ──────────────────────────────────────────────────────────────────────────
# Iveštaji
# ──────────────────────────────────────────────────────────────────────────
with st.expander("📊 **Izveštaji** — Generiše Struktuirane Skupove Podataka"):
   render_help_screenshot(
      "Izveštaji",
      "Stranica izveštaja — Prikaz stranice sa izborom šablona, izborom dokumenata, izvučenim vrednostima i akcijama izvoza.",
      "reports.png",
      "Reports.png",
      "page_reports.png",
   )
   st.markdown("""
    The **Izveštaji** stranica upravlja automatskom ekstrakcijom strukturiranih podataka koristeći šablone.
    
    #### Radni tok generisanja izveštaja:
    1. **Izaberite šablon** — Odaberite koji šablon definiše polja za ekstrakciju
    2. **Izaberite dokumente** — Odaberite jedan ili više izvora dokumenata za ekstrakciju
    3. **Pokrenite ekstrakciju** — Sistem obrađuje dokumente koristeći fuzzy matching + semantičku analizu
    4. **Pregled rezultata** — Pregledajte izvučene vrednosti, ocene poverenja i eventualna nedostajuća polja
    5. **Izvoz izveštaja** — Sačuvajte kao CSV, JSON ili Excel za dalju analizu

    #### Poverenje u ekstrakciju:
    - Svako izvučeno polje uključuje **ocenu poverenja** (0–100%)
    - **Visoko poverenje** (>80%) — Polje je jasno identifikovano u izvoru
    - **Srednje poverenje** (50–80%) — Polje je pronađeno, ali sa određenom nesigurnošću
    - **Nisko poverenje** (<50%) — Slabo podudaranje; preporučuje se ručna provera
    - **Nedostaje** — Polje nije pronađeno ni u jednom od odabranih dokumenata

    #### Istaknute funkcionalnosti:
    - **Batch ekstrakcija** — Obrada više dokumenata odjednom koristeći isti šablon
    - **Pregled polja** — Ručno uređivanje izvučenih vrednosti pre izvoza
    - **Audit trail** — Svaki izveštaj beleži koji su dokumenti korišćeni i kada
    - **Skladištenje** — Svi generisani izveštaji se čuvaju u bazi podataka
    - **Formati izvoza** — CSV (tabela), JSON (sistemska integracija), PDF (deljenje)

    #### Kada koristiti:
    - Za automatsko popunjavanje standardizovanih obrazaca izveštaja
    - Za prikupljanje doslednih podataka iz mnogih sličnih dokumenata
    - Za kreiranje CSV fajlova za dalju analizu ili vizualizaciju
    - Kada su vam potrebne verifikovane izvučene vrednosti sa ocenama poverenja
    """)

# ──────────────────────────────────────────────────────────────────────────
# PROMENE
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🔍 **Promene** — Praćenje verzija dokumenata"):
   render_help_screenshot(
      "Promene",
      "Snimak ekrana stranice Promene sa izlazom poređenja verzija i detektovanim razlikama.",
      "changes.png",
      "Changes.png",
      "page_changes.png",
   )
   st.markdown("""
    The **Promene** stranica prati i vizualizuje razlike između verzija dokumenata.
    
    #### Radni tok praćenja promena:
    1. **Automatsko otkrivanje** — Kada otpremite revidiranu verziju postojećeg dokumenta,
       SIPMT otkriva da ima isto ime, ali različit sadržaj
    2. **Generisanje razlika** — Sistem izvršava poređenje kako bi identifikovao:
       - **Dodato** — Nove sekcije, pasusi ili sadržaj
       - **Uklonjeno** — Sekcije obrisane u novoj verziji
       - **Izmenjeno** — Tekst koji je promenjen, ali nije dodat/uklonjen
    3. **Vizualizacija** — Prikaz jedan pored drugog sa isticanjem boja:
       - 🟢 **Zeleno** — Dodati sadržaj
       - 🔴 **Crveno** — Uklonjeni sadržaj
       - 🟡 **Žuto** — Izmenjeni sadržaj

    #### Revizija promena:
    - **Vremenska oznaka** — Tačno kada je svaka verzija otpremljena
    - **Promena veličine** — Koliko bajtova se promenilo između verzija
    - **Trajno skladištenje** — Sve detektovane promene se čuvaju za potrebe revizije

    #### Primeri upotrebe:
    - Praćenje evolucije politika tokom vremena
    - Praćenje kada su uputstva ili procedure ažurirane
    - Osiguranje da ste svesni svih promena u referentnim dokumentima
    - Kreiranje revizijskog traga verzija za izveštavanje o usklađenosti

    #### Kada koristiti:
    - Kada otpremite novu verziju postojećeg dokumenta
    - Za pregled šta se promenilo u ažuriranju politike
    - Za revizije usklađenosti koje zahtevaju praćenje promena
    - Pre usvajanja nove verzije dokumenta
    """)

# ──────────────────────────────────────────────────────────────────────────
# MAPA
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🗺️ **Mapa** — Prostorna Vizualizacija"):
   render_help_screenshot(
      "Mapa",
      "Snimak ekrana stranice Mapa sa oznakama lokacija dokumenata i geografskim filterima.",
      "map.png",
      "Map.png",
      "page_map.png",
   )
   st.markdown("""
    The **Mapa** stranica omogućava interaktivnu prostornu vizualizaciju izvučenih lokacija.
    
    #### Kako funkcioniše:
    1. **Ekstrakcija lokacija** — Kada se dokumenti obrade, imena mesta se identifikuju koristeći:
       - **Prepoznavanje obrazaca** — Prepoznaje poznate stringove zemalja/regija
       - **NLP (spaCy)** — Prepoznavanje imenovanih entiteta za pominjanje mesta
    2. **Geocoding** (optional):
       - Ako je `ENABLE_GEOCODING=True` u `.env`, svako ime mesta se konvertuje u geografske koordinate (latitude/longitude)
       - Koristi **Nominatim** (besplatna geokodirajuća usluga OpenStreetMap-a)
       - Zahteva internet konekciju
    3. **Vizualizacija** — Interaktivna mapa prikazuje:
       - **Oznake** — Svaka lokacija je označena na OpenStreetMap-u
       - **Pop-up prozori** — Klik na oznaku da vidite izvor dokumenta i kontekst
       - **Zumiranje/Pomeranje** — Istražite geografsku oblast interaktivno

    #### Karakteristike mape:
    - **Filtriranje po tipu dokumenta** — Prikazuje samo lokacije iz Politika, Izveštaja, Monitoring-a, itd.
    - **Zumiranje na region** — Fokusirajte se na određenu geografsku oblast
    - **Izvoz mape** — Sačuvajte kao HTML ili snimak ekrana za prezentacije

    #### Konfiguracija:
    - **Omogući geokodiranje**: Postavite `ENABLE_GEOCODING=True` u vašem `.env` fajlu
    - **Izaberite dokumente**: Odaberite koje dokumente želite da vizualizujete
    - **Ažurirajte lokacije**: Ponovo obradite dokumente da biste izvukli nove lokacije

    #### Primeri upotrebe:
    - Vizualizujte pokrivenost politika i programa
    - Identifikujte geografske praznine u implementacijama
    - Podelite obim sa zainteresovanim stranama u interaktivnom formatu
    - Planirajte regionalnu ekspanziju ili raspodelu resursa

    #### Kada koristiti:
    - Nakon otpremanja dokumenata Politika ili Programa
    - To brief stakeholders on geographic scope
    - For regional analysis and planning
    - In presentations or reports to show coverage
    """)

# ──────────────────────────────────────────────────────────────────────────
# KPIS & GRAFIKONI
# ──────────────────────────────────────────────────────────────────────────
with st.expander("📈 **KPIs & GrafikonI — Definicije, Izvori Podataka i Detalji Populacije", expanded=False):
   render_help_screenshot(
      "KPIs & GrafikonI",
      "Grafikoni se koriste kao referenca za KPI kartice i preglednu mapu geo-opsega.",
      "dashboard.png",
      "Dashboard.png",
      "kpis.png",
   )
   st.markdown("""
      Ovaj odeljak objašnjava svaki KPI prikazan na **Početnoj** tabli i svaki grafikon korišćen u aplikaciji: šta svaki metrik predstavlja, koje DB tabele i upiti ga popunjavaju, koliko često se ažurira i sve napomene.

      **Opšte napomene**
      - Svi KPI-ji na tabli su samo za čitanje i agregati se izvršavaju nad tabelama `documents`, `report_templates`, `reports` i `document_changes`.
      - Grafikoni mogu biti prikazani iz agregiranih SQL upita ili iz analiza u memoriji sačuvanih u JSON kolonama (za semantičke analize i izveštaje).
      - Vrednosti na tabli se izračunavaju u trenutku prikaza; one odražavaju trenutni sadržaj baze podataka kada se stranica učita ili kada korisnik navigira na stranicu.

      ---

      **Dashboard KPIs (Početna stranica)**

      - **Documents** (label: "📄 Documenta")
         - Šta predstavlja: Ukupan broj zapisa dokumenata sačuvanih za trenutnu organizaciju.
         - Izvor podataka / SQL: `SELECT COUNT(*) FROM documents WHERE organisation_id = ?`
         - Kako se kreira: povećava se kada se novi dokument otpremi i obradi; brisanja smanjuju broj (soft-delete poštuje polje `status`).
         - Update frequency: real-time at page render.

      - **Templates** (label: "📋 Šabloni")
         - Šta predstavlja: Broj sačuvanih šablona izveštaja dostupnih za ekstrakciju i izveštavanje.
         - Izvor podataka / SQL: `SELECT COUNT(*) FROM report_templates`
         - Kako se kreira: kreira se putem stranice Šabloni kada korisnik sačuva novi šablon.
         - Napomene: tela šablona mogu uključivati velike JSON podatke; KPI broji šablone bez obzira na veličinu tela ili izvor (DB ili uvezeni fajl).

      - **Reports** (label: "📊 Izveštaji")
         - Šta predstavlja: Broj generisanih izveštaja (strukturirani izlazi ekstrakcije) sačuvanih u tabeli `reports`.
         - Izvor podataka / SQL: `SELECT COUNT(*) FROM reports WHERE organisation_id = ?`
         - Kako se kreira: kada korisnik pokrene ekstrakciju nad dokumentima i sačuva ili izveze rezultate.

      - **Changes detected** (label: "🔍 Detektovane promene")
         - Šta predstavlja: Broj detektovanih promena (diff zapisa) između verzija dokumenata.
         - Izvor podataka / SQL: `SELECT COUNT(*) FROM document_changes WHERE organisation_id = ?`
         - Kako se kreira: kada se novi upload identifikuje kao nova verzija postojećeg dokumenta i proces diff kreira zapise promena.

      ---

      **Mapa i podaci o lokaciji**
      - Mapa opsega prikazuje geokodirane `locations` povezane sa `documents` (pogledajte tabelu `locations`).
      - Primarni SQL korišćen za mapu na tabli (preferirano za Politike):
         - Ograničeno na Politike: SELECT redove iz `locations` JOIN `documents` WHERE `document_type = 'Policies'` AND `geocoded = 1`.
         - Fallback: sve geokodirane lokacije kada Politike nemaju nijednu.
      - Kako se markeri popunjavaju: svaki geokodirani red `location` pruža `latitude`/`longitude`, `place_name`, `context` i `document_title` koji se koriste u iskačućem prozoru.

      ---

      **Usklađenost stranica grafikon i KPI-jevi**
      - **Rezultat usklađenosti**
         - Šta predstavlja: normalizovani skor usklađenosti (0–1) izračunat od strane `ComplianceChecker` kombinujući pokrivenost ključnih reči, zahteva i sekcija sa malim bonusima za telo/kategoriju.
         - Kako se izračunava: pogledajte `_score_reference_template` i `_build_executive_summary` u kodu stranice za usklađenost — algoritam kombinuje metrike pokrivenosti tokena i primenjuje težine (ključne reči 45%, zahtevi 35%, sekcije 20% plus bonusi).
         - Izvor: analitički payload-ovi sačuvani u `semantic_analyses` i privremeni rezultat u memoriji tokom izvođenja analize.

      - **SHAP mapa (proxy za doprinos karakteristika)**
         - Šta predstavlja: proxy za objašnjivost koji pokazuje koji faktori (Prisustvo elemenata, Snage, Nedostaci, Delimično, Praznine, Pritisak preporuka, Pokrivenost ključnih reči/zahteva/sekcija) su pozitivno ili negativno doprineli konačnom rezultatu usklađenosti.
         - Kako se kreira: `_compute_shap_proxy` agregira brojeve iz rezultata analize i vraća normalizovane vrednosti doprinosa između -1 i +1.
         - Popunjavanje grafikona: koristi Plotly Heatmap sa jednim redom `z` niza doprinosa i eksplicitnom skalom boja centriranom na 0.

      - **Klasifikacija i poređenje skorova (line/points)**
         - Šta predstavljaju: vremenske serije poverenja klasifikatora i rezultata poređenja šablona za trenutnu sesiju monitora ili istorijske analize.
         - Izvor: nizovi `classification_confidence_history` i `comparison_score_history` održavani u stanju monitora usklađenosti; sačuvane analize su dostupne putem `checker.get_analyses(document_id)`.
         - Kako se popunjavaju: dodaju se dok monitor prolazi kroz svaku fazu (classify, match, compare, persist). Grafikoni koriste Plotly `scatter` ili `line` tragove sa tačkama zabeleženim u listama `*_points`.

      - **Gantt prikaz vremenskog dijagrama (po segmentima)**
         - Šta predstavlja: vremenska linija po segmentima generisanja prilikom strimovanja LLM izlaza; trake su veličine prema skoru i obojene prema AAAQ oznaci.
         - Izvor: strimovani delovi obrađeni tokom Ollama/Gemini pokretanja, svaki praćen sa početkom/krajem i dodeljenom kategorijom/skorom.
         - Kako se popunjava: monitor usklađenosti beleži vremenske oznake i skorove delova u `chunk_history`; vremenska linija se prikazuje iz tih zapisa.

      ---

      **HRBA prikaz usaglašenosti**
      - **Live streaming preview**: inkrementalni tekst iz LLM tokom izvođenja HRBA analize. Popunjava se strimovanim HTTP odgovorima od Ollama (ako je podržano) ili se zamenjuje finalnim JSON-om kada strimovanje nije dostupno.
      - **Per-segment Gantt**: isti mehanizam kao vremenska linija usklađenosti — segmenti se generišu i vremenski prate tokom pokretanja modela.

      ---

      **Other charts across the app**
      - **Template source health table**: a diagnostics table produced by `_probe_source_url_health` that verifies external source URLs for templates; populated by issuing HEAD/GET requests and collecting HTTP status and suggestions.
      - **Map exports & filters**: map layers are created by `MapGenerator.build_map()` using the `scope_locations` rows; filters are executed by SQL before the map is built.

      ---

      **Problemi i saveti**
      - Ako je neki KPI neočekivano nula ili zastarela, proverite da li je vaš filter organizacije (`organisation_id`) postavljen i da li dokumenti imaju `status='active'`.
      - Grafikoni izvedeni iz semantičke analize oslanjaju se na keširane analize; ponovo pokrenite analize ili očistite keš ako mislite da se prikazuju zastareli rezultati.
      - Grafikoni koji se oslanjaju na LLM strimovanje zahtevaju da izabrani provajder podržava strimovanje; u suprotnom, grafikoni će se ažurirati kada stigne konačni odgovor.

      """)

# ──────────────────────────────────────────────────────────────────────────
# IZVORI
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🌐 **Izvori** — Katalog referenci i radni tok osvežavanja"):
   render_help_screenshot(
      "Izvori",
      "Screenshot stranice Izvori prikazuje katalog referenci, upravljanje izvorima i kontrole osvežavanja.",
      "sources.png",
      "Sources.png",
      "page_sources.png",
   )
   st.markdown("""
    The **Izvori** stranica upravlja zvaničnim spoljnim referentnim materijalom koji koristi motor za usklađenost.

    #### Šta ova stranica radi:
    - Prikazuje sve konfigurisane unose u katalogu izvora i referentna tela
    - Omogućava dodavanje novih zvaničnih URL-ova za standarde, direktive i smernice
    - Pokreće radne tokove osvežavanja za preuzimanje stranica izvora i ažuriranje interne baze šablona
    - Prikazuje trenutni snimak baze podataka aktivnog skupa referenci

    #### Glavni elementi interfejsa:
    - **Tabela kataloga** — Prikazuje trenutne zapise izvora, grupisane po telu i kategoriji
    - **Forma za dodavanje novog izvora** — Kreira novi unos izvora sa telom, oznakom, URL-om i naznakom fajla
    - **Kontrole za preuzimanje / obogaćivanje** — Preuzima sadržaj izvora sa interneta, zatim ga obogaćuje odabranim provajderom
    - **Sekcija snimka baze podataka** — Prikazuje trenutno materijalizovane zapise šablona koji se koriste za analizu usklađenosti

    #### Kada koristiti:
    - Kada je potrebno dodati nova međunarodna ili institucionalna uputstva
    - When existing external URLs changed and references must be refreshed
    - Before running compliance analyses that depend on newly updated source material
    """)

# ──────────────────────────────────────────────────────────────────────────
# USAGLAŠENOST
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🔎 **Usaglašenost** — Semantička analiza prema standardima"):
   render_help_screenshot(
      "Usaglašenost",
      "Screenshot stranice Usaglašenost sa selektorom provajdera, izborom referentnog šablona, prikazom rezultata i grafikona.",
      "compliance.png",
      "Compliance.png",
      "page_compliance.png",
   )
   st.markdown("""
    The **Usaglašenost** stranica omogućava naprednu AI podržanu semantičku analizu vaših dokumenata
    prema međunarodnim referentnim okvirima.
    
    #### Radni tok semantičke analize:
    1. **Izbor provajdera** — Odaberite vaš AI backend:
       - **Google Gemini** (cloud, zahteva API ključ) — Napredno rezonovanje, internet konektivnost
       - **Ollama** (lokalno, self-hosted) — Privatnost, offline rad
    2. **Provera zdravlja** — Proverite da li je odabrani AI provajder dostupan i funkcionalan
    3. **Izbor dokumenta** — Odaberite dokument koji želite analizirati
    4. **Referentni šablon** — Odaberite međunarodni okvir (UN, UNESCO, EU, itd.)
    5. **Pokretanje analize** — AI upoređuje dokument sa referentnim okvirom
    6. **Pregled izveštaja** — Struktuirana procena usaglašenosti sa preporukama

    #### Dostupni referentni okviri:
    - **UN Human Rights** — Okviri Univerzalne deklaracije o ljudskim pravima
    - **UN Sustainable Development Goals (SDGs)** — Fokus na Cilj 10 (Smanjenje nejednakosti)
    - **UNESCO Education** — Standardi i smernice za inkluzivno obrazovanje
    - **EU Equality Directive** — EU standardi za jednakost i nediskriminaciju
    - **EU Social Inclusion** — Direktive za socijalnu koheziju i inkluziju

    #### Struktura izveštaja o usaglašenosti:
    - **Klasifikacija dokumenta** — AI kategorizuje tip/opseg dokumenta
    - **Compliance Score** — 0–100% usklađenost sa referentnim okvirom
    - **Present Elements** — Koji zahtevi su već ispunjeni
    - **Identified Gaps** — Nedostajući ili nedovoljno specificirani delovi
    - **Recommendations** — Preporučeni koraci za poboljšanje usaglašenosti
    - **Source References** — Linkovi ka relevantnim spoljnim standardima

    #### Napredne funkcije:
    - **Template Version History** — Pregled ažuriranja i porekla referentnih šablona za administratore
    - **Refresh Sources** — Ručno ažuriranje referentnih šablona sa spoljnjih izvora
    - **Error Transparency** — Jasne poruke o greškama ako provajder nije dostupan

    #### Konfiguracija modela:
    - **Gemini**: Zahteva `GEMINI_API_KEY` u `.env`, postavite `SEMANTIC_LLM_PROVIDER=gemini`
    - **Ollama**: Zahteva da Ollama servis radi lokalno, postavite `SEMANTIC_LLM_PROVIDER=ollama`
    - **Izbor modela**: Konfigurišite putem `OLLAMA_MODEL` u `.env` (podrazumevano: qwen2.5:14b-instruct)

    #### Kada koristiti:
    - Za procenu usklađenosti politika sa međunarodnim standardima
    - Za izveštavanje i reviziju usaglašenosti
    - Za identifikaciju nedostataka u okviru socijalne inkluzije
    - Pre finalizacije novih politika ili procedura
    - Za izveštavanje zainteresovanih strana o usaglašenosti sa standardima
    """)

# ──────────────────────────────────────────────────────────────────────────
# KONFIGURACIJA
# ──────────────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("⚙️ **Konfiguracija** — Podešavanje okruženja"):
    st.markdown("""
    #### Ključne opcije konfiguracije (u `.env` fajlu)

    **Obrada dokumenata**
    - `UPLOAD_FOLDER` — Direktorijum gde se čuvaju otpremljeni fajlovi
    - `ALLOWED_EXTENSIONS` — Tipovi fajlova koje prihvatamo (pdf, docx, xlsx)
    - `MAX_FILE_SIZE_MB` — Ograničenje veličine fajla na serveru
    - `ENABLE_OCR` — Ekstrakcija teksta iz skeniranih/slikovnih dokumenata

    **Semantička analiza**
    - `ENABLE_SEMANTIC_ANALYSIS` — Uključivanje/isključivanje semantičke analize usaglašenosti
    - `SEMANTIC_LLM_PROVIDER` — Izbor `gemini` ili `ollama`
    - `GEMINI_API_KEY` — Vaš Google Gemini API ključ (za cloud analizu)
    - `GEMINI_MODEL` — Naziv modela (podrazumevano: `gemini-2.0-flash`)
    - `OLLAMA_BASE_URL` — Endpoint Ollama servisa (podrazumevano: `http://localhost:11434`)
    - `OLLAMA_MODEL` — Lokalni model za korišćenje (podrazumevano: `qwen2.5:14b-instruct`)

    **Geospatial**
    - `ENABLE_GEOCODING` — Omogućavanje automatskog geokodiranja lokacija (zahteva internet)

    **Logging**
    - `LOG_FILE` — Putanja do log fajlova aplikacije
    - `LOG_LEVEL` — Nivo detaljnosti logovanja (DEBUG, INFO, WARNING, ERROR)

    #### Početak rada sa različitim provajderima:

    **Korišćenje Google Gemini**
    ```
    SEMANTIC_LLM_PROVIDER=gemini
    GEMINI_API_KEY=your-api-key-here
    GEMINI_MODEL=gemini-2.0-flash
    ```
    [Get API key →](https://ai.google.dev)

    **Korišćenje Ollama (lokalno)**
    ```
    SEMANTIC_LLM_PROVIDER=ollama
    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_MODEL=qwen2.5:14b-instruct
    ```
    [Ollama Installation →](https://ollama.ai)

    Zatim povucite model:
    ```bash
    ollama pull qwen2.5:14b-instruct
    ```
    """)

# ──────────────────────────────────────────────────────────────────────────
# HRBA
# ──────────────────────────────────────────────────────────────────────────
with st.expander("⚖️ **HRBA — AAAQ Usaglašenost & Prikazi"):
   render_help_screenshot(
      "HRBA",
      "HRBA stranica screenshot sa AAAQ usaglašenostima, live izlazom i vremenskim prikazima.",
      "hrba.png",
      "HRBA.png",
      "page_hrba.png",
   )
   st.markdown("""
      The **HRBA** stranica skenira dokumente za AAAQ indikatore (Dostupnost, Pristupačnost,
      Prihvatljivost, Kvalitet) koristeći ili brzi `spaCy` matcher ili lokalni Ollama LLM.

      Glavne funkcionalnosti:
      - **Live streaming generation**: Kada koristite Ollama, aplikacija prikazuje uživo pregled teksta
         izlaza modela u desnom panelu dok model generiše.
      - **Per-segment timeline (Gantt)**: Stranica beleži početne/krajnje vremenske tačke po segmentu tokom
         streaminga i prikazuje Gantt-ov stil vremenske linije koja pokazuje kada je svaki segment generisan.
         Trake su veličine prema rezultatu i obojene prema najvišoj AAAQ kategoriji.
      - **Save analyses**: Sačuvajte kompletne JSON opravdanja u `semantic_analyses` za kasniji pregled
         na stranici **HRBA Insights**.

      Kako interpretirati korisnički interfejs:
      - **Live preview** prikazuje inkrementalni tekst dok model generiše. Ako model vraća
         samo konačni JSON objekat, pregled će se ažurirati kada konačni sadržaj stigne.
      - **Timeline** vizualizuje događaje generisanja po dokumentu. Duže trake označavaju
         rezultate sa višim ocenama (dužina je proporcionalna oceni). Koristite timeline da uočite
         spore segmente ili grupisanje analiza po dokumentu.

      Ispravke i saveti:
      - Ako ne vidite nijedan streaming fragment, proverite da li su `OLLAMA_BASE_URL` i `OLLAMA_MODEL` ispravni
         i da li je Ollama servis pokrenut. Neki modeli možda neće streamovati međufragmente.
      - Za dugotrajne generacije, povećajte `OLLAMA_TIMEOUT` u vašem okruženju (sekunde).
      - Ako generacija izgleda sporo, zagrejte model ili restartujte Ollama proces.
      """)

# ──────────────────────────────────────────────────────────────────────────
# HRBA PRIKAZI
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🧾 **HRBA Prikazi** — Sačuvana opravdanja & Pregled"):
   render_help_screenshot(
      "HRBA Prikazi",
      "HRBA Prikazi screenshot showing saved justifications, aggregated views, and raw saved entries.",
      "hrba_insights.png",
      "HRBA_Insights.png",
      "page_hrba_insights.png",
   )
   st.markdown("""
    The **HRBA Prikazi** stranica je prostor za pregled prethodno sačuvanih AAAQ analiza.

    #### Šta vidite ovde:
    - **Tabela sačuvanih opravdanja** — Struktuirani pregled svih sačuvanih HRBA opravdanja
    - **Filteri i grupisanje** — Omogućava sužavanje rezultata po dokumentu ili kontekstu analize
    - **Sirovi unosi** — Puni sačuvani podaci za reviziju, izvoz ili ručnu inspekciju

    #### Šta predstavlja:
    - Svaki red odgovara jednom sačuvanom zapisu analize prethodno pohranjenom iz HRBA match workflow-a
    - Ova stranica ne generiše nove analize; čita istorijske zapise iz skladišta

    #### Kada koristiti:
    - Za pregled prethodno generisanih analiza zasnovanih na ljudskim pravima
    - Za poređenje kvaliteta opravdanja između dokumenata
    - Za reviziju sačuvanih dokaza koji podržavaju HRBA nalaze
    """)

# ──────────────────────────────────────────────────────────────────────────
# Developer & Admin
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🛠️ Developer & Admin — Setup, Env vars, Troubleshooting", expanded=False):
   render_help_screenshot(
      "Developer & Admin",
      "Developer and admin stranica sa okruženjem, održavanjem i alatima za rešavanje problema.",
      "developer_admin.png",
      "Developer_Admin.png",
      "page_admin.png",
   )
   st.markdown("""
      Ovaj odeljak pokriva promenljive okruženja, uobičajene administrativne zadatke i korake za rešavanje problema.

      Promenljive okruženja (važno):
      - `DATABASE_URL`: puna PostgreSQL konekcija. Ako nije prisutna, koristi se `DATABASE_PATH` (SQLite).
      - `DATABASE_PATH`: putanja do rezervne SQLite baze podataka (podrazumevano `./data/sipmt.db`).
      - `FORCE_POSTGRES`: ako je postavljeno na `1`, forsira korišćenje `DATABASE_URL` čak i kada pokazuje na localhost.
      - `SEMANTIC_LLM_PROVIDER`: `gemini` ili `ollama`.
      - `GEMINI_API_KEY`: obavezno kada je `SEMANTIC_LLM_PROVIDER=gemini`.
      - `OLLAMA_BASE_URL`: lokalni Ollama endpoint (podrazumevano `http://localhost:11434`).
      - `OLLAMA_MODEL`: ime Ollama modela (npr. `qwen2.5:14b-instruct`).
      - `OLLAMA_TIMEOUT`: HTTP timeout za Ollama zahteve (sekunde). Podrazumevano 120.
      - `ENABLE_GEOCODING`: `true`/`false` za omogućavanje geokodiranja izvučenih lokacija.

      Uobičajeni administrativni zadaci:
      - Inicijalizacija baze podataka i direktorijuma:
         ```bash
         python setup.py
         ```
      - Migracija postojećih SQLite demo podataka u Postgres:
         ```bash
         python scripts/migrate_sqlite_to_postgres.py --sqlite-path ./data/sipmt.db --postgres-url <YOUR_URL>
         ```
      - Preuzimanje Ollama modela (lokalna mašina):
         ```bash
         ollama pull qwen2.5:14b-instruct
         ```

      Koraci za rešavanje problema:
      - Aplikacija ne može da se pokrene: pokrenite `bash scripts/pre_deploy_check.sh` da locirate sintaksne ili konfiguracione probleme.
      - Ollama nedostupan: proverite `OLLAMA_BASE_URL`, pokušajte `curl http://localhost:11434/`.
      - Spora semantička analiza: povećajte `OLLAMA_TIMEOUT`, zagrejte model malim zahtevom ili izaberite manji model.
      - Nedostaje izvučeni tekst: proverite OCR podešavanja i ponovo pokrenite pipeline za ekstrakciju dokumenata.

      Logs i dijagnostika:
      - Proverite `logs/` za nedavne logove aplikacije.
      - Streamlit konzola prikazuje greške pri pokretanju; konsultujte server logove za stack trace.

      Bezbednost i tajne:
      - Nikada ne komitujte tajne (API ključeve, lozinke za bazu) u git. Koristite platformske tajne ili `.env` fajl isključen iz VCS.
      - Rotirajte API ključeve ako su slučajno otkriveni.
      """)

# ──────────────────────────────────────────────────────────────────────────
# SAVETI I NAJBOLE PRAKSE
# ──────────────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("💡 **Savet i najbolje prakse**"):
    st.markdown("""
    #### Saveti za učitavanje dokumenata
    - **Kvalitet je važan**: Osigurajte da skenirani PDF-ovi imaju dobru rezoluciju (≥200 DPI) za bolje izdvajanje teksta
    - **Nazivanje fajlova**: Koristite opisne nazive (npr. `Policy_2024_Social_Inclusion.pdf`) radi lakšeg praćenja
    - **Organizujte po tipu**: Kategorizujte dokumente ispravno — ovo pomaže u podudaranju šablona
    - **Kontrola verzija**: Učitajte verzirane dokumente (v1, v2) da pratite evoluciju

    #### Dizajn šablona
    - **Budite specifični**: Detaljniji opisi polja pomažu matcher-u da pronađe vrednosti
    - **Koristite dosledna imena**: Slična polja u različitim šablonima treba da imaju slična imena
    - **Postavite realne prioritete**: Obeležite zaista obavezna polja, ostala držite kao opcionalna
    - **Testirajte prvo**: Kreirajte šablon i testirajte sa 1–2 dokumenta pre obrade u seriji

    #### Generisanje izveštaja
    - **Pregledajte polja sa niskim poverenjem**: Uvek proverite izdvojene podatke sa <70% poverenja
    - **Izvori dokumenata**: Vodite evidenciju o tome koji dokumenti su korišćeni za svaki izveštaj
    - **Redovno izvozite**: Sačuvajte izveštaje kao CSV/JSON za rezervne kopije i integraciju sa drugim alatima

    #### Analiza usklađenosti
    - **Pročitajte preporuke**: AI-generisane praznine često sadrže primenljive poboljšanja
    - **Proverite reference**: Verifikujte da su spoljašnji linkovi u preporukama tačni
    - **Pratite promene**: Ponovo pokrenite analizu nakon ažuriranja dokumenata da biste prikazali napredak
    - **Koristite istoriju verzija**: Pregledajte kako se referentni šabloni razvijaju tokom vremena

    #### Saveti za performanse
    - **Obrada u serijama**: Učitajte više dokumenata odjednom radi efikasnosti
    - **Local Ollama**: Koristite Ollama umesto Gemini za bržu, offline analizu
    - **Onemogućite geokodiranje**: Isključite ako vam nije potrebno mapiranje lokacija (brža obrada)
    - **Očistite stare podatke**: Arhivirajte ili obrišite dokumente koje više ne analizirate

    #### Greške i rešavanje problema
    - **Upload ne uspeva**: Osigurajte da je fajl <20 MB i u PDF/DOCX/XLSX formatu
    - **Nema izvučenog teksta**: Koristite dugme "Ponovo obradi" na stranici Dokumenti
    - **Analiza usklađenosti spora**: Proverite internet konekciju (za Gemini) ili status Ollama servisa
    - **Mapa ne prikazuje lokacije**: Osigurajte da su dokumenti kategorizovani kao "Politike"
    """)

st.markdown("---")
st.markdown("""
#### 📞 Trebate dodatnu pomoć?
- **Proverite bočnu traku** — Navigacija i brzi saveti na svakoj stranici
- **Tooltipovi** — Mnogi UI elementi imaju kontekstualnu pomoć pri prelasku mišem
- **Prijavite probleme** — Kontaktirajte svog sistem administratora sa porukama o greškama

---
*Last updated: March 2026 | SIPMT v1.0*
""")

render_page_disclaimer()
