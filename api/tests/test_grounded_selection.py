"""What may leave the machine, and what a grounded answer must prove.

These are the safety tests for Pass C. `select_blocks` is the only thing
standing between a patient's UHID and a third-party API, and `verify_grounding`
is the only thing standing between a hallucinated potassium value and a
patient's chart. Both are pinned here rather than trusted.

The identity cases are written against a real thermal slip in the corpus
(P05-R08), because the reason the deny-list needs a follows-a-label rule at all
is a structure no hand-written fixture would have suggested: these engines emit
"Hospital No" and "MCH/226104" as two separate blocks, and only the first
contains a word any keyword list can match.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.ocr.base import RawBlock, RawDocument, RawPage
from app.services.ocr.contracts import DocumentMeta, Extraction, Row, Section
from app.services.ocr.grounded import (
    Candidate,
    escalation_reason,
    select_blocks,
    verify_grounding,
)


def _doc(*blocks: tuple[str, str]) -> RawDocument:
    """A one-page document from (label, content) pairs, in reading order."""
    return RawDocument(
        source_path=Path("x.pdf"),
        engine="TEST",
        engine_version="0",
        pages=[
            RawPage(
                page_number=1,
                width=1000,
                height=1000,
                blocks=[
                    RawBlock(
                        label=label,
                        content=content,
                        bbox=(0, i * 10, 100, i * 10 + 9),
                        order=i,
                        score=1.0,
                    )
                    for i, (label, content) in enumerate(blocks)
                ],
            )
        ],
    )


def _extraction(row_count: int) -> Extraction:
    rows = [Row(row_index=i, raw_label=f"T{i}", raw_value=str(i)) for i in range(row_count)]
    return Extraction(
        document=DocumentMeta(engine="TEST", engine_version="0", source_name="x.pdf"),
        sections=[Section(printed_title="S", rows=rows)] if rows else [],
    )


# --------------------------------------------------------------- escalation
def test_a_document_with_no_rows_escalates():
    assert escalation_reason(_extraction(0)) == "no rows extracted"


def test_a_document_that_read_fine_does_not_escalate():
    assert escalation_reason(_extraction(12)) is None


def _coverage(name: str, *, is_core: bool) -> SimpleNamespace:
    """A coverage report holding one panel with one member nobody read."""
    member = SimpleNamespace(
        analyte_name=name, analyte_code=name, is_core=is_core, found=False, printed_label=None
    )
    return SimpleNamespace(panels=[SimpleNamespace(members=[member])])


def test_a_missing_core_analyte_escalates_even_though_rows_were_read():
    """The dangerous case: the page looks fine until someone counts."""
    reason = escalation_reason(_extraction(6), _coverage("LDL Cholesterol", is_core=True))
    assert reason is not None
    assert "LDL Cholesterol" in reason


def test_an_unread_optional_analyte_does_not_escalate():
    """A test the lab did not run is routine, not a failure to read."""
    assert escalation_reason(_extraction(6), _coverage("Non-HDL", is_core=False)) is None


# ------------------------------------------------------------------ selection
def test_the_header_of_a_real_thermal_slip_does_not_leave_the_machine():
    """P05-R08's shape: label and value as separate consecutive blocks."""
    raw = _doc(
        ("doc_title", "Maharana Childrens Hospital Laboratory"),
        ("text", "Jaipur 0141 220 9100"),
        ("text", "Patient Name"),
        ("text", "Devansh Choudhary"),
        ("text", "Hospital No"),
        ("text", "MCH/226104"),
        ("text", "Age / Sex"),
        ("text", "13 Y / M"),
        ("text", "Referred By"),
        ("text", "Dr. Anand Joshi, MBBS, MD"),
        ("text", "Plt Count"),
        ("text", "96000 /uL L"),
        ("number", "Page 1 of 1"),
    )
    sent = " | ".join(c.text for c in select_blocks(raw))

    for identity in (
        "Devansh Choudhary",
        "MCH/226104",
        "13 Y / M",
        "Anand Joshi",
        "0141 220 9100",
        "Maharana Childrens Hospital",
    ):
        assert identity not in sent, f"{identity!r} must not leave the machine"

    # ...and the payload still does, or the pass has nothing to work with.
    assert "Plt Count" in sent
    assert "96000 /uL L" in sent


