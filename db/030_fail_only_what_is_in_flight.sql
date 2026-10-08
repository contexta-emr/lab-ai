-- =============================================================================
-- Contexta - Lab extraction store
-- 030  A failure may only fail a document that is still being read
-- =============================================================================
-- Run after 029. Review item B5 in docs/review-2026-10-08.md.
--
-- WHAT WENT WRONG
--   fn_complete_document locks the row and refuses anything not 'received' or
--   'parsing'. fn_fail_document, from 011, had no such guard: it set 'received'
--   or 'failed' whatever the document's state. Two ways that reverted a document
--   that had been read successfully:
--
--   1. The stale-claim race. A worker slower than fn_claim_document's 15-minute
--      window loses its claim; a second worker reads and completes the document;
--      the first finally returns, fn_complete_document rightly refuses it, and
--      its error path calls fn_fail_document - which reverted the winner's work.
--
--   2. Any exception after the commit. ocr_worker.py committed the completion
--      and then ran a SELECT and a print inside the same try, so a database
--      hiccup there failed the document it had just completed.
--
--   Proven before this migration, in a rolled-back transaction: document 6569,
--   'parsed' with 12 results, became 'received' with its results still attached.
--   Re-queued, it would be read again - another OCR charge - and gain a second
--   report on top of the first.
--
-- NOW
--   The update applies only to a document still in flight. A late failure for
--   one already completed, reviewed or rejected changes nothing, and is recorded
--   as 'ocr_failure_ignored' so the race stays visible in the audit trail rather
--   than disappearing. The signature and return type are unchanged; callers get
--   the document's actual status back either way.
-- =============================================================================

CREATE OR REPLACE FUNCTION lab.fn_fail_document(
    p_practice_id  BIGINT,
    p_document_id  BIGINT,
    p_error        TEXT,
    p_max_attempts SMALLINT DEFAULT 3
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
    SET    status = CASE WHEN ocr_attempts >= p_max_attempts
                         THEN 'failed' ELSE 'received' END,
           ocr_error = left(coalesce(p_error, ''), 500),
           claimed_at = NULL,
           updated_at = now()
    WHERE  id = p_document_id AND practice_id = p_practice_id
      AND  status IN ('received', 'parsing')
    RETURNING status INTO v_status;

    IF NOT FOUND THEN
        -- Not in flight: completed, reviewed or rejected by someone else first.
        -- Leave it exactly as it is, and say that a late failure arrived.
        SELECT status INTO v_status
        FROM   lab.documents
        WHERE  id = p_document_id AND practice_id = p_practice_id;

        INSERT INTO lab.document_events (document_id, practice_id, event_type, detail)
        SELECT p_document_id, p_practice_id, 'ocr_failure_ignored',
               jsonb_build_object('error', left(coalesce(p_error, ''), 500),
                                  'status', v_status)
        WHERE  v_status IS NOT NULL;

        RETURN v_status;
    END IF;

    INSERT INTO lab.document_events (document_id, practice_id, event_type, detail)
    SELECT p_document_id, p_practice_id, 'ocr_failed',
           jsonb_build_object('error', left(coalesce(p_error, ''), 500),
                              'status', v_status);
    RETURN v_status;
END;
$$;

COMMENT ON FUNCTION lab.fn_fail_document IS
  'Record a failed OCR attempt on a document still being read: back to received '
  'while attempts remain, then failed. A late failure for a document already '
  'completed, reviewed or rejected changes nothing and is logged as '
  'ocr_failure_ignored - see migration 030.';
