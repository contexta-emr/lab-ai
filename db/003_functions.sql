-- =============================================================================
-- Contexta - Lab extraction store
-- 003  Functions: resolve, match, ingest, review, trend
-- =============================================================================
-- Run after 002.
--
-- FUNCTIONS-FIRST (CLAUDE.md section 8)
--   The API calls these. It does not write lab.* directly and it does not build
--   SQL. Every function takes p_practice_id explicitly and filters on it - the
--   caller passes req.user.practiceId, never anything from the client body.
--
--   SECURITY INVOKER throughout: these run as the calling role, so a role with
--   no rights to lab.* cannot borrow any through a function.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- lab.fn_resolve_analyte - printed label -> canonical analyte
-- -----------------------------------------------------------------------------
-- Three passes, best first, and it stops at the first that hits:
--   1. exact_alias       the spelling is in the master verbatim
--   2. normalised_alias  same once punctuation and case are stripped
--   3. fuzzy_alias       trigram similarity above p_min_similarity
-- No hit returns no rows. That is deliberate: the caller writes NULL, and a
-- blank code on a test we do not know is worth more than a confident wrong one.
--
-- p_panel_id, when given, prefers an analyte in that panel. "Glucose" under a
-- urine heading is UR_GLU; under a diabetes heading it is GLU_F.
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
    WHERE  al.is_deleted = FALSE
      AND  al.is_active  = TRUE
      AND  al.alias = p_label
      AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
    ORDER  BY al.practice_id NULLS LAST,
              (a.panel_id IS NOT DISTINCT FROM p_panel_id) DESC
    LIMIT  1;
    IF FOUND THEN RETURN; END IF;

    -- 2. same label once punctuation and case stop mattering
    RETURN QUERY
    SELECT a.id, a.code, 'normalised_alias'::VARCHAR(20),
           LEAST(al.confidence, 0.9800)::NUMERIC(5,4)
    FROM   lab.analyte_aliases al
    JOIN   lab.analytes a ON a.id = al.analyte_id AND a.is_deleted = FALSE
    WHERE  al.is_deleted = FALSE
      AND  al.is_active  = TRUE
      AND  al.alias_normalised = v_norm
      AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
    ORDER  BY al.practice_id NULLS LAST,
              (a.panel_id IS NOT DISTINCT FROM p_panel_id) DESC
    LIMIT  1;
    IF FOUND THEN RETURN; END IF;

    -- 3. close enough, and say how close
    RETURN QUERY
    SELECT a.id, a.code, 'fuzzy_alias'::VARCHAR(20),
           ROUND(similarity(al.alias_normalised, v_norm)::NUMERIC, 4)
    FROM   lab.analyte_aliases al
    JOIN   lab.analytes a ON a.id = al.analyte_id AND a.is_deleted = FALSE
    WHERE  al.is_deleted = FALSE
      AND  al.is_active  = TRUE
      AND  (al.practice_id IS NULL OR al.practice_id = p_practice_id)
      AND  similarity(al.alias_normalised, v_norm) >= p_min_similarity
    ORDER  BY (a.panel_id IS NOT DISTINCT FROM p_panel_id) DESC,
              similarity(al.alias_normalised, v_norm) DESC
    LIMIT  1;
END;
$$;

COMMENT ON FUNCTION lab.fn_resolve_analyte IS
  'Printed label to canonical analyte. Returns no rows when nothing matches - '
  'the caller must store NULL rather than guess.';


-- -----------------------------------------------------------------------------
-- lab.fn_resolve_panel - printed section heading -> canonical panel
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION lab.fn_resolve_panel(
    p_practice_id    BIGINT,
    p_heading        TEXT,
    p_min_similarity REAL DEFAULT 0.66
)
RETURNS TABLE (
    panel_id     BIGINT,
    panel_code   VARCHAR(40),
    match_method VARCHAR(20),
    confidence   NUMERIC(5,4)
)
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
AS $$
DECLARE
    v_norm TEXT := lab.fn_normalise_label(p_heading);
