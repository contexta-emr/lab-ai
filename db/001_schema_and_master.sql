-- =============================================================================
-- Contexta - Lab extraction store
-- 001  Schema, analyte master, aliases, reference ranges
-- =============================================================================
-- Target:  PostgreSQL 16 (Neon today, Azure Flexible Server later - nothing in
--          this file is Neon-specific).
-- Run as:  a role that may CREATE SCHEMA and CREATE EXTENSION.
-- Order:   001 -> 002 -> 003 -> 004 -> 005 -> 006 (006 is optional, see its head).
--
-- WHY A SEPARATE SCHEMA
--   core/config/registry are the EMR's. Extraction is a different lifecycle: a
--   document arrives, is parsed, is reviewed, and only then is it clinical fact.
--   Keeping that in lab.* means no existing table changes and no impact on the
--   still-open question of whether consultation labs live in a JSONB column or a
--   child table. When that is decided, lab.results is the source that feeds it.
--
-- CONVENTIONS (matched to apps/api/prisma/schema.prisma)
--   BIGINT identity PKs, practice_id on every tenant-scoped table, audit columns
--   created_at/created_by/updated_at/updated_by, soft delete is_deleted/
--   deleted_at/deleted_by, TIMESTAMP(6), explicit VARCHAR lengths, no native
--   enums (VARCHAR + CHECK, as the EMR does).
--
-- TENANCY
--   The vocabulary tables (panels, analytes, aliases, ranges) are GLOBAL: a
--   haemoglobin is a haemoglobin in every practice. Aliases and reference ranges
--   additionally allow a practice_id, where NULL means "applies everywhere" and
--   a value means "this practice's local override". Everything holding patient
--   data is practice-scoped and NOT NULL.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS lab;

-- Trigram matching is how a printed label that is in no alias list still finds
-- its analyte. Without it fn_resolve_analyte falls back to exact matching only.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

COMMENT ON SCHEMA lab IS
  'Lab document extraction: analyte master, parsed documents, results awaiting '
  'or past human review. Clinical truth only after status = verified.';


