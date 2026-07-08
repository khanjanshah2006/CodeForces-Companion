"""
potd_service.py — Algorithmic Problem-of-the-Day (POTD) Scheduling Engine
==========================================================================
Implements a three-stage deterministic pipeline that selects a personalised
daily Codeforces problem for a given user:

  Stage 1 – _calculate_daily_target : decides the *what* (tags + rating window)
              based on the 50-30-20 day-of-week learning balance matrix.
  Stage 2 – _fetch_and_filter_problems : hits the Codeforces global problemset
              API and runs a three-pass filtering funnel with O(1) exclusion.
  Stage 3 – generate_or_get_potd     : the public entry-point; enforces
              idempotency via the `potd_ledger` table and persists the result.

JSONB shape contracts (from sync_service.py / data_transformer.py)
-------------------------------------------------------------------
  analytics.weak_tags         → List[Dict]  e.g. [{"tag": "dp", "failure_index": 0.75, ...}]
  analytics.strong_tags       → List[Dict]  same shape as weak_tags
  analytics.under_explored_tags → List[str] e.g. ["geometry", "games", ...]
"""

import datetime
import logging
import random
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

try:
    from .models import HistoricalAnalytics, PotdLedger, User
except ImportError:
    from models import HistoricalAnalytics, PotdLedger, User

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Day-of-week category constants (Python weekday(): 0 = Monday, 6 = Sunday)
# ---------------------------------------------------------------------------
# Core Focus days (50% allocation) — attack the user's *weakest* topics with
# problems that are slightly above their current comfort zone.
_CORE_FOCUS_DAYS: frozenset[int] = frozenset({0, 2, 4})  # Mon, Wed, Fri

# Breadth & Maintenance days (30% allocation) — explore under-represented topics
# at a rating level that is achievable to build confidence.
_BREADTH_DAYS: frozenset[int] = frozenset({1, 3})  # Tue, Thu

# Speed/Conditioning days (20% allocation) — reinforce the user's *strongest*
# topics with easier problems to maximise speed and solidify fundamentals.
_SPEED_DAYS: frozenset[int] = frozenset({5, 6})  # Sat, Sun

# Fallback tags used when all analytics lists are empty (new / cold-start user).
_FALLBACK_TAGS: list[str] = ["implementation", "math"]

# Codeforces global problemset API endpoint.
_CF_PROBLEMSET_URL: str = "https://codeforces.com/api/problemset.problems"

# Rating expansion applied when the strict filter yields zero candidates.
_FALLBACK_RATING_EXPAND: int = 200


# ---------------------------------------------------------------------------
# Stage 1 — Daily Target Calculator
# ---------------------------------------------------------------------------

