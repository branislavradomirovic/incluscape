"""
Reference template source refresher and versioner.

Checks official source URLs, computes source hash, and creates a new active
reference template version when source content changes.
"""

import hashlib
import json
import re
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional


_GEMINI_TEMPLATE_REFRESH_PROMPT = """\
You are an expert policy analyst. Extract a compact compliance reference template from source text.

Reference metadata:
Body: {body}
Category: {category}
Name: {name}

Source text:
{source_text}

Return ONLY valid JSON with this exact schema:
{{
    "description": "<1-2 sentence concise description>",
    "key_sections": ["<section 1>", "<section 2>"],
    "key_requirements": ["<requirement 1>", "<requirement 2>"],
    "keywords": ["<keyword 1>", "<keyword 2>"]
}}

Constraints:
- key_sections: 5 to 12 items
- key_requirements: 8 to 20 items
- keywords: 10 to 25 items
- items must be short, specific, and deduplicated
"""


class ReferenceTemplateUpdater:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _normalise_text(raw: str) -> str:
        text = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _fetch_source_payload(self, url: str) -> Dict[str, str]:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SIPMT/1.0 (+reference-refresh)"},
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        normalized = self._normalise_text(raw)
        return {
            "normalized_text": normalized,
            "hash": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        }

    @staticmethod
    def _dedupe_keep_order(items: List[str]) -> List[str]:
        seen = set()
        out: List[str] = []
        for item in items:
            s = str(item).strip()
            if not s:
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
        return out

    def _parse_llm_enrichment_json(self, raw: str) -> Dict:
        """Parse JSON from LLM response, stripping markdown fences if present."""
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            if len(parts) > 1:
                raw = parts[1]
            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:]
            raw = raw.strip()
        # Recover first JSON object if model prefixed with explanation text
        if not raw.startswith("{"):
            start = raw.find("{")
            if start != -1:
                raw = raw[start:]
        return json.loads(raw)

    def _build_enrichment_result(self, parsed: Dict) -> Dict:
        key_sections = self._dedupe_keep_order(parsed.get("key_sections") or [])[:12]
        key_requirements = self._dedupe_keep_order(parsed.get("key_requirements") or [])[:20]
        keywords = self._dedupe_keep_order(parsed.get("keywords") or [])[:25]
        return {
            "ok": True,
            "description": str(parsed.get("description") or "").strip(),
            "key_sections": key_sections,
            "key_requirements": key_requirements,
            "keywords": keywords,
        }

    def _ollama_enrich_template(self, template: Dict, source_text: str) -> Dict:
        from config import Config

        try:
            base_url = (Config.OLLAMA_BASE_URL or "http://localhost:11434").rstrip("/")
            model = Config.OLLAMA_MODEL or "llama3"
            prompt = _GEMINI_TEMPLATE_REFRESH_PROMPT.format(
                body=template.get("body", "Other"),
                category=template.get("category", "Other"),
                name=template.get("name", ""),
                source_text=(source_text or "")[:12000],
            )
            payload = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 1024},
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            raw = (data.get("response") or "").strip()
            parsed = self._parse_llm_enrichment_json(raw)
            return self._build_enrichment_result(parsed)
        except Exception as exc:
            return {"ok": False, "error": f"Ollama enrichment failed: {exc}"}

    def _gemini_enrich_template(self, template: Dict, source_text: str) -> Dict:
        from config import Config

        api_key = (Config.GEMINI_API_KEY or "").strip()
        if not api_key:
            return {
                "ok": False,
                "error": "GEMINI_API_KEY is missing; Gemini enrichment skipped.",
            }

        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(Config.GEMINI_MODEL)
            prompt = _GEMINI_TEMPLATE_REFRESH_PROMPT.format(
                body=template.get("body", "Other"),
                category=template.get("category", "Other"),
                name=template.get("name", ""),
                source_text=(source_text or "")[:12000],
            )
            response = model.generate_content(prompt)
            raw = (response.text or "").strip()
            parsed = self._parse_llm_enrichment_json(raw)
            return self._build_enrichment_result(parsed)
        except Exception as exc:
            return {"ok": False, "error": f"Gemini enrichment failed: {exc}"}

    def _llm_enrich_template(self, template: Dict, source_text: str) -> Dict:
        """Dispatch to Ollama or Gemini based on SEMANTIC_LLM_PROVIDER config."""
        from config import Config

        provider = (Config.SEMANTIC_LLM_PROVIDER or "ollama").strip().lower()
        if provider == "gemini":
            return self._gemini_enrich_template(template, source_text)
        return self._ollama_enrich_template(template, source_text)

    @staticmethod
    def _bump_version(version: Optional[str]) -> str:
        if not version:
            return "1.0"
        try:
            major, minor = version.split(".", 1)
            return f"{major}.{int(minor) + 1}"
        except Exception:
            return f"{version}.1"

    def refresh_template(self, template: Dict, use_llm: bool = False, use_gemini: bool = False) -> Dict:
        """Refresh a single reference template from its source URL.

        Args:
            use_llm:    Enrich extracted text with the configured LLM provider
                        (Ollama when SEMANTIC_LLM_PROVIDER=ollama, Gemini otherwise).
            use_gemini: Deprecated alias for use_llm — kept for backward compatibility.
        """
        enrich = use_llm or use_gemini
        out = {
            "template_id": template["id"],
            "name": template.get("name", ""),
            "body": template.get("body", ""),
            "updated": False,
            "error": "",
            "llm_enriched": False,
            # legacy key kept so existing callers reading "gemini_enriched" still work
            "gemini_enriched": False,
        }

        source_url = (template.get("source_url") or "").strip()
        if not source_url:
            out["error"] = "No source_url configured"
            return out

        try:
            source_payload = self._fetch_source_payload(source_url)
            new_hash = source_payload["hash"]
            normalized_text = source_payload["normalized_text"]
        except Exception as exc:
            out["error"] = str(exc)
            return out

        llm_enrichment = None
        if enrich:
            llm_enrichment = self._llm_enrich_template(template, normalized_text)
            if llm_enrichment.get("ok"):
                out["llm_enriched"] = True
                out["gemini_enriched"] = True  # legacy compat
            else:
                # Keep refresh functioning even if enrichment fails.
                out["llm_error"] = llm_enrichment.get("error", "LLM enrichment failed")
                out["gemini_error"] = out["llm_error"]  # legacy compat

        current_hash = (template.get("source_hash") or "").strip()
        now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if current_hash and current_hash == new_hash:
            update_payload = {
                "source_last_checked": now_iso,
            }
            if llm_enrichment and llm_enrichment.get("ok"):
                if llm_enrichment.get("description"):
                    update_payload["description"] = llm_enrichment["description"]
                update_payload["key_sections"] = json.dumps(llm_enrichment.get("key_sections") or [])
                update_payload["key_requirements"] = json.dumps(llm_enrichment.get("key_requirements") or [])
                update_payload["keywords"] = json.dumps(llm_enrichment.get("keywords") or [])
            self.db.update(
                "reference_templates",
                update_payload,
                "id = ?",
                (template["id"],),
            )
            out["status"] = "unchanged"
            return out

        if not current_hash:
            update_payload = {
                "source_hash": new_hash,
                "source_last_checked": now_iso,
                "effective_date": now_iso,
            }
            if llm_enrichment and llm_enrichment.get("ok"):
                if llm_enrichment.get("description"):
                    update_payload["description"] = llm_enrichment["description"]
                update_payload["key_sections"] = json.dumps(llm_enrichment.get("key_sections") or [])
                update_payload["key_requirements"] = json.dumps(llm_enrichment.get("key_requirements") or [])
                update_payload["keywords"] = json.dumps(llm_enrichment.get("keywords") or [])
            self.db.update(
                "reference_templates",
                update_payload,
                "id = ?",
                (template["id"],),
            )
            out["status"] = "baseline_hash_set"
            return out

        self.db.update(
            "reference_templates",
            {"is_active": 0},
            "id = ?",
            (template["id"],),
        )

        new_id = self.db.insert(
            "reference_templates",
            {
                "body": template.get("body"),
                "category": template.get("category"),
                "name": template.get("name"),
                "description": (
                    llm_enrichment.get("description")
                    if llm_enrichment and llm_enrichment.get("ok") and llm_enrichment.get("description")
                    else template.get("description")
                ),
                "source_url": source_url,
                "source_hash": new_hash,
                "source_last_checked": now_iso,
                "effective_date": now_iso,
                "supersedes_template_id": template["id"],
                "change_summary": "Detected upstream source content change during refresh.",
                "file_path": template.get("file_path"),
                "key_sections": (
                    json.dumps(llm_enrichment.get("key_sections") or [])
                    if llm_enrichment and llm_enrichment.get("ok")
                    else template.get("key_sections")
                ),
                "key_requirements": (
                    json.dumps(llm_enrichment.get("key_requirements") or [])
                    if llm_enrichment and llm_enrichment.get("ok")
                    else template.get("key_requirements")
                ),
                "keywords": (
                    json.dumps(llm_enrichment.get("keywords") or [])
                    if llm_enrichment and llm_enrichment.get("ok")
                    else template.get("keywords")
                ),
                "version": self._bump_version(template.get("version")),
                "is_active": 1,
            },
        )

        out["updated"] = True
        out["status"] = "new_version_created"
        out["new_template_id"] = new_id
        return out

    def refresh_bodies(
        self,
        bodies: Optional[List[str]] = None,
        use_llm: bool = False,
        use_gemini: bool = False,
    ) -> List[Dict]:
        """Refresh all active templates for the given bodies list.

        Args:
            bodies:     Filter to specific governing bodies (e.g. ["UN", "EU"]).
                        Pass None to refresh all.
            use_llm:    Enrich with the configured LLM provider after fetching.
            use_gemini: Deprecated alias for use_llm.
        """
        if bodies:
            placeholders = ", ".join("?" for _ in bodies)
            rows = self.db.fetchall(
                f"SELECT * FROM reference_templates WHERE is_active = 1 AND body IN ({placeholders}) ORDER BY body, category, name",
                tuple(bodies),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM reference_templates WHERE is_active = 1 ORDER BY body, category, name"
            )
        return [self.refresh_template(row, use_llm=use_llm, use_gemini=use_gemini) for row in rows]
