import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# spaCy entity types considered relevant for social inclusion analysis
RELEVANT_TYPES = {
    "GPE", "LOC", "FAC",          # Geospatial
    "ORG",                         # Organisations
    "PERSON",                      # People
    "DATE", "TIME",                # Temporal
    "LAW",                         # Legislation / policies
    "MONEY", "PERCENT", "CARDINAL",# Numeric indicators
}


class EntityRecognizer:
    """Extract named entities from text using spaCy."""

    def __init__(self):
        self._nlp = None

    def _load_model(self):
        if self._nlp is None:
            try:
                import spacy
                from config import Config
                self._nlp = spacy.load(Config.SPACY_MODEL)
            except Exception as exc:
                logger.warning("Could not load spaCy model: %s. Entity recognition disabled.", exc)
                self._nlp = False
        return self._nlp

    def recognize(self, text: str, document_id: int = 0, page_number: int = 0) -> List[Dict[str, Any]]:
        nlp = self._load_model()
        if not nlp:
            return []
        entities = []
        # Process in chunks to avoid memory issues with large documents
        chunk_size = 50_000
        for start in range(0, len(text), chunk_size):
            chunk = text[start : start + chunk_size]
            doc = nlp(chunk)
            for ent in doc.ents:
                if ent.label_ in RELEVANT_TYPES:
                    entities.append({
                        "document_id": document_id,
                        "entity_type": ent.label_,
                        "entity_text": ent.text.strip(),
                        "context": chunk[max(0, ent.start_char - 60): ent.end_char + 60],
                        "confidence": 0.85,  # spaCy doesn't expose raw confidence
                        "page_number": page_number,
                    })
        return entities
