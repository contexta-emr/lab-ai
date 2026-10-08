"""Pass B - a grounded language-model read, for documents Pass A lost.

WHY IT IS PASS B
    Pass A reads HTML tables. A geometry pass that would have read loose blocks
    by position was designed as Pass B and eliminated on 2026-10-08 (Karthik's
    call); this pass, built as Pass C, took its letter. So there is no middle
    rung by decision: whatever Pass A cannot read comes here.

WHAT THIS IS FOR
    Pass A works by position, and position is exactly what a thermal till roll,
    a carbon copy and a screenshot destroy. On the 2026-09-23 run twenty-six of
    three hundred documents yielded nothing at all, and a further set gave back
    half their rows.

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
    Table and text blocks, minus every block that reads like a header line and
    the block that follows one - the keyword and follows-a-label deny-list,
    Karthik's call of 2026-10-08. Header lines carry the name, UHID, age,
    referring doctor, address and phone, and none of them is sent. Text blocks
    have to be candidates: a thermal slip and a single-test report come back
    from the engine as loose text, with no table block on the page at all.

    This is the one case the PII design in ../VectorDB_Analysis explicitly
    permits. Its section 10 rules out sending the IMAGE to an external vision
    model, because you cannot redact a photograph before you have read it. This
    pass runs after OCR, on text that already exists, so the header can simply
    be left behind.

    `select_blocks` is the control. If it cannot tell a block's region, the
    block is not sent. Fail closed.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass

from .base import RawBlock, RawDocument, RawPage
from .contracts import Extraction, Row, Section
from .labels import split_label
from .numbers import split_flag_suffix, split_value_unit
from .pipeline import _unmath
from .tables import is_annotation
from .templates import DocumentCoverage

__all__ = [
    "KEY_ENV",
    "MODEL",
    "Candidate",
    "GroundedPass",
    "GroundedUnavailableError",
    "escalation_reason",
    "merge",
    "parse_reply",
    "render_prompt",
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
    r"(\b[\w.+-]+@[\w-]+\.[\w.]+\b"  # email
    r"|\b(?:\+?91[\s-]?)?[6-9]\d{9}\b"  # Indian mobile
    r"|\b0\d{2,4}[\s-]\d{3,4}[\s-]?\d{3,4}\b"  # Indian landline, "0141 220 9100"
    r"|\b\d{4}\s?\d{4}\s?\d{4}\b)",  # Aadhaar
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


def escalation_reason(
    extraction: Extraction, coverage: DocumentCoverage | None = None
) -> str | None:
    """Why this document needs Pass B, or None if Pass A did its job.

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
    rows = [row for section in extraction.sections for row in section.rows]
    if not rows:
        return "no rows extracted"
    # A row with no value is not a reading. P03-R06 came back as one row -
    # "Age / Sex" and nothing beside it - and counting that as a row kept the
    # page from ever escalating: 23 of the 47 documents with no value read in
    # the saved results. Measured over all 323: this catches all 47 and fires
    # on none that read anything.
    if not any((row.raw_value or "").strip() for row in rows):
        return f"{len(rows)} row(s) read, none with a value"

    if coverage is not None:
        missing = [
            member.analyte_name or member.analyte_code
            for panel in getattr(coverage, "panels", [])
            for member in panel.members
            if getattr(member, "is_core", False)
            and not getattr(member, "found", False)
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

    Table and text blocks, minus anything that reads like a header line and
    the block after one. A block whose label the engine did not give us is NOT
    sent: an unclassified block might be the letterhead, and the control only
    works if unknown means no.

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
            out.append(
                Candidate(
                    ref=f"b{len(out)}",
                    text=text,
                    page=page.page_number,
                    bbox=_quantise(block, page),
                )
            )
    return out


def _quantise(block: RawBlock, page: RawPage) -> tuple[int, int, int, int] | None:
    """The block's box as integers 0-999, the LMDX coordinate scheme.

    Normalised to the page so one prompt can carry blocks from pages of
    different sizes, and coarse because the model needs relative position, not
    typographic precision.
    """
    if not block.bbox or not page.width or not page.height:
        return None
    x0, y0, x1, y1 = block.bbox
    scale = lambda v, size: max(0, min(999, int(v / size * 999)))  # noqa: E731
    return (
        scale(x0, page.width),
        scale(y0, page.height),
        scale(x1, page.width),
        scale(y1, page.height),
    )


def _norm(text: str) -> str:
    """Loose comparison for the grounding check - case and spacing only."""
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def verify_grounding(rows: list[dict], sent: list[Candidate]) -> tuple[list[dict], list[dict]]:
    """Split returned rows into those their cited block supports, and the rest.

    Each half is checked against ITS OWN cited block. A row survives when both
    blocks were actually sent, the label appears in the label's block, and the
    value appears in the value's block.

    Grounding each half separately is not a relaxation, it is the correction of
    a contradiction. The first version demanded both halves in one block, which
    on every layout this pass exists for - a till roll emitting "Plt Count" and
    "96000 /uL L" as consecutive blocks - rejected correct readings for being
    correctly attributed. The guarantee is unchanged: an invented number still
    appears in no block and still cannot survive.

    Returns:
        ``(kept, rejected)``. Rejected rows carry a ``reject`` key saying which
        test they failed, because the rejection rate is the measurement that
        says whether this pass is worth its money.
    """
    by_ref = {candidate.ref: candidate for candidate in sent}
    kept: list[dict] = []
    rejected: list[dict] = []

    for row in rows:
        label_ref = str(row.get("label_ref") or row.get("ref") or "")
        value_ref = str(row.get("value_ref") or label_ref)
        label = str(row.get("label") or "").strip()
        value = row.get("value")
        value = "" if value is None else str(value).strip()

        label_block = by_ref.get(label_ref)
        value_block = by_ref.get(value_ref)
        if label_block is None:
            rejected.append(
                {
                    **row,
                    "reject": f"cites {label_ref or '(nothing)'} for the label, "
                    f"which was not sent",
                }
            )
            continue
        if value and value_block is None:
            rejected.append(
                {**row, "reject": f"cites {value_ref} for the value, which was not sent"}
            )
            continue
        if not label:
            rejected.append({**row, "reject": "no label"})
            continue

        if _norm(label) not in _norm(label_block.text):
            rejected.append({**row, "reject": "label is not in the block it cites"})
            continue
        # value_block cannot be None here - a valued row with an unsent value
        # block was rejected above - but the check is what lets that be seen.
        if value and value_block is not None and _norm(value) not in _norm(value_block.text):
            rejected.append({**row, "reject": "value is not in the block it cites"})
            continue
        kept.append(row)

    return kept, rejected


# ---------------------------------------------------------------- the call
#
# Runs in the worker, never in the API. The api image has no `requests` and no
# key on purpose - the service answering a doctor's browser cannot call a third
# party or spend money. Dockerfile.worker says so and this depends on it.

MODEL = "claude-haiku-4-5-20251001"
ENDPOINT = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MAX_TOKENS = 2048
CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 120.0

SYSTEM = """\
You read laboratory report text that OCR has already extracted. The blocks are \
given out of any table structure, because the layout was too damaged for a grid \
reader - a till-roll printout, a photograph, a screenshot.

Return one line per test result, in exactly this form:

LABEL_REF | VALUE_REF | LABEL | VALUE | UNIT | FLAG

LABEL_REF is the block the test name came from. VALUE_REF is the block the \
result came from. They are often DIFFERENT blocks - a till-roll printout emits \
"Plt Count" and "96000 /uL L" separately - and are the same block only when one \
block holds both.

Rules:
- Only report a test whose name AND result you can both see in the blocks.
- Both refs must be blocks you were given. Never invent one.
- Copy LABEL and VALUE exactly as printed. Do not expand abbreviations, \
convert units, or correct what looks like a typo.
- A reference range is not a result. A collection time is not a result.
- Output nothing but result lines. No preamble, no totals, no explanation.

Example, given blocks b8 "Plt Count" and b9 "96000 /uL L":
b8 | b9 | Plt Count | 96000 | /uL | L\
"""

# VALUE_REF may be blank for a row with no value, so the second group is
# optional. Anything that does not start with a ref is not a row and is dropped.
_LINE = re.compile(r"^\s*(?P<label_ref>b\d+)\s*\|\s*(?P<value_ref>b\d+)?\s*\|(?P<rest>.*)$")


class GroundedUnavailableError(RuntimeError):
    """No key, no `requests`, or the service refused. Never fatal to a document.

    A document that could not be escalated keeps whatever the grid passes got.
    Pass B is a recovery attempt, so failing it returns us to where we already
    were - which is why every caller treats this as a skip rather than an error.
    """


def render_prompt(candidates: list[Candidate]) -> str:
    """The blocks, numbered and positioned, as the model sees them.

    Coordinates ride along because position is most of what distinguishes a
    label from its value on a page with no table structure - and it is the one
    thing the grid passes could not use, because there was no grid to use it in.
    """
    lines = []
    for c in candidates:
        where = f" @{c.page}:{','.join(str(n) for n in c.bbox)}" if c.bbox else f" @{c.page}"
        lines.append(f"{c.ref}{where} {c.text}")
    return "\n".join(lines)


def parse_reply(text: str) -> list[dict]:
    """Rows out of the model's plain-text reply.

    Deliberately NOT JSON mode. Constrained decoding costs 3-9 points of
    accuracy across open-weight models, and one benchmark saw output validity
    FALL from 51% to 37% under structured output - the sources are in
    docs/extraction-strategy.md. A pipe-delimited line is trivial to parse and
    costs the model nothing to produce, and anything malformed is simply not a
    row. The guarantee is verify_grounding, not the format.
    """
    rows: list[dict] = []
    for line in (text or "").splitlines():
        match = _LINE.match(line)
        if not match:
            continue
        parts = [p.strip() for p in match.group("rest").split("|")]
        parts += [""] * (4 - len(parts))
        label, value, unit, flag = parts[:4]
        if not label:
            continue
        rows.append(
            {
                "label_ref": match.group("label_ref"),
                # A row with no value grounds on its label alone, so the value ref
                # falls back to the label's rather than being invented.
                "value_ref": match.group("value_ref") or match.group("label_ref"),
                "label": label,
                "value": value or None,
                "unit": unit or None,
                "flag": flag or None,
            }
        )
    return rows


class GroundedPass:
    """One grounded read of one document's blocks."""

    def __init__(
        self,
        key: str | None = None,
        *,
        model: str = MODEL,
        attempts: int = 3,
        status: Callable[[str], None] | None = None,
    ) -> None:
        from .openparser import read_key

        self._key = key if key is not None else read_key(var=KEY_ENV)
        self._model = model
        self._attempts = max(1, attempts)
        self._status = status or (lambda _message: None)
        self.last_usage: dict | None = None

    @property
    def configured(self) -> bool:
        return bool(self._key)

    def read(self, candidates: list[Candidate]) -> tuple[list[dict], list[dict]]:
        """Blocks in, grounded rows out.

        Returns:
            ``(kept, rejected)`` straight from verify_grounding, so a caller
            can log the rejection rate - which is the measurement that says
            whether this pass earns its money.

        Raises:
            GroundedUnavailableError: no key, no `requests`, or the API gave up.
        """
        if not candidates:
            return [], []
        if not self._key:
            raise GroundedUnavailableError(
                f"no API key. Put {KEY_ENV}=... in the .env beside the project, "
                f"or set it in the environment - never a literal in the source."
            )
        try:
            import requests
        except ImportError as exc:  # pragma: no cover
            raise GroundedUnavailableError(
                "the grounded pass needs requests; it runs in the worker image"
            ) from exc

        body = {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            "system": SYSTEM,
            "messages": [{"role": "user", "content": render_prompt(candidates)}],
        }
        headers = {
            "x-api-key": self._key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }

        last = ""
        for attempt in range(1, self._attempts + 1):
            try:
                response = requests.post(
                    ENDPOINT,
                    json=body,
                    headers=headers,
                    timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                )
            # Network failures only. A programming error here used to be caught too,
            # retried three times with backoff, and then reported as the API being
            # unavailable - the one diagnosis guaranteed to send someone looking in
            # the wrong place.
            except requests.RequestException as exc:  # pragma: no cover - network
                last = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 200:
                    payload = response.json()
                    self.last_usage = payload.get("usage")
                    text = "".join(part.get("text", "") for part in payload.get("content", []))
                    rows = parse_reply(text)
                    kept, rejected = verify_grounding(rows, candidates)
                    self._status(
                        f"{len(rows)} row(s) returned, {len(kept)} grounded, "
                        f"{len(rejected)} discarded"
                    )
                    return kept, rejected
                # 429 and 5xx are worth another go; a 400 is our bug and is not.
                if response.status_code not in (429, 500, 502, 503, 529):
                    raise GroundedUnavailableError(
                        f"HTTP {response.status_code}: {(response.text or '')[:200]}"
                    )
                last = f"HTTP {response.status_code}"
            if attempt < self._attempts:
                self._status(f"{last}, retrying ({attempt} of {self._attempts})")
                time.sleep(min(8.0, 2.0**attempt))
        raise GroundedUnavailableError(f"exhausted {self._attempts} attempt(s): {last}")


def _strip_tail(text: str, tail: str | None) -> str:
    """`text` without `tail` on its end, when it stands there as its own word."""
    if not tail:
        return text
    if text.lower().endswith(tail.lower()):
        head = text[: len(text) - len(tail)]
        if head and head[-1].isspace():
            return head.rstrip()
    return text


def _cleaned(index: int, row: dict) -> Row:
    """A grounded row, cleaned the way Pass A cleans its cells.

    The model quotes the cell it read, because grounding demands that the text
    be in the block - so a value arrives as "1.12 mg/dL $ H $", with the unit,
    the flag and the engine's LaTeX still on it. Stored like that it never
    parses as a number, and the reading never reaches a trend: creatinine,
    urea and eGFR on the first live run, all with the right code and no
    number. The model reports the unit and flag in their own fields, so those
    exact texts come off the end of the value first - Pass A's helpers expect
    "214 H" or "12.9 g/dL", not both at once - and the helpers handle the rest.
    Every step only removes text the grounding check already saw.
    """
    label = split_label(_unmath(str(row.get("label") or "")))
    unit = _unmath(str(row.get("unit") or "")) or label.unit
    flag = _unmath(str(row.get("flag") or "")) or None
    value = _unmath(str(row.get("value") or ""))
    if value:
        value = _strip_tail(_strip_tail(value, flag), unit)
        value, trailing = split_flag_suffix(value)
        flag = flag or trailing
        value, embedded = split_value_unit(value)
        unit = unit or embedded
    return Row(
        row_index=index,
        raw_label=label.name,
        raw_value=value or None,
        raw_unit=unit or None,
        raw_flag=flag,
        raw_method=label.method,
    )


def merge(extraction: Extraction, kept: list[dict]) -> Extraction:
    """Fold grounded rows into the extraction the grid passes produced.

    The rows enter the SAME contract every other row uses, so everything
    downstream - analyte resolution, panel detection, the review table - treats
    them identically and no screen needs to know Pass B exists. Karthik's call
    of 2026-10-08: "just like now, just instead of the pipeline we use the LLM".

    Provenance is recorded where it costs nothing to carry and nothing to
    display: the engine string on the document gains a `+grounded` suffix, so
    lab.documents.ocr_engine says how a row was obtained without any row
    looking different. A wrong value traced back later should not require
    guessing which pass produced it.

    A recovered row FILLS IN the row Pass A left empty under the same label,
    keeping the heading, printed range and position Pass A found. Pass B fires
    when no row has a value, so Pass A has often read the labels and only the
    values defeated it; appending beside those showed every recovered test
    twice, once empty, and the review screen and the bulk-confirm gate then
    called the page unread. What has no empty twin gets a section of its own,
    as before: there is no trustworthy grid to put it in.
    """
    if not kept:
        return extraction

    recovered = [_cleaned(index, row) for index, row in enumerate(kept)]
    waiting: dict[str, list[Row]] = {}
    for row in recovered:
        waiting.setdefault(_norm(row.raw_label), []).append(row)

    filled: set[int] = set()
    for existing in (row for section in extraction.sections for row in section.rows):
        queue = waiting.get(_norm(existing.raw_label))
        if (existing.raw_value or "").strip() or not queue:
            continue
        got = queue.pop(0)
        filled.add(id(got))
        existing.raw_value = got.raw_value
        existing.raw_unit = existing.raw_unit or got.raw_unit
        existing.raw_flag = existing.raw_flag or got.raw_flag

    leftover = [row for row in recovered if id(row) not in filled]
    for index, row in enumerate(leftover):
        row.row_index = index
    if leftover:
        extraction.sections.append(Section(printed_title=None, rows=leftover))

    engine = extraction.document.engine or ""
    if "+grounded" not in engine:
        extraction.document.engine = f"{engine}+grounded" if engine else "grounded"
    return extraction
