-- =============================================================================
-- Contexta - Lab extraction store
-- 002  Documents, reports, sections, results, notes, pipeline audit
-- =============================================================================
-- Run after 001.
--
-- THE SHAPE, AND WHY
--   document   one uploaded file. Points at core.visit_attachments for the blob;
--              this table only owns extraction state and the patient match.
--   report     one lab report inside that file. Usually one per document, but a
--              register page or a discharge summary can carry more, and a
--              two-page report is still one report.
--   section    one panel block on the report ("COMPLETE HEMOGRAM").
--   result     one printed test line. The atom everything else is built from.
--   note       interpretation paragraphs, footnotes, method remarks.
--
-- NOTHING HERE IS CLINICAL FACT UNTIL documents.status = 'verified'. A parsed
-- but unreviewed result is a machine's opinion about a photograph.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- lab.documents
-- -----------------------------------------------------------------------------
CREATE TABLE lab.documents (
    id                      BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    practice_id             BIGINT       NOT NULL,

    -- The file itself lives in core.visit_attachments (Azure blob, mime type,
    -- size, upload status). FK added in 006 so this schema installs standalone.
    visit_attachment_id     BIGINT,
    visit_id                BIGINT,

    -- Patient resolution. NULL patient_id with status 'needs_review' is the
    -- quarantine state: parsed, stored, attached to nobody.
    patient_id              BIGINT,
    detected_uhid           VARCHAR(40),
    detected_uhid_label     VARCHAR(40),
    detected_patient_name   VARCHAR(255),
    patient_match_method    VARCHAR(20),
    patient_match_confidence NUMERIC(5,4),

    -- Pipeline state
    status                  VARCHAR(20)  NOT NULL DEFAULT 'received',
    source                  VARCHAR(30)  NOT NULL DEFAULT 'emr_upload',
    page_count              INTEGER,
    has_text_layer          BOOLEAN,
    ocr_engine              VARCHAR(40),
    engine_version          VARCHAR(40),
    extraction_confidence   NUMERIC(5,4),
    checksum_sha256         CHAR(64),

    -- Synthetic corpus rows carry this so they can never be mistaken for, or
    -- left mixed in with, real patient documents.
    is_synthetic            BOOLEAN      NOT NULL DEFAULT FALSE,

    received_at             TIMESTAMP(6) NOT NULL DEFAULT now(),
    parsed_at               TIMESTAMP(6),
    reviewed_at             TIMESTAMP(6),
    reviewed_by             BIGINT,
    error_code              VARCHAR(40),
    error_detail            TEXT,

    is_deleted              BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at              TIMESTAMP(6),
    deleted_by              BIGINT,
    created_at              TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by              BIGINT,
    updated_at              TIMESTAMP(6),
    updated_by              BIGINT,

    CONSTRAINT documents_status_check CHECK (status IN (
        'received',      -- row exists, nothing parsed yet
        'parsing',       -- engine running
        'parsed',        -- extracted, patient matched, awaiting review
        'needs_review',  -- extracted, patient NOT matched or low confidence
        'verified',      -- a human confirmed it; clinical fact from here
        'rejected',      -- a human rejected it (wrong patient, unreadable)
        'failed'         -- the engine could not parse it
    )),
    CONSTRAINT documents_source_check CHECK (source IN (
        'emr_upload', 'patient_portal', 'bulk_import', 'whatsapp', 'email', 'api'
    )),
    CONSTRAINT documents_match_method_check CHECK (
        patient_match_method IS NULL OR patient_match_method IN
        ('uhid_exact', 'uhid_normalised', 'uhid_fuzzy', 'name_dob', 'manual', 'none')
    ),
    CONSTRAINT documents_confidence_check CHECK (
        patient_match_confidence IS NULL
        OR (patient_match_confidence >= 0 AND patient_match_confidence <= 1)
    ),
    -- A verified document must be attached to somebody. This is the guardrail
    -- that stops a result becoming clinical fact while orphaned.
    CONSTRAINT documents_verified_needs_patient CHECK (
        status <> 'verified' OR patient_id IS NOT NULL
    )
);

