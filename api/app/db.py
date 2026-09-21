"""Database access: a connection pool, and the rule that we only call functions.

WHY THERE IS NO ORM HERE
    The schema is owned by hand-written SQL and the write path is owned by
    Postgres functions. An ORM would give us a second, inferred description of
    the same tables and a second way to write them - which is exactly how the
    two drift apart. This module is thin on purpose.

WHAT CALLERS GET
    fetch_all / fetch_one   read queries, rows as dicts
    call_function           invoke a lab.fn_* function
    transaction             a connection for a multi-statement unit of work

Every one of them takes practice_id from the caller, and the caller got it from
a verified token. Nothing in this file accepts a practice id from a request body.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings

_pool: ConnectionPool | None = None


def pool() -> ConnectionPool:
    global _pool
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
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def transaction() -> Iterator[psycopg.Connection]:
    """A connection with an open transaction. Commits on clean exit, rolls back on error."""
    with pool().connection() as conn:
        with conn.transaction():
            yield conn


def fetch_all(sql: str, params: tuple | dict | None = None) -> list[dict[str, Any]]:
    with pool().connection() as conn:
        return conn.execute(sql, params).fetchall()


def fetch_one(sql: str, params: tuple | dict | None = None) -> dict[str, Any] | None:
    with pool().connection() as conn:
        return conn.execute(sql, params).fetchone()


def call_function(name: str, *args: Any, returns_table: bool = False) -> Any:
    """Call a lab.fn_* function.

    returns_table=True for set-returning functions (SELECT * FROM fn(...)),
    False for scalar ones (SELECT fn(...)).
    """
    placeholders = ", ".join(["%s"] * len(args))
    if returns_table:
        sql = f"SELECT * FROM {name}({placeholders})"
        return fetch_all(sql, args)
    row = fetch_one(f"SELECT {name}({placeholders}) AS result", args)
    return row["result"] if row else None


def healthcheck() -> dict[str, Any]:
    """Enough to tell a load balancer whether this instance is usable."""
    row = fetch_one(
        "SELECT current_database() AS database, "
        "       (SELECT count(*) FROM lab.analytes WHERE is_deleted = FALSE) AS analytes, "
        "       (SELECT count(*) FROM lab.analyte_aliases WHERE is_deleted = FALSE) AS aliases"
    )
    return row or {}
