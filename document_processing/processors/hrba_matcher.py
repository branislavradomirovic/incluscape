import spacy
from typing import Dict, List
from config import Config


# Lazy-load the spaCy model specified in config to avoid heavy import at module load.
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        model = getattr(Config, "SPACY_MODEL", "en_core_web_sm")
        _nlp = spacy.load(model)
    return _nlp


class HRBAMatcher:
    """Matches document segments to Human Rights Based Approach (HRBA) indicators.

    Hybrid approach: semantic similarity using spaCy plus keyword anchoring.
    """

    INDICATORS = {
        "Availability": ["infrastructure", "supply", "staffing", "facilities", "coverage"],
        "Accessibility": ["physical access", "affordability", "non-discrimination", "information"],
        "Acceptability": ["cultural relevance", "ethics", "gender sensitivity", "language"],
        "Quality": ["standards", "safety", "scientific approval", "efficiency"],
    }

    def __init__(self):
        nlp = _get_nlp()
        self.indicator_docs = {
            cat: [nlp(keyword) for keyword in keywords]
            for cat, keywords in self.INDICATORS.items()
        }

    def analyze_segment(self, text: str) -> Dict[str, float]:
        """Calculates matching scores for a text segment against HRBA indicators."""
        nlp = _get_nlp()
        doc = nlp(text.lower())
        results: Dict[str, float] = {}

        for category, keywords in self.indicator_docs.items():
            # semantic similarity: take max similarity to any keyword
            try:
                score = max([doc.similarity(kw) for kw in keywords]) if doc.vector_norm else 0
            except Exception:
                score = 0

            # simple keyword anchor boost (if exact keyword present)
            lower = text.lower()
            boost = 0.15 if any(k.lower() in lower for k in [t.text for t in keywords]) else 0
            results[category] = round(min(score + boost, 1.0), 3)

        return results

    def extract_hrba_insights(self, document_text: str) -> List[Dict]:
        """Processes full text to find high-relevance HRBA passages."""
        nlp = _get_nlp()
        doc = nlp(document_text)
        insights: List[Dict] = []

        for sent in doc.sents:
            scores = self.analyze_segment(sent.text)
            top_category = max(scores, key=scores.get)
            if scores[top_category] > 0.6:
                insights.append({
                    "text": sent.text.strip(),
                    "category": top_category,
                    "score": scores[top_category],
                })

        return insights
