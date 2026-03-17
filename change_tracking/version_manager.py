import hashlib
import logging
from typing import Dict, List, Optional

from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class VersionManager:
    """Track document versions and resolve the latest version for a given lineage."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def get_versions(self, root_document_id: int) -> List[Dict]:
        """Return all versions in the lineage of a document, oldest first."""
        return self.db.fetchall(
            "SELECT id, title, version, file_hash, created_at, status "
            "FROM documents WHERE id = ? OR parent_id = ? ORDER BY version ASC",
            (root_document_id, root_document_id),
        )

    def get_latest(self, root_document_id: int) -> Optional[Dict]:
        versions = self.get_versions(root_document_id)
        return versions[-1] if versions else None

    def is_duplicate(self, file_hash: str, organisation_id: int) -> bool:
        row = self.db.fetchone(
            "SELECT id FROM documents WHERE file_hash = ? AND organisation_id = ?",
            (file_hash, organisation_id),
        )
        return row is not None

    def next_version_number(self, root_document_id: int) -> int:
        versions = self.get_versions(root_document_id)
        return (max(v["version"] for v in versions) + 1) if versions else 1
