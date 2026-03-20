#!/bin/bash
set -e

MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"

echo "=== INCLUSCAPE Startup ==="
echo "Model: $MODEL"

# ── 1. Start Ollama in the background ─────────────────────────────────────
echo "[1/3] Starting Ollama..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama API to become ready (up to 60 seconds)
echo "      Waiting for Ollama to be ready..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "      Ollama is ready."
        break
    fi
    sleep 2
    if [ "$i" -eq 30 ]; then
        echo "ERROR: Ollama did not start within 60 seconds." >&2
        exit 1
    fi
done

# ── 2. Pull the model ──────────────────────────────────────────────────────
echo "[2/3] Pulling model '$MODEL' (this may take several minutes on first run)..."
ollama pull "$MODEL"
echo "      Model ready."

# ── 3. Start Streamlit ─────────────────────────────────────────────────────
echo "[3/3] Starting Streamlit on port ${PORT:-8501}..."
exec streamlit run streamlit_app/app.py \
    --server.port="${PORT:-8501}" \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.fileWatcherType=none
