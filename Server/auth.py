"""
auth.py — JWT Utilities & FastAPI Authentication Dependency
===========================================================
Provides:
  - create_access_token(cf_handle)  : Mint a signed HS256 JWT.
  - decode_access_token(token)      : Verify and decode a JWT.
  - get_current_user(token, db)     : FastAPI dependency that returns the
                                      authenticated AppUser or raises HTTP 401.
"""

import os
import datetime
import logging
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — read from .env
# ---------------------------------------------------------------------------
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "changeme-insecure-default-key")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_DAYS: int = int(os.getenv("JWT_EXPIRE_DAYS", "7"))

# HTTPBearer extracts the token from  "Authorization: Bearer <token>"
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Token Creation
# ---------------------------------------------------------------------------
def create_access_token(cf_handle: str) -> str:
    """
    Mint a signed JWT that encodes the CF handle as the subject claim.
    Token is valid for JWT_EXPIRE_DAYS calendar days from now (UTC).
    """
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        days=JWT_EXPIRE_DAYS
    )
    payload = {
        "sub": cf_handle,
        "exp": expire,
        "iat": datetime.datetime.now(datetime.timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Token Decoding
# ---------------------------------------------------------------------------
def decode_access_token(token: str) -> Optional[str]:
    """
    Decode and verify a JWT.  Returns the CF handle (sub claim) on success,
    or None if the token is invalid / expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# FastAPI Dependency: get_current_user
# ---------------------------------------------------------------------------
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """
    FastAPI dependency.  Validates the Bearer token in the Authorization header
    and returns the matching AppUser row from the database.

    Raises HTTP 401 when:
      - No Authorization header is present.
      - The token is malformed, expired, or the subject claim is missing.
      - No AppUser row exists for the embedded cf_handle.

    NOTE: The db session is intentionally NOT injected here via Depends(get_db)
    to avoid a circular import at module load time. The session factory is
    imported lazily inside the function body.
    """
    from fastapi import Request as _Request

    _unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Please verify your Codeforces handle first.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise _unauthorized

    cf_handle = decode_access_token(credentials.credentials)
    if not cf_handle:
        raise _unauthorized

    return cf_handle  # route handlers look up the AppUser themselves

