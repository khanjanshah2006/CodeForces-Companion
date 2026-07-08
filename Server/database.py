"""
database.py — Async Connection Pool for Supabase PostgreSQL
============================================================
Manages the full asynchronous connection lifecycle to the remote Supabase
cloud instance. All DB access across the application must route through
the `get_db` dependency injector exported here.
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

# ---------------------------------------------------------------------------
# Environment Bootstrap
# ---------------------------------------------------------------------------
# Load variables from the .env file sitting at the project root.
# os.path gymnastics ensure this works regardless of the CWD at launch time.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL: str | None = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fail loudly and early — a missing connection string is unrecoverable.
    raise ValueError(
        "CRITICAL: DATABASE_URL environment variable is not set. "
        "Add it to your .env file (e.g. postgresql+asyncpg://user:pass@host/db)."
    )

# ---------------------------------------------------------------------------
# Async Engine
# ---------------------------------------------------------------------------
# `create_async_engine` is the SQLAlchemy 2.0 entry-point for non-blocking
# database access. The driver implied by the URL must be async-capable
# (e.g. asyncpg for PostgreSQL).
#
# pool_size=5      — The number of *permanent* connections kept alive in the
#                    pool. Sufficient for moderate concurrent traffic.
# max_overflow=10  — Extra connections that may be opened above pool_size
#                    during traffic spikes; they are closed once demand drops.
# echo=False       — Disable per-statement SQL logging in production.
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------
# `async_sessionmaker` returns a factory that produces `AsyncSession` objects
# on demand. Configured once here to avoid scattered session configuration.
#
# expire_on_commit=False — By default SQLAlchemy expires all ORM attributes
#                          after a commit, forcing a new SELECT on next access.
#                          In async contexts this causes DetachedInstanceErrors
#                          because the session may already be closed when the
#                          Pydantic response model reads the object. Disabling
#                          expiry lets us safely return committed objects to
#                          FastAPI without re-attaching them to a session.
#
# autoflush=False        — We control flushes explicitly via session.flush()
#                          or session.commit(), preventing accidental early writes.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------
# All ORM model classes must inherit from this Base so that SQLAlchemy's
# MetaData registry is aware of their table definitions when `create_all`
# is called in init_db.py.
Base = declarative_base()


# ---------------------------------------------------------------------------
# FastAPI Dependency: get_db
# ---------------------------------------------------------------------------
async def get_db():
    """
    Async generator that yields a transactional database session.

    Intended for use as a FastAPI dependency:
        async def my_endpoint(db: AsyncSession = Depends(get_db)): ...

    Lifecycle:
      1. A new `AsyncSession` is opened via the pool.
      2. The session is yielded to the route handler.
      3. The `async with` context manager guarantees the session is closed
         and the underlying connection is returned to the pool, even if an
         exception propagates out of the route handler.
    """
    async with AsyncSessionLocal() as session:
        yield session
