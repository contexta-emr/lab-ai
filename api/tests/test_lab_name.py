"""A run of header fields is not the name of a laboratory.

P01-R13 reported its lab as "Patient Name : Mahesh V. Deshpande Accession No :
AHL25-051869 Hospital No : SRV/207431 Sample Collected :" - the demographics strip,
taken whole. It passed because the lab-name fallback accepts any title containing a
lab word, and "Hospital No" contains one.
"""
from __future__ import annotations

from pathlib import Path

from app.services.ocr.base import RawBlock, RawDocument, RawPage
from app.services.ocr.pipeline import build_extraction

HEADER_STRIP = ("Patient Name : Mahesh V. Deshpande  Accession No : AHL25-051869  "
                "Hospital No : SRV/207431  Sample Collected : 14/03/2023")
REAL_LAB = "Kaveri Path Labs, 2nd Floor, Shivaji Chowk, Pune 411038"


def _doc(*titles: str) -> RawDocument:
    return RawDocument(
        source_path=Path("x.pdf"), engine="OPENPARSER", engine_version="v",
        pages=[RawPage(page_number=1, width=600.0, height=800.0,
                       blocks=[RawBlock(label="title", content=t, order=i)
                               for i, t in enumerate(titles)])],
    )


def test_a_header_strip_is_not_a_lab_name():
    header = build_extraction(_doc(HEADER_STRIP)).header
    assert header.lab_name is None, f"took the demographics strip as a lab: {header.lab_name!r}"


def test_a_real_lab_name_still_survives():
    """The fix must not cost the thing the fallback exists for."""
    header = build_extraction(_doc(REAL_LAB)).header
    assert header.lab_name == "Kaveri Path Labs"


def test_the_header_strip_is_not_discarded():
    """Rejecting it as a lab name must not throw it away - the patient is in there.

    Known limitation, deliberately asserted as it behaves rather than as it should:
    _key_values takes everything after the first colon as the value, so several
    fields printed on ONE line collapse into the first one. The patient is captured
    with the rest of the strip trailing behind it. Splitting a multi-field line is a
    separate piece of work; this test exists so that work has a failing assertion
    waiting for it.
    """
    header = build_extraction(_doc(HEADER_STRIP)).header
    assert header.patient_name is not None
    assert header.patient_name.startswith("Mahesh V. Deshpande")
