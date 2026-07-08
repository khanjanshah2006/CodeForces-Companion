"""
auth_router.py — Codeforces TLE Proof-of-Ownership Authentication
==================================================================
Implements a passwordless authentication mechanism where users prove
ownership of a Codeforces handle by intentionally triggering a
Time-Limit-Exceeded (TLE) verdict on a randomly assigned problem.

Endpoints
---------
  POST /challenge/{handle}  — Issue a TLE challenge for a CF handle.
  POST /verify/{handle}     — Verify the TLE submission and issue a JWT.
  GET  /me                  — Return the currently authenticated user's info.
"""

import datetime
import logging
import os
import random
from dataclasses import dataclass, field
from typing import Dict, Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)

CHALLENGE_EXPIRE_MINUTES: int = int(os.getenv("CHALLENGE_EXPIRE_MINUTES", "15"))

# ---------------------------------------------------------------------------
# Pool of easy challenge problems — trivially TLE-able with an infinite loop.
# Each entry: contestId (int) + index (str) that together form the problem_id.
# ---------------------------------------------------------------------------
CHALLENGE_PROBLEMS = [
    {"contest_id": 1,   "index": "A", "id": "1A",   "title": "Theatre Square",
     "url": "https://codeforces.com/problemset/problem/1/A"},
    {"contest_id": 4,   "index": "A", "id": "4A",   "title": "Watermelon",
     "url": "https://codeforces.com/problemset/problem/4/A"},
    {"contest_id": 71,  "index": "A", "id": "71A",  "title": "Way Too Long Words",
     "url": "https://codeforces.com/problemset/problem/71/A"},
    {"contest_id": 118, "index": "A", "id": "118A", "title": "Stockbroker Gump",
     "url": "https://codeforces.com/problemset/problem/118/A"},
    {"contest_id": 158, "index": "A", "id": "158A", "title": "Next Round",
     "url": "https://codeforces.com/problemset/problem/158/A"},
    {"contest_id": 263, "index": "A", "id": "263A", "title": "Beautiful Matrix",
     "url": "https://codeforces.com/problemset/problem/263/A"},
    {"contest_id": 50,  "index": "A", "id": "50A",  "title": "Domino piling",
     "url": "https://codeforces.com/problemset/problem/50/A"},
    {"contest_id": 339, "index": "A", "id": "339A", "title": "Helpful Maths",
     "url": "https://codeforces.com/problemset/problem/339/A"},
]

TLE_SNIPPET = "while True:\n    pass"

# ---------------------------------------------------------------------------
# In-memory challenge store  (short-lived, no DB needed)
# ---------------------------------------------------------------------------
@dataclass
class ChallengeEntry:
    problem_id: str       # e.g. "4A"
    contest_id: int       # e.g. 4
    index: str            # e.g. "A"
    problem_url: str
    problem_title: str
    issued_at: datetime.datetime         # UTC
    expires_at: datetime.datetime        # UTC


ACTIVE_CHALLENGES: Dict[str, ChallengeEntry] = {}


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------
class ChallengeResponse(BaseModel):
    problem_id: str
    problem_title: str
    problem_url: str
    expires_at: str         # ISO-8601 UTC string
    snippet: str


class VerifyResponse(BaseModel):
    status: str             # "ok" | "pending" | "expired"
    access_token: Optional[str] = None
    token_type: str = "bearer"
    cf_handle: Optional[str] = None


class MeResponse(BaseModel):
    cf_handle: str
    created_at: str
    last_verified_at: str


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/auth", tags=["auth"])


def _get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


# ---------------------------------------------------------------------------
# POST /auth/challenge/{handle}
# ---------------------------------------------------------------------------
@router.post(
    "/challenge/{handle}",
    response_model=ChallengeResponse,
    summary="Issue a TLE ownership challenge for a CF handle",
)
async def issue_challenge(
    handle: str,
    request: Request,
    client: httpx.AsyncClient = Depends(_get_http_client),
) -> ChallengeResponse:
    handle = handle.strip()

    # 1. Validate the handle exists on Codeforces.
    info_url = f"https://codeforces.com/api/user.info?handles={handle}"
    try:
        resp = await client.get(info_url)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.error("CF user.info request failed for '%s': %s", handle, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot reach the Codeforces API right now. Please try again.",
        )

    if data.get("status") != "OK" or not data.get("result"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Codeforces handle '{handle}' does not exist.",
        )

    # 2. Pick a random challenge problem.
    problem = random.choice(CHALLENGE_PROBLEMS)

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    expires_at = now_utc + datetime.timedelta(minutes=CHALLENGE_EXPIRE_MINUTES)

    # 3. Store in the in-memory challenge map (overwrites any previous challenge).
    ACTIVE_CHALLENGES[handle.lower()] = ChallengeEntry(
        problem_id=problem["id"],
        contest_id=problem["contest_id"],
        index=problem["index"],
        problem_url=problem["url"],
        problem_title=problem["title"],
        issued_at=now_utc,
        expires_at=expires_at,
    )

    logger.info(
        "Challenge issued for '%s': problem=%s, expires=%s",
        handle, problem["id"], expires_at.isoformat(),
    )

    return ChallengeResponse(
        problem_id=problem["id"],
        problem_title=problem["title"],
        problem_url=problem["url"],
        expires_at=expires_at.isoformat(),
        snippet=TLE_SNIPPET,
    )


