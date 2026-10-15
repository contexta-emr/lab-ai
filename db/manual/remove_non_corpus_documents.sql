-- =============================================================================
-- Contexta - Lab extraction store
-- MANUAL: take every non-corpus report out of practice 1
-- =============================================================================
-- NOT A MIGRATION. run_migrations.py reads only db/NNN_*.sql, so this is
-- never applied by accident. Karthik runs it by hand, in two steps, against
-- Neon, BEFORE setting OPEN_ACCESS_SAMPLE on Vercel.
--
-- WHY
--   The Sample data switch shows practice 1 to anyone with the link, so
--   practice 1 must hold nothing but the synthetic corpus. Four uploads of
--   2026-10-13 look like real people's reports (Ashwini, sudhir_gundu,
--   5987510-PM-..., DocScanner), and there may be others.
--
--   lab.fn_purge_synthetic cannot remove them: it only touches documents
--   marked is_synthetic, and an upload is not.
--
--   A corpus report is named P##-R##.pdf (P01-P23). Anything else is listed.
-- =============================================================================

-- STEP 1 - read the list. Nothing changes.
SELECT d.id, d.status, d.received_at::date AS received, va.original_file_name,
       d.patient_id, p.uhid AS patient_uhid
FROM   lab.documents d
JOIN   core.practices pr ON pr.id = d.practice_id AND pr.name = 'Contexta Demo Clinic'
LEFT   JOIN core.visit_attachments va ON va.id = d.visit_attachment_id
LEFT   JOIN core.patients p ON p.id = d.patient_id
WHERE  d.is_deleted = FALSE
  AND  coalesce(va.original_file_name, '') !~ '^P[0-9]{2}-R[0-9]{2}\.pdf$'
ORDER  BY d.received_at;


-- STEP 2 - only after reading that list, run everything from BEGIN to COMMIT.
-- One transaction: if any statement fails, nothing is removed. Paste the
-- error back rather than editing around it.
BEGIN;

CREATE TEMP TABLE doomed ON COMMIT DROP AS
SELECT d.id, d.visit_attachment_id
FROM   lab.documents d
JOIN   core.practices pr ON pr.id = d.practice_id AND pr.name = 'Contexta Demo Clinic'
LEFT   JOIN core.visit_attachments va ON va.id = d.visit_attachment_id
WHERE  d.is_deleted = FALSE
  AND  coalesce(va.original_file_name, '') !~ '^P[0-9]{2}-R[0-9]{2}\.pdf$';

DELETE FROM lab.results         WHERE document_id IN (SELECT id FROM doomed);
DELETE FROM lab.report_notes    WHERE report_id IN
    (SELECT r.id FROM lab.reports r WHERE r.document_id IN (SELECT id FROM doomed));
DELETE FROM lab.report_sections WHERE report_id IN
    (SELECT r.id FROM lab.reports r WHERE r.document_id IN (SELECT id FROM doomed));
DELETE FROM lab.reports         WHERE document_id IN (SELECT id FROM doomed);
DELETE FROM lab.document_events WHERE document_id IN (SELECT id FROM doomed);
DELETE FROM lab.document_lists  WHERE document_id IN (SELECT id FROM doomed);
DELETE FROM lab.documents       WHERE id IN (SELECT id FROM doomed);
DELETE FROM lab.document_files  WHERE visit_attachment_id IN (SELECT visit_attachment_id FROM doomed);
DELETE FROM core.visit_attachments WHERE id IN (SELECT visit_attachment_id FROM doomed);

SELECT count(*) AS removed FROM doomed;

COMMIT;


-- Patients those reports created are NOT removed here: a seeded patient may
-- also appear on corpus reports. To see any patient left with no report:
--
--   SELECT p.id, p.uhid, p.created_at
--   FROM   core.patients p
--   JOIN   core.practices pr ON pr.id = p.practice_id AND pr.name = 'Contexta Demo Clinic'
--   WHERE  NOT EXISTS (SELECT 1 FROM lab.documents d
--                      WHERE d.patient_id = p.id AND d.is_deleted = FALSE);
