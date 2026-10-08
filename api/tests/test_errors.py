"""What leaves the server when something goes wrong (review B7, B8, B9).

The caller is told its own mistakes, the browser can always read the answer, and
the server's own mistakes - and patient identifiers - stay in the server's log.
"""

from __future__ import annotations

import logging

import psycopg
import pytest

MISSING_DOCUMENT = "999999999999"


def test_reviewing_a_document_that_does_not_exist_is_a_404(client) -> None:
    """fn_review_lab_document raises P0002. That used to be a 500."""
    response = client.post(f"/review/{MISSING_DOCUMENT}", json={"decision": "verify"})
    assert response.status_code == 404, response.text
    assert "not found" in response.json()["detail"]


def test_a_malformed_id_is_the_callers_mistake(client) -> None:
    response = client.get("/review/12abc/events")
    assert response.status_code == 400
    assert "positive integer" in response.json()["detail"]


def test_an_internal_value_error_is_not_blamed_on_the_caller(client, monkeypatch) -> None:
    """Every ValueError used to become a 400 carrying its internal message."""

    def broken(*_args: object, **_kwargs: object) -> None:
        raise ValueError("page size must be positive, got 0x0")

    monkeypatch.setattr("app.routers.review.fetch_all", broken)
    response = client.get("/review/1/events")
    assert response.status_code == 500
    assert "page size" not in response.text


def test_a_server_error_is_readable_by_the_browser(client, monkeypatch) -> None:
    """A 500 used to leave without CORS headers, so the console saw 'Failed to fetch'."""
    from app.config import settings

    def broken(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("connection string with a password in it")

    monkeypatch.setattr("app.routers.review.fetch_all", broken)
    origin = settings().cors_origins[0]
    response = client.get("/review/1/events", headers={"Origin": origin})

    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") == origin
    body = response.json()
    assert body["ref"] in body["detail"]
    assert "password" not in response.text


def test_health_does_not_hand_out_the_database_error(client, monkeypatch) -> None:
    """/health needs no token; a connection error names the host and the user."""

    def unreachable() -> None:
        raise psycopg.OperationalError(
            'connection to server at "10.1.2.3", port 5432 failed: '
            'FATAL:  password authentication failed for user "labidp"'
        )

    monkeypatch.setattr("app.main.healthcheck", unreachable)
    response = client.get("/health")
    assert response.status_code == 503
    assert "10.1.2.3" not in response.text
    assert "labidp" not in response.text


def test_the_access_log_keeps_no_query_string() -> None:
    """Patient search is GET /patients?q=<what was typed> - a name, in the log."""
    try:
        from app.main import _NoQueryStrings
    except RuntimeError as exc:  # settings refuse to load without a database here
        pytest.skip(str(exc))
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        0,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "GET", "/patients?q=Aadhya", "1.1", 200),
        None,
    )
    assert _NoQueryStrings().filter(record)
    assert record.getMessage() == '127.0.0.1:5000 - "GET /patients HTTP/1.1" 200'
