"""Contexta Lab IDP - FastAPI service.

    uvicorn app.main:app --reload

Docs at /docs, health at /health. Everything else needs a bearer token.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from app.auth import CurrentUserDep, issue_token, verify_password
from app.config import settings
from app.db import close_pool, fetch_one, healthcheck, pool
from app.routers import documents, master, patients, review
from app.schemas import InvalidIdError, LoginRequest, TokenResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
)
log = logging.getLogger("lab-idp")


class _NoQueryStrings(logging.Filter):
    """Keep query strings out of uvicorn's access log - review B9.

    Patient search sends what was typed as ?q=, so the log was recording patient
    names: GET /patients?q=Aadhya. The path stays; it carries only ids.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # uvicorn logs '%s - "%s %s HTTP/%s" %d', the path third.
        if isinstance(record.args, tuple) and len(record.args) == 5:
            client, method, path, version, code = record.args
            record.args = (client, method, str(path).split("?", 1)[0], version, code)
        return True


logging.getLogger("uvicorn.access").addFilter(_NoQueryStrings())


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
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

# ---------------------------------------------------------------------- errors
# Review B7. Three rules: the browser can always read an error, the caller is
# told its own mistakes, and the server's mistakes stay in the server's log.

#: SQLSTATEs the lab.fn_* functions raise on purpose, and what each means to the
#: caller. A RAISE with no ERRCODE is P0001, and it is a message a person wrote
#: for the caller. Every other database error is a server fault.
CLIENT_SQLSTATES = {
    "P0002": status.HTTP_404_NOT_FOUND,  # "document 5 not found in practice 1"
    "23505": status.HTTP_409_CONFLICT,  # that UHID is already registered
    "P0001": status.HTTP_400_BAD_REQUEST,  # "no analyte with code XYZ"
    "22023": status.HTTP_400_BAD_REQUEST,  # invalid_parameter_value
    "22001": status.HTTP_400_BAD_REQUEST,  # string_data_right_truncation
    "22004": status.HTTP_400_BAD_REQUEST,  # null_value_not_allowed
    "23502": status.HTTP_400_BAD_REQUEST,  # not_null_violation
}


def _server_error(request: Request, exc: BaseException) -> JSONResponse:
    """A 500 that names a reference to search the log for, and nothing else."""
    ref = uuid.uuid4().hex[:12]
    log.error(
        "unhandled %s on %s %s - ref %s",
        type(exc).__name__,
        request.method,
        request.url.path,  # never the query string: see _NoQueryStrings
        ref,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Something went wrong on our side. Reference {ref}.", "ref": ref},
    )


# REGISTERED BEFORE CORSMiddleware, AND IT MUST STAY THERE.
#
# Starlette answers an unhandled exception in ServerErrorMiddleware, which sits
# outside every middleware added here - including CORS. So a 500 went out with
# no Access-Control-Allow-Origin, and all the console could say was "Failed to
# fetch". Middleware added first sits innermost, so CORS now wraps this one.
@app.middleware("http")
async def unhandled_errors(request: Request, call_next: RequestResponseEndpoint) -> Response:
    try:
        return await call_next(request)
    except Exception as exc:  # noqa: BLE001 - this is the last line; it logs everything
        return _server_error(request, exc)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(InvalidIdError)
async def invalid_id_handler(_request: Request, exc: InvalidIdError) -> JSONResponse:
    """A malformed id is the caller's mistake, not a server fault."""
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


@app.exception_handler(psycopg.Error)
async def database_error_handler(request: Request, exc: psycopg.Error) -> JSONResponse:
    """A refusal from a lab.fn_* function, as the status code it means."""
    code = CLIENT_SQLSTATES.get(exc.sqlstate or "")
    if code is None:
        return _server_error(request, exc)
    return JSONResponse(
        status_code=code, content={"detail": exc.diag.message_primary or "Request refused."}
    )


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness plus enough to prove the vocabulary is actually loaded."""
    try:
        info = healthcheck()
    except Exception as exc:
        # The reason goes to the log, never the response - review B8. This needs
        # no token, and a connection error names the host, the port and the user,
        # sometimes as "password authentication failed for user labidp".
        log.exception("health check: database unreachable")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "database unreachable"
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