-- -----------------------------------------------------------------------------
-- Label normalisation
-- -----------------------------------------------------------------------------
-- "S. CREATININE", "Sr.Creat" and "Creatinine, Serum" are the same test. This
-- strips everything that is not a letter or digit and lowercases the rest, so
-- punctuation and spacing stop mattering. It does NOT make those three equal -
-- they are genuinely different strings - which is why each spelling is seeded as
-- its own alias and why fn_resolve_analyte has a trigram fallback behind this.
-- IMMUTABLE so it can back a generated column and an index.
CREATE OR REPLACE FUNCTION lab.fn_normalise_label(p_label TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT regexp_replace(lower(coalesce(p_label, '')), '[^a-z0-9]+', '', 'g');
$$;

COMMENT ON FUNCTION lab.fn_normalise_label(TEXT) IS
  'Lowercase and strip non-alphanumerics. Used for alias lookup and dedupe.';


-- -----------------------------------------------------------------------------
-- lab.panels - the ten canonical panel groups, plus the extras
-- -----------------------------------------------------------------------------
CREATE TABLE lab.panels (
    id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code            VARCHAR(40)  NOT NULL,
    display_name    VARCHAR(120) NOT NULL,
    description     TEXT,
    is_core         BOOLEAN      NOT NULL DEFAULT TRUE,
    sort_order      INTEGER      NOT NULL DEFAULT 0,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    is_deleted      BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMP(6),
    deleted_by      BIGINT,
    created_at      TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by      BIGINT,
    updated_at      TIMESTAMP(6),
    updated_by      BIGINT,
    CONSTRAINT panels_code_key UNIQUE (code)
);

COMMENT ON TABLE  lab.panels IS
  'Canonical panel vocabulary. is_core marks the ten high-frequency groups.';
COMMENT ON COLUMN lab.panels.code IS
  'Contexta internal canonical code (CBC, LIPID, ...), not a LOINC code.';


-- -----------------------------------------------------------------------------
-- lab.panel_aliases - the printed titles a panel arrives under
-- -----------------------------------------------------------------------------
-- "Complete Hemogram", "Haemogram", "CBC" are all the CBC panel. Matching these
-- is how a section heading becomes a panel.
CREATE TABLE lab.panel_aliases (
    id                BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    panel_id          BIGINT       NOT NULL REFERENCES lab.panels(id),
    practice_id       BIGINT,                     -- NULL = applies to every practice
    alias             VARCHAR(200) NOT NULL,
    alias_normalised  VARCHAR(200) GENERATED ALWAYS AS
                      (regexp_replace(lower(alias), '[^a-z0-9]+', '', 'g')) STORED,
    source            VARCHAR(20)  NOT NULL DEFAULT 'seed',
    is_active         BOOLEAN      NOT NULL DEFAULT TRUE,
    is_deleted        BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at        TIMESTAMP(6),
    deleted_by        BIGINT,
    created_at        TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by        BIGINT,
    updated_at        TIMESTAMP(6),
    updated_by        BIGINT,
    CONSTRAINT panel_aliases_source_check
        CHECK (source IN ('seed', 'learned', 'manual'))
);

-- One normalised spelling maps to one panel, globally or within a practice.
CREATE UNIQUE INDEX panel_aliases_norm_uq
    ON lab.panel_aliases (alias_normalised, COALESCE(practice_id, 0))
    WHERE is_deleted = FALSE;
CREATE INDEX panel_aliases_panel_idx
    ON lab.panel_aliases (panel_id) WHERE is_deleted = FALSE;
CREATE INDEX panel_aliases_trgm_idx
    ON lab.panel_aliases USING gin (alias_normalised gin_trgm_ops);


-- -----------------------------------------------------------------------------
-- lab.analytes - the canonical tests
-- -----------------------------------------------------------------------------
CREATE TABLE lab.analytes (
    id               BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code             VARCHAR(40)  NOT NULL,
    panel_id         BIGINT       REFERENCES lab.panels(id),
    display_name     VARCHAR(160) NOT NULL,
    value_type       VARCHAR(10)  NOT NULL DEFAULT 'numeric',
    default_unit     VARCHAR(40),
    decimals         SMALLINT     NOT NULL DEFAULT 1,
    is_derived       BOOLEAN      NOT NULL DEFAULT FALSE,
    derivation_note  VARCHAR(255),
    loinc_code       VARCHAR(20),
    sort_order       INTEGER      NOT NULL DEFAULT 0,
    is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
    is_deleted       BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at       TIMESTAMP(6),
    deleted_by       BIGINT,
    created_at       TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by       BIGINT,
    updated_at       TIMESTAMP(6),
    updated_by       BIGINT,
    CONSTRAINT analytes_code_key UNIQUE (code),
    CONSTRAINT analytes_value_type_check
        CHECK (value_type IN ('numeric', 'text')),
    CONSTRAINT analytes_decimals_check
        CHECK (decimals BETWEEN 0 AND 4)
);

COMMENT ON COLUMN lab.analytes.is_derived IS
  'VLDL, LDL, NON_HDL, the lipid ratios, BUN, GLOB, AG_RATIO, BILI_I, EAG, '
  'TSAT and EGFR are usually calculated, not measured. Flagged so a recomputation '
  'check can be run against the printed value.';
COMMENT ON COLUMN lab.analytes.loinc_code IS
  'Reserved for a later mapping to LOINC. Empty by design today.';

CREATE INDEX analytes_panel_idx ON lab.analytes (panel_id) WHERE is_deleted = FALSE;


-- -----------------------------------------------------------------------------
-- lab.analyte_aliases - every spelling a lab prints
-- -----------------------------------------------------------------------------
-- This is the table the whole pipeline turns on. Query the raw printed label and
-- a trend line silently plots three points where there should be seven.
CREATE TABLE lab.analyte_aliases (
    id                BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    analyte_id        BIGINT       NOT NULL REFERENCES lab.analytes(id),
    practice_id       BIGINT,                     -- NULL = applies to every practice
    alias             VARCHAR(200) NOT NULL,
    alias_normalised  VARCHAR(200) GENERATED ALWAYS AS
                      (regexp_replace(lower(alias), '[^a-z0-9]+', '', 'g')) STORED,
    source            VARCHAR(20)  NOT NULL DEFAULT 'seed',
    confidence        NUMERIC(5,4) NOT NULL DEFAULT 1.0000,
    is_active         BOOLEAN      NOT NULL DEFAULT TRUE,
    is_deleted        BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at        TIMESTAMP(6),
    deleted_by        BIGINT,
    created_at        TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by        BIGINT,
    updated_at        TIMESTAMP(6),
    updated_by        BIGINT,
    CONSTRAINT analyte_aliases_source_check
        CHECK (source IN ('seed', 'learned', 'manual')),
    CONSTRAINT analyte_aliases_confidence_check
        CHECK (confidence > 0 AND confidence <= 1)
);

CREATE UNIQUE INDEX analyte_aliases_norm_uq
    ON lab.analyte_aliases (alias_normalised, COALESCE(practice_id, 0))
    WHERE is_deleted = FALSE;
CREATE INDEX analyte_aliases_analyte_idx
    ON lab.analyte_aliases (analyte_id) WHERE is_deleted = FALSE;
-- Backs the fuzzy fallback in fn_resolve_analyte.
CREATE INDEX analyte_aliases_trgm_idx
    ON lab.analyte_aliases USING gin (alias_normalised gin_trgm_ops);


-- -----------------------------------------------------------------------------
-- lab.reference_ranges - what "normal" means, by sex and age
-- -----------------------------------------------------------------------------
-- A haemoglobin of 12.4 is normal for a woman, low for a man and normal for a
-- six-year-old. One row per applicable band; the most specific match wins.
CREATE TABLE lab.reference_ranges (
    id              BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    analyte_id      BIGINT       NOT NULL REFERENCES lab.analytes(id),
    practice_id     BIGINT,                       -- NULL = Contexta default
    sex             CHAR(1),                      -- NULL = any
    age_min_years   NUMERIC(5,2),                 -- NULL = no lower bound
    age_max_years   NUMERIC(5,2),                 -- NULL = no upper bound
    range_low       NUMERIC(14,4),
    range_high      NUMERIC(14,4),
    range_text      VARCHAR(120)  NOT NULL,       -- as a report would print it
    unit            VARCHAR(40),
    source          VARCHAR(80)   NOT NULL DEFAULT 'contexta_default',
    is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
    is_deleted      BOOLEAN       NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMP(6),
    deleted_by      BIGINT,
    created_at      TIMESTAMP(6)  NOT NULL DEFAULT now(),
    created_by      BIGINT,
    updated_at      TIMESTAMP(6),
    updated_by      BIGINT,
    CONSTRAINT reference_ranges_sex_check
        CHECK (sex IS NULL OR sex IN ('M', 'F')),
    CONSTRAINT reference_ranges_age_check
        CHECK (age_min_years IS NULL OR age_max_years IS NULL
               OR age_min_years < age_max_years),
    CONSTRAINT reference_ranges_bounds_check
        CHECK (range_low IS NULL OR range_high IS NULL OR range_low <= range_high)
);

CREATE INDEX reference_ranges_lookup_idx
    ON lab.reference_ranges (analyte_id, sex, age_min_years, age_max_years)
    WHERE is_deleted = FALSE AND is_active = TRUE;

COMMENT ON COLUMN lab.reference_ranges.range_text IS
  'The printable form: "13.0 - 17.0", "< 200", "Absent", "Non Reactive". Kept '
  'alongside the numeric bounds because not every range is numeric.';


-- -----------------------------------------------------------------------------
-- lab.unmatched_labels - the vocabulary learning its own gaps
-- -----------------------------------------------------------------------------
-- Every printed label that resolved to nothing lands here with a count. It is
-- the work queue for growing analyte_aliases, and the honest measure of how much
-- of the real world the master still misses.
CREATE TABLE lab.unmatched_labels (
    id                   BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    practice_id          BIGINT,
    printed_label        VARCHAR(255) NOT NULL,
    label_normalised     VARCHAR(255) GENERATED ALWAYS AS
                         (regexp_replace(lower(printed_label), '[^a-z0-9]+', '', 'g')) STORED,
    occurrence_count     INTEGER      NOT NULL DEFAULT 1,
    sample_unit          VARCHAR(40),
    sample_value         VARCHAR(255),
    first_seen_at        TIMESTAMP(6) NOT NULL DEFAULT now(),
    last_seen_at         TIMESTAMP(6) NOT NULL DEFAULT now(),
    resolved_analyte_id  BIGINT       REFERENCES lab.analytes(id),
    resolved_by          BIGINT,
    resolved_at          TIMESTAMP(6)
);

CREATE UNIQUE INDEX unmatched_labels_uq
    ON lab.unmatched_labels (label_normalised, COALESCE(practice_id, 0));
CREATE INDEX unmatched_labels_open_idx
    ON lab.unmatched_labels (occurrence_count DESC)
    WHERE resolved_analyte_id IS NULL;
