#!/usr/bin/env python3
"""Refresh and version all active reference templates from source URLs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db_manager import DatabaseManager
from document_processing.semantic_comparison.reference_updater import ReferenceTemplateUpdater


def main() -> int:
    db = DatabaseManager()
    db.initialize()
    updater = ReferenceTemplateUpdater(db)
    results = updater.refresh_bodies()

    checked = len(results)
    updated = sum(1 for r in results if r.get("updated"))
    errors = [r for r in results if r.get("error")]

    print(f"Checked: {checked}")
    print(f"Updated: {updated}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nFailed checks:")
        for row in errors:
            print(f"- [{row.get('body')}] {row.get('name')}: {row.get('error')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
