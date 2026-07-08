"""
models.py — SQLAlchemy 2.0 ORM Schema Blueprint
================================================
Defines the three relational PostgreSQL tables used by the Codeforces
Companion Platform. All models use the strict SQLAlchemy 2.0 `Mapped`
typed paradigm — legacy `Column(...)` syntax is intentionally absent.

Tables
------
- users               : Primary user identity and live rating snapshot.
- historical_analytics: Per-sync analytics snapshots (weak/strong tags, etc.).
- potd_ledger         : Daily problem assignments and their completion status.
"""

import datetime
import uuid
from typing import Any, Dict, List

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

# `Base` is defined in database.py so that the MetaData registry is shared
# across the whole application. Importing it here registers every subclass
# automatically when this module is imported.
try:
    # Works when imported as part of the Server package (e.g. python -m Server.init_db)
    from .database import Base
except ImportError:
    # Works when run directly from inside the Server/ directory
    from database import Base


# ---------------------------------------------------------------------------
# Table 1: users
# ---------------------------------------------------------------------------
class User(Base):
    """
    Represents a unique Codeforces user tracked by the platform.

    `cf_handle` is the natural unique key (Codeforces usernames are globally
    unique), but we use a surrogate UUID as the PK for join performance and to
    insulate FK references from handle-change edge cases.
    """

    __tablename__ = "users"

    # Primary key — UUID generated on the Python side so it is available
    # before the INSERT round-trip completes.
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # The Codeforces handle; uniquely indexed for fast O(1) lookups by handle.
    cf_handle: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )

    current_rating: Mapped[int] = mapped_column(Integer, default=0)
    max_rating: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[str] = mapped_column(String(50), default="unrated")

    # `DateTime(timezone=True)` stores an TIMESTAMPTZ column in PostgreSQL,
    # which preserves the UTC offset and prevents silent drift when cloud
    # servers operate in different regional timezones.
    last_synced_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    # --- Relationships ---
    # `cascade="all, delete-orphan"` propagates deletes so that removing a
    # User row automatically removes all child analytics and POTD records
    # without requiring a manual cascade query.
    analytics_history: Mapped[List["HistoricalAnalytics"]] = relationship(
        "HistoricalAnalytics",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    potd_records: Mapped[List["PotdLedger"]] = relationship(
        "PotdLedger",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User cf_handle={self.cf_handle!r} rating={self.current_rating}>"


# ---------------------------------------------------------------------------
# Table 2: historical_analytics
# ---------------------------------------------------------------------------
class HistoricalAnalytics(Base):
    """
    Stores a point-in-time analytics snapshot produced by `CodeforcesDataProcessor`
    for a given user on each sync cycle.

    JSONB columns (`weak_tags`, `strong_tags`, `under_explored_tags`) leverage
    PostgreSQL's native binary JSON storage, which supports GIN indexing and
    containment operators — significantly faster than TEXT-stored JSON for
    analytical queries filtering on nested keys.
    """

    __tablename__ = "historical_analytics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # `ondelete="CASCADE"` adds a DB-level ON DELETE CASCADE constraint,
    # complementing the ORM-level cascade defined on the User relationship.
    # This ensures orphan rows are cleaned up even when the ORM is bypassed
    # (e.g., raw SQL admin operations).
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    overall_acceptance_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # The single highest-count non-OK verdict, e.g. "WRONG_ANSWER".
    top_issue_verdict: Mapped[str] = mapped_column(String(50), default="")

    # JSONB columns store rich structured data (lists of tag dicts) natively
    # in PostgreSQL without an extra serialisation round-trip on reads.
    # Example shape: [{"tag": "dp", "failure_index": 0.75, ...}, ...]
    weak_tags: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    strong_tags: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    under_explored_tags: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # --- Relationship ---
    user: Mapped["User"] = relationship("User", back_populates="analytics_history")

    def __repr__(self) -> str:
        return (
            f"<HistoricalAnalytics user_id={self.user_id} "
            f"recorded_at={self.recorded_at}>"
        )


# ---------------------------------------------------------------------------
# Table 3: potd_ledger
# ---------------------------------------------------------------------------
class PotdLedger(Base):
    """
    Ledger tracking which Problem-of-the-Day (POTD) was assigned to a user
    on a given calendar date and whether they have completed it.

    `assigned_date` is indexed because the POTD engine performs range-date
    queries (e.g., "fetch all problems assigned this week").
    `status` is indexed to efficiently filter PENDING vs COMPLETED rows
    across large ledgers.
    """

    __tablename__ = "potd_ledger"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # `Date` stores a plain calendar date (no time component) — appropriate
    # for POTD assignment which is a per-day concept, not per-instant.
    assigned_date: Mapped[datetime.date] = mapped_column(
        Date, default=datetime.date.today, index=True
    )

    # Codeforces problem identifier, e.g. "1520F".
    problem_id: Mapped[str] = mapped_column(String(20), nullable=False)
    problem_title: Mapped[str] = mapped_column(String(200), nullable=False)
    problem_tag: Mapped[str] = mapped_column(String(255), nullable=False)

    # Difficulty corresponds to the Codeforces problem rating integer.
    difficulty: Mapped[int] = mapped_column(Integer, default=0)

    # Lifecycle states: "PENDING" → "COMPLETED" (or "SKIPPED" in future).
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)

    # --- Relationship ---
    user: Mapped["User"] = relationship("User", back_populates="potd_records")

    def __repr__(self) -> str:
        return (
            f"<PotdLedger user_id={self.user_id} "
            f"problem_id={self.problem_id!r} status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# Table 4: app_users
# ---------------------------------------------------------------------------
class AppUser(Base):
    """
    Represents a registered platform account authenticated via the
    Codeforces TLE proof-of-ownership flow.

    The CF handle is the sole identity — no email or password is stored.
    `created_at`      is set on first-time verification.
    `last_verified_at` is refreshed on every subsequent re-login.
    """

    __tablename__ = "app_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Codeforces handle — the only identity token we need.
    cf_handle: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    last_verified_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<AppUser cf_handle={self.cf_handle!r}>"

