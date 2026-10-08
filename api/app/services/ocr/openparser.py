"""OpenParser hosted PaddleOCR-VL 1.6. **Testing only. Never production.**

The same model we run locally, on someone else's GPU. Every caveat that applies to
`aistudio.py` applies here word for word - the document leaves our network and leaves
India, which contradicts `pii-masking-layer-and-architecture.md` section 10, *"No
external vision API, ever"*. Paying an invoice does not make a patient's lab report
legal to send abroad; it makes it a contracted transfer somebody has to answer for.

What it buys, and the only reason it exists here:

* **No queue.** AI Studio's free tier answered ``10010 queue full`` four times in five.
  This is a paid endpoint with no shared-capacity lottery in front of it.
* **A GPU.** One CPU page measured 1385s locally. This returns in seconds.
* **$0.001 per page**, confirmed from ``GET /models/ocr`` rather than a pricing page.

So it answers "how good is PaddleOCR-VL 1.6 on our documents, without waiting 23 minutes
a page" - which is a question about *the model*, and transfers straight to the GPU we
would run in Azure Central India. It answers nothing about where production runs.

The guards are deliberately the same objects the AI Studio engine uses, not copies:
:func:`~idp.engines.aistudio.blocked_reason` refuses anything under ``fixtures/`` with no
override, and the CLI will not construct this without ``--allow-remote``.

Install and configure::

    uv pip install -e ".[remote]"
    # .env  ->  IDP_OPENPARSER_KEY=eig_...

Reference: https://api.openparser.dev/openapi.json (the authoritative contract; the two
prose doc pages disagree with each other about the response shape).
"""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import re
import time
import uuid
from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import Any

from .aistudio import RemoteRefusedError, blocked_reason, markdown_blocks
from .base import RawBlock, RawDocument, RawPage
from .paddle_vl import normalise_page_result

logger = logging.getLogger(__name__)

__all__ = [
    "CONNECT_TIMEOUT",
    "DEFAULT_MODEL",
    "KEY_ENV",
    "OCR_OPTIONS",
    "READ_TIMEOUT",
    "RETRYABLE_STATUS",
    "ROLE_LABELS",
    "USD_PER_PAGE",
    "OpenParserEngine",
    "cells_to_html",
    "normalise_parsed_document",
    "read_key",
    "retry_after_seconds",
]

BASE_URL = "https://api.openparser.dev"
KEY_ENV = "IDP_OPENPARSER_KEY"

#: The same weights we run locally, so a comparison measures the hosting and the hardware
#: rather than a different model. It is also their default and their cheapest.
DEFAULT_MODEL = "paddleocr-vl-1.6"

#: Retail price from ``GET /models/ocr``, not from a marketing page.
USD_PER_PAGE = 0.001

#: Matched to the local engine's configuration. ``chart_recognition`` is *on* by default
#: at OpenParser and off locally; leaving that difference in place would make every
#: comparison an argument about which knob caused it. Lab reports have no charts.
OCR_OPTIONS: dict[str, bool] = {
    "image_block_ocr": False,
    "chart_recognition": False,
    "merge_layout_blocks": False,
}

#: Their admission limit. Refusing here beats uploading 50 MiB to be told no.
MAX_INPUT_BYTES = 50 * 1024 * 1024

#: Codes the service itself calls transient. 429 and 503 are documented; 502 and 504 are
#: what sits in front of it saying it could not reach a healthy instance. Retrying
#: anything else just spends the credits twice on the same wrong request.
RETRYABLE_STATUS = frozenset({429, 502, 503, 504})

#: Connect fast, read slow. One number for both means a stalled DNS lookup hangs for as
#: long as a legitimately slow parse, and those are not the same problem.
CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 300.0


