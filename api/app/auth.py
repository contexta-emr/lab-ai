"""Authentication and tenant scope.

POC AUTH, SHAPED FOR WHAT COMES NEXT
    Today this service issues its own JWT against core.users, because it stands
    alone. Tomorrow it will verify the EMR's token instead. Both paths end in
    the same place: a CurrentUser with a practice_id that came from a signed
    token and never from the request.

    When the switch happens, only decode_token() changes. Every endpoint already
    depends on CurrentUser, so nothing else moves.

THE RULE THAT MATTERS
    practice_id comes from the token. Not from a query string, not from a body
    field, not from a header a client can set. An LLM or a careless client that
    could choose its own practice_id is a cross-tenant PHI leak waiting for an
    unlucky request.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.db import fetch_one

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    practice_id: int
    email: str
    role: str

    @property
    def can_review(self) -> bool:
        return self.role in ("admin", "reviewer", "clinician")

    @property
    def can_edit_master(self) -> bool:
        return self.role == "admin"


# --------------------------------------------------------------------- passwords
# PBKDF2 from the standard library rather than a dependency. Not argon2, and the
# comment says so: if this service ever holds real credentials at scale, move to
# argon2id. For a POC against seeded users, 480k iterations of SHA-256 is honest.
def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 480_000)
    return f"pbkdf2_sha256$480000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded or encoded.count("$") != 3:
        return False
    _, iterations, salt_hex, digest_hex = encoded.split("$")
    expected = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
    )
    return hmac.compare_digest(expected.hex(), digest_hex)


# ------------------------------------------------------------------------ tokens
def issue_token(user_id: int, practice_id: int, email: str, role: str) -> str:
    cfg = settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "practice_id": practice_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=cfg.jwt_ttl_minutes),
        "iss": "contexta-lab-idp",
    }
    return jwt.encode(payload, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)


def decode_token(token: str) -> dict:
    """The one function that changes when the EMR becomes the issuer."""
    cfg = settings()
    try:
        return jwt.decode(
            token,
            cfg.jwt_secret,
            algorithms=[cfg.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> CurrentUser:
    # AUTH_DISABLED: no login, no roles. Every request runs as the practice's
    # reviewer account, which is looked up here on the SERVER. That last part
    # is the whole reason this is six lines and not zero: practice_id still
    # never comes from anything a client sends. A service that took a practice
    # id from a header or a body would be one unlucky request away from
    # showing one clinic another clinic's patients, and turning auth off for
    # convenience must not turn that into a possibility too.
    #
    # It is also still the one function the EMR replaces. When the EMR issues
    # the JWT, this is what changes, and nothing else - which is what
    # CLAUDE.md section 2 promised when it called this auth a POC.
    if settings().auth_disabled:
        row = fetch_one(
            "SELECT id, practice_id, email, role FROM core.users "
            "WHERE is_active = TRUE AND is_deleted = FALSE "
            "  AND role IN (%s, %s, %s) ORDER BY id LIMIT 1",
            ("reviewer", "clinician", "admin"),
        )
        if row is None:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "No reviewer account exists. Apply db/013."
            )
        return CurrentUser(
            user_id=row["id"],
            practice_id=row["practice_id"],
            email=row["email"],
            role=row["role"],
        )

    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authorization header missing")

    claims = decode_token(credentials.credentials)
    user_id = int(claims["sub"])
    practice_id = int(claims["practice_id"])

    # The token could be valid and the user since disabled. Check every request:
    # a revoked reviewer should stop being able to verify documents immediately,
    # not when their token happens to expire.
    row = fetch_one(
        "SELECT id, practice_id, email, role FROM core.users "
        "WHERE id = %s AND practice_id = %s AND is_active = TRUE AND is_deleted = FALSE",
        (user_id, practice_id),
    )
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is no longer active")

    return CurrentUser(
        user_id=row["id"],
        practice_id=row["practice_id"],
        email=row["email"],
        role=row["role"],
    )


CurrentUserDep = Annotated[CurrentUser, Depends(current_user)]


def require_reviewer(user: CurrentUserDep) -> CurrentUser:
    # With AUTH_DISABLED there are no roles to check, so this waves everything
    # through. It stays in the signature of every endpoint that verifies a
    # document, because that is the list of actions that will need a role
    # again the moment real users exist, and reconstructing that list later
    # from memory is how one gets missed.
    if settings().auth_disabled:
        return user
    if not user.can_review:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "This action needs a reviewer or clinician role"
        )
    return user


ReviewerDep = Annotated[CurrentUser, Depends(require_reviewer)]
