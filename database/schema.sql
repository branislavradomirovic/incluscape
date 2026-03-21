-- ============================================================
-- INCLUSCAPE — SQLite Database Schema
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ------------------------------------------------------------
-- Organisations & Users
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS organisations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    organisation_id INTEGER NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    username        TEXT    NOT NULL UNIQUE,
    email           TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    role            TEXT    NOT NULL DEFAULT 'analyst' CHECK(role IN ('admin','analyst','viewer')),
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login      TIMESTAMP
);

-- ------------------------------------------------------------
-- Document storage & versioning
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    organisation_id INTEGER NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    uploaded_by     INTEGER REFERENCES users(id),
    title           TEXT    NOT NULL,
    document_type   TEXT    NOT NULL CHECK(document_type IN ('Questionnaire','Policies','Instructions','Forms','Reports','Monitoring')),
    file_name       TEXT    NOT NULL,
    file_path       TEXT    NOT NULL,
    file_size       INTEGER,
    mime_type       TEXT,
    file_hash       TEXT    NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    parent_id       INTEGER REFERENCES documents(id),
    status          TEXT    NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived','processing','error')),
    processed_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_org     ON documents(organisation_id);
CREATE INDEX IF NOT EXISTS idx_documents_hash    ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_parent  ON documents(parent_id);

CREATE TABLE IF NOT EXISTS document_blobs (
    document_id  INTEGER PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    content      BLOB NOT NULL,
    mime_type    TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Extracted content
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_pages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    content     TEXT,
    page_type   TEXT    DEFAULT 'text' CHECK(page_type IN ('text','table','image','mixed')),
    word_count  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS extracted_entities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    entity_type TEXT    NOT NULL,  -- e.g. LOCATION, ORG, DATE, PERSON, POLICY_NUMBER
    entity_text TEXT    NOT NULL,
    context     TEXT,
    confidence  REAL    DEFAULT 0.0,
    page_number INTEGER,
    char_start  INTEGER,
    char_end    INTEGER
);

CREATE INDEX IF NOT EXISTS idx_entities_doc  ON extracted_entities(document_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON extracted_entities(entity_type);

-- ------------------------------------------------------------
-- Report templates
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS report_templates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    organisation_id INTEGER NOT NULL REFERENCES organisations(id),
    name            TEXT    NOT NULL,
    description     TEXT,
    template_json   TEXT    NOT NULL,  -- JSON field definitions
    created_by      INTEGER REFERENCES users(id),
    version         INTEGER NOT NULL DEFAULT 1,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS template_fields (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id     INTEGER NOT NULL REFERENCES report_templates(id) ON DELETE CASCADE,
    field_key       TEXT    NOT NULL,
    field_label     TEXT    NOT NULL,
    field_type      TEXT    NOT NULL DEFAULT 'text'
                    CHECK(field_type IN ('text','number','date','boolean','list','location','table')),
    description     TEXT,
    is_required     INTEGER NOT NULL DEFAULT 0,
    default_value   TEXT,
    validation_rule TEXT,
    extraction_hint TEXT,   -- keywords/phrases that hint at this field in documents
    display_order   INTEGER NOT NULL DEFAULT 0
);

-- ------------------------------------------------------------
-- Generated reports
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    organisation_id INTEGER NOT NULL REFERENCES organisations(id),
    template_id     INTEGER NOT NULL REFERENCES report_templates(id),
    name            TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','complete','archived')),
    generated_by    INTEGER REFERENCES users(id),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS report_values (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id   INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    field_id    INTEGER NOT NULL REFERENCES template_fields(id),
    document_id INTEGER REFERENCES documents(id),
    raw_value   TEXT,
    typed_value TEXT,
    confidence  REAL    DEFAULT 0.0,
    is_verified INTEGER NOT NULL DEFAULT 0,
    verified_by INTEGER REFERENCES users(id),
    verified_at TIMESTAMP,
    notes       TEXT
);

-- link a report to the source documents it was built from
CREATE TABLE IF NOT EXISTS report_sources (
    report_id   INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    PRIMARY KEY (report_id, document_id)
);

-- ------------------------------------------------------------
-- Change tracking
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS document_changes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id     INTEGER NOT NULL REFERENCES documents(id),
    previous_doc_id INTEGER REFERENCES documents(id),
    change_type     TEXT    NOT NULL CHECK(change_type IN ('created','updated','deleted','restored')),
    changed_fields  TEXT,   -- JSON list of changed field keys
    diff_summary    TEXT,
    impact_level    TEXT    DEFAULT 'low' CHECK(impact_level IN ('low','medium','high','critical')),
    detected_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detected_by     INTEGER REFERENCES users(id)
);

-- ------------------------------------------------------------
-- Geospatial locations
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS locations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    place_name  TEXT    NOT NULL,
    latitude    REAL,
    longitude   REAL,
    location_type TEXT  DEFAULT 'general',
    context     TEXT,
    geocoded    INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Audit log
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id),
    action      TEXT    NOT NULL,
    entity_type TEXT,
    entity_id   INTEGER,
    detail      TEXT,
    ip_address  TEXT,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Semantic / Compliance Analysis
-- ------------------------------------------------------------

-- Reference templates sourced from international bodies (UN, UNESCO, EU, …)
CREATE TABLE IF NOT EXISTS reference_templates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    body            TEXT    NOT NULL,  -- UN | UNESCO | EU | World Bank | OECD | National | Other
    category        TEXT    NOT NULL,  -- Policies | Reports | Questionnaire | …
    name            TEXT    NOT NULL,
    description     TEXT,
    source_url      TEXT,              -- official source URL for the reference framework
    source_hash     TEXT,              -- hash of fetched source content
    source_last_checked TIMESTAMP,     -- last successful source check
    effective_date  TIMESTAMP,         -- when this template version became active
    supersedes_template_id INTEGER REFERENCES reference_templates(id),
    change_summary  TEXT,
    file_path       TEXT,              -- path to JSON file under reference_templates/
    key_sections    TEXT,              -- JSON array
    key_requirements TEXT,             -- JSON array
    keywords        TEXT,              -- JSON array
    version         TEXT    NOT NULL DEFAULT '1.0',
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ref_tmpl_body     ON reference_templates(body);
CREATE INDEX IF NOT EXISTS idx_ref_tmpl_category ON reference_templates(category);

-- Results of Gemini-powered semantic comparison for each uploaded document
CREATE TABLE IF NOT EXISTS semantic_analyses (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id           INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    reference_template_id INTEGER REFERENCES reference_templates(id),
    model_used            TEXT,
    body_detected         TEXT,
    category_detected     TEXT,
    compliance_score      REAL,       -- 0.0 – 1.0
    present_elements      TEXT,       -- JSON array
    missing_elements      TEXT,       -- JSON array
    partial_elements      TEXT,       -- JSON array
    strengths             TEXT,       -- JSON array
    gaps                  TEXT,       -- JSON array
    recommendations       TEXT,       -- JSON array
    summary               TEXT,
    full_response_json    TEXT,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sem_analysis_doc ON semantic_analyses(document_id);
