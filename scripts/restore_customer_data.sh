#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/restore_customer_data.sh <backup-directory>" >&2
  exit 1
fi

BACKUP_DIR="$1"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-incluscape}"

if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "Backup directory not found: $BACKUP_DIR" >&2
  exit 1
fi

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-sipmt}"

restore_volume() {
  local logical_name="$1"
  local archive_path="$BACKUP_DIR/${logical_name}.tar.gz"
  local volume_name="${COMPOSE_PROJECT_NAME}_${logical_name}"

  if [[ ! -f "$archive_path" ]]; then
    echo "[WARN] Archive not found, skipping: $archive_path"
    return 0
  fi

  docker volume create "$volume_name" >/dev/null
  echo "[INFO] Restoring volume $volume_name"
  docker run --rm \
    -v "$volume_name":/target \
    -v "$BACKUP_DIR":/backup:ro \
    alpine:3.20 \
    sh -c "rm -rf /target/* /target/.[!.]* /target/..?* 2>/dev/null || true; cd /target && tar -xzf /backup/${logical_name}.tar.gz"
}

echo "[INFO] Ensuring PostgreSQL service is running"
docker compose up -d postgres

echo "[INFO] Waiting for PostgreSQL readiness"
for _ in $(seq 1 60); do
  if docker compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! docker compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
  echo "[FAIL] PostgreSQL did not become ready in time" >&2
  exit 1
fi

if [[ -f "$BACKUP_DIR/postgres.sql" ]]; then
  echo "[INFO] Restoring PostgreSQL database dump"
  docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
  docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$BACKUP_DIR/postgres.sql"
else
  echo "[WARN] Database dump not found, skipping DB restore"
fi

restore_volume "sipmt_uploads"
restore_volume "sipmt_exports"
restore_volume "sipmt_logs"
restore_volume "sipmt_temp"
restore_volume "sipmt_data"

echo "[OK] Restore completed from $BACKUP_DIR"