-- Same file uploaded twice is the same document.
CREATE UNIQUE INDEX documents_checksum_uq
    ON lab.documents (practice_id, checksum_sha256)
    WHERE is_deleted = FALSE AND checksum_sha256 IS NOT NULL;
CREATE INDEX documents_patient_idx
    ON lab.documents (practice_id, patient_id)
    WHERE is_deleted = FALSE;
-- The review queue reads this one.
CREATE INDEX documents_review_idx
    ON lab.documents (practice_id, status, received_at DESC)
    WHERE is_deleted = FALSE AND status IN ('needs_review', 'parsed');
CREATE INDEX documents_attachment_idx
    ON lab.documents (visit_attachment_id)
    WHERE is_deleted = FALSE AND visit_attachment_id IS NOT NULL;

COMMENT ON TABLE lab.documents IS
  'One uploaded file and its extraction state. The blob lives in '
  'core.visit_attachments; this row owns parsing, patient matching and review.';
COMMENT ON COLUMN lab.documents.ocr_engine IS
  'Which engine read this document, so a result can be traced back to how it was '
  'read. Expected values: pdf-text (the PDF had a text layer, no OCR needed), '
  'paddle_vl (PaddleOCR-VL on our own hardware, in boundary), openparser '
  '(the same model on OpenParser hosted GPU - the document leaves India for '
  'api.openparser.dev in the United States, so synthetic and vendor samples only), '
  'none (stored but not read).';


-- -----------------------------------------------------------------------------
-- lab.reports
-- -----------------------------------------------------------------------------
CREATE TABLE lab.reports (
    id                    BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id           BIGINT       NOT NULL REFERENCES lab.documents(id),
    practice_id           BIGINT       NOT NULL,
    patient_id            BIGINT,               -- denormalised from the document

    lab_name              VARCHAR(255),
    lab_address           VARCHAR(500),
    lab_phone             VARCHAR(40),
    accession_no          VARCHAR(60),

    -- As printed on the page, before any interpretation. Kept verbatim so a
    -- reviewer can see what the paper actually said.
    uhid_printed          VARCHAR(40),
    uhid_label_printed    VARCHAR(40),
    patient_name_printed  VARCHAR(255),
    age_printed           VARCHAR(20),
    sex_printed           CHAR(1),
    collected_text        VARCHAR(60),
    reported_text         VARCHAR(60),

    -- Parsed. Indian reports print DD/MM/YYYY; the text above is the audit trail
    -- if this parse turns out wrong.
    collected_at          TIMESTAMP(6),
    reported_at           TIMESTAMP(6),

    referring_doctor      VARCHAR(255),
    department            VARCHAR(100),
    specimen              VARCHAR(200),
    pathologist_name      VARCHAR(255),
    pathologist_regn      VARCHAR(60),

    -- Useful later for recognising a lab's house format.
    layout_hint           VARCHAR(40),
    header_hint           VARCHAR(40),
    page_from             INTEGER,
    page_to               INTEGER,
    sequence              INTEGER      NOT NULL DEFAULT 1,

    is_deleted            BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at            TIMESTAMP(6),
    deleted_by            BIGINT,
    created_at            TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by            BIGINT,
    updated_at            TIMESTAMP(6),
    updated_by            BIGINT,

    CONSTRAINT reports_sex_check CHECK (sex_printed IS NULL OR sex_printed IN ('M','F','O'))
);

CREATE INDEX reports_document_idx ON lab.reports (document_id) WHERE is_deleted = FALSE;
CREATE INDEX reports_patient_date_idx
    ON lab.reports (practice_id, patient_id, collected_at DESC)
    WHERE is_deleted = FALSE;


