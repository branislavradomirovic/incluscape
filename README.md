# SIPMT

**SIPMT** is a Python/Streamlit SaaS application for **social inclusion document analysis**. Upload questionnaires, policies, instructions, forms, reports, and monitoring documents — SIPMT extracts structured data, fills predefined report templates, monitors document changes over time, and visualizes information on an interactive map.

## Features

- 📄 **Multi-format document ingestion** — PDF, DOCX, XLSX with optional OCR
- 📋 **Template-driven extraction** — upload a report template; SIPMT fills it from your documents automatically
- 🔍 **Change monitoring** — detect and track changes across document versions over time
- 🗺️ **Geospatial visualization** — extract locations from documents and plot them on an interactive map
- 🏢 **Multi-organization support** — manage multiple organisations and user roles
 - ⚖️ **HRBA (AAAQ) matcher** — scan documents for Availability, Accessibility, Acceptability, and Quality indicators using `spaCy` or a local Ollama LLM; includes live streaming previews and per-document timelines

## Detailed Features

Below is a concise but comprehensive description of SIPMT's major features and UI modules.

- **Documents (Upload & Management)**
    - Upload PDF/DOCX/XLSX files; optional OCR for scanned PDFs.
    - Documents are split into pages and stored with metadata (title, author, created_at).
    - Re-process uploaded files to refresh extraction results.

- **Templates (Report Definitions)**
    - Create structured templates with named fields and types (text, number, date, boolean, location).
    - Templates drive automated extraction and report generation across many documents.

- **Reports (Extraction & Export)**
    - Select a template and run batch extraction across selected documents.
    - Review extracted values and confidence scores before export (CSV/JSON/PDF).

- **Change Monitoring**
    - Detects document version changes and produces a diff highlighting added/removed/modified text.
    - Stores an audit trail including timestamps and size deltas.

- **Geospatial Mapping**
    - Extracts place names and optionally geocodes them to lat/lon using Nominatim.
    - Interactive Folium map shows markers with document source and context.

- **HRBA — AAAQ Matching & Insights**
    - Two modes: `spaCy` (fast, deterministic) and `Ollama` (LLM, JSON justifications).
    - Ollama integration supports streaming responses; the UI shows a live preview and builds a per-segment Gantt/timeline for visibility into when segments were generated.
    - Save full analysis JSON to the `semantic_analyses` table for later inspection in the `HRBA Insights` page.

- **Compliance (Semantic Analysis)**
    - Compare documents against reference frameworks (UN, EU, UNESCO) using semantic LLMs.
    - Supports Google Gemini (cloud) and Ollama (local) backends.

- **Insights & Exports**
    - The HRBA Insights page surfaces saved justifications in a table, allows CSV export, and visualizes analysis activity across documents with timelines and multi-document Gantt views.

- **Multi-organisation & Roles**
    - Project supports storing documents and analyses per organisation; session state contains `org_id` selections used by pages.

- **Developer & Admin Tools**
    - `scripts/pre_deploy_check.sh` validates the environment before deploys and refreshes the SQLite demo mirror when PostgreSQL is configured locally.
    - `scripts/migrate_sqlite_to_postgres.py` migrates demo SQLite data into Postgres in a foreign-key safe order.


## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | Python 3.11+ |
| Database | PostgreSQL (recommended) / SQLite (local fallback) |
| Document parsing | pypdf, python-docx, openpyxl, pytesseract |
| NLP | spaCy, NLTK |
| Mapping | Folium, geopy |
| Visualization | Plotly |

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/branislavradomirovic/sipmt.git
cd sipmt

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize the project (creates dirs, .env, database)
python setup.py

# 5. (Optional) Download the spaCy model
python -m spacy download en_core_web_sm

# 6. Run the application
streamlit run streamlit_app/app.py
```

The app will be available at **http://localhost:8501**

## HRBA — AAAQ Matching & Timeline

The project includes an HRBA matcher that can run in two modes:

- `spaCy (fast)`: lightweight local matcher for quick scans.
- `Ollama (LLM)`: self-hosted LLM that returns structured JSON justifications and supports streaming output.

When using the Ollama matcher the UI shows a live generation preview and a Gantt-style timeline per-document that helps visualise which segments were generated when and how long they took. To use Ollama locally:

```bash
# Start Ollama (follow Ollama docs for installation)
ollama pull qwen2.5:14b-instruct
# Ensure Ollama is reachable (default http://localhost:11434)
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=qwen2.5:14b-instruct
export SEMANTIC_LLM_PROVIDER=ollama
```

If the model does not stream intermediate chunks, the UI will still display the final JSON when available and the timeline will render after the segment completes.

## Database Configuration

SIPMT supports two database modes:

1. PostgreSQL as the primary local and production database
2. SQLite as a synced demo mirror for Streamlit Community Cloud or offline demos

Set one of the following:

```bash
# Preferred local/production primary database
DATABASE_URL=postgresql://postgres:replace-with-password@db-host:5432/incluscape?sslmode=require