def read_key(start: Path | None = None, var: str = KEY_ENV) -> str:
    """The API key, from the environment or the nearest ``.env``.

    The environment wins. The file exists because setting a variable per PowerShell
    session is a papercut that has already cost this project one debugging session.

    Args:
        start: Directory to begin searching upward from. Defaults to this file's
            location, which finds the ``.env`` beside the project.
        var: Which variable to read. Defaults to this engine's key; the grounded
            pass reads its own through the same lookup rather than a second copy
            of the environment-then-.env rule.

    Returns:
        The key, or ``""`` when none is configured. Never raises - the caller decides
        whether a missing key is fatal, and it always is before anything is uploaded.
    """
    from_env = os.environ.get(var, "").strip()
    if from_env:
        return from_env
    here = start or Path(__file__).resolve().parent
    for directory in [here, *here.parents]:
        candidate = directory / ".env"
        if not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == var and value.strip():
                return value.strip().strip("\"'")
    return ""


def cells_to_html(element: dict[str, Any]) -> str:
    """Render a ``TableElement`` as HTML the pipeline already knows how to read.

    ``html`` is optional in the schema, so a table cannot depend on it being there. The
    cells always are, carrying ``row_index``, ``column_index`` and both spans - which is
    exactly what :func:`idp.tables.parse_html_tables` reconstructs a grid from.

    Args:
        element: One element with ``kind == "table"``.

    Returns:
        A ``<table>`` string. Empty when the element carries no cells at all.
    """
    existing = element.get("html")
    if isinstance(existing, str) and existing.strip():
        return existing

    cells = element.get("cells") or []
    if not cells:
        return ""

    rows: dict[int, list[dict[str, Any]]] = {}
    for cell in cells:
        rows.setdefault(int(cell.get("row_index") or 0), []).append(cell)

    parts: list[str] = ["<table>"]
    for index in sorted(rows):
        parts.append("<tr>")
        for cell in sorted(rows[index], key=lambda c: int(c.get("column_index") or 0)):
            attributes = ""
            for key, name in (("column_span", "colspan"), ("row_span", "rowspan")):
                span = int(cell.get(key) or 1)
                if span > 1:
                    attributes += f' {name}="{span}"'
            parts.append(f"<td{attributes}>{escape(str(cell.get('text') or ''))}</td>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def _bbox(element: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """The first geometry's box, in whatever unit the page declares."""
    for location in element.get("locations") or []:
        box = location.get("bbox")
        if isinstance(box, dict):
            try:
                return (
                    float(box["left"]),
                    float(box["top"]),
                    float(box["right"]),
                    float(box["bottom"]),
                )
            except (KeyError, TypeError, ValueError):
                return None
    return None


def _page_of(element: dict[str, Any]) -> int | None:
    """Which page an element sits on, per its first geometry."""
    for location in element.get("locations") or []:
        number = location.get("page_number")
        if isinstance(number, int):
            return number
    return None


#: OpenParser splits what PaddleOCR calls a block label across two fields: a structural
#: ``kind`` (text/table/figure) and a semantic ``role`` (heading, page_header, ...). The
#: pipeline keys section titles off the label, so mapping ``role`` onto the vocabulary it
#: already speaks is what makes a hosted run and a local run interchangeable. Reading
#: only ``kind`` flattened every line of a report to "text" and cost it every heading.
ROLE_LABELS = {
    "document_title": "doc_title",
    "heading": "paragraph_title",
    "page_header": "header",
    "page_footer": "footer",
    "page_number": "number",
    "caption": "figure_title",
    "footnote": "footnote",
}

#: A heading arrives as rendered markdown - ``## LIPID PROFILE``. Only the hashes are
#: stripped, and only at the start: ``*****End of Report*****`` is printed on the page
#: exactly like that, so treating asterisks as emphasis would delete real content.
_MD_HEADING_RE = re.compile(r"^\s*#{1,6}\s+")


def _label_of(element: dict[str, Any]) -> str:
    """The pipeline-facing block label for one element."""
    kind = str(element.get("kind") or "text")
    if kind != "text":
        return kind
    return ROLE_LABELS.get(str(element.get("role") or ""), "text")


def _content(element: dict[str, Any]) -> str:
    """Text for a text-shaped element, HTML for a table."""
    if element.get("kind") == "table":
        return cells_to_html(element)
    for key in ("text", "markdown", "caption", "value"):
        value = element.get(key)
        if isinstance(value, str) and value.strip():
            return _MD_HEADING_RE.sub("", value)
    return ""


def normalise_parsed_document(payload: dict[str, Any]) -> list[RawPage]:
    """Map an ``openparser@1`` document onto pages of blocks.

    Elements live in one flat list and pages reference them by id, so this walks each
    page's ``reading_order`` - which is the order the service believes the document is
    read in, and the order the pipeline needs to keep a value beside its label.

    Args:
        payload: A ``ParsedDocument``.

    Returns:
        One :class:`RawPage` per page. Falls back to splitting the top-level markdown
        when the document carries no elements, so a response the schema did not predict
        still produces visible content instead of a silently empty file.
    """
    elements = {
        str(e.get("id")): e for e in payload.get("elements") or [] if isinstance(e, dict)
    }
    declared = payload.get("pages") or []

    if not elements:
        markdown = payload.get("markdown") or payload.get("text") or ""
        if not str(markdown).strip():
            return []
        return [
            normalise_page_result(
                {"width": 1, "height": 1, "parsing_res_list": markdown_blocks(str(markdown))},
                fallback_page=1,
            )
        ]

    pages: list[RawPage] = []
    placed: set[str] = set()
    for index, page in enumerate(declared, start=1):
        number = page.get("number")
        blocks: list[RawBlock] = []
        order = page.get("reading_order") or page.get("element_ids") or []
        for element_id in order:
            element = elements.get(str(element_id))
            if element is None:
                continue
            placed.add(str(element_id))
            content = _content(element)
            if not content.strip():
                continue
            blocks.append(
                RawBlock(
                    label=_label_of(element),
                    content=content,
                    bbox=_bbox(element),
                    order=len(blocks),
                    score=(element.get("confidence") or {}).get("score"),
                )
            )
        pages.append(
            RawPage(
                page_number=int(number) if isinstance(number, int) else index,
                width=float(page.get("width") or 0) or 1.0,
                height=float(page.get("height") or 0) or 1.0,
                blocks=blocks,
            )
        )

    # An element no page listed would otherwise vanish without a trace, which is the one
    # failure mode this whole contract exists to prevent. Group the strays by their own
    # declared page and append them.
    strays = [e for key, e in elements.items() if key not in placed]
    for element in strays:
        content = _content(element)
        if not content.strip():
            continue
        number = _page_of(element) or 1
        target = next((p for p in pages if p.page_number == number), None)
        if target is None:
            target = RawPage(page_number=number, width=1.0, height=1.0, blocks=[])
            pages.append(target)
        target.blocks.append(
            RawBlock(
                label=_label_of(element),
                content=content,
                bbox=_bbox(element),
                order=len(target.blocks),
                score=(element.get("confidence") or {}).get("score"),
            )
        )

    return sorted(pages, key=lambda p: p.page_number)


def _error_text(response: Any) -> str:
    """The server's own words, not just a status code.

    Reporting "failed (400)" is what turned a five-second fix into an afternoon once
    already. OpenParser returns a structured error; unwrap it when it is there.
    """
    try:
        error = response.json().get("error") or {}
        message = error.get("message")
        if message:
            code = error.get("code") or response.status_code
            return f"{code}: {message}"
    except (ValueError, AttributeError):
        pass
    return (response.text or "").strip()[:400] or "<empty response body>"


def retry_after_seconds(response: Any, default: float) -> float:
    """How long the service asked us to wait, or ``default``.

    ``Retry-After`` is what turns a rate limit from a failure into a pause. Ignoring it
    and backing off on our own schedule is how a client gets throttled harder.

    Args:
        response: The throttled response.
        default: Fallback when the header is absent or unparseable.

    Returns:
        Seconds to wait, clamped to something a person will sit through.
    """
    try:
        raw = str(response.headers.get("Retry-After", "")).strip()
    except AttributeError:
        return default
    if not raw:
        return default
    try:
        return max(0.0, min(120.0, float(raw)))
    except ValueError:
        # It may be an HTTP-date rather than seconds. Not worth parsing a value that
        # would be clamped anyway.
        return default


class OpenParserEngine:
    """Submits a document to OpenParser and maps ``openparser@1`` back onto blocks."""

    name = "OPENPARSER"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        key: str | None = None,
        options: dict[str, bool] | None = None,
        poll_seconds: float = 2.0,
        timeout_seconds: float = 600.0,
        attempts: int = 4,
    ) -> None:
        """Configure the engine without contacting anything.

        Args:
            model: Hosted OCR model id. See ``GET /models/ocr``.
            key: API key. Defaults to :func:`read_key`; passing a literal is discouraged.
            options: ``ocr_options`` overrides, merged over :data:`OCR_OPTIONS`.
            poll_seconds: Delay between status checks when the sync call defers to a job.
            timeout_seconds: Give up on a deferred job after this long.
            attempts: Tries per HTTP call, for transient failures only.
        """
        self.version = model
        self._model = model
        self._key = key if key is not None else read_key()
        self._options = {**OCR_OPTIONS, **(options or {})}
        self._poll = poll_seconds
        self._timeout = timeout_seconds
        self._attempts = max(1, attempts)
        #: Attached by :func:`idp.jobs.start_extraction` so a UI can show the phase. A
        #: bare spinner cannot tell a slow parse from a stalled socket, and those need
        #: different reactions from whoever is watching.
        self.on_status: Callable[[str], None] | None = None
        #: Wall time of the last successful call, and how many pages it billed.
        self.last_seconds = 0.0
        self.last_pages = 0

    def _status(self, text: str) -> None:
        """Report a phase to stderr and to whoever is watching."""
        logger.info("  openparser: %s", text)
        if self.on_status is not None:
            self.on_status(text)

    def _call(self, session: Any, method: str, url: str, **kwargs: Any) -> Any:
        """One HTTP call, retried while the failure is transient.

        A refused connection, a rate limit and a gateway timeout are all *the network*,
        not the request - the same call a moment later usually works. A 400 or a 402 is
        a decision, and repeating it only spends the credits twice.

        Args:
            session: The ``requests`` session to call through.
            method: HTTP verb.
            url: Absolute URL.
            **kwargs: Passed through to ``requests``.

        Returns:
            The response, which may still carry a non-retryable error status - reading
            that status is the caller's job, because what counts as failure differs
            between submitting and polling.

        Raises:
            RuntimeError: If the service could not be reached at all.
        """
        import requests

        delay = 2.0
        for attempt in range(1, self._attempts + 1):
            final = attempt == self._attempts
            try:
                response = session.request(
                    method, url, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), **kwargs
                )
            except requests.exceptions.RequestException as exc:
                if final:
                    raise RuntimeError(
                        f"could not reach {url} after {attempt} attempt(s): "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
                self._status(
                    f"{type(exc).__name__} reaching the service, retrying in {delay:.0f}s"
                )
                time.sleep(delay)
                delay *= 2
                continue

            if response.status_code not in RETRYABLE_STATUS or final:
                return response

            wait = retry_after_seconds(response, delay)
            self._status(
                f"HTTP {response.status_code} from the service, retrying in {wait:.0f}s "
                f"(attempt {attempt} of {self._attempts})"
            )
            time.sleep(wait)
            delay *= 2
        raise RuntimeError(f"exhausted {self._attempts} attempt(s) against {url}")

    def extract(self, path: Path) -> RawDocument:
        """Send one document to OpenParser and map what comes back.

        Args:
            path: The document to send.

        Returns:
            The same :class:`RawDocument` shape every other engine produces.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            RemoteRefusedError: If the document may not leave the machine, if it exceeds
                the service's admission limit, or if no key is configured.
            RuntimeError: If ``requests`` is missing, or the API fails or times out.
        """
        if not path.exists():
            raise FileNotFoundError(path)

        reason = blocked_reason(path)
        if reason:
            raise RemoteRefusedError(reason)
        if not self._key:
            raise RemoteRefusedError(
                f"no API key. Put {KEY_ENV}=... in the .env beside the project, or set it "
                f"in the environment - never a literal in the source."
            )
        size = path.stat().st_size
        if size > MAX_INPUT_BYTES:
            raise RemoteRefusedError(
                f"{path.name} is {size / 1048576:.1f} MiB; the service admits at most "
                f"{MAX_INPUT_BYTES // 1048576} MiB. Split it rather than upload and fail."
            )

        try:
            import requests
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                'the remote engine needs requests: uv pip install -e ".[remote]"'
            ) from exc

        # Read once rather than stream: a retry cannot rewind a consumed file handle,
        # and the admission check above already caps this at 50 MiB.
        content = path.read_bytes()
        request = {
            "ocr_model": self._model,
            "output_format": "openparser@1",
            "ocr_options": self._options,
        }
        # One key for the whole logical call, deliberately. If a 504 leaves the outcome
        # unknown, retrying under the same key returns the result we already paid for
        # instead of parsing - and being billed for - the document a second time.
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Idempotency-Key": uuid.uuid4().hex,
        }

        started = time.monotonic()
        with requests.Session() as session:
            session.headers.update(headers)
            # The caller already knows which file this is - repeating it here is
            # what put the name on screen twice.
            self._status(f"uploading {size / 1024:.0f} KB")
            # `request` is a multipart part, not a form field: the spec declares
            # contentType application/json on it, and a plain field is rejected.
            # Declare the real media type. The service sniffs the bytes anyway, but it
            # documents a 415 for unsupported types, and "octet-stream" is the one answer
            # guaranteed to be wrong if it ever stops sniffing.
            media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            parts: dict[str, tuple[str | None, Any, str]] = {
                "request": (None, json.dumps(request), "application/json"),
                "file": (path.name, content, media_type),
            }
            response = self._call(session, "POST", f"{BASE_URL}/parse", files=parts)

            if response.status_code == 202:
                # Documented: the sync call defers to a job when its wait limit expires.
                document = self._await_job(session, response)
            elif response.status_code == 200:
                self._status("parsed, mapping the result")
                document = response.json()
            else:
                raise RuntimeError(
                    f"parse failed ({response.status_code}) {_error_text(response)}"
                )

        pages = normalise_parsed_document(document)
        self.last_seconds = time.monotonic() - started
        self.last_pages = len(pages)
        self._status(
            f"{self.last_seconds:.1f}s for {self.last_pages} page(s) "
            f"(~${self.last_pages * USD_PER_PAGE:.4f})"
        )
        return RawDocument(
            source_path=path, engine=self.name, engine_version=self.version, pages=pages
        )

    def _await_job(self, session: Any, accepted: Any) -> dict[str, Any]:
        """Poll a deferred job until it reaches a terminal status.

        Args:
            session: The session the 202 arrived on.
            accepted: The 202 response, carrying the job id.

        Returns:
            The ``ParsedDocument`` from the finished job.

        Raises:
            RuntimeError: If the job fails, or does not finish in time.
        """
        job_id = accepted.json().get("id")
        if not job_id:
            raise RuntimeError("202 accepted but no job id was returned")
        deadline = time.monotonic() + self._timeout
        while True:
            # Checked before the first sleep. A small document is often finished by the
            # time the 202 arrives, and sleeping first would add dead time to every
            # deferred call for nothing.
            status = self._call(session, "GET", f"{BASE_URL}/jobs/{job_id}")
            if status.status_code != 200:
                raise RuntimeError(
                    f"status check failed ({status.status_code}) {_error_text(status)}"
                )
            body = status.json()
            state = body.get("status")
            if state == "succeeded":
                self._status("parsed, mapping the result")
                result: dict[str, Any] = body.get("result") or {}
                return result
            if state in {"failed", "cancelled", "expired"}:
                raise RuntimeError(f"job {job_id} {state}: {body.get('error') or ''}")
            if time.monotonic() > deadline:
                raise RuntimeError(
                    f"job {job_id} still {state} after {self._timeout:.0f}s. It may yet "
                    f"finish - the result is at GET /jobs/{job_id}."
                )
            waited = self._timeout - (deadline - time.monotonic())
            self._status(f"waiting at the service ({state}, {waited:.0f}s so far)")
            time.sleep(self._poll)
