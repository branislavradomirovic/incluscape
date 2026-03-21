# INCLUSCAPE

**INCLUSCAPE** is a Python/Streamlit SaaS application for **social inclusion document analysis**. Upload questionnaires, policies, instructions, forms, reports, and monitoring documents — INCLUSCAPE extracts structured data, fills predefined report templates, monitors document changes over time, and visualizes information on an interactive map.

## Features

- 📄 **Multi-format document ingestion** — PDF, DOCX, XLSX with optional OCR
- 📋 **Template-driven extraction** — upload a report template; INCLUSCAPE fills it from your documents automatically
- 🔍 **Change monitoring** — detect and track changes across document versions over time
- 🗺️ **Geospatial visualization** — extract locations from documents and plot them on an interactive map
- 🏢 **Multi-organization support** — manage multiple organisations and user roles

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
git clone https://github.com/branislavradomirovic/incluscape.git
cd incluscape

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

## Database Configuration

INCLUSCAPE supports two database modes:

1. PostgreSQL (recommended for Streamlit Cloud and production)
2. SQLite (local fallback for quick development)

Set one of the following:

```bash
# Preferred: persistent cloud database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Fallback local file database
DATABASE_PATH=./data/incluscape.db
```

When `DATABASE_URL` is present, PostgreSQL is used automatically.

## Supabase + Streamlit Cloud (Persistent Storage)

For Streamlit Community Cloud, filesystem is ephemeral. To persist both metadata and uploaded files:

1. Create a Supabase PostgreSQL project and copy the connection string.
2. In Streamlit app secrets, set:

```toml
DATABASE_URL="postgresql://postgres:[PASSWORD]@[HOST]:6543/postgres"
STORE_FILES_IN_DB=true
ENABLE_SEMANTIC_ANALYSIS=true
SEMANTIC_LLM_PROVIDER="gemini"
GEMINI_API_KEY="..."
```

3. Keep `DATABASE_PATH` unset (or ignored) in cloud mode.

Notes:

1. INCLUSCAPE auto-adds `sslmode=require` when missing for PostgreSQL URLs (Supabase-safe default).
2. `STORE_FILES_IN_DB=true` stores uploaded binary files in table `document_blobs`, enabling reliable re-processing even after container/app restarts.

### Migrate Existing SQLite Demo Data to PostgreSQL

Use the one-time migration script:

```bash
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path ./data/incluscape.db \
    --postgres-url postgresql://user:password@host:5432/dbname
```

If your target PostgreSQL already contains old data and you want to replace it:

```bash
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path ./data/incluscape.db \
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
| Customer demo | Streamlit Community Cloud | Gemini | `SEMANTIC_LLM_PROVIDER=gemini`, `GEMINI_API_KEY=...`, `ENABLE_SEMANTIC_ANALYSIS=true` |

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
5. `bash scripts/pre_deploy_check.sh` passes
6. Demo dataset is present and recent outputs are clean
7. Commit message clearly describes customer-visible change
8. Push to `main` completed and cloud deployment is green

## Container Deployment

### Docker (single container)

```bash
docker build -t incluscape:latest .
docker run --rm -p 8501:8501 \
  --env-file .env \
  -e DATABASE_URL="postgresql://user:password@host:5432/dbname" \
  -e STORE_FILES_IN_DB=true \
  incluscape:latest
```

### Docker Compose (app + local PostgreSQL)

```bash
docker compose up --build
```

Then open: `http://localhost:8501`

For cloud container services (Cloud Run, Render, Fly.io, Azure Container Apps), use the same image built from `Dockerfile` and inject environment variables/secrets exactly as in `.env.example`.

## Project Structure

```
incluscape/
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
