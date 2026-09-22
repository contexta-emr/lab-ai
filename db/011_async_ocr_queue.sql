-- =============================================================================
-- Contexta - Lab extraction store
-- 011  The OCR queue: claim a document, attach what the engine read
-- =============================================================================
-- Run after 010.
--
-- WHY UPLOAD BECAME ASYNCHRONOUS
--   OpenParser is the only engine now, and it is hosted. Measured over the
--   full 239-document corpus run: 38.9 seconds a document sustained (the first
--   few are ~6s; it throttles hard), 4 connection errors and 1 hard timeout in
--   239 requests. A synchronous upload would block a doctor's browser for the
--   best part of a minute and fail outright about 2% of the time.
--
--   So POST /documents now stores the file, writes a document in 'received',
--   and returns immediately. A worker claims it, calls the engine, and attaches
--   the result. The two states were already in the status CHECK from 002 -
--   'received' and 'parsing' - because this was always the intended shape.
--
-- WHY THE DATABASE IS THE QUEUE
--   No Redis, no Celery, no broker. The work is "documents in state
--   'received'", that set already exists and is already durable, and a lab
--   sees tens of uploads a day rather than thousands a second. Adding a broker
--   would add a second thing that can be down, to move rows between states
--   Postgres is already tracking.
--
--   fn_claim_document uses FOR UPDATE SKIP LOCKED, which is how you do this
--   safely: two workers running at once cannot take the same document, and
--   neither waits for the other.
-- =============================================================================


-- ----------------------------------------------------------------------------
-- 1. Why a document failed, and how many times we have tried
-- ----------------------------------------------------------------------------
ALTER TABLE lab.documents
    ADD COLUMN IF NOT EXISTS ocr_attempts  SMALLINT     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS ocr_error     VARCHAR(500),
    ADD COLUMN IF NOT EXISTS claimed_at    TIMESTAMP(6);

COMMENT ON COLUMN lab.documents.ocr_attempts IS
  'How many times an engine has been asked to read this. The queue stops at a '
  'limit so one poisonous document cannot be retried until the bill notices.';
COMMENT ON COLUMN lab.documents.ocr_error IS
  'Why the last attempt failed, verbatim. A reviewer looking at a stuck '
  'document needs to know whether it was the network or the file.';
COMMENT ON COLUMN lab.documents.claimed_at IS
  'When a worker took this document. A claim older than the requeue window is '
  'assumed dead - a worker that is killed mid-call must not strand a document.';

-- The queue read, which is the hottest query the worker makes.
CREATE INDEX IF NOT EXISTS documents_ocr_queue_idx
    ON lab.documents (practice_id, received_at)
    WHERE is_deleted = FALSE AND status IN ('received', 'parsing');


-- ----------------------------------------------------------------------------
-- 2. lab.fn_claim_document - take the next document to read
-- ----------------------------------------------------------------------------
-- Returns one document and moves it to 'parsing', or no rows when the queue is
-- empty. SKIP LOCKED means several workers can run without coordinating.
--
-- A document in 'parsing' whose claim is older than p_stale_minutes is taken
-- again: a worker killed mid-call would otherwise strand it there forever, and
-- a document nobody will ever look at again is worse than one read twice.
CREATE OR REPLACE FUNCTION lab.fn_claim_document(
    p_practice_id   BIGINT,
    p_max_attempts  SMALLINT DEFAULT 3,
    p_stale_minutes INT      DEFAULT 15
)
RETURNS TABLE (
    document_id          BIGINT,
    visit_attachment_id  BIGINT,
    checksum_sha256      CHAR(64),
    stored_path          VARCHAR(1000),
    attempts             SMALLINT
)
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
AS $$
DECLARE
    v_id BIGINT;
