-- =============================================================================
-- Contexta - Lab extraction store
-- 037  Delete a report for good
-- =============================================================================
-- Run after 036.
--
-- WHY
--   The team console is open to anyone with its link, and people upload real
--   reports to it. One uploaded by mistake has to be able to leave the system
--   completely - Karthik's call of 2026-10-15: erase, not hide.
--
--   This is a deliberate exception to "soft delete everywhere": a hidden row
--   is still a patient's lab report sitting in the database.
--
-- WHAT
--   lab.fn_erase_document removes the document and everything hanging off it,
--   children first: results, notes, sections, reports, lists, events, the
--   document, the stored file, and the attachment record. A patient record is
--   NOT removed - it may hold other reports - and nor is the vocabulary.
--
--   What stays is one row in lab.document_deletions: which document, which
--   practice, who, when, and the status it had. Deliberately no file name,
--   label or value - a file name is often the patient's name.
--
--   Any status may be erased; a verified report's values leave the patient's
--   trends with it. The screen warns before that.
-- =============================================================================

CREATE TABLE IF NOT EXISTS lab.document_deletions (
    id                 BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    practice_id        BIGINT       NOT NULL REFERENCES core.practices(id),
    document_id        BIGINT       NOT NULL,   -- no FK: the document is gone
    status_at_deletion VARCHAR(20),
    result_count       INTEGER      NOT NULL DEFAULT 0,
    deleted_by         BIGINT       REFERENCES core.users(id),
    deleted_at         TIMESTAMP(6) NOT NULL DEFAULT now()
);

COMMENT ON TABLE lab.document_deletions IS
  'One row per report erased through lab.fn_erase_document (037). Holds no '
  'file name, label or value - only which document, who, when, and its status.';

CREATE OR REPLACE FUNCTION lab.fn_erase_document(
    p_practice_id  BIGINT,
    p_document_id  BIGINT,
    p_actor        BIGINT
)
RETURNS BIGINT
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
AS $$
DECLARE
    v_doc        lab.documents%ROWTYPE;
    v_results    INTEGER;
BEGIN
    SELECT * INTO v_doc FROM lab.documents
    WHERE  id = p_document_id AND practice_id = p_practice_id
    FOR    UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION USING ERRCODE = 'P0002',
              MESSAGE = format('document %s not found', p_document_id);
    END IF;

    SELECT count(*) INTO v_results FROM lab.results WHERE document_id = p_document_id;

    DELETE FROM lab.results         WHERE document_id = p_document_id;
    DELETE FROM lab.report_notes    WHERE report_id IN
        (SELECT id FROM lab.reports WHERE document_id = p_document_id);
    DELETE FROM lab.report_sections WHERE report_id IN
        (SELECT id FROM lab.reports WHERE document_id = p_document_id);
    DELETE FROM lab.reports         WHERE document_id = p_document_id;
    DELETE FROM lab.document_lists  WHERE document_id = p_document_id;
    DELETE FROM lab.document_events WHERE document_id = p_document_id;
    DELETE FROM lab.documents       WHERE id = p_document_id;

    IF v_doc.visit_attachment_id IS NOT NULL THEN
        DELETE FROM lab.document_files    WHERE visit_attachment_id = v_doc.visit_attachment_id;
        DELETE FROM core.visit_attachments
        WHERE  id = v_doc.visit_attachment_id AND practice_id = p_practice_id;
    END IF;

    INSERT INTO lab.document_deletions
        (practice_id, document_id, status_at_deletion, result_count, deleted_by)
    VALUES (p_practice_id, p_document_id, v_doc.status, v_results, p_actor);

    RETURN p_document_id;
END;
$$;

COMMENT ON FUNCTION lab.fn_erase_document IS
  'Erase one report for good: results, notes, sections, reports, lists, events, '
  'the document, its stored file and attachment. Records only who and when in '
  'lab.document_deletions. P0002 when the document is not in this practice.';
