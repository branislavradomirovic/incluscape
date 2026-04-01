#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

APP_URL="${APP_URL:-http://localhost:8501/_stcore/health}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434/api/tags}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-180}"
START_TS="$(date +%s)"

wait_for_http() {
  local name="$1"
  local url="$2"

  while true; do
    if curl --silent --show-error --fail "$url" >/dev/null 2>&1; then
      echo "[OK] $name is reachable: $url"
      return 0
    fi

    if (( $(date +%s) - START_TS >= MAX_WAIT_SECONDS )); then
      echo "[FAIL] Timed out waiting for $name at $url" >&2
      return 1
    fi

    sleep 5
  done
}

wait_for_pg() {
  while true; do
    if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-sipmt}" >/dev/null 2>&1; then
      echo "[OK] PostgreSQL is accepting connections"
      return 0
    fi

    if (( $(date +%s) - START_TS >= MAX_WAIT_SECONDS )); then
      echo "[FAIL] Timed out waiting for PostgreSQL" >&2
      return 1
    fi

    sleep 5
  done
}

echo "Running SIPMT bundle smoke test..."

wait_for_pg
wait_for_http "Ollama" "$OLLAMA_URL"
wait_for_http "SIPMT app" "$APP_URL"

echo
echo "Smoke test passed."
echo "- App health endpoint: $APP_URL"
echo "- Ollama tags endpoint: $OLLAMA_URL"
echo "- PostgreSQL: healthy via pg_isready"