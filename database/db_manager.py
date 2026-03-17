import sqlite3
import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Thin SQLite access layer for INCLUSCAPE."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from config import Config
            db_path = Config.DATABASE_PATH
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create all tables from schema.sql."""
        schema_path = Path(__file__).parent / "schema.sql"
        with self.get_connection() as conn:
            conn.executescript(schema_path.read_text())
        logger.info("Database initialised at %s", self.db_path)

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------
    def execute(self, sql: str, params: tuple = ()) -> None:
        with self.get_connection() as conn:
            conn.execute(sql, params)

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        with self.get_connection() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict]:
        with self.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        with self.get_connection() as conn:
            cur = conn.execute(sql, tuple(data.values()))
            return cur.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: str, params: tuple = ()) -> None:
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        with self.get_connection() as conn:
            conn.execute(sql, tuple(data.values()) + params)

    # ------------------------------------------------------------------
    # Domain helpers
    # ------------------------------------------------------------------
    def get_or_create_organisation(self, name: str) -> int:
        row = self.fetchone(
            "SELECT id FROM organisations WHERE name = ?", (name,)
        )
        if row:
            return row["id"]
        return self.insert("organisations", {"name": name})

    def save_document(self, doc_data: Dict[str, Any]) -> int:
        return self.insert("documents", doc_data)

    def save_entities(self, entities: List[Dict[str, Any]]) -> None:
        if not entities:
            return
        with self.get_connection() as conn:
            conn.executemany(
                "INSERT INTO extracted_entities "
                "(document_id, entity_type, entity_text, context, confidence, page_number) "
                "VALUES (:document_id, :entity_type, :entity_text, :context, :confidence, :page_number)",
                entities,
            )

    def get_document_history(self, document_id: int) -> List[Dict]:
        return self.fetchall(
            "SELECT * FROM documents WHERE id = ? OR parent_id = ? ORDER BY version",
            (document_id, document_id),
        )

    def log_audit(self, user_id: Optional[int], action: str,
                  entity_type: str = "", entity_id: int = 0, detail: str = "") -> None:
        self.insert("audit_log", {
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "detail": detail,
        })
