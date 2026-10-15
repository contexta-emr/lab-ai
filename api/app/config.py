"""Settings, read once from the environment.

Nothing in this file has a usable default for a secret. If DATABASE_URL or
JWT_SECRET is missing the service refuses to start, rather than running on a
placeholder that works locally and leaks in production.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: Signing keys that appear in this repository - docker-compose.yml and
#: .env.example. Fine for a laptop, forgeable anywhere else.
PUBLISHED_SECRETS = frozenset(
    {"local-development-only-do-not-ship", "change-me-before-anyone-else-uses-this"}
)


def _load_dotenv() -> None:
    """Read .env from the project root. Never overwrites a real environment variable."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class Settings:
    def __init__(self) -> None:
        _load_dotenv()

        self.database_url: str = self._required("DATABASE_URL")
        self.jwt_secret: str = self._required("JWT_SECRET")
        self.jwt_algorithm: str = os.environ.get("JWT_ALGORITHM", "HS256")
        self.jwt_ttl_minutes: int = int(os.environ.get("JWT_TTL_MINUTES", "480"))

        self.storage_dir: Path = Path(os.environ.get("STORAGE_DIR", str(ROOT / "storage")))
        self.max_upload_mb: int = int(os.environ.get("MAX_UPLOAD_MB", "25"))
        self.cors_origins: list[str] = [
            o.strip()
            for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
            if o.strip()
        ]
        # Production unless told otherwise. This defaulted to development, and
        # development turns authentication off - so a deployment that forgot one
        # variable served patient data to anyone who asked (review B6). Every
        # relaxation below needs ENVIRONMENT=development said out loud.
        self.environment: str = os.environ.get("ENVIRONMENT", "production")
        development = self.environment == "development"

        # No login, no roles. On by default in development, because the console
        # is a single-tenant demo and a sign-in screen was only ever friction
        # in front of it. Set AUTH_DISABLED=false to put the POC JWT back.
        #
        # It does NOT make practice_id client-controlled: auth.current_user
        # still resolves the account server-side. See the comment there.
        self.auth_disabled: bool = os.environ.get(
            "AUTH_DISABLED", "true" if development else "false"
        ).strip().lower() in ("1", "true", "yes")
        if self.auth_disabled and not development:
            raise RuntimeError(
                f"AUTH_DISABLED is set but ENVIRONMENT is {self.environment!r}. "
                "Authentication can only be turned off with ENVIRONMENT=development."
            )

        # Open access: no sign-in, every visitor IS one named account. For the
        # team console on Vercel (README: "Deploying the team console").
        #
        # Unlike AUTH_DISABLED this is allowed in production, because the
        # account is NAMED here. AUTH_DISABLED takes "the first reviewer by id",
        # which is practice 1 and its 20 test patients. The sample account is
        # optional; when set, a visitor may switch to it, read-only.
        self.open_access_team: str | None = (
            os.environ.get("OPEN_ACCESS_TEAM", "").strip() or None
        )
        self.open_access_sample: str | None = (
            os.environ.get("OPEN_ACCESS_SAMPLE", "").strip() or None
        )
        if self.open_access_sample and not self.open_access_team:
            raise RuntimeError(
                "OPEN_ACCESS_SAMPLE is set without OPEN_ACCESS_TEAM. The sample is "
                "something to switch to from the team workspace, not instead of it."
            )

        # Warm connections per process. Four suits one long-lived server; Vercel
        # runs many short-lived copies, each of which needs one (DB_POOL_MIN=1).
        self.db_pool_min: int = int(os.environ.get("DB_POOL_MIN", "4"))

        # Anyone holding the signing key can mint a token for any practice. The
        # placeholders below are published in this repository, so outside
        # development they are refused, as is anything short enough to guess
        # (review B14).
        if not development and (
            self.jwt_secret in PUBLISHED_SECRETS or len(self.jwt_secret.encode()) < 32
        ):
            raise RuntimeError(
                "JWT_SECRET is a published placeholder or shorter than 32 bytes. "
                'Generate one: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )

        # There is deliberately no MATCH_AUTO_ACCEPT setting here. The UHID
        # auto-accept threshold is 0.95 and it lives in lab.fn_ingest_lab_document,
        # which is where the decision is actually made. Mirroring it into an env
        # var read by nothing made it look configurable when it was not - setting
        # it changed no behaviour at all. One threshold, one place, in the
        # function that attaches a document to a patient.

        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _required(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            raise RuntimeError(
                f"{name} is not set. Copy .env.example to .env and fill it in. "
                "This service will not start on a default secret."
            )
        return value


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()
