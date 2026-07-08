"""
sync_service.py — Database Synchronisation Service
====================================================
Provides the async persistence layer that writes processed Codeforces data
into the PostgreSQL (Supabase) tables managed by SQLAlchemy 2.0 ORM.

Responsibilities
----------------
- Upsert a ``User`` row (insert on first sync, update on subsequent syncs).
- Always insert a fresh ``HistoricalAnalytics`` snapshot so that per-sync
  history is preserved for trend analysis.
- Guarantee atomic writes: any exception triggers a full rollback before
  the error is propagated to the caller.
"""

import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

try:
    from .models import HistoricalAnalytics, User
    from .data_transformer import AnalyticsSummaryResponse
except ImportError:
    from models import HistoricalAnalytics, User
    from data_transformer import AnalyticsSummaryResponse

logger = logging.getLogger(__name__)


async def sync_user_data(
    db: AsyncSession,
    summary: AnalyticsSummaryResponse,
) -> User:
    """
    Persist a fresh ``AnalyticsSummaryResponse`` snapshot to the database.

    The function performs two writes inside a single transaction:

    1. **Upsert** the ``users`` row identified by ``summary.handle``:
       - If the user already exists, update their rating fields and
         ``last_synced_at`` timestamp.
       - If the user does not exist, create and add a new ``User`` object.

    2. **Insert** a new ``HistoricalAnalytics`` record linked to the user,
       capturing the full analytics snapshot at the current point in time.

    After a successful commit the ``user`` object is refreshed from the
    database and returned to the caller.

    Parameters
    ----------
    db:
        An active SQLAlchemy async session provided by the dependency
        injection layer (e.g. FastAPI ``Depends``).
    summary:
        A fully populated ``AnalyticsSummaryResponse`` produced by
        ``CodeforcesDataProcessor.process_submissions()``.

    Returns
    -------
    User
        The persisted (and refreshed) ``User`` ORM object.

    Raises
    ------
    Exception
        Any database-level error is caught, triggers an ``await db.rollback()``,
        and is re-raised so the caller (or middleware) can handle it cleanly
        without leaving the session in a hung-transaction state.
    """
    try:
        # ------------------------------------------------------------------
        # Step 1: Find or Create User (Upsert)
        # ------------------------------------------------------------------
        result = await db.execute(
            select(User).where(User.cf_handle == summary.handle)
        )
        user: User | None = result.scalars().first()

        if user is not None:
            # User already exists — update live rating snapshot and sync timestamp.
            logger.info(
                "Updating existing user '%s' (id=%s).", summary.handle, user.id
            )
            user.current_rating = summary.current_rating
            user.max_rating = summary.max_rating
            user.rank = summary.rank
            user.last_synced_at = datetime.datetime.now(datetime.timezone.utc)
        else:
            # First-time sync — create a fresh User row.
            logger.info("Creating new user record for handle '%s'.", summary.handle)
            user = User(
                cf_handle=summary.handle,
                current_rating=summary.current_rating,
                max_rating=summary.max_rating,
                rank=summary.rank,
                last_synced_at=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(user)

        # Flush so that the UUID primary key is generated and available
        # for the foreign-key reference in the next step.
        await db.flush()

        # ------------------------------------------------------------------
        # Step 2: Insert a New Analytics Snapshot
        # ------------------------------------------------------------------
        # ``under_explored_tags`` is populated from ``summary.untried_tags``
        # (tags the user has never attempted), stored as a JSONB list in PG.
        analytics_record = HistoricalAnalytics(
            user_id=user.id,
            overall_acceptance_rate=summary.overall_acceptance_rate,
            top_issue_verdict=summary.top_issue_verdict,
            weak_tags=summary.weak_tags,
            strong_tags=summary.strong_tags,
            under_explored_tags=summary.untried_tags,
        )
        db.add(analytics_record)

        logger.info(
            "Inserted analytics snapshot for user '%s' (user_id=%s).",
            summary.handle,
            user.id,
        )

        # ------------------------------------------------------------------
        # Step 3: Commit & Refresh
        # ------------------------------------------------------------------
        await db.commit()
        await db.refresh(user)

        logger.info(
            "sync_user_data completed successfully for handle '%s'.", summary.handle
        )
        return user

    except Exception:
        logger.exception(
            "Database error during sync for handle '%s'. Rolling back transaction.",
            summary.handle,
        )
        await db.rollback()
        raise
