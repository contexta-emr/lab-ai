# api/tests/test_thermal_slip_extraction.py
"""A thermal slip must yield a patient and rows that carry values."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.ocr.base import RawBlock, RawDocument, RawPage
from app.services.ocr.pipeline import build_extraction


def _document(blocks: list[dict]) -> RawDocument:
    """Rebuild a RawDocument from a recorded dump.

    Field names are exactly base.py's: RawDocument takes ``source_path`` (a Path),
    and RawBlock takes ``label``/``content`` positionally with bbox, order and score
    optional. bbox is a 4-tuple, not the list JSON stores it as.
    """
    return RawDocument(
        source_path=Path("test.pdf"),
        engine="OPENPARSER",
        engine_version="paddleocr-vl-1.6",
        pages=[
            RawPage(
                page_number=1,
                width=455.0,
                height=1684.0,
                blocks=[
                    RawBlock(
                        label=b["label"],
                        content=b["content"],
                        bbox=tuple(b["bbox"]) if b.get("bbox") else None,
                        order=b.get("order"),
                        score=b.get("score"),
                    )
                    for b in blocks
                ],
            )
        ],
    )


@pytest.mark.xfail(
    strict=True,
    reason="_header_rows promotes a table only when every filled row pairs, and a folded "
           "2-cell row yields one pair, so the len(pairs) >= 2 fallback never fires; "
           "'Report Released' and 'Specimen' are also absent from _HEADER_KEYS. "
           "Unblocked by Task 5 (header vocabulary).",
)
def test_header_fields_are_recovered(cached_blocks):
    """The UHID is why this matters: patient matching reads exactly this field."""
    extraction = build_extraction(_document(cached_blocks("P05-R02")))
    assert extraction.header.patient_name == "Devansh Choudhary"
    assert extraction.header.patient_id == "MCH/226104"


def test_patient_name_is_not_a_result_row(cached_blocks):
    extraction = build_extraction(_document(cached_blocks("P05-R02")))
    labels = [r.raw_label for s in extraction.sections for r in s.rows]
    assert "Devansh Choudhary" not in labels


@pytest.mark.xfail(
    strict=True,
    reason="infer_roles types a value column UNKNOWN when the unit is glued to the value "
           "('12.9 g/dL'), so no value column is recognised. Pre-existing, unrelated to "
           "folding, and deferred to the value-accuracy work in spec section 8.",
)
def test_result_rows_carry_values(cached_blocks):
    extraction = build_extraction(_document(cached_blocks("P05-R02")))
    rows = [r for s in extraction.sections for r in s.rows]
    assert rows, "expected result rows"
    assert any(r.raw_value for r in rows), "every row came back valueless"
