import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.sidebar import render_page_disclaimer, render_sidebar

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HELP_IMAGE_ROOTS = [
   PROJECT_ROOT / "assets" / "help",
   PROJECT_ROOT / "assets",
   PROJECT_ROOT / "landing_page_assets",
]

VISUAL_CALLOUTS = {
   "Home": {
      "focus": "Dashboard overview",
      "highlights": [
         "The KPI cards at the top summarize the current workspace state: documents, templates, reports, and detected changes.",
         "The geo-scope panel underneath shows where extracted locations are concentrated and whether the dashboard is using policy-only or fallback geocoded data.",
         "This screen is the fastest place to confirm that ingestion, reporting, and geospatial extraction are all populated.",
      ],
   },
   "Documents": {
      "focus": "Upload and library workflow",
      "highlights": [
         "The upload controls are the entry point for new PDFs, Word files, and spreadsheets.",
         "The document library beneath the uploader is the operational list where users review titles, document type, processing state, and available actions.",
         "This screenshot is intended to show both ingestion and post-processing management in one frame.",
      ],
   },
   "Templates": {
      "focus": "Template builder",
      "highlights": [
         "The main form defines the template name and the extraction schema that downstream reports rely on.",
         "Field rows represent the exact structure SIPMT will try to populate from uploaded documents.",
         "This screen is the reference view for how a reporting schema is authored before extraction begins.",
      ],
   },
   "Reports": {
      "focus": "Report generation flow",
      "highlights": [
         "The top selectors determine which template and which documents are used for the extraction run.",
         "The results region shows extracted values, confidence signals, and generated report outputs once processing completes.",
         "This image should help users connect report setup with the saved/generated outputs that appear lower on the page.",
      ],
   },
   "Changes": {
      "focus": "Version comparison view",
      "highlights": [
         "Recent change entries summarize which document revisions were detected and when they were stored.",
         "The comparison widget is where two versions are placed side-by-side to inspect additions, deletions, and modifications.",
         "This screenshot emphasizes the audit trail and the detailed diff workflow together.",
      ],
   },
   "Map": {
      "focus": "Geospatial exploration",
      "highlights": [
         "The map itself is the primary widget, showing geocoded locations extracted from documents.",
         "Supporting panels such as the extraction summary and location list explain what was found and from which documents it came.",
         "This image should orient users to both the visual map and the underlying extracted location records.",
      ],
   },
   "KPIs & Charts": {
      "focus": "Metric interpretation",
      "highlights": [
         "The screenshot anchors the KPI explanations to a real dashboard view so users can identify each metric card visually.",
         "It also shows where the map/chart region sits relative to the numeric summary cards.",
         "Use this callout when explaining what the dashboard is counting and where those values come from.",
      ],
   },
   "Sources": {
      "focus": "Reference source management",
      "highlights": [
         "The catalogue region displays the currently managed sources grouped by body, category, and refresh status.",
         "The source creation and refresh widgets drive how external standards are fetched and transformed into internal reference templates.",
         "This screenshot should make the governance workflow for compliance source material visible at a glance.",
      ],
   },
   "Compliance": {
      "focus": "Semantic analysis workspace",
      "highlights": [
         "The provider selection, document selection, and reference template controls define the analysis run configuration.",
         "Score summaries and charts explain both the final alignment result and the evidence behind it.",
         "This image is meant to show the full path from setup controls to analysis output in a single visual summary.",
      ],
   },
   "HRBA": {
      "focus": "AAAQ matching workflow",
      "highlights": [
         "The central view shows the document-level AAAQ matching process and any generated matches or scores.",
         "Live output or timeline panels expose how the selected model produced the result over time.",
         "This screenshot should help users understand that HRBA is both an analysis tool and an evidence capture workflow.",
      ],
   },
   "HRBA Insights": {
      "focus": "Saved analysis review",
      "highlights": [
         "The saved justifications table is the historical record of previously persisted HRBA findings.",
         "The raw entries section gives audit-level visibility into the stored payloads and explanations.",
         "This view is designed for review and evidence tracing rather than new analysis generation.",
      ],
   },
   "Developer & Admin": {
      "focus": "Operational controls",
      "highlights": [
         "This section is the operational reference for environment variables, troubleshooting steps, and maintenance commands.",
         "The paired screenshot should help administrators connect the written setup guidance with the visible admin interface.",
         "Use it when onboarding maintainers or diagnosing deployment and runtime configuration issues.",
      ],
   },
}


def _resolve_help_image(*candidates: str) -> Optional[Path]:
   for root in HELP_IMAGE_ROOTS:
      for candidate in candidates:
         image_path = root / candidate
         if image_path.exists():
            return image_path
   return None


