#!/usr/bin/env python
"""
INCLUSCAPE — One-time project initialization script.
Run after cloning: python setup.py
"""

import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DIRECTORIES = [
    BASE_DIR / "data",
    BASE_DIR / "uploads",
    BASE_DIR / "exports",
    BASE_DIR / "temp",
    BASE_DIR / "logs",
]


def create_directories():
    print("Creating directories...")
    for d in DIRECTORIES:
        d.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {d.relative_to(BASE_DIR)}/")


def create_env_file():
    env_file = BASE_DIR / ".env"
    example = BASE_DIR / ".env.example"
    if env_file.exists():
        print("  .env already exists — skipping.")
        return
    if example.exists():
        shutil.copy(example, env_file)
        print("  ✓ .env created from .env.example")
    else:
        env_file.write_text(
            "DATABASE_PATH=./data/incluscape.db\n"
            "UPLOAD_FOLDER=./uploads\n"
            "DEBUG=False\n"
            "SECRET_KEY=change-me\n"
        )
        print("  ✓ .env created with defaults")


def initialize_database():
    sys.path.insert(0, str(BASE_DIR))
    try:
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        db.initialize()
        print("  ✓ Database initialized")
    except Exception as exc:
        print(f"  ⚠ Database init skipped: {exc}")


def main():
    print("=" * 52)
    print("  INCLUSCAPE — Project Setup")
    print("=" * 52)
    create_directories()
    print("\nConfiguration...")
    create_env_file()
    print("\nDatabase...")
    initialize_database()
    print("\n✅  Setup complete!\n")
    print("Next steps:")
    print("  pip install -r requirements.txt")
    print("  streamlit run streamlit_app/app.py")


if __name__ == "__main__":
    main()
