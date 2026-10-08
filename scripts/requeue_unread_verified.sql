-- =============================================================================
-- Send bulk-verified documents with no value read back to the review queue
-- Review B2, docs/review-2026-10-08.md. Approved by Karthik, 2026-10-08.
-- =============================================================================
-- WHY
--   Bulk confirm used to verify every document whose UHID matched a patient,
--   whatever had been read from it. 35 were verified with no value on any row -
--   17 with nothing stored at all - every one through the bulk button, none by
--   a person who opened it. 'verified' is the one state the trend and every
--   clinical read trust, so those documents claimed a check nobody made.
--
-- WHAT IT DOES
--   Each goes back to 'parsed' - still matched to its patient, waiting for a
--   person - and exactly what verifying did is undone: the reviewer and review
--   time come off the document and its rows, and the rows stop being marked
--   reviewed. The patient match, the rows and their values are untouched. One
--   'requeued' event per document records why, and whose verification was
--   withdrawn.
--
-- ONLY BULK CONFIRMATIONS
--   A document a person verified on its own is left alone, whatever was read
--   from it: that was a decision. This withdraws only verifications nobody
--   made - the latest 'reviewed' event carries the bulk path's own note.
--
-- SAFE TO RE-RUN
--   A second run finds nothing: what it moved is no longer verified. Confirm
--   all will not re-verify them either - it now holds back any document with
--   nothing read or a value missing.
--
--   docker compose exec -T db psql -U labidp -d labidp -v ON_ERROR_STOP=1 \
--       < scripts/requeue_unread_verified.sql
-- =============================================================================

BEGIN;

WITH target AS (
    SELECT d.id, d.practice_id, d.reviewed_by, d.reviewed_at
    FROM   lab.documents d
    WHERE  d.status = 'verified'
      AND  d.is_deleted = FALSE
      AND  NOT EXISTS (
               SELECT 1 FROM lab.results r
               WHERE  r.document_id = d.id
                 AND  r.is_deleted = FALSE
                 AND  btrim(coalesce(r.value_text, '')) <> '')
      AND  (SELECT e.detail ->> 'note'
            FROM   lab.document_events e
            WHERE  e.document_id = d.id
              AND  e.event_type = 'reviewed' AND e.to_status = 'verified'
            ORDER  BY e.created_at DESC, e.id DESC
            LIMIT  1) = 'confirmed in bulk from the queue'
),
documents AS (
    UPDATE lab.documents d
    SET    status = 'parsed',
           reviewed_by = NULL, reviewed_at = NULL,
           -- No application user made this change; the event below says who did.
           updated_by = NULL, updated_at = now()
    FROM   target t
    WHERE  d.id = t.id AND d.practice_id = t.practice_id
      AND  d.status = 'verified'
    RETURNING d.id, d.practice_id, t.reviewed_by, t.reviewed_at
),
results AS (
    -- Every row, deleted or not: verifying marked every row.
    UPDATE lab.results r
    SET    is_reviewed = FALSE, reviewed_by = NULL, reviewed_at = NULL,
           updated_by = NULL, updated_at = now()
    FROM   documents d
    WHERE  r.document_id = d.id AND r.practice_id = d.practice_id
    RETURNING r.document_id
)
INSERT INTO lab.document_events
       (document_id, practice_id, event_type, from_status, to_status, detail)
SELECT d.id, d.practice_id, 'requeued', 'verified', 'parsed',
       jsonb_build_object(
           'review', 'B2',
           'reason', 'verified in bulk with no value read',
           'approved_by', 'Karthik, 2026-10-08 - a data fix, not an application user',
           'withdrawn_verification_by', d.reviewed_by,
           'withdrawn_verification_at', d.reviewed_at,
           'rows_unmarked', (SELECT count(*) FROM results x WHERE x.document_id = d.id))
FROM   documents d;

COMMIT;
