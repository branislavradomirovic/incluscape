#!/usr/bin/env python3
"""Osveži SQLite demo bazu podataka iz trenutne primarne PostgreSQL baze."""

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
        description="Sinhronizuj SQLite demo bazu iz PostgreSQL-a kako bi Streamlit Community Cloud koristio najnovije podatke."
    )
    parser.add_argument(
        "--if-configured",
        action="store_true",
        help="Završi uspešno kada sinhronizacija sa primarnim PostgreSQL-om nije podešena umesto da prijavi grešku.",
    )
    parser.add_argument(
        "--postgres-url",
        default=str(getattr(Config, "DATABASE_URL", "") or ""),
        help="URL primarnog PostgreSQL-a. Podrazumevano DATABASE_URL.",
    )
    parser.add_argument(
        "--sqlite-path",
        default=str(getattr(Config, "SQLITE_MIRROR_PATH", "") or getattr(Config, "DATABASE_PATH", "") or "./data/sipmt.db"),
        help="Putanja ciljnog SQLite fajla. Podrazumevano SQLITE_MIRROR_PATH, zatim DATABASE_PATH.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    postgres_url = (args.postgres_url or "").strip()
    sqlite_path = (args.sqlite_path or "").strip()

    if args.if_configured and (not postgres_url or bool(getattr(Config, "FORCE_SQLITE", False))):
        print("Preskačem osvežavanje SQLite kopije: sinhronizacija sa primarnim PostgreSQL-om nije podešena.")
        return 0

    if not postgres_url:
        raise ValueError("Nedostaje PostgreSQL URL. Prosledi --postgres-url ili postavi DATABASE_URL.")
    if not sqlite_path:
        raise ValueError("Nedostaje putanja SQLite kopije. Prosledi --sqlite-path ili postavi SQLITE_MIRROR_PATH / DATABASE_PATH.")

    os.environ["DATABASE_URL"] = postgres_url
    os.environ["FORCE_SQLITE"] = "false"

    from database.db_manager import DatabaseManager

    db = DatabaseManager()
    if db.backend != "postgres":
        if args.if_configured:
            print("Preskačem osvežavanje SQLite kopije: aktivni backend nije PostgreSQL.")
            return 0
        raise RuntimeError("Primarni backend nije PostgreSQL. Proveri podešavanja DATABASE_URL / FORCE_SQLITE.")

    db.initialize()
    summary = db.sync_sqlite_mirror(sqlite_path)

    print(f"SQLite kopija je osvežena: {sqlite_path}")
    for table, count in summary.items():
        print(f"  {table}: {count} redova")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
