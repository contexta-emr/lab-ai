-- =============================================================================
-- Contexta - Lab extraction store
-- 033  The uploaded file, kept in the database
-- =============================================================================
-- Run after 032.
--
-- WHY
--   The upload used to write the file to STORAGE_DIR and then record it. On
--   Vercel the disk is temporary: a file written by one request is gone by
--   the next. So the bytes move into Neon, beside the record that names them.
--
--   They are written in the same transaction as core.visit_attachments, so
--   an upload that fails leaves neither. That also closes review B12: the
--   file used to be written before the transaction, so a failed insert left
--   an orphan on disk.
--
--   core.visit_attachments is the EMR's table and is not altered here. Its
--   storage_provider stays 'local', meaning held by this service rather than
--   by Azure or S3, and a row in this table is where the bytes are.
--   Documents stored before 033 have no row here and are still read from
--   STORAGE_DIR.
-- =============================================================================

CREATE TABLE IF NOT EXISTS lab.document_files (
    id                   BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    practice_id          BIGINT       NOT NULL REFERENCES core.practices(id),
    visit_attachment_id  BIGINT       NOT NULL REFERENCES core.visit_attachments(id),
    content              BYTEA        NOT NULL,
    byte_count           BIGINT       NOT NULL,
    is_deleted           BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at           TIMESTAMP(6),
    deleted_by           BIGINT,
    created_at           TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by           BIGINT,
    updated_at           TIMESTAMP(6),
    updated_by           BIGINT,
    CONSTRAINT document_files_size_check CHECK (byte_count = octet_length(content))
);

CREATE UNIQUE INDEX IF NOT EXISTS document_files_attachment_key
    ON lab.document_files (visit_attachment_id)
    WHERE is_deleted = FALSE;

COMMENT ON TABLE lab.document_files IS
  'The bytes of an uploaded report, one live row per visit_attachment. Written '
  'in the upload transaction (033). Older documents have no row and are read '
  'from STORAGE_DIR by stored_file_name.';
