-- =============================================================================
-- Contexta - Lab extraction store
-- 023  Seed: the 1 BENCHMARK vocabulary fixture patient(s)
-- =============================================================================
-- GENERATED FILE - do not edit by hand.
--   Source:     corpus/generator/patients/p31.py
--   Regenerate: python db/seed/export_patients.py --benchmark
--
-- These three are the evaluation set. Their PDFs live in
-- corpus/data/holdout/ and are loaded only by
-- scripts/load_corpus.py --holdout.
--
-- Numbered last on purpose: it must run after 005 has created the
-- practice these patients hang off, and it is the one migration a
-- normal setup is expected to skip.
--
-- Apply this migration ONLY when you intend to score the extractor. Without
-- it these UHIDs match no patient, so every holdout document lands in the
-- review queue - which is the right answer for a patient the practice has
-- never registered, and is itself worth testing.
-- =============================================================================

BEGIN;

-- ------------------------------------------------------------- patients
INSERT INTO core.patients (practice_id, uhid, first_name, last_name, dob,
                           gender, city, created_by)
SELECT pr.id, v.uhid, v.first_name, v.last_name, v.dob::DATE, v.gender,
       v.city, u.id
FROM (VALUES
    -- Internal Medicine: Urosepsis - culture, coagulation and serology fixtures
    ('DCH/880471', 'Shalini', 'Kulkarni', '1959-02-11', 'Female', 'Pune')
) AS v(uhid, first_name, last_name, dob, gender, city)
CROSS JOIN core.practices pr
LEFT JOIN core.users u ON u.email = 'idp.seed@contexta.local'
WHERE pr.name = 'Contexta Demo Clinic'
  AND NOT EXISTS (
      SELECT 1 FROM core.patients ex
      WHERE ex.practice_id = pr.id AND ex.uhid = v.uhid
  );

COMMIT;