def test_payload_that_resembles_a_header_is_still_sent():
    """Reference ranges and collection times are payload, not identity."""
    raw = _doc(
        ("text", "Haemoglobin"),
        ("text", "13.2 g/dL"),
        ("text", "4.5 - 5.5"),
        ("text", "16/09/2023 8:20 AM"),
    )
    sent = [c.text for c in select_blocks(raw)]
    assert sent == ["Haemoglobin", "13.2 g/dL", "4.5 - 5.5", "16/09/2023 8:20 AM"]


def test_furniture_labels_are_dropped_without_being_read():
    raw = _doc(("image", "signature"), ("number", "Page 2 of 3"), ("text", "Urea 24 mg/dL"))
    assert [c.text for c in select_blocks(raw)] == ["Urea 24 mg/dL"]


def test_refs_are_indices_into_what_we_sent():
    """So a model citing b9 when nine blocks were sent fails rather than
    landing on something real by accident."""
    raw = _doc(("text", "A 1"), ("text", "Patient Name"), ("text", "Hidden"), ("text", "B 2"))
    sent = select_blocks(raw)
    assert [c.ref for c in sent] == ["b0", "b1"]
    assert [c.text for c in sent] == ["A 1", "B 2"]


def test_the_limit_is_honoured():
    raw = _doc(*[("text", f"Test{i} {i} mg/dL") for i in range(50)])
    assert len(select_blocks(raw, limit=10)) == 10


# ---------------------------------------------------------------- grounding
@pytest.fixture
def sent() -> list[Candidate]:
    return [
        Candidate(ref="b0", text="Plt Count", page=1, bbox=(0, 0, 10, 10)),
        Candidate(ref="b1", text="96000 /uL L", page=1, bbox=(0, 20, 10, 30)),
        Candidate(ref="b2", text="Haemoglobin 13.2 g/dL", page=1, bbox=(0, 40, 10, 50)),
    ]


def test_a_row_whose_block_contains_both_halves_is_kept(sent):
    kept, rejected = verify_grounding(
        [{"label_ref": "b2", "value_ref": "b2", "label": "Haemoglobin", "value": "13.2"}], sent
    )
    assert len(kept) == 1
    assert rejected == []


def test_an_invented_value_is_discarded(sent):
    """The whole point. The block is real; the number is not in it."""
    kept, rejected = verify_grounding(
        [{"label_ref": "b2", "value_ref": "b2", "label": "Haemoglobin", "value": "9.9"}], sent
    )
    assert kept == []
    assert "value is not in the block" in rejected[0]["reject"]


def test_a_row_citing_a_block_we_never_sent_is_discarded(sent):
    kept, rejected = verify_grounding(
        [{"label_ref": "b9", "value_ref": "b9", "label": "Potassium", "value": "4.1"}], sent
    )
    assert kept == []
    assert "not sent" in rejected[0]["reject"]


def test_a_row_citing_nothing_is_discarded(sent):
    kept, rejected = verify_grounding([{"label": "Potassium", "value": "4.1"}], sent)
    assert kept == []
    assert rejected[0]["reject"].startswith("cites")


def test_a_label_from_a_different_block_is_discarded(sent):
    """Grounding is per row, not per document - citing SOME block we sent is
    not enough."""
    kept, rejected = verify_grounding(
        [{"label_ref": "b2", "value_ref": "b2", "label": "Plt Count", "value": "13.2"}], sent
    )
    assert kept == []
    assert "label is not in the block" in rejected[0]["reject"]


def test_a_text_result_with_no_value_grounds_on_its_label(sent):
    kept, _ = verify_grounding(
        [{"label_ref": "b0", "value_ref": "b0", "label": "Plt Count", "value": None}], sent
    )
    assert len(kept) == 1


def test_grounding_ignores_case_and_punctuation(sent):
    kept, rejected = verify_grounding(
        [{"label_ref": "b2", "value_ref": "b2", "label": "haemoglobin", "value": "13.2"}], sent
    )
    assert len(kept) == 1
    assert rejected == []


