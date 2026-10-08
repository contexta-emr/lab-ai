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
        self.environment: str = os.environ.get("ENVIRONMENT", "development")

        # No login, no roles. On by default in development, because the console
        # is a single-tenant demo and a sign-in screen was only ever friction
        # in front of it. Set AUTH_DISABLED=false to put the POC JWT back.
        #
        # It does NOT make practice_id client-controlled: auth.current_user
        # still resolves the account server-side. See the comment there.
        self.auth_disabled: bool = os.environ.get(
            "AUTH_DISABLED", "true" if self.environment == "development" else "false"
        ).strip().lower() in ("1", "true", "yes")

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