def render_help_screenshot(section_name: str, caption: str, *candidates: str) -> None:
   image_path = _resolve_help_image(*candidates)
   callout = VISUAL_CALLOUTS.get(section_name, {})

   left_col, right_col = st.columns([1.75, 1.0], gap="large")
   with left_col:
      if image_path:
         st.image(str(image_path), width="stretch", caption=caption)
      else:
         joined_candidates = ", ".join(candidates)
         st.info(
            f"Screenshot for {section_name} will appear here when an asset is added as one of: {joined_candidates}."
         )

   with right_col:
      focus_label = callout.get("focus", "Screen focus")
      highlights = callout.get("highlights", [])
      st.markdown(f"### Visual Callout")
      st.markdown(f"**Primary focus:** {focus_label}")
      if highlights:
         st.markdown("**What To Look For**")
         for item in highlights:
            st.markdown(f"- {item}")
      st.markdown("**Image use in Help**")
      st.markdown(
         "Use this screenshot as the visual reference while reading the section guidance below. "
         "It is intended to connect the written workflow with the actual controls and outputs on the page."
      )
   st.markdown("")

st.set_page_config(page_title="Help — SIPMT", page_icon="❓", layout="wide")
render_sidebar()

st.title("❓ Help & Documentation")
st.markdown("Comprehensive guide to all features in SIPMT")
st.caption(
   "This help page can embed live application screenshots from the repository. "
   "Place section images under assets/help, assets, or landing_page_assets to populate them automatically."
)
st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────
# HOME
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🏠 **Home** — Overview Dashboard", expanded=True):
   render_help_screenshot(
      "Home",
      "Current dashboard screenshot showing KPI cards and the geo-scope area.",
      "home.png",
      "dashboard.png",
      "Dashboard.png",
   )
   st.markdown("""
    The **Home** page is your workspace dashboard, providing at-a-glance metrics and overview of your data.

    #### Key Features:

    **📊 Metrics Overview**
    - **Documents**: Total number of uploaded documents in the system
    - **Templates**: Number of defined report templates available
    - **Reports**: Count of generated reports from template + document combinations
    - **Changes Detected**: Number of change instances discovered via document version comparison

    **📍 Document Scope Map**
    - Displays an interactive map of all geographic locations extracted from **Policies** documents
    - Helps you visualize the geographic scope of your policy framework
    - Requires documents to be processed with location extraction enabled
    - Locations are geocoded (if `ENABLE_GEOCODING=True` in `.env`) and marked on an OpenStreetMap layer

    #### When to Use:
    - When you first open SIPMT to see workspace statistics
    - To understand the geographic reach of your policies
    - As a quick health check that documents are being processed
    """)

# ──────────────────────────────────────────────────────────────────────────
# DOCUMENTS
# ──────────────────────────────────────────────────────────────────────────
with st.expander("📄 **Documents** — Upload & Manage Source Files"):
   render_help_screenshot(
      "Documents",
      "Documents page screenshot with upload controls, categorisation options, and processing results.",
      "documents.png",
      "Documents.png",
      "page_documents.png",
   )
   st.markdown("""
    The **Documents** page is where you upload and manage all your source files.
    
    #### Supported File Formats:
    - **PDF** — Scanned documents, policy documents, reports (with or without embedded text)
    - **DOCX** — Microsoft Word documents, forms, instructions
    - **XLSX** — Excel spreadsheets, data tables, monitoring data

    #### File Size & Constraints:
    - **Maximum size per file**: 20 MB
    - **Multiple uploads**: You can upload multiple files at once
    - **Duplicate detection**: Files with identical content are automatically flagged and can be skipped

    #### Processing Steps:
    1. **Upload**: Select one or more files from your computer
    2. **Categorize**: Assign each file to one of six document types:
       - **Questionnaire** — Surveys, forms for data collection
       - **Policies** — Official policy frameworks, guidelines
       - **Instructions** — How-to guides, operational manuals
       - **Forms** — Templates, application forms, compliance forms
       - **Reports** — Monitoring reports, assessment reports, evaluations
       - **Monitoring** — Ongoing tracking documents, dashboards, KPI reports
    3. **Extract**: System automatically extracts:
       - **Text** — All text content from documents
       - **Tables** — Structured data formatted as CSV
       - **Named Entities** — People, organizations, locations identified via NLP
       - **Locations** — Geographic place names (countries, cities, regions)
    4. **Store**: Processed content is saved to the database for analysis

    #### Advanced Features:
    - **Re-process button**: For older documents that weren't fully extracted, re-run the entire pipeline
    - **View extracted text**: Click "View" next to a document to see extracted content
    - **Deletion**: Remove documents you no longer need (soft delete)

    #### When to Use:
    - To onboard new documents for analysis
    - To prepare documents for report generation or compliance checking
    - To update your data scope with new policy versions
    """)