# ------------------------------------------------------------------- the call
def test_the_prompt_carries_refs_and_position():
    """Position is most of what separates a label from its value on a page with
    no table structure - and the one thing the grid passes could not use."""
    from app.services.ocr.grounded import render_prompt

    text = render_prompt(
        [
            Candidate(ref="b0", text="Plt Count", page=1, bbox=(10, 20, 30, 40)),
            Candidate(ref="b1", text="96000 /uL L", page=2, bbox=None),
        ]
    )
    assert text.splitlines() == ["b0 @1:10,20,30,40 Plt Count", "b1 @2 96000 /uL L"]


def test_a_reply_parses_into_rows_and_ignores_anything_else():
    from app.services.ocr.grounded import parse_reply

    rows = parse_reply(
        "Here are the results:\n"
        "b0 | b1 | Plt Count | 96000 | /uL | L\n"
        "not a row at all\n"
        "b2 | b2 | Haemoglobin | 13.2 ||\n"
        "b3 | b4 | | 5 | |\n"  # no label, not a row
    )
    assert [r["label_ref"] for r in rows] == ["b0", "b2"]
    assert rows[0] == {
        "label_ref": "b0",
        "value_ref": "b1",
        "label": "Plt Count",
        "value": "96000",
        "unit": "/uL",
        "flag": "L",
    }
    assert rows[1]["unit"] is None
    assert rows[1]["flag"] is None


def test_a_row_with_no_value_ref_falls_back_to_the_label_block():
    """Rather than inventing one, so the grounding check still has something
    real to test against."""
    from app.services.ocr.grounded import parse_reply

    rows = parse_reply("b4 | | Peripheral Smear | Normocytic | |")
    assert rows[0]["label_ref"] == "b4"
    assert rows[0]["value_ref"] == "b4"


def test_a_malformed_reply_yields_nothing_rather_than_guessing():
    from app.services.ocr.grounded import parse_reply

    assert parse_reply("I could not read this document.") == []
    assert parse_reply("") == []


def test_no_key_is_a_skip_with_a_message_that_says_where_to_put_one():
    """Never fatal: a document that could not be escalated keeps whatever the
    grid passes got, which is where it already was."""
    from app.services.ocr.grounded import GroundedPass, GroundedUnavailableError

    pass_c = GroundedPass(key="")
    assert pass_c.configured is False
    with pytest.raises(GroundedUnavailableError, match="ANTHROPIC_API_KEY"):
        pass_c.read([Candidate(ref="b0", text="x", page=1, bbox=None)])


def test_no_candidates_is_not_an_api_call():
    """A document with nothing sendable must not spend money finding that out."""
    from app.services.ocr.grounded import GroundedPass

    assert GroundedPass(key="").read([]) == ([], [])


def test_a_label_and_value_in_separate_blocks_grounds(sent):
    """The thermal-slip shape, and the case the first grounding rule got wrong:
    "Plt Count" and "96000 /uL L" are consecutive blocks, and citing each half
    to its own block is correct attribution, not a weaker check."""
    kept, rejected = verify_grounding(
        [{"label_ref": "b0", "value_ref": "b1", "label": "Plt Count", "value": "96000"}], sent
    )
    assert len(kept) == 1
    assert rejected == []


def test_a_value_cited_to_an_unsent_block_is_still_discarded(sent):
    kept, rejected = verify_grounding(
        [{"label_ref": "b0", "value_ref": "b7", "label": "Plt Count", "value": "96000"}], sent
    )
    assert kept == []
    assert "for the value, which was not sent" in rejected[0]["reject"]


def test_a_value_from_the_wrong_block_is_still_discarded(sent):
    """Grounding each half separately must not let a value borrow another
    test's number."""
    kept, rejected = verify_grounding(
        [{"label_ref": "b0", "value_ref": "b2", "label": "Plt Count", "value": "96000"}], sent
    )
    assert kept == []
    assert "value is not in the block" in rejected[0]["reject"]
