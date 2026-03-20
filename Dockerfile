FROM python:3.11-slim

WORKDIR /app

# Install system dependencies + Ollama prerequisites
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama binary
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make startup script executable
RUN chmod +x start.sh

ENV PYTHONUNBUFFERED=1

# Railway injects $PORT — Streamlit will bind to it via start.sh
EXPOSE 8501

# Health check (Streamlit)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -sf http://localhost:${PORT:-8501}/_stcore/health || exit 1

CMD ["bash", "start.sh"]
