-- =============================================================================
-- Contexta - Lab extraction store
-- 005  Seed: demo practice, seed user, 20 synthetic patients
-- =============================================================================
-- GENERATED FILE - do not edit by hand.
--   Source:     corpus/generator/patients/p01.py .. p20.py
--   Regenerate: python db/seed/export_patients.py
--
-- Every person below is invented. The UHIDs are the ones printed on the 300
-- corpus PDFs, so scripts/load_corpus.py can match documents to patients the
-- same way the real pipeline will: by reading the UHID off the page.
-- =============================================================================

BEGIN;

-- ------------------------------------------------------------- practice
INSERT INTO core.practices (name, city)
VALUES ('Contexta Demo Clinic', 'Pune')
ON CONFLICT DO NOTHING;

-- ----------------------------------------------------------- seed user
-- The actor recorded as created_by on everything the loader writes.
INSERT INTO core.users (practice_id, email, full_name, role)
SELECT p.id, 'idp.seed@contexta.local', 'Corpus Loader', 'service'
FROM core.practices p WHERE p.name = 'Contexta Demo Clinic'
ON CONFLICT (email) DO NOTHING;

-- ------------------------------------------------------------- patients
INSERT INTO core.patients (practice_id, uhid, first_name, last_name, dob,
                           gender, city, created_by)
SELECT pr.id, v.uhid, v.first_name, v.last_name, v.dob::DATE, v.gender,
       v.city, u.id
FROM (VALUES
    -- Endocrinology: Type 2 diabetes, poor control improving, then a relapse year
    ('SRV/207431', 'Mahesh', 'V. Deshpande', '1969-04-12', 'Male', 'Pune'),
    -- Cardiology: Post-MI secondary prevention, statin titration
    ('SKH/318645', 'Vasantrao', 'B. Ingle', '1960-05-22', 'Male', 'Nagpur'),
    -- Nephrology: CKD stage 3a progressing to 3b, diabetic nephropathy
    ('GCH/442719', 'Padmavathi', 'Rangaiah', '1963-08-19', 'Female', 'Hyderabad'),
    -- Paediatrics: Iron-deficiency anaemia in a child, treated and resolving
    ('SACH/108842', 'Aadhya', 'Menon', '2015-06-30', 'Female', 'Kochi'),
    -- Paediatrics: Recurrent febrile illness, dengue episode, full recovery
    ('MCH/226104', 'Devansh', 'Choudhary', '2010-03-14', 'Male', 'Jaipur'),
    -- Hepatology: Non-alcoholic fatty liver, weight loss improves enzymes
    ('SVH/513207', 'Jigar', 'H. Bhavsar', '1976-07-08', 'Male', 'Ahmedabad'),
    -- Endocrinology: Hypothyroidism, dose titration to euthyroid
    ('MLC/607318', 'Shalini', 'Awasthi', '1987-02-25', 'Female', 'Lucknow'),
    -- Obstetrics: Two pregnancies: anaemia and gestational diabetes screening
    ('KGH/731592', 'Sasmita', 'Pradhan', '1992-06-18', 'Female', 'Bhubaneswar'),
    -- Haematology: B12 deficiency anaemia, macrocytic, corrected
    ('ARH/845027', 'Rajalakshmi', 'Srinivasan', '1955-01-30', 'Female', 'Chennai'),
    -- Cardiology: Hypertension with dyslipidaemia, stable on treatment
    ('NBH/409376', 'Devendra', 'Singh Thakur', '1973-03-05', 'Male', 'Bhopal'),
    -- Nephrology: Recurrent UTI with stones, kidney function preserved
    ('SKD/562840', 'Hetal', 'D. Rathod', '1984-09-27', 'Female', 'Surat'),
    -- General Medicine: Enteric fever episode, then annual health checks
    ('JPH/318064', 'Ranjan', 'Kumar Choudhary', '1995-04-19', 'Male', 'Patna'),
    -- Endocrinology: Prediabetes progressing to diabetes despite advice
    ('DMC/470913', 'Gurpreet', 'Singh Sahni', '1980-08-14', 'Male', 'Ludhiana'),
    -- Geriatrics: Multi-morbidity: CKD, anaemia, vitamin D deficiency
    ('HVH/205718', 'Brijmohan', 'Lal Uniyal', '1943-05-11', 'Male', 'Dehradun'),
    -- Rheumatology: Rheumatoid arthritis, inflammatory markers responding
    ('BRH/649238', 'Anjali', 'Bhattacharyya', '1977-09-06', 'Female', 'Guwahati'),
    -- Hepatology: Hepatitis B carrier under surveillance, stable
    ('SNH/912476', 'Subhankar', 'Ghoshal', '1982-06-23', 'Male', 'Kolkata'),
    -- Paediatrics: Thalassaemia trait, monitored, no progression
    ('CHM/384051', 'Kiran', 'Gowda Shivakumar', '2012-04-26', 'Male', 'Mysuru'),
    -- Oncology Follow-up: Post-treatment monitoring, counts recovering
    ('SGO/573910', 'Vijayalakshmi', 'Appalaraju', '1966-02-17', 'Female', 'Visakhapatnam'),
    -- Pulmonology: Recurrent chest infections in a smoker, inflammation
    ('LMH/704628', 'Ramakant', 'Dwivedi', '1958-03-08', 'Male', 'Kanpur'),
    -- Endocrinology: Thyrotoxicosis treated to hypothyroid, then stable
    ('ANT/826135', 'Divya', 'Sreekumar', '1990-07-19', 'Female', 'Thiruvananthapuram')
) AS v(uhid, first_name, last_name, dob, gender, city)
CROSS JOIN core.practices pr
LEFT JOIN core.users u ON u.email = 'idp.seed@contexta.local'
WHERE pr.name = 'Contexta Demo Clinic'
  AND NOT EXISTS (
      SELECT 1 FROM core.patients ex
      WHERE ex.practice_id = pr.id AND ex.uhid = v.uhid
  );

COMMIT;
