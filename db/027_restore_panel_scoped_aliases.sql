-- =============================================================================
-- Contexta - Lab extraction store
-- 027  Restore the panel-scoped alias logic that 025 destroyed
-- =============================================================================
-- WHAT WENT WRONG
--   025 rewrote fn_resolve_analyte to read panel membership from
--   lab.panel_analytes. It was built from the version in 003_functions.sql -
--   without checking that 007 had already replaced that function with a much
--   more careful one. CREATE OR REPLACE does not warn you; it simply wins.
--
--   What 007 added and 025 deleted:
--
--     requires_panel_id   an alias that only applies inside one panel.
--                         ('ALB', 'Albumin', NULL)                   the default
--                         ('UR_PROT', 'Albumin', URINE_ROUTINE)      urine only
--
--     the ambiguity rule  when a spelling matches several analytes and NOTHING
--                         distinguishes them - no practice override, no panel
--                         scope, no panel context - return nothing rather than
--                         pick. An honest blank over a coin toss.
--
--   Measured cost of the deletion: 7 rows across the corpus print ALBUMIN or ALB
--   under a urine heading, meaning urine protein, and all 7 resolved to serum
--   albumin. A wrong code on a clinical value, which is the one failure this
--   system is built to refuse.
--
-- WHY THE VERIFICATION DID NOT CATCH IT
--   scripts/diff_resolver.py compared the new function against a "legacy" copy
--   written from 003 - not against what was actually installed. Both lacked the
--   007 logic, so they agreed on all 34,003 comparisons. The number was real and
--   the baseline was wrong, which is worse than having no number at all.
--
--   A baseline must be read from the live database, never reconstructed from a
--   migration file. pg_get_functiondef is how.
--
-- WHAT THIS MIGRATION IS
--   007's function exactly, with one substitution: it cannot reference
--   a.panel_id, which 026 dropped. Every
--       (panel_id IS NOT DISTINCT FROM p_panel_id)
--   becomes
--       lab.fn_in_panel(analyte_id, p_panel_id)
--
--   One behaviour difference comes with that, and it is deliberate. The old test
--   was TRUE when both sides were NULL, so passing no panel quietly preferred
--   analytes belonging to no panel at all. fn_in_panel returns FALSE for a NULL
--   panel, so that accident is gone. Two analytes in the database belong to no
--   panel; neither is reachable by an ambiguous spelling.
-- =============================================================================

