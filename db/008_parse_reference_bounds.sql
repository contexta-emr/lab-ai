-- =============================================================================
-- Contexta - Lab extraction store
-- 008  Parse the printed reference range into ref_low / ref_high
-- =============================================================================
-- Run after 007.
--
-- THE PROBLEM
--   lab.results has reference_printed, ref_low and ref_high. Only the first was
--   ever written: fn_ingest_lab_document stores the printed string and does not
--   parse it, so ref_low and ref_high are NULL on all 4,177 corpus results.
--
--   web/components/TrendChart.tsx lines 29-30 read exactly those two columns to
--   draw the reference band behind the line. The band therefore never rendered
--   and never could. A chart quietly missing the band that says what normal
--   looks like is worth less than half a chart.
--
-- WHY A TRIGGER AND NOT A CHANGE TO fn_ingest_lab_document
--   Two reasons. The rule then holds for every write path, not just the one
--   function - a backfill, a reviewer correction, a future OCR importer. And it
--   avoids reprinting 270 lines of ingest function into a migration to change
--   two columns, where the diff would be invisible and the transcription risk
--   real.
--
--   It only fills what is NULL. A human who corrects a mis-parsed bound is not
--   overwritten on the next update, which a generated column would not allow.
--
-- COVERAGE
--   Measured over the 4,176 corpus results that carry a printed reference:
--   3,884 (93.0%) match one of the three forms below. The 292 that do not are
--   text ranges - Absent, Pale Yellow, Non Reactive, Negative, No growth - and
--   correctly have no numeric bounds. reference_printed keeps the full text
--   either way; these columns are only ever an additional convenience.
-- =============================================================================


-- ----------------------------------------------------------------------------
-- The parser
-- ----------------------------------------------------------------------------
-- Three forms, which is all a lab prints:
--     13.0 - 17.0     a band          -> low 13.0, high 17.0
--     < 200           an upper bound  -> low NULL, high 200
--     > 40            a lower bound   -> low 40,   high NULL
--
-- En and em dashes are accepted because OCR and word processors both produce
-- them. Anything else returns NULLs, which is the honest answer for "Absent".
CREATE OR REPLACE FUNCTION lab.fn_parse_reference(p_text TEXT)
RETURNS TABLE (ref_low NUMERIC(14,4), ref_high NUMERIC(14,4))
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
  SELECT
    CASE
      WHEN m_band[1] IS NOT NULL THEN m_band[1]::NUMERIC
      WHEN m_gt[1]   IS NOT NULL THEN m_gt[1]::NUMERIC
    END,
    CASE
      WHEN m_band[2] IS NOT NULL THEN m_band[2]::NUMERIC
      WHEN m_lt[1]   IS NOT NULL THEN m_lt[1]::NUMERIC
    END
  FROM (
    SELECT
      regexp_match(coalesce(p_text, ''),
                   '^\s*(-?[0-9]+(?:\.[0-9]+)?)\s*[-–—]\s*(-?[0-9]+(?:\.[0-9]+)?)\s*$') AS m_band,
      regexp_match(coalesce(p_text, ''),
                   '^\s*[<≤]\s*=?\s*(-?[0-9]+(?:\.[0-9]+)?)\s*$') AS m_lt,
      regexp_match(coalesce(p_text, ''),
                   '^\s*[>≥]\s*=?\s*(-?[0-9]+(?:\.[0-9]+)?)\s*$') AS m_gt
  ) AS parsed;
$$;

COMMENT ON FUNCTION lab.fn_parse_reference IS
  'Printed reference range to numeric bounds. Handles "13.0 - 17.0", "< 200" '
  'and "> 40". Returns NULLs for a text range such as Absent, which is correct: '
  'reference_printed keeps the full text and these columns are the convenience.';


-- ----------------------------------------------------------------------------
-- Applied on the way in, for every write path
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION lab.fn_results_fill_reference()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.reference_printed IS NOT NULL
       AND (NEW.ref_low IS NULL AND NEW.ref_high IS NULL) THEN
        SELECT p.ref_low, p.ref_high
          INTO NEW.ref_low, NEW.ref_high
          FROM lab.fn_parse_reference(NEW.reference_printed) p;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS results_fill_reference ON lab.results;

CREATE TRIGGER results_fill_reference
    BEFORE INSERT ON lab.results
    FOR EACH ROW
    EXECUTE FUNCTION lab.fn_results_fill_reference();

COMMENT ON FUNCTION lab.fn_results_fill_reference IS
  'Fills ref_low and ref_high from reference_printed when both are NULL. Only '
  'when both are NULL, so a reviewer correcting a mis-parsed bound stays.';


-- ----------------------------------------------------------------------------
-- Backfill what is already stored
-- ----------------------------------------------------------------------------
-- The parsed bounds are computed in a subquery rather than by calling the
-- function in the UPDATE's own FROM clause: a set-returning function there
-- cannot reference the row being updated.
UPDATE lab.results r
SET    ref_low  = p.ref_low,
       ref_high = p.ref_high
FROM (
    SELECT x.id, q.ref_low, q.ref_high
    FROM   lab.results x
    CROSS  JOIN LATERAL lab.fn_parse_reference(x.reference_printed) q
    WHERE  x.reference_printed IS NOT NULL
      AND  x.ref_low  IS NULL
      AND  x.ref_high IS NULL
) p
WHERE  r.id = p.id
  AND  (p.ref_low IS NOT NULL OR p.ref_high IS NOT NULL);
