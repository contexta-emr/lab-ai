"""Reading inside a request: claim, read, complete, each step reported (spec section 5).

The engine is recorded OpenParser output, so nothing here calls out or costs
anything. The document goes into the TEAM practice, which holds no other
waiting document, so the claim can only take this one.
"""

from __future__ import annotations

import json
import uuid

import pytest

from tests import conftest


class Recorded:
    """An engine that returns what OpenParser returned for one corpus report."""

    def __init__(self, report_id: str) -> None:
        self.path = conftest.RESULTS / f"{report_id}.OPENPARSER.raw.json"
        if not self.path.exists():
            pytest.fail(f"missing recorded dump {self.path.name}")

    def extract(self, _path):
        from app.services.ocr.outputs import read_raw

        return read_raw(self.path)


class Broken:
    def extract(self, _path):
        raise RuntimeError("engine down")


@pytest.fixture
def team_client(client, db_write):
    from app.auth import CurrentUser, current_user
    from app.main import app

    row = db_write.execute(
        "SELECT id, practice_id, email, role FROM core.users WHERE email = 'team@contexta.local'"
    ).fetchone()
    if row is None:
        pytest.fail("db/032 is not applied here: python scripts/run_migrations.py")
    waiting = db_write.execute(
        "SELECT count(*) AS n FROM lab.documents WHERE practice_id = %s "
        "AND status IN ('received', 'parsing') AND is_deleted = FALSE",
        (row["practice_id"],),
    ).fetchone()["n"]
    if waiting:
        pytest.skip("the team practice has documents waiting here; the claim could take one")
    team = CurrentUser(
        user_id=row["id"], practice_id=row["practice_id"], email=row["email"], role=row["role"]
    )
    app.dependency_overrides[current_user] = lambda: team
    return client


@pytest.fixture
def use_engine():
    from app.main import app
    from app.routers.documents import reading_tools
    from app.services.reader import Tools

    def _use(engine) -> None:
        app.dependency_overrides[reading_tools] = lambda: Tools(engine=engine)

    yield _use
    app.dependency_overrides.pop(reading_tools, None)


def _upload(client) -> str:
    blob = b"%PDF-1.4\n% " + uuid.uuid4().hex.encode() + b"\n%%EOF\n"
    response = client.post(
        "/documents", files={"file": ("P05-R02.pdf", blob, "application/pdf")}
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "received"
    return response.json()["id"]


def _steps(response) -> list[dict]:
    assert response.status_code == 200, response.text
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_a_waiting_report_is_read_and_every_step_is_reported(team_client, use_engine) -> None:
    use_engine(Recorded("P05-R02"))
    uploaded = _upload(team_client)

    steps = _steps(team_client.post("/documents/read-next"))

    assert steps[0] == {"step": "reading", "document_id": uploaded, "attempt": 1}
    found = [s for s in steps if s["step"] == "found"]
    assert found
    assert found[-1]["tests"] > 0
    done = steps[-1]
    assert done["step"] == "done"
    assert done["replaced"] == uploaded
    assert done["status"] in ("parsed", "needs_review")
    assert done["tests"] > 0


def test_with_nothing_waiting_it_says_so(team_client, use_engine) -> None:
    use_engine(Recorded("P05-R02"))
    assert _steps(team_client.post("/documents/read-next")) == [{"step": "idle"}]


def test_a_failed_read_goes_back_in_line(team_client, use_engine, db_write) -> None:
    use_engine(Broken())
    uploaded = _upload(team_client)

    steps = _steps(team_client.post("/documents/read-next"))

    assert steps[-1] == {"step": "failed", "document_id": uploaded, "state": "received"}
    status = db_write.execute(
        "SELECT status FROM lab.documents WHERE id = %s", (int(uploaded),)
    ).fetchone()["status"]
    assert status == "received"


def test_a_read_stopped_midway_is_claimed_again_after_fifteen_minutes(
    team_client, use_engine, db_write
) -> None:
    use_engine(Recorded("P05-R02"))
    uploaded = _upload(team_client)
    # What a request stopped at Vercel's 300 s leaves behind: 'parsing', claimed long ago.
    db_write.execute(
        "UPDATE lab.documents SET status = 'parsing', ocr_attempts = 1, "
        "claimed_at = now() - interval '16 minutes' WHERE id = %s",
        (int(uploaded),),
    )

    steps = _steps(team_client.post("/documents/read-next"))

    assert steps[0]["step"] == "reading"
    assert steps[0]["document_id"] == uploaded
    assert steps[-1]["step"] == "done"


def test_without_an_engine_key_reading_is_a_clear_503(team_client, monkeypatch) -> None:
    from app.services import reader

    monkeypatch.setattr(reader, "from_environment", lambda: None)
    assert team_client.post("/documents/read-next").status_code == 503


def test_a_report_the_database_refuses_is_not_read_again(
    team_client, use_engine, db_write, monkeypatch
) -> None:
    """A refused save fails the same way every time; retrying only pays OpenParser again.

    A redacted vendor report, 2026-10-15: a CHECK refused the report, and each of three attempts
    read all six pages again before failing identically.
    """
    from app.services import reader

    use_engine(Recorded("P05-R02"))
    real = reader.extract_with

    def refused(*args, **kwargs):
        payload = real(*args, **kwargs)
        payload["reports"][0]["sex_printed"] = "X"  # the value the CHECK refused
        return payload

    monkeypatch.setattr(reader, "extract_with", refused)
    uploaded = _upload(team_client)

    steps = _steps(team_client.post("/documents/read-next"))

    assert steps[-1] == {"step": "failed", "document_id": uploaded, "state": "failed"}
    status = db_write.execute(
        "SELECT status FROM lab.documents WHERE id = %s", (int(uploaded),)
    ).fetchone()["status"]
    assert status == "failed"


def test_dropping_a_failed_report_again_puts_it_back_in_line(
    team_client, use_engine, db_write
) -> None:
    """The same file uploaded again is the retry - on Vercel there is nothing else.

    It used to hand back the failed copy, so a report that failed once could
    never be read again: a redacted vendor report, 2026-10-15, after the CHECK that refused it
    was fixed.
    """
    blob = b"%PDF-1.4\n% " + uuid.uuid4().hex.encode() + b"\n%%EOF\n"
    file = {"file": ("again.pdf", blob, "application/pdf")}
    first = team_client.post("/documents", files=file).json()

    use_engine(Broken())
    for _ in range(3):
        last = _steps(team_client.post("/documents/read-next"))[-1]
    assert last == {"step": "failed", "document_id": first["id"], "state": "failed"}

    again = team_client.post("/documents", files=file)
    assert again.status_code == 201, again.text
    assert again.json()["id"] == first["id"]
    assert again.json()["status"] == "received"

    use_engine(Recorded("P05-R02"))
    assert _steps(team_client.post("/documents/read-next"))[-1]["step"] == "done"


def test_dropping_a_report_that_was_read_again_changes_nothing(team_client, use_engine) -> None:
    """Only a failed report is put back in line; one already read is handed back as it is."""
    use_engine(Recorded("P05-R02"))
    blob = b"%PDF-1.4\n% " + uuid.uuid4().hex.encode() + b"\n%%EOF\n"
    file = {"file": ("read.pdf", blob, "application/pdf")}
    team_client.post("/documents", files=file)
    done = _steps(team_client.post("/documents/read-next"))[-1]

    again = team_client.post("/documents", files=file).json()

    assert again["id"] == done["document_id"]
    assert again["status"] == done["status"]
