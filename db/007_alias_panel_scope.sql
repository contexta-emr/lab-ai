-- =============================================================================
-- Contexta - Lab extraction store
-- 007  Panel-scoped aliases: making panel disambiguation actually possible
-- =============================================================================
-- Run after 006.
--
-- THE PROBLEM THIS FIXES
--   docs/architecture.md section 4 promises that panel context disambiguates a
--   printed label: "Glucose under a urine heading is UR_GLU; under a diabetes
--   heading it is GLU_F". fn_resolve_analyte was written for that - every pass
--   orders by (a.panel_id IS NOT DISTINCT FROM p_panel_id) DESC.
--
--   It could never happen. The unique index from 001 was
--       (alias_normalised, COALESCE(practice_id, 0))
--   which permits exactly ONE analyte per spelling, globally. With one candidate
--   there is never a tie, so the panel clause in every ORDER BY was dead code.
--   The schema forbade precisely what the resolver was built to resolve.
--
--   Measured cost in the 300-report corpus: 17 rows print ALBUMIN or ALB under a
--   urine heading and mean urine protein (values "Absent", "Trace", "++", no
--   unit). All 17 resolved to ALB - serum albumin, numeric, g/dL. A wrong code,
--   which CLAUDE.md section 7 says never to produce.
--
-- WHY NOT JUST ALLOW DUPLICATE SPELLINGS
--   Because it trades one bug for another. 14 of the 59 serum albumin rows sit
--   under generic headings - "Biochemistry Screen", "Biochemistry - Liver and
--   Renal" - that resolve to no panel at all. Make "Albumin" ambiguous outright
--   and those 14 lose their code too: 16 fixed, 14 broken, no net gain.
--
-- THE FIX
--   An alias may be CONDITIONAL on a panel. requires_panel_id NULL means the
--   alias always applies - that is every existing row and stays the default.
--   A value means the alias only applies when the section resolved to that
--   panel, and when it does it BEATS the unconditional one.
--
--     ('ALB',     'Albumin', requires_panel_id = NULL)           the default
--     ('UR_PROT', 'Albumin', requires_panel_id = URINE_ROUTINE)  urine only
--
--   Under a urine heading      -> UR_PROT   (scoped alias wins)
--   Under an LFT heading       -> ALB       (scoped alias not eligible)
--   Under "Biochemistry Screen"-> ALB       (no panel, scoped alias not eligible)
--
--   Measured against the sealed answer key, all 4,177 rows: wrong codes 17 -> 0,
--   serum albumin regressions 0, exact resolution 99.88% before the fuzzy pass.
--
--   Nothing is done to Glucose. Bare "Glucose" is seeded to UR_GLU and GLU_F
--   carries only qualified spellings, so the corpus produces zero glucose
--   mismatches today. The mechanism is here when a report proves otherwise.
-- =============================================================================


-- ----------------------------------------------------------------------------
-- 1. The column
-- ----------------------------------------------------------------------------
ALTER TABLE lab.analyte_aliases
    ADD COLUMN IF NOT EXISTS requires_panel_id BIGINT REFERENCES lab.panels(id);

COMMENT ON COLUMN lab.analyte_aliases.requires_panel_id IS
  'NULL - the alias always applies. A panel id - the alias applies only when the '
  'section resolved to that panel, and then it beats the unconditional alias. '
  'This is how one printed spelling can mean two analytes on two kinds of report.';


-- ----------------------------------------------------------------------------
-- 2. The index that was blocking it
-- ----------------------------------------------------------------------------
-- The new key still forbids real ambiguity: within one panel scope and one
-- practice a spelling maps to exactly one analyte. What it now permits is one
-- unconditional alias plus one override per panel - so any (label, panel) pair
-- has at most two candidates, and the resolver knows which of the two wins.
DROP INDEX IF EXISTS lab.analyte_aliases_norm_uq;

CREATE UNIQUE INDEX analyte_aliases_norm_uq
    ON lab.analyte_aliases (alias_normalised,
                            COALESCE(requires_panel_id, 0),
                            COALESCE(practice_id, 0))
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS analyte_aliases_scope_idx
    ON lab.analyte_aliases (requires_panel_id)
    WHERE is_deleted = FALSE AND requires_panel_id IS NOT NULL;


