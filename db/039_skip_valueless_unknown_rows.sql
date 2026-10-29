-- =============================================================================
-- Contexta - Lab extraction store
-- 039  A line with no value and no test name is not a result
-- =============================================================================
-- Run after 038.
--
-- WHY
--   Real reports print a banded range on the lines under a test:
--
--       APOLIPOPROTEIN - A1      124   mg/dL
--       Male : 86 - 152
--       Female : 94 - 162
--
--   Each band line was stored as a result of its own, with no value: 149 such
--   rows over twelve real reports (2026-10-28), with section titles, header
--   fields and interpretation lines among them. They cluttered the review
--   screen, and every one held its document out of "confirm all".
--
--   Dropping every row with no value was measured and rejected. It also
--   deleted 28 printed tests whose number we had failed to read - the holes a
--   reviewer most needs to see. On the same twelve reports the rule below
--   skips 126 of the 149 and loses no value; the 10 real rows it does skip are
--   smear lines no test in the master names ("Platelets on Smear").
--
-- WHAT
--   lab.fn_ingest_lab_document is replaced, unchanged except for two things.
--
--   1. A result with no value is skipped - not stored, and not logged to
--      lab.unmatched_labels, the list the master grows from - when
--      lab.fn_resolve_analyte places neither its label nor the label cut at
--      its first line break or bracket. The resolver that assigns codes
--      decides, so "Hemoglobin" is as known here as it is for coding, and
--      "COLOUR\n( Specimen: URINE. )" counts as the urine test it is. A line
--      break in a stored label is escaped - a backslash and an n - and is
--      treated as one. A row with a value is always stored, whatever it is
--      called.
--   2. A section left with no rows is not kept. The payload never carried an
--      empty section; now one can arise, and its heading would still name a
--      panel on the patient's timeline.
--
--   Documents already stored keep their rows until they are read again.
-- =============================================================================