BEGIN
    IF v_norm = '' THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT p.id, p.code, 'title_alias'::VARCHAR(20), 1.0000::NUMERIC(5,4)
    FROM   lab.panel_aliases pa
    JOIN   lab.panels p ON p.id = pa.panel_id AND p.is_deleted = FALSE
    WHERE  pa.is_deleted = FALSE
      AND  pa.is_active  = TRUE
      AND  pa.alias_normalised = v_norm
      AND  (pa.practice_id IS NULL OR pa.practice_id = p_practice_id)
    ORDER  BY pa.practice_id NULLS LAST
    LIMIT  1;
    IF FOUND THEN RETURN; END IF;

    RETURN QUERY
    SELECT p.id, p.code, 'title_fuzzy'::VARCHAR(20),
           ROUND(similarity(pa.alias_normalised, v_norm)::NUMERIC, 4)
    FROM   lab.panel_aliases pa
    JOIN   lab.panels p ON p.id = pa.panel_id AND p.is_deleted = FALSE
    WHERE  pa.is_deleted = FALSE
      AND  pa.is_active  = TRUE
      AND  (pa.practice_id IS NULL OR pa.practice_id = p_practice_id)
      AND  similarity(pa.alias_normalised, v_norm) >= p_min_similarity
    ORDER  BY similarity(pa.alias_normalised, v_norm) DESC
    LIMIT  1;
END;
$$;


-- -----------------------------------------------------------------------------
-- lab.fn_match_patient_by_uhid - the auto-detect step
-- -----------------------------------------------------------------------------
-- Labs label the same number UHID, MRN, Patient ID, Reg. No or Hospital No, and
-- OCR mangles punctuation. So: exact, then punctuation-insensitive, then close.
-- Fuzzy matches deliberately come back with a confidence below 1 so the caller
-- can quarantine them rather than attach on a maybe.
CREATE OR REPLACE FUNCTION lab.fn_match_patient_by_uhid(
    p_practice_id    BIGINT,
    p_uhid           TEXT,
    p_min_similarity REAL DEFAULT 0.80
)
RETURNS TABLE (
    patient_id   BIGINT,
    matched_uhid VARCHAR(20),
    match_method VARCHAR(20),
    confidence   NUMERIC(5,4)
)
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
AS $$
DECLARE
    v_norm TEXT := lab.fn_normalise_label(p_uhid);
BEGIN
    IF v_norm = '' THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT pt.id, pt.uhid, 'uhid_exact'::VARCHAR(20), 1.0000::NUMERIC(5,4)
    FROM   core.patients pt
    WHERE  pt.practice_id = p_practice_id
      AND  pt.is_deleted = FALSE
      AND  pt.uhid = p_uhid
    LIMIT  1;
    IF FOUND THEN RETURN; END IF;

    RETURN QUERY
    SELECT pt.id, pt.uhid, 'uhid_normalised'::VARCHAR(20), 0.9500::NUMERIC(5,4)
    FROM   core.patients pt
    WHERE  pt.practice_id = p_practice_id
      AND  pt.is_deleted = FALSE
      AND  lab.fn_normalise_label(pt.uhid) = v_norm
    LIMIT  1;
    IF FOUND THEN RETURN; END IF;

    -- OCR read SRV/2O7431 for SRV/207431. Close, but not close enough to trust
    -- without a human, which is what the confidence is telling the caller.
    RETURN QUERY
    SELECT pt.id, pt.uhid, 'uhid_fuzzy'::VARCHAR(20),
           ROUND(similarity(lab.fn_normalise_label(pt.uhid), v_norm)::NUMERIC, 4)
    FROM   core.patients pt
    WHERE  pt.practice_id = p_practice_id
      AND  pt.is_deleted = FALSE
      AND  similarity(lab.fn_normalise_label(pt.uhid), v_norm) >= p_min_similarity
    ORDER  BY similarity(lab.fn_normalise_label(pt.uhid), v_norm) DESC
    LIMIT  1;
END;
$$;

