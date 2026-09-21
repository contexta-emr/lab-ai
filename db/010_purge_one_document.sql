-- =============================================================================
-- Contexta - Lab extraction store
-- 010  fn_purge_synthetic takes an optional checksum
-- =============================================================================
-- Run after 009.
--
-- WHY
--   scripts/ocr_corpus.py re-reads a document that is already in the database.
--   The text-layer run stored all 300 by checksum; the 61 with no text layer
--   stored zero rows, and OCR now has something to put there. But
--   lab.documents is unique on (practice_id, checksum_sha256), so ingesting
--   the OCR result fails - or worse, is quietly ignored - unless the earlier
--   empty row goes first.
--
--   Purging one document rather than all of them matters because a partial
--   OCR run is normal. Reading five of the sixty-one must not destroy the
--   other fifty-six, and re-running one document after a failure must not
--   mean re-reading and re-paying for the rest.
--
-- WHY THE SIGNATURE CHANGES INSTEAD OF A SECOND FUNCTION
--   The delete order - results, notes, sections, reports, events, document -
--   is the part that is easy to get wrong, and 009 exists because two scripts
--   got it wrong independently. Copying it into a near-identical
--   fn_purge_synthetic_one would put it in two places and guarantee they
--   drift. One function, one optional filter.
--
--   p_checksum defaults to NULL, which means every synthetic document, so
--   existing callers - load_corpus.py --reset and upload_corpus.py --reset -
--   keep working unchanged.
--
--   The is_synthetic = TRUE filter is still applied at every level. This still
--   cannot reach a real patient document, whatever checksum it is handed.
-- =============================================================================

DROP FUNCTION IF EXISTS lab.fn_purge_synthetic(BIGINT);

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
  'Hard-deletes fixture documents and everything under them, for one practice. '
  'With a checksum, just that one document, so a partial OCR run does not '
  'destroy the rest. Filters is_synthetic = TRUE throughout, so it cannot '
  'reach a real patient document. Real documents are deleted softly.';
