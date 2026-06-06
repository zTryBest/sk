-- Complete PostgreSQL initialization script for the AI agent knowledge base.
-- This file can be used by the official postgres Docker image or by psql.
--
-- Default values are compatible with docker-compose.yml:
--   database: enterprise_knowledge_base
--   user:     knowledge_user
--   password: knowledge_password
--
-- Optional psql overrides:
--   psql -v app_database=my_db -v app_user=my_user -v app_password=my_pwd -f database/init.sql

\set ON_ERROR_STOP on

\if :{?app_database}
\else
\set app_database enterprise_knowledge_base
\endif

\if :{?app_user}
\else
\set app_user knowledge_user
\endif

\if :{?app_password}
\else
\set app_password knowledge_password
\endif

SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L',
    :'app_user',
    :'app_password'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'app_user'
)\gexec

ALTER ROLE :"app_user" WITH LOGIN PASSWORD :'app_password';

SELECT format(
    'CREATE DATABASE %I WITH OWNER %I ENCODING %L TEMPLATE template0',
    :'app_database',
    :'app_user',
    'UTF8'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = :'app_database'
)\gexec

ALTER DATABASE :"app_database" OWNER TO :"app_user";

\connect :"app_database"

SET client_encoding = 'UTF8';
SET TIME ZONE 'Asia/Shanghai';

CREATE SCHEMA IF NOT EXISTS public;
GRANT USAGE, CREATE ON SCHEMA public TO :"app_user";

-- ---------------------------------------------------------------------------
-- Legacy component and API knowledge tables.
-- Kept for compatibility with older repositories and services in this project.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS component_info (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT NOT NULL,
    product_version TEXT NOT NULL,
    comp_id TEXT NOT NULL,
    comp_name TEXT NOT NULL,
    comp_version TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    scene TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (product_id, product_version, comp_id, comp_version)
);

CREATE INDEX IF NOT EXISTS idx_component_info_product
    ON component_info (product_id, product_version);

CREATE TABLE IF NOT EXISTS api_info (
    id BIGSERIAL PRIMARY KEY,
    comp_id TEXT NOT NULL,
    comp_version TEXT NOT NULL,
    api_path TEXT NOT NULL,
    api_name TEXT NOT NULL,
    params_desc TEXT NOT NULL DEFAULT '',
    response_demo TEXT NOT NULL DEFAULT '',
    scene TEXT NOT NULL DEFAULT '',
    request_method TEXT NOT NULL DEFAULT '',
    capability_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    request_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_headers JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_example JSONB NOT NULL DEFAULT '{}'::jsonb,
    usage_notes TEXT NOT NULL DEFAULT '',
    source_doc TEXT NOT NULL DEFAULT '',
    version_status TEXT NOT NULL DEFAULT 'ACTIVE',
    validation_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    latest_response_status INTEGER,
    latest_response_body TEXT NOT NULL DEFAULT '',
    last_verified_at TIMESTAMPTZ,
    content TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (comp_id, comp_version, api_path)
);

ALTER TABLE api_info
    ADD COLUMN IF NOT EXISTS request_method TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS capability_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    ADD COLUMN IF NOT EXISTS request_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS response_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS request_headers JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS request_example JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS usage_notes TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS source_doc TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS version_status TEXT NOT NULL DEFAULT 'ACTIVE',
    ADD COLUMN IF NOT EXISTS validation_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    ADD COLUMN IF NOT EXISTS latest_response_status INTEGER,
    ADD COLUMN IF NOT EXISTS latest_response_body TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_api_info_component
    ON api_info (comp_id, comp_version);

CREATE INDEX IF NOT EXISTS idx_api_info_validation
    ON api_info (version_status, last_verified_at);

