import hashlib
import json
import logging
from difflib import unified_diff
from typing import Any, Dict, List, Optional

from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Detect and record changes between document versions."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    # ------------------------------------------------------------------
    def compare(self, old_text: str, new_text: str) -> Dict[str, Any]:
        """Compare two text bodies and return a change summary."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        diff_lines = list(unified_diff(old_lines, new_lines, lineterm=""))

        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
        total_old = len(old_lines) or 1
        change_pct = (added + removed) / total_old

        return {
            "added_lines": added,
            "removed_lines": removed,
            "change_percentage": round(change_pct * 100, 1),
            "impact_level": self._impact_level(change_pct),
            "diff_snippet": "".join(diff_lines[:60]),  # first 60 diff lines
        }

    # ------------------------------------------------------------------
    def record_change(
        self,
        document_id: int,
        previous_doc_id: Optional[int],
        change_type: str,
        comparison: Optional[Dict] = None,
        user_id: Optional[int] = None,
    ) -> int:
        data: Dict[str, Any] = {
            "document_id": document_id,
            "previous_doc_id": previous_doc_id,
            "change_type": change_type,
            "impact_level": (comparison or {}).get("impact_level", "low"),
            "diff_summary": json.dumps(comparison or {}),
        }
        if user_id is not None:
            data["detected_by"] = user_id
        change_id = self.db.insert("document_changes", data)
        logger.info("Recorded change id=%d for document %d", change_id, document_id)
        return change_id

    # ------------------------------------------------------------------
    def get_changes(self, document_id: int) -> List[Dict]:
        return self.db.fetchall(
            "SELECT * FROM document_changes WHERE document_id = ? ORDER BY detected_at DESC",
            (document_id,),
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _impact_level(change_pct: float) -> str:
        if change_pct < 0.05:
            return "low"
        if change_pct < 0.20:
            return "medium"
        if change_pct < 0.50:
            return "high"
        return "critical"
