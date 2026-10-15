"""Read the next document waiting in one practice's queue.

ONE PATH, TWO CALLERS
    scripts/ocr_worker.py loops over read_next; POST /documents/read-next
    calls it once per request. On Vercel the second is the only one -
    nothing there runs between requests - and the worker keeps the local
    stack reading as it always has. This is the worker's old body, moved,
    not rewritten: two loops that each knew the steps would drift.

STEPS ARE REPORTED AS THEY HAPPEN
    on_step receives one dict per real event: claimed, values found, a second
    look by Pass B, done or failed. The upload screen shows exactly these, so
    nothing there is timed to look busy.

NO CONNECTION IS HELD WHILE READING
    OpenParser takes seconds to minutes. `connect` is called per statement,
    so a pooled connection goes back to the pool for the whole read.

WHERE THE DATA GOES
    The file to api.openparser.dev, and, for a page Pass A read no value from,
    its table and text blocks to api.anthropic.com - both in the United
    States, both permitted by Karthik's decisions recorded in CLAUDE.md
    section 2.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.db import required
from app.services import files
from app.services.files import Connect
from app.services.ocr.base import ExtractionEngine, RawDocument
from app.services.ocr.contracts import Extraction
from app.services.ocr.grounded import (
    GroundedPass,
    GroundedUnavailableError,
    cost_usd,
    escalation_reason,
    merge,
    select_blocks,
)
from app.services.ocr_ingest import extract_with

log = logging.getLogger(__name__)

#: Receives one event at a time, as it happens.
Step = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class Tools:
    """What reading needs besides the document."""

    engine: ExtractionEngine
    pass_b: GroundedPass | None = None
    storage_dir: Path | None = None
    results_dir: Path | None = None


def _quiet(_event: dict[str, Any]) -> None:
    """The default on_step. The worker logs instead."""


def values_read(extraction: Extraction) -> int:
    """How many rows carry a value - what the screen calls tests found."""
    return sum(
        1
        for section in extraction.sections
        for row in section.rows
        if (row.raw_value or "").strip()
    )


def _hook(tools: Tools, on_step: Step) -> Callable[[RawDocument, Extraction], Extraction]:
    """Report what Pass A found, then run Pass B when Pass A read no value. Never fatal."""

    def hook(raw: RawDocument, extraction: Extraction) -> Extraction:
        on_step({"step": "found", "tests": values_read(extraction)})
        if tools.pass_b is None or not escalation_reason(extraction):
            return extraction
        candidates = select_blocks(raw)
        if not candidates:
            return extraction
        on_step({"step": "second_look"})
        try:
            kept, rejected = tools.pass_b.read(candidates)
        except GroundedUnavailableError as exc:
            # The document keeps what Pass A got, which is where it already was.
            log.info("grounded: skipped - %s", exc)
            return extraction
        usage = tools.pass_b.last_usage or {}
        log.info(
            "grounded: %s in / %s out tokens, ~$%.4f",
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            cost_usd(usage),
        )
        for row in rejected[:3]:
            log.info("grounded: discarded %r - %s", row.get("label"), row["reject"])
        merged = merge(extraction, kept)
        on_step({"step": "found", "tests": values_read(merged)})
        return merged

    return hook


def read_next(
    practice_id: int, tools: Tools, connect: Connect, on_step: Step = _quiet
) -> dict[str, Any] | None:
    """Claim the next waiting document of `practice_id`, read it, store the result.

    Returns the final event - {"step": "done", ...} or {"step": "failed", ...}
    - or None when nothing is waiting, after reporting {"step": "idle"}.
    """
    with connect() as conn:
        cur = conn.cursor(row_factory=dict_row)
        claimed = cur.execute(
            "SELECT * FROM lab.fn_claim_document(%s)", (practice_id,)
        ).fetchone()
        if claimed is None:
            on_step({"step": "idle"})
            return None
        attachment = (
            cur.execute(
                "SELECT original_file_name, stored_file_name, file_extension "
                "FROM core.visit_attachments WHERE id = %s",
                (claimed["visit_attachment_id"],),
            ).fetchone()
            or {}
        )

    doc_id = claimed["document_id"]
    on_step({"step": "reading", "document_id": str(doc_id), "attempt": claimed["attempts"]})
    # Basename only: the name comes out of the database, and "../../x" would
    # otherwise name a dump wherever it liked.
    original = Path(attachment.get("original_file_name") or f"document-{doc_id}.pdf").name
    suffix = attachment.get("file_extension") or Path(original).suffix or ".pdf"

    try:
        blob = files.load(
            connect,
            practice_id=practice_id,
            attachment_id=claimed["visit_attachment_id"],
            stored_file_name=attachment.get("stored_file_name"),
            storage_dir=tools.storage_dir,
        )
        if blob is None:
            # Raised inside the try on purpose: a missing file takes the same
            # fail path as any other, so it is recorded on the document.
            raise FileNotFoundError("stored file missing")  # noqa: TRY301
        with tempfile.TemporaryDirectory() as tmp:
            local = Path(tmp) / f"document{suffix}"
            local.write_bytes(blob)
            payload = extract_with(
                tools.engine,
                local,
                checksum=claimed["checksum_sha256"],
                dump_dir=tools.results_dir,
                dump_name=original,
                escalate=_hook(tools, on_step),
            )
        # Its own transaction - a savepoint, inside a caller's - so a refused
        # save leaves the connection usable for recording why.
        with connect() as conn, conn.transaction():
            new_id = required(
                conn.cursor(row_factory=dict_row)
                .execute(
                    "SELECT lab.fn_complete_document(%s, %s, %s::jsonb, %s) AS id",
                    (practice_id, doc_id, json.dumps(payload), None),
                )
                .fetchone(),
                "fn_complete_document",
            )["id"]
    except Exception as exc:  # noqa: BLE001 - every failure is recorded on the document
        reason = f"{type(exc).__name__}: {exc}"
        # The database refusing what was read fails the same way every time, so
        # it is not worth another OpenParser read: give up now (max attempts =
        # this attempt). A network or engine failure keeps its retries.
        fail: str = "SELECT lab.fn_fail_document(%s, %s, %s) AS state"
        params: tuple[Any, ...] = (practice_id, doc_id, reason)
        if isinstance(exc, (psycopg.errors.IntegrityError, psycopg.errors.DataError)):
            fail = "SELECT lab.fn_fail_document(%s, %s, %s, %s::smallint) AS state"
            params += (claimed["attempts"],)
        with connect() as conn:
            state = required(
                conn.cursor(row_factory=dict_row).execute(fail, params).fetchone(),
                "fn_fail_document",
            )["state"]
        # Ids only in the log, never the file name: real file names are often
        # the patient's name - review B9.
        log.warning(
            "doc %s attempt %s failed (%s): %s", doc_id, claimed["attempts"], state, reason[:90]
        )
        failed = {"step": "failed", "document_id": str(doc_id), "state": state}
        on_step(failed)
        return failed

    # Outside the failure path: a hiccup while summarising must not send a
    # document that was just read successfully to fn_fail_document - review B5.
    done = {
        "step": "done",
        "document_id": str(new_id),
        "replaced": str(doc_id),
        **_summary(connect, practice_id, new_id),
    }
    on_step(done)
    return done


def _summary(connect: Connect, practice_id: int, document_id: int) -> dict[str, Any]:
    """What the card shows once reading is done. Empty if it cannot be had."""
    try:
        with connect() as conn:
            row = (
                conn.cursor(row_factory=dict_row)
                .execute(
                    """
                    SELECT d.status, d.patient_id,
                           p.first_name || ' ' || p.last_name AS patient_name,
                           (SELECT count(*) FROM lab.results x
                             WHERE x.document_id = d.id AND x.is_deleted = FALSE) AS tests
                    FROM   lab.documents d
                    LEFT   JOIN core.patients p ON p.id = d.patient_id
                    WHERE  d.id = %s AND d.practice_id = %s
                    """,
                    (document_id, practice_id),
                )
                .fetchone()
            )
    except Exception:  # a summary must never fail a document that was read
        log.warning("doc %s completed; could not summarise it", document_id, exc_info=True)
        return {}
    if row is None:
        return {}
    return {
        "status": row["status"],
        "patient_id": str(row["patient_id"]) if row["patient_id"] else None,
        "patient_name": row["patient_name"],
        "tests": row["tests"],
    }


@lru_cache(maxsize=1)
def from_environment() -> Tools | None:
    """The API's reading tools, built once per process. None without an OpenParser key."""
    from app.config import settings
    from app.services.ocr.openparser import OpenParserEngine, read_key

    key = read_key()
    if not key:
        return None
    pass_b = GroundedPass(status=lambda message: log.info("grounded: %s", message))
    results = os.environ.get("RESULTS_DIR", "").strip()
    return Tools(
        engine=OpenParserEngine(key=key),
        pass_b=pass_b if pass_b.configured else None,
        storage_dir=settings().storage_dir,
        results_dir=Path(results) if results else None,
    )