def _calculate_daily_target(
    user: User,
    analytics: HistoricalAnalytics,
) -> tuple[list[str], int, int]:
    """
    Determine the target tag list and rating window for today's problem
    based on the 50-30-20 day-of-week learning balance matrix.

    Parameters
    ----------
    user:
        The ORM ``User`` object; provides ``current_rating``.
    analytics:
        The most recent ``HistoricalAnalytics`` snapshot; provides
        ``weak_tags``, ``strong_tags``, and ``under_explored_tags``.

    Returns
    -------
    tuple[list[str], int, int]
        ``(target_tags, min_rating, max_rating)``

    Day-of-Week Matrix
    ------------------
    Monday / Wednesday / Friday  (weekday 0, 2, 4)  — CORE FOCUS (50%)
      • Rating window : current_rating + 100  →  current_rating + 200
      • Tags          : Top-3 tags from weak_tags sorted descending by
                        failure_index.  Fallback → ["implementation", "math"].

    Tuesday / Thursday           (weekday 1, 3)     — BREADTH (30%)
      • Rating window : current_rating  →  current_rating + 100
      • Tags          : under_explored_tags (List[str]).
                        Fallback → middle-slice of weak_tags tags.

    Saturday / Sunday            (weekday 5, 6)     — SPEED (20%)
      • Rating window : current_rating - 200  →  current_rating - 100
      • Tags          : Top-3 tags from strong_tags sorted ascending by
                        failure_index.  Fallback → ["implementation", "math"].
    """
    today_weekday: int = datetime.datetime.now(datetime.timezone.utc).weekday()
    rating: int = user.current_rating

    # ------------------------------------------------------------------
    # Safely coerce JSONB values to the expected Python types.
    # Under normal operation these are already lists, but defensive casting
    # guards against cold-start or schema migration edge cases.
    # ------------------------------------------------------------------
    raw_weak: list[dict[str, Any]] = analytics.weak_tags if isinstance(analytics.weak_tags, list) else []
    raw_strong: list[dict[str, Any]] = analytics.strong_tags if isinstance(analytics.strong_tags, list) else []
    raw_unexplored: list[str] = analytics.under_explored_tags if isinstance(analytics.under_explored_tags, list) else []

    if today_weekday in _CORE_FOCUS_DAYS:
        # ── CORE FOCUS (Mon / Wed / Fri) ──────────────────────────────
        # Attack weakness: problems just above the current rating ceiling.
        min_rating: int = rating + 100
        max_rating: int = rating + 200

        # Sort weak tags descending by failure_index so the hardest topic
        # is first in the list and therefore anchors the DB `problem_tag` field.
        sorted_weak = sorted(
            raw_weak,
            key=lambda d: d.get("failure_index", 0.0),
            reverse=True,
        )
        target_tags: list[str] = [d["tag"] for d in sorted_weak[:3] if "tag" in d]

        if not target_tags:
            logger.debug(
                "_calculate_daily_target: weak_tags empty for user %s; "
                "falling back to %s.",
                user.cf_handle,
                _FALLBACK_TAGS,
            )
            target_tags = list(_FALLBACK_TAGS)

    elif today_weekday in _BREADTH_DAYS:
        # ── BREADTH & MAINTENANCE (Tue / Thu) ─────────────────────────
        # Explore under-represented topics at a comfortable, achievable level.
        min_rating = rating
        max_rating = rating + 100

        # under_explored_tags is stored as a flat List[str] of tag names.
        target_tags = list(raw_unexplored[:3]) if raw_unexplored else []

        if not target_tags:
            # Fallback: pull from the *middle* of weak_tags — these are
            # mediocre tags (not the worst, not the best) that benefit from
            # targeted breadth practice.
            sorted_weak = sorted(
                raw_weak,
                key=lambda d: d.get("failure_index", 0.0),
                reverse=True,
            )
            mid_start: int = len(sorted_weak) // 4
            mid_slice = sorted_weak[mid_start: mid_start + 3]
            target_tags = [d["tag"] for d in mid_slice if "tag" in d]

        if not target_tags:
            logger.debug(
                "_calculate_daily_target: under_explored_tags and weak_tags both "
                "empty for user %s; falling back to %s.",
                user.cf_handle,
                _FALLBACK_TAGS,
            )
            target_tags = list(_FALLBACK_TAGS)

    elif today_weekday in _SPEED_DAYS:
        # ── SPEED / CONDITIONING (Sat / Sun) ──────────────────────────
        # Reinforce strengths: easier problems to maximise solve speed.
        min_rating = rating - 200
        max_rating = rating - 100

        # Sort strong tags ascending by failure_index — lowest failure rate
        # means most comfortable, ideal for speed conditioning.
        sorted_strong = sorted(
            raw_strong,
            key=lambda d: d.get("failure_index", 0.0),
        )
        target_tags = [d["tag"] for d in sorted_strong[:3] if "tag" in d]

        if not target_tags:
            logger.debug(
                "_calculate_daily_target: strong_tags empty for user %s; "
                "falling back to %s.",
                user.cf_handle,
                _FALLBACK_TAGS,
            )
            target_tags = list(_FALLBACK_TAGS)

    else:
        # This branch should never be reached — Python's weekday() is guaranteed
        # to return an integer in [0, 6]. A ValueError here signals a logic bug
        # (e.g., a future change to the day-set constants that leaves a gap).
        raise ValueError(
            f"Invalid weekday integer: {today_weekday}. "
            "Expected 0–6 from datetime.weekday()."
        )

    logger.info(
        "_calculate_daily_target → weekday=%d tags=%s min_r=%d max_r=%d",
        today_weekday,
        target_tags,
        min_rating,
        max_rating,
    )
    return target_tags, min_rating, max_rating