# SQLite demo mirror used by Streamlit Community Cloud
DATABASE_PATH=./data/sipmt.db
SQLITE_MIRROR_PATH=./data/sipmt.db
ENABLE_SQLITE_MIRROR_SYNC=true
```

When `DATABASE_URL` is present, PostgreSQL is used automatically unless you explicitly set `FORCE_SQLITE=true`.

Note about deployments
----------------------

Recommended split:

1. Local development: keep `DATABASE_URL` pointed at PostgreSQL and enable `ENABLE_SQLITE_MIRROR_SYNC=true` so SQLite stays aligned with your live local data.
2. Streamlit Community Cloud: leave `DATABASE_URL` empty, keep `DATABASE_PATH` / `SQLITE_MIRROR_PATH` pointed at the SQLite file, and optionally set `FORCE_SQLITE=true` in secrets for clarity.

This keeps local development authoritative on Postgres while maintaining a demo-ready SQLite database for Cloud.

### Streamlit Community Cloud + Gemini

For Streamlit Community Cloud, use Gemini and leave `DATABASE_URL` empty unless you have a managed external PostgreSQL database.

Recommended Streamlit Cloud Secrets:

```toml
ENABLE_SEMANTIC_ANALYSIS = true
SEMANTIC_LLM_PROVIDER = "gemini"
GEMINI_API_KEY = "your-real-google-api-key"
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_FALLBACK_MODELS = "gemini-2.0-flash-lite-001,gemini-2.0-flash,gemini-2.5-flash"
DATABASE_URL = ""
DATABASE_PATH = "./data/sipmt.db"
SQLITE_MIRROR_PATH = "./data/sipmt.db"
FORCE_SQLITE = true
```

Notes:

1. Do not use `OLLAMA_*` settings on Streamlit Community Cloud. Ollama requires a local server and is not available in that environment.
2. Do not point `DATABASE_URL` at `localhost` for Cloud deploys.
3. SQLite is acceptable for a lightweight demo, but saved data is not guaranteed to persist across container restarts or redeploys.
4. If you need persistent uploaded documents and analysis history, use a managed PostgreSQL instance and set `DATABASE_URL` to that external service.

### Postgres-Primary Local Workflow With SQLite Demo Sync

Use this when you want your local instance to stay authoritative on PostgreSQL while keeping the SQLite demo database ready for Streamlit Community Cloud.

```bash
# Local development
DATABASE_URL=postgresql://postgres:replace-with-password@127.0.0.1:5432/incluscape?sslmode=disable
DATABASE_PATH=./data/sipmt.db
SQLITE_MIRROR_PATH=./data/sipmt.db
ENABLE_SQLITE_MIRROR_SYNC=true

# Refresh the SQLite demo snapshot manually whenever needed
python scripts/sync_postgres_to_sqlite.py
```

Notes:

1. With `ENABLE_SQLITE_MIRROR_SYNC=true`, normal app writes performed through `DatabaseManager` are mirrored into the SQLite demo database automatically.
2. `python scripts/sync_postgres_to_sqlite.py` performs a full refresh from PostgreSQL into SQLite and is useful after backfills, migrations, or legacy data imports.
3. Streamlit Community Cloud should still use the SQLite file by leaving `DATABASE_URL` empty in Cloud secrets.

## Shipping Local Postgres + Ollama

For demo deployments you can keep Streamlit on SQLite, but production/back-office installs should include a bundled PostgreSQL server plus Ollama for semantic analysis:

1. Install PostgreSQL locally (Windows installer or bundled service). During installation note the service port (default 5432) and create `sipmt` user/database.
2. Start Ollama locally (it can be shipped as part of the appliance or run from the same host) and point `OLLAMA_BASE_URL`/`OLLAMA_MODEL` in `.env`.
3. In `.env`, set:

```text
DATABASE_URL=postgresql://postgres:replace-with-password@127.0.0.1:5432/incluscape?sslmode=disable
ENABLE_SEMANTIC_ANALYSIS=true
SEMANTIC_LLM_PROVIDER=ollama
```

4. Initialize the database by running `python setup.py`, then run the Postgres migration script if you have existing SQLite data.
5. If you want the Streamlit Cloud demo database to match the latest local Postgres data, run `python scripts/sync_postgres_to_sqlite.py` before pushing the updated SQLite file.

The bundled installer should include PostgreSQL binaries, your `sipmt` database, and the required Ollama model/configuration so the customer only needs to configure service credentials and secrets.

### Migrate Existing SQLite Demo Data to PostgreSQL

Use the one-time migration script:

```bash
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path ./data/sipmt.db \
    --postgres-url postgresql://user:password@host:5432/dbname
