-- =============================================================================
-- Contexta - Lab extraction store
-- 025  Panel preference reads the join table, not lab.analytes.panel_id
-- =============================================================================
-- Since 020, which panels an analyte belongs to lives in lab.panel_analytes.
-- lab.analytes.panel_id survived as a compatibility column and now says
-- something narrower than the truth: Calcium's panel_id reads ELECTROLYTES while
-- the join table has it in Renal, Electrolytes and Calcium, each with its own
-- role. Two answers to one question, and the stale one is the one a new query
-- reaches for first.
--
-- This migration moves every reader onto the join table. It does NOT drop the
-- column - that is 026, after the diff in scripts/diff_resolver.py has shown the
-- two give the same answer for every printed label in the database. The column
-- staying put is what makes that comparison possible at all.
--
-- WHAT CHANGES, PRECISELY
--   fn_resolve_analyte      "prefers an analyte in that panel" now means a
--                           MEMBER of that panel, which is strictly more
--                           permissive: an analyte can be a member of several
--                           panels, so nothing that is preferred today stops
--                           being preferred.
--   v_results_verified      reports the panel the PAGE declared for that row -
--                           report_sections.panel_id, set by fn_resolve_panel
--                           from the printed heading - rather than the analyte's
--                           nominal one. With membership many-to-many there is
--                           no single panel an analyte "is in", and the panel a
--                           result belongs to is a property of where it was
--                           printed, not of the analyte.
--
-- THE OLD FUNCTION IS KEPT as fn_resolve_analyte_legacy so the two can be run
-- side by side over real labels. Deleted in 026 once they agree.
-- =============================================================================

BEGIN;