COMMENT ON FUNCTION lab.fn_match_patient_by_uhid IS
  'Auto-detect the patient from the UHID printed on the document. A fuzzy hit '
  'returns confidence below 1 so the caller quarantines instead of attaching.';


-- -----------------------------------------------------------------------------
-- lab.fn_ingest_lab_document - the write path
-- -----------------------------------------------------------------------------
-- Takes the extractor's JSON for one file and writes the whole tree in one
-- transaction: document, reports, sections, results, notes. Resolves each
-- printed label to an analyte and each heading to a panel on the way in, and
-- records what it could not resolve in lab.unmatched_labels.
--
-- Returns the document id. Status on exit:
--   'parsed'       a patient was matched with full confidence
--   'needs_review' no patient, or matched only fuzzily - the quarantine state
--
-- Payload shape (see README for a worked example):
-- {
--   "source": "emr_upload", "visit_attachment_id": 123, "checksum_sha256": "..",
--   "page_count": 1, "has_text_layer": true, "ocr_engine": "paddle_vl",
--   "engine_version": "0.9.1", "extraction_confidence": 0.94,
--   "is_synthetic": false,
--   "reports": [{
--      "lab_name": "..", "accession_no": "..", "uhid_printed": "SRV/207431",
--      "uhid_label_printed": "UHID", "patient_name_printed": "..",
--      "age_printed": "52", "sex_printed": "M",
--      "collected_text": "05/10/2021 8:40 AM", "collected_at": "2021-10-05T08:40:00",
--      "reported_at": "2021-10-05T18:20:00", "referring_doctor": "..",
--      "department": "..", "specimen": "..", "layout_hint": "clean_table",
--      "sections": [{
--         "heading_printed": "Diabetes Profile",
--         "results": [{"printed_label": "Glucose, Fasting", "value_text": "214",
--                      "unit_printed": "mg/dL", "reference_printed": "70 - 100",
--                      "flag": "H", "method_printed": null,
--                      "is_text_result": false, "extraction_confidence": 0.97}]
--      }],
--      "notes": [{"note_type": "interpretation", "note_text": "..", "marker": null}]
--   }]
-- }
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
                    created_by, created_at
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


-- -----------------------------------------------------------------------------
-- lab.fn_review_lab_document - a human settles the match
-- -----------------------------------------------------------------------------
-- Confirms or corrects the patient and moves the document to verified, or
-- rejects it. Cascades patient_id and collected_at down to reports and results
-- so the trend index is populated in the same transaction.
CREATE OR REPLACE FUNCTION lab.fn_review_lab_document(
    p_practice_id BIGINT,
    p_document_id BIGINT,
    p_patient_id  BIGINT,
    p_actor       BIGINT,
    p_decision    VARCHAR(10) DEFAULT 'verify',
    p_note        TEXT        DEFAULT NULL
)
RETURNS VARCHAR(20)
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
AS $$
DECLARE
    v_from   VARCHAR(20);
    v_to     VARCHAR(20);
