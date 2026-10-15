-- =============================================================================
-- Contexta - Lab extraction store
-- 035  A person adds a row the reading missed
-- =============================================================================
-- Run after 034.
--
-- WHY
--   A reviewer could correct a row and remove one, but not add one. When the
--   reading lost a test the page plainly printed - or a panel listed a test as
--   missing that sits on page four - the only way to record it was not at all.
--
-- WHAT
--   lab.fn_add_result inserts one result under the document's first report,
--   in the section whose printed heading matches p_heading (or the first
--   section; or a new "Added by hand" section when the document has none).
--
--   It is a person's entry, so it stands on the same footing as a correction:
--   match_method 'manual' when it carries a code, 'none' when it does not;
--   is_reviewed with the actor and the time; and a 'result_added' event.
--   An unknown test keeps its printed name and NO code - never a guessed one.
--   The value is parsed exactly as fn_correct_result parses a typed value, the
--   flag goes through fn_normalise_flag, and the reference band is filled by
--   the trigger from 008.
-- =============================================================================

CREATE OR REPLACE FUNCTION lab.fn_add_result(
    p_practice_id  BIGINT,
    p_document_id  BIGINT,
    p_actor        BIGINT,
    p_label        TEXT,
    p_value        TEXT,
    p_unit         TEXT        DEFAULT NULL,
    p_reference    TEXT        DEFAULT NULL,
    p_flag         TEXT        DEFAULT NULL,
    p_analyte_code VARCHAR(40) DEFAULT NULL,
    p_heading      TEXT        DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
AS $$
DECLARE
    v_doc       lab.documents%ROWTYPE;
    v_report    lab.reports%ROWTYPE;
    v_section   BIGINT;
    v_analyte   BIGINT;
    v_label     TEXT;
    v_numeric   NUMERIC(14,4);
    v_operator  VARCHAR(2);
    v_id        BIGINT;
BEGIN
    SELECT * INTO v_doc FROM lab.documents
    WHERE  id = p_document_id AND practice_id = p_practice_id AND is_deleted = FALSE
    FOR    UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'document % not found in practice %', p_document_id, p_practice_id;
    END IF;
    IF v_doc.status IN ('received', 'parsing', 'failed', 'rejected') THEN
        RAISE EXCEPTION 'a % document cannot take new rows', v_doc.status;
    END IF;

    IF nullif(btrim(coalesce(p_value, '')), '') IS NULL THEN
        RAISE EXCEPTION 'a row needs a value';
    END IF;

    IF nullif(btrim(coalesce(p_analyte_code, '')), '') IS NOT NULL THEN
        SELECT id, display_name INTO v_analyte, v_label FROM lab.analytes
        WHERE  code = upper(btrim(p_analyte_code)) AND is_deleted = FALSE;
        IF v_analyte IS NULL THEN
            RAISE EXCEPTION 'no analyte with code %', p_analyte_code;
        END IF;
    END IF;
    -- What the page printed, when typed; else our name for the test.
    v_label := coalesce(nullif(btrim(coalesce(p_label, '')), ''), v_label);
    IF v_label IS NULL THEN
        RAISE EXCEPTION 'a row needs a test name or a code';
    END IF;

    SELECT * INTO v_report FROM lab.reports
    WHERE  document_id = p_document_id AND is_deleted = FALSE
    ORDER  BY sequence, id LIMIT 1;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'document % has no report to add to', p_document_id;
    END IF;

    SELECT id INTO v_section FROM lab.report_sections
    WHERE  report_id = v_report.id AND is_deleted = FALSE
    ORDER  BY (lower(btrim(heading_printed)) = lower(btrim(coalesce(p_heading, '')))) DESC,
              sequence, id
    LIMIT  1;
    IF v_section IS NULL THEN
        INSERT INTO lab.report_sections (report_id, practice_id, heading_printed, sequence)
        VALUES (v_report.id, p_practice_id, 'Added by hand', 1)
        RETURNING id INTO v_section;
    END IF;

    -- Parsed as fn_correct_result parses a typed value: "<0.01" keeps its
    -- operator, and a text result has no number rather than zero.
    v_operator := nullif(substring(btrim(p_value) from '^(<=|>=|<|>)'), '');
    BEGIN
        v_numeric := regexp_replace(btrim(p_value), '^(<=|>=|<|>)\s*', '')::NUMERIC;
    EXCEPTION WHEN others THEN
        v_numeric := NULL;
    END;

    INSERT INTO lab.results (
        section_id, report_id, document_id, practice_id, patient_id, collected_at,
        printed_label, analyte_id, match_method, match_confidence,
        value_text, value_numeric, value_operator, unit_printed, reference_printed, flag,
        is_text_result, sequence, is_reviewed, reviewed_by, reviewed_at, created_by)
    VALUES (
        v_section, v_report.id, p_document_id, p_practice_id, v_doc.patient_id,
        v_report.collected_at,
        left(v_label, 255), v_analyte,
        CASE WHEN v_analyte IS NULL THEN 'none' ELSE 'manual' END,
        CASE WHEN v_analyte IS NULL THEN NULL ELSE 1.0000 END,
        left(btrim(p_value), 255), v_numeric, v_operator,
        nullif(btrim(coalesce(p_unit, '')), ''),
        nullif(btrim(coalesce(p_reference, '')), ''),
        lab.fn_normalise_flag(p_flag),
        v_numeric IS NULL,
        (SELECT coalesce(max(sequence), 0) + 1 FROM lab.results WHERE section_id = v_section),
        TRUE, p_actor, now(), p_actor)
    RETURNING id INTO v_id;

    INSERT INTO lab.document_events (document_id, practice_id, event_type, detail, actor_user_id)
    VALUES (p_document_id, p_practice_id, 'result_added',
            jsonb_strip_nulls(jsonb_build_object(
                'result_id', v_id, 'label', v_label, 'value', btrim(p_value),
                'analyte', upper(nullif(btrim(coalesce(p_analyte_code, '')), '')))),
            p_actor);

    RETURN v_id;
END;
$$;

COMMENT ON FUNCTION lab.fn_add_result IS
  'A person adds one row the reading missed. Marked reviewed, match_method '
  'manual (or none without a code), recorded as result_added. An unknown test '
  'keeps its printed name and no code.';
