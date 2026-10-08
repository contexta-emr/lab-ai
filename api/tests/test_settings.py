"""Settings fail closed: authentication and the signing key (review B6, B14).

Each test builds Settings from an environment holding only what it sets, with the
.env file out of the way, so the answer cannot depend on the machine running it.
"""

from __future__ import annotations

import pytest

from app import config

STRONG = "k" * 48


@pytest.fixture
def env(monkeypatch, tmp_path):
    for name in ("ENVIRONMENT", "AUTH_DISABLED", "JWT_SECRET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "_load_dotenv", lambda: None)
    monkeypatch.setenv("DATABASE_URL", "postgresql://never-connected")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path))
    return monkeypatch


def test_authentication_is_on_unless_development_is_said_out_loud(env) -> None:
    """ENVIRONMENT used to default to development, which turned authentication off."""
    env.setenv("JWT_SECRET", STRONG)
    settings = config.Settings()
    assert settings.environment == "production"
    assert settings.auth_disabled is False


def test_the_local_console_still_runs_without_a_login(env) -> None:
    env.setenv("ENVIRONMENT", "development")
    env.setenv("JWT_SECRET", "local-development-only-do-not-ship")
    assert config.Settings().auth_disabled is True


def test_turning_authentication_off_outside_development_refuses_to_start(env) -> None:
    env.setenv("JWT_SECRET", STRONG)
    env.setenv("AUTH_DISABLED", "true")
    with pytest.raises(RuntimeError, match="AUTH_DISABLED"):
        config.Settings()


@pytest.mark.parametrize("secret", [*sorted(config.PUBLISHED_SECRETS), "short-and-unpublished"])
def test_a_published_or_short_secret_refuses_to_start(env, secret: str) -> None:
    env.setenv("JWT_SECRET", secret)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        config.Settings()