# ──────────────────────────────────────────────────────────────────────────
# TEMPLATES
# ──────────────────────────────────────────────────────────────────────────
with st.expander("📋 **Templates** — Define Data Extraction Fields"):
   render_help_screenshot(
      "Templates",
      "Templates page screenshot with template form fields and extraction schema editor.",
      "templates.png",
      "Templates.png",
      "page_templates.png",
   )
   st.markdown("""
    The **Templates** page lets you create reusable field definitions for automated data extraction.
    
    #### What is a Template?
    A **report template** is a structured specification of the information you want to extract from documents:
    - A **name** that describes what the template captures (e.g., "Social Inclusion Indicators", "Health Policy Compliance Check")
    - A **set of fields**, each with:
      - **Field name** — A descriptive label (e.g., "Target Population", "Implementation Date")
      - **Field type** — The data type SIPMT will look for:
        - **Text** — Free-form text fields (e.g., description, summary)
        - **Number** — Numeric values (e.g., budget amount, percentage)
        - **Date** — Calendar dates (e.g., effective date, review date)
        - **Boolean** — Yes/No fields (e.g., "Is monitoring required?")
        - **List** — Comma-separated or bulleted values (e.g., stakeholder names)
        - **Location** — Place names, regions, countries
      - **Description** (optional) — Context to help the extractor
      - **Priority** — Whether field is Required or Optional

    #### Template Matching Process:
    Once you create a template, SIPMT uses **fuzzy matching** to automatically find corresponding values in documents:
    1. Field name is compared against extracted document text
    2. Semantic analyzer (Gemini or Ollama) helps interpret intent
    3. Matched values are auto-filled in generated reports

    #### Creating a Template:
    1. Click **"Create New Template"**
    2. Enter template name
    3. Add fields using the table widget:
       - Specify field name, type, description
       - Mark Required/Optional
    4. Click "Save Template"

    #### Use Cases:
    - Define fields for different document types (policies, reports, questionnaires)
    - Create institution-specific templates for consistent data extraction
    - Enable standardized reporting across multiple documents

    #### When to Use:
    - Before generating reports — define the structure first
    - When you want consistent data extraction across similar documents
    - To standardize information collection
    """)

# ──────────────────────────────────────────────────────────────────────────
# REPORTS
# ──────────────────────────────────────────────────────────────────────────
with st.expander("📊 **Reports** — Generate Structured Data Extracts"):
   render_help_screenshot(
      "Reports",
      "Reports page screenshot with template selection, document selection, extracted values, and export actions.",
      "reports.png",
      "Reports.png",
      "page_reports.png",
   )
   st.markdown("""
    The **Reports** page handles automated extraction of structured data using templates.
    
    #### The Report Generation Workflow:
    1. **Select Template** — Choose which template defines the extraction fields
    2. **Select Documents** — Pick one or more source documents to extract from
    3. **Run Extraction** — System processes the documents with fuzzy matching + semantic analysis
    4. **Review Results** — View extracted values, confidence scores, and any missing fields
    5. **Export Report** — Save as CSV, JSON, or Excel for downstream analysis

    #### Extraction Confidence:
    - Each extracted field includes a **confidence score** (0–100%)
    - **High confidence** (>80%) — Field was clearly identified in the source
    - **Medium confidence** (50–80%) — Field found but with some uncertainty
    - **Low confidence** (<50%) — Weak match; manual review recommended
    - **Missing** — Field not found in any of the selected documents

    #### Feature Highlights:
    - **Batch extraction** — Process multiple documents at once against same template
    - **Field review** — Manually edit extracted values before export
    - **Audit trail** — Each report captures which documents were used and when
    - **Storage** — All generated reports are saved to the database
    - **Export formats** — CSV (spreadsheet), JSON (system integration), PDF (sharing)

    #### When to Use:
    - To fill standardized reporting forms automatically
    - To compile consistent data from many similar documents
    - To create CSVs for further analysis or visualization
    - When you need verified extracted values with confidence scores
    """)

