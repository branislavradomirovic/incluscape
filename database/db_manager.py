import sqlite3
import logging
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:  # pragma: no cover - optional dependency at import time
    psycopg2 = None
    RealDictCursor = None

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database access layer for INCLUSCAPE (PostgreSQL or SQLite)."""

    DOCUMENT_TYPE_MIGRATION_MAP = {
        "policy": "Policies",
        "procedure": "Instructions",
        "form": "Forms",
        "report": "Reports",
        "template": "Reports",
        "other": "Monitoring",
    }

    def __init__(self, db_path: Optional[str] = None):
        self.backend = "sqlite"
        self.database_url = ""

        if db_path is None:
            from config import Config

            # Prefer PostgreSQL when DATABASE_URL is provided.
            self.database_url = str(getattr(Config, "DATABASE_URL", "") or "").strip()
            if self.database_url.startswith("postgresql://") or self.database_url.startswith("postgres://"):
                self.backend = "postgres"

            db_path = Config.DATABASE_PATH

        self.db_path = str(db_path)
        if self.backend == "sqlite":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _normalise_sql(self, sql: str) -> str:
        """Convert SQLite-style placeholders to backend-specific placeholders."""
        if self.backend == "postgres":
            return sql.replace("?", "%s")
        return sql

    @staticmethod
    def _execute_script(conn, script: str) -> None:
        """Execute multi-statement SQL script for DB-API drivers without executescript."""
        statements = [chunk.strip() for chunk in script.split(";") if chunk.strip()]
        with conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    @contextmanager
    def get_connection(self):
        if self.backend == "postgres":
            if psycopg2 is None:
                raise RuntimeError(
                    "PostgreSQL backend requested but psycopg2 is not installed. "
                    "Add psycopg2-binary to requirements.txt"
                )
            conn = psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
        else:
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
        schema_file = "schema_postgres.sql" if self.backend == "postgres" else "schema.sql"
        schema_path = Path(__file__).parent / schema_file
        schema_sql = schema_path.read_text()
        with self.get_connection() as conn:
            if self.backend == "postgres":
                self._execute_script(conn, schema_sql)
            else:
                conn.executescript(schema_sql)
                self._migrate_document_categories(conn)
                self._repair_legacy_document_foreign_keys(conn)
            self._ensure_reference_template_columns(conn)
        target = self.database_url if self.backend == "postgres" else self.db_path
        logger.info("Database initialised (%s): %s", self.backend, target)

    def _ensure_reference_template_columns(self, conn) -> None:
        """Add newly introduced columns to reference_templates for existing DBs."""
        if self.backend == "postgres":
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'reference_templates'
                    """
                )
                existing_cols = {r["column_name"] for r in cur.fetchall()}
                for col, ddl in (
                    ("source_url", "ALTER TABLE reference_templates ADD COLUMN source_url TEXT"),
                    ("source_hash", "ALTER TABLE reference_templates ADD COLUMN source_hash TEXT"),
                    ("source_last_checked", "ALTER TABLE reference_templates ADD COLUMN source_last_checked TIMESTAMP"),
                    ("effective_date", "ALTER TABLE reference_templates ADD COLUMN effective_date TIMESTAMP"),
                    ("supersedes_template_id", "ALTER TABLE reference_templates ADD COLUMN supersedes_template_id BIGINT REFERENCES reference_templates(id)"),
                    ("change_summary", "ALTER TABLE reference_templates ADD COLUMN change_summary TEXT"),
                ):
                    if col not in existing_cols:
                        cur.execute(ddl)
            return

        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'reference_templates'"
        ).fetchone()
        if not row:
            return

        existing_cols = {
            r["name"] for r in conn.execute("PRAGMA table_info(reference_templates)").fetchall()
        }
        for col, ddl in (
            ("source_url", "ALTER TABLE reference_templates ADD COLUMN source_url TEXT"),
            ("source_hash", "ALTER TABLE reference_templates ADD COLUMN source_hash TEXT"),
            ("source_last_checked", "ALTER TABLE reference_templates ADD COLUMN source_last_checked TIMESTAMP"),
            ("effective_date", "ALTER TABLE reference_templates ADD COLUMN effective_date TIMESTAMP"),
            ("supersedes_template_id", "ALTER TABLE reference_templates ADD COLUMN supersedes_template_id INTEGER REFERENCES reference_templates(id)"),
            ("change_summary", "ALTER TABLE reference_templates ADD COLUMN change_summary TEXT"),
        ):
            if col not in existing_cols:
                conn.execute(ddl)

    def _repair_legacy_document_foreign_keys(self, conn: sqlite3.Connection) -> None:
        """
        Repair tables whose foreign keys still reference documents_legacy.

        Older category migration renamed `documents` -> `documents_legacy`, which made
        SQLite rewrite dependent FKs to point at `documents_legacy`. After dropping that
        table, those FKs cause runtime errors such as:
            OperationalError: no such table: main.documents_legacy
        """
        table_names = [r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()]

        broken_tables: List[str] = []
        for table in table_names:
            fks = conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
            if any(fk[2] == "documents_legacy" for fk in fks):
                broken_tables.append(table)

        if not broken_tables:
            return

        logger.warning(
            "Repairing legacy foreign keys in tables: %s",
            ", ".join(broken_tables),
        )

        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            for table in broken_tables:
                row = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                    (table,),
                ).fetchone()
                if not row or not row["sql"]:
                    continue

                create_sql = re.sub(
                    r'REFERENCES\s+"?documents_legacy"?',
                    "REFERENCES documents",
                    row["sql"],
                    flags=re.IGNORECASE,
                )

                tmp_table = f"{table}__fkfix_old"
                conn.execute(f"ALTER TABLE {table} RENAME TO {tmp_table}")
                conn.execute(create_sql)

                cols = [c["name"] for c in conn.execute(f"PRAGMA table_info({tmp_table})").fetchall()]
                col_csv = ", ".join(cols)
                conn.execute(
                    f"INSERT INTO {table} ({col_csv}) SELECT {col_csv} FROM {tmp_table}"
                )
                conn.execute(f"DROP TABLE {tmp_table}")
        finally:
            conn.execute("PRAGMA foreign_keys = ON")

    def _migrate_document_categories(self, conn: sqlite3.Connection) -> None:
        from config import Config

        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'documents'"
        ).fetchone()
        if not row or not row["sql"]:
            return

        table_sql = row["sql"]
        if all(category in table_sql for category in Config.DOCUMENT_CATEGORIES):
            return

        allowed_categories = ", ".join(f"'{category}'" for category in Config.DOCUMENT_CATEGORIES)
        migration_case = "\n".join(
            f"            WHEN '{legacy}' THEN '{current}'"
            for legacy, current in self.DOCUMENT_TYPE_MIGRATION_MAP.items()
        )

        conn.executescript(
            f"""
            ALTER TABLE documents RENAME TO documents_legacy;

            CREATE TABLE documents (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                organisation_id INTEGER NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
                uploaded_by     INTEGER REFERENCES users(id),
                title           TEXT    NOT NULL,
                document_type   TEXT    NOT NULL CHECK(document_type IN ({allowed_categories})),
                file_name       TEXT    NOT NULL,
                file_path       TEXT    NOT NULL,
                file_size       INTEGER,
                mime_type       TEXT,
                file_hash       TEXT    NOT NULL,
                version         INTEGER NOT NULL DEFAULT 1,
                parent_id       INTEGER REFERENCES documents(id),
                status          TEXT    NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived','processing','error')),
                processed_at    TIMESTAMP,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            INSERT INTO documents (
                id,
                organisation_id,
                uploaded_by,
                title,
                document_type,
                file_name,
                file_path,
                file_size,
                mime_type,
                file_hash,
                version,
                parent_id,
                status,
                processed_at,
                created_at
            )
            SELECT
                id,
                organisation_id,
                uploaded_by,
                title,
                CASE document_type
{migration_case}
                    WHEN 'Questionnaire' THEN 'Questionnaire'
                    WHEN 'Policies' THEN 'Policies'
                    WHEN 'Instructions' THEN 'Instructions'
                    WHEN 'Forms' THEN 'Forms'
                    WHEN 'Reports' THEN 'Reports'
                    WHEN 'Monitoring' THEN 'Monitoring'
                    ELSE 'Monitoring'
                END,
                file_name,
                file_path,
                file_size,
                mime_type,
                file_hash,
                version,
                parent_id,
                status,
                processed_at,
                created_at
            FROM documents_legacy;

            DROP TABLE documents_legacy;

            CREATE INDEX IF NOT EXISTS idx_documents_org     ON documents(organisation_id);
            CREATE INDEX IF NOT EXISTS idx_documents_hash    ON documents(file_hash);
            CREATE INDEX IF NOT EXISTS idx_documents_parent  ON documents(parent_id);
            """
        )
        logger.info("Migrated document categories to the current structure")

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------
    def execute(self, sql: str, params: tuple = ()) -> None:
        sql = self._normalise_sql(sql)
        with self.get_connection() as conn:
            if self.backend == "postgres":
                with conn.cursor() as cur:
                    cur.execute(sql, params)
            else:
                conn.execute(sql, params)

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        sql = self._normalise_sql(sql)
        with self.get_connection() as conn:
            if self.backend == "postgres":
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    row = cur.fetchone()
            else:
                row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict]:
        sql = self._normalise_sql(sql)
        with self.get_connection() as conn:
            if self.backend == "postgres":
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
            else:
                rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        cols = ", ".join(data.keys())
        if self.backend == "postgres":
            placeholders = ", ".join(["%s"] * len(data))
            sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) RETURNING id"
        else:
            placeholders = ", ".join("?" * len(data))
            sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        with self.get_connection() as conn:
            if self.backend == "postgres":
                with conn.cursor() as cur:
                    cur.execute(sql, tuple(data.values()))
                    row = cur.fetchone()
                    return int(row["id"] if isinstance(row, dict) else row[0])
            cur = conn.execute(sql, tuple(data.values()))
            return cur.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: str, params: tuple = ()) -> None:
        placeholder = "%s" if self.backend == "postgres" else "?"
        set_clause = ", ".join(f"{k} = {placeholder}" for k in data.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        sql = self._normalise_sql(sql)
        with self.get_connection() as conn:
            if self.backend == "postgres":
                with conn.cursor() as cur:
                    cur.execute(sql, tuple(data.values()) + params)
            else:
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

    def delete_document(self, document_id: int) -> None:
        """Permanently delete a document record, cascade child rows, and remove the physical file."""
        row = self.fetchone("SELECT file_path FROM documents WHERE id = ?", (document_id,))
        if row and row.get("file_path"):
            try:
                Path(row["file_path"]).unlink(missing_ok=True)
            except OSError:
                pass
        self.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    def save_entities(self, entities: List[Dict[str, Any]]) -> None:
        if not entities:
            return
        with self.get_connection() as conn:
            sql = (
                "INSERT INTO extracted_entities "
                "(document_id, entity_type, entity_text, context, confidence, page_number) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            )
            rows = [
                (
                    e.get("document_id"),
                    e.get("entity_type"),
                    e.get("entity_text"),
                    e.get("context"),
                    e.get("confidence"),
                    e.get("page_number"),
                )
                for e in entities
            ]
            if self.backend == "postgres":
                with conn.cursor() as cur:
                    cur.executemany(self._normalise_sql(sql), rows)
            else:
                conn.executemany(sql, rows)

    def get_document_history(self, document_id: int) -> List[Dict]:
        return self.fetchall(
            "SELECT * FROM documents WHERE id = ? OR parent_id = ? ORDER BY version",
            (document_id, document_id),
        )

    def save_semantic_analysis(self, data: Dict[str, Any]) -> int:
        """Persist a semantic analysis result; returns the new row id."""
        return self.insert("semantic_analyses", data)

    def get_semantic_analyses(self, document_id: int) -> List[Dict]:
        return self.fetchall(
            """
            SELECT sa.*, rt.name AS reference_name, rt.body, rt.category, rt.source_url
            FROM   semantic_analyses sa
            LEFT JOIN reference_templates rt ON rt.id = sa.reference_template_id
            WHERE  sa.document_id = ?
            ORDER  BY sa.created_at DESC
            """,
            (document_id,),
        )

    def get_reference_templates(
        self,
        body: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict]:
        """Return active reference templates, optionally filtered."""
        clauses = ["is_active = 1"]
        params: list = []
        if body:
            clauses.append("body = ?")
            params.append(body)
        if category:
            clauses.append("category = ?")
            params.append(category)
        where = " AND ".join(clauses)
        return self.fetchall(
            f"SELECT * FROM reference_templates WHERE {where} ORDER BY body, category, name",
            tuple(params),
        )

    def upsert_reference_template(self, data: Dict[str, Any]) -> int:
        """Insert or update a reference template by (body, category, name)."""
        existing = self.fetchone(
            "SELECT id FROM reference_templates "
            "WHERE body = ? AND category = ? AND name = ? AND is_active = 1 "
            "ORDER BY id DESC LIMIT 1",
            (data["body"], data["category"], data["name"]),
        )
        if existing:
            protected_on_update = {
                "version",
                "source_hash",
                "source_last_checked",
                "effective_date",
                "supersedes_template_id",
                "change_summary",
                "is_active",
            }
            self.update(
                "reference_templates",
                {
                    k: v for k, v in data.items()
                    if k not in ("body", "category", "name") and k not in protected_on_update
                },
                "id = ?",
                (existing["id"],),
            )
            return existing["id"]
        return self.insert("reference_templates", data)

    def log_audit(self, user_id: Optional[int], action: str,
                  entity_type: str = "", entity_id: int = 0, detail: str = "") -> None:
        self.insert("audit_log", {
            "user_id": user_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "detail": detail,
        })