-- -----------------------------------------------------------------------------
-- lab.report_sections
-- -----------------------------------------------------------------------------
CREATE TABLE lab.report_sections (
    id                     BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_id              BIGINT       NOT NULL REFERENCES lab.reports(id),
    practice_id            BIGINT       NOT NULL,
    heading_printed        VARCHAR(255),
    panel_id               BIGINT       REFERENCES lab.panels(id),
    panel_match_method     VARCHAR(20),
    panel_match_confidence NUMERIC(5,4),
    sequence               INTEGER      NOT NULL DEFAULT 1,
    is_deleted             BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at             TIMESTAMP(6),
    deleted_by             BIGINT,
    created_at             TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by             BIGINT,
    updated_at             TIMESTAMP(6),
    updated_by             BIGINT,
    CONSTRAINT report_sections_match_check CHECK (
        panel_match_method IS NULL OR panel_match_method IN
        ('title_alias', 'title_fuzzy', 'analyte_vote', 'manual', 'none')
    )
);

CREATE INDEX report_sections_report_idx
    ON lab.report_sections (report_id) WHERE is_deleted = FALSE;

COMMENT ON COLUMN lab.report_sections.panel_match_method IS
  'analyte_vote means the heading matched nothing but the rows underneath were '
  'mostly one panel - the case where a lab groups by specimen instead of panel.';


-- -----------------------------------------------------------------------------
-- lab.results - one printed test line
-- -----------------------------------------------------------------------------
CREATE TABLE lab.results (
    id                    BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    section_id            BIGINT       REFERENCES lab.report_sections(id),
    report_id             BIGINT       NOT NULL REFERENCES lab.reports(id),
    document_id           BIGINT       NOT NULL REFERENCES lab.documents(id),
    practice_id           BIGINT       NOT NULL,
    patient_id            BIGINT,

    -- Denormalised from the report so a five-year trend is one index scan and
    -- not a join per point. Kept in step by fn_ingest_lab_document and
    -- fn_review_lab_document; nothing else writes it.
    collected_at          TIMESTAMP(6),

    printed_label         VARCHAR(255) NOT NULL,
    analyte_id            BIGINT       REFERENCES lab.analytes(id),
    match_method          VARCHAR(20),
    match_confidence      NUMERIC(5,4),

    -- Exactly as printed: '03', '<0.01', 'Not Detected', '++'. Never cleaned up.
    value_text            VARCHAR(255) NOT NULL,
    -- Parsed when the value is a number. NULL for text results, and NULL is the
    -- honest answer - it is not zero.
    value_numeric         NUMERIC(14,4),
    value_operator        VARCHAR(2),

    unit_printed          VARCHAR(40),
    unit_canonical        VARCHAR(40),
    reference_printed     VARCHAR(160),
    ref_low               NUMERIC(14,4),
    ref_high              NUMERIC(14,4),
    flag                  VARCHAR(4),
    method_printed        VARCHAR(160),

    is_text_result        BOOLEAN      NOT NULL DEFAULT FALSE,
    is_derived            BOOLEAN      NOT NULL DEFAULT FALSE,
    sequence              INTEGER      NOT NULL DEFAULT 1,
    extraction_confidence NUMERIC(5,4),

    -- Review trail. corrected_from_analyte_id records what the machine thought
    -- before a human changed it: the training signal for the alias master.
    is_reviewed              BOOLEAN   NOT NULL DEFAULT FALSE,
    reviewed_by              BIGINT,
    reviewed_at              TIMESTAMP(6),
    corrected_from_analyte_id BIGINT   REFERENCES lab.analytes(id),

    is_deleted            BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at            TIMESTAMP(6),
    deleted_by            BIGINT,
    created_at            TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by            BIGINT,
    updated_at            TIMESTAMP(6),
    updated_by            BIGINT,

    CONSTRAINT results_match_method_check CHECK (
        match_method IS NULL OR match_method IN
        ('exact_alias', 'normalised_alias', 'fuzzy_alias', 'manual', 'none')
    ),
    CONSTRAINT results_flag_check CHECK (
        flag IS NULL OR flag IN ('H', 'L', 'HH', 'LL', 'A', 'N')
    ),
    CONSTRAINT results_operator_check CHECK (
        value_operator IS NULL OR value_operator IN ('<', '>', '<=', '>=')
    ),
    CONSTRAINT results_confidence_check CHECK (
        match_confidence IS NULL OR (match_confidence >= 0 AND match_confidence <= 1)
    )
);

