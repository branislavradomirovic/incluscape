"""
Gemini-powered semantic analysis for INCLUSCAPE.

Wraps google-generativeai to provide:
  - classify_document()   — detect governing body + category from text
  - compare_with_template()  — compliance check against a reference template
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_CLASSIFY_PROMPT = """\
You are an expert in international governance, social inclusion, and policy analysis.

Analyse the document text below and classify it.

Respond ONLY with valid JSON — no markdown fences, no extra text — using this exact schema:
{{
  "body": "<one of: UN | UNESCO | EU | World Bank | OECD | National | Other>",
  "category": "<one of: Policies | Reports | Questionnaire | Instructions | Forms | Monitoring | Guideline | Resolution | Directive | Other>",
  "topic": "<short topic phrase>",
  "social_inclusion_aspects": ["<aspect 1>", "<aspect 2>"],
  "confidence": <float 0.0-1.0>,
  "reasoning": "<one sentence explanation>"
}}

Document text (first 3 000 characters):
{text}
"""

_COMPARE_PROMPT = """\
You are an expert in international governance, social inclusion, and policy analysis.

Compare the USER DOCUMENT against the REFERENCE TEMPLATE and produce a structured compliance report.

REFERENCE TEMPLATE
Body: {body}
Category: {category}
Name: {template_name}
Description: {template_description}

Expected key sections:
{key_sections}

Required elements / criteria:
{key_requirements}

USER DOCUMENT TEXT (first 4 000 characters):
{document_text}

Respond ONLY with valid JSON — no markdown fences, no extra text — using this exact schema:
{{
  "compliance_score": <float 0.0-1.0>,
  "present_elements": ["<element found>"],
  "missing_elements": ["<required element absent>"],
  "partial_elements": ["<element partially addressed>"],
  "strengths": ["<what the document does well>"],
  "gaps": ["<what is missing or insufficient>"],
  "recommendations": ["<specific actionable improvement>"],
  "summary": "<2-3 sentence overall assessment>"
}}
"""


class GeminiSemanticAnalyzer:
    """Wraps Google Gemini for document classification and compliance analysis."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        from config import Config
        self._api_key = api_key or Config.GEMINI_API_KEY
        self._model_name = model or Config.GEMINI_MODEL
        self._model = None  # lazy-init

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def provider(self) -> str:
        return "gemini"

    # ------------------------------------------------------------------
    def _get_model(self):
        if self._model is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._model = genai.GenerativeModel(self._model_name)
            except Exception as exc:
                logger.error("Failed to initialise Gemini model: %s", exc)
                raise
        return self._model

    def _call(self, prompt: str) -> Dict[str, Any]:
        """Send a prompt and parse the JSON response."""
        model = self._get_model()
        response = model.generate_content(prompt)
        raw = response.text.strip()
        # Strip accidental markdown fences if the model adds them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)

    # ------------------------------------------------------------------
    def classify_document(self, text: str) -> Dict[str, Any]:
        """
        Classify a document by governing body and category.

        Returns a dict with keys:
            body, category, topic, social_inclusion_aspects, confidence, reasoning
        On failure returns {"error": ..., "body": "Other", "category": "Other", "confidence": 0.0}
        """
        try:
            prompt = _CLASSIFY_PROMPT.format(text=text[:3000])
            result = self._call(prompt)
            logger.info(
                "Document classified as %s / %s (confidence=%.2f)",
                result.get("body"), result.get("category"), result.get("confidence", 0),
            )
            return result
        except Exception as exc:
            logger.error("classify_document failed: %s", exc)
            return {
                "error": str(exc),
                "body": "Other",
                "category": "Other",
                "confidence": 0.0,
            }

    def compare_with_template(
        self,
        document_text: str,
        template: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Compare document text against a reference template dict.

        Returns a dict with keys:
            compliance_score, present_elements, missing_elements, partial_elements,
            strengths, gaps, recommendations, summary
        On failure returns {"error": ..., "compliance_score": 0.0}
        """
        try:
            key_sections = "\n".join(
                f"  - {s}" for s in template.get("key_sections", [])
            )
            key_requirements = "\n".join(
                f"  - {r}" for r in template.get("key_requirements", [])
            )
            prompt = _COMPARE_PROMPT.format(
                body=template.get("body", ""),
                category=template.get("category", ""),
                template_name=template.get("name", ""),
                template_description=template.get("description", ""),
                key_sections=key_sections,
                key_requirements=key_requirements,
                document_text=document_text[:4000],
            )
            result = self._call(prompt)
            logger.info(
                "Compliance score for '%s': %.2f",
                template.get("name"), result.get("compliance_score", 0),
            )
            return result
        except Exception as exc:
            logger.error("compare_with_template failed: %s", exc)
            return {"error": str(exc), "compliance_score": 0.0}
