-- =============================================================================
-- Contexta - Lab extraction store
-- 021  value_type needs room for the words the benchmark uses
-- =============================================================================
-- 020 widened the CHECK on lab.analytes.value_type to the eleven result types of
-- the 30-panel benchmark, and did not widen the COLUMN. VARCHAR(10) holds
-- 'numeric' and 'text' comfortably and truncates 'qualitative' (11) and
-- 'susceptibility' (14), so the seed that followed failed on the first
-- qualitative analyte with "value too long for type character varying(10)".
--
-- A CHECK constraint cannot save a value the column has no room for. Both have
-- to move together, and this is the half that was missed.
--
-- Its own migration rather than an edit to 020, which is already applied:
-- changing an applied file makes every checksum downstream a lie about what ran.
-- =============================================================================

BEGIN;

ALTER TABLE lab.analytes ALTER COLUMN value_type TYPE VARCHAR(20);

COMMENT ON COLUMN lab.analytes.value_type IS
  'How the result reads, per benchmark section 1: numeric, text, qualitative, '
  'ordinal, coded, reactive, detected, organism, susceptibility, structured, '
  'narrative. Not a storage type - the value is always kept as printed text. It '
  'says whether comparing two results numerically is meaningful, which for '
  'Reactive or S/I/R it is not.';

COMMIT;
