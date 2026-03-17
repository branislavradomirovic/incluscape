import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
from streamlit_app.components.sidebar import render_sidebar

st.set_page_config(page_title="Help — INCLUSCAPE", page_icon="❓", layout="wide")
render_sidebar()

st.title("❓ Help & Documentation")
st.markdown("Comprehensive guide to all features in INCLUSCAPE")
st.markdown("---")

# ──────────────────────────────────────────────────────────────────────────
# HOME
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🏠 **Home** — Overview Dashboard", expanded=True):
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
    - When you first open INCLUSCAPE to see workspace statistics
    - To understand the geographic reach of your policies
    - As a quick health check that documents are being processed
    """)

# ──────────────────────────────────────────────────────────────────────────
# DOCUMENTS
# ──────────────────────────────────────────────────────────────────────────
with st.expander("📄 **Documents** — Upload & Manage Source Files"):
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
    st.markdown("""
    The **Templates** page lets you create reusable field definitions for automated data extraction.
    
    #### What is a Template?
    A **report template** is a structured specification of the information you want to extract from documents:
    - A **name** that describes what the template captures (e.g., "Social Inclusion Indicators", "Health Policy Compliance Check")
    - A **set of fields**, each with:
      - **Field name** — A descriptive label (e.g., "Target Population", "Implementation Date")
      - **Field type** — The data type INCLUSCAPE will look for:
        - **Text** — Free-form text fields (e.g., description, summary)
        - **Number** — Numeric values (e.g., budget amount, percentage)
        - **Date** — Calendar dates (e.g., effective date, review date)
        - **Boolean** — Yes/No fields (e.g., "Is monitoring required?")
        - **List** — Comma-separated or bulleted values (e.g., stakeholder names)
        - **Location** — Place names, regions, countries
      - **Description** (optional) — Context to help the extractor
      - **Priority** — Whether field is Required or Optional

    #### Template Matching Process:
    Once you create a template, INCLUSCAPE uses **fuzzy matching** to automatically find corresponding values in documents:
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
    st.markdown("""
    The **Changes** page detects and visualizes differences between document versions.
    
    #### Change Tracking Workflow:
    1. **Automatic Detection** — When you upload a revised version of an existing document,
       INCLUSCAPE detects it has the same name but different content
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
# COMPLIANCE
# ──────────────────────────────────────────────────────────────────────────
with st.expander("🔎 **Compliance** — Semantic Analysis Against Standards"):
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
*Last updated: March 2026 | INCLUSCAPE v1.0*
""")