# ──────────────────────────────────────────────────────────────────────────
# CHANGES
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🔍 **Changes** — Track Document Versions"):
   render_help_screenshot(
      "Changes",
      "Changes page screenshot with version comparison output and detected differences.",
      "changes.png",
      "Changes.png",
      "page_changes.png",
   )
   st.markdown("""
    The **Changes** page detects and visualizes differences between document versions.
    
    #### Change Tracking Workflow:
    1. **Automatic Detection** — When you upload a revised version of an existing document,
       SIPMT detects it has the same name but different content
    2. **Diff Generation** — The system runs a comparison to identify:
       - **Added** — New sections, paragraphs, or content
       - **Removed** — Sections deleted in the new version
       - **Modified** — Text that changed but wasn't added/removed
    3. **Visualization** — Side-by-side display with color highlighting:
       - 🟢 **Green** — Added content
       - 🔴 **Red** — Removed content
       - 🟡 **Yellow** — Modified content

    #### Change Audit:
    - **Timestamp** — Exactly when each version was uploaded
    - **Size delta** — How many bytes changed between versions
    - **Persistent storage** — All detected changes are saved for compliance auditing

    #### Use Cases:
    - Track policy evolution over time
    - Monitor when instructions or procedures have been updated
    - Ensure you're aware of all changes to reference documents
    - Create a versioning audit trail for compliance reporting

    #### When to Use:
    - When you upload a new version of an existing document
    - To review what changed in a policy update
    - For compliance audits that require change tracking
    - Before adopting a new document version
    """)

# ──────────────────────────────────────────────────────────────────────────
# MAP
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🗺️ **Map** — Geospatial Visualization"):
   render_help_screenshot(
      "Map",
      "Map page screenshot with document location markers and geographic filters.",
      "map.png",
      "Map.png",
      "page_map.png",
   )
   st.markdown("""
    The **Map** page provides interactive geographic visualization of extracted locations.
    
    #### How It Works:
    1. **Location Extraction** — When documents are processed, place names are identified using:
       - **Pattern matching** — Recognizes known country/region strings
       - **NLP (spaCy)** — Named Entity Recognition for place mentions
    2. **Geocoding** (optional):
       - If `ENABLE_GEOCODING=True` in `.env`, each place name is converted to latitude/longitude
       - Uses **Nominatim** (OpenStreetMap's free geocoding service)
       - Requires internet connectivity
    3. **Visualization** — Interactive map shows:
       - **Markers** — Each location pinned on OpenStreetMap
       - **Pop-ups** — Click marker to see document source and context
       - **Zoom/Pan** — Explore the geographic scope interactively

    #### Map Features:
    - **Filter by document type** — Show only locations from Policies, Reports, Monitoring, etc.
    - **Zoom to region** — Focus on a specific geographic area
    - **Export map** — Save as HTML or screenshot for presentations

    #### Configuration:
    - **Enable geocoding**: Set `ENABLE_GEOCODING=True` in your `.env` file
    - **Select documents**: Choose which documents to visualize
    - **Update locations**: Re-process documents to extract new locations

    #### Use Cases:
    - Visualize coverage area of policies and programs
    - Identify geographic gaps in implementations
    - Share scope with stakeholders in an interactive format
    - Plan regional expansion or resource allocation

    #### When to Use:
    - After uploading Policies or Programs documents
    - To brief stakeholders on geographic scope
    - For regional analysis and planning
    - In presentations or reports to show coverage
    """)