```

If your target PostgreSQL already contains old data and you want to replace it:

```bash
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path ./data/sipmt.db \
    --postgres-url postgresql://user:password@host:5432/dbname \
    --truncate-target
```

Notes:

1. The script copies all application tables in foreign-key-safe order.
2. The migration runs in one PostgreSQL transaction; on error, writes are rolled back.
3. Document metadata is migrated, but binary files should be kept in persistent storage for production.

## Environment Profiles

Use one codebase with different providers per environment.

| Environment | Hosting | Provider | Key Variables |
|---|---|---|---|
| Local development | Your notebook | Ollama | `SEMANTIC_LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://localhost:11434`, `OLLAMA_MODEL=qwen2.5:14b-instruct` |
| Customer demo | Streamlit Community Cloud | Gemini | `SEMANTIC_LLM_PROVIDER=gemini`, `GEMINI_API_KEY=...`, `ENABLE_SEMANTIC_ANALYSIS=true`, `DATABASE_URL=` |

This keeps local AI quality and speed, while preserving a stable external demo URL from GitHub.

## Branching Policy

### Fast Production Mode

This is the default workflow for this project.

- `main`: live demo branch, auto-deployed by Streamlit Community Cloud
- preferred flow: make changes locally, run checks, commit, push to `main`

Use this mode when you want the latest version visible to customers immediately after push.

### Structured PR Mode

Use this when a change is larger, riskier, or needs review.

- `dev`: integration branch for ongoing work
- `feature/<name>`: short-lived branches for focused changes

Recommended PR flow:

1. Create a feature branch from `dev`
2. Commit and push frequently
3. Open PR `feature/<name>` -> `dev`
4. Run pre-deploy checks
5. Open PR `dev` -> `main` when ready to showcase

### PR Workflow Commands

```bash
# Start new work from dev
git checkout dev
git pull
git checkout -b feature/<short-name>

# Work, commit, push
git add .
git commit -m "<clear change summary>"
git push -u origin feature/<short-name>

# Open PR: feature/<short-name> -> dev
# After merge to dev and final validation, open PR: dev -> main
```

### Required GitHub Settings

If you use Structured PR Mode, enable branch protection for `dev` and `main` in GitHub:

1. Require a pull request before merging
2. Require status checks to pass
3. Select status check: `Pre-Deploy Check / pre-deploy-check`
4. Restrict direct pushes (optional but recommended)

## Pre-Deploy Check

Run this before every merge to `main`:

```bash
bash scripts/pre_deploy_check.sh
```

The check script validates:

- required project files
- Python syntax compilation for app modules
- local environment sample consistency
- automatic SQLite mirror refresh from PostgreSQL when Postgres is configured locally

## Release to Streamlit

Use this exact 5-step checklist:

1. Make changes
2. Run check: `bash scripts/pre_deploy_check.sh`
3. Commit
4. Get commit to deploy branch (`main` in your setup): either direct push to `main`, or PR merge `dev -> main`
5. Streamlit Cloud auto-redeploys from `main`

## Demo Checklist

Before pushing to `main`, confirm all items below:

1. App starts locally without errors (`streamlit run streamlit_app/app.py`)
2. Core pages load: Documents, Reports, Changes, Map, Compliance
3. Semantic analysis works in target demo environment
4. No secrets committed (API keys only in platform secrets)
5. `bash scripts/pre_deploy_check.sh` passes and refreshes the SQLite demo mirror when applicable
6. Demo dataset is present and recent outputs are clean
7. Commit message clearly describes customer-visible change
8. Push to `main` completed and cloud deployment is green

