-- 018: confirming an automatic match must not erase how it was matched.
--
-- fn_review_lab_document set patient_match_method = 'manual' and confidence = 1.0 on
-- every verify. That is right when a human CHOSE the patient - they searched, they
-- picked, the machine had nothing to do with it.
--
-- It is wrong when a human merely CONFIRMS what the UHID already found. The document
-- keeps the same patient and the only new fact is that someone agreed. Overwriting the
-- method there throws away the answer to a question worth asking later: how many
-- documents did the UHID match on its own, and how often was it right? After a bulk
-- confirm, every document in the practice would claim to have been matched by hand.
--
-- So the method and confidence change only when the patient actually changes.
-- reviewed_by and reviewed_at always change, because a person always did something.
--
-- Also: verifying with a NULL patient now means "confirm the one already on the
-- document" instead of raising. Asking a caller to repeat a value the row already
-- holds is an invitation to send a different one by accident.
--
-- Everything else is 003's function unchanged - the results update still backfills
-- collected_at from the report and marks the rows reviewed, and the audit row still
-- carries its detail as JSONB.

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
    v_from    VARCHAR(20);
    v_to      VARCHAR(20);
    v_current BIGINT;
    v_target  BIGINT;
    v_changed BOOLEAN := FALSE;
BEGIN
    IF p_decision NOT IN ('verify', 'reject') THEN
        RAISE EXCEPTION 'decision must be verify or reject' USING ERRCODE = '22023';
    END IF;

    SELECT status, patient_id INTO v_from, v_current
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
        -- Confirming needs no patient argument: the answer is already on the document.
        v_target := COALESCE(p_patient_id, v_current);

        IF v_target IS NULL THEN
            RAISE EXCEPTION 'a patient is required to verify a document'
                USING ERRCODE = '22023';
        END IF;

        -- The patient must belong to this practice. Never trust the id alone.
        PERFORM 1 FROM core.patients
         WHERE id = v_target AND practice_id = p_practice_id AND is_deleted = FALSE;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'patient % not found in practice %', v_target, p_practice_id
                USING ERRCODE = 'P0002';
        END IF;

        v_changed := v_current IS DISTINCT FROM v_target;
        v_to := 'verified';

        UPDATE lab.documents
           SET patient_id = v_target, status = v_to,
               -- Only a change of patient is a manual match. A confirmation keeps the
               -- method that found them, so "how did this document reach this patient"
               -- still has a truthful answer afterwards.
               patient_match_method =
                   CASE WHEN v_changed THEN 'manual' ELSE patient_match_method END,
               patient_match_confidence =
                   CASE WHEN v_changed THEN 1.0000 ELSE patient_match_confidence END,
               reviewed_by = p_actor, reviewed_at = now(),
               updated_by = p_actor, updated_at = now()
         WHERE id = p_document_id AND practice_id = p_practice_id;

        UPDATE lab.reports
           SET patient_id = v_target, updated_by = p_actor, updated_at = now()
         WHERE document_id = p_document_id AND practice_id = p_practice_id;

        UPDATE lab.results r
           SET patient_id  = v_target,
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
        jsonb_build_object('patient_id', COALESCE(v_target, v_current),
                           'note', p_note,
                           'patient_changed', v_changed),
        p_actor
    );

    RETURN v_to;
END;
$$;

COMMENT ON FUNCTION lab.fn_review_lab_document IS
  'Verify or reject a document. Verifying with no patient confirms the one already on '
  'the document and keeps the method that found them; passing a different patient is a '
  'manual match and is recorded as one.';
