-- =============================================================================
-- Contexta - Lab extraction store
-- 014  A human corrects what the machine read
-- =============================================================================
-- Run after 013.
--
-- WHY
--   Every screen so far could only accept or reject a whole document. A
--   reviewer looking at a row where the engine read "1O.5" for "10.5", or
--   mapped a label to the wrong code, or invented a row out of a footer, had
--   two options: verify a document they know is wrong, or reject a page that
--   is almost entirely right. Neither is what they want, and one of them puts
--   a bad number on a patient's chart.
--
--   These two functions are the third option. The reviewer fixes the row.
--
-- WHAT IS AUDITED, AND WHY THAT MATTERS MORE HERE THAN USUALLY
--   corrected_from_analyte_id has been in lab.results since 002, described
--   there as "what the machine thought before a human changed it - the
--   training signal for the alias master". This is the function that fills it.
--   Every correction is also a row in lab.document_events carrying the old and
--   new values, because a misfiled result is a patient-safety event and the
--   question afterwards is always how it got there.
--
--   A correction that renames a label is the most valuable signal the system
--   produces: it is a real spelling a real lab printed, mapped by a human to a
--   real code. That is exactly what lab.analyte_aliases needs and cannot
--   invent for itself.
--
-- DELETION IS SOFT
--   fn_remove_result sets is_deleted rather than deleting. A row the engine
--   invented is still evidence of what it does wrong, and a reviewer who
--   removes the wrong row must be able to have it back.
-- =============================================================================


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
           flag          = CASE WHEN p_flag IS NULL THEN flag
                                ELSE NULLIF(upper(btrim(p_flag)), '') END,
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
  'NULL leaves a field alone; passing an empty string clears it.';


CREATE OR REPLACE FUNCTION lab.fn_remove_result(
    p_practice_id BIGINT,
    p_result_id   BIGINT,
    p_actor       BIGINT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
AS $$
DECLARE
    v_label    TEXT;
    v_document BIGINT;
BEGIN
    UPDATE lab.results
    SET    is_deleted = TRUE,
           deleted_at = now(),
           deleted_by = p_actor,
           updated_at = now()
    WHERE  id = p_result_id AND practice_id = p_practice_id AND is_deleted = FALSE
    RETURNING printed_label, document_id INTO v_label, v_document;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'result % not found in practice %', p_result_id, p_practice_id;
    END IF;

    INSERT INTO lab.document_events (document_id, practice_id, event_type,
                                     detail, actor_user_id)
    VALUES (v_document, p_practice_id, 'result_removed',
            jsonb_build_object('result_id', p_result_id, 'printed_label', v_label),
            p_actor);

    RETURN p_result_id;
END;
$$;

COMMENT ON FUNCTION lab.fn_remove_result IS
  'Soft-deletes one row a reviewer says is not a result. Recoverable on '
  'purpose: a row the engine invented is evidence of what it gets wrong, and '
  'a reviewer who removes the wrong one must be able to have it back.';
