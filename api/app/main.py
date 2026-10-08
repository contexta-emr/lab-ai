"""Contexta Lab IDP - FastAPI service.

    uvicorn app.main:app --reload

Docs at /docs, health at /health. Everything else needs a bearer token.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import CurrentUserDep, issue_token, verify_password
from app.config import settings
from app.db import close_pool, fetch_one, healthcheck, pool
from app.routers import documents, master, patients, review
from app.schemas import LoginRequest, TokenResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
)
log = logging.getLogger("lab-idp")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    cfg = settings()
    pool()  # fail fast if the database is unreachable
    log.info("started in %s, storage at %s", cfg.environment, cfg.storage_dir)
    yield
    close_pool()


app = FastAPI(
    title="Contexta Lab IDP",
    version="0.1.0",
    summary="Read a lab report, find the patient, store the results.",
    description=(
        "Upload a lab report; the service extracts it, matches the patient from "
        "the UHID printed on the page, resolves every printed test name to a "
        "canonical code, and stores the result.\n\n"
        "**Nothing is clinical fact until a human verifies it.** Parsed documents "
        "sit in a review queue; only verified ones appear in trends."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    """A bad id or a bad enum is the caller's mistake, not a server fault."""
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness plus enough to prove the vocabulary is actually loaded."""
    try:
        info = healthcheck()
    except Exception as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, f"database unreachable: {exc}"
        ) from exc
    ready = info.get("analytes", 0) > 0
    return {
        "status": "ok" if ready else "degraded",
        "database": info.get("database"),
        "analytes": info.get("analytes", 0),
        "aliases": info.get("aliases", 0),
        "note": None
        if ready
        else "The analyte master is empty. Run db/004_seed_analyte_master.sql.",
    }


@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login(body: LoginRequest) -> TokenResponse:
    """POC login against core.users.

    Swapped for EMR token verification later; only app.auth.decode_token changes.
    """
    row = fetch_one(
        "SELECT id, practice_id, email, role, password_hash FROM core.users "
        "WHERE email = %s AND is_active = TRUE AND is_deleted = FALSE",
        (body.email.lower().strip(),),
    )
    # Same error either way: a different message for "no such user" tells an
    # attacker which addresses are real.
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    cfg = settings()
    return TokenResponse(
        access_token=issue_token(row["id"], row["practice_id"], row["email"], row["role"]),
        expires_in_minutes=cfg.jwt_ttl_minutes,
        user_id=str(row["id"]),
        practice_id=str(row["practice_id"]),
        email=row["email"],
        role=row["role"],
    )


@app.get("/auth/me", tags=["auth"])
def me(user: CurrentUserDep) -> dict:
    return {
        "user_id": str(user.user_id),
        "practice_id": str(user.practice_id),
        "email": user.email,
        "role": user.role,
        "can_review": user.can_review,
        "can_edit_master": user.can_edit_master,
    }


app.include_router(documents.router)
app.include_router(review.router)
app.include_router(patients.router)
app.include_router(master.router)
