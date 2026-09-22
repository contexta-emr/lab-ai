-- =============================================================================
-- Contexta - Lab extraction store
-- 012  fn_complete_document must remove the placeholder's children first
-- =============================================================================
-- Run after 011.
--
-- THE BUG
--   011 said, in its own comment: "The placeholder carries no reports,
--   sections or results: it was created empty." That is wrong, and the first
--   worker run proved it - every document failed with
--
--       ForeignKeyViolation: update or delete on table "documents" violates
--       foreign key constraint
--
--   The placeholder is created by fn_ingest_lab_document like any other
--   document, and that function always writes a lab.reports row for each entry
--   in the payload. The upload placeholder has one report with one note
--   ("Queued for extraction"), so the DELETE had children to trip over.
--
--   Assuming the shape of a row instead of reading the function that writes it
--   is what caused this. The retry ladder behaved correctly throughout - three
--   attempts, then 'failed', with the reason recorded - which is the only
--   reason it was obvious rather than silent. It still burned nine OpenParser
--   calls proving a database bug.
--
-- THE FIX
--   Delete the children in dependency order, the same order fn_purge_synthetic
--   uses, and for the same reason: results references section, report and
--   document, so it goes before all three.
-- =============================================================================

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

    -- Keep the attachment link whatever the caller passed: the database knows
    -- which file this document was created from and the engine does not.
    IF v_attachment IS NOT NULL THEN
        v_payload := jsonb_set(v_payload, '{visit_attachment_id}',
                               to_jsonb(v_attachment));
    END IF;

    -- Children first, deepest first. The placeholder has a report and a note,
    -- and may have sections and results if it was ever partly read.
    DELETE FROM lab.results         WHERE document_id = p_document_id;
    DELETE FROM lab.report_notes    WHERE report_id IN
        (SELECT id FROM lab.reports WHERE document_id = p_document_id);
    DELETE FROM lab.report_sections WHERE report_id IN
        (SELECT id FROM lab.reports WHERE document_id = p_document_id);
    DELETE FROM lab.reports         WHERE document_id = p_document_id;
    DELETE FROM lab.document_events WHERE document_id = p_document_id;
    DELETE FROM lab.documents       WHERE id = p_document_id;

    RETURN lab.fn_ingest_lab_document(p_practice_id, v_payload, p_actor);
END;
$$;

COMMENT ON FUNCTION lab.fn_complete_document IS
  'Replace the placeholder written at upload with the real extracted document. '
  'Removes the placeholder and everything under it, then goes through '
  'fn_ingest_lab_document so there stays exactly one write path that turns a '
  'payload into clinical rows.';
