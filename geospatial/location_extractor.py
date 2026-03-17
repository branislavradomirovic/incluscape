import logging
import re
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Common patterns found in social inclusion documents
_LOCATION_PATTERNS = [
    r"\bMunicipality\s+of\s+([A-Z][a-zA-Z\s]+)",
    r"\bCity\s+of\s+([A-Z][a-zA-Z\s]+)",
    r"\bVillage\s+(?:of\s+)?([A-Z][a-zA-Z\s]+)",
    r"\bDistrict\s+(?:of\s+)?([A-Z][a-zA-Z\s]+)",
    r"\bRegion\s+(?:of\s+)?([A-Z][a-zA-Z\s]+)",
    r"\bSettlement\s+(?:of\s+)?([A-Z][a-zA-Z\s]+)",
]


class LocationExtractor:
    """Extract place names from document text."""

    def extract_from_text(self, text: str, document_id: int = 0) -> List[Dict]:
        locations = []
        seen: set[str] = set()

        # Rule-based patterns
        for pattern in _LOCATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                place = match.group(1).strip().rstrip(".,;")
                if place and place not in seen:
                    seen.add(place)
                    start = max(0, match.start() - 80)
                    end = min(len(text), match.end() + 80)
                    locations.append({
                        "document_id": document_id,
                        "place_name": place,
                        "location_type": self._infer_type(match.group(0)),
                        "context": text[start:end].strip(),
                        "latitude": None,
                        "longitude": None,
                        "geocoded": 0,
                    })

        # spaCy GPE / LOC entities as a fallback
        nlp_locations = self._extract_nlp(text, document_id)
        for loc in nlp_locations:
            if loc["place_name"] not in seen:
                seen.add(loc["place_name"])
                locations.append(loc)

        return locations

    def _extract_nlp(self, text: str, document_id: int) -> List[Dict]:
        results = []
        try:
            import spacy
            from config import Config
            nlp = spacy.load(Config.SPACY_MODEL)
            doc = nlp(text[:50_000])
            for ent in doc.ents:
                if ent.label_ in ("GPE", "LOC", "FAC"):
                    results.append({
                        "document_id": document_id,
                        "place_name": ent.text.strip(),
                        "location_type": "general",
                        "context": text[max(0, ent.start_char-60): ent.end_char+60],
                        "latitude": None,
                        "longitude": None,
                        "geocoded": 0,
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