-- ----------------------------------------------------------------------------
-- 3. The resolver
-- ----------------------------------------------------------------------------
-- Same three passes, same order, same return shape. Two changes:
--
--   a) a pass only considers aliases eligible for this panel
--      (requires_panel_id IS NULL OR requires_panel_id = p_panel_id)
--
--   b) when a pass produces two or more candidate ANALYTES, one of them has to
--      win for a stated reason - it is a practice override, or its alias is
--      scoped to this panel, or the analyte itself belongs to this panel. If
--      none of those separates them the function returns NO ROWS and the caller
--      writes NULL. An arbitrary pick between two clinical codes is the one
--      outcome this service must never produce.
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
               a.id AS aid, a.code, a.panel_id, al.confidence,
               al.practice_id, al.requires_panel_id
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
                                           (c.panel_id IS NOT DISTINCT FROM p_panel_id) DESC,
                                           c.aid) AS rn
        FROM   cand c
    )
    SELECT r.aid, r.code, 'exact_alias'::VARCHAR(20), r.confidence
    FROM   ranked r
    WHERE  r.rn = 1
      AND  (r.n = 1
            OR r.practice_id IS NOT NULL
            OR r.requires_panel_id IS NOT NULL
            OR r.panel_id IS NOT DISTINCT FROM p_panel_id);
    IF FOUND THEN RETURN; END IF;

    -- 2. same label once punctuation and case stop mattering
    RETURN QUERY
    WITH cand AS (
        SELECT DISTINCT ON (a.id)
               a.id AS aid, a.code, a.panel_id,
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
                                           (c.panel_id IS NOT DISTINCT FROM p_panel_id) DESC,
                                           c.aid) AS rn
        FROM   cand c
    )
    SELECT r.aid, r.code, 'normalised_alias'::VARCHAR(20), r.confidence
    FROM   ranked r
    WHERE  r.rn = 1
      AND  (r.n = 1
            OR r.practice_id IS NOT NULL
            OR r.requires_panel_id IS NOT NULL
            OR r.panel_id IS NOT DISTINCT FROM p_panel_id);
    IF FOUND THEN RETURN; END IF;

    -- 3. close enough, and say how close. Only the best-scoring analytes are
    --    candidates; below that the similarity itself has already decided.
    RETURN QUERY
    WITH scored AS (
        SELECT DISTINCT ON (a.id)
               a.id AS aid, a.code, a.panel_id, al.practice_id, al.requires_panel_id,
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
                                           (b.panel_id IS NOT DISTINCT FROM p_panel_id) DESC,
                                           b.aid) AS rn
        FROM   best b
    )
    SELECT r.aid, r.code, 'fuzzy_alias'::VARCHAR(20), ROUND(r.sim::NUMERIC, 4)
    FROM   ranked r
    WHERE  r.rn = 1
      AND  (r.n = 1
            OR r.practice_id IS NOT NULL
            OR r.requires_panel_id IS NOT NULL
            OR r.panel_id IS NOT DISTINCT FROM p_panel_id);
END;
$$;

COMMENT ON FUNCTION lab.fn_resolve_analyte IS
  'Printed label to canonical analyte. Three passes: exact, normalised, trigram. '
  'An alias scoped to a panel beats an unconditional one when the section matched '
  'that panel. Returns no rows when nothing matches OR when two analytes remain '
  'and nothing separates them - the caller must store NULL rather than guess.';


-- ----------------------------------------------------------------------------
-- 4. The first two scoped aliases, and the heading that was missing
-- ----------------------------------------------------------------------------
-- Urine reports print the protein line as ALBUMIN or ALB as often as Protein.
-- Spelled exactly as the serum aliases are spelled, so both passes see a
-- symmetric pair and the panel decides which one is meant.
INSERT INTO lab.analyte_aliases (analyte_id, alias, source, confidence, requires_panel_id)
SELECT a.id, v.alias, 'manual', 1.0000, p.id
FROM (VALUES
    ('UR_PROT', 'Albumin', 'URINE_ROUTINE'),
    ('UR_PROT', 'Alb',     'URINE_ROUTINE')
) AS v(analyte_code, alias, panel_code)
JOIN lab.analytes a ON a.code = v.analyte_code
JOIN lab.panels   p ON p.code = v.panel_code
WHERE NOT EXISTS (
    SELECT 1 FROM lab.analyte_aliases al
    WHERE al.alias_normalised = lab.fn_normalise_label(v.alias)
      AND al.requires_panel_id = p.id
      AND al.practice_id IS NULL
      AND al.is_deleted = FALSE
);

-- "Urine, Midstream" was the one urine heading with no panel alias, which left
-- its rows with no panel context for the rule above to use.
INSERT INTO lab.panel_aliases (panel_id, alias, source)
SELECT p.id, v.alias, 'manual'
FROM (VALUES
    ('URINE_ROUTINE', 'Urine, Midstream')
) AS v(panel_code, alias)
JOIN lab.panels p ON p.code = v.panel_code
WHERE NOT EXISTS (
    SELECT 1 FROM lab.panel_aliases pa
    WHERE pa.alias_normalised = lab.fn_normalise_label(v.alias)
      AND pa.practice_id IS NULL
      AND pa.is_deleted = FALSE
);