CREATE TABLE IF NOT EXISTS best_practice (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT NOT NULL,
    product_version TEXT NOT NULL,
    practice_name TEXT NOT NULL,
    scenario TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    recommended_component TEXT NOT NULL DEFAULT '',
    recommended_api TEXT NOT NULL DEFAULT '',
    sample_code TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_best_practice_product
    ON best_practice (product_id, product_version);

CREATE TABLE IF NOT EXISTS knowledge_candidate (
    id BIGSERIAL PRIMARY KEY,
    candidate_type TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product_version TEXT NOT NULL,
    component_id TEXT NOT NULL DEFAULT '',
    component_version TEXT NOT NULL DEFAULT '',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    created_by TEXT NOT NULL DEFAULT 'AI_AGENT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_candidate_status
    ON knowledge_candidate (status, id DESC);

CREATE TABLE IF NOT EXISTS requirement_api_feedback (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT NOT NULL,
    product_version TEXT NOT NULL,
    requirement_text TEXT NOT NULL,
    component_id TEXT NOT NULL,
    segment_id TEXT NOT NULL DEFAULT '',
    component_version TEXT NOT NULL,
    api_path TEXT NOT NULL,
    api_name TEXT NOT NULL DEFAULT '',
    feedback_type TEXT NOT NULL DEFAULT 'HUMAN_CONFIRM'
        CHECK (feedback_type IN ('MCP_EMPTY', 'MCP_WRONG', 'HUMAN_CONFIRM')),
    feedback_reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    created_by TEXT NOT NULL DEFAULT 'AI_AGENT',
    content TEXT NOT NULL DEFAULT '',
    method TEXT NOT NULL DEFAULT '',
    api_identity_id BIGINT,
    api_contract_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE requirement_api_feedback
    ADD COLUMN IF NOT EXISTS segment_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS method TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS api_identity_id BIGINT,
    ADD COLUMN IF NOT EXISTS api_contract_id BIGINT;

CREATE INDEX IF NOT EXISTS idx_requirement_api_feedback_product
    ON requirement_api_feedback (product_id, product_version, status);

CREATE TABLE IF NOT EXISTS api_validation_record (
    id BIGSERIAL PRIMARY KEY,
    api_id BIGINT,
    product_id TEXT NOT NULL,
    product_version TEXT NOT NULL,
    component_id TEXT NOT NULL,
    segment_id TEXT NOT NULL DEFAULT '',
    component_version TEXT NOT NULL,
    test_env TEXT NOT NULL,
    request_url TEXT NOT NULL,
    request_method TEXT NOT NULL,
    request_headers JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_body JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_status INTEGER,
    response_body TEXT NOT NULL DEFAULT '',
    response_schema_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_success BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT NOT NULL DEFAULT '',
    api_identity_id BIGINT,
    api_contract_id BIGINT,
    resolved_component_version TEXT NOT NULL DEFAULT '',
    resolved_doc_version TEXT NOT NULL DEFAULT '',
    validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE api_validation_record
    ADD COLUMN IF NOT EXISTS segment_id TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS api_identity_id BIGINT,
    ADD COLUMN IF NOT EXISTS api_contract_id BIGINT,
    ADD COLUMN IF NOT EXISTS resolved_component_version TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS resolved_doc_version TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_api_validation_record_api
    ON api_validation_record (api_id, validated_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_validation_record_product
    ON api_validation_record (product_id, product_version, validated_at DESC);

-- ---------------------------------------------------------------------------
-- Design-phase API identity and contract model.
-- This is the primary model used by the current MCP design workflow.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS product_release (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT NOT NULL,
    product_version TEXT NOT NULL,
    product_name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (product_id, product_version)
);

CREATE TABLE IF NOT EXISTS component_catalog (
    id BIGSERIAL PRIMARY KEY,
    component_id TEXT NOT NULL UNIQUE,
    component_name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    scene TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS component_segment (
    id BIGSERIAL PRIMARY KEY,
    component_id TEXT NOT NULL,
    segment_id TEXT NOT NULL,
    segment_name TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    scene TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (component_id, segment_id)
);

CREATE INDEX IF NOT EXISTS idx_component_segment_component
    ON component_segment (component_id);

CREATE TABLE IF NOT EXISTS product_component_baseline (
    id BIGSERIAL PRIMARY KEY,
    product_id TEXT NOT NULL,
    product_version TEXT NOT NULL,
    component_id TEXT NOT NULL,
    component_version TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'BASELINE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (product_id, product_version, component_id)
);

CREATE INDEX IF NOT EXISTS idx_product_component_baseline_product
    ON product_component_baseline (product_id, product_version);

CREATE TABLE IF NOT EXISTS component_doc_version (
    id BIGSERIAL PRIMARY KEY,
    component_id TEXT NOT NULL,
    segment_id TEXT NOT NULL DEFAULT '',
    doc_version TEXT NOT NULL,
    doc_url TEXT NOT NULL DEFAULT '',
    crawl_status TEXT NOT NULL DEFAULT 'PENDING',
    last_crawled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE component_doc_version
    ADD COLUMN IF NOT EXISTS segment_id TEXT NOT NULL DEFAULT '';

ALTER TABLE component_doc_version
    DROP CONSTRAINT IF EXISTS component_doc_version_component_id_doc_version_key;

CREATE UNIQUE INDEX IF NOT EXISTS uq_component_doc_version_segment
    ON component_doc_version (component_id, segment_id, doc_version);

CREATE INDEX IF NOT EXISTS idx_component_doc_version_component_segment
    ON component_doc_version (component_id, segment_id);

CREATE TABLE IF NOT EXISTS component_version_doc_mapping (
    id BIGSERIAL PRIMARY KEY,
    component_id TEXT NOT NULL,
    segment_id TEXT NOT NULL DEFAULT '',
    component_version TEXT NOT NULL,
    doc_version TEXT NOT NULL,
    mapping_type TEXT NOT NULL DEFAULT 'MANUAL',
    confidence NUMERIC(5, 2) NOT NULL DEFAULT 1.0,
    reason TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT 'AI_AGENT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE component_version_doc_mapping
    ADD COLUMN IF NOT EXISTS segment_id TEXT NOT NULL DEFAULT '';

ALTER TABLE component_version_doc_mapping
    DROP CONSTRAINT IF EXISTS component_version_doc_mapping_component_id_component_version_key;

CREATE UNIQUE INDEX IF NOT EXISTS uq_component_version_doc_mapping_segment
    ON component_version_doc_mapping (component_id, segment_id, component_version);

CREATE TABLE IF NOT EXISTS api_identity (
    id BIGSERIAL PRIMARY KEY,
    component_id TEXT NOT NULL,
    segment_id TEXT NOT NULL DEFAULT '',
    method TEXT NOT NULL,
    api_path TEXT NOT NULL,
    api_name TEXT NOT NULL,
    capability_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    scene TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE api_identity
    ADD COLUMN IF NOT EXISTS segment_id TEXT NOT NULL DEFAULT '';

ALTER TABLE api_identity
    ADD COLUMN IF NOT EXISTS introduced_doc_version TEXT NOT NULL DEFAULT '';

ALTER TABLE api_identity
    ADD COLUMN IF NOT EXISTS last_seen_doc_version TEXT NOT NULL DEFAULT '';

ALTER TABLE api_identity
    ADD COLUMN IF NOT EXISTS removed_doc_version TEXT NULL;

ALTER TABLE api_identity
    DROP CONSTRAINT IF EXISTS api_identity_component_id_method_api_path_key;

CREATE UNIQUE INDEX IF NOT EXISTS uq_api_identity_segment
    ON api_identity (component_id, segment_id, method, api_path);

CREATE INDEX IF NOT EXISTS idx_api_identity_component_segment
    ON api_identity (component_id, segment_id);

CREATE INDEX IF NOT EXISTS idx_api_identity_version_range
    ON api_identity (component_id, segment_id, introduced_doc_version, removed_doc_version);

CREATE TABLE IF NOT EXISTS api_contract (
    id BIGSERIAL PRIMARY KEY,
    api_identity_id BIGINT NOT NULL REFERENCES api_identity(id) ON DELETE CASCADE,
    doc_version TEXT NOT NULL,
    params_desc TEXT NOT NULL DEFAULT '',
    request_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_headers JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_example JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_example JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_demo TEXT NOT NULL DEFAULT '',
    usage_notes TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (api_identity_id, doc_version)
);

CREATE INDEX IF NOT EXISTS idx_api_contract_identity
    ON api_contract (api_identity_id);

CREATE TABLE IF NOT EXISTS api_lifecycle (
    id BIGSERIAL PRIMARY KEY,
    api_identity_id BIGINT NOT NULL REFERENCES api_identity(id) ON DELETE CASCADE,
    doc_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PRESENT'
        CHECK (status IN ('PRESENT', 'DEPRECATED', 'REMOVED')),
    change_type TEXT NOT NULL DEFAULT 'UNCHANGED'
        CHECK (change_type IN ('ADDED', 'CHANGED', 'UNCHANGED', 'REMOVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (api_identity_id, doc_version)
);

CREATE INDEX IF NOT EXISTS idx_api_lifecycle_identity
    ON api_lifecycle (api_identity_id, doc_version);

-- ---------------------------------------------------------------------------
-- Identifier normalization.
-- Keep product_id, component_id, and segment_id case-insensitive in practice by
-- storing canonical uppercase values. Versions and API paths keep their source
-- casing.
-- ---------------------------------------------------------------------------

UPDATE component_info
SET
    product_id = UPPER(product_id),
    comp_id = UPPER(comp_id)
WHERE product_id <> UPPER(product_id)
   OR comp_id <> UPPER(comp_id);

UPDATE best_practice
SET product_id = UPPER(product_id)
WHERE product_id <> UPPER(product_id);

UPDATE knowledge_candidate
SET
    product_id = UPPER(product_id),
    component_id = UPPER(component_id)
WHERE product_id <> UPPER(product_id)
   OR component_id <> UPPER(component_id);

UPDATE requirement_api_feedback
SET
    product_id = UPPER(product_id),
    component_id = UPPER(component_id),
    segment_id = UPPER(segment_id)
WHERE product_id <> UPPER(product_id)
   OR component_id <> UPPER(component_id)
   OR segment_id <> UPPER(segment_id);

UPDATE api_validation_record
SET
    product_id = UPPER(product_id),
    component_id = UPPER(component_id),
    segment_id = UPPER(segment_id)
WHERE product_id <> UPPER(product_id)
   OR component_id <> UPPER(component_id)
   OR segment_id <> UPPER(segment_id);

UPDATE product_release
SET product_id = UPPER(product_id)
WHERE product_id <> UPPER(product_id);

UPDATE component_catalog
SET component_id = UPPER(component_id)
WHERE component_id <> UPPER(component_id);

UPDATE component_segment
SET
    component_id = UPPER(component_id),
    segment_id = UPPER(segment_id)
WHERE component_id <> UPPER(component_id)
   OR segment_id <> UPPER(segment_id);

UPDATE product_component_baseline
SET
    product_id = UPPER(product_id),
    component_id = UPPER(component_id)
WHERE product_id <> UPPER(product_id)
   OR component_id <> UPPER(component_id);

UPDATE component_doc_version
SET
    component_id = UPPER(component_id),
    segment_id = UPPER(segment_id)
WHERE component_id <> UPPER(component_id)
   OR segment_id <> UPPER(segment_id);

UPDATE component_version_doc_mapping
SET
    component_id = UPPER(component_id),
    segment_id = UPPER(segment_id)
WHERE component_id <> UPPER(component_id)
   OR segment_id <> UPPER(segment_id);

UPDATE api_identity
SET
    component_id = UPPER(component_id),
    segment_id = UPPER(segment_id)
WHERE component_id <> UPPER(component_id)
   OR segment_id <> UPPER(segment_id);

-- ---------------------------------------------------------------------------
-- Permissions.
-- ---------------------------------------------------------------------------

GRANT ALL PRIVILEGES ON DATABASE :"app_database" TO :"app_user";
GRANT USAGE, CREATE ON SCHEMA public TO :"app_user";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"app_user";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO :"app_user";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"app_user";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"app_user";
