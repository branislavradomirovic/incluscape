"""
Ollama-powered semantic analysis for INCLUSCAPE.

Uses local Ollama HTTP API to provide:
  - classify_document()
  - compare_with_template()
"""

import json
import logging
import re
import socket
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _extract_first_json_object(text: str) -> str:
    """Extract the first balanced JSON object from model text output."""
    if not text:
        return ""

    start = text.find("{")
    if start == -1:
        return ""

    depth = 0
    in_string = False
    escape = False

    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
            continue
        if ch == "}":
            depth -= 1
            if depth == 0:
                return text[start: idx + 1]

    return ""

_CLASSIFY_PROMPT = """\
You are an expert in international governance, social inclusion, and policy analysis.

Analyse the document text below and classify it.

Respond ONLY with valid JSON - no markdown fences, no extra text - using this exact schema:
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

Respond ONLY with valid JSON - no markdown fences, no extra text - using this exact schema:
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


class OllamaSemanticAnalyzer:
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        from config import Config

        self._base_url = (base_url or Config.OLLAMA_BASE_URL).rstrip("/")
        self._model_name = model or Config.OLLAMA_MODEL
        self._timeout_sec = Config.OLLAMA_TIMEOUT_SEC
        self._keep_alive = Config.OLLAMA_KEEP_ALIVE
        self._num_ctx = Config.OLLAMA_NUM_CTX
        self._num_thread = Config.OLLAMA_NUM_THREAD
        self._num_gpu = Config.OLLAMA_NUM_GPU
        self._num_batch = Config.OLLAMA_NUM_BATCH

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def provider(self) -> str:
        return "ollama"

    def _call(self, prompt: str, num_predict: int = 1024) -> Dict[str, Any]:
        endpoint = f"{self._base_url}/api/generate"
        options = {
            "temperature": 0.1,
            "num_ctx": self._num_ctx,
            "num_predict": num_predict,
        }
        if self._num_thread is not None:
            options["num_thread"] = self._num_thread
        if self._num_gpu is not None:
            options["num_gpu"] = self._num_gpu
        if self._num_batch is not None:
            options["num_batch"] = self._num_batch

        payload = json.dumps({
            "model": self._model_name,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self._keep_alive,
            "options": options,
        }).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self._timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        raw = (data.get("response") or "").strip()
        if raw.startswith("```"):
            fence_parts = raw.split("```")
            if len(fence_parts) > 1:
                raw = fence_parts[1]
            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:]
            raw = raw.strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Some models prepend explanations and only later emit valid JSON.
            recovered = _extract_first_json_object(raw)
            if not recovered:
                recovered_match = re.search(r"\{[\s\S]*\}", raw)
                recovered = recovered_match.group(0) if recovered_match else ""
            if not recovered:
                preview = raw[:220].replace("\n", " ")
                raise ValueError(f"Model did not return valid JSON. Preview: {preview}")
            parsed = json.loads(recovered)

        if not isinstance(parsed, dict):
            raise ValueError("Model JSON output must be an object")
        return parsed

    def classify_document(self, text: str) -> Dict[str, Any]:
        try:
            result = self._call(_CLASSIFY_PROMPT.format(text=text[:3000]), num_predict=128)
            return result
        except socket.timeout:
            logger.error("ollama classify_document timed out after %ss", self._timeout_sec)
            return {
                "error": (
                    f"Ollama request timed out after {self._timeout_sec}s. "
                    "Increase OLLAMA_TIMEOUT_SEC or use a smaller/faster model."
                ),
                "body": "Other",
                "category": "Other",
                "confidence": 0.0,
            }
        except Exception as exc:
            logger.error("ollama classify_document failed: %s", exc)
            return {
                "error": str(exc),
                "body": "Other",
                "category": "Other",
                "confidence": 0.0,
            }

    def compare_with_template(self, document_text: str, template: Dict[str, Any]) -> Dict[str, Any]:
        try:
            key_sections = "\n".join(f"  - {s}" for s in template.get("key_sections", [])[:8])
            key_requirements = "\n".join(
                f"  - {r}" for r in template.get("key_requirements", [])[:15]
            )
            prompt = _COMPARE_PROMPT.format(
                body=template.get("body", ""),
                category=template.get("category", ""),
                template_name=template.get("name", ""),
                template_description=(template.get("description") or "")[:300],
                key_sections=key_sections,
                key_requirements=key_requirements,
                document_text=document_text[:2500],
            )
            return self._call(prompt, num_predict=1024)
        except socket.timeout:
            logger.error("ollama compare_with_template timed out after %ss", self._timeout_sec)
            return {
                "error": (
                    f"Ollama request timed out after {self._timeout_sec}s. "
                    "Increase OLLAMA_TIMEOUT_SEC or use a smaller/faster model."
                ),
                "compliance_score": 0.0,
            }
        except Exception as exc:
            logger.error("ollama compare_with_template failed: %s", exc)
            return {"error": str(exc), "compliance_score": 0.0}
