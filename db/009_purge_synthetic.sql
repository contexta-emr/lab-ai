-- =============================================================================
-- Contexta - Lab extraction store
-- 009  lab.fn_purge_synthetic - the one way to remove fixture data
-- =============================================================================
-- Run after 008.
--
-- THE PROBLEM
--   Both scripts/load_corpus.py --reset and scripts/upload_corpus.py --reset
--   did this:
--
--       DELETE FROM lab.documents WHERE is_synthetic = TRUE
--
--   which cannot work. reports, report_sections, results, report_notes and
--   document_events all reference a document, so the delete fails on
--   reports_document_id_fkey before it removes anything. Neither had ever been
--   run; the first --reset found it immediately.
--
-- WHY A FUNCTION AND NOT ON DELETE CASCADE
--   Cascade would make both scripts work unchanged and is tempting. It also
--   makes every hard delete of a document silently take its whole extraction
--   with it, including for real patient documents, which is a bigger blast
--   radius than the problem deserves.
--
--   This function cannot do that. It filters on is_synthetic = TRUE at every
--   level, so a real document is not reachable from it however it is called.
--   It also keeps the rule CLAUDE.md sets for everything else: writes to lab.*
--   go through a function, and the scripts do not build SQL.
--
--   Ordinary deletion of real documents stays soft (is_deleted), as designed.
--   This is a fixture tool and says so in its name.
-- =============================================================================

CREATE OR REPLACE FUNCTION lab.fn_purge_synthetic(
    p_practice_id BIGINT
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
      AND  is_synthetic = TRUE;

    IF v_docs IS NULL THEN
        RETURN QUERY SELECT 0::BIGINT, 0::BIGINT;
        RETURN;
    END IF;

    SELECT count(*) INTO v_results
    FROM   lab.results WHERE document_id = ANY(v_docs);

    -- Children first, deepest first. results references section, report and
    -- document, so it goes before all three.
    DELETE FROM lab.results         WHERE document_id = ANY(v_docs);
    DELETE FROM lab.report_notes    WHERE report_id IN
        (SELECT id FROM lab.reports WHERE document_id = ANY(v_docs));
    DELETE FROM lab.report_sections WHERE report_id IN
        (SELECT id FROM lab.reports WHERE document_id = ANY(v_docs));
    DELETE FROM lab.reports         WHERE document_id = ANY(v_docs);
    DELETE FROM lab.document_events WHERE document_id = ANY(v_docs);
    DELETE FROM lab.documents       WHERE id = ANY(v_docs);

    -- Labels learned only from fixture pages should not outlive them, or the
    -- unmatched queue slowly fills with tests no real report ever printed.
    DELETE FROM lab.unmatched_labels
    WHERE  practice_id = p_practice_id
      AND  resolved_analyte_id IS NULL;

    RETURN QUERY SELECT array_length(v_docs, 1)::BIGINT, v_results;
END;
$$;

COMMENT ON FUNCTION lab.fn_purge_synthetic IS
  'Hard-deletes fixture documents and everything under them, for one practice. '
  'Filters on is_synthetic = TRUE throughout, so it cannot reach a real '
  'patient document. Real documents are deleted softly, never by this.';
