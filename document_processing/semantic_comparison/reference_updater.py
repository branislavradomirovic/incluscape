"""
Reference template source refresher and versioner.

Checks official source URLs, computes source hash, and creates a new active
reference template version when source content changes.
"""

import hashlib
import re
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional


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

    def _fetch_source_hash(self, url: str) -> str:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "INCLUSCAPE/1.0 (+reference-refresh)"},
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        normalized = self._normalise_text(raw)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _bump_version(version: Optional[str]) -> str:
        if not version:
            return "1.0"
        try:
            major, minor = version.split(".", 1)
            return f"{major}.{int(minor) + 1}"
        except Exception:
            return f"{version}.1"

    def refresh_template(self, template: Dict) -> Dict:
        out = {
            "template_id": template["id"],
            "name": template.get("name", ""),
            "body": template.get("body", ""),
            "updated": False,
            "error": "",
        }

        source_url = (template.get("source_url") or "").strip()
        if not source_url:
            out["error"] = "No source_url configured"
            return out

        try:
            new_hash = self._fetch_source_hash(source_url)
        except Exception as exc:
            out["error"] = str(exc)
            return out

        current_hash = (template.get("source_hash") or "").strip()
        now_iso = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        if current_hash and current_hash == new_hash:
            self.db.update(
                "reference_templates",
                {
                    "source_last_checked": now_iso,
                },
                "id = ?",
                (template["id"],),
            )
            out["status"] = "unchanged"
            return out

        if not current_hash:
            self.db.update(
                "reference_templates",
                {
                    "source_hash": new_hash,
                    "source_last_checked": now_iso,
                    "effective_date": now_iso,
                },
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
                "description": template.get("description"),
                "source_url": source_url,
                "source_hash": new_hash,
                "source_last_checked": now_iso,
                "effective_date": now_iso,
                "supersedes_template_id": template["id"],
                "change_summary": "Detected upstream source content change during refresh.",
                "file_path": template.get("file_path"),
                "key_sections": template.get("key_sections"),
                "key_requirements": template.get("key_requirements"),
                "keywords": template.get("keywords"),
                "version": self._bump_version(template.get("version")),
                "is_active": 1,
            },
        )

        out["updated"] = True
        out["status"] = "new_version_created"
        out["new_template_id"] = new_id
        return out

    def refresh_bodies(self, bodies: Optional[List[str]] = None) -> List[Dict]:
        bodies = bodies or ["UNESCO", "EU"]
        placeholders = ", ".join("?" for _ in bodies)
        rows = self.db.fetchall(
            f"SELECT * FROM reference_templates WHERE is_active = 1 AND body IN ({placeholders}) ORDER BY body, name",
            tuple(bodies),
        )
        return [self.refresh_template(row) for row in rows]
