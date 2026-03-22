#!/usr/bin/env python3
"""Refresh the SQLite demo database from the current PostgreSQL primary database."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from config import Config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync the SQLite demo database from PostgreSQL so Streamlit Community Cloud can use the latest data."
    )
    parser.add_argument(
        "--if-configured",
        action="store_true",
        help="Exit successfully when PostgreSQL-primary sync is not configured instead of failing.",
    )
    parser.add_argument(
        "--postgres-url",
        default=str(getattr(Config, "DATABASE_URL", "") or ""),
        help="Primary PostgreSQL URL. Defaults to DATABASE_URL.",
    )
    parser.add_argument(
        "--sqlite-path",
        default=str(getattr(Config, "SQLITE_MIRROR_PATH", "") or getattr(Config, "DATABASE_PATH", "") or "./data/sipmt.db"),
        help="Target SQLite path. Defaults to SQLITE_MIRROR_PATH, then DATABASE_PATH.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    postgres_url = (args.postgres_url or "").strip()
    sqlite_path = (args.sqlite_path or "").strip()

    if args.if_configured and (not postgres_url or bool(getattr(Config, "FORCE_SQLITE", False))):
        print("Skipping SQLite mirror refresh: PostgreSQL-primary sync is not configured.")
        return 0

    if not postgres_url:
        raise ValueError("Missing PostgreSQL URL. Pass --postgres-url or set DATABASE_URL.")
    if not sqlite_path:
        raise ValueError("Missing SQLite mirror path. Pass --sqlite-path or set SQLITE_MIRROR_PATH / DATABASE_PATH.")

    os.environ["DATABASE_URL"] = postgres_url
    os.environ["FORCE_SQLITE"] = "false"

    from database.db_manager import DatabaseManager

    db = DatabaseManager()
    if db.backend != "postgres":
        if args.if_configured:
            print("Skipping SQLite mirror refresh: active backend is not PostgreSQL.")
            return 0
        raise RuntimeError("Primary backend is not PostgreSQL. Check DATABASE_URL / FORCE_SQLITE settings.")

    db.initialize()
    summary = db.sync_sqlite_mirror(sqlite_path)

    print(f"SQLite mirror refreshed: {sqlite_path}")
    for table, count in summary.items():
        print(f"  {table}: {count} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
