import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)

_NAME_TOKEN = r"[A-Z\u0160\u0110\u010c\u0106\u017d][a-zA-Z\u0161\u0111\u010d\u0107\u017eA-Z\u0160\u0110\u010c\u0106\u017d'.-]*"
_NAME_PHRASE = rf"{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{0,3}}"

_LOCATION_PATTERNS = [
    ("municipality", rf"(?i:\bMunicipality\s+of)\s+({_NAME_PHRASE})"),
    ("city", rf"(?i:\bCity\s+of)\s+({_NAME_PHRASE})"),
    ("village", rf"(?i:\bVillage(?:\s+of)?)\s+({_NAME_PHRASE})"),
    ("district", rf"(?i:\bDistrict(?:\s+of)?)\s+({_NAME_PHRASE})"),
    ("region", rf"(?i:\bRegion(?:\s+of)?)\s+({_NAME_PHRASE})"),
    ("general", rf"(?i:\bSettlement(?:\s+of)?)\s+({_NAME_PHRASE})"),
    ("city", rf"(?i:\bGrad(?:a|u|om)?)\s+({_NAME_PHRASE})"),
    ("municipality", rf"(?i:\bOp(?:s|\u0161)tin(?:a|e|i|u|om)?)\s+({_NAME_PHRASE})"),
    ("district", rf"(?i:\bOkrug(?:a|u|om)?)\s+({_NAME_PHRASE})"),
    ("region", rf"(?i:\bRegion(?:a|u|om)?)\s+({_NAME_PHRASE})"),
    ("village", rf"(?i:\bSelo)\s+({_NAME_PHRASE})"),
    ("general", rf"(?i:\bNaselj(?:e|a|u))\s+({_NAME_PHRASE})"),
]

_KNOWN_PLACE_ALIASES = {
    "Srbija": [
        "Republika Srbija",
        "Republike Srbije",
        "Srbija",
        "Srbije",
        "Srbiji",
        "Srbiju",
    ],
    "Beograd": ["Beograd", "Beograda", "Beogradu"],
    "Novi Sad": ["Novi Sad", "Novog Sada", "Novom Sadu"],
    "Nis": ["Nis", "Ni\u0161", "Ni\u0161a", "Ni\u0161u"],
    "Kragujevac": ["Kragujevac", "Kragujevca", "Kragujevcu"],
    "Subotica": ["Subotica", "Subotice", "Subotici"],
    "Novi Pazar": ["Novi Pazar", "Novog Pazara", "Novom Pazaru"],
    "Leskovac": ["Leskovac", "Leskovca", "Leskovcu"],
    "Vranje": ["Vranje", "Vranja", "Vranju"],
    "Pirot": ["Pirot", "Pirota", "Pirotu"],
    "Zemun": ["Zemun", "Zemuna", "Zemunu"],
    "Vojvodina": ["Vojvodina", "Vojvodine", "Vojvodini"],
    "Kosovo": ["Kosovo", "Kosova", "Kosovu"],
    "Zagreb": ["Zagreb", "Zagreba", "Zagrebu"],
    "Cazma": ["Cazma", "\u010cazma", "\u010cazme", "\u010cazmi"],
    "Daruvar": ["Daruvar", "Daruvara", "Daruvaru"],
    "Medjimurje": [
        "Medjimurje",
        "Me\u0111imurje",
        "Medjimurska zupanija",
        "Me\u0111imurska \u017eupanija",
    ],
    "Varazdin": ["Varazdin", "Vara\u017edin", "Vara\u017edina", "Vara\u017edinu"],
    "Osijek": ["Osijek", "Osijeka", "Osijeku"],
    "Rijeka": ["Rijeka", "Rijeke", "Rijeci", "Rijeci"],
    "Split": ["Split", "Splita", "Splitu"],
    "Crna Gora": ["Crna Gora", "Crne Gore", "Crnoj Gori"],
    "Bosna i Hercegovina": [
        "Bosna i Hercegovina",
        "Bosne i Hercegovine",
        "Bosni i Hercegovini",
    ],
    "Hrvatska": ["Hrvatska", "Hrvatske", "Hrvatskoj"],
    "Severna Makedonija": [
        "Severna Makedonija",
        "Severne Makedonije",
        "Severnoj Makedoniji",
        "Makedonija",
        "Makedonije",
    ],
    "Rumunija": ["Rumunija", "Rumunije", "Rumuniji"],
    "Bugarska": ["Bugarska", "Bugarske", "Bugarskoj"],
    "Madarska": ["Madarska", "Ma\u0111arska", "Madarske", "Ma\u0111arske"],
}

_DISALLOWED_PLACE_TOKENS = {
    "autonomna",
    "baza",
    "broj",
    "do",
    "izvestaj",
    "izvjestaj",
    "jls",
    "pokrajina",
    "program",
    "roma",
    "sros",
    "strategija",
}

