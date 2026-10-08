"""Database access: a connection pool, and the rule that we only call functions.

WHY THERE IS NO ORM HERE
    The schema is owned by hand-written SQL and the write path is owned by
    Postgres functions. An ORM would give us a second, inferred description of
    the same tables and a second way to write them - which is exactly how the
    two drift apart. This module is thin on purpose.

WHAT CALLERS GET
    fetch_all / fetch_one   read queries, rows as dicts
    fetch_required          a query that returns a row by construction
    call_function           invoke a lab.fn_* function
    transaction             a connection for a multi-statement unit of work

Every one of them takes practice_id from the caller, and the caller got it from
a verified token. Nothing in this file accepts a practice id from a request body.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast

import psycopg
from psycopg import sql
from psycopg.abc import Params
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool

from app.config import settings

# What callers pass: SQL text, or a statement composed with psycopg.sql. Not
# psycopg.abc.Query, which also admits 3.14 template strings - its own execute()
# overload rejects those under the 3.11 floor this package declares.
SQLText = str | sql.Composed

_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    # A module singleton, created once by the FastAPI lifespan before any request
    # can race it, and closed by the same lifespan on shutdown.
    global _pool  # noqa: PLW0603
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings().database_url,
            min_size=1,
            max_size=10,
            # Neon suspends when idle; a long-lived idle connection comes back
            # dead. Recycling on checkout costs a round trip and saves a 500.
            check=ConnectionPool.check_connection,
            kwargs={"row_factory": dict_row, "application_name": "contexta-lab-idp"},
            open=True,
        )
    return _pool


def close_pool() -> None:
    global _pool  # noqa: PLW0603
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def transaction() -> Iterator[psycopg.Connection[DictRow]]:
    """A connection with an open transaction. Commits on clean exit, rolls back on error."""
    with pool().connection() as conn, conn.transaction():
        # The pool opens every connection with row_factory=dict_row, which the
        # pool's own type cannot express. The cast states that fact; it adds none.
        yield cast("psycopg.Connection[DictRow]", conn)


def fetch_all(query: SQLText, params: Params | None = None) -> list[DictRow]:
    with pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(query, params).fetchall()


def fetch_one(query: SQLText, params: Params | None = None) -> DictRow | None:
    with pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(query, params).fetchone()


def required(row: DictRow | None, what: object) -> DictRow:
    """A row that cannot be absent, as a row rather than an Optional.

    For count(*), for SELECT fn(...) - which yields exactly one row or raises -
    for INSERT ... RETURNING, and for a row this request wrote a moment ago.
    Saying so once beats a None check at every such call site that can never
    fire, and an absent row then fails naming what was expected rather than
    with a TypeError about None.
    """
    if row is None:
        raise LookupError(f"expected a row and got none: {what!r}"[:300])
    return row


def fetch_required(query: SQLText, params: Params | None = None) -> DictRow:
    """fetch_one for a query that returns a row by construction. See required()."""
    return required(fetch_one(query, params), query)


def call_function(name: str, *args: Any, returns_table: bool = False) -> Any:
    """Call a lab.fn_* function.

    returns_table=True for set-returning functions (SELECT * FROM fn(...)),
    False for scalar ones (SELECT fn(...)).

    CAST NUMERIC ARGUMENTS YOURSELF, or write the SQL out.
        This helper sends every argument untyped, and PostgreSQL resolves the
        overload from what psycopg inferred. A Python float arrives as double
        precision and will NOT resolve to a REAL parameter; a small int can
        arrive as smallint and not resolve to BIGINT. The error is

            function lab.fn_x(smallint, unknown, double precision) does not exist

        which reads like a missing migration and is actually wrong argument
        types. It cost an afternoon: every document in needs_review returned
        500 from /documents/{id} because the candidate lookup passes a
        similarity threshold as a float, while every parsed document was fine
        because it never calls it.

        There is no fix inside this function - it cannot know a signature -
        so a call with a float or a bare int in it belongs in SQL with ::REAL
        and ::BIGINT written out.
    """
    # The function name is composed as an identifier, never interpolated. It is
    # a literal at the one call site today; this keeps the next call site from
    # turning a user-influenced name into SQL.
    function = sql.Identifier(*name.split("."))
    placeholders = sql.SQL(", ").join(sql.Placeholder() * len(args))
    if returns_table:
        return fetch_all(sql.SQL("SELECT * FROM {}({})").format(function, placeholders), args)
    row = fetch_one(sql.SQL("SELECT {}({}) AS result").format(function, placeholders), args)
    return row["result"] if row else None


def healthcheck() -> dict[str, Any]:
    """Enough to tell a load balancer whether this instance is usable."""
    row = fetch_one(
        "SELECT current_database() AS database, "
        "       (SELECT count(*) FROM lab.analytes WHERE is_deleted = FALSE) AS analytes, "
        "       (SELECT count(*) FROM lab.analyte_aliases WHERE is_deleted = FALSE) AS aliases"
    )
    return row or {}
