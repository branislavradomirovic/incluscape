import json
import logging
from typing import Any, Dict, List, Optional

from database.db_manager import DatabaseManager
from .fuzzy_matcher import FuzzyMatcher

logger = logging.getLogger(__name__)


class TemplateManager:
    """Create, retrieve, and apply report templates."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()
        self.matcher = FuzzyMatcher()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def create_template(
        self,
        name: str,
        fields: List[Dict[str, Any]],
        organisation_id: int,
        description: str = "",
    ) -> int:
        template_json = json.dumps(fields, ensure_ascii=False)
        template_id = self.db.insert("report_templates", {
            "organisation_id": organisation_id,
            "name": name,
            "description": description,
            "template_json": template_json,
        })
        for order, field_def in enumerate(fields):
            self.db.insert("template_fields", {
                "template_id": template_id,
                "field_key": field_def["key"],
                "field_label": field_def.get("label", field_def["key"]),
                "field_type": field_def.get("type", "text"),
                "description": field_def.get("description", ""),
                "is_required": int(field_def.get("required", False)),
                "default_value": field_def.get("default"),
                "extraction_hint": field_def.get("hint", ""),
                "display_order": order,
            })
        logger.info("Created template '%s' (id=%d)", name, template_id)
        return template_id

    def get_template(self, template_id: int) -> Optional[Dict]:
        template = self.db.fetchone(
            "SELECT * FROM report_templates WHERE id = ?", (template_id,)
        )
        if not template:
            return None
        template["fields"] = self.db.fetchall(
            "SELECT * FROM template_fields WHERE template_id = ? ORDER BY display_order",
            (template_id,),
        )
        return template

    def list_templates(self, organisation_id: int) -> List[Dict]:
        return self.db.fetchall(
            "SELECT id, name, description, version, created_at "
            "FROM report_templates WHERE organisation_id = ? AND is_active = 1",
            (organisation_id,),
        )

    # ------------------------------------------------------------------
    # Filling
    # ------------------------------------------------------------------
    def fill_template(
        self,
        template_id: int,
        document_texts: List[str],
    ) -> Dict[str, Any]:
        """
        Try to fill every field in a template from the provided document texts.

        Returns a dict of {field_key: {value, confidence, context}}.
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found.")

        combined_text = "\n\n".join(document_texts)
        filled: Dict[str, Any] = {}

        for field in template["fields"]:
            match = self.matcher.extract_field_value(
                field_label=field["field_label"],
                extraction_hint=field.get("extraction_hint") or "",
                text=combined_text,
                field_type=field["field_type"],
            )
            filled[field["field_key"]] = {
                "label": field["field_label"],
                "type": field["field_type"],
                "value": match["value"] if match["value"] else field.get("default_value"),
                "confidence": match["confidence"],
                "context": match["context"],
                "required": bool(field.get("is_required")),
            }
        return filled