-- Copied from 038, the current definition. The only changes are marked 039.
CREATE OR REPLACE FUNCTION lab.fn_ingest_lab_document(
    p_practice_id BIGINT,
    p_payload     JSONB,
    p_actor       BIGINT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
AS $$
DECLARE
    v_document_id  BIGINT;
    v_report_id    BIGINT;
    v_section_id   BIGINT;
    v_report       JSONB;
    v_section      JSONB;
    v_result       JSONB;
    v_note         JSONB;
    v_uhid         TEXT;
    v_patient_id   BIGINT;
    v_match_method VARCHAR(20);
    v_match_conf   NUMERIC(5,4);
    v_status       VARCHAR(20);
    v_panel_id     BIGINT;
    v_panel_method VARCHAR(20);
    v_panel_conf   NUMERIC(5,4);
    v_analyte_id   BIGINT;
    v_a_method     VARCHAR(20);
    v_a_conf       NUMERIC(5,4);
    v_collected    TIMESTAMP(6);
    v_seq          INTEGER;
    v_rseq         INTEGER := 0;
    v_value_text   TEXT;
    v_stripped     TEXT;
    v_numeric      NUMERIC(14,4);
    v_operator     VARCHAR(2);
    v_existing     BIGINT;
BEGIN
    IF p_practice_id IS NULL THEN
        RAISE EXCEPTION 'practice_id is required' USING ERRCODE = '22023';
    END IF;

    -- Same file twice is the same document. Return the original rather than
    -- creating a duplicate the reviewer then has to reconcile.
    IF p_payload ? 'checksum_sha256' THEN
        SELECT id INTO v_existing
        FROM   lab.documents
        WHERE  practice_id = p_practice_id
          AND  checksum_sha256 = p_payload->>'checksum_sha256'
          AND  is_deleted = FALSE;
        IF v_existing IS NOT NULL THEN
            RETURN v_existing;
        END IF;
    END IF;

    -- The UHID comes off the first report that carries one.
    SELECT r->>'uhid_printed'
    INTO   v_uhid
    FROM   jsonb_array_elements(COALESCE(p_payload->'reports', '[]'::JSONB)) r
    WHERE  NULLIF(r->>'uhid_printed', '') IS NOT NULL
    LIMIT  1;

    IF v_uhid IS NOT NULL THEN
        SELECT m.patient_id, m.match_method, m.confidence
        INTO   v_patient_id, v_match_method, v_match_conf
        FROM   lab.fn_match_patient_by_uhid(p_practice_id, v_uhid) m;
    END IF;

    -- Anything less than a certain match waits for a human.
    IF v_patient_id IS NOT NULL AND COALESCE(v_match_conf, 0) >= 0.95 THEN
        v_status := 'parsed';
    ELSE
        v_status := 'needs_review';
        IF v_patient_id IS NOT NULL THEN
            -- A fuzzy hit is a suggestion, not an attachment. Keep the guess in
            -- the audit trail but do not bind the document to the patient.
            v_patient_id := NULL;
        END IF;
        v_match_method := COALESCE(v_match_method, 'none');
    END IF;

    INSERT INTO lab.documents (
        practice_id, visit_attachment_id, visit_id, patient_id,
        detected_uhid, detected_uhid_label, detected_patient_name,
        patient_match_method, patient_match_confidence,
        status, source, page_count, has_text_layer, ocr_engine, engine_version,
        extraction_confidence, checksum_sha256, is_synthetic,
        parsed_at, created_by, created_at
    )
    VALUES (
        p_practice_id,
        NULLIF(p_payload->>'visit_attachment_id', '')::BIGINT,
        NULLIF(p_payload->>'visit_id', '')::BIGINT,
        v_patient_id,
        v_uhid,
        (SELECT r->>'uhid_label_printed'
         FROM jsonb_array_elements(COALESCE(p_payload->'reports','[]'::JSONB)) r LIMIT 1),
        (SELECT r->>'patient_name_printed'
         FROM jsonb_array_elements(COALESCE(p_payload->'reports','[]'::JSONB)) r LIMIT 1),
        v_match_method, v_match_conf,
        v_status,
        COALESCE(p_payload->>'source', 'emr_upload'),
        NULLIF(p_payload->>'page_count', '')::INTEGER,
        NULLIF(p_payload->>'has_text_layer', '')::BOOLEAN,
        p_payload->>'ocr_engine',
        p_payload->>'engine_version',
        NULLIF(p_payload->>'extraction_confidence', '')::NUMERIC,
        p_payload->>'checksum_sha256',
        COALESCE(NULLIF(p_payload->>'is_synthetic','')::BOOLEAN, FALSE),
        now(), p_actor, now()
    )
    RETURNING id INTO v_document_id;

    FOR v_report IN
        SELECT * FROM jsonb_array_elements(COALESCE(p_payload->'reports', '[]'::JSONB))
    LOOP
        v_rseq := v_rseq + 1;
        v_collected := NULLIF(v_report->>'collected_at', '')::TIMESTAMP(6);

        INSERT INTO lab.reports (
            document_id, practice_id, patient_id, lab_name, lab_address, lab_phone,
            accession_no, uhid_printed, uhid_label_printed, patient_name_printed,
            age_printed, sex_printed, collected_text, reported_text,
            collected_at, reported_at, referring_doctor, department, specimen,
            pathologist_name, pathologist_regn, layout_hint, header_hint,
            page_from, page_to, sequence, created_by, created_at
        )
        VALUES (
            v_document_id, p_practice_id, v_patient_id,
            v_report->>'lab_name', v_report->>'lab_address', v_report->>'lab_phone',
            v_report->>'accession_no', v_report->>'uhid_printed',
            v_report->>'uhid_label_printed', v_report->>'patient_name_printed',
            v_report->>'age_printed', NULLIF(v_report->>'sex_printed','')::CHAR(1),
            v_report->>'collected_text', v_report->>'reported_text',
            v_collected, NULLIF(v_report->>'reported_at','')::TIMESTAMP(6),
            v_report->>'referring_doctor', v_report->>'department',
            v_report->>'specimen', v_report->>'pathologist_name',
            v_report->>'pathologist_regn', v_report->>'layout_hint',
            v_report->>'header_hint',
            NULLIF(v_report->>'page_from','')::INTEGER,
            NULLIF(v_report->>'page_to','')::INTEGER,
            v_rseq, p_actor, now()
        )
        RETURNING id INTO v_report_id;

        v_seq := 0;
        FOR v_section IN
            SELECT * FROM jsonb_array_elements(COALESCE(v_report->'sections', '[]'::JSONB))
        LOOP
            v_seq := v_seq + 1;
            v_panel_id := NULL; v_panel_method := NULL; v_panel_conf := NULL;

            SELECT p.panel_id, p.match_method, p.confidence
            INTO   v_panel_id, v_panel_method, v_panel_conf
            FROM   lab.fn_resolve_panel(p_practice_id, v_section->>'heading_printed') p;

            INSERT INTO lab.report_sections (
                report_id, practice_id, heading_printed, panel_id,
                panel_match_method, panel_match_confidence, sequence,
                created_by, created_at
            )
            VALUES (
                v_report_id, p_practice_id, v_section->>'heading_printed',
                v_panel_id, COALESCE(v_panel_method, 'none'), v_panel_conf,
                v_seq, p_actor, now()
            )
            RETURNING id INTO v_section_id;

            FOR v_result IN
                SELECT * FROM jsonb_array_elements(COALESCE(v_section->'results', '[]'::JSONB))
            LOOP
                v_analyte_id := NULL; v_a_method := NULL; v_a_conf := NULL;

                SELECT x.analyte_id, x.match_method, x.confidence
                INTO   v_analyte_id, v_a_method, v_a_conf
                FROM   lab.fn_resolve_analyte(
                           p_practice_id, v_result->>'printed_label', v_panel_id) x;

                v_value_text := COALESCE(v_result->>'value_text', '');

                -- 039: no value, and a label no test resolves to, is not a result.
                -- Typically a banded range printed under the test above it
                -- ("Male : 86 - 152"). Skipped before it is stored or logged as an
                -- unmatched label. A known test with no value is kept: that is a
                -- number we failed to read, and the reviewer has to see the hole.
                IF btrim(v_value_text) = ''
                   AND v_analyte_id IS NULL
                   -- The name may carry a method or specimen line stuck to it,
                   -- "COLOUR\n( Specimen: URINE. )"; its first line still names it.
                   -- Line breaks arrive escaped, a backslash and an n, as
                   -- labels.py already expects; both forms end the first line.
                   AND NOT EXISTS (
                       SELECT 1
                       FROM   lab.fn_resolve_analyte(
                                  p_practice_id,
                                  btrim(split_part(split_part(
                                      replace(v_result->>'printed_label', '\n', E'\n'),
                                      E'\n', 1), '(', 1)),
                                  v_panel_id) y
                       WHERE  y.analyte_id IS NOT NULL)
                THEN
                    CONTINUE;
                END IF;

                -- Split a leading operator off so '<0.01' can still be charted
                -- without pretending the value is exactly 0.01. Commas go too:
                -- some labs print 2,68,000 for a platelet count.
                v_operator := NULLIF(substring(v_value_text FROM '^\s*(<=|>=|<|>)'), '');
                v_stripped := replace(
                                regexp_replace(v_value_text, '^\s*(<=|>=|<|>)\s*', ''),
                                ',', '');

                IF COALESCE((v_result->>'is_text_result')::BOOLEAN, FALSE)
                   OR v_stripped !~ '^-?[0-9]+(\.[0-9]+)?$' THEN
                    v_numeric := NULL;          -- text result, or not a number
                ELSE
                    v_numeric := v_stripped::NUMERIC;
                END IF;

                INSERT INTO lab.results (
                    section_id, report_id, document_id, practice_id, patient_id,
                    collected_at, printed_label, analyte_id, match_method,
                    match_confidence, value_text, value_numeric, value_operator,
                    unit_printed, reference_printed, flag, method_printed,
                    is_text_result, extraction_confidence, sequence,
                    page_number, created_by, created_at
                )
                VALUES (
                    v_section_id, v_report_id, v_document_id, p_practice_id,
                    v_patient_id, v_collected,
                    v_result->>'printed_label', v_analyte_id,
                    COALESCE(v_a_method, 'none'), v_a_conf,
                    v_value_text, v_numeric, v_operator,
                    v_result->>'unit_printed', v_result->>'reference_printed',
                    NULLIF(v_result->>'flag', ''), v_result->>'method_printed',
                    COALESCE((v_result->>'is_text_result')::BOOLEAN, FALSE),
                    NULLIF(v_result->>'extraction_confidence','')::NUMERIC,
                    COALESCE(NULLIF(v_result->>'sequence','')::INTEGER, 1),
                    -- 038: the page the reader saw the row on. Anything that is
                    -- not a plain positive number is not a page, so it is NULL.
                    CASE WHEN v_result->>'page' ~ '^[1-9][0-9]{0,3}$'
                         THEN (v_result->>'page')::SMALLINT END,
                    p_actor, now()
                );

                -- Nothing matched: record the gap so the master can grow.
                IF v_analyte_id IS NULL
                   AND NULLIF(v_result->>'printed_label','') IS NOT NULL THEN
                    INSERT INTO lab.unmatched_labels (
                        practice_id, printed_label, sample_unit, sample_value
                    )
                    VALUES (
                        p_practice_id, v_result->>'printed_label',
                        v_result->>'unit_printed', v_value_text
                    )
                    ON CONFLICT (label_normalised, COALESCE(practice_id, 0))
                    DO UPDATE SET occurrence_count = lab.unmatched_labels.occurrence_count + 1,
                                  last_seen_at     = now();
                END IF;
            END LOOP;

            -- 039: a section whose every line was skipped holds nothing.
            IF NOT EXISTS (SELECT 1 FROM lab.results WHERE section_id = v_section_id) THEN
                DELETE FROM lab.report_sections WHERE id = v_section_id;
            END IF;
        END LOOP;

        FOR v_note IN
            SELECT * FROM jsonb_array_elements(COALESCE(v_report->'notes', '[]'::JSONB))
        LOOP
            INSERT INTO lab.report_notes (
                report_id, practice_id, note_type, marker, note_text, created_by, created_at
            )
            VALUES (
                v_report_id, p_practice_id,
                COALESCE(v_note->>'note_type', 'remark'),
                v_note->>'marker', v_note->>'note_text', p_actor, now()
            );
        END LOOP;
    END LOOP;

    INSERT INTO lab.document_events (
        document_id, practice_id, event_type, from_status, to_status, detail, actor_user_id
    )
    VALUES (
        v_document_id, p_practice_id, 'ingested', 'received', v_status,
        jsonb_build_object('detected_uhid', v_uhid,
                           'match_method', v_match_method,
                           'match_confidence', v_match_conf),
        p_actor
    );

    RETURN v_document_id;
END;
$$;
