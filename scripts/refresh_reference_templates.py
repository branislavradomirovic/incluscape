#!/usr/bin/env python3
"""
Refresh and version all active reference templates from source URLs.

Usage:
    python scripts/refresh_reference_templates.py [--no-enrich] [--bodies UN,EU,…]

By default:
  - enriches with the configured LLM provider (Ollama or Gemini, from .env)
  - refreshes UN, OECD, EU, UNESCO bodies
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config
from database.db_manager import DatabaseManager
from document_processing.semantic_comparison.reference_updater import ReferenceTemplateUpdater
from document_processing.semantic_comparison.sources_catalogue import SourcesCatalogue


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh SIPMT reference templates.")
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip LLM enrichment (hash-only update).",
    )
    parser.add_argument(
        "--bodies",
        default="UN,OECD,EU,UNESCO",
        help="Comma-separated list of governing bodies to refresh (default: UN,OECD,EU,UNESCO).",
    )
    args = parser.parse_args()

    bodies = [b.strip() for b in args.bodies.split(",") if b.strip()]
    use_llm = not args.no_enrich
    provider = Config.SEMANTIC_LLM_PROVIDER.lower()

    print(f"Provider : {provider}")
    print(f"Bodies   : {', '.join(bodies)}")
    print(f"Enrich   : {'yes (' + provider + ')' if use_llm else 'no'}")
    print()

    db = DatabaseManager()
    db.initialize()

    # Sync any new catalogue entries into the DB first
    catalogue = SourcesCatalogue(db=db)
    synced = catalogue.sync_to_db(db)
    print(f"Catalogue sync: {synced} entries processed")

    updater = ReferenceTemplateUpdater(db)
    results = updater.refresh_bodies(bodies=bodies, use_llm=use_llm)

    checked = len(results)
    updated = sum(1 for r in results if r.get("updated"))
    errors = [r for r in results if r.get("error")]
    llm_enriched = sum(1 for r in results if r.get("llm_enriched"))
    llm_warnings = [r for r in results if r.get("llm_error")]

    print(f"Checked         : {checked}")
    print(f"Updated         : {updated}")
    print(f"Errors          : {len(errors)}")
    if use_llm:
        print(f"LLM enriched    : {llm_enriched}")
        print(f"LLM warnings    : {len(llm_warnings)}")

    if errors:
        print("\nFailed source fetches:")
        for row in errors:
            print(f"  [{row.get('body')}] {row.get('name')}: {row.get('error')}")

    if llm_warnings:
        print(f"\n{provider.capitalize()} enrichment warnings:")
        for row in llm_warnings:
            print(f"  [{row.get('body')}] {row.get('name')}: {row.get('llm_error')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
