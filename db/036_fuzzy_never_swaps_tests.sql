-- =============================================================================
-- Contexta - Lab extraction store
-- 036  A near-miss must not swap one test for another
-- =============================================================================
-- Run after 035. Replaces lab.fn_resolve_analyte from 027; only its third,
-- fuzzy tier changes. Exact and normalised matches are untouched.
--
-- WHAT WENT WRONG
--   "Total RBC Count" is not a spelling the alias master holds. The fuzzy tier
--   found "Total WBC Count" at 0.65 similarity (the floor is 0.62), and
--   Ashwini's red cell count (2026-10-15) was stored as a WHITE cell count -
--   a confident wrong code, the one outcome CLAUDE.md section 7 forbids.
--
-- THE GUARD
--   One letter apart is what fuzzy matching is for - unless that letter is
--   the test. A candidate alias is refused when a word of the printed label is,
--   by itself, an alias of a DIFFERENT analyte and the candidate alias does not
--   contain that word. "rbc" names RBC; "total wbc count" lacks it; refused, and
--   the row is left blank for a person. A misspelling of the SAME test
--   ("Haemoglobn") is untouched: no word of it names another test. Only words
--   of four letters or fewer can veto - swaps come from abbreviations.
--
--   Measured 2026-10-15 over all 26 fuzzily matched labels stored locally.
--   Three change, all to blank, none to another code:
--     "Total RBC Count"          was WBC   - the swap this exists to stop
--     "Prothrombin Time (INR)"   was PT    - the label names PT and INR both
--     "Glycated Hemoglobin Alc"  was HBA1C - the engine read "A1c" as "Alc",
--                                            and "alc" names Absolute
--                                            Lymphocyte Count
--   The last is a correct match lost to an OCR typo. Accepted: a blank costs
--   a person one edit, a wrong code silently corrupts a trend line. No alias
--   was added to rescue it - it may be a holdout spelling.
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
          -- 036: a near-miss must not swap one test for another. When a word of
          -- the printed label is, on its own, the name of a DIFFERENT test
          -- ("rbc") and this alias does not contain that word, the two names
          -- differ by exactly the thing that tells the tests apart.
          AND  NOT EXISTS (
                   SELECT 1
                   -- Words as printed: labels are normalised without spaces
                   -- ("totalrbccount"), so the words come from p_label itself.
                   FROM   regexp_split_to_table(lower(p_label), '[^a-z0-9]+') AS tok(word)
                   JOIN   lab.analyte_aliases other
                          ON  other.alias_normalised = tok.word
                          AND other.analyte_id <> a.id
                          AND other.is_deleted = FALSE
                          AND other.is_active  = TRUE
                          AND (other.practice_id IS NULL OR other.practice_id = p_practice_id)
                   -- Short words only: swaps come from abbreviations a letter
                   -- apart (rbc/wbc, hdl/ldl, t3/t4, alt/ast). A long word -
                   -- "hemoglobin" inside "Glycated Hemoglobin" - is part of the
                   -- name, and vetoing it lost a correct HbA1c match.
                   WHERE  tok.word <> '' AND length(tok.word) <= 4
                     AND  NOT (tok.word = ANY (regexp_split_to_array(lower(al.alias), '[^a-z0-9]+')))
               )
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
