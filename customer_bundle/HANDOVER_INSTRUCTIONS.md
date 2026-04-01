# SIPMT Customer Handover

This package contains a prebuilt SIPMT delivery for customer installation with bundled:

- SIPMT application
- PostgreSQL database service
- Ollama service and model

## What You Received

- `images/` - Docker image archives to import on the customer machine
- `.env` - customer runtime configuration
- `docker-compose.yml` - service startup definition
- `scripts/` - startup, smoke-test, backup, and restore commands
- application source and runtime assets needed for support or rebuilds

## Customer Prerequisites

- Docker Desktop installed and running
- enough free disk space for Docker images, model files, and customer data
- outbound internet access if geocoding, reference refresh, or Gemini are required

## Install Steps

Run these commands from the delivery folder:

```bash
docker load -i images/incluscape-sipmt.tar
docker load -i images/incluscape-ollama.tar
docker load -i images/postgres-16-alpine.tar

docker compose up -d postgres ollama sipmt
bash scripts/smoke_test_bundle.sh
```

If the smoke test passes, open:

- App: `http://localhost:8501`
- Ollama API: `http://localhost:11434`

## First Configuration Check

Review `.env` before first startup and replace at minimum:

- `POSTGRES_PASSWORD`
- `SECRET_KEY`

Optional changes:

- `GEMINI_API_KEY`
- `OLLAMA_MODEL`
- `LOG_LEVEL`

## Daily Operations

Start services:

```bash
docker compose up -d postgres ollama sipmt
```

Check status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f sipmt ollama postgres
```

Stop services:

```bash
docker compose down
```

## Backup and Restore

Create backup:

```bash
bash scripts/backup_customer_data.sh
```

Restore backup:

```bash
bash scripts/restore_customer_data.sh backups/sipmt_bundle_YYYYMMDD_HHMMSS
docker compose restart sipmt
```

## Support Hand-Off Notes

- Customer data is stored in Docker volumes and PostgreSQL.
- Do not run `docker compose down -v` unless data removal is intended.
- If images must be re-imported on a new machine, use the files in `images/` again.