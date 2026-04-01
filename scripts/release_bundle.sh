#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Building SIPMT production bundle..."
docker compose build sipmt ollama

echo "Starting SIPMT stack..."
docker compose up -d postgres ollama sipmt

echo
echo "SIPMT bundle is starting."
echo "App URL: http://localhost:8501"
echo "Ollama API: http://localhost:11434"
echo
echo "Check status with: docker compose ps"
echo "View logs with: docker compose logs -f sipmt ollama postgres"