# ──────────────────────────────────────────────────────────────────────────
# KPIS & CHARTS
# ──────────────────────────────────────────────────────────────────────────
with st.expander("📈 **KPIs & Charts — Definitions, Data Sources, and Population Details", expanded=False):
   render_help_screenshot(
      "KPIs & Charts",
      "Dashboard screenshot used as a reference for KPI cards and the geo-scope overview chart area.",
      "dashboard.png",
      "Dashboard.png",
      "kpis.png",
   )
   st.markdown("""
      This section explains every KPI shown on the **Home** dashboard and every chart used across the application: what each metric represents, which DB tables and queries populate it, how often it updates, and any caveats.

      **General notes**
      - All KPIs on the dashboard are read-only aggregates run against the `documents`, `report_templates`, `reports`, and `document_changes` tables.
      - Charts may be rendered from aggregated SQL queries or from in-memory analysis payloads saved in JSON columns (for semantic analyses and reports).
      - Dashboard values are computed at render time; they reflect the current contents of the database when the page is loaded or when the user navigates to the page.

      ---

      **Dashboard KPIs (Home page)**

      - **Documents** (label: "📄 Documents")
         - What it represents: Total count of document records stored for the current organisation.
         - Data source / SQL: `SELECT COUNT(*) FROM documents WHERE organisation_id = ?`
         - How it's created: incremented when a new document is uploaded and processed; deletions reduce the count (soft-deletes respect `status` field).
         - Update frequency: real-time at page render.

      - **Templates** (label: "📋 Templates")
         - What it represents: Number of saved report templates available for extraction & reporting.
         - Data source / SQL: `SELECT COUNT(*) FROM report_templates`
         - How it's created: created via the Templates page when the user saves a new template.
         - Caveats: template bodies may include large JSON; the KPI counts templates regardless of body size or source (DB or file-imported).

      - **Reports** (label: "📊 Reports")
         - What it represents: Count of generated reports (structured extraction outputs) stored in `reports` table.
         - Data source / SQL: `SELECT COUNT(*) FROM reports WHERE organisation_id = ?`
         - How it's created: when a user runs extraction against documents and saves or exports results.

      - **Changes detected** (label: "🔍 Changes detected")
         - What it represents: Number of detected change instances (diff records) between document versions.
         - Data source / SQL: `SELECT COUNT(*) FROM document_changes WHERE organisation_id = ?`
         - How it's created: when a new upload is identified as a new version of an existing document and the diff process creates change rows.

      ---

      **Map & Location Data**
      - The scope map shows geocoded `locations` joined to `documents` (see `locations` table).
      - Primary SQL used for the dashboard map (Policies-preferred):
         - Policies restricted: SELECT rows from `locations` JOIN `documents` WHERE `document_type = 'Policies'` AND `geocoded = 1`.
         - Fallback: all geocoded locations when Policies have none.
      - How markers are populated: each geocoded `location` row provides `latitude`/`longitude`, `place_name`, `context` and `document_title` used in the pop-up.

      ---

      **Compliance page charts & KPIs**
      - **Compliance Score**
         - What it represents: a normalized alignment score (0–1) computed by `ComplianceChecker` combining keyword, requirement, and section coverage with small body/category bonuses.
         - How it's computed: see `_score_reference_template` and `_build_executive_summary` in the compliance page code — the algorithm combines token-coverage metrics and applies weights (keywords 45%, requirements 35%, sections 20% plus bonuses).
         - Source: analysis payloads stored in `semantic_analyses` and the temporary result in-memory while running the analysis.

      - **SHAP-style heatmap (feature contribution proxy)**
         - What it represents: an explainability proxy that shows which factors (Present elements, Strengths, Missing, Partial, Gaps, Recommendation pressure, Keyword/Requirement/Section coverage) contributed positively or negatively to the final compliance score.
         - How it's created: `_compute_shap_proxy` aggregates counts from the analysis result and returns normalized contribution values between -1 and +1.
         - Chart population: uses Plotly Heatmap with a single-row `z` array of contributions and an explicit color scale centered at 0.

      - **Classification & Comparison score histories (line/points)**
         - What they represent: time-series of the classifier confidence and template comparison scores for the current monitor session or historical analyses.
         - Source: `classification_confidence_history` and `comparison_score_history` arrays maintained in the compliance monitor state; persisted analyses are available via `checker.get_analyses(document_id)`.
         - How populated: appended as the monitor runs each stage (classify, match, compare, persist). Charts use Plotly `scatter` or `line` traces with points recorded in `*_points` lists.

      - **Gantt-style timeline (per-segment timeline)**
         - What it represents: per-segment generation timing when streaming LLM outputs; bars are sized by score and colored by AAAQ label.
         - Source: streaming chunks processed during Ollama/Gemini runs, each tracked with start/end and assigned category/score.
         - How populated: compliance monitor records chunk timestamps and scores into `chunk_history`; the timeline is rendered from those records.

      ---

      **HRBA page visuals**
      - **Live streaming preview**: incremental text from the LLM while running a HRBA analysis. Populated by streaming HTTP responses from Ollama (if supported) or replaced by final JSON when streaming not available.
      - **Per-segment Gantt**: same mechanism as Compliance timeline — segments are generated and timed during model runs.

      ---

      **Other charts across the app**
      - **Template source health table**: a diagnostics table produced by `_probe_source_url_health` that verifies external source URLs for templates; populated by issuing HEAD/GET requests and collecting HTTP status and suggestions.
      - **Map exports & filters**: map layers are created by `MapGenerator.build_map()` using the `scope_locations` rows; filters are executed by SQL before the map is built.

      ---

      **Troubleshooting & caveats**
      - If a KPI is unexpectedly zero or stale, check whether your organisation filter (`organisation_id`) is set and whether documents have `status='active'`.
      - Semantic analysis-derived charts rely on cached analysis payloads; re-run analyses or clear cache if you believe stale results are shown.
      - Charts that rely on LLM streaming require the selected provider to support streaming; otherwise charts will update once the final response arrives.

      """)

