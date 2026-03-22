import sqlite3
import os
import logging
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:  # pragma: no cover - optional dependency at import time
    psycopg2 = None
    RealDictCursor = None

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database access layer for SIPMT (PostgreSQL or SQLite)."""

    APP_TABLE_ORDER = [
        "organisations",
        "users",
        "documents",
        "document_blobs",
        "document_pages",
        "extracted_entities",
        "report_templates",
        "template_fields",
        "reports",
        "report_values",
        "report_sources",
        "document_changes",
        "locations",
        "audit_log",
        "reference_templates",
        "semantic_analyses",
    ]

    APP_ID_TABLES = [
        "organisations",
        "users",
        "documents",
        "document_pages",
        "extracted_entities",
        "report_templates",
        "template_fields",
        "reports",
        "report_values",
        "document_changes",
        "locations",
        "audit_log",
        "reference_templates",
        "semantic_analyses",
    ]

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
        self.sqlite_mirror_path = ""
        self.enable_sqlite_mirror_sync = False
        self._sqlite_mirror_ready = False

        if db_path is None:
            from config import Config

            self.database_url = str(getattr(Config, "DATABASE_URL", "") or "").strip()
            force_pg = bool(getattr(Config, "FORCE_POSTGRES", False))
            force_sqlite = bool(getattr(Config, "FORCE_SQLITE", False))
            self.sqlite_mirror_path = str(getattr(Config, "SQLITE_MIRROR_PATH", "") or getattr(Config, "DATABASE_PATH", "")).strip()

            if force_sqlite:
                self.database_url = ""
                self.backend = "sqlite"
            elif self.database_url.startswith("postgresql://") or self.database_url.startswith("postgres://"):
                self.backend = "postgres"
                if force_pg or "sslmode=" not in self.database_url.lower():
                    self.database_url = self._ensure_sslmode(self.database_url)

            db_path = Config.DATABASE_PATH
        else:
            self.sqlite_mirror_path = str(db_path)

        self.db_path = str(db_path)
        if self.backend == "sqlite":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        elif self.sqlite_mirror_path:
            self.enable_sqlite_mirror_sync = bool(os.getenv("ENABLE_SQLITE_MIRROR_SYNC", "").strip().lower() in ("1", "true", "yes"))
            try:
                from config import Config

                self.enable_sqlite_mirror_sync = bool(getattr(Config, "ENABLE_SQLITE_MIRROR_SYNC", False))
                if not self.sqlite_mirror_path:
                    self.sqlite_mirror_path = str(getattr(Config, "SQLITE_MIRROR_PATH", "") or getattr(Config, "DATABASE_PATH", ""))
            except Exception:
                pass

    @staticmethod
    def _is_mutating_sql(sql: str) -> bool:
        statement = (sql or "").lstrip().split(None, 1)
        if not statement:
            return False
        return statement[0].upper() in {"INSERT", "UPDATE", "DELETE", "REPLACE"}

    @staticmethod
    def _coerce_sqlite_value(value: Any) -> Any:
        if isinstance(value, memoryview):
            return value.tobytes()
        return value

    def _ensure_sqlite_mirror_ready(self) -> None:
        if not self.enable_sqlite_mirror_sync or not self.sqlite_mirror_path:
            return
        if self._sqlite_mirror_ready:
            return

        mirror_db = DatabaseManager(db_path=self.sqlite_mirror_path)
        mirror_db.initialize()
        self._sqlite_mirror_ready = True

    def _run_sqlite_mirror(self, sql: str, params: tuple = (), many: Optional[List[tuple]] = None) -> None:
        if not self.enable_sqlite_mirror_sync or not self.sqlite_mirror_path:
            return

        self._ensure_sqlite_mirror_ready()
        with sqlite3.connect(self.sqlite_mirror_path, detect_types=sqlite3.PARSE_DECLTYPES) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            if many is not None:
                rows = [tuple(self._coerce_sqlite_value(v) for v in row) for row in many]
                conn.executemany(sql, rows)
            else:
                conn.execute(sql, tuple(self._coerce_sqlite_value(v) for v in params))
            conn.commit()

    def sync_sqlite_mirror(self, sqlite_path: Optional[str] = None) -> Dict[str, int]:
        if self.backend != "postgres":
            raise RuntimeError("SQLite mirror sync is only available when PostgreSQL is the primary backend.")

        target_path = str(sqlite_path or self.sqlite_mirror_path or self.db_path)
        if not target_path:
            raise ValueError("Missing SQLite mirror path.")

        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_target = target.with_suffix(target.suffix + ".sync")
        temp_target.unlink(missing_ok=True)

        mirror_db = DatabaseManager(db_path=str(temp_target))
        mirror_db.initialize()

        summary: Dict[str, int] = {}
        with self.get_connection() as pg_conn:
            with sqlite3.connect(str(temp_target), detect_types=sqlite3.PARSE_DECLTYPES) as sqlite_conn:
                sqlite_conn.execute("PRAGMA foreign_keys = OFF")
                for table in reversed(self.APP_TABLE_ORDER):
                    sqlite_conn.execute(f"DELETE FROM {table}")

                with pg_conn.cursor() as cur:
                    for table in self.APP_TABLE_ORDER:
                        cur.execute(f"SELECT * FROM {table}")
                        rows = cur.fetchall()
                        col_names = [desc[0] for desc in cur.description]
                        summary[table] = len(rows)
                        if not rows:
                            continue

                        placeholders = ", ".join("?" * len(col_names))
                        sql = f"INSERT INTO {table} ({', '.join(col_names)}) VALUES ({placeholders})"
                        sqlite_conn.executemany(
                            sql,
                            [tuple(self._coerce_sqlite_value(row[col]) for col in col_names) for row in rows],
                        )

                sqlite_conn.execute("DELETE FROM sqlite_sequence")
                for table in self.APP_ID_TABLES:
                    max_id_row = sqlite_conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}").fetchone()
                    max_id = int(max_id_row[0] if max_id_row else 0)
                    if max_id > 0:
                        sqlite_conn.execute(
                            "INSERT INTO sqlite_sequence(name, seq) VALUES(?, ?)",
                            (table, max_id),
                        )

                sqlite_conn.execute("PRAGMA foreign_keys = ON")
                sqlite_conn.commit()

        os.replace(temp_target, target)
        self._sqlite_mirror_ready = False
        return summary

    @staticmethod
    def _ensure_sslmode(url: str) -> str:
        """Add sslmode=require to postgres URLs if missing (Supabase compatibility)."""
        parsed = urlparse(url)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if "sslmode" not in params:
            params["sslmode"] = "require"
            parsed = parsed._replace(query=urlencode(params))
            return urlunparse(parsed)
        return url

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
                self._ensure_document_blobs_table(conn)
            self._ensure_reference_template_columns(conn)
            if self.backend == "postgres":
                self._ensure_document_blobs_table(conn)
        target = self.database_url if self.backend == "postgres" else self.db_path
        logger.info("Database initialised (%s): %s", self.backend, target)

    def _ensure_document_blobs_table(self, conn) -> None:
        """Ensure optional binary storage table exists for cloud-persistent uploads."""
        if self.backend == "postgres":
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS document_blobs (
                        document_id BIGINT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
                        content BYTEA NOT NULL,
                        mime_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            return

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_blobs (
                document_id INTEGER PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
                content BLOB NOT NULL,
                mime_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

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
        mirror_sql = sql
        sql = self._normalise_sql(sql)
        with self.get_connection() as conn:
            if self.backend == "postgres":
                with conn.cursor() as cur:
                    cur.execute(sql, params)
            else:
                conn.execute(sql, params)
        if self.backend == "postgres" and self._is_mutating_sql(mirror_sql):
            self._run_sqlite_mirror(mirror_sql, params)

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
                    inserted_id = int(row["id"] if isinstance(row, dict) else row[0])
                mirror_data = dict(data)
                mirror_data.setdefault("id", inserted_id)
                mirror_cols = ", ".join(mirror_data.keys())
                mirror_placeholders = ", ".join("?" * len(mirror_data))
                self._run_sqlite_mirror(
                    f"INSERT INTO {table} ({mirror_cols}) VALUES ({mirror_placeholders})",
                    tuple(mirror_data.values()),
                )
                return inserted_id
            cur = conn.execute(sql, tuple(data.values()))
            return cur.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: str, params: tuple = ()) -> None:
        placeholder = "%s" if self.backend == "postgres" else "?"
        set_clause = ", ".join(f"{k} = {placeholder}" for k in data.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        mirror_sql = f"UPDATE {table} SET {', '.join(f'{k} = ?' for k in data.keys())} WHERE {where}"
        sql = self._normalise_sql(sql)
        with self.get_connection() as conn:
            if self.backend == "postgres":
                with conn.cursor() as cur:
                    cur.execute(sql, tuple(data.values()) + params)
            else:
                conn.execute(sql, tuple(data.values()) + params)
        if self.backend == "postgres":
            self._run_sqlite_mirror(mirror_sql, tuple(data.values()) + params)

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
                path_str = str(row["file_path"])
                if not path_str.startswith("db://"):
                    Path(path_str).unlink(missing_ok=True)
            except OSError:
                pass
        self.execute("DELETE FROM documents WHERE id = ?", (document_id,))

    def save_document_blob(self, document_id: int, content: bytes, mime_type: Optional[str] = None) -> None:
        if self.backend == "postgres":
            sql = (
                "INSERT INTO document_blobs (document_id, content, mime_type) "
                "VALUES (%s, %s, %s) "
                "ON CONFLICT (document_id) DO UPDATE SET content = EXCLUDED.content, mime_type = EXCLUDED.mime_type"
            )
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (document_id, psycopg2.Binary(content), mime_type))
            self._run_sqlite_mirror(
                "INSERT INTO document_blobs (document_id, content, mime_type) VALUES (?, ?, ?) "
                "ON CONFLICT(document_id) DO UPDATE SET content = excluded.content, mime_type = excluded.mime_type",
                (document_id, sqlite3.Binary(content), mime_type),
            )
            return

        sql = (
            "INSERT INTO document_blobs (document_id, content, mime_type) VALUES (?, ?, ?) "
            "ON CONFLICT(document_id) DO UPDATE SET content = excluded.content, mime_type = excluded.mime_type"
        )
        with self.get_connection() as conn:
            conn.execute(sql, (document_id, sqlite3.Binary(content), mime_type))

    def get_document_blob(self, document_id: int) -> Optional[Dict[str, Any]]:
        return self.fetchone(
            "SELECT content, mime_type FROM document_blobs WHERE document_id = ?",
            (document_id,),
        )

    def materialize_document_for_processing(self, document_id: int, file_name: str, temp_dir: str) -> Optional[str]:
        """Write a stored blob to a temp file and return path, or None when absent."""
        row = self.get_document_blob(document_id)
        if not row or row.get("content") is None:
            return None

        suffix = Path(file_name or "").suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=temp_dir) as tmp:
            tmp.write(bytes(row["content"]))
            return tmp.name

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
        if self.backend == "postgres":
            self._run_sqlite_mirror(sql, many=rows)

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

    def get_latest_hrba_analyses(self, limit: int = 200, organisation_id: Optional[int] = None) -> List[Dict]:
        """Return recent rows from `semantic_analyses` joined with document titles.

        Returns rows with keys: id, document_id, doc_title, model_used, full_response_json, created_at.
        """
        params: list = []
        where_clause = ""
        if organisation_id is not None:
            where_clause = "WHERE d.organisation_id = ?"
            params.append(organisation_id)

        params.append(limit)
        sql = (
            "SELECT sa.id, sa.document_id, d.title AS doc_title, sa.model_used, sa.full_response_json, sa.created_at "
            "FROM semantic_analyses sa JOIN documents d ON d.id = sa.document_id "
            f"{where_clause} "
            "ORDER BY sa.created_at DESC LIMIT ?"
        )
        return self.fetchall(sql, tuple(params))

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
