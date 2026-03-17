import re
from difflib import SequenceMatcher
from typing import Dict, List, Tuple


class FuzzyMatcher:
    """Match template field labels/hints against segments of extracted text."""

    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold

    # ------------------------------------------------------------------
    def find_best_match(
        self, query: str, candidates: List[str]
    ) -> Tuple[str, float]:
        """Return (best_candidate, score) — score in [0, 1]."""
        best, best_score = "", 0.0
        q = query.lower()
        for candidate in candidates:
            score = self.similarity(q, candidate.lower())
            if score > best_score:
                best_score = score
                best = candidate
        return best, best_score

    def similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

    # ------------------------------------------------------------------
    def extract_field_value(
        self,
        field_label: str,
        extraction_hint: str,
        text: str,
        field_type: str = "text",
    ) -> Dict:
        """
        Search `text` for the best matching value for a template field.

        Returns:
            { value: str, confidence: float, context: str }
        """
        hints = [h.strip() for h in (extraction_hint or field_label).split(",") if h.strip()]
        sentences = [s.strip() for s in re.split(r"(?<=[.!\n])\s+", text) if s.strip()]

        best_sentence, best_score = self.find_best_match(
            " ".join(hints), sentences
        )

        if best_score < self.threshold:
            return {"value": None, "confidence": best_score, "context": ""}

        value = self._extract_value_from_sentence(best_sentence, hints, field_type)
        return {
            "value": value,
            "confidence": best_score,
            "context": best_sentence,
        }

    # ------------------------------------------------------------------
    def _extract_value_from_sentence(
        self, sentence: str, hints: List[str], field_type: str
    ) -> str:
        """Naive value extraction: strip hint keywords, return remainder."""
        result = sentence
        for hint in hints:
            result = re.sub(re.escape(hint), "", result, flags=re.IGNORECASE)
        result = re.sub(r"^[\s:–\-]+", "", result).strip()
        if field_type == "date":
            date_match = re.search(
                r"\b\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}\b|\b\d{4}\b", result
            )
            if date_match:
                return date_match.group()
        if field_type == "number":
            num_match = re.search(r"[\d,\.]+", result)
            if num_match:
                return num_match.group()
        return result or sentence
