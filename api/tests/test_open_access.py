"""Open access: the team console's one account, and the read-only sample (spec section 3).

Every request runs as a NAMED account, never "the first reviewer by id", which
is practice 1 and its 20 test patients. These run the real endpoints in-process
against the real tables, inside one transaction that is rolled back.
"""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import pytest

TEAM = "team@contexta.local"
SAMPLE = "reviewer@contexta.local"


@pytest.fixture
def open_client(db_write, monkeypatch):
    from fastapi.testclient import TestClient
    from psycopg.rows import dict_row

    from app import auth
    from app import db as app_db
    from app.config import settings
    from app.main import app

    db_write.row_factory = dict_row
    if (
        db_write.execute("SELECT 1 FROM core.users WHERE email = %s", (TEAM,)).fetchone()
        is None
    ):
        pytest.fail("db/032 is not applied here: python scripts/run_migrations.py")

    @contextmanager
    def connection():
        yield db_write

    monkeypatch.setattr(app_db, "pool", lambda: SimpleNamespace(connection=connection))
    cfg = settings()
    monkeypatch.setattr(cfg, "open_access_team", TEAM)
    monkeypatch.setattr(cfg, "open_access_sample", SAMPLE)
    auth._open_access_user.cache_clear()
    try:
        yield TestClient(app)
    finally:
        auth._open_access_user.cache_clear()


def _practice_one(db_write, table: str) -> set[str]:
    """Ids in `table` that belong to the sample account's practice."""
    rows = db_write.execute(
        f"SELECT t.id FROM {table} t JOIN core.users u ON u.practice_id = t.practice_id "  # noqa: S608 - fixed table names
        "WHERE u.email = %s AND t.is_deleted = FALSE",
        (SAMPLE,),
    ).fetchall()
    return {str(r["id"]) for r in rows}


def test_the_team_sees_none_of_the_test_data(open_client, db_write) -> None:
    documents = _practice_one(db_write, "lab.documents")
    patients = _practice_one(db_write, "core.patients")
    if not documents:
        pytest.skip("practice 1 holds no documents here, so there is nothing to keep hidden")
    seen_documents = {d["id"] for d in open_client.get("/documents?limit=200").json()}
    seen_patients = {p["id"] for p in open_client.get("/patients").json()}
    assert not seen_documents & documents
    assert not seen_patients & patients


def test_the_sample_switch_reaches_practice_one(open_client, db_write) -> None:
    if not _practice_one(db_write, "lab.documents"):
        pytest.skip("practice 1 holds no documents here")
    assert open_client.get("/documents", headers={"X-Workspace": "sample"}).json()
    # The query form, which the <object> showing the page uses: it cannot send a header.
    assert open_client.get("/documents", params={"workspace": "sample"}).json()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/review/confirm-all"),
        ("PUT", "/documents/1/lists/doctor_order"),
        ("PATCH", "/documents/1/results/1"),
        ("DELETE", "/documents/1/results/1"),
    ],
)
def test_sample_data_is_read_only(open_client, method: str, path: str) -> None:
    response = open_client.request(method, path, headers={"X-Workspace": "sample"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Sample data is read-only."


@pytest.mark.parametrize("asked", ["Sample", "SAMPLE", "admin", "1", ""])
def test_any_other_workspace_name_is_the_team(open_client, asked: str) -> None:
    body = open_client.get("/workspace", headers={"X-Workspace": asked}).json()
    assert body["workspace"] == "team"


def test_workspace_says_where_the_browser_is(open_client) -> None:
    team = open_client.get("/workspace").json()
    assert team["workspace"] == "team"
    assert team["read_only"] is False
    assert team["sample_available"] is True
    assert team["practice_name"] == "Contexta Team"
    assert isinstance(team["max_upload_mb"], int)

    sample = open_client.get("/workspace", headers={"X-Workspace": "sample"}).json()
    assert sample["workspace"] == "sample"
    assert sample["read_only"] is True
    assert sample["practice_name"] == "Contexta Demo Clinic"


def test_without_a_sample_account_the_header_is_ignored(open_client, monkeypatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings(), "open_access_sample", None)
    body = open_client.get("/workspace", headers={"X-Workspace": "sample"}).json()
    assert body["workspace"] == "team"
    assert body["sample_available"] is False


def test_a_missing_account_is_a_503_not_a_fallback(open_client, monkeypatch) -> None:
    from app import auth
    from app.config import settings

    monkeypatch.setattr(settings(), "open_access_team", "nobody@contexta.local")
    auth._open_access_user.cache_clear()
    assert open_client.get("/documents").status_code == 503