class LocationExtractor:
    """Extract place names from document text."""

    def __init__(self):
        self._nlp = None
        self._model_error = ""

    def extract_from_text(self, text: str, document_id: int = 0) -> List[Dict]:
        locations = []
        seen: set[str] = set()

        # Rule-based patterns
        for location_type, pattern in _LOCATION_PATTERNS:
            for match in re.finditer(pattern, text):
                place = match.group(1).strip().rstrip(".,;:)")
                self._append_location(
                    locations,
                    seen,
                    document_id=document_id,
                    place_name=place,
                    location_type=location_type or self._infer_type(match.group(0)),
                    text=text,
                    start=match.start(1),
                    end=match.end(1),
                )

        for canonical_name, aliases in _KNOWN_PLACE_ALIASES.items():
            for alias in aliases:
                pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    self._append_location(
                        locations,
                        seen,
                        document_id=document_id,
                        place_name=canonical_name,
                        location_type="general",
                        text=text,
                        start=match.start(),
                        end=match.end(),
                    )

        # spaCy GPE / LOC entities as a fallback
        nlp_locations = self._extract_nlp(text, document_id)
        for loc in nlp_locations:
            self._append_location(
                locations,
                seen,
                document_id=document_id,
                place_name=loc["place_name"],
                location_type=loc.get("location_type", "general"),
                text=text,
                start=loc.get("char_start", 0),
                end=loc.get("char_end", 0),
            )

        return locations

    def get_diagnostics(self) -> Dict[str, str]:
        nlp = self._load_model()
        return {
            "spacy_model": self._configured_model_name(),
            "spacy_ready": bool(nlp),
            "spacy_error": self._model_error,
            "rule_patterns": str(len(_LOCATION_PATTERNS)),
            "known_places": str(len(_KNOWN_PLACE_ALIASES)),
        }

    def _configured_model_name(self) -> str:
        from config import Config

        return Config.SPACY_MODEL

    @staticmethod
    def _normalise_key(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip().lower()

    def _append_location(
        self,
        locations: List[Dict],
        seen: set,
        document_id: int,
        place_name: str,
        location_type: str,
        text: str,
        start: int,
        end: int,
    ) -> None:
        clean_name = self._canonicalize_place_name(place_name)
        if len(clean_name) < 2:
            return
        if not self._is_plausible_place_name(clean_name):
            return
        dedupe_key = self._normalise_key(clean_name)
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        context_start = max(0, start - 80)
        context_end = min(len(text), max(end, start) + 80)
        locations.append({
            "document_id": document_id,
            "place_name": clean_name,
            "location_type": location_type or "general",
            "context": text[context_start:context_end].strip(),
            "latitude": None,
            "longitude": None,
            "geocoded": 0,
        })

    def _canonicalize_place_name(self, value: str) -> str:
        clean_name = re.sub(r"\s+", " ", str(value or "")).strip().rstrip(".,;:")
        normalised = self._normalise_key(clean_name)
        for canonical_name, aliases in _KNOWN_PLACE_ALIASES.items():
            if normalised == self._normalise_key(canonical_name):
                return canonical_name
            for alias in aliases:
                if normalised == self._normalise_key(alias):
                    return canonical_name
        return clean_name

    def _is_plausible_place_name(self, value: str) -> bool:
        if any(ch in value for ch in ".|/"):
            return False
        words = value.split()
        if len(words) > 3:
            return False
        lowered_words = {word.lower() for word in words}
        if lowered_words & _DISALLOWED_PLACE_TOKENS:
            return False
        return True

    def _load_model(self):
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load(self._configured_model_name())
                self._model_error = ""
            except Exception as exc:
                self._model_error = str(exc)
                logger.warning("Could not load spaCy model for location extraction: %s", exc)
                self._nlp = False
        return self._nlp

    def _extract_nlp(self, text: str, document_id: int) -> List[Dict]:
        results = []
        nlp = self._load_model()
        if not nlp:
            return results

        try:
            doc = nlp(text[:50_000])
            for ent in doc.ents:
                if ent.label_ in ("GPE", "LOC", "FAC"):
                    results.append({
                        "document_id": document_id,
                        "place_name": ent.text.strip(),
                        "location_type": "general",
                        "char_start": ent.start_char,
                        "char_end": ent.end_char,
                    })
        except Exception as exc:
            logger.debug("NLP location extraction skipped: %s", exc)
        return results

    @staticmethod
    def _infer_type(matched_phrase: str) -> str:
        phrase = matched_phrase.lower()
        if "municipality" in phrase:
            return "municipality"
        if "city" in phrase:
            return "city"
        if "village" in phrase:
            return "village"
        if "district" in phrase:
            return "district"
        if "region" in phrase:
            return "region"
        return "general"
