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

import time
import weakref
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Self, cast

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

#: [statements, seconds] for the request in progress, which app.main reports
#: in its Server-Timing header. None outside a request.
db_tally: ContextVar[list[float] | None] = ContextVar("db_tally", default=None)


class _TalliedCursor(psycopg.Cursor[Any]):
    """A cursor that adds each statement and its wall time to the request's tally.

    Against a database across an ocean every statement is a round trip, so the
    count is the number that explains a slow screen. The pool's own connection
    check runs through here too, and is counted as the round trip it is.
    """

    def execute(
        self,
        query: Any,
        params: Params | None = None,
        *,
        prepare: bool | None = None,
        binary: bool | None = None,
    ) -> Self:
        started = time.perf_counter()
        try:
            return super().execute(query, params, prepare=prepare, binary=binary)
        finally:
            tally = db_tally.get()
            if tally is not None:
                tally[0] += 1
                tally[1] += time.perf_counter() - started


_pool: ConnectionPool | None = None


#: When each pooled connection was last handed back, so the check before reuse
#: can be skipped for one that was working a moment ago.
_last_returned: weakref.WeakKeyDictionary[psycopg.Connection[Any], float] = (
    weakref.WeakKeyDictionary()
)

#: Seconds a connection may sit idle and still be reused without a check.
CHECK_AFTER_IDLE = 30.0


def _returned(conn: psycopg.Connection[Any]) -> None:
    _last_returned[conn] = time.monotonic()


def _check_if_idle(conn: psycopg.Connection[Any]) -> None:
    """Check a connection before reuse - only when it has been idle a while.

    Neon suspends an idle database and drops its connections, so a connection
    from the pool can be dead, and the check catches that. But the check is a
    round trip, and from here to Neon one costs a third of a second; doing it
    on every query doubled the time of every screen. A connection returned less
    than half a minute ago was working then and is all but certainly working
    now, so it goes straight back into use.
    """
    if time.monotonic() - _last_returned.get(conn, 0.0) > CHECK_AFTER_IDLE:
        ConnectionPool.check_connection(conn)


def pool() -> ConnectionPool:
    # A module singleton, created once by the FastAPI lifespan before any request
    # can race it, and closed by the same lifespan on shutdown.
    global _pool  # noqa: PLW0603
    if _pool is None:
        _pool = ConnectionPool(
            conninfo=settings().database_url,
            # A screen fires several requests at once. Each one finding a warm
            # connection is the difference between one round trip and the five
            # it takes to open a new TLS connection and authenticate.
            min_size=4,
            max_size=10,
            # Closed after four idle minutes - before Neon's five-minute suspend
            # would kill them under us.
            max_idle=240,
            check=_check_if_idle,
            reset=_returned,
            kwargs={
                # No implicit transaction around each statement. Without this a
                # read left a transaction open and the pool sent a COMMIT when
                # the connection came back: a second round trip per query, for
                # nothing. One statement - a read, or one lab.fn_* call - is
                # atomic on its own; transaction() still opens a real one where
                # several statements must stand or fall together.
                "autocommit": True,
                "row_factory": dict_row,
                "cursor_factory": _TalliedCursor,
                "application_name": "contexta-lab-idp",
            },
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
