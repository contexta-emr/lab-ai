-- =============================================================================
-- Contexta - Lab extraction store
-- 015  A flag is a closed domain, not a short string
-- =============================================================================
-- Run after 014.
--
-- WHAT WENT WRONG
--   lab.results.flag is VARCHAR(4) with a CHECK allowing exactly H, L, HH, LL,
--   A and N. The OCR payload builder treated it as a short text field and
--   clipped whatever the flag column held to four characters to make it fit.
--   When column-role inference picked a column that was not a flag column, the
--   word "Interpretation" became "Inte", which is not too long and is not a
--   flag either - so it passed the length and failed the CHECK, the INSERT
--   aborted, and the whole document was lost. Four reports of the first
--   fifty-seven in the corpus run died that way, each after three OpenParser
--   calls, each yielding nothing from a page the engine had read perfectly.
--
--   The reader side is fixed in api/app/services/ocr_ingest.py, which now
--   validates against the six rather than truncating. This migration fixes the
--   other way in.
--
-- THE OTHER WAY IN
--   fn_correct_result, added in 014, takes the flag a reviewer types in the
--   review screen and stores upper(btrim(p_flag)). A reviewer typing "High" -
--   which is what the word means and what half the printed reports say - gets
--   HIGH: four characters, passes the length, fails the CHECK, 500. Typing
--   "Interpretation" gets "value too long" instead. Both are the same bug as
--   the one above, reached from the UI instead of from the engine.
--
-- WHY A FUNCTION AND NOT A TRIGGER
--   008 fixed ref_low/ref_high with a BEFORE INSERT trigger and explained why.
--   That option is not available here: VARCHAR(4) is enforced when the tuple
--   is built, which happens before any BEFORE trigger runs, so a trigger never
--   sees an over-long flag to rescue. Measured, not assumed - a temp table
--   with a NEW.flag := NULL trigger still raises "value too long". The
--   normalisation has to happen in the expression that writes the column.
--
-- UNRECOGNISED IS NULL
--   The same rule as an unknown analyte code, for the same reason. The six are
--   what the column means. A value outside them is something we did not
--   understand, and an honest blank beats forcing it in - nothing downstream
--   reads flag to decide a number, so a dropped flag costs a display hint and
--   a wrong one asserts a clinical judgement nobody made.
-- =============================================================================


CREATE OR REPLACE FUNCTION lab.fn_normalise_flag(p_text TEXT)
RETURNS VARCHAR(4)
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT CASE upper(btrim(COALESCE(p_text, '')))
        WHEN 'H'        THEN 'H'
        WHEN 'HIGH'     THEN 'H'
        WHEN U&'\2191'  THEN 'H'
        WHEN 'L'        THEN 'L'
        WHEN 'LOW'      THEN 'L'
        WHEN U&'\2193'  THEN 'L'
        WHEN 'HH'       THEN 'HH'
        WHEN U&'\2191\2191' THEN 'HH'
        WHEN 'LL'       THEN 'LL'
        WHEN U&'\2193\2193' THEN 'LL'
        WHEN 'A'        THEN 'A'
        WHEN 'ABNORMAL' THEN 'A'
        WHEN '*'        THEN 'A'
        WHEN '**'       THEN 'A'
        WHEN 'N'        THEN 'N'
        WHEN 'NORMAL'   THEN 'N'
        ELSE NULL
    END::VARCHAR(4);
$$;

COMMENT ON FUNCTION lab.fn_normalise_flag IS
  'Whatever was printed or typed, mapped to one of the six lab.results.flag '
  'allows, or NULL. Kept in step with _FLAGS in api/app/services/ocr_ingest.py.';


