-- =============================================================================
-- Contexta - Lab extraction store
-- 028  What was ordered, and what the patient said they were tested for
-- =============================================================================
-- Two lists a human types against one document, and they are NOT the same kind
-- of thing:
--
--   doctor_order   what the clinician asked for. A claim about INTENT, against
--                  which the report can be judged: this panel was ordered and
--                  the page does not contain it. That judgement is the point.
--
--   patient_tag    what the patient says they were tested for. Context, not an
--                  order. It is resolved so matching rows can be highlighted and
--                  it is never scored, because a patient naming a test is not a
--                  clinical instruction and reporting it as "missing" would
--                  invent an order nobody placed.
--
-- WHY IN THE DATABASE AND NOT THE BROWSER
--   A doctor's order is a clinical artifact. The existing analyte checklist
--   lives in sessionStorage, which is right for a view preference and wrong for
--   this: the next person to open the document would see nothing, and there
--   would be no record that the comparison was ever made.
--
-- WHY THE RAW TEXT IS STORED, NOT THE RESOLVED CODES
--   What the doctor wrote is the evidence; what we made of it is an opinion that
--   improves every time the alias master grows. Store the opinion and a document
--   reviewed today keeps a worse reading forever. The text is re-resolved on
--   read, so a term that resolves to nothing now resolves later once somebody
--   adds the alias - with no migration and no backfill.
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS lab.document_lists (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id   BIGINT       NOT NULL REFERENCES lab.documents(id),
    practice_id   BIGINT       NOT NULL,

    kind          VARCHAR(20)  NOT NULL,
    -- As typed, newlines and all. Parsing is the reader's job.
    raw_text      TEXT         NOT NULL DEFAULT '',

    is_deleted    BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at    TIMESTAMP(6),
    deleted_by    BIGINT,
    created_at    TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by    BIGINT,
    updated_at    TIMESTAMP(6),
    updated_by    BIGINT,

    CONSTRAINT document_lists_kind_check
        CHECK (kind IN ('doctor_order', 'patient_tag'))
);

-- One list of each kind per document. A second doctor's order on the same page
-- is an edit of the first, not another list.
CREATE UNIQUE INDEX IF NOT EXISTS document_lists_doc_kind_uq
    ON lab.document_lists (document_id, kind)
    WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS document_lists_practice_idx
    ON lab.document_lists (practice_id) WHERE is_deleted = FALSE;

COMMENT ON TABLE lab.document_lists IS
  'What a human typed against a document: the ordered tests (doctor_order) and '
  'what the patient said they were tested for (patient_tag). Raw text only - it '
  'is re-resolved against the master on every read, so the reading improves as '
  'the vocabulary does.';
COMMENT ON COLUMN lab.document_lists.kind IS
  'doctor_order is judged against the page - complete, partial or not present. '
  'patient_tag is never judged: it is context, not an instruction.';

COMMIT;