BEGIN
    SELECT d.id INTO v_id
    FROM   lab.documents d
    WHERE  d.practice_id = p_practice_id
      AND  d.is_deleted = FALSE
      AND  d.ocr_attempts < p_max_attempts
      AND  (d.status = 'received'
            OR (d.status = 'parsing'
                AND d.claimed_at < now() - make_interval(mins => p_stale_minutes)))
    ORDER  BY d.received_at
    FOR    UPDATE SKIP LOCKED
    LIMIT  1;

    IF v_id IS NULL THEN
        RETURN;
    END IF;

    UPDATE lab.documents
    SET    status = 'parsing',
           claimed_at = now(),
           ocr_attempts = ocr_attempts + 1,
           updated_at = now()
    WHERE  id = v_id;

    RETURN QUERY
    SELECT d.id, d.visit_attachment_id, d.checksum_sha256,
           va.azure_blob_path, d.ocr_attempts
    FROM   lab.documents d
    LEFT   JOIN core.visit_attachments va ON va.id = d.visit_attachment_id
    WHERE  d.id = v_id;
END;
$$;

COMMENT ON FUNCTION lab.fn_claim_document IS
  'Take the next document needing OCR and mark it parsing. FOR UPDATE SKIP '
  'LOCKED, so workers do not collide. Re-claims a stale parsing document, '
  'because a killed worker must not strand one there forever.';


-- ----------------------------------------------------------------------------
-- 3. lab.fn_fail_document - record why an attempt failed
-- ----------------------------------------------------------------------------
-- Back to 'received' while attempts remain, so the next pass retries it.
-- Out of attempts, it goes to 'failed' and stops costing money - and a human
-- can see it in the console with the reason still attached.
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
    RETURNING status INTO v_status;

    INSERT INTO lab.document_events (document_id, practice_id, event_type, detail)
    SELECT p_document_id, p_practice_id, 'ocr_failed',
           jsonb_build_object('error', left(coalesce(p_error, ''), 500),
                              'status', v_status);
    RETURN v_status;
END;
$$;

COMMENT ON FUNCTION lab.fn_fail_document IS
  'Record a failed OCR attempt. Back to received while attempts remain, then '
  'failed. The reason is kept so a stuck document can be explained.';


-- ----------------------------------------------------------------------------
-- 4. lab.fn_complete_document - attach what the engine read
-- ----------------------------------------------------------------------------
-- The placeholder written at upload time is replaced by the real document.
--
-- Replaced rather than updated in place, because fn_ingest_lab_document is the
-- one function that turns a payload into a document tree - it resolves every
-- label to an analyte, every heading to a panel, matches the patient by UHID
-- and decides the status. Reimplementing any part of that here would be a
-- second write path, and the whole schema exists to have exactly one.
--
-- The placeholder carries no reports, sections or results: it was created
-- empty. So there is nothing to migrate but the attachment link, which is
-- passed through in the payload, and the one 'ingested' event, which is not
-- worth keeping - the new document logs its own.
--
-- Unique on (practice_id, checksum) means the placeholder must go before the
-- real one lands, and both happen inside this function so no window exists
-- where the document is missing.
CREATE OR REPLACE FUNCTION lab.fn_complete_document(
    p_practice_id BIGINT,
    p_document_id BIGINT,
    p_payload     JSONB,
    p_actor       BIGINT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
AS $$
DECLARE
    v_attachment BIGINT;
    v_new_id     BIGINT;
    v_payload    JSONB := p_payload;
BEGIN
    SELECT visit_attachment_id INTO v_attachment
    FROM   lab.documents
    WHERE  id = p_document_id AND practice_id = p_practice_id
      AND  status IN ('received', 'parsing')
    FOR    UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'document % is not awaiting extraction in practice %',
            p_document_id, p_practice_id;
    END IF;

    -- Keep the attachment link whatever the caller passed, since the database
    -- knows which file this document was created from and the engine does not.
    IF v_attachment IS NOT NULL THEN
        v_payload := jsonb_set(v_payload, '{visit_attachment_id}',
                               to_jsonb(v_attachment));
    END IF;

    DELETE FROM lab.document_events WHERE document_id = p_document_id;
    DELETE FROM lab.documents       WHERE id = p_document_id;

    v_new_id := lab.fn_ingest_lab_document(p_practice_id, v_payload, p_actor);
    RETURN v_new_id;
END;
$$;

COMMENT ON FUNCTION lab.fn_complete_document IS
  'Replace the placeholder written at upload with the real extracted document. '
  'Goes through fn_ingest_lab_document so there stays exactly one write path '
  'that turns a payload into clinical rows.';
