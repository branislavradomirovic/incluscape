-- SIPMT — PostgreSQL Database Schema
CREATE TABLE IF NOT EXISTS organisations (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    organisation_id BIGINT NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    username        TEXT    NOT NULL UNIQUE,
    email           TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    role            TEXT    NOT NULL DEFAULT 'analyst' CHECK(role IN ('admin','analyst','viewer')),
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login      TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id              BIGSERIAL PRIMARY KEY,
    organisation_id BIGINT NOT NULL REFERENCES organisations(id) ON DELETE CASCADE,
    uploaded_by     BIGINT REFERENCES users(id),
    title           TEXT    NOT NULL,
    document_type   TEXT    NOT NULL CHECK(document_type IN ('Questionnaire','Policies','Instructions','Forms','Reports','Monitoring')),
    file_name       TEXT    NOT NULL,
    file_path       TEXT    NOT NULL,
    file_size       BIGINT,
    mime_type       TEXT,
    file_hash       TEXT    NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    parent_id       BIGINT REFERENCES documents(id),
    status          TEXT    NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived','processing','error')),
    processed_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_org     ON documents(organisation_id);
CREATE INDEX IF NOT EXISTS idx_documents_hash    ON documents(file_hash);
CREATE INDEX IF NOT EXISTS idx_documents_parent  ON documents(parent_id);

CREATE TABLE IF NOT EXISTS document_blobs (
    document_id BIGINT PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    content     BYTEA NOT NULL,
    mime_type   TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_pages (
    id          BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    content     TEXT,
    page_type   TEXT    DEFAULT 'text' CHECK(page_type IN ('text','table','image','mixed')),
    word_count  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS extracted_entities (
    id          BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    entity_type TEXT    NOT NULL,
    entity_text TEXT    NOT NULL,
    context     TEXT,
    confidence  REAL    DEFAULT 0.0,
    page_number INTEGER,
    char_start  INTEGER,
    char_end    INTEGER
);

CREATE INDEX IF NOT EXISTS idx_entities_doc  ON extracted_entities(document_id);
CREATE INDEX IF NOT EXISTS idx_entities_type ON extracted_entities(entity_type);

CREATE TABLE IF NOT EXISTS report_templates (
    id              BIGSERIAL PRIMARY KEY,
    organisation_id BIGINT NOT NULL REFERENCES organisations(id),
    name            TEXT    NOT NULL,
    description     TEXT,
    template_json   TEXT    NOT NULL,
    created_by      BIGINT REFERENCES users(id),
    version         INTEGER NOT NULL DEFAULT 1,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS template_fields (
    id              BIGSERIAL PRIMARY KEY,
    template_id     BIGINT NOT NULL REFERENCES report_templates(id) ON DELETE CASCADE,
    field_key       TEXT    NOT NULL,
    field_label     TEXT    NOT NULL,
    field_type      TEXT    NOT NULL DEFAULT 'text'
                    CHECK(field_type IN ('text','number','date','boolean','list','location','table')),
    description     TEXT,
    is_required     INTEGER NOT NULL DEFAULT 0,
    default_value   TEXT,
    validation_rule TEXT,
    extraction_hint TEXT,
    display_order   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reports (
    id              BIGSERIAL PRIMARY KEY,
    organisation_id BIGINT NOT NULL REFERENCES organisations(id),
    template_id     BIGINT NOT NULL REFERENCES report_templates(id),
    name            TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','complete','archived')),
    generated_by    BIGINT REFERENCES users(id),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS report_values (
    id          BIGSERIAL PRIMARY KEY,
    report_id   BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    field_id    BIGINT NOT NULL REFERENCES template_fields(id),
    document_id BIGINT REFERENCES documents(id),
    raw_value   TEXT,
    typed_value TEXT,
    confidence  REAL    DEFAULT 0.0,
    is_verified INTEGER NOT NULL DEFAULT 0,
    verified_by BIGINT REFERENCES users(id),
    verified_at TIMESTAMP,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS report_sources (
    report_id   BIGINT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    document_id BIGINT NOT NULL REFERENCES documents(id),
    PRIMARY KEY (report_id, document_id)
);

CREATE TABLE IF NOT EXISTS document_changes (
    id              BIGSERIAL PRIMARY KEY,
    document_id     BIGINT NOT NULL REFERENCES documents(id),
    previous_doc_id BIGINT REFERENCES documents(id),
    change_type     TEXT    NOT NULL CHECK(change_type IN ('created','updated','deleted','restored')),
    changed_fields  TEXT,
    diff_summary    TEXT,
    impact_level    TEXT    DEFAULT 'low' CHECK(impact_level IN ('low','medium','high','critical')),
    detected_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detected_by     BIGINT REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS locations (
    id            BIGSERIAL PRIMARY KEY,
    document_id   BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    place_name    TEXT    NOT NULL,
    latitude      REAL,
    longitude     REAL,
    location_type TEXT    DEFAULT 'general',
    context       TEXT,
    geocoded      INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT REFERENCES users(id),
    action      TEXT    NOT NULL,
    entity_type TEXT,
    entity_id   BIGINT,
    detail      TEXT,
    ip_address  TEXT,
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reference_templates (
    id                    BIGSERIAL PRIMARY KEY,
    body                  TEXT    NOT NULL,
    category              TEXT    NOT NULL,
    name                  TEXT    NOT NULL,
    description           TEXT,
    source_url            TEXT,
    source_hash           TEXT,
    source_last_checked   TIMESTAMP,
    effective_date        TIMESTAMP,
    supersedes_template_id BIGINT REFERENCES reference_templates(id),
    change_summary        TEXT,
    file_path             TEXT,
    key_sections          TEXT,
    key_requirements      TEXT,
    keywords              TEXT,
    version               TEXT    NOT NULL DEFAULT '1.0',
    is_active             INTEGER NOT NULL DEFAULT 1,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ref_tmpl_body     ON reference_templates(body);
CREATE INDEX IF NOT EXISTS idx_ref_tmpl_category ON reference_templates(category);

CREATE TABLE IF NOT EXISTS semantic_analyses (
    id                    BIGSERIAL PRIMARY KEY,
    document_id           BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    reference_template_id BIGINT REFERENCES reference_templates(id),
    model_used            TEXT,
    body_detected         TEXT,
    category_detected     TEXT,
    compliance_score      REAL,
    present_elements      TEXT,
    missing_elements      TEXT,
    partial_elements      TEXT,
    strengths             TEXT,
    gaps                  TEXT,
    recommendations       TEXT,
    summary               TEXT,
    full_response_json    TEXT,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sem_analysis_doc ON semantic_analyses(document_id);