## Container Deployment

### Docker (single container, SQLite-backed)

```bash
docker build -t sipmt:latest .
docker run --rm -p 8501:8501 \
  --env-file .env \
    -v sipmt-data:/app/data \
    -v sipmt-uploads:/app/uploads \
    -v sipmt-exports:/app/exports \
    -v sipmt-logs:/app/logs \
    -v sipmt-temp:/app/temp \
    sipmt:latest
```

This mode is appropriate for demos and lightweight single-user installs. It persists local application data in Docker volumes, but SQLite is still not the preferred option for multi-user deployments.

If the single container must connect to a PostgreSQL server running on the Docker host, use `host.docker.internal` on Docker Desktop instead of `127.0.0.1`:

```bash
docker run --rm -p 8501:8501 \
    --env-file .env \
    -e DATABASE_URL="postgresql://postgres:replace-with-password@host.docker.internal:5432/sipmt?sslmode=disable" \
    -e FORCE_POSTGRES=True \
    sipmt:latest
```

### Docker Compose (production bundle: app + PostgreSQL + Ollama)

```bash
cp .env.production .env
bash scripts/release_bundle.sh
```

Then open: `http://localhost:8501`

The Compose stack provides:
- The Streamlit application on port `8501`
- A bundled PostgreSQL 16 instance for persistent application data
- A bundled `ollama/ollama:latest` service with the selected model baked into the image
- Persistent Docker volumes for uploads, exports, logs, temp files, SQLite fallback data, and PostgreSQL storage
- Internet-enabled runtime features such as geocoding and external reference refresh, assuming the customer network permits outbound access

If `DATABASE_URL` is left empty in `.env`, Compose injects an internal default that points the app at the bundled `postgres` service.

If `OLLAMA_MODEL` is left unchanged, the offline bundle preloads `qwen2.5:14b-instruct`, which matches the current machine defaults in this repository.

Important packaging behavior:
- The first `docker compose build` is heavy because the Ollama image bakes the selected model into the image layer.
- After that build completes, the stack can run semantic analysis without downloading the Ollama model at startup.
- This bundle is offline for Ollama inference after build, while internet-capable app features still work during customer use: geocoding, external source refresh, and Gemini if enabled.

The most useful override variables are:
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `OLLAMA_MODEL`
- `SIPMT_DATABASE_URL` if you explicitly want the app to use an external PostgreSQL server instead of the bundled one
- `.env.production` is the recommended customer-facing template for production installs

To stop the stack:

```bash
docker compose down
```

To stop it and remove all persisted volumes too:

```bash
docker compose down -v
```

For shipping to customers, replace the containerized Postgres service with the packaged Windows service you include in the installer while keeping the Streamlit container/image unchanged.

If you want a new offline bundle with a different Ollama model, rebuild after changing `OLLAMA_MODEL` in `.env`:

```bash
docker compose build --no-cache ollama sipmt
docker compose up -d
```

For customer-side installs with internet access, the recommended flow is:

```bash
cp .env.production .env
bash scripts/release_bundle.sh
```

That command builds the app image, builds the Ollama image with the selected model baked in, starts PostgreSQL, and brings the full SIPMT stack online. It also runs the smoke test automatically.

Manual smoke test:

```bash
bash scripts/smoke_test_bundle.sh
```

Customer handover checklist:
- [CUSTOMER_RELEASE_CHECKLIST.md](CUSTOMER_RELEASE_CHECKLIST.md)

## Project Structure

```
sipmt/
├── config.py                        # Central configuration
├── setup.py                         # One-time initialization script
├── requirements.txt
├── .env.example                     # Copy to .env and adjust
│
├── database/
│   ├── schema.sql                   # Full SQLite schema
│   └── db_manager.py                # Database access layer
│
├── document_processing/
│   ├── extractors/                  # PDF / DOCX / XLSX extractors
│   ├── processors/                  # Text cleaning, entity recognition
│   └── pipeline.py                  # Unified processing pipeline
│
├── template_matching/               # Fuzzy matching & data filling
├── change_tracking/                 # Version management & diff detection
├── geospatial/                      # Location extraction & mapping
├── utils/                           # Logging, file helpers, hashing
│
└── streamlit_app/
    ├── app.py                       # Entry point
    └── pages/                       # Multi-page Streamlit UI
```

## License

MIT