BEGIN;

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

    -- 1. exact spelling
    RETURN QUERY
    WITH cand AS (
        SELECT DISTINCT ON (a.id)
               a.id AS aid, a.code, lab.fn_in_panel(a.id, p_panel_id) AS in_panel,
               al.confidence, al.practice_id, al.requires_panel_id
        FROM   lab.analyte_aliases al
        JOIN   lab.analytes a ON a.id = al.analyte_id AND a.is_deleted = FALSE
        WHERE  al.is_deleted = FALSE
          AND  al.is_active  = TRUE
          AND  al.alias = p_label
          AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
          AND  (al.requires_panel_id IS NULL OR al.requires_panel_id = p_panel_id)
        ORDER  BY a.id, al.practice_id NULLS LAST, al.requires_panel_id NULLS LAST
    ), ranked AS (
        SELECT c.*, count(*) OVER () AS n,
               row_number() OVER (ORDER BY c.practice_id NULLS LAST,
                                           (c.requires_panel_id IS NOT NULL) DESC,
                                           c.in_panel DESC,
                                           c.aid) AS rn
        FROM   cand c
    )
    SELECT r.aid, r.code, 'exact_alias'::VARCHAR(20), r.confidence
    FROM   ranked r
    WHERE  r.rn = 1
      AND  (r.n = 1
            OR r.practice_id IS NOT NULL
            OR r.requires_panel_id IS NOT NULL
            OR r.in_panel);
    IF FOUND THEN RETURN; END IF;

    -- 2. same label once punctuation and case stop mattering
    RETURN QUERY
    WITH cand AS (
        SELECT DISTINCT ON (a.id)
               a.id AS aid, a.code, lab.fn_in_panel(a.id, p_panel_id) AS in_panel,
               LEAST(al.confidence, 0.9800)::NUMERIC(5,4) AS confidence,
               al.practice_id, al.requires_panel_id
        FROM   lab.analyte_aliases al
        JOIN   lab.analytes a ON a.id = al.analyte_id AND a.is_deleted = FALSE
        WHERE  al.is_deleted = FALSE
          AND  al.is_active  = TRUE
          AND  al.alias_normalised = v_norm
          AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
          AND  (al.requires_panel_id IS NULL OR al.requires_panel_id = p_panel_id)
        ORDER  BY a.id, al.practice_id NULLS LAST, al.requires_panel_id NULLS LAST
    ), ranked AS (
        SELECT c.*, count(*) OVER () AS n,
               row_number() OVER (ORDER BY c.practice_id NULLS LAST,
                                           (c.requires_panel_id IS NOT NULL) DESC,
                                           c.in_panel DESC,
                                           c.aid) AS rn
        FROM   cand c
    )
    SELECT r.aid, r.code, 'normalised_alias'::VARCHAR(20), r.confidence
    FROM   ranked r
    WHERE  r.rn = 1
      AND  (r.n = 1
            OR r.practice_id IS NOT NULL
            OR r.requires_panel_id IS NOT NULL
            OR r.in_panel);
    IF FOUND THEN RETURN; END IF;

    -- 3. close enough, and say how close. Only the best-scoring analytes are
    --    candidates; below that the similarity itself has already decided.
    RETURN QUERY
    WITH scored AS (
        SELECT DISTINCT ON (a.id)
               a.id AS aid, a.code, lab.fn_in_panel(a.id, p_panel_id) AS in_panel,
               al.practice_id, al.requires_panel_id,
               similarity(al.alias_normalised, v_norm) AS sim
        FROM   lab.analyte_aliases al
        JOIN   lab.analytes a ON a.id = al.analyte_id AND a.is_deleted = FALSE
        WHERE  al.is_deleted = FALSE
          AND  al.is_active  = TRUE
          AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
          AND  (al.requires_panel_id IS NULL OR al.requires_panel_id = p_panel_id)
          AND  similarity(al.alias_normalised, v_norm) >= p_min_similarity
        ORDER  BY a.id, similarity(al.alias_normalised, v_norm) DESC,
                  al.practice_id NULLS LAST
    ), best AS (
        SELECT s.* FROM scored s
        WHERE  s.sim = (SELECT max(x.sim) FROM scored x)
    ), ranked AS (
        SELECT b.*, count(*) OVER () AS n,
               row_number() OVER (ORDER BY b.practice_id NULLS LAST,
                                           (b.requires_panel_id IS NOT NULL) DESC,
                                           b.in_panel DESC,
                                           b.aid) AS rn
        FROM   best b
    )
    SELECT r.aid, r.code, 'fuzzy_alias'::VARCHAR(20), ROUND(r.sim::NUMERIC, 4)
    FROM   ranked r
    WHERE  r.rn = 1
      AND  (r.n = 1
            OR r.practice_id IS NOT NULL
            OR r.requires_panel_id IS NOT NULL
            OR r.in_panel);
END;
$$;

COMMENT ON FUNCTION lab.fn_resolve_analyte IS
  'Printed label to canonical analyte. Three passes - exact, normalised, fuzzy - '
  'stopping at the first hit. Returns no rows when nothing matches OR when '
  'several analytes match and nothing distinguishes them: the caller writes '
  'NULL, because a blank beats a guess. p_panel_id both filters aliases scoped '
  'to a panel (requires_panel_id) and prefers an analyte that is a member of it '
  'per lab.panel_analytes.';

COMMIT;
