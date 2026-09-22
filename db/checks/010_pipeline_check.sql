-- Read-only. What actually landed in the tables after an upload + worker run.
--
--   docker compose exec -T db psql -U labidp -d labidp -f /work/db/checks/010_pipeline_check.sql
--
-- Nothing here writes. Seven questions, in the order worth asking them.

\pset border 2
\echo
\echo '=== 1. Where is every document? ==============================='
\echo 'received = uploaded, not read yet.  parsing = a worker has it.'
\echo 'parsed   = read and the patient matched.  needs_review = no match.'
\echo 'failed   = the engine gave up after its attempts.'
SELECT status,
       ocr_engine,
       count(*)                       AS documents,
       sum(ocr_attempts)              AS total_attempts,
       count(*) FILTER (WHERE ocr_error IS NOT NULL) AS with_error
FROM   lab.documents
WHERE  is_deleted = FALSE
GROUP  BY status, ocr_engine
ORDER  BY documents DESC;

\echo
\echo '=== 2. Did rows actually get stored, per document? ============='
\echo 'result_count 0 with status parsed means it read the page and found'
\echo 'nothing - a different problem from never having been read.'
SELECT d.id,
       d.status,
       r.lab_name,
       d.detected_uhid,
       p.uhid                          AS matched_patient,
       d.page_count,
       (SELECT count(*) FROM lab.report_sections s
         WHERE s.report_id = r.id AND s.is_deleted = FALSE) AS sections,
       (SELECT count(*) FROM lab.results x
         WHERE x.document_id = d.id AND x.is_deleted = FALSE) AS results,
       (SELECT count(*) FROM lab.results x
         WHERE x.document_id = d.id AND x.is_deleted = FALSE
           AND x.analyte_id IS NULL)                         AS no_code,
       round(d.extraction_confidence, 2) AS conf
FROM   lab.documents d
LEFT   JOIN lab.reports  r ON r.document_id = d.id AND r.is_deleted = FALSE
LEFT   JOIN core.patients p ON p.id = d.patient_id
WHERE  d.is_deleted = FALSE
ORDER  BY d.id;

\echo
\echo '=== 3. The actual stored rows - the point of the whole service =='
\echo 'printed_label is what the page said. code is what SQL resolved it'
\echo 'to. A blank code is honest: the row is stored, just not chartable.'
SELECT d.id                AS doc,
       s.heading_printed   AS section,
       res.printed_label,
       a.code,
       res.match_method,
       res.value_text,
       res.unit_printed    AS unit,
       res.reference_printed AS reference,
       res.flag
FROM   lab.results res
JOIN   lab.documents d ON d.id = res.document_id
LEFT   JOIN lab.report_sections s ON s.id = res.section_id
LEFT   JOIN lab.analytes a ON a.id = res.analyte_id
WHERE  res.is_deleted = FALSE
ORDER  BY d.id, res.section_id NULLS FIRST, res.sequence
LIMIT  40;

\echo
\echo '=== 4. How well did the vocabulary do? ========================='
SELECT match_method,
       count(*)                                  AS rows,
       round(avg(match_confidence), 3)           AS avg_confidence
FROM   lab.results
WHERE  is_deleted = FALSE
GROUP  BY match_method
ORDER  BY rows DESC;

\echo
\echo '=== 5. Labels the master still misses ========================='
\echo 'The work queue for growing the vocabulary, and the honest measure'
\echo 'of how much of the real world it does not know yet.'
SELECT printed_label, sample_value, sample_unit, occurrence_count
FROM   lab.unmatched_labels
WHERE  resolved_analyte_id IS NULL
ORDER  BY occurrence_count DESC, printed_label
LIMIT  20;

\echo
\echo '=== 6. Anything stuck or broken? =============================='
SELECT id, status, ocr_attempts, claimed_at, left(ocr_error, 110) AS error
FROM   lab.documents
WHERE  is_deleted = FALSE
  AND  (status IN ('failed', 'parsing') OR ocr_error IS NOT NULL)
ORDER  BY id;

\echo
\echo '=== 7. What a clinician would actually see ===================='
\echo 'Nothing counts until a human verifies it, so this is normally'
\echo 'empty until you verify a document in the review console.'
SELECT count(*) AS verified_results_visible_in_trends
FROM   lab.v_results_verified;