-- The trend query: one patient, one analyte, in date order.
CREATE INDEX results_trend_idx
    ON lab.results (practice_id, patient_id, analyte_id, collected_at DESC)
    WHERE is_deleted = FALSE AND analyte_id IS NOT NULL;
CREATE INDEX results_report_idx
    ON lab.results (report_id) WHERE is_deleted = FALSE;
CREATE INDEX results_document_idx
    ON lab.results (document_id) WHERE is_deleted = FALSE;
-- Everything the master could not name, for the review queue and the metrics.
CREATE INDEX results_unmatched_idx
    ON lab.results (practice_id, created_at DESC)
    WHERE is_deleted = FALSE AND analyte_id IS NULL;

COMMENT ON COLUMN lab.results.analyte_id IS
  'NULL when the printed label matched no analyte. An honest blank, never a '
  'guess - a wrong code on a test the vocabulary does not have is worse than '
  'no code at all.';
COMMENT ON COLUMN lab.results.value_text IS
  'Verbatim. Reconstructing what the page said must never require inference.';


-- -----------------------------------------------------------------------------
-- lab.report_notes - the prose around the numbers
-- -----------------------------------------------------------------------------
CREATE TABLE lab.report_notes (
    id             BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_id      BIGINT       NOT NULL REFERENCES lab.reports(id),
    practice_id    BIGINT       NOT NULL,
    note_type      VARCHAR(20)  NOT NULL,
    marker         VARCHAR(8),
    note_text      TEXT         NOT NULL,
    sequence       INTEGER      NOT NULL DEFAULT 1,
    is_deleted     BOOLEAN      NOT NULL DEFAULT FALSE,
    deleted_at     TIMESTAMP(6),
    deleted_by     BIGINT,
    created_at     TIMESTAMP(6) NOT NULL DEFAULT now(),
    created_by     BIGINT,
    CONSTRAINT report_notes_type_check CHECK (note_type IN (
        'interpretation', 'footnote', 'remark', 'advice', 'method', 'legend'
    ))
);

CREATE INDEX report_notes_report_idx
    ON lab.report_notes (report_id) WHERE is_deleted = FALSE;


-- -----------------------------------------------------------------------------
-- lab.document_events - who did what to this document, and when
-- -----------------------------------------------------------------------------
-- Append only. A misfiled lab result is a clinical safety event; when one
-- happens, this is the table that answers how.
CREATE TABLE lab.document_events (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id   BIGINT       NOT NULL REFERENCES lab.documents(id),
    practice_id   BIGINT       NOT NULL,
    event_type    VARCHAR(40)  NOT NULL,
    from_status   VARCHAR(20),
    to_status     VARCHAR(20),
    detail        JSONB,
    actor_user_id BIGINT,
    created_at    TIMESTAMP(6) NOT NULL DEFAULT now()
);

CREATE INDEX document_events_document_idx
    ON lab.document_events (document_id, created_at DESC);


-- -----------------------------------------------------------------------------
-- Read model for the review queue and the chat panel
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW lab.v_results_verified AS
SELECT r.practice_id,
       r.patient_id,
       r.collected_at,
       a.code            AS analyte_code,
       a.display_name    AS analyte_name,
       p.code            AS panel_code,
       r.printed_label,
       r.value_text,
       r.value_numeric,
       r.value_operator,
       COALESCE(r.unit_canonical, r.unit_printed) AS unit,
       r.reference_printed,
       r.ref_low,
       r.ref_high,
       r.flag,
       r.is_derived,
       r.id              AS result_id,
       r.report_id,
       r.document_id
FROM   lab.results   r
JOIN   lab.documents d ON d.id = r.document_id
LEFT   JOIN lab.analytes a ON a.id = r.analyte_id
LEFT   JOIN lab.panels   p ON p.id = a.panel_id
WHERE  r.is_deleted = FALSE
  AND  d.is_deleted = FALSE
  AND  d.status = 'verified';

COMMENT ON VIEW lab.v_results_verified IS
  'Only results on documents a human has verified. Anything reading lab data '
  'for clinical use should read this, not lab.results.';