# ──────────────────────────────────────────────────────────────────────────
# SOURCES
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🌐 **Sources** — Reference Catalogue & Refresh Workflow"):
   render_help_screenshot(
      "Sources",
      "Sources page screenshot showing the reference catalogue, source management, and refresh controls.",
      "sources.png",
      "Sources.png",
      "page_sources.png",
   )
   st.markdown("""
    The **Sources** page manages the official external reference material used by the compliance engine.

    #### What This Page Does:
    - Lists all configured source catalog entries and reference bodies
    - Lets you add new official URLs for standards, directives, and guidance notes
    - Runs refresh workflows to fetch source pages and update the internal template database
    - Shows a current database snapshot of the active reference set

    #### Main Interface Elements:
    - **Catalogue table** — Displays the current source records, grouped by body and category
    - **Add new source form** — Creates a new source entry with body, label, URL, and file hint
    - **Fetch / enrich controls** — Pulls source content from the internet, then enriches it with the selected provider
    - **DB snapshot section** — Shows the currently materialized template records used by compliance analysis

    #### When to Use:
    - When new international or institutional guidance needs to be added
    - When existing external URLs changed and references must be refreshed
    - Before running compliance analyses that depend on newly updated source material
    """)

# ──────────────────────────────────────────────────────────────────────────
# COMPLIANCE
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🔎 **Compliance** — Semantic Analysis Against Standards"):
   render_help_screenshot(
      "Compliance",
      "Compliance page screenshot with provider selector, reference template selection, score outputs, and charts.",
      "compliance.png",
      "Compliance.png",
      "page_compliance.png",
   )
   st.markdown("""
    The **Compliance** page provides advanced AI-powered semantic analysis of your documents
    against international reference frameworks.
    
    #### Semantic Analysis Workflow:
    1. **Provider Selection** — Choose your AI backend:
       - **Google Gemini** (cloud, requires API key) — Advanced reasoning, internet connectivity
       - **Ollama** (local, self-hosted) — Privacy-preserving, offline operation
    2. **Health Check** — Verify the selected AI provider is reachable and working
    3. **Document Selection** — Choose which document to analyze
    4. **Reference Template** — Select an international framework (UN, UNESCO, EU, etc.)
    5. **Run Analysis** — AI compares document against reference framework
    6. **Review Report** — Structured compliance assessment with recommendations

    #### Reference Frameworks Available:
    - **UN Human Rights** — Universal Declaration of Human Rights frameworks
    - **UN Sustainable Development Goals (SDGs)** — Goal 10 (Reduced Inequalities) focused
    - **UNESCO Education** — Inclusive education standards and guidelines
    - **EU Equality Directive** — EU equality and non-discrimination standards
    - **EU Social Inclusion** — Social cohesion and inclusion directives

    #### Compliance Report Structure:
    - **Document Classification** — AI categorizes the document type/scope
    - **Compliance Score** — 0–100% alignment with reference framework
    - **Present Elements** — Which requirements are already addressed
    - **Identified Gaps** — Missing or underspecified areas
    - **Recommendations** — Actionable steps to improve compliance
    - **Source References** — Links to relevant external standards

    #### Advanced Features:
    - **Template Version History** — Admin view of reference template updates and lineage
    - **Refresh Sources** — Manually update reference templates from external sources
    - **Error Transparency** — Clear error messages if provider is down

    #### Model Configuration:
    - **Gemini**: Requires `GEMINI_API_KEY` in `.env`, set `SEMANTIC_LLM_PROVIDER=gemini`
    - **Ollama**: Requires Ollama service running locally, set `SEMANTIC_LLM_PROVIDER=ollama`
    - **Model selection**: Configure via `OLLAMA_MODEL` in `.env` (default: qwen2.5:14b-instruct)

    #### When to Use:
    - To assess policy alignment with international standards
    - For compliance reporting and auditing
    - To identify gaps in your social inclusion framework
    - Before finalizing new policies or procedures
    - For stakeholder reporting on standards compliance
    """)

