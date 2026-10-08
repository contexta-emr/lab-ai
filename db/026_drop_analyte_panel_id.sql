-- =============================================================================
-- Contexta - Lab extraction store
-- 026  lab.analytes.panel_id goes
-- =============================================================================
-- The column said an analyte belongs to one panel. It does not: Calcium is in
-- Renal, Electrolytes and Calcium, with a different role in each. Since 020 the
-- truth has been in lab.panel_analytes and this column has been a second,
-- narrower answer to the same question - the kind a new query reaches for
-- because it is simpler, and gets wrong.
--
-- 025 moved every reader. This drops the column and the legacy function kept
-- for the comparison.
--
-- THE EVIDENCE FOR DOING IT
--   scripts/diff_resolver.py --all-panels re-resolved every printed label in the
--   database against every panel - 34,003 combinations - through both the old
--   panel_id resolver and the membership one:
--
--       identical, resolved            18,130
--       identical, both unresolved     15,873
--       one resolved, the other not         0
--       both resolved, different code       0
--
--   Not one label resolves differently. That is why this is safe to drop rather
--   than merely plausible to drop.
--
-- WHAT THIS DOES NOT TOUCH
--   lab.report_sections.panel_id, which is a different thing entirely: the panel
--   THIS PRINTED SECTION was judged to be, from its own heading. A section has
--   exactly one heading, so one panel there is correct and stays.
-- =============================================================================

BEGIN;

DROP FUNCTION IF EXISTS lab.fn_resolve_analyte_legacy(BIGINT, TEXT, BIGINT, REAL);

DROP INDEX IF EXISTS lab.analytes_panel_idx;
ALTER TABLE lab.analytes DROP COLUMN IF EXISTS panel_id;

COMMENT ON TABLE lab.analytes IS
  'Canonical analyte vocabulary. Which panels an analyte belongs to is in '
  'lab.panel_analytes - many-to-many, with a per-panel role - not here.';

COMMIT;
