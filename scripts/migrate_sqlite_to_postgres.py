#!/usr/bin/env python3
"""One-time data migration from SQLite to PostgreSQL for INCLUSCAPE.

Usage:
  python scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path ./data/incluscape.db \
    --postgres-url postgresql://user:pass@host:5432/dbname

Safety:
- Aborts if target PostgreSQL tables are not empty unless --truncate-target is set.
- Runs in a single PostgreSQL transaction; any error rolls back all writes.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Sequence

import psycopg2
from psycopg2.extras import execute_values


TABLE_ORDER: List[str] = [
    "organisations",
    "users",
    "documents",
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

ID_TABLES: List[str] = [
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate INCLUSCAPE data from SQLite to PostgreSQL")
    parser.add_argument(
        "--sqlite-path",
        default="./data/incluscape.db",
        help="Path to SQLite database file (default: ./data/incluscape.db)",
    )
    parser.add_argument(
        "--postgres-url",
        default=os.getenv("DATABASE_URL", ""),
        help="PostgreSQL URL (or set DATABASE_URL env var)",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Truncate target PostgreSQL tables before import",
    )
    return parser.parse_args()


def _sqlite_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row[1] for row in rows]


def _load_sqlite_rows(conn: sqlite3.Connection, table: str, columns: Sequence[str]) -> List[tuple]:
    if not columns:
        return []
    col_csv = ", ".join(columns)
    rows = conn.execute(f"SELECT {col_csv} FROM {table}").fetchall()
    return [tuple(r[col] for col in columns) for r in rows]


def _count_pg_rows(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        return int(cur.fetchone()[0])


def _ensure_target_empty_or_truncate(conn, truncate_target: bool) -> None:
    if truncate_target:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE " + ", ".join(TABLE_ORDER) + " RESTART IDENTITY CASCADE")
        return

    non_empty = {}
    for table in TABLE_ORDER:
        count = _count_pg_rows(conn, table)
        if count > 0:
            non_empty[table] = count

    if non_empty:
        details = ", ".join(f"{table}={count}" for table, count in non_empty.items())
        raise RuntimeError(
            "Target PostgreSQL is not empty. Aborting migration to avoid overwrite. "
            f"Non-empty tables: {details}. Use --truncate-target if this is intentional."
        )


def _insert_rows_pg(conn, table: str, columns: Sequence[str], rows: Sequence[tuple]) -> int:
    if not rows:
        return 0
    col_csv = ", ".join(columns)
    query = f"INSERT INTO {table} ({col_csv}) VALUES %s"
    with conn.cursor() as cur:
        execute_values(cur, query, rows, page_size=1000)
    return len(rows)


def _reset_sequences(conn) -> None:
    with conn.cursor() as cur:
        for table in ID_TABLES:
            cur.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 1),
                    true
                )
                """
            )


def main() -> int:
    args = parse_args()

    sqlite_path = Path(args.sqlite_path).resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {sqlite_path}")

    postgres_url = (args.postgres_url or "").strip()
    if not postgres_url:
        raise ValueError("Missing PostgreSQL URL. Pass --postgres-url or set DATABASE_URL.")

    # Ensure PostgreSQL schema exists by reusing app initialization.
    os.environ["DATABASE_URL"] = postgres_url
    from database.db_manager import DatabaseManager

    target_db = DatabaseManager()
    target_db.initialize()

    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row

    pg_conn = psycopg2.connect(postgres_url)
    try:
        pg_conn.autocommit = False

        _ensure_target_empty_or_truncate(pg_conn, args.truncate_target)

        summary: Dict[str, int] = {}
        for table in TABLE_ORDER:
            columns = _sqlite_columns(sqlite_conn, table)
            rows = _load_sqlite_rows(sqlite_conn, table, columns)
            count = _insert_rows_pg(pg_conn, table, columns, rows)
            summary[table] = count

        _reset_sequences(pg_conn)
        pg_conn.commit()

        print("Migration completed successfully.")
        for table in TABLE_ORDER:
            print(f"  {table}: {summary.get(table, 0)} rows")

    except Exception:
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
