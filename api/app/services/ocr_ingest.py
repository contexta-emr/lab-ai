"""Extraction to the payload lab.fn_ingest_lab_document expects.

This file contains no reading logic. Every decision about what a page says -
which block is a heading, which column is the value, where the patient id is
printed, what a reference range looks like - is made by app/services/ocr/,
the pipeline from the idp workspace. This is the rename between its output
contract and the database's input contract, and nothing else.

WHY THERE IS NOTHING ELSE HERE
    There used to be. A hand-written adapter read the tables itself, and it
    silently dropped four things build_extraction does:

        _header_rows     pulls key/value pairs OUT of a table. On a real lab
                         report "Patient ID | SRV/207431" is a table row, not
                         a paragraph. The old adapter handed that row to the
                         result reader as though it were a test, and the UHID
                         was lost on every document.
        plain_text       strips the HTML an engine leaves in a text block, so
                         the key/value patterns can see the text at all.
        centred_heading  finds the panel name in a centred div. idp's own
                         note: "the single most reliable signal there is for
                         what a report contains", and every document in their
                         corpus carried one.
        split_sections   splits one HTML table at full-width heading rows, so
                         a table's own header row does not become the section
                         title. Without it sections came out named
                         "INVESTIGATION" and "RESULT BIOLOGICAL REFERENCE
                         INTERVAL".

    Those four are why the review console showed "Unnamed lab / no UHID read"
    over documents OpenParser had read perfectly well.

    The adapter was kept for a while because it scored higher on the
    synthetic corpus. That corpus is 300 PDFs from one producer; the reader it
    favoured found 0 of 13 patient ids on real vendor reports. A corpus score
    is now used to catch regressions and never to choose an approach.

THE CONTRACT LINES UP BECAUSE IT WAS DESIGNED TO
    Section.printed_title is documented over there as "the panel hint passed
    to fn_resolve_panel later - never a panel code". Row carries raw_label,
    raw_value, raw_unit, raw_reference, raw_flag, raw_method. Extraction is
    open-vocabulary by construction: no analyte codes anywhere, because
    resolution is a separate pass that is allowed to fail. That is the same
    division this schema was built around.

        Row.raw_label          -> printed_label
        Row.raw_value          -> value_text
        Row.raw_unit           -> unit_printed
        Row.raw_reference      -> reference_printed
        Row.raw_flag           -> flag
        Row.raw_method         -> method_printed
        Section.printed_title  -> heading_printed
        Header.patient_id      -> uhid_printed      the UHID matcher's input
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.services.ocr.contracts import Extraction
from app.services.ocr.numbers import is_numeric
from app.services.ocr.outputs import write_extraction, write_raw
from app.services.ocr.pipeline import _is_only_a_key, build_extraction
from app.services.ocr.tables import is_annotation

logger = logging.getLogger(__name__)

#: What lab.documents.ocr_engine holds. A small vocabulary, because it is what
#: the scoring table groups on and what traces a result back to how it was read.
ENGINE_KEYS = {
    "openparser": "openparser",
    "paddleocrvl": "paddle_vl",
    "paddle": "paddle_vl",
    "textlayer": "pdf-text",
    "pdfplumber": "pdf-text",
}


def engine_key(engine: str) -> str:
    name = (engine or "").strip().lower().replace("-", "").replace("_", "")
    for needle, key in ENGINE_KEYS.items():
        if needle in name:
            return key
    return name[:30] or "unknown"


def payload_from_extraction(
    ex: Extraction,
    *,
    checksum: str,
    visit_attachment_id: int | None = None,
    source: str = "emr_upload",
) -> dict:
    """One Extraction to one ingest payload. A rename, not a translation."""
    sections: list[dict] = []
    for section in ex.sections:
        results = []
        for row in section.rows:
            label = (row.raw_label or "").strip()
            value = (row.raw_value or "").strip()
            if not label:
                continue
            # A row with no value AND a label that is not a test name is not a
            # result at all: it is a header field or a footer that landed in
            # the grid. "Age / Sex", "Referred By", "Tested by: M. Shaikh".
            #
            # Both tests come from vocabulary this codebase already keeps for
            # those exact purposes - the header keys the field extractor
            # promotes, and the annotation prefixes split_sections refuses to
            # treat as headings. Nothing here is a list of strings seen in one
            # corpus.
            #
            # Only when there is no value. A row carrying a number is a result
            # whatever it is called, and dropping one because its label looked
            # administrative is how a real reading disappears.
            if not value and (_is_only_a_key(label) or is_annotation(label)):
                continue
            # A row with a label and NO value is kept, not dropped.
            #
            # It is a different fact from a row that is absent, and only one of
            # them is our bug: absent means the lab did not run the test, no
            # value means the test is printed on the page and we failed to read
            # its number. Dropping them made those two indistinguishable and
            # made our row count disagree with the engine's - idp's own
            # reference outputs keep every row, which is why their screen says
            # "19 rows read" where ours said 16.
            #
            # It cannot become a false reading: value_numeric stays NULL, so it
            # never reaches a chart, and lab.v_results_verified is what any
            # clinical read touches. The review screen shows it as "printed but
            # no value read" and a human fills it in or removes it.
            results.append(
                {
                    "printed_label": label[:255],
                    # Empty string, not NULL: the column is NOT NULL because every
                    # row of a lab report has a printed value position, even when
                    # nothing was read out of it.
                    "value_text": value[:255],
                    "unit_printed": _clip(row.raw_unit, 40),
                    "reference_printed": _clip(row.raw_reference, 160),
                    "method_printed": _clip(row.raw_method, 160),
                    "flag": _flag(row.raw_flag),
                    "is_text_result": not is_numeric(value),
                    "sequence": len(results) + 1,
                }
            )
        if results:
            sections.append(
                {
                    "heading_printed": _clip(section.printed_title, 255),
                    "results": results,
                }
            )

    head = ex.header
    n_results = sum(len(s["results"]) for s in sections)

    # Confidence is a statement about this parse, not a decoration. No patient
    # identifier or no rows means a reviewer should look before any of it is
    # treated as clinical fact.
    confidence = 0.9
    if not head.patient_id:
        confidence -= 0.35
    if not n_results:
        confidence -= 0.4
    elif n_results < 4:
        confidence -= 0.15

    return {
        "source": source,
        "visit_attachment_id": visit_attachment_id,
        "checksum_sha256": checksum,
        "page_count": ex.document.page_count or 1,
        "has_text_layer": engine_key(ex.document.engine) == "pdf-text",
        "ocr_engine": engine_key(ex.document.engine),
        "engine_version": ex.document.engine_version or "",
        "extraction_confidence": round(max(confidence, 0.05), 4),
        "reports": [
            {
                "lab_name": _clip(head.lab_name, 255),
                "accession_no": _clip(head.lab_reference_no, 60),
                "uhid_printed": _clip(head.patient_id, 20),
                "uhid_label_printed": "UHID" if head.patient_id else None,
                "patient_name_printed": _clip(head.patient_name, 255),
                "age_printed": _clip(head.patient_age, 20),
                "sex_printed": _clip(head.patient_sex, 10),
                "collected_text": _clip(head.collected_at, 60),
                # The parsed form as well as the printed one. Every longitudinal
                # query orders by collection date, and a result with no date
                # cannot sit on a trend line at all - which is how a document
                # that extracted perfectly still produced an unusable chart.
                "collected_at": getattr(head, "collected_at_iso", None),
                "reported_at": getattr(head, "reported_at_iso", None),
                "referring_doctor": _clip(head.referring_doctor, 255),
                "layout_hint": engine_key(ex.document.engine),
                "sections": sections,
                "notes": [],
            }
        ],
    }


def extract_with(
    engine,
    path: Path,
    *,
    checksum: str,
    visit_attachment_id: int | None = None,
    source: str = "emr_upload",
    dump_dir: Path | None = None,
    dump_name: str | None = None,
    escalate=None,
) -> dict:
    """Run one engine over one file and return the ingest payload.

    With ``dump_dir``, also writes the pair the idp workspace writes - the
    engine's blocks verbatim and the extraction built from them, both named
    after the source document. ``dump_name`` overrides the name when the file
    on disk is not called what the document is called, which is the normal
    case here: storage holds P01-R05.pdf under its checksum.

    The raw dump is the expensive half to reproduce and the cheap half to
    replay. Once it exists, a pipeline change is measured against the whole
    corpus in seconds rather than forty minutes and another bill.

    ``escalate`` is Pass C's hook: ``(raw, extraction) -> extraction``. Left
    None, nothing is escalated and no third party is contacted, which is what
    every caller outside the worker wants.
    """
    raw = engine.extract(path)
    extraction = build_extraction(raw)
    # Pass C, when the caller supplies one. Called with both the engine's
    # blocks and what the grid passes made of them, because deciding whether to
    # escalate needs the second and doing it needs the first. The policy - when
    # to fire, what may be sent, which model - lives in the worker, so this
    # module keeps knowing nothing about keys or third parties.
    if escalate is not None:
        extraction = escalate(raw, extraction) or extraction
    if dump_dir is not None:
        named = Path(dump_name or path.name)
        try:
            write_raw(raw, Path(dump_dir), named)
            write_extraction(extraction, Path(dump_dir), named, engine=raw.engine)
        except OSError as exc:
            # Never fatal. Losing a document because its dump could not be
            # written would be the worse trade.
            logger.warning("no dump for %s: %s", named.stem, exc)
    return payload_from_extraction(
        extraction,
        checksum=checksum,
        visit_attachment_id=visit_attachment_id,
        source=source,
    )


def _clip(value, length: int) -> str | None:
    text = value.strip() if isinstance(value, str) else None
    return text[:length] if text else None


# The six values lab.results.flag allows, and the spellings a report prints
# for them. High/Low as words, the arrows, and the asterisk that conventionally
# marks an out-of-range value.
# One line per canonical flag, carrying every spelling that maps to it.
# fmt: off
_FLAGS = {
    "H": "H",   "HIGH": "H",  "↑": "H",
    "L": "L",   "LOW": "L",   "↓": "L",
    "HH": "HH", "↑↑": "HH",
    "LL": "LL", "↓↓": "LL",
    "A": "A",   "ABNORMAL": "A", "*": "A", "**": "A",
    "N": "N",   "NORMAL": "N",
}
# fmt: on


def _flag(value) -> str | None:
    """One of the six the column allows, or nothing.

    A flag is a closed domain, not a short string, so it is validated rather
    than truncated. _clip(.., 4) was neither: a column misread as the flag
    column holds prose, and prose cut to four characters is not a flag and not
    a length error either - it is a CHECK violation that aborts the insert and
    loses the whole document. Four reports died that way before this existed,
    each after three OpenParser calls.

    Unrecognised is NULL, the same rule as an unknown analyte code and for the
    same reason: the six are what the column means, and a value outside them
    is something we did not understand rather than something to force in.
    """
    if not isinstance(value, str):
        return None
    return _FLAGS.get(value.strip().upper())
