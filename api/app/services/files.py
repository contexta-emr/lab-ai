"""Where an uploaded file's bytes live.

In lab.document_files since 033, written in the upload's own transaction.
Documents stored before that are still on disk under the storage directory,
found by their stored NAME - never by a path out of the database, which is a
value someone could set.

The storage directory is a parameter rather than settings(): the worker
imports this, and it has no JWT_SECRET, so it cannot build Settings.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

#: Hands out one connection for one statement - a pool's, or the worker's own.
Connect = Callable[[], AbstractContextManager[psycopg.Connection[Any]]]


def save(
    conn: psycopg.Connection[Any],
    *,
    practice_id: int,
    attachment_id: int,
    blob: bytes,
    user_id: int,
) -> None:
    """Store the bytes on the caller's connection, inside the caller's transaction."""
    conn.execute(
        "INSERT INTO lab.document_files "
        "(practice_id, visit_attachment_id, content, byte_count, created_by) "
        "VALUES (%s, %s, %s, %s, %s)",
        (practice_id, attachment_id, blob, len(blob), user_id),
    )


def load(
    connect: Connect,
    *,
    practice_id: int,
    attachment_id: int,
    stored_file_name: str | None,
    storage_dir: Path | None,
) -> bytes | None:
    """The bytes from the database, else from disk for an older document, else None."""
    with connect() as conn:
        row = (
            conn.cursor(row_factory=dict_row)
            .execute(
                "SELECT content FROM lab.document_files "
                "WHERE visit_attachment_id = %s AND practice_id = %s AND is_deleted = FALSE",
                (attachment_id, practice_id),
            )
            .fetchone()
        )
    if row is not None:
        return bytes(row["content"])
    if stored_file_name and storage_dir is not None:
        path = storage_dir / Path(stored_file_name).name
        if path.is_file():
            return path.read_bytes()
    return None
