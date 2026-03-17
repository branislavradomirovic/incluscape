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
| Database | SQLite |
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

# 3. Initialize the project (creates dirs, .env, database)
python setup.py

# 4. Install dependencies
pip install -r requirements.txt

# 5. (Optional) Download the spaCy model
python -m spacy download en_core_web_sm

# 6. Run the application
streamlit run streamlit_app/app.py
```

The app will be available at **http://localhost:8501**

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