# ---------------------------------------------------------------------------
# POST /auth/verify/{handle}
# ---------------------------------------------------------------------------
@router.post(
    "/verify/{handle}",
    response_model=VerifyResponse,
    status_code=200,
    summary="Verify TLE submission and issue JWT on success",
)
async def verify_challenge(
    handle: str,
    request: Request,
    client: httpx.AsyncClient = Depends(_get_http_client),
    db: AsyncSession = Depends(lambda: None),  # overridden below via __init__
) -> VerifyResponse:
    # Re-import db dependency properly
    try:
        from .database import get_db
    except ImportError:
        from database import get_db

    try:
        from .models import AppUser
    except ImportError:
        from models import AppUser

    try:
        from .auth import create_access_token
    except ImportError:
        from auth import create_access_token

    handle = handle.strip()
    key = handle.lower()

    # 1. Look up the active challenge.
    challenge = ACTIVE_CHALLENGES.get(key)
    if challenge is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active challenge for this handle. Please request a new one.",
        )

    # 2. Check expiry.
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if now_utc > challenge.expires_at:
        del ACTIVE_CHALLENGES[key]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge expired. Please request a new one.",
        )

    # 3. Fetch recent submissions from Codeforces.
    status_url = (
        f"https://codeforces.com/api/user.status"
        f"?handle={handle}&from=1&count=30"
    )
    try:
        resp = await client.get(status_url)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.error("CF user.status request failed for '%s': %s", handle, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot reach the Codeforces API. Please try again.",
        )

    submissions = data.get("result", [])

    # 4. Search for a matching TLE submission made after the challenge was issued.
    issued_ts = challenge.issued_at.timestamp()
    found_tle = False

    for sub in submissions:
        if sub.get("verdict") != "TIME_LIMIT_EXCEEDED":
            continue
        sub_ts = sub.get("creationTimeSeconds", 0)
        if sub_ts <= issued_ts:
            continue
        prob = sub.get("problem", {})
        sub_contest_id = prob.get("contestId")
        sub_index = prob.get("index", "")
        if sub_contest_id == challenge.contest_id and sub_index == challenge.index:
            found_tle = True
            break

    if not found_tle:
        # Return 202 so the frontend knows to keep polling.
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=202,
            content={"status": "pending"},
        )

    # 5. TLE confirmed — upsert AppUser.
    async with request.app.state.db_session_factory() as session:
        result = await session.execute(
            select(AppUser).where(AppUser.cf_handle == handle)
        )
        app_user = result.scalars().first()

        if app_user is None:
            app_user = AppUser(cf_handle=handle)
            session.add(app_user)
        else:
            app_user.last_verified_at = now_utc

        await session.commit()
        await session.refresh(app_user)

    # 6. Clear challenge and mint JWT.
    del ACTIVE_CHALLENGES[key]
    token = create_access_token(handle)

    logger.info("Handle '%s' verified via TLE — JWT issued.", handle)
    return VerifyResponse(
        status="ok",
        access_token=token,
        cf_handle=handle,
    )


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=MeResponse,
    summary="Return the currently authenticated user's profile",
)
async def get_me(
    request: Request,
    db: AsyncSession = Depends(lambda: None),
) -> MeResponse:
    """
    Protected endpoint — requires a valid Bearer JWT.
    Used by the frontend to restore sessions on page refresh.
    """
    try:
        from .auth import get_current_user
    except ImportError:
        from auth import get_current_user

    # Extract credentials manually since we can't easily inject bearer_scheme here
    # without restructuring. Use the helper directly.
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        from .auth import decode_access_token
    except ImportError:
        from auth import decode_access_token

    try:
        from .models import AppUser
    except ImportError:
        from models import AppUser

    token = auth_header[7:]
    cf_handle = decode_access_token(token)
    if not cf_handle:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with request.app.state.db_session_factory() as session:
        result = await session.execute(
            select(AppUser).where(AppUser.cf_handle == cf_handle)
        )
        app_user = result.scalars().first()

    if app_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return MeResponse(
        cf_handle=app_user.cf_handle,
        created_at=app_user.created_at.isoformat(),
        last_verified_at=app_user.last_verified_at.isoformat(),
    )
