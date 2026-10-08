"""Baidu AI Studio hosted PaddleOCR API. **Testing only. Never production.**

This engine sends the document to a server outside our network and outside India. That
directly contradicts the constraint in `pii-masking-layer-and-architecture.md` section 10
- *"No external vision API, ever"* - which is why PaddleOCR-VL was chosen as weights we
run ourselves in the first place.

It exists to answer one question: does the hosted service read pages better than what we
run locally? Comparing them needs both. Nothing more is intended.

Three guards make accidental misuse hard:

1. The token is read from ``IDP_AISTUDIO_TOKEN``. There is no literal in the source, so a
   token cannot leak by being committed.
2. Any file under a ``fixtures`` directory is **refused outright, with no override**. That
   is where real patient reports live.
3. The CLI will not construct this engine without ``--allow-remote``, which prints a
   warning naming what is about to leave the network.

Install the extra::

    uv pip install -e ".[remote]"
    setx IDP_AISTUDIO_TOKEN "..."     # PowerShell: $env:IDP_AISTUDIO_TOKEN = "..."
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import RawDocument, RawPage
from .paddle_vl import normalise_page_result

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_MODEL",
    "OPTIONAL_PAYLOAD",
    "AiStudioEngine",
    "RemoteRefusedError",
    "blocked_reason",
    "markdown_blocks",
    "normalise_api_result",
    "report_progress",
]

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
TOKEN_ENV = "IDP_AISTUDIO_TOKEN"  # noqa: S105 - the variable NAME, never its value

#: Directory names that must never be sent off the machine. `tests/fixtures` holds real
#: Tenet Diagnostics reports for a real patient.
BLOCKED_DIR_NAMES = frozenset({"fixtures"})

#: The same model we run locally, so a comparison measures the *hosting*, not a different
#: model. PP-OCRv6 would return loose text lines with the numbers detached from the test
#: names, which no amount of downstream code can reassemble - hence not the default.
DEFAULT_MODEL = "PaddleOCR-VL-1.6"

#: Matches the local engine's configuration so the two runs differ only in where they ran.
OPTIONAL_PAYLOAD = {
    "useDocOrientationClassify": False,
    "useDocUnwarping": False,
    "useChartRecognition": False,
}


def markdown_blocks(markdown: str) -> list[dict[str, Any]]:
    """Split a markdown page into blocks, converting pipe tables back to HTML.

    The hosted service can answer with markdown instead of the structured payload. A
    markdown pipe table carries the same rows and columns as the HTML one, so converting
    it means the pipeline needs no special case - it still receives a table.

    Args:
        markdown: One page of markdown.

    Returns:
        Block dicts in the shape :func:`normalise_page_result` expects.
    """
    blocks: list[dict[str, Any]] = []
    pending: list[str] = []

    def flush_table() -> None:
        # A pipe table's second line is the |---|---| separator, which is not data.
        rows = [r for i, r in enumerate(pending) if i != 1]
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        html = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in cells if row
        )
        blocks.append(
            {
                "block_label": "table",
                "block_content": f"<table>{html}</table>",
                "block_order": len(blocks),
            }
        )
        pending.clear()

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            pending.append(stripped)
            continue
        if pending:
            flush_table()
        if not stripped:
            continue
        label = "paragraph_title" if stripped.startswith("#") else "text"
        blocks.append(
            {
                "block_label": label,
                "block_content": stripped.lstrip("# ").strip(),
                "block_order": len(blocks),
            }
        )
    if pending:
        flush_table()
    return blocks


def _as_seconds(value: Any) -> float | None:
    """Parse a timestamp the service may report as epoch millis, epoch, or ISO text."""
    if isinstance(value, (int, float)):
        # Anything this large is milliseconds; epoch seconds passed 1e10 in the year 2286.
        return float(value) / 1000.0 if value > 1e10 else float(value)
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value).timestamp()  # 3.11+ reads a trailing Z
        except ValueError:
            return None
    return None


def report_progress(progress: dict[str, Any], *, total_seconds: float) -> str:
    """Describe where the time went, splitting queue wait from actual extraction.

    "The model is slow" and "we sat behind other people's jobs on a shared free tier" are
    different problems with different answers, and only this split tells them apart.

    Args:
        progress: The service's ``extractProgress`` object.
        total_seconds: Wall time measured on our side, submission to result.

    Returns:
        The line that was printed, so it can be asserted on.
    """
    start = _as_seconds(progress.get("startTime"))
    end = _as_seconds(progress.get("endTime"))
    pages = progress.get("extractedPages")

    if start is not None and end is not None and end >= start:
        extraction = end - start
        queued = max(0.0, total_seconds - extraction)
        suffix = f" ({pages} page(s))" if pages else ""
        if extraction < 0.5:
            # A zero-length extraction window means nothing was extracted. Resubmitting
            # the same file returns a stored result, so this timing says nothing about
            # how fast the model is - and must not be quoted as if it did.
            line = (
                f"  timing: {total_seconds:.1f}s total - CACHED RESULT, no extraction ran."
                f" Not a measurement of model speed.{suffix}"
            )
        else:
            line = (
                f"  timing: {total_seconds:.1f}s total = "
                f"{queued:.1f}s queued + {extraction:.1f}s extracting{suffix}"
            )
    else:
        line = f"  timing: {total_seconds:.1f}s total (service reported no usable window)"

    logger.info("%s", line)
    return line


class RemoteRefusedError(RuntimeError):
    """Raised when a document must not be sent to a third party."""


def blocked_reason(path: Path) -> str | None:
    """Return why ``path`` may not be sent remotely, or ``None`` if it may.

    Args:
        path: The document being considered.

    Returns:
        A human-readable reason, or ``None`` when sending is permitted.
    """
    for part in path.resolve().parts:
        if part.lower() in BLOCKED_DIR_NAMES:
            return (
                f"{path.name} sits under a '{part}' directory, which holds real patient "
                f"reports. Sending it to a third-party API is refused and cannot be "
                f"overridden. Copy a synthetic or already-public document elsewhere to "
                f"compare engines."
            )
    return None


def normalise_api_result(payload: dict[str, Any], *, fallback_page: int) -> list[RawPage]:
    """Map one AI Studio result record onto pages.

    Three response shapes are handled. The structured one matches what the local engine
    returns, so that mapping is reused rather than duplicated. A markdown-only response has
    its pipe tables converted back to HTML, so the pipeline still receives a table. A plain
    OCR response yields loose text lines - carried through so the difference is visible in
    the output rather than showing up as a silently empty file.

    Args:
        payload: One decoded JSONL record's ``result`` object.
        fallback_page: Page number to use when the payload does not carry one.

    Returns:
        One :class:`RawPage` per page in the record.
    """
    pages: list[RawPage] = []
    layout = payload.get("layoutParsingResults") or payload.get("layoutParsingResult")
    if isinstance(layout, list) and layout:
        for offset, item in enumerate(layout):
            pruned = item.get("prunedResult") or item.get("result")
            if isinstance(pruned, dict) and pruned.get("parsing_res_list"):
                # Same shape the local engine returns, so reuse rather than duplicate.
                pages.append(
                    normalise_page_result(pruned, fallback_page=fallback_page + offset)
                )
                continue
            # Markdown-only response. Tables survive as pipe tables or embedded HTML;
            # both are converted so the rest of the pipeline sees what it always sees.
            markdown = (item.get("markdown") or {}).get("text") or ""
            pages.append(
                normalise_page_result(
                    {"width": 1, "height": 1, "parsing_res_list": markdown_blocks(markdown)},
                    fallback_page=fallback_page + offset,
                )
            )
        return pages

    # Plain OCR fallback: text lines, no table structure. Kept so a PP-OCRv6 run produces
    # visible text rather than an empty file that looks like a crash.
    for offset, item in enumerate(payload.get("ocrResults") or []):
        pruned = item.get("prunedResult") or item
        texts = pruned.get("rec_texts") or []
        pages.append(
            normalise_page_result(
                {
                    "width": pruned.get("width") or 1,
                    "height": pruned.get("height") or 1,
                    "parsing_res_list": [
                        {"block_label": "text", "block_content": t, "block_order": i}
                        for i, t in enumerate(texts)
                    ],
                },
                fallback_page=fallback_page + offset,
            )
        )
    return pages


class AiStudioEngine:
    """Submits a document to the hosted API and waits for the result."""

    name = "AISTUDIO_HOSTED"

    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        token: str | None = None,
        poll_seconds: float = 5.0,
        timeout_seconds: float = 900.0,
    ) -> None:
        """Configure the engine without contacting anything.

        Args:
            model: Hosted model name. Defaults to a document-parsing model, because a
                plain OCR model cannot produce the table structure the pipeline needs.
            token: API token. Defaults to the ``IDP_AISTUDIO_TOKEN`` environment
                variable; passing a literal here is discouraged.
            poll_seconds: Delay between status checks.
            timeout_seconds: Give up after this long.
        """
        self.version = model
        self._model = model
        self._token = token or os.environ.get(TOKEN_ENV, "")
        self._poll = poll_seconds
        self._timeout = timeout_seconds
        #: ``extractProgress`` from the last completed job: pages, startTime, endTime.
        self.last_progress: dict[str, Any] = {}

    def extract(self, path: Path) -> RawDocument:
        """Send one document to the hosted API and map what comes back.

        Args:
            path: The document to send.

        Returns:
            The same :class:`RawDocument` shape every other engine produces.

        Raises:
            FileNotFoundError: If ``path`` does not exist.
            RemoteRefusedError: If the document may not leave the machine, or no token is set.
            RuntimeError: If ``requests`` is missing, or the API fails or times out.
        """
        if not path.exists():
            raise FileNotFoundError(path)

        reason = blocked_reason(path)
        if reason:
            raise RemoteRefusedError(reason)
        if not self._token:
            raise RemoteRefusedError(
                f"no API token. Set {TOKEN_ENV} in the environment - never in the source."
            )

        try:
            import requests
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise RuntimeError(
                'the remote engine needs requests: uv pip install -e ".[remote]"'
            ) from exc

        headers = {"Authorization": f"bearer {self._token}"}
        submitted_at = time.monotonic()
        with path.open("rb") as handle:
            submitted = requests.post(
                JOB_URL,
                headers=headers,
                data={
                    "model": self._model,
                    "optionalPayload": json.dumps(OPTIONAL_PAYLOAD),
                },
                files={"file": handle},
                timeout=120,
            )
        if submitted.status_code != 200:
            # Carry the server's own words through. Reporting only a status code is how
            # a five-second fix turns into an afternoon of guessing.
            raise RuntimeError(
                f"job submission failed ({submitted.status_code}): "
                f"{submitted.text.strip()[:400] or '<empty response body>'}"
            )
        job_id = submitted.json()["data"]["jobId"]

        deadline = time.monotonic() + self._timeout
        while True:
            if time.monotonic() > deadline:
                raise RuntimeError(f"job {job_id} did not finish within {self._timeout:.0f}s")
            status = requests.get(f"{JOB_URL}/{job_id}", headers=headers, timeout=60)
            if status.status_code != 200:
                raise RuntimeError(
                    f"status check failed ({status.status_code}): "
                    f"{status.text.strip()[:400] or '<empty response body>'}"
                )
            data = status.json()["data"]
            state = data.get("state")
            if state == "done":
                # The service reports when extraction actually started and finished.
                # Total elapsed minus that window is queue wait - the difference between
                # "the model is slow" and "we were sitting behind other people's jobs",
                # which are entirely different problems.
                self.last_progress = data.get("extractProgress") or {}
                jsonl_url = data["resultUrl"]["jsonUrl"]
                break
            if state == "failed":
                raise RuntimeError(f"job failed: {data.get('errorMsg')}")
            time.sleep(self._poll)

        report_progress(self.last_progress, total_seconds=time.monotonic() - submitted_at)

        body = requests.get(jsonl_url, timeout=120)
        body.raise_for_status()

        pages: list[RawPage] = []
        for line in body.text.strip().splitlines():
            if line.strip():
                pages.extend(
                    normalise_api_result(
                        json.loads(line)["result"], fallback_page=len(pages) + 1
                    )
                )

        return RawDocument(
            source_path=path, engine=self.name, engine_version=self.version, pages=pages
        )
