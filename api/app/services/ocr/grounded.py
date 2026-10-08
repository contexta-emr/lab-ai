"""Pass C - a grounded language-model read, for documents the grid passes lost.

WHAT THIS IS FOR
    Pass A reads HTML tables and Pass B (unbuilt) would read loose blocks by
    geometry. Both work by position, and position is exactly what a thermal
    till roll, a carbon copy and a screenshot destroy. On the 2026-09-23 run
    twenty-six of three hundred documents yielded nothing at all, and a further
    set gave back half their rows.

    This asks a model instead - but only for documents where the existing
    passes demonstrably failed, which `escalation_reason` decides.

GROUNDING IS THE WHOLE GUARANTEE
    The model is given numbered blocks and must name the block each value came
    from. A row whose cited block does not exist, or does not contain the text
    the model claims to have read, is DISCARDED. An invented potassium value
    points at no block and cannot survive the check.

    This is the LMDX technique, recorded in docs/extraction-strategy.md with
    its sources. Reported localisation accuracy is 88-94% zero-shot, which is
    why the check matters: roughly one in ten groundings is wrong even when the
    reading is right, and we would rather drop a real row than keep a fake one.

    Deliberately NOT using JSON mode. Constrained decoding costs 3-9 points of
    accuracy across open-weight models and one benchmark saw output validity
    FALL from 51% to 37% under structured output. Generate freely; the
    grounding check is the guarantee, not the schema.

WHAT CROSSES THE BOUNDARY
    Table-region blocks only. Header blocks - which carry the name, UHID, age,
    referring doctor, address and phone - are never sent, so there is nothing
    identifying to redact and no redaction rule to get wrong. Karthik's call of
    2026-10-08.

    This is the one case the PII design in ../VectorDB_Analysis explicitly
    permits. Its section 10 rules out sending the IMAGE to an external vision
    model, because you cannot redact a photograph before you have read it. Pass
    C runs after OCR, on text that already exists, so the header can simply be
    left behind.

    `select_blocks` is the control. If it cannot tell a block's region, the
    block is not sent. Fail closed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .base import RawBlock, RawDocument
from .contracts import Extraction
from .tables import is_annotation

__all__ = [
    "KEY_ENV",
    "Candidate",
    "escalation_reason",
    "select_blocks",
    "verify_grounding",
]

KEY_ENV = "ANTHROPIC_API_KEY"

# Block labels that can carry a result. Restricting to table labels alone was
# tried first and sent NOTHING on all 23 escalating documents: a thermal slip
# has no table blocks at all, which is precisely why the grid passes failed on
# it. Everything there is `text`, results and header alike.
#
# Everything outside this set is furniture - `doc_title` is the letterhead,
# `number` is "Page 1 of 1", figures and stamps carry no values - and is
# dropped without being examined.
PAYLOAD_LABELS = {"table", "table_caption", "table_footnote", "text"}

# A header block says "Patient Name" or "Age / Sex". Matching one keeps that
# block out of the request.
IDENTIFYING = re.compile(
    r"\b(patient|name|uhid|mrn|mr\.?\s*no|hosp(ital)?\s*(no|id)|"
    r"reg(istration)?\s*no|ip\s*no|op\s*no|age\s*/?\s*sex|sex\s*/?\s*age|"
    r"referr?ed|referring|doctor|dr\.|consultant|physician|"
    r"address|phone|mobile|tel|email|aadhaar|passport|"
    r"husband|wife|father|s/o|w/o|d/o)\b",
    re.IGNORECASE,
)

# Shapes that are identifying wherever they appear, with no label beside them:
# a phone number, an email, an Aadhaar-length digit run.
IDENTIFYING_SHAPE = re.compile(
    r"(\b[\w.+-]+@[\w-]+\.[\w.]+\b"            # email
    r"|\b(?:\+?91[\s-]?)?[6-9]\d{9}\b"          # Indian mobile
    r"|\b0\d{2,4}[\s-]\d{3,4}[\s-]?\d{3,4}\b"   # Indian landline, "0141 220 9100"
    r"|\b\d{4}\s?\d{4}\s?\d{4}\b)",             # Aadhaar
)


@dataclass(frozen=True)
class Candidate:
    """One block, as offered to the model.

    `ref` is what the model must cite. It is an index into the list we sent,
    not an engine id, so a model that invents "block_47" when we sent nine
    blocks fails the check rather than landing on something real by accident.
    """

    ref: str
    text: str
    page: int
    bbox: tuple[int, int, int, int] | None


def escalation_reason(extraction: Extraction, coverage=None) -> str | None:
    """Why this document needs Pass C, or None if the grid passes did their job.

    Two signals, both already computed elsewhere, per Karthik's call of
    2026-10-08:

    * the page yielded no rows at all - the thermal slips and the screenshots
    * a core member of a detected panel is missing - a partial read, which is
      the more dangerous case because the document looks fine until someone
      counts

    Deliberately NOT escalating on an unresolved label. A label we have no
    code for is usually a gap in the vocabulary rather than a failure to read,
    and sending those would fire on documents that are entirely correct.

    Args:
        extraction: What the grid passes produced.
        coverage: A coverage report, when one is available. Pass None to use
            the row-count signal alone - the caller inside the OCR worker has
            no database connection to build one with.

    Returns:
        A short reason for the log and the audit trail, or None.
    """
    rows = sum(len(section.rows) for section in extraction.sections)
    if rows == 0:
        return "no rows extracted"

    if coverage is not None:
        missing = [
            member.analyte_name or member.analyte_code
            for panel in getattr(coverage, "panels", [])
            for member in panel.members
            if getattr(member, "is_core", False) and not getattr(member, "found", False)
            and not getattr(member, "printed_label", None)
        ]
        if missing:
            shown = ", ".join(missing[:4])
            more = f" and {len(missing) - 4} more" if len(missing) > 4 else ""
            return f"core analyte not read: {shown}{more}"
    return None


def _looks_identifying(text: str) -> bool:
    """Whether a block carries patient or clinician identity.

    Erring towards True on purpose. Dropping a grid block costs us some rows on
    one escalated document; sending a UHID to a third party is a reportable
    event. The two mistakes are not the same size.
    """
    text = text or ""
    return bool(IDENTIFYING.search(text) or IDENTIFYING_SHAPE.search(text))


def select_blocks(raw: RawDocument, *, limit: int = 120) -> list[Candidate]:
    """The blocks that may leave this machine, numbered for citation.

    Table-region blocks only, minus anything that reads like a header line.
    A block whose label the engine did not give us is NOT sent: an unclassified
    block might be the letterhead, and the control only works if unknown means
    no.

    Args:
        raw: The engine's output, as recorded in bench/results/*.raw.json.
        limit: Most blocks to send. A document with more than this has
            something wrong with it that a bigger prompt will not fix.
    """
    out: list[Candidate] = []
    for page in raw.pages:
        # These engines emit a header as two blocks in reading order - the label
        # "Hospital No" and then the value "MCH/226104" - and only the first
        # carries a word any keyword list can match. So a block that FOLLOWS an
        # identifying one is withheld too. On the 23 escalating documents that
        # rule withholds 58 blocks the keywords alone let through, which is very
        # nearly the whole patient identity on each page.
        previous_was_identifying = False
        for block in page.blocks:
            if len(out) >= limit:
                return out
            text = (block.content or "").strip()
            if not text:
                continue

            identifying = _looks_identifying(text)
            label = (block.label or "").strip().lower()
            sendable = (
                label in PAYLOAD_LABELS
                and not identifying
                and not previous_was_identifying
                and not is_annotation(text)
            )
            # Set before the continue, and from THIS block's own verdict, so a
            # dropped identifying block still shields the one after it.
            previous_was_identifying = identifying

            if not sendable:
                continue
            out.append(Candidate(
                ref=f"b{len(out)}",
                text=text,
                page=page.page_number,
                bbox=_quantise(block, page),
            ))
    return out


def _quantise(block: RawBlock, page) -> tuple[int, int, int, int] | None:
    """The block's box as integers 0-999, the LMDX coordinate scheme.

    Normalised to the page so one prompt can carry blocks from pages of
    different sizes, and coarse because the model needs relative position, not
    typographic precision.
    """
    if not block.bbox or not page.width or not page.height:
        return None
    x0, y0, x1, y1 = block.bbox
    scale = lambda v, size: max(0, min(999, int(v / size * 999)))  # noqa: E731
    return (scale(x0, page.width), scale(y0, page.height),
            scale(x1, page.width), scale(y1, page.height))


def _norm(text: str) -> str:
    """Loose comparison for the grounding check - case and spacing only."""
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def verify_grounding(rows: list[dict], sent: list[Candidate]) -> tuple[list[dict], list[dict]]:
    """Split returned rows into those their cited block supports, and the rest.

    A row survives when the block it cites was actually sent AND that block
    contains both the label and the value as substrings. The second half is the
    part that matters: a model that cites a real block but invents the number
    inside it passes a reference check and fails this one.

    Returns:
        ``(kept, rejected)``. Rejected rows carry a ``reject`` key saying which
        test they failed, because the rejection rate is the measurement that
        says whether this pass is worth its money.
    """
    by_ref = {candidate.ref: candidate for candidate in sent}
    kept: list[dict] = []
    rejected: list[dict] = []

    for row in rows:
        ref = str(row.get("ref") or "")
        label = str(row.get("label") or "").strip()
        value = row.get("value")
        value = "" if value is None else str(value).strip()

        block = by_ref.get(ref)
        if block is None:
            rejected.append({**row, "reject": f"cites {ref or '(nothing)'}, which was not sent"})
            continue
        if not label:
            rejected.append({**row, "reject": "no label"})
            continue

        haystack = _norm(block.text)
        if _norm(label) not in haystack:
            rejected.append({**row, "reject": "label is not in the block it cites"})
            continue
        if value and _norm(value) not in haystack:
            rejected.append({**row, "reject": "value is not in the block it cites"})
            continue
        kept.append(row)

    return kept, rejected
