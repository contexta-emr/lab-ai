"""The document says whether Pass B helped read it (review B28).

grounded.merge() marks the engine "+grounded" when the language model added
rows, and engine_key() used to strip it on the way into lab.documents, so no
stored document could ever say it was read with help - the review screen could
not show it and the benchmark's "with Pass B rows" counter was always 0.
"""

from __future__ import annotations

from app.services.ocr.outputs import read_raw
from app.services.ocr.pipeline import build_extraction
from app.services.ocr_ingest import payload_from_extraction
from tests import conftest


def _extraction():
    return build_extraction(read_raw(conftest.RESULTS / "P05-R02.OPENPARSER.raw.json"))


def test_a_document_pass_b_helped_says_so() -> None:
    ex = _extraction()
    ex.document.engine = f"{ex.document.engine}+grounded"  # what merge() leaves
    assert payload_from_extraction(ex, checksum="0" * 64)["ocr_engine"] == "openparser+grounded"


def test_a_document_pass_a_read_alone_is_just_the_engine() -> None:
    assert (
        payload_from_extraction(_extraction(), checksum="0" * 64)["ocr_engine"] == "openparser"
    )