# ──────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("⚙️ **Configuration** — Environment Setup"):
    st.markdown("""
    #### Key Configuration Options (in `.env` file)

    **Document Processing**
    - `UPLOAD_FOLDER` — Directory where uploaded files are stored
    - `ALLOWED_EXTENSIONS` — File types to accept (pdf, docx, xlsx)
    - `MAX_FILE_SIZE_MB` — Server-side file size limit
    - `ENABLE_OCR` — Extract text from scanned/image documents

    **Semantic Analysis**
    - `ENABLE_SEMANTIC_ANALYSIS` — Turn semantic compliance analysis on/off
    - `SEMANTIC_LLM_PROVIDER` — Choose `gemini` or `ollama`
    - `GEMINI_API_KEY` — Your Google Gemini API key (for cloud analysis)
    - `GEMINI_MODEL` — Model name (default: `gemini-2.0-flash`)
    - `OLLAMA_BASE_URL` — Ollama service endpoint (default: `http://localhost:11434`)
    - `OLLAMA_MODEL` — Local model to use (default: `qwen2.5:14b-instruct`)

    **Geospatial**
    - `ENABLE_GEOCODING` — Enable automatic geocoding of locations (requires internet)

    **Logging**
    - `LOG_FILE` — Path to application logs
    - `LOG_LEVEL` — Verbosity (DEBUG, INFO, WARNING, ERROR)

    #### Getting Started with Different Providers:

    **Using Google Gemini**
    ```
    SEMANTIC_LLM_PROVIDER=gemini
    GEMINI_API_KEY=your-api-key-here
    GEMINI_MODEL=gemini-2.0-flash
    ```
    [Get API key →](https://ai.google.dev)

    **Using Ollama (Local)**
    ```
    SEMANTIC_LLM_PROVIDER=ollama
    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_MODEL=qwen2.5:14b-instruct
    ```
    [Ollama Installation →](https://ollama.ai)

    Then pull the model:
    ```bash
    ollama pull qwen2.5:14b-instruct
    ```
    """)

# ──────────────────────────────────────────────────────────────────────────
# HRBA
# ──────────────────────────────────────────────────────────────────────────
with st.expander("⚖️ **HRBA — AAAQ Matching & Insights"):
   render_help_screenshot(
      "HRBA",
      "HRBA page screenshot with AAAQ matches, live output, and timeline visualisations.",
      "hrba.png",
      "HRBA.png",
      "page_hrba.png",
   )
   st.markdown("""
      The **HRBA** page scans documents for AAAQ indicators (Availability, Accessibility,
      Acceptability, Quality) using either a fast `spaCy` matcher or the local Ollama LLM.

      Key features:
      - **Live streaming generation**: When using Ollama the app displays a live text preview
         of the model's output in a right-side pane while the model is generating.
      - **Per-segment timeline (Gantt)**: The page records per-segment start/end times during
         streaming and renders a Gantt-style timeline showing when each segment was generated.
         Bars are sized by score and colored by the highest-scoring AAAQ category.
      - **Save analyses**: Store full JSON justifications into `semantic_analyses` for later review
         on the **HRBA Insights** page.

      How to interpret the UI:
      - The **live preview** shows incremental text as the model streams. If the model returns
         only a final JSON object, the preview will update when the final content arrives.
      - The **timeline** visualises per-document generation events. Longer bars indicate
         higher scoring results (length is proportional to score). Use the timeline to spot
         slow segments or clustering of analyses by document.

      Troubleshooting:
      - If you see no streaming chunks, ensure `OLLAMA_BASE_URL` and `OLLAMA_MODEL` are correct
         and the Ollama service is running. Some models may not stream intermediate fragments.
      - For long-running generations, increase `OLLAMA_TIMEOUT` in your environment (seconds).
      - If generation appears slow, warm the model or restart the Ollama process.
      """)

# ──────────────────────────────────────────────────────────────────────────
# HRBA INSIGHTS
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🧾 **HRBA Insights** — Saved Justifications & Review"):
   render_help_screenshot(
      "HRBA Insights",
      "HRBA Insights screenshot showing saved justifications, aggregated views, and raw saved entries.",
      "hrba_insights.png",
      "HRBA_Insights.png",
      "page_hrba_insights.png",
   )
   st.markdown("""
    The **HRBA Insights** page is the review workspace for previously saved AAAQ analyses.

    #### What You See Here:
    - **Saved Justifications table** — A structured view of all persisted HRBA justifications
    - **Filters and grouping** — Lets you narrow results by document or analysis context
    - **Raw entries** — Full stored payloads for auditing, export, or manual inspection

    #### What It Represents:
    - Each row corresponds to a saved analysis record previously stored from the HRBA match workflow
    - This page is not generating new analyses; it is reading historical records from storage

    #### When to Use:
    - To review previously generated human-rights-based analyses
    - To compare justification quality across documents
    - To audit the saved evidence that supports HRBA findings
    """)

