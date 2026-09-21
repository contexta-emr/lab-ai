-- =============================================================================
-- Contexta - Lab extraction store
-- 006  The visit_attachment foreign key
-- =============================================================================
-- Run after 005.
--
-- WHY THIS IS A SEPARATE FILE AND NOT PART OF 002
--   lab.documents.visit_attachment_id points at core.visit_attachments, which
--   belongs to the EMR. 002 leaves it as a bare BIGINT so the lab schema can be
--   installed on a database that has no core schema at all - a scoring harness,
--   a vocabulary-only deployment, a test fixture.
--
--   This file is the opposite case: core IS present (000 created it, or the real
--   EMR database already has it), so the reference can be enforced. Both 002 and
--   docs/architecture.md section 3.2 promised this file existed. It did not.
--   This is it.
--
--   When this service is pointed at the real EMR database you drop 000 from the
--   run order and keep this one: the FK is against core.visit_attachments either
--   way, and the EMR's table is the same table.
-- =============================================================================


-- ON DELETE SET NULL, not CASCADE. Deleting the stored file must never delete
-- the extraction: the parsed results, the review decision and the audit trail
-- outlive the blob. A document whose file has gone is still clinical history.
ALTER TABLE lab.documents
    DROP CONSTRAINT IF EXISTS documents_visit_attachment_fk;

ALTER TABLE lab.documents
    ADD CONSTRAINT documents_visit_attachment_fk
    FOREIGN KEY (visit_attachment_id)
    REFERENCES core.visit_attachments (id)
    ON DELETE SET NULL;

COMMENT ON CONSTRAINT documents_visit_attachment_fk ON lab.documents IS
  'Added in 006 rather than 002 so the lab schema installs without core. '
  'SET NULL on delete: the extraction outlives the file.';
