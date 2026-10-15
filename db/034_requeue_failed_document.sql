-- =============================================================================
-- Contexta - Lab extraction store
-- 034  A failed document goes back in line when its file is uploaded again
-- =============================================================================
-- Run after 033.
--
-- WHY
--   An upload whose bytes are already held returns the document that holds
--   them. When that document had FAILED, it returned the failure, so a report
--   that failed once could never be read again - however the cause was later
--   fixed. On Vercel there is no worker and no other way back.
--
--   Seen on 2026-10-15: Ashwini_reports_redact.pdf was refused by
--   reports_sex_check, three reads, then 'failed'. After the fix, dropping
--   the same file again handed back the same failure.
--
-- WHAT
--   lab.fn_requeue_document puts a FAILED document back to 'received' with
--   its attempts reset, and records the event. It touches nothing else: a
--   document in any other state is left exactly as it is, so dropping a file
--   that was read, or is being read, changes nothing.
-- =============================================================================

CREATE OR REPLACE FUNCTION lab.fn_requeue_document(
    p_practice_id  BIGINT,
    p_document_id  BIGINT,
    p_user_id      BIGINT
)
RETURNS VARCHAR(20)
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
AS $$
DECLARE
    v_status VARCHAR(20);
BEGIN
    UPDATE lab.documents
    SET    status = 'received',
           ocr_attempts = 0,
           ocr_error = NULL,
           claimed_at = NULL,
           updated_at = now(),
           updated_by = p_user_id
    WHERE  id = p_document_id AND practice_id = p_practice_id
      AND  status = 'failed'
    RETURNING status INTO v_status;

    IF NOT FOUND THEN
        SELECT status INTO v_status
        FROM   lab.documents
        WHERE  id = p_document_id AND practice_id = p_practice_id;
        RETURN v_status;
    END IF;

    INSERT INTO lab.document_events (document_id, practice_id, event_type, detail)
    VALUES (p_document_id, p_practice_id, 'requeued',
            jsonb_build_object('by', p_user_id, 'reason', 'uploaded again'));
    RETURN v_status;
END;
$$;

COMMENT ON FUNCTION lab.fn_requeue_document IS
  'Put a FAILED document back to received, attempts reset, because its file was '
  'uploaded again. Any other state is left as it is. Returns the status after.';
