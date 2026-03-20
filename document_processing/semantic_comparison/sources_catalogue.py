"""
Sources catalogue manager for INCLUSCAPE reference templates.

The catalogue (reference_templates/sources_catalogue.json) is the single
source of truth for *which* official documents to track.  This module
provides helpers to:

  - load and save the catalogue file
  - sync catalogue entries into the reference_templates DB table
  - add / remove / toggle sources without touching the DB directly
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_CATALOGUE_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "reference_templates"
    / "sources_catalogue.json"
)


class SourcesCatalogue:
    def __init__(self, catalogue_path: Optional[Path] = None, db=None):
        self._path = Path(catalogue_path or _DEFAULT_CATALOGUE_PATH)
        self._db = db
        self._data: Optional[Dict] = None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> Dict:
        if self._data is None:
            if self._path.exists():
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            else:
                self._data = {"_version": "2.0", "sources": []}
        return self._data

    def _save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def reload(self) -> None:
        """Force reload from disk (discards any unsaved in-memory state)."""
        self._data = None
        self._load()

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def all_sources(self) -> List[Dict]:
        """Return all catalogue entries (enabled and disabled)."""
        return list(self._load().get("sources", []))

    def enabled_sources(self, body: Optional[str] = None) -> List[Dict]:
        """Return enabled entries, optionally filtered by governing body."""
        entries = [s for s in self.all_sources() if s.get("enabled", True) and s.get("source_url")]
        if body:
            entries = [s for s in entries if s.get("body", "").upper() == body.upper()]
        return entries

    def known_bodies(self) -> List[str]:
        """Sorted list of distinct bodies present in the catalogue."""
        bodies = {s.get("body", "Other") for s in self.all_sources()}
        return sorted(bodies)

    def find(self, source_url: str) -> Optional[Dict]:
        """Return the catalogue entry whose source_url matches (exact)."""
        for s in self.all_sources():
            if s.get("source_url") == source_url:
                return s
        return None

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def add_source(
        self,
        body: str,
        name: str,
        source_url: str,
        category: str = "Policies",
        file_hint: str = "",
        enabled: bool = True,
    ) -> Dict:
        """Add a new entry to the catalogue if it doesn't already exist."""
        existing = self.find(source_url)
        if existing:
            return existing

        self._load()
        entry = {
            "body": body,
            "category": category,
            "name": name,
            "source_url": source_url,
            "file_hint": file_hint or f"{body.lower()}/{name.lower().replace(' ', '_')[:40]}.json",
            "enabled": enabled,
        }
        self._data["sources"].append(entry)
        self._save()
        logger.info("Added source to catalogue: [%s] %s", body, name)
        return entry

    def set_enabled(self, source_url: str, enabled: bool) -> bool:
        """Enable or disable a catalogue entry. Returns True if found."""
        self._load()
        for entry in self._data["sources"]:
            if entry.get("source_url") == source_url:
                entry["enabled"] = enabled
                self._save()
                return True
        return False

    def remove_source(self, source_url: str) -> bool:
        """Remove an entry from the catalogue. Returns True if found."""
        self._load()
        before = len(self._data["sources"])
        self._data["sources"] = [
            s for s in self._data["sources"]
            if s.get("source_url") != source_url
        ]
        removed = len(self._data["sources"]) < before
        if removed:
            self._save()
        return removed

    # ------------------------------------------------------------------
    # DB sync
    # ------------------------------------------------------------------

    def sync_to_db(self, db=None) -> int:
        """
        Upsert all enabled catalogue entries into the reference_templates table.

        For entries already in the DB (matched by source_url + body + name),
        nothing is overwritten unless db.upsert_reference_template handles it.
        Returns the number of entries processed.
        """
        target_db = db or self._db
        if target_db is None:
            raise ValueError("No database provided for sync_to_db()")

        count = 0
        for entry in self.enabled_sources():
            target_db.upsert_reference_template({
                "body": entry.get("body", "Other"),
                "category": entry.get("category", "Other"),
                "name": entry.get("name", ""),
                "description": "",
                "source_url": entry.get("source_url", ""),
                "file_path": entry.get("file_hint", ""),
                "key_sections": json.dumps([]),
                "key_requirements": json.dumps([]),
                "keywords": json.dumps([]),
                "version": "1.0",
            })
            count += 1
        logger.info("Synced %d catalogue entries to DB", count)
        return count
