-- =============================================================================
-- Contexta - Lab extraction store
-- 000  core compatibility schema
-- =============================================================================
-- Run FIRST, before 001.
--
-- WHY THIS FILE EXISTS
--   This service owns its own database. The EMR's core schema is not here, but
--   lab.* needs somewhere to hang a patient, a practice, a user and an uploaded
--   file. So we create the four tables we touch, with the EXACT table names,
--   column names and types they have in apps/api/prisma/schema.prisma.
--
--   That is the whole point: the day this service is pointed at the real EMR
--   database instead, you drop this file from the run order and nothing else
--   changes - not a query, not a function, not a line of API code. The names
--   already match.
--
--   These are therefore deliberately partial. core.patients in the EMR has
--   forty columns; we create the ones the lab pipeline reads. Adding the rest
--   later is additive and breaks nothing.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS core;

COMMENT ON SCHEMA core IS
  'Compatibility subset of the EMR core schema. Same names and types as '
  'apps/api/prisma/schema.prisma so this service ports to the real database '
  'without code changes. Drop 000 from the run order when pointing at the EMR.';

-- Needed here, not only in 001: patients_uhid_trgm_idx below is a gin_trgm_ops
-- index, so the extension has to exist before this file finishes. 001 declares
-- it again with IF NOT EXISTS, which is harmless and keeps 001 standalone for a
-- vocabulary-only install that never creates the core schema at all.
CREATE EXTENSION IF NOT EXISTS pg_trgm;


-- -----------------------------------------------------------------------------
-- core.practices - the tenant
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.practices (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          VARCHAR(255) NOT NULL,
    city          VARCHAR(100),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    is_deleted    BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at    TIMESTAMP(6),
    deleted_by    BIGINT,
    created_at    TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by    BIGINT,
    updated_at    TIMESTAMP(6),
    updated_by    BIGINT
);


-- -----------------------------------------------------------------------------
-- core.users - who uploaded, who reviewed
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.users (
    id             BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    practice_id    BIGINT       NOT NULL REFERENCES core.practices(id),
    email          VARCHAR(255) NOT NULL,
    full_name      VARCHAR(255),
    role           VARCHAR(50)  NOT NULL DEFAULT 'reviewer',
    password_hash  VARCHAR(255),
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    is_deleted     BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at     TIMESTAMP(6),
    deleted_by     BIGINT,
    created_at     TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by     BIGINT,
    updated_at     TIMESTAMP(6),
    updated_by     BIGINT,
    CONSTRAINT users_email_key UNIQUE (email),
    CONSTRAINT users_role_check CHECK (role IN ('admin', 'reviewer', 'clinician', 'service'))
);

COMMENT ON COLUMN core.users.password_hash IS
  'Local POC auth only. When this service moves behind the EMR JWT, this column '
  'stops being read and the EMR remains the only place credentials live.';


-- -----------------------------------------------------------------------------
-- core.patients - the match target for UHID auto-detection
-- -----------------------------------------------------------------------------
-- uhid is VARCHAR(20) here because it is VARCHAR(20) in the EMR. Do not widen it
-- without widening it there; a UHID that fits one and not the other is a bug
-- that only shows up on the day of the migration.
CREATE TABLE IF NOT EXISTS core.patients (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    practice_id   BIGINT       NOT NULL REFERENCES core.practices(id),
    uhid          VARCHAR(20)  NOT NULL,
    first_name    TEXT         NOT NULL,
    last_name     TEXT         NOT NULL,
    dob           DATE,
    gender        VARCHAR(10),
    blood_group   VARCHAR(10),
    mobile        VARCHAR(15),
    email         VARCHAR(255),
    city          VARCHAR(100),
    is_deleted    BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at    TIMESTAMP(6),
    deleted_by    BIGINT,
    created_at    TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by    BIGINT,
    updated_at    TIMESTAMP(6),
    updated_by    BIGINT
);

-- A UHID is unique within a practice, not globally. Two clinics may both have
-- a patient numbered 104772.
CREATE UNIQUE INDEX IF NOT EXISTS patients_practice_uhid_uq
    ON core.patients (practice_id, uhid)
    WHERE is_deleted = FALSE;
-- Backs the fuzzy arm of fn_match_patient_by_uhid.
CREATE INDEX IF NOT EXISTS patients_uhid_trgm_idx
    ON core.patients USING gin (uhid gin_trgm_ops);


-- -----------------------------------------------------------------------------
-- core.visit_attachments - the uploaded file
-- -----------------------------------------------------------------------------
-- Column names copied from the EMR model, including the azure_* ones, because
-- that is where files land in production. For local development the blob path
-- is a filesystem path and storage_provider says so.
CREATE TABLE IF NOT EXISTS core.visit_attachments (
    id                   BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    practice_id          BIGINT       NOT NULL REFERENCES core.practices(id),
    patient_id           BIGINT       REFERENCES core.patients(id),
    visit_id             BIGINT,
    uploaded_by          BIGINT       REFERENCES core.users(id),
    original_file_name   VARCHAR(500) NOT NULL,
    stored_file_name     VARCHAR(500) NOT NULL,
    file_extension       VARCHAR(10)  NOT NULL,
    mime_type            VARCHAR(100),
    file_size_bytes      BIGINT       NOT NULL,
    storage_provider     VARCHAR(20)  NOT NULL DEFAULT 'local',
    azure_container_name VARCHAR(200),
    azure_blob_path      VARCHAR(1000),
    azure_blob_url       VARCHAR(2000),
    upload_status        VARCHAR(30)  NOT NULL DEFAULT 'completed',
    source               VARCHAR(50)  NOT NULL DEFAULT 'emr_user',
    uploaded_at          TIMESTAMP(6) NOT NULL DEFAULT now(),
    is_verified          BOOLEAN      NOT NULL DEFAULT FALSE,
    verified_by          BIGINT,
    verified_at          TIMESTAMP(6),
    is_deleted           BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at           TIMESTAMP(6),
    deleted_by           BIGINT,
    created_at           TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by           BIGINT,
    updated_at           TIMESTAMP(6),
    updated_by           BIGINT,
    CONSTRAINT visit_attachments_storage_check
        CHECK (storage_provider IN ('local', 'azure_blob', 's3'))
);

CREATE INDEX IF NOT EXISTS visit_attachments_patient_idx
    ON core.visit_attachments (practice_id, patient_id)
    WHERE is_deleted = FALSE;
