#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="python"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python is not available on PATH." >&2
  exit 1
fi

echo "[1/4] Checking required files..."
required_files=(
  "streamlit_app/app.py"
  "config.py"
  "requirements.txt"
  ".env.example"
)
for file in "${required_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "Missing required file: $file" >&2
    exit 1
  fi
done

echo "[2/4] Validating Python syntax..."
"$PYTHON_BIN" -m compileall -q \
  config.py \
  streamlit_app \
  document_processing \
  database \
  geospatial \
  template_matching \
  change_tracking \
  utils

echo "[3/4] Checking environment sample defaults..."
if ! grep -q "^SEMANTIC_LLM_PROVIDER=" .env.example; then
  echo "Missing SEMANTIC_LLM_PROVIDER in .env.example" >&2
  exit 1
fi
if ! grep -q "^ENABLE_SEMANTIC_ANALYSIS=" .env.example; then
  echo "Missing ENABLE_SEMANTIC_ANALYSIS in .env.example" >&2
  exit 1
fi

echo "[4/4] Checking git working tree state..."
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Warning: working tree has uncommitted changes."
  echo "Pre-deploy checks passed, but commit or stash changes before release."
else
  echo "Working tree is clean."
fi

echo "All pre-deploy checks passed."
