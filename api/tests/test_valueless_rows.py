"""A row with no value is stored only when its label names a test we know (migration 039).

Real reports print a sex- or age-banded range on the lines under a test:

    APOLIPOPROTEIN - A1      124   mg/dL
    Male : 86 - 152
    Female : 94 - 162

Each band line came through as a row of its own, with no value - 149 such rows
over twelve real reports (2026-10-28), cluttering the review screen and holding
every one of those documents out of "confirm all". Dropping every row with no
value was measured and rejected: it also deleted 28 printed tests whose number
we had failed to read, the holes a reviewer most needs to see. The rule kept is
the narrower one: no value AND a label the analyte resolver does not know.
"""

from __future__ import annotations

import json


def _ingest(db_write, results: list[dict], *more_sections: dict) -> int:
    practice = db_write.execute("SELECT id FROM core.practices ORDER BY id LIMIT 1").fetchone()[
        0
    ]
    sections = [{"heading_printed": "Lipid Profile", "results": results}, *more_sections]
    payload = {
        "source": "emr_upload",
        "checksum_sha256": "f" * 64,
        "page_count": 1,
        "reports": [{"sections": sections}],
    }
    return db_write.execute(
        "SELECT lab.fn_ingest_lab_document(%s, %s::jsonb)", (practice, json.dumps(payload))
    ).fetchone()[0]


def _stored(db_write, doc_id: int) -> list[str]:
    rows = db_write.execute(
        "SELECT printed_label FROM lab.results WHERE document_id = %s ORDER BY sequence",
        (doc_id,),
    ).fetchall()
    return [r[0] for r in rows]


BANDED = [
    {"printed_label": "Apolipoprotein A1", "value_text": "124", "sequence": 1},
    {"printed_label": "Male : 86 - 152", "value_text": "", "sequence": 2},
    {"printed_label": "Female : 94 - 162", "value_text": "", "sequence": 3},
    {"printed_label": "RBC Count", "value_text": "", "sequence": 4},
]


def test_a_range_band_line_with_no_value_is_not_stored(db_write) -> None:
    stored = _stored(db_write, _ingest(db_write, BANDED))
    assert "Male : 86 - 152" not in stored
    assert "Female : 94 - 162" not in stored


def test_a_known_test_whose_value_was_not_read_is_still_stored(db_write) -> None:
    # The hole a reviewer has to see: printed on the page, number not read.
    assert "RBC Count" in _stored(db_write, _ingest(db_write, BANDED))


# Labels arrive with the engine's line breaks escaped - a backslash and an "n", never a
# real newline (56 of 852 stored rows on real reports, 2026-10-29) - so these are too.
URINE_COLOUR = r"COLOUR\n( Specimen: URINE. )"
BILIRUBIN_RUN_ON = r"Total Bilirubin\n0.78 mg/dL\n0.3 - 1.2"


def test_a_known_test_with_its_specimen_line_stuck_to_the_name_is_still_stored(
    db_write,
) -> None:
    # The whole label resolves to nothing; up to its bracket it is plainly a urine test.
    urine = {
        "heading_printed": "Urine Routine Examination",
        "results": [{"printed_label": URINE_COLOUR, "value_text": "", "sequence": 1}],
    }
    assert URINE_COLOUR in _stored(db_write, _ingest(db_write, BANDED, urine))


def test_a_known_test_whose_row_ran_into_its_name_is_still_stored(db_write) -> None:
    # Value, unit and range glued onto the name after escaped line breaks, no bracket:
    # its first line is still the test, and the reviewer has to see the row.
    liver = {
        "heading_printed": "Liver Function Test",
        "results": [{"printed_label": BILIRUBIN_RUN_ON, "value_text": "", "sequence": 1}],
    }
    assert BILIRUBIN_RUN_ON in _stored(db_write, _ingest(db_write, BANDED, liver))


def test_an_unknown_test_with_a_value_is_still_stored(db_write) -> None:
    # A value is a result whatever it is called; an unknown name only means no code.
    assert "Apolipoprotein A1" in _stored(db_write, _ingest(db_write, BANDED))


def test_a_section_left_with_no_rows_is_not_stored(db_write) -> None:
    # Its heading would still list a panel on the patient's timeline with nothing under it.
    bands_only = {
        "heading_printed": "Apolipoprotein B",
        "results": [{"printed_label": "Male : 56 - 145", "value_text": "", "sequence": 1}],
    }
    doc_id = _ingest(db_write, BANDED, bands_only)
    headings = db_write.execute(
        "SELECT s.heading_printed FROM lab.report_sections s"
        " JOIN lab.reports r ON r.id = s.report_id WHERE r.document_id = %s",
        (doc_id,),
    ).fetchall()
    assert [h[0] for h in headings] == ["Lipid Profile"]


def test_a_dropped_line_is_not_logged_as_an_unmatched_label(db_write) -> None:
    # lab.unmatched_labels is the list the master grows from; a band line is not a test.
    def seen() -> int:
        return db_write.execute(
            "SELECT COALESCE(sum(occurrence_count), 0) FROM lab.unmatched_labels"
            " WHERE printed_label = %s",
            ("Male : 86 - 152",),
        ).fetchone()[0]

    before = seen()
    _ingest(db_write, BANDED)
    assert seen() == before