-- Unchanged from 014 apart from the flag expression, which now normalises
-- instead of upper-casing. Repeated in full because CREATE OR REPLACE takes a
-- whole body and an applied migration is not edited.
CREATE OR REPLACE FUNCTION lab.fn_correct_result(
    p_practice_id  BIGINT,
    p_result_id    BIGINT,
    p_actor        BIGINT DEFAULT NULL,
    p_label        TEXT   DEFAULT NULL,
    p_value        TEXT   DEFAULT NULL,
    p_unit         TEXT   DEFAULT NULL,
    p_reference    TEXT   DEFAULT NULL,
    p_flag         TEXT   DEFAULT NULL,
    p_analyte_code VARCHAR(40) DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
AS $$
DECLARE
    v_before        lab.results%ROWTYPE;
    v_new_analyte   BIGINT;
    v_document      BIGINT;
    v_numeric       NUMERIC(14,4);
    v_operator      VARCHAR(2);
BEGIN
    SELECT * INTO v_before
    FROM   lab.results
    WHERE  id = p_result_id AND practice_id = p_practice_id AND is_deleted = FALSE
    FOR    UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'result % not found in practice %', p_result_id, p_practice_id;
    END IF;
    v_document := v_before.document_id;

    -- An empty code clears the mapping, which is a legitimate correction: a
    -- reviewer who cannot say what a row is must be able to say so, and a
    -- blank is always better than a confident wrong code.
    IF p_analyte_code IS NOT NULL THEN
        IF btrim(p_analyte_code) = '' THEN
            v_new_analyte := NULL;
        ELSE
            SELECT id INTO v_new_analyte FROM lab.analytes
            WHERE  code = upper(btrim(p_analyte_code)) AND is_deleted = FALSE;
            IF v_new_analyte IS NULL THEN
                RAISE EXCEPTION 'no analyte with code %', p_analyte_code;
            END IF;
        END IF;
    ELSE
        v_new_analyte := v_before.analyte_id;
    END IF;

    -- Re-derive the numeric form from whatever the human typed. Storing a new
    -- value_text while leaving the old value_numeric behind would leave the
    -- table and the chart disagreeing, and the chart is what gets believed.
    IF p_value IS NOT NULL THEN
        -- "<0.01" charts as a bound, not as exactly 0.01, so the operator
        -- is split off and kept rather than folded into the number.
        v_operator := NULLIF(substring(btrim(p_value) from '^(<=|>=|<|>)'), '');
        BEGIN
            v_numeric := regexp_replace(btrim(p_value), '^(<=|>=|<|>)\s*', '')::NUMERIC;
        EXCEPTION WHEN others THEN
            -- A text result. NULL is correct and is not zero: value_text keeps
            -- what was typed and the chart simply has no point for it.
            v_numeric := NULL;
        END;
    ELSE
        v_numeric := v_before.value_numeric;
        v_operator := v_before.value_operator;
    END IF;

    UPDATE lab.results
    SET    printed_label = COALESCE(NULLIF(btrim(p_label), ''), printed_label),
           value_text    = COALESCE(p_value, value_text),
           value_numeric = v_numeric,
           value_operator = v_operator,
           unit_printed  = CASE WHEN p_unit IS NULL THEN unit_printed
                                ELSE NULLIF(btrim(p_unit), '') END,
           reference_printed = CASE WHEN p_reference IS NULL THEN reference_printed
                                    ELSE NULLIF(btrim(p_reference), '') END,
           -- The one line that changed. A reviewer types what the page says -
           -- "High", not "H" - and used to get a 500 for being right.
           flag          = CASE WHEN p_flag IS NULL THEN flag
                                ELSE lab.fn_normalise_flag(p_flag) END,
           analyte_id    = v_new_analyte,
           -- Only when the mapping actually changed, and only the FIRST time,
           -- so a second edit does not overwrite what the machine originally
           -- thought. That original guess is the whole value of the column.
           corrected_from_analyte_id =
               CASE WHEN v_new_analyte IS DISTINCT FROM v_before.analyte_id
                         AND corrected_from_analyte_id IS NULL
                    THEN v_before.analyte_id ELSE corrected_from_analyte_id END,
           match_method  = CASE WHEN v_new_analyte IS DISTINCT FROM v_before.analyte_id
                                THEN 'manual' ELSE match_method END,
           match_confidence = CASE WHEN v_new_analyte IS DISTINCT FROM v_before.analyte_id
                                   THEN 1.0000 ELSE match_confidence END,
           is_reviewed   = TRUE,
           reviewed_by   = p_actor,
           reviewed_at   = now(),
           updated_at    = now(),
           updated_by    = p_actor
    WHERE  id = p_result_id;

    INSERT INTO lab.document_events (document_id, practice_id, event_type,
                                     detail, actor_user_id)
    VALUES (v_document, p_practice_id, 'result_corrected',
            jsonb_strip_nulls(jsonb_build_object(
                'result_id',  p_result_id,
                'was_label',  v_before.printed_label,
                'now_label',  p_label,
                'was_value',  v_before.value_text,
                'now_value',  p_value,
                'was_analyte', (SELECT code FROM lab.analytes WHERE id = v_before.analyte_id),
                'now_analyte', (SELECT code FROM lab.analytes WHERE id = v_new_analyte))),
            p_actor);

    RETURN p_result_id;
END;
$$;

COMMENT ON FUNCTION lab.fn_correct_result IS
  'A human fixes one row. Records what the machine thought in '
  'corrected_from_analyte_id and the whole change in document_events. Passing '
  'NULL leaves a field alone; passing an empty string clears it. The flag is '
  'normalised through fn_normalise_flag rather than stored as typed.';


DO $$
BEGIN
    ASSERT lab.fn_normalise_flag('High') = 'H',  'word spellings map';
    ASSERT lab.fn_normalise_flag(' h ')  = 'H',  'trimmed and upper-cased';
    ASSERT lab.fn_normalise_flag('*')    = 'A',  'asterisk means abnormal';
    ASSERT lab.fn_normalise_flag('Interpretation') IS NULL, 'prose is not a flag';
    ASSERT lab.fn_normalise_flag('Inte') IS NULL, 'nor is prose cut to fit';
    ASSERT lab.fn_normalise_flag(NULL)   IS NULL;
    RAISE NOTICE '015 self-check ok';
END $$;
