-- Put failed documents back on the queue.
--
-- Not a migration - an operational one-off you run when a document failed for
-- a reason that has since been fixed in code. It does not re-upload anything;
-- the PDF is already stored and the worker picks the document up again on its
-- next poll. One fresh OpenParser call each.
--
--   docker compose exec -T db psql -U labidp -d labidp < scripts/requeue_failed.sql
--
-- Fed on stdin rather than with -f: Git Bash rewrites a /work/... argument
-- into a Windows path before docker ever sees it, and scripts/ is not
-- mounted into the db container anyway.
--
-- Safe to run while a corpus run is in progress. It touches only rows sitting
-- in 'failed', never one the worker currently holds.

BEGIN;

SELECT count(*) AS about_to_requeue
FROM   lab.documents
WHERE  status = 'failed' AND is_deleted = FALSE;

UPDATE lab.documents
SET    status       = 'received',
       ocr_attempts = 0,          -- fn_claim_document skips anything at the cap
       ocr_error    = NULL,
       claimed_at   = NULL,
       updated_at   = now()
WHERE  status = 'failed' AND is_deleted = FALSE;

COMMIT;

SELECT status, count(*)
FROM   lab.documents
WHERE  is_deleted = FALSE
GROUP  BY status
ORDER  BY 2 DESC;
