#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-incluscape}"
BACKUP_ROOT="${1:-$REPO_ROOT/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/sipmt_bundle_$TIMESTAMP"

mkdir -p "$BACKUP_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-sipmt}"

backup_volume() {
  local logical_name="$1"
  local volume_name="${COMPOSE_PROJECT_NAME}_${logical_name}"

  if ! docker volume inspect "$volume_name" >/dev/null 2>&1; then
    echo "[WARN] Volume not found, skipping: $volume_name"
    return 0
  fi

  echo "[INFO] Backing up volume $volume_name"
  docker run --rm \
    -v "$volume_name":/source:ro \
    -v "$BACKUP_DIR":/backup \
    alpine:3.20 \
    sh -c "cd /source && tar -czf /backup/${logical_name}.tar.gz ."
}

echo "[INFO] Creating customer backup in $BACKUP_DIR"

echo "[INFO] Exporting PostgreSQL database"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$BACKUP_DIR/postgres.sql"

backup_volume "sipmt_uploads"
backup_volume "sipmt_exports"
backup_volume "sipmt_logs"
backup_volume "sipmt_temp"
backup_volume "sipmt_data"

cat > "$BACKUP_DIR/README.txt" <<EOF
SIPMT backup created: $TIMESTAMP
Project: $COMPOSE_PROJECT_NAME
Database dump: postgres.sql
Volume archives:
- sipmt_uploads.tar.gz
- sipmt_exports.tar.gz
- sipmt_logs.tar.gz
- sipmt_temp.tar.gz
- sipmt_data.tar.gz
EOF

echo "[OK] Backup completed: $BACKUP_DIR"