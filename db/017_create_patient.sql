-- 017: create a patient, deliberately, from the review screen.
--
-- A report arrives for someone the practice has never registered. The reviewer can see
-- the name and the UHID printed on the page and knows this is a real patient; there is
-- nowhere to attach the document until a record exists.
--
-- THE RULE: nothing calls this except an explicit reviewer action. Ingest never calls it.
-- fn_match_patient_by_uhid and fn_match_patient_by_demographics never call it. A document
-- that matches nobody goes to needs_review and STAYS there until a human decides. An
-- automatic create turns one misread UHID into a duplicate patient record, and duplicate
-- patients are how two halves of one person's history end up on two charts.
--
-- It is a function rather than an INSERT in the API for the same reason every other write
-- here is: the validation lives next to the constraint it protects, and the API cannot
-- forget to pass practice_id.

CREATE OR REPLACE FUNCTION lab.fn_create_patient(
    p_practice_id BIGINT,
    p_uhid        TEXT,
    p_first_name  TEXT,
    p_last_name   TEXT    DEFAULT '',
    p_dob         DATE    DEFAULT NULL,
    p_gender      TEXT    DEFAULT NULL,
    p_city        TEXT    DEFAULT NULL,
    p_created_by  BIGINT  DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
VOLATILE
SECURITY INVOKER
AS $$
DECLARE
    v_uhid  TEXT := TRIM(COALESCE(p_uhid, ''));
    v_first TEXT := TRIM(COALESCE(p_first_name, ''));
    v_last  TEXT := TRIM(COALESCE(p_last_name, ''));
    v_id    BIGINT;
BEGIN
    IF p_practice_id IS NULL THEN
        RAISE EXCEPTION 'practice_id is required' USING ERRCODE = 'null_value_not_allowed';
    END IF;

    -- A patient with no identifier cannot be found again, and a second report for the
    -- same person would create a second record. The reviewer supplies the UHID printed
    -- on the page, or the one the practice issues.
    IF v_uhid = '' THEN
        RAISE EXCEPTION 'uhid is required: a patient with no identifier cannot be matched '
                        'to their next report'
              USING ERRCODE = 'null_value_not_allowed';
    END IF;
    IF length(v_uhid) > 20 THEN
        RAISE EXCEPTION 'uhid is longer than the 20 characters core.patients allows: %',
                        v_uhid USING ERRCODE = 'string_data_right_truncation';
    END IF;

    -- Many Indian reports print one name, so a surname is optional. A given name is not:
    -- an unnamed patient record is indistinguishable from the next unnamed one.
    IF v_first = '' THEN
        RAISE EXCEPTION 'first_name is required' USING ERRCODE = 'null_value_not_allowed';
    END IF;

    BEGIN
        INSERT INTO core.patients (practice_id, uhid, first_name, last_name,
                                   dob, gender, city, created_by)
        VALUES (p_practice_id, v_uhid, v_first, v_last,
                p_dob, NULLIF(TRIM(COALESCE(p_gender, '')), ''),
                NULLIF(TRIM(COALESCE(p_city, '')), ''), p_created_by)
        RETURNING id INTO v_id;
    EXCEPTION WHEN unique_violation THEN
        -- patients_practice_uhid_uq. The reviewer is looking at a patient who already
        -- exists; the answer is to attach the document to them, not to make a second
        -- record. Naming the UHID lets the caller say exactly that.
        RAISE EXCEPTION 'a patient with UHID % already exists in this practice', v_uhid
              USING ERRCODE = 'unique_violation';
    END;

    RETURN v_id;
END;
$$;

COMMENT ON FUNCTION lab.fn_create_patient IS
  'Create a patient as a deliberate reviewer action. Never called by ingest or by either '
  'matcher: an unmatched document waits in needs_review until a human decides, because an '
  'automatic create turns one misread UHID into a duplicate patient.';
