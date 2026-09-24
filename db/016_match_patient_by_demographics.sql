-- 016: match a patient on what the report printed, when it printed no usable UHID.
--
-- fn_match_patient_by_uhid answers the easy question. Plenty of reports carry no
-- identifier at all, or one the reading model mangled past recognition, and the only
-- thing left on the page is a name, an age and a sex.
--
-- This is deliberately a SEPARATE function rather than another branch inside the UHID
-- matcher. The two ask different questions with different risks: a UHID is an identifier
-- the practice issued, a name is not, and two patients at one clinic can share a name and
-- a birth year. Keeping them apart means the UHID path stays short enough to read, and
-- this one can be tested and tuned without touching it.
--
-- THE RULE THAT MATTERS: this function never returns confidence 1.0. A demographic match
-- always quarantines to needs_review. Only an exact UHID attaches a document to a patient
-- without a human looking at it.

CREATE OR REPLACE FUNCTION lab.fn_match_patient_by_demographics(
    p_practice_id    BIGINT,
    p_name           TEXT,
    p_dob            DATE    DEFAULT NULL,
    p_age_printed    TEXT    DEFAULT NULL,
    p_sex            TEXT    DEFAULT NULL,
    p_min_similarity REAL    DEFAULT 0.80,
    p_limit          INT     DEFAULT 5
)
RETURNS TABLE (
    patient_id   BIGINT,
    matched_name TEXT,
    match_method VARCHAR(30),
    confidence   NUMERIC(5,4),
    evidence     JSONB
)
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
AS $$
DECLARE
    v_name TEXT := lab.fn_normalise_label(COALESCE(p_name, ''));
    v_age  INT;
    v_sex  TEXT := NULLIF(UPPER(LEFT(TRIM(COALESCE(p_sex, '')), 1)), '');
BEGIN
    -- A name is the only thing worth matching on. Without one there is nothing here that
    -- distinguishes one patient from another, and guessing from age and sex alone would
    -- attach a stranger's results to a chart.
    IF v_name = '' THEN
        RETURN;
    END IF;

    -- Reports print "52", "11 Y", "11 Y / M", "52 years". Take the leading integer and
    -- ignore the rest; anything that is not a plain number is simply no age.
    v_age := NULLIF(substring(COALESCE(p_age_printed, '') FROM '^[^0-9]*([0-9]{1,3})'), '')::INT;

    RETURN QUERY
    WITH scored AS (
        SELECT
            pt.id,
            pt.first_name || ' ' || pt.last_name                          AS full_name,
            similarity(
                lab.fn_normalise_label(pt.first_name || ' ' || pt.last_name), v_name
            )::NUMERIC                                                    AS name_sim,
            (p_dob IS NOT NULL AND pt.dob = p_dob)                        AS dob_exact,
            -- Age is printed as it was AT COLLECTION, and a report can be read months
            -- later, so a year either side still corroborates. It is weak evidence and
            -- scores as such - it narrows a shortlist, it never confirms one.
            (p_dob IS NULL
             AND v_age IS NOT NULL
             AND pt.dob IS NOT NULL
             AND abs(date_part('year', age(pt.dob))::INT - v_age) <= 1)   AS age_close,
            (v_sex IS NOT NULL
             AND pt.gender IS NOT NULL
             AND UPPER(LEFT(pt.gender, 1)) = v_sex)                       AS sex_match,
            (v_sex IS NOT NULL
             AND pt.gender IS NOT NULL
             AND UPPER(LEFT(pt.gender, 1)) <> v_sex)                      AS sex_differs
        FROM   core.patients pt
        WHERE  pt.practice_id = p_practice_id
          AND  pt.is_deleted = FALSE
    )
    SELECT
        s.id,
        s.full_name,
        CASE
            WHEN s.dob_exact THEN 'name_dob'
            WHEN s.age_close THEN 'name_age'
            ELSE                   'name_only'
        END::VARCHAR(30),
        -- Capped at 0.95 by construction. The cap is the point: whatever the evidence,
        -- the caller must still quarantine, because none of this is an identifier.
        LEAST(
            0.9500,
            ROUND(
                  s.name_sim * 0.60
                + CASE WHEN s.dob_exact  THEN 0.30 ELSE 0 END
                + CASE WHEN s.age_close  THEN 0.15 ELSE 0 END
                + CASE WHEN s.sex_match  THEN 0.05 ELSE 0 END
            , 4)
        )::NUMERIC(5,4),
        jsonb_build_object(
            'name_similarity', ROUND(s.name_sim, 4),
            'dob',  CASE WHEN s.dob_exact THEN 'exact'
                         WHEN s.age_close THEN 'age_within_1_year'
                         ELSE 'no_evidence' END,
            'sex',  CASE WHEN s.sex_match   THEN 'match'
                         WHEN s.sex_differs THEN 'differs'
                         ELSE 'no_evidence' END,
            'printed_name', p_name
        )
    FROM   scored s
    WHERE  s.name_sim >= p_min_similarity
      -- A printed sex that contradicts the record is disqualifying, not merely
      -- unhelpful. Two people can share a name; the same person does not change sex
      -- between the requisition and the report, and letting a contradiction through
      -- on a strong name score is how the wrong chart gets the results.
      AND  NOT s.sex_differs
    ORDER  BY 4 DESC, s.name_sim DESC
    LIMIT  p_limit;
END;
$$;

COMMENT ON FUNCTION lab.fn_match_patient_by_demographics IS
  'Shortlist patients from the printed name, age and sex when no usable UHID was read. '
  'Never returns confidence 1.0: a demographic match always quarantines for review, and '
  'a printed sex that contradicts the record disqualifies the candidate outright.';