-- -------------------------------------------------- is this analyte in that panel
-- Its own function so the three passes below read the same way they did when the
-- test was a column comparison, and so the membership rule lives in one place
-- rather than three ORDER BY clauses that can drift apart.
--
-- NULL panel means "no preference" and returns FALSE for everything, which is a
-- deliberate change: the old column test, a.panel_id IS NOT DISTINCT FROM NULL,
-- quietly preferred analytes that belonged to no panel at all whenever the
-- caller passed nothing. That was an accident of SQL null semantics, not a rule
-- anybody wrote down.
CREATE OR REPLACE FUNCTION lab.fn_in_panel(p_analyte_id BIGINT, p_panel_id BIGINT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY INVOKER
AS $$
    SELECT p_panel_id IS NOT NULL
       AND EXISTS (SELECT 1 FROM lab.panel_analytes pa
                   WHERE pa.analyte_id = p_analyte_id
                     AND pa.panel_id   = p_panel_id
                     AND pa.is_deleted = FALSE);
$$;

COMMENT ON FUNCTION lab.fn_in_panel IS
  'Membership test against lab.panel_analytes, replacing the analytes.panel_id '
  'comparison fn_resolve_analyte used before 025.';


-- ------------------------------------------------- the old one, preserved
CREATE OR REPLACE FUNCTION lab.fn_resolve_analyte_legacy(
    p_practice_id     BIGINT,
    p_label           TEXT,
    p_panel_id        BIGINT  DEFAULT NULL,
    p_min_similarity  REAL    DEFAULT 0.62
)
RETURNS TABLE (
    analyte_id    BIGINT,
    analyte_code  VARCHAR(40),
    match_method  VARCHAR(20),
    confidence    NUMERIC(5,4)
)
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
AS $$
DECLARE
    v_norm TEXT := lab.fn_normalise_label(p_label);
BEGIN
    IF v_norm = '' THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT a.id, a.code, 'exact_alias'::VARCHAR(20), al.confidence
    FROM   lab.analyte_aliases al
    JOIN   lab.analytes a ON a.id = al.analyte_id AND a.is_deleted = FALSE
    WHERE  al.is_deleted = FALSE AND al.is_active = TRUE
      AND  al.alias = p_label
      AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
    ORDER  BY al.practice_id NULLS LAST,
              (a.panel_id IS NOT DISTINCT FROM p_panel_id) DESC
    LIMIT  1;
    IF FOUND THEN RETURN; END IF;

    RETURN QUERY
    SELECT a.id, a.code, 'normalised_alias'::VARCHAR(20),
           LEAST(al.confidence, 0.9800)::NUMERIC(5,4)
    FROM   lab.analyte_aliases al
    JOIN   lab.analytes a ON a.id = al.analyte_id AND a.is_deleted = FALSE
    WHERE  al.is_deleted = FALSE AND al.is_active = TRUE
      AND  al.alias_normalised = v_norm
      AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
    ORDER  BY al.practice_id NULLS LAST,
              (a.panel_id IS NOT DISTINCT FROM p_panel_id) DESC
    LIMIT  1;
    IF FOUND THEN RETURN; END IF;

    RETURN QUERY
    SELECT a.id, a.code, 'fuzzy_alias'::VARCHAR(20),
           ROUND(similarity(al.alias_normalised, v_norm)::NUMERIC, 4)
    FROM   lab.analyte_aliases al
    JOIN   lab.analytes a ON a.id = al.analyte_id AND a.is_deleted = FALSE
    WHERE  al.is_deleted = FALSE AND al.is_active = TRUE
      AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
      AND  similarity(al.alias_normalised, v_norm) >= p_min_similarity
    ORDER  BY (a.panel_id IS NOT DISTINCT FROM p_panel_id) DESC,
              similarity(al.alias_normalised, v_norm) DESC
    LIMIT  1;
END;
$$;

COMMENT ON FUNCTION lab.fn_resolve_analyte_legacy IS
  'The pre-025 resolver, kept only so its answers can be diffed against the new '
  'one over real labels. Dropped in 026. Do not call it from anything.';


-- ------------------------------------------- the one everything actually uses
CREATE OR REPLACE FUNCTION lab.fn_resolve_analyte(
    p_practice_id     BIGINT,
    p_label           TEXT,
    p_panel_id        BIGINT  DEFAULT NULL,
    p_min_similarity  REAL    DEFAULT 0.62
)
RETURNS TABLE (
    analyte_id    BIGINT,
    analyte_code  VARCHAR(40),
    match_method  VARCHAR(20),
    confidence    NUMERIC(5,4)
)
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
AS $$
DECLARE
    v_norm TEXT := lab.fn_normalise_label(p_label);
BEGIN
    IF v_norm = '' THEN
        RETURN;
    END IF;

    -- 1. exact spelling, practice override beating the global row
    RETURN QUERY
    SELECT a.id, a.code, 'exact_alias'::VARCHAR(20), al.confidence
    FROM   lab.analyte_aliases al
    JOIN   lab.analytes a ON a.id = al.analyte_id AND a.is_deleted = FALSE
    WHERE  al.is_deleted = FALSE AND al.is_active = TRUE
      AND  al.alias = p_label
      AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
    ORDER  BY al.practice_id NULLS LAST,
              lab.fn_in_panel(a.id, p_panel_id) DESC,
              a.id
    LIMIT  1;
    IF FOUND THEN RETURN; END IF;

    -- 2. same label once punctuation and case stop mattering
    RETURN QUERY
    SELECT a.id, a.code, 'normalised_alias'::VARCHAR(20),
           LEAST(al.confidence, 0.9800)::NUMERIC(5,4)
    FROM   lab.analyte_aliases al
    JOIN   lab.analytes a ON a.id = al.analyte_id AND a.is_deleted = FALSE
    WHERE  al.is_deleted = FALSE AND al.is_active = TRUE
      AND  al.alias_normalised = v_norm
      AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
    ORDER  BY al.practice_id NULLS LAST,
              lab.fn_in_panel(a.id, p_panel_id) DESC,
              a.id
    LIMIT  1;
    IF FOUND THEN RETURN; END IF;

    -- 3. close enough, and say how close
    RETURN QUERY
    SELECT a.id, a.code, 'fuzzy_alias'::VARCHAR(20),
           ROUND(similarity(al.alias_normalised, v_norm)::NUMERIC, 4)
    FROM   lab.analyte_aliases al
    JOIN   lab.analytes a ON a.id = al.analyte_id AND a.is_deleted = FALSE
    WHERE  al.is_deleted = FALSE AND al.is_active = TRUE
      AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
      AND  similarity(al.alias_normalised, v_norm) >= p_min_similarity
    ORDER  BY lab.fn_in_panel(a.id, p_panel_id) DESC,
              similarity(al.alias_normalised, v_norm) DESC,
              a.id
    LIMIT  1;
END;
$$;

COMMENT ON FUNCTION lab.fn_resolve_analyte IS
  'Printed label to canonical analyte. Returns no rows when nothing matches - '
  'the caller must store NULL rather than guess. p_panel_id prefers an analyte '
  'that is a MEMBER of that panel per lab.panel_analytes: "Glucose" under a '
  'urine heading is UR_GLU, under a diabetes heading GLU_F.';

-- ------------------------------------------------------ the verified view
-- Was: LEFT JOIN lab.panels p ON p.id = a.panel_id - the analyte's nominal
-- panel. With membership many-to-many there is no such thing: Calcium is in
-- three. The panel a RESULT belongs to is a property of where it was printed,
-- which the pipeline already recorded on report_sections from the page's own
-- heading. So the view reports that, and reports nothing when the page gave no
-- heading - which is honest, where naming one of three panels was not.
CREATE OR REPLACE VIEW lab.v_results_verified AS
SELECT r.practice_id,
       r.patient_id,
       r.collected_at,
       a.code            AS analyte_code,
       a.display_name    AS analyte_name,
       p.code            AS panel_code,
       r.printed_label,
       r.value_text,
       r.value_numeric,
       r.value_operator,
       COALESCE(r.unit_canonical, r.unit_printed) AS unit,
       r.reference_printed,
       r.ref_low,
       r.ref_high,
       r.flag,
       r.is_derived,
       r.id              AS result_id,
       r.report_id,
       r.document_id
FROM   lab.results   r
JOIN   lab.documents d ON d.id = r.document_id
LEFT   JOIN lab.analytes       a ON a.id = r.analyte_id
LEFT   JOIN lab.report_sections s ON s.id = r.section_id
LEFT   JOIN lab.panels         p ON p.id = s.panel_id
WHERE  r.is_deleted = FALSE
  AND  d.is_deleted = FALSE
  AND  d.status = 'verified';

COMMIT;
