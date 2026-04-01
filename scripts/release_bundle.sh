#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

COMPOSE_ARGS=(-f docker-compose.yml)

if [[ ! -f .env ]]; then
  if [[ -f .env.production ]]; then
    cp .env.production .env
    echo "Created .env from .env.production"
  else
    cp .env.example .env
    echo "Created .env from .env.example"
  fi
fi

echo "Building SIPMT production bundle..."
docker compose "${COMPOSE_ARGS[@]}" build sipmt ollama

echo "Starting SIPMT stack..."
docker compose "${COMPOSE_ARGS[@]}" up -d postgres ollama sipmt

echo "Running smoke test..."
bash scripts/smoke_test_bundle.sh

echo
echo "SIPMT bundle is ready."
echo "App URL: http://localhost:8501"
echo "Ollama API: http://localhost:11434"
echo
echo "Check status with: docker compose ps"
echo "View logs with: docker compose logs -f sipmt ollama postgres"