# ---------------------------------------------------------------------------
# Stage 2 — Codeforces Problemset Fetch & Filter Funnel
# ---------------------------------------------------------------------------

async def _fetch_and_filter_problems(
    target_tags: list[str],
    min_r: int,
    max_r: int,
    solved_ids: set[str],
) -> dict[str, Any]:
    """
    Fetch the global Codeforces problemset and apply the three-pass filter
    funnel to select one appropriate unsolved problem.

    Filtering Funnel
    ----------------
    Pass 1 — Tag Match   : at least one of the problem's tags must appear in
                           ``target_tags`` (set intersection, O(T) per problem).
    Pass 2 — Rating Match: ``problem['rating']`` must fall within
                           [``min_r``, ``max_r``] (inclusive).  Problems with
                           no rating field are silently dropped.
    Pass 3 — Exclusion   : the composite ID ``f"{contestId}{index}"`` must NOT
                           appear in ``solved_ids`` (O(1) set lookup).

    Graceful Degradation
    --------------------
    If the strict funnel yields zero candidates, the rating bounds are widened
    by ±200 and the funnel is re-run once.  The tag match and exclusion filters
    remain unchanged so the result is still contextually relevant.

    Parameters
    ----------
    target_tags:
        Tags the selected problem must overlap with (at least one).
    min_r / max_r:
        Inclusive lower and upper rating bounds.
    solved_ids:
        Set of CF problem IDs (e.g. ``"1520F"``) the user has already solved;
        used as the O(1) exclusion filter.

    Returns
    -------
    dict
        A single raw Codeforces problem dict from the API response.

    Raises
    ------
    RuntimeError
        If the fallback filter also yields zero candidates, or if the
        Codeforces API returns a non-OK status or network error.
    """
    # Convert target_tags to a set for O(1) intersection checks across the
    # potentially large (~9 000+) global problemset.
    target_tag_set: set[str] = set(target_tags)

    # ── Network fetch ──────────────────────────────────────────────────────
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        try:
            response = await client.get(_CF_PROBLEMSET_URL)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Codeforces problemset API returned HTTP {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(
                f"Network error reaching Codeforces problemset API: {exc}"
            ) from exc

        data = response.json()

    if data.get("status") != "OK":
        raise RuntimeError(
            f"Codeforces API status not OK: {data.get('comment', 'unknown error')}"
        )

    all_problems: list[dict[str, Any]] = data["result"]["problems"]
    logger.debug("_fetch_and_filter_problems: fetched %d total problems.", len(all_problems))

    def _apply_filters(
        problems: list[dict[str, Any]],
        lo: int,
        hi: int,
    ) -> list[dict[str, Any]]:
        """
        Inner helper: apply all three passes with the given rating bounds.

        Pass 1 — Tag Match   (keeps semantically relevant problems)
        Pass 2 — Rating Match (keeps difficulty-appropriate problems)
        Pass 3 — Exclusion   (keeps only unsolved problems)
        """
        candidates: list[dict[str, Any]] = []

        for prob in problems:
            # ── Pass 1: Tag Match ─────────────────────────────────────
            # `problem['tags']` is a list of lowercase tag strings.
            # We need at least one to intersect with our target_tag_set.
            prob_tags: list[str] = prob.get("tags", [])
            if not target_tag_set.intersection(prob_tags):
                continue  # no relevant tag — discard

            # ── Pass 2: Rating Match ──────────────────────────────────
            # Problems without a rating key are unrated and statistically
            # unreliable; we always drop them regardless of the filter bounds.
            prob_rating: int | None = prob.get("rating")
            if prob_rating is None:
                continue  # unrated problem — discard

            if not (lo <= prob_rating <= hi):
                continue  # outside rating window — discard

            # ── Pass 3: Exclusion ─────────────────────────────────────
            # Construct the canonical composite ID in the same format that
            # CodeforcesDataProcessor uses so the set lookup is always valid.
            prob_id: str = f"{prob.get('contestId', '')}{prob.get('index', '')}"
            if prob_id in solved_ids:
                continue  # already solved — discard

            candidates.append(prob)

        return candidates

    # ── Strict pass ────────────────────────────────────────────────────────
    strict_candidates = _apply_filters(all_problems, min_r, max_r)
    logger.info(
        "_fetch_and_filter_problems: strict filter (tags=%s, r=[%d,%d]) → %d candidates.",
        target_tags,
        min_r,
        max_r,
        len(strict_candidates),
    )

    if strict_candidates:
        return random.choice(strict_candidates)

    # ── Fallback pass (Graceful Degradation) ───────────────────────────────
    # The strict rating window yielded nothing.  Widen by ±200 and retry once.
    # The tag and exclusion passes are unchanged to preserve relevance.
    fallback_lo: int = min_r - _FALLBACK_RATING_EXPAND
    fallback_hi: int = max_r + _FALLBACK_RATING_EXPAND

    logger.warning(
        "_fetch_and_filter_problems: strict filter returned 0 candidates. "
        "Widening bounds to [%d, %d] and retrying.",
        fallback_lo,
        fallback_hi,
    )

    fallback_candidates = _apply_filters(all_problems, fallback_lo, fallback_hi)
    logger.info(
        "_fetch_and_filter_problems: fallback filter → %d candidates.",
        len(fallback_candidates),
    )

    if fallback_candidates:
        return random.choice(fallback_candidates)

    # Both strict and fallback passes produced nothing.  This is an extreme
    # edge case (new user with no history, or tags with near-zero CF coverage).
    raise RuntimeError(
        f"No suitable problems found for tags={target_tags} even after "
        f"widening rating bounds to [{fallback_lo}, {fallback_hi}]."
    )


# ---------------------------------------------------------------------------
# Stage 3 — Public Entry-Point
# ---------------------------------------------------------------------------

async def generate_or_get_potd(
    db: AsyncSession,
    user: User,
    analytics: HistoricalAnalytics,
    solved_ids: set[str],
) -> PotdLedger:
    """
    Return today's Problem-of-the-Day for the given user, creating it if it
    does not yet exist.

    This is the sole public function exposed to the FastAPI router.

    Lifecycle
    ---------
    Phase 1 — Idempotency Check
        Query `potd_ledger` for ``(user_id, assigned_date == today)``.
        If a record already exists, return it immediately without any API
        calls or DB writes.  This prevents multiple assignments on the same
        calendar day regardless of how many times the endpoint is called.

    Phase 2 — Calculate & Fetch
        Delegate to ``_calculate_daily_target`` to get the tag list and
        rating window for today, then call ``_fetch_and_filter_problems``
        to select an appropriate unsolved problem from the CF problemset.

    Phase 3 — Database Persistence
        Construct a ``PotdLedger`` ORM object, add it to the session,
        commit, and refresh before returning.

    Parameters
    ----------
    db:
        Active SQLAlchemy async session (injected by FastAPI ``Depends``).
    user:
        The ``User`` ORM object whose POTD is being generated.
    analytics:
        The most recent ``HistoricalAnalytics`` snapshot for this user.
    solved_ids:
        Set of CF problem IDs the user has already solved (exclusion filter).

    Returns
    -------
    PotdLedger
        The persisted (and DB-refreshed) POTD ledger record for today.

    Raises
    ------
    RuntimeError
        Propagated from ``_fetch_and_filter_problems`` if no suitable problem
        can be found even after fallback bound expansion.
    """
    # ── Phase 1: Idempotency Check ─────────────────────────────────────────
    # Use UTC date — consistent regardless of where the server process runs.
    today: datetime.date = datetime.datetime.now(datetime.timezone.utc).date()

    result = await db.execute(
        select(PotdLedger).where(
            PotdLedger.user_id == user.id,
            PotdLedger.assigned_date == today,
        )
    )
    existing_record: PotdLedger | None = result.scalars().first()

    if existing_record is not None:
        # A valid assignment already exists for today — return it immediately.
        # Never overwrite an active daily assignment (idempotency guarantee).
        logger.info(
            "generate_or_get_potd: POTD already assigned for user '%s' on %s "
            "(problem_id=%s). Returning existing record.",
            user.cf_handle,
            today,
            existing_record.problem_id,
        )
        return existing_record

    # ── Phase 2: Calculate & Fetch ─────────────────────────────────────────
    logger.info(
        "generate_or_get_potd: No POTD found for user '%s' on %s. Generating.",
        user.cf_handle,
        today,
    )

    target_tags, min_rating, max_rating = _calculate_daily_target(user, analytics)

    # Delegates to the async Codeforces API client; raises RuntimeError on failure.
    selected_problem: dict[str, Any] = await _fetch_and_filter_problems(
        target_tags=target_tags,
        min_r=min_rating,
        max_r=max_rating,
        solved_ids=solved_ids,
    )

    logger.info(
        "generate_or_get_potd: selected problem '%s%s' (%s) for user '%s'.",
        selected_problem.get("contestId", ""),
        selected_problem.get("index", ""),
        selected_problem.get("name", ""),
        user.cf_handle,
    )

    # ── Phase 3: Database Persistence ─────────────────────────────────────
    # Construct the canonical composite problem ID used throughout the platform.
    problem_id: str = (
        f"{selected_problem.get('contestId', '')}"
        f"{selected_problem.get('index', '')}"
    )

    # Find all tags for the selected problem and store them comma-separated.
    # If the problem has no tags, fallback to the first target tag.
    prob_tags = selected_problem.get("tags", [])
    assigned_tags_str = ",".join(prob_tags) if prob_tags else target_tags[0]

    new_ledger = PotdLedger(
        user_id=user.id,
        assigned_date=today,
        problem_id=problem_id,
        problem_title=selected_problem.get("name", ""),
        problem_tag=assigned_tags_str,
        difficulty=selected_problem.get("rating", 0),
        # status defaults to "PENDING" per the model definition.
    )

    try:
        db.add(new_ledger)
        await db.commit()
        await db.refresh(new_ledger)
    except Exception:
        await db.rollback()
        logger.exception(
            f"generate_or_get_potd: DB commit failed for user '{user.cf_handle}'. "
            "Transaction rolled back."
        )
        raise

    logger.info(
        "generate_or_get_potd: POTD persisted for user '%s' "
        "(ledger_id=%s, problem_id=%s, difficulty=%d).",
        user.cf_handle,
        new_ledger.id,
        new_ledger.problem_id,
        new_ledger.difficulty,
    )

    return new_ledger


# ---------------------------------------------------------------------------
# Public API: POTD Verification
# ---------------------------------------------------------------------------

async def verify_user_potd(db: AsyncSession, handle: str) -> dict:
    """
    Verify whether the user has solved their assigned POTD on Codeforces and
    update the ``potd_ledger`` row accordingly.

    Execution Pipeline
    ------------------
    Step 1 — Locate the User & Today's Ledger
        Query ``users`` by ``cf_handle``.  If absent, raise ``ValueError``
        (the router maps this to HTTP 404).
        Query ``potd_ledger`` for today's UTC date.  If no assignment exists,
        return ``{"status": "NO_POTD_GENERATED"}`` immediately — no CF call made.

    Step 2 — Idempotency Guard
        If the ledger's ``status`` is already ``"SOLVED"``, return
        ``{"status": "ALREADY_SOLVED"}`` immediately without hitting the
        Codeforces API.  Satisfies the double-click safety constraint.

    Step 3 — Lightweight Codeforces Verification Fetch
        Fetch only the 20 most recent submissions (``from=1&count=20``) to
        minimise network payload and avoid hitting Codeforces rate limits.

    Step 4 — Solve Detection
        A submission matches iff:
          ``str(contestId) + str(index) == ledger.problem_id``  AND
          ``verdict == "OK"``

    Step 5 — Database State Mutation
        On match: set ``ledger.status = "SOLVED"`` and commit inside a
        ``try/except`` that calls ``await db.rollback()`` on failure.
        On no match: return ``{"status": "STILL_PENDING"}`` — no DB write.

    Parameters
    ----------
    db:
        Active SQLAlchemy async session (injected by FastAPI ``Depends``).
    handle:
        Normalised (stripped) Codeforces handle string.

    Returns
    -------
    dict
        One of:
        ``{"status": "NO_POTD_GENERATED"}``
        ``{"status": "ALREADY_SOLVED"}``
        ``{"status": "NEWLY_SOLVED", "problem_id": str}``
        ``{"status": "STILL_PENDING"}``

    Raises
    ------
    ValueError
        If the handle does not exist in the ``users`` table.
    httpx.HTTPError
        Propagated from the Codeforces API call if the service is down or
        rate-limiting.  The router maps this to HTTP 503.
    Exception
        Any database commit failure after a ``db.rollback()`` is re-raised
        for the router to surface as HTTP 500.
    """
    # ── Step 1: Locate the User & Today's Ledger ──────────────────────────
    today: datetime.date = datetime.datetime.now(datetime.timezone.utc).date()

    user_result = await db.execute(
        select(User).where(User.cf_handle == handle)
    )
    user: User | None = user_result.scalars().first()

    if user is None:
        raise ValueError(f"User '{handle}' not found in the database.")

    ledger_result = await db.execute(
        select(PotdLedger).where(
            PotdLedger.user_id == user.id,
            PotdLedger.assigned_date == today,
        )
    )
    ledger: PotdLedger | None = ledger_result.scalars().first()

    if ledger is None:
        # No POTD has been generated for this user today — nothing to verify.
        logger.info(
            "verify_user_potd: No POTD found for user '%s' on %s.",
            handle,
            today,
        )
        return {"status": "NO_POTD_GENERATED"}

    # ── Step 2: Idempotency Guard ──────────────────────────────────────────
    # Return immediately if the status is already SOLVED — no network call needed.
    if ledger.status == "SOLVED":
        logger.info(
            "verify_user_potd: POTD for user '%s' is already SOLVED (problem_id=%s).",
            handle,
            ledger.problem_id,
        )
        return {"status": "ALREADY_SOLVED"}

    # ── Step 3: Lightweight Codeforces Verification Fetch ─────────────────
    # Fetch only the 20 most recent submissions to keep the payload minimal and
    # avoid triggering Codeforces rate limits on frequent verification calls.
    cf_verify_url = (
        f"https://codeforces.com/api/user.status"
        f"?handle={handle}&from=1&count=20"
    )

    logger.info(
        "verify_user_potd: Fetching recent submissions for user '%s' "
        "to verify problem_id=%s.",
        handle,
        ledger.problem_id,
    )

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        response = await client.get(cf_verify_url)
        response.raise_for_status()

    cf_data = response.json()
    recent_submissions: list[dict] = cf_data.get("result", [])

    # ── Step 4: Solve Detection ────────────────────────────────────────────
    # A submission is a valid match iff the composite problem ID equals the
    # ledger's stored problem_id AND the verdict is "OK".
    solved: bool = False
    for sub in recent_submissions:
        problem_node = sub.get("problem", {})
        sub_problem_id: str = (
            str(problem_node.get("contestId", ""))
            + str(problem_node.get("index", ""))
        )
        if sub_problem_id == ledger.problem_id and sub.get("verdict") == "OK":
            solved = True
            logger.info(
                "verify_user_potd: Match found — user '%s' solved problem_id=%s.",
                handle,
                ledger.problem_id,
            )
            break

    # ── Step 5: Database State Mutation ───────────────────────────────────
    if solved:
        ledger.status = "SOLVED"
        try:
            await db.commit()
            logger.info(
                "verify_user_potd: Ledger updated to SOLVED for user '%s' "
                "(problem_id=%s).",
                handle,
                ledger.problem_id,
            )
            return {"status": "NEWLY_SOLVED", "problem_id": ledger.problem_id}
        except Exception:
            await db.rollback()
            logger.exception(
                "verify_user_potd: DB commit failed while updating SOLVED status "
                "for user '%s'. Transaction rolled back.",
                handle,
            )
            raise

    # No matching OK submission found in the 20 most recent — still pending.
    logger.info(
        "verify_user_potd: No solved submission found for user '%s' "
        "(problem_id=%s). Status remains PENDING.",
        handle,
        ledger.problem_id,
    )
    return {"status": "STILL_PENDING"}
