FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    HOME=/home/appuser

WORKDIR /app

# Install only runtime OS packages needed by the app and use tini as PID 1.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tini \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system appuser \
    && useradd --system --gid appuser --create-home --home-dir /home/appuser appuser \
    && mkdir -p /app/uploads /app/exports /app/logs /app/temp /app/data \
    && chown -R appuser:appuser /app /home/appuser

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health').read()"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["streamlit", "run", "streamlit_app/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