# ──────────────────────────────────────────────────────────────────────────
# Developer & Admin
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🛠️ Developer & Admin — Setup, Env vars, Troubleshooting", expanded=False):
   render_help_screenshot(
      "Developer & Admin",
      "Developer and admin screenshot with environment, maintenance, and troubleshooting utilities.",
      "developer_admin.png",
      "Developer_Admin.png",
      "page_admin.png",
   )
   st.markdown("""
      This section covers environment variables, common admin tasks, and troubleshooting steps.

      Environment variables (important):
      - `DATABASE_URL`: full PostgreSQL connection string. If not present, `DATABASE_PATH` (SQLite) is used.
      - `DATABASE_PATH`: path to fallback SQLite database (default `./data/sipmt.db`).
      - `FORCE_POSTGRES`: if set to `1`, force use of `DATABASE_URL` even when it points to localhost.
      - `SEMANTIC_LLM_PROVIDER`: `gemini` or `ollama`.
      - `GEMINI_API_KEY`: required when `SEMANTIC_LLM_PROVIDER=gemini`.
      - `OLLAMA_BASE_URL`: local Ollama endpoint (default `http://localhost:11434`).
      - `OLLAMA_MODEL`: Ollama model name (e.g., `qwen2.5:14b-instruct`).
      - `OLLAMA_TIMEOUT`: HTTP timeout for Ollama requests (seconds). Default 120.
      - `ENABLE_GEOCODING`: `true`/`false` to enable geocoding of extracted locations.

      Common admin tasks:
      - Initialize DB and directories:
         ```bash
         python setup.py
         ```
      - Migrate existing SQLite demo data to Postgres:
         ```bash
         python scripts/migrate_sqlite_to_postgres.py --sqlite-path ./data/sipmt.db --postgres-url <YOUR_URL>
         ```
      - Pull Ollama model (local machine):
         ```bash
         ollama pull qwen2.5:14b-instruct
         ```

      Troubleshooting tips:
      - App fails to start: run `bash scripts/pre_deploy_check.sh` to locate syntax or config issues.
      - Ollama unreachable: confirm `OLLAMA_BASE_URL`, try `curl http://localhost:11434/`.
      - Slow semantic analysis: increase `OLLAMA_TIMEOUT`, warm the model by making a small request, or choose a smaller model.
      - Missing extracted text: verify OCR settings and re-run the document extractor pipeline.

      Logs and diagnostics:
      - Check `logs/` for recent app logs.
      - Streamlit console shows startup errors; consult server logs for stack traces.

      Security & secrets:
      - Never commit secrets (API keys, DB passwords) to git. Use platform secrets or an `.env` file excluded from VCS.
      - Rotate API keys if they are accidentally exposed.
      """)

# ──────────────────────────────────────────────────────────────────────────
# TIPS & BEST PRACTICES
# ──────────────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("💡 **Tips & Best Practices"):
    st.markdown("""
    #### Document Upload Tips
    - **Quality matters**: Ensure scanned PDFs have good resolution (≥200 DPI) for better text extraction
    - **File naming**: Use descriptive names (e.g., `Policy_2024_Social_Inclusion.pdf`) for easy tracking
    - **Organize by type**: Categorize documents correctly — this helps template matching
    - **Version control**: Upload versioned documents (v1, v2) to track evolution

    #### Template Design
    - **Be specific**: More detailed field descriptions help the matcher find values
    - **Use consistent naming**: Similar fields across templates should have similar names
    - **Set realistic priorities**: Mark truly required fields, keep others optional
    - **Test first**: Create a template and test with 1–2 documents before batch processing

    #### Report Generation
    - **Review low-confidence fields**: Always verify extractions with <70% confidence
    - **Document sources**: Keep records of which documents were used for each report
    - **Export regularly**: Save reports as CSV/JSON for backup and integration with other tools

    #### Compliance Analysis
    - **Read recommendations**: AI-generated gaps often contain actionable improvements
    - **Cross-check references**: Verify external links in recommendations are correct
    - **Track changes**: Re-run analysis after document updates to show progress
    - **Use version history**: Review how reference templates evolve over time

    #### Performance Tips
    - **Batch processing**: Upload multiple documents at once for efficiency
    - **Local Ollama**: Use Ollama instead of Gemini for faster, offline analysis
    - **Disable geocoding**: Turn off if you don't need location mapping (faster processing)
    - **Clean up old data**: Archive or delete documents you no longer analyze

    #### Troubleshooting
    - **Upload fails**: Ensure file is <20 MB and is PDF/DOCX/XLSX format
    - **No extracted text**: Use "Re-process" button on Documents page
    - **Compliance analysis slow**: Check internet connection (for Gemini) or Ollama service status
    - **Map shows no locations**: Ensure documents were categorized as "Policies"
    """)

st.markdown("---")
st.markdown("""
#### 📞 Need More Help?
- **Check the sidebar** — Navigation and quick tips on every page
- **Hover tooltips** — Many UI elements have context help on hover
- **Report issues** — Contact your system administrator with error messages

---
*Last updated: March 2026 | SIPMT v1.0*
""")

render_page_disclaimer()
