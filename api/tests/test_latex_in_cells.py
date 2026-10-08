r"""LaTeX an engine emitted for a superscript must not reach a clinical field.

OpenParser renders "x10^6/ul" as math: ``$ \times 10^{{6}}/ul $``. ``plain_text()``
already undid that for TEXT blocks, but table cells never went through it, so a real
report showed a unit of ``$ \times 10^{{6}}/ul $`` on screen and stored it against the
result.

Every fixture string here is a RAW literal on purpose. In a normal Python string
``"\times"`` is a TAB followed by "imes", so the fixture would contain no LaTeX at all
and every assertion below would pass while testing nothing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.ocr.base import RawBlock, RawDocument, RawPage
from app.services.ocr.pipeline import _unmath, build_extraction

TABLE = (
    "<table>"
    "<tr><td>TEST NAME</td><td>RESULT</td><td>UNIT</td><td>BIOLOGICAL REF RANGE</td></tr>"
    r"<tr><td>RBC Count</td><td>5.2</td><td>$ \times 10^{{6}}/ul $</td><td>3.5 - 5.2</td></tr>"
    "<tr><td>Haemoglobin</td><td>15.4</td><td>g%</td><td>13 - 18</td></tr>"
    "<tr><td>Platelet Count</td><td>2.12</td><td>Lakhs/cumm</td><td>1.5 - 4.5</td></tr>"
    # The differential rows carry "%", which IS in UNIT_LEXICON. Without them the
    # unit column scores below threshold and is typed UNKNOWN, units are dropped,
    # and the LaTeX never reaches a field - so the test would pass having exercised
    # nothing. This mirrors the real report, where the percentages are what let the
    # unit column be claimed at all.
    "<tr><td>Neutrophils</td><td>55</td><td>%</td><td>40 - 75</td></tr>"
    "<tr><td>Lymphocytes</td><td>40</td><td>%</td><td>20 - 40</td></tr>"
    "<tr><td>Eosinophils</td><td>03</td><td>%</td><td>0 - 6</td></tr>"
    "<tr><td>Monocytes</td><td>02</td><td>%</td><td>2 - 10</td></tr>"
    "</table>"
)


def test_the_fixture_really_contains_latex():
    """Guard the guard. If the escaping is wrong the fixture is already clean and
    the assertions below prove nothing - which is how this test first passed."""
    assert r"\times" in TABLE
    assert "$" in TABLE


def _doc(html: str) -> RawDocument:
    return RawDocument(
        source_path=Path("x.pdf"),
        engine="OPENPARSER",
        engine_version="v",
        pages=[
            RawPage(
                page_number=1,
                width=600.0,
                height=800.0,
                blocks=[RawBlock(label="table", content=html, order=0)],
            )
        ],
    )


def test_no_latex_reaches_any_clinical_field():
    """The invariant covers every field, not one column: whichever role the
    inference gives a cell, LaTeX must not be inside it."""
    rows = [r for s in build_extraction(_doc(TABLE)).sections for r in s.rows]
    assert rows, "expected rows to be extracted"
    for r in rows:
        for field in (
            r.raw_label,
            r.raw_value,
            r.raw_unit,
            r.raw_reference,
            r.raw_flag,
            r.raw_method,
        ):
            if not field:
                continue
            assert "\\times" not in field, f"LaTeX command survived: {field!r}"
            assert "$" not in field, f"math delimiter survived: {field!r}"
            assert "{" not in field, f"TeX brace survived: {field!r}"
            assert "}" not in field, f"TeX brace survived: {field!r}"


def test_the_latex_cell_actually_reaches_a_field():
    """Without this the suite can pass because the cell was dropped, not cleaned."""
    rows = [r for s in build_extraction(_doc(TABLE)).sections for r in s.rows]
    rbc = next(r for r in rows if r.raw_label and "RBC" in r.raw_label)
    assert rbc.raw_unit, "the unit column was not claimed - the fixture proves nothing"
    assert "10" in rbc.raw_unit
    assert "ul" in rbc.raw_unit.lower()


def test_the_exponent_survives_the_stripping():
    """10^6 and 10 differ by a factor of a million, which on an RBC count is the
    entire result. Removing the markup must not remove the magnitude."""
    assert _unmath(r"$ \times 10^{{6}}/ul $") == "10⁶/ul"
    assert _unmath(r"10^{9}/L") == "10⁹/L"
    assert _unmath("g%") == "g%"  # nothing to do, nothing done


@pytest.mark.parametrize(
    ("cell", "kept"),
    [
        # The three shapes in the 31 real occurrences across 15 corpus documents.
        (r"$ \mu g/dL $", "µg/dL"),
        (r"86  $ \mu g/dL $", "86 µg/dL"),
        (r"/ \mu L", "/ µL"),
        (r"\mu g/dL", "µg/dL"),
        # Plausible engine output not yet seen: glued to the dollar, or braced.
        (r"$\mu$g/dL", "µg/dL"),
        (r"\mu{}g/dL", "µg/dL"),
    ],
)
def test_the_micro_sign_survives_the_stripping(cell: str, kept: str) -> None:
    r"""Review B1. \mu was deleted as if it were formatting, so micrograms were
    stored as grams and platelets per microlitre as per litre - a factor of a
    million. The test above this one only checked that no TeX survived, which
    deleting the symbol satisfied perfectly. This one checks the meaning did."""
    assert _unmath(cell) == kept


def test_a_command_that_merely_starts_with_mu_is_not_a_micro_sign() -> None:
    assert "µ" not in _unmath(r"\multicolumn{2}{c}{x}")