BEGIN
    IF p_decision NOT IN ('verify', 'reject') THEN
        RAISE EXCEPTION 'decision must be verify or reject' USING ERRCODE = '22023';
    END IF;

    SELECT status INTO v_from
    FROM   lab.documents
    WHERE  id = p_document_id
      AND  practice_id = p_practice_id      -- tenant scope, always
      AND  is_deleted = FALSE
    FOR UPDATE;

    IF v_from IS NULL THEN
        RAISE EXCEPTION 'document % not found in practice %', p_document_id, p_practice_id
            USING ERRCODE = 'P0002';
    END IF;

    IF p_decision = 'reject' THEN
        v_to := 'rejected';
        UPDATE lab.documents
           SET status = v_to, reviewed_by = p_actor, reviewed_at = now(),
               updated_by = p_actor, updated_at = now()
         WHERE id = p_document_id AND practice_id = p_practice_id;
    ELSE
        IF p_patient_id IS NULL THEN
            RAISE EXCEPTION 'a patient is required to verify a document'
                USING ERRCODE = '22023';
        END IF;
        -- The patient must belong to this practice. Never trust the id alone.
        PERFORM 1 FROM core.patients
         WHERE id = p_patient_id AND practice_id = p_practice_id AND is_deleted = FALSE;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'patient % not found in practice %', p_patient_id, p_practice_id
                USING ERRCODE = 'P0002';
        END IF;

        v_to := 'verified';
        UPDATE lab.documents
           SET patient_id = p_patient_id, status = v_to,
               patient_match_method = 'manual', patient_match_confidence = 1.0000,
               reviewed_by = p_actor, reviewed_at = now(),
               updated_by = p_actor, updated_at = now()
         WHERE id = p_document_id AND practice_id = p_practice_id;

        UPDATE lab.reports
           SET patient_id = p_patient_id, updated_by = p_actor, updated_at = now()
         WHERE document_id = p_document_id AND practice_id = p_practice_id;

        UPDATE lab.results r
           SET patient_id  = p_patient_id,
               collected_at = COALESCE(r.collected_at, rep.collected_at),
               is_reviewed = TRUE, reviewed_by = p_actor, reviewed_at = now(),
               updated_by = p_actor, updated_at = now()
          FROM lab.reports rep
         WHERE r.report_id = rep.id
           AND r.document_id = p_document_id
           AND r.practice_id = p_practice_id;
    END IF;

    INSERT INTO lab.document_events (
        document_id, practice_id, event_type, from_status, to_status, detail, actor_user_id
    )
    VALUES (
        p_document_id, p_practice_id, 'reviewed', v_from, v_to,
        jsonb_build_object('patient_id', p_patient_id, 'note', p_note), p_actor
    );

    RETURN v_to;
END;
$$;


-- -----------------------------------------------------------------------------
-- lab.fn_get_analyte_trend - the read path the chat panel uses
-- -----------------------------------------------------------------------------
-- Complete and in date order, from verified documents only. Completeness is the
-- whole point: a trend that silently drops a point is worse than no trend.
CREATE OR REPLACE FUNCTION lab.fn_get_analyte_trend(
    p_practice_id  BIGINT,
    p_patient_id   BIGINT,
    p_analyte_code VARCHAR(40),
    p_from         DATE DEFAULT NULL,
    p_to           DATE DEFAULT NULL
)
RETURNS TABLE (
    collected_at      TIMESTAMP(6),
    value_numeric     NUMERIC(14,4),
    value_text        VARCHAR(255),
    value_operator    VARCHAR(2),
    unit              VARCHAR(40),
    reference_printed VARCHAR(160),
    ref_low           NUMERIC(14,4),
    ref_high          NUMERIC(14,4),
    flag              VARCHAR(4),
    lab_name          VARCHAR(255),
    printed_label     VARCHAR(255),
    result_id         BIGINT,
    document_id       BIGINT
)
LANGUAGE sql
STABLE
SECURITY INVOKER
AS $$
    SELECT r.collected_at,
           r.value_numeric,
           r.value_text,
           r.value_operator,
           COALESCE(r.unit_canonical, r.unit_printed),
           r.reference_printed,
           r.ref_low,
           r.ref_high,
           r.flag,
           rep.lab_name,
           r.printed_label,
           r.id,
           r.document_id
    FROM   lab.results   r
    JOIN   lab.documents d   ON d.id = r.document_id
    JOIN   lab.reports   rep ON rep.id = r.report_id
    JOIN   lab.analytes  a   ON a.id = r.analyte_id
    WHERE  r.practice_id = p_practice_id
      AND  r.patient_id  = p_patient_id
      AND  a.code        = p_analyte_code
      AND  r.is_deleted  = FALSE
      AND  d.is_deleted  = FALSE
      AND  d.status      = 'verified'
      AND  (p_from IS NULL OR r.collected_at >= p_from::TIMESTAMP)
      AND  (p_to   IS NULL OR r.collected_at <  (p_to + 1)::TIMESTAMP)
    ORDER  BY r.collected_at;
$$;

COMMENT ON FUNCTION lab.fn_get_analyte_trend IS
  'Every verified point for one analyte on one patient, in date order. Reads '
  'verified documents only.';
