"""lab.fn_match_patient_by_demographics: the fallback when no UHID was read.

These run against the real database because the function IS the behaviour - a
reimplementation in Python would test the reimplementation. They skip when there is no
DATABASE_URL, so the rest of the suite still runs anywhere.

The invariant worth more than all the others: this function must never return confidence
1.0. Only an exact UHID may attach a document to a patient without a human.
"""

from __future__ import annotations

from decimal import Decimal

PRACTICE = 1
CALL = """
SELECT patient_id, matched_name, match_method, confidence, evidence
FROM   lab.fn_match_patient_by_demographics(%s, %s, %s, %s, %s)
"""


def _match(db, name, dob=None, age=None, sex=None, practice=PRACTICE):
    with db.cursor() as cur:
        cur.execute(CALL, (practice, name, dob, age, sex))
        return cur.fetchall()


def test_an_exact_name_shortlists_the_patient(db):
    rows = _match(db, "Devansh Choudhary")
    assert rows, "expected a candidate for a name that is in the seed verbatim"
    assert rows[0][1] == "Devansh Choudhary"


def test_confidence_never_reaches_certainty(db):
    """The whole point. Every candidate must quarantine, however good the evidence."""
    rows = _match(db, "Devansh Choudhary", dob="2010-03-14", sex="M")
    assert rows
    # Decimal, not float: the cap is exactly 0.95 and the nearest double to 0.95 sits
    # just below it, so a float comparison fails on a correct value.
    for row in rows:
        assert row[3] < 1, f"{row[1]} returned confidence {row[3]} - it must never reach 1.0"
        assert row[3] <= Decimal("0.95")


def test_a_matching_dob_scores_above_a_name_alone(db):
    name_only = _match(db, "Devansh Choudhary")[0][3]
    with_dob = _match(db, "Devansh Choudhary", dob="2010-03-14")[0][3]
    assert with_dob > name_only
    assert _match(db, "Devansh Choudhary", dob="2010-03-14")[0][2] == "name_dob"


def test_a_printed_age_is_weaker_evidence_than_a_dob(db):
    """A report prints age at collection, so it corroborates; it never confirms."""
    with_dob = _match(db, "Devansh Choudhary", dob="2010-03-14")[0][3]
    with_age = _match(db, "Devansh Choudhary", age="16 Y")[0][3]
    assert with_age > _match(db, "Devansh Choudhary")[0][3]
    assert with_age < with_dob
    assert _match(db, "Devansh Choudhary", age="16 Y")[0][2] == "name_age"


def test_a_contradicting_sex_disqualifies_the_candidate(db):
    """Two people share a name; one person does not change sex between requisition
    and report. A strong name score must not carry a contradiction through."""
    assert _match(db, "Devansh Choudhary", sex="M")
    assert _match(db, "Devansh Choudhary", sex="F") == []


def test_an_unknown_name_matches_nobody(db):
    assert _match(db, "Wilhelmina Fotheringay-Smythe") == []


def test_no_name_matches_nobody(db):
    """Age and sex alone cannot identify anyone - guessing would attach a stranger."""
    assert _match(db, "", age="16 Y", sex="M") == []
    assert _match(db, None, age="16 Y", sex="M") == []


def test_a_bare_surname_does_not_shortlist_everyone_who_shares_it(db):
    """The seed holds Devansh Choudhary and Ranjan Kumar Choudhary."""
    assert _match(db, "Choudhary") == []


def test_evidence_says_what_matched(db):
    """A reviewer needs to see why, not just a number."""
    evidence = _match(db, "Devansh Choudhary", dob="2010-03-14", sex="M")[0][4]
    assert evidence["dob"] == "exact"
    assert evidence["sex"] == "match"
    assert evidence["printed_name"] == "Devansh Choudhary"
    assert 0 < evidence["name_similarity"] <= 1


def test_another_practice_sees_nothing(db):
    """Practice scoping is the tenancy boundary and is not optional."""
    assert _match(db, "Devansh Choudhary", practice=999999) == []
