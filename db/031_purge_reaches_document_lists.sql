-- =============================================================================
-- Contexta - Lab extraction store
-- 031  The fixture purge reaches lab.document_lists
-- =============================================================================
-- Run after 030.
--
-- WHAT WENT WRONG
--   028 added lab.document_lists, a child of lab.documents, and nothing told
--   fn_purge_synthetic (010) about it. The first benchmark run after a reviewer
--   had typed a doctor's order failed on the foreign key:
--
--       update or delete on table "documents" violates foreign key constraint
--       "document_lists_document_id_fkey" on table "document_lists"
--
--   The purge rolled back, as a function does - but bench/run.ps1 ran its
--   other clearing statements separately and hid the error, so it went on to
--   delete every core.visit_attachments row, the stored PDFs and the saved
--   engine output, "uploaded" 300 PDFs that all deduplicated against the
--   documents still there, and scored the old data as a new run. run.ps1 now
--   clears in one transaction and stops when it fails; this lets it succeed.
--
-- NOW
--   The purge deletes a purged document's lists with the rest of its
--   children. Everything else is 010's function unchanged. Checked against
--   pg_constraint: document_lists was the only child of lab.documents, or of
--   anything under it, that the purge did not reach.
-- =============================================================================

CREATE OR REPLACE FUNCTION lab.fn_purge_synthetic(
    p_practice_id BIGINT,
    p_checksum    CHAR(64) DEFAULT NULL
)
RETURNS TABLE (
    documents_removed BIGINT,
    results_removed   BIGINT
)
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
AS $$
DECLARE
    v_docs    BIGINT[];
    v_results BIGINT;
BEGIN
    SELECT array_agg(id) INTO v_docs
    FROM   lab.documents
    WHERE  practice_id = p_practice_id
      AND  is_synthetic = TRUE
      AND  (p_checksum IS NULL OR checksum_sha256 = p_checksum);

    IF v_docs IS NULL THEN
        RETURN QUERY SELECT 0::BIGINT, 0::BIGINT;
        RETURN;
    END IF;

    SELECT count(*) INTO v_results
    FROM   lab.results WHERE document_id = ANY(v_docs);

    DELETE FROM lab.results         WHERE document_id = ANY(v_docs);
    DELETE FROM lab.report_notes    WHERE report_id IN
        (SELECT id FROM lab.reports WHERE document_id = ANY(v_docs));
    DELETE FROM lab.report_sections WHERE report_id IN
        (SELECT id FROM lab.reports WHERE document_id = ANY(v_docs));
    DELETE FROM lab.reports         WHERE document_id = ANY(v_docs);
    DELETE FROM lab.document_events WHERE document_id = ANY(v_docs);
    DELETE FROM lab.document_lists  WHERE document_id = ANY(v_docs);
    DELETE FROM lab.documents       WHERE id = ANY(v_docs);

    -- Only on a full purge. Clearing the unmatched queue while re-reading one
    -- document would throw away what the other sixty told us.
    IF p_checksum IS NULL THEN
        DELETE FROM lab.unmatched_labels
        WHERE  practice_id = p_practice_id
          AND  resolved_analyte_id IS NULL;
    END IF;

    RETURN QUERY SELECT array_length(v_docs, 1)::BIGINT, v_results;
END;
$$;

COMMENT ON FUNCTION lab.fn_purge_synthetic IS
  'Hard-deletes fixture documents and everything under them, document_lists '
  'included (031), for one practice. With a checksum, just that one document, '
  'so a partial OCR run does not destroy the rest. Filters is_synthetic = TRUE '
  'throughout, so it cannot reach a real patient document. Real documents are '
  'deleted softly.';
