-- =============================================================================
-- Contexta - Lab extraction store
-- 020  Panel membership becomes many-to-many, and a result stops being a number
-- =============================================================================
-- Source: Contexta_Lab_30_Panels_Full_Tabular_Benchmark.md v1.1, September 2026.
-- Where that document disagrees with what was here, it wins - that was the call.
--
-- TWO THINGS CHANGE, AND NEITHER BREAKS WHAT EXISTS.
--
-- 1. MEMBERSHIP
--    lab.analytes.panel_id says an analyte belongs to one panel. The benchmark
--    is explicit that it does not: section 11 rule 2, and section 3 lists the
--    cases - Sodium in Electrolytes AND Renal, PT in Coagulation AND PT/INR,
--    Ferritin in Iron Profile AND as a test of its own. With one FK, every one
--    of those had to pick a side, and the panel that lost simply never reported
--    the analyte missing.
--
--    lab.panel_analytes carries the relationship instead. panel_id stays on
--    lab.analytes as the PRIMARY panel so that nothing reading it today breaks;
--    coverage moves to the join table, where an analyte can be core to one panel
--    and optional in another.
--
-- 2. ROLE
--    is_core was computed as NOT is_derived - reproducible, and wrong about LDL,
--    which is calculated and printed on every lipid report. The benchmark states
--    Core / Common / Optional / Derived per analyte PER PANEL, so the role lives
--    on the membership row, not on the analyte.
--
-- 3. RESULT TYPE
--    value_type allowed 'numeric' or 'text'. A blood group is coded, a urine
--    protein is ordinal, an HIV screen is reactive/non-reactive, a culture
--    yields an organism and a susceptibility. Section 1 of the benchmark lists
--    them; the CHECK is widened to match. Nothing stored changes: every existing
--    row is 'numeric' and stays 'numeric'.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------- 1. the join
CREATE TABLE IF NOT EXISTS lab.panel_analytes (
    id           BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    panel_id     BIGINT       NOT NULL REFERENCES lab.panels(id),
    analyte_id   BIGINT       NOT NULL REFERENCES lab.analytes(id),

    -- The benchmark's own word, kept verbatim rather than reduced to a boolean,
    -- because "common" and "core" are different clinical claims and a later
    -- reader should not have to reverse-engineer which one produced the flag.
    role         VARCHAR(12)  NOT NULL DEFAULT 'core',
    -- Denormalised from role so coverage can filter without a CASE on every
    -- query. core and common are worth flagging when absent; optional and
    -- derived are not.
    is_core      BOOLEAN      NOT NULL DEFAULT TRUE,

    sort_order   INTEGER      NOT NULL DEFAULT 0,
    source       VARCHAR(20)  NOT NULL DEFAULT 'benchmark_v1',

    is_deleted   BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at   TIMESTAMP(6),
    deleted_by   BIGINT,
    created_at   TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by   BIGINT,
    updated_at   TIMESTAMP(6),
    updated_by   BIGINT,

    CONSTRAINT panel_analytes_role_check
        CHECK (role IN ('core', 'common', 'optional', 'derived')),
    CONSTRAINT panel_analytes_source_check
        CHECK (source IN ('benchmark_v1', 'catalog', 'manual'))
);

-- One row per pair. A panel listing the same analyte twice is a data error, not
-- a thing to be tolerated and deduplicated downstream.
CREATE UNIQUE INDEX IF NOT EXISTS panel_analytes_pair_uq
    ON lab.panel_analytes (panel_id, analyte_id)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS panel_analytes_panel_idx
    ON lab.panel_analytes (panel_id) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS panel_analytes_analyte_idx
    ON lab.panel_analytes (analyte_id) WHERE is_deleted = FALSE;

COMMENT ON TABLE lab.panel_analytes IS
  'Which analytes make up which panel. Many-to-many: benchmark section 11 rule 2. '
  'An analyte can be core to one panel and optional in another, which a single '
  'panel_id on lab.analytes could not express.';
COMMENT ON COLUMN lab.panel_analytes.role IS
  'Core, Common, Optional or Derived, taken from the benchmark. Replaces the old '
  'mechanical is_core = NOT is_derived, which called LDL optional because it is '
  'calculated - though every lipid report prints it.';


-- ------------------------------------------- 2. seed it from what already is
-- Every existing analyte keeps its current panel, at its current coreness, so
-- coverage reads the same the moment this lands. The benchmark seed that follows
-- adds to this rather than replacing it.
INSERT INTO lab.panel_analytes (panel_id, analyte_id, role, is_core, sort_order, source)
SELECT a.panel_id,
       a.id,
       CASE WHEN a.is_derived THEN 'derived' ELSE 'core' END,
       NOT a.is_derived,
       a.sort_order,
       'catalog'
FROM   lab.analytes a
WHERE  a.panel_id IS NOT NULL
  AND  a.is_deleted = FALSE
ON CONFLICT DO NOTHING;


-- ------------------------------------------------------- 3. result types
-- A result is not always a number. Section 1 of the benchmark:
--   numeric       Hb 13.8                 ordinal       Trace / 1+ / 2+
--   text          free text               coded         Blood group O; Rh Positive
--   qualitative   Positive / Negative     reactive      Reactive / Non-reactive
--   detected      Detected / Not detected organism      E. coli
--   susceptibility S / I / R              structured    casts, crystals
--   narrative     smear or culture comment
ALTER TABLE lab.analytes DROP CONSTRAINT IF EXISTS analytes_value_type_check;
ALTER TABLE lab.analytes ADD CONSTRAINT analytes_value_type_check
    CHECK (value_type IN ('numeric', 'text', 'qualitative', 'ordinal', 'coded',
                          'reactive', 'detected', 'organism', 'susceptibility',
                          'structured', 'narrative'));

COMMENT ON COLUMN lab.analytes.value_type IS
  'How the result reads, per benchmark section 1. Not a storage type - every '
  'value is still kept as the printed text. It tells a reader whether comparing '
  'two results numerically is meaningful, which for Reactive or S/I/R it is not.';

-- Specimen, which the benchmark asks to be retained per observation (section 1)
-- and which decides whether two similarly named tests are the same observation
-- at all: serum uric acid and urine uric acid are not interchangeable.
ALTER TABLE lab.analytes ADD COLUMN IF NOT EXISTS specimen VARCHAR(60);
COMMENT ON COLUMN lab.analytes.specimen IS
  'Serum/plasma, Whole blood, Urine, Citrated plasma, Culture isolate. Benchmark '
  'rule 16: do not merge specimen types into one observation without an explicit '
  'mapping rule.';

COMMIT;
