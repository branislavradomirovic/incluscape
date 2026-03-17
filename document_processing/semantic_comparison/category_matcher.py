"""
CategoryMatcher — loads reference templates from JSON files and the database,
then finds the best match(es) for a document using the configured semantic LLM.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CategoryMatcher:
    """
    Match a user-uploaded document to the most relevant reference templates.

    Priority order for template data:
      1. Templates already seeded in the database  (db.get_reference_templates)
      2. JSON files in REFERENCE_TEMPLATES_DIR     (loaded on first call)
    """

    def __init__(self, db=None, analyzer=None):
        from config import Config
        from database.db_manager import DatabaseManager
        from document_processing.semantic_comparison.analyzer_factory import get_semantic_analyzer

        self.db = db or DatabaseManager()
        self.analyzer = analyzer or get_semantic_analyzer()
        self._templates_dir = Path(Config.REFERENCE_TEMPLATES_DIR)
        self._cached_file_templates: Optional[List[Dict]] = None

    # ------------------------------------------------------------------
    def _load_file_templates(self) -> List[Dict]:
        """Load all JSON reference templates from the file system (cached)."""
        if self._cached_file_templates is not None:
            return self._cached_file_templates

        templates: List[Dict] = []
        metadata_path = self._templates_dir / "metadata.json"

        if not metadata_path.exists():
            logger.warning("Reference templates metadata not found at %s", metadata_path)
            self._cached_file_templates = templates
            return templates

        try:
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            for entry in meta.get("templates", []):
                file_path = self._templates_dir / entry["file"]
                if file_path.exists():
                    tmpl = json.loads(file_path.read_text(encoding="utf-8"))
                    tmpl["_file_path"] = str(file_path)
                    templates.append(tmpl)
                else:
                    logger.warning("Template file not found: %s", file_path)
        except Exception as exc:
            logger.error("Error loading reference templates: %s", exc)

        self._cached_file_templates = templates
        return templates

    def seed_database(self) -> int:
        """
        Seed the database with all JSON file templates that are not yet stored.
        Returns the number of templates upserted.
        """
        count = 0
        for tmpl in self._load_file_templates():
            self.db.upsert_reference_template({
                "body": tmpl.get("body", "Other"),
                "category": tmpl.get("category", "Other"),
                "name": tmpl.get("name", ""),
                "description": tmpl.get("description", ""),
                "source_url": tmpl.get("source_url", ""),
                "file_path": tmpl.get("_file_path", ""),
                "key_sections": json.dumps(tmpl.get("key_sections", [])),
                "key_requirements": json.dumps(tmpl.get("key_requirements", [])),
                "keywords": json.dumps(tmpl.get("keywords", [])),
                "version": tmpl.get("version", "1.0"),
            })
            count += 1
        logger.info("Seeded %d reference templates into database", count)
        return count

    # ------------------------------------------------------------------
    def get_all_templates(self) -> List[Dict]:
        """Return merged list from DB first, supplemented by file templates."""
        db_templates = self.db.get_reference_templates()
        if db_templates:
            # Deserialise JSON fields
            for t in db_templates:
                for key in ("key_sections", "key_requirements", "keywords"):
                    if isinstance(t.get(key), str):
                        try:
                            t[key] = json.loads(t[key])
                        except (json.JSONDecodeError, TypeError):
                            t[key] = []
            return db_templates
        return self._load_file_templates()

    def get_templates_for(self, body: str, category: str) -> List[Dict]:
        """Return templates filtered by body and category."""
        return [
            t for t in self.get_all_templates()
            if t.get("body", "").lower() == body.lower()
            and t.get("category", "").lower() == category.lower()
        ]

    # ------------------------------------------------------------------
    def classify_and_match(self, document_text: str) -> Dict[str, Any]:
        """
        Classify a document with Gemini, then find matching reference templates.

        Returns:
            {
                "classification": { body, category, topic, confidence, ... },
                "matched_templates": [ <template dict>, ... ]
            }
        """
        classification = self.analyzer.classify_document(document_text)
        body = classification.get("body", "Other")
        category = classification.get("category", "Other")

        matched = self.get_templates_for(body, category)
        if not matched:
            # Broaden: same body, any category
            matched = [
                t for t in self.get_all_templates()
                if t.get("body", "").lower() == body.lower()
            ]
        if not matched:
            # Final fallback: same category across all bodies
            matched = [
                t for t in self.get_all_templates()
                if t.get("category", "").lower() == category.lower()
            ]

        return {
            "classification": classification,
            "matched_templates": matched,
        }
