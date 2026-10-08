"""lab.fn_create_patient: registering a patient is a deliberate act, never automatic.

Every test here runs inside a transaction that is rolled back, so the seed the rest of
the suite reads is untouched.
"""

from __future__ import annotations

import psycopg
import pytest

PRACTICE = 1
CREATE = """
SELECT lab.fn_create_patient(
    %s::BIGINT, %s::TEXT, %s::TEXT, %s::TEXT, %s::DATE, %s::TEXT, %s::TEXT, %s::BIGINT
)
"""


def _create(
    db,
    uhid,
    first="Ananya",
    last="Bose",
    dob=None,
    gender=None,
    city=None,
    by=None,
    practice=PRACTICE,
):
    with db.cursor() as cur:
        cur.execute(CREATE, (practice, uhid, first, last, dob, gender, city, by))
        return cur.fetchone()[0]


def test_creates_a_patient_and_returns_its_id(db_write):
    new_id = _create(db_write, "TST/000001", dob="1990-01-01", gender="Female")
    assert new_id
    assert new_id > 0
    with db_write.cursor() as cur:
        cur.execute(
            "SELECT uhid, first_name, last_name, gender, practice_id "
            "FROM core.patients WHERE id = %s",
            (new_id,),
        )
        assert cur.fetchone() == ("TST/000001", "Ananya", "Bose", "Female", PRACTICE)


def test_a_uhid_already_in_this_practice_is_a_conflict(db_write):
    """The reviewer is looking at someone already registered. The answer is to attach
    the document to them, not to make a second record of the same person."""
    _create(db_write, "TST/000002")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _create(db_write, "TST/000002", first="Someone", last="Else")


def test_a_uhid_is_required(db_write):
    """A patient with no identifier cannot be matched to their next report."""
    for blank in ("", "   ", None):
        with pytest.raises(psycopg.errors.NullValueNotAllowed):
            _create(db_write, blank)
        db_write.rollback()


def test_a_given_name_is_required(db_write):
    with pytest.raises(psycopg.errors.NullValueNotAllowed):
        _create(db_write, "TST/000003", first="  ")


def test_a_surname_is_optional(db_write):
    """Many Indian reports print one name; refusing the record would strand the
    document with nowhere to attach."""
    new_id = _create(db_write, "TST/000004", first="Devansh", last="")
    with db_write.cursor() as cur:
        cur.execute("SELECT last_name FROM core.patients WHERE id = %s", (new_id,))
        assert cur.fetchone()[0] == ""


def test_a_uhid_longer_than_the_column_is_rejected_by_name(db_write):
    """Not a truncation, and not a 500 three layers up: a stated limit."""
    with pytest.raises(psycopg.errors.StringDataRightTruncation):
        _create(db_write, "X" * 21)


def test_the_new_patient_is_findable_by_the_matcher(db_write):
    """The point of creating one: the next report for this person must match."""
    _create(db_write, "TST/000005", first="Meenakshi", last="Sundaram")
    with db_write.cursor() as cur:
        cur.execute(
            "SELECT matched_name, confidence FROM lab.fn_match_patient_by_demographics(%s, %s)",
            (PRACTICE, "Meenakshi Sundaram"),
        )
        row = cur.fetchone()
    assert row
    assert row[0] == "Meenakshi Sundaram"
    assert row[1] < 1
