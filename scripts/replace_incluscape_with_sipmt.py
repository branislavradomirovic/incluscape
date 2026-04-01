#!/usr/bin/env python3
"""Replace occurrences of SIPMT -> SIPMT across text files.
Skips binary files, .git, .venv, __pycache__, and uploads directory by default.
Reports files changed and total replacements.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {'.git', '.venv', '__pycache__', 'uploads', 'data', 'logs'}

REPLACEMENTS = [
    ("SIPMT", "SIPMT"),
    ("sipmt", "sipmt"),
    ("SIPMT", "SIPMT"),
]

def is_text_file(path: Path) -> bool:
    try:
        data = path.read_bytes()
        data.decode('utf-8')
        return True
    except Exception:
        return False


def main():
    files_changed = 0
    total_replacements = 0
    for p in ROOT.rglob('*'):
        if p.is_dir():
            if p.name in EXCLUDE_DIRS:
                # skip dir tree
                for _ in p.rglob('*'):
                    pass
                continue
            else:
                continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.doc', '.docx', '.xlsx'}:
            continue
        try:
            if not is_text_file(p):
                continue
            text = p.read_text(encoding='utf-8')
        except Exception:
            continue
        new_text = text
        file_replacements = 0
        for old, new in REPLACEMENTS:
            if old in new_text:
                count = new_text.count(old)
                new_text = new_text.replace(old, new)
                file_replacements += count
        if file_replacements > 0:
            p.write_text(new_text, encoding='utf-8')
            files_changed += 1
            total_replacements += file_replacements
            print(f"Updated {p}: {file_replacements} replacements")
    print(f"\nDone. Files changed: {files_changed}. Total replacements: {total_replacements}")

if __name__ == '__main__':
    main()
