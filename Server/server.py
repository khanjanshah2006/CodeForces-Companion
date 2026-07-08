from contextlib import asynccontextmanager
import asyncio
import logging
import os
import time
from typing import Any, Dict

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends, Path, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


try:
    # Works when the app is launched as Server.server from the project root.
    from .codeforces_helper import (
        CodeforcesStatsResponse,
        fetch_endpoint,
        get_codeforces_stats,
    )
    from .data_transformer import AnalyticsSummaryResponse, CodeforcesDataProcessor
    from .summary_service import generate_coach_summary
    from .database import get_db, AsyncSessionLocal
    from .sync_service import sync_user_data
    from .potd_service import verify_user_potd, generate_or_get_potd
    from .models import User, HistoricalAnalytics
    from .auth import get_current_user
    from .auth_router import router as auth_router
except ImportError:
    # Works when server.py is launched directly from the Server directory.
    from codeforces_helper import (
        CodeforcesStatsResponse,
        fetch_endpoint,
        get_codeforces_stats,
    )
    from data_transformer import AnalyticsSummaryResponse, CodeforcesDataProcessor
    from summary_service import generate_coach_summary
    from database import get_db, AsyncSessionLocal
    from sync_service import sync_user_data
    from potd_service import verify_user_potd, generate_or_get_potd
    from models import User, HistoricalAnalytics
    from auth import get_current_user
    from auth_router import router as auth_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global In-Memory Cache
# ---------------------------------------------------------------------------
# Structure per key (handle):
#   {
#       "timestamp": float,                  # time.monotonic() of last fetch
#       "analytics": AnalyticsSummaryResponse,
#       "potd":      POTDContextResponse,
#       "roadmap":   RoadmapContextResponse,
#   }
SERVER_CACHE: Dict[str, Dict[str, Any]] = {}

_CACHE_TTL_SECONDS: int = 900  # 15 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize a shared AsyncClient with connection pool and timeout parameters
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=50)
    timeout = httpx.Timeout(15.0, connect=5.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        app.state.http_client = client
        # Expose the session factory so auth_router can open its own sessions
        app.state.db_session_factory = AsyncSessionLocal
        yield


app = FastAPI(
    title="Codeforces API Aggregator",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register authentication router under /api/v1/auth
app.include_router(auth_router, prefix="/api/v1")


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Dependency injection helper to access the shared HTTP client."""
    return request.app.state.http_client


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Codeforces API Aggregator Service",
        "docs": "/docs",
        "dashboard": "/dashboard",
    }


@app.get("/dashboard", summary="Open the Codeforces Companion dashboard")
def read_dashboard():
    dashboard_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "index.html")
    )
    if not os.path.exists(dashboard_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard frontend was not found.",
        )
    return FileResponse(dashboard_path)


@app.get(
    "/api/v1/stats/{handle}",
    response_model=CodeforcesStatsResponse,
    summary="Get aggregated Codeforces statistics",
    description="Fetches user profile, rating history, and submission metrics concurrently and aggregates them.",
)
async def get_stats(
    handle: str = Path(..., description="The Codeforces handle of the user"),
    client: httpx.AsyncClient = Depends(get_http_client),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if handle.lower() != current_user.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own Codeforces profile.",
        )
    return await get_codeforces_stats(handle, client)


@app.get(
    "/api/v1/summary/{handle}",
    response_model=AnalyticsSummaryResponse,
    summary="Get Analytics Summary for a Codeforces user",
    description=(
        "Returns a fully processed AnalyticsSummaryResponse for the given handle. "
        "Results are cached in-memory for 15 minutes to avoid redundant network "
        "calls and heavy O(N) reprocessing."
    ),
)
async def get_summary(
    handle: str = Path(..., description="The Codeforces handle of the user"),
    client: httpx.AsyncClient = Depends(get_http_client),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> AnalyticsSummaryResponse:
    if handle.lower() != current_user.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own Codeforces profile.",
        )
    handle = handle.strip()

    # ------------------------------------------------------------------
    # 1. Cache Check — O(1) dictionary lookup
    # ------------------------------------------------------------------
    cached = SERVER_CACHE.get(handle)
    if cached is not None:
        age = time.monotonic() - cached["timestamp"]
        if age < _CACHE_TTL_SECONDS:
            logger.info(
                "Cache HIT for handle '%s' (age=%.1fs, TTL=%ds).",
                handle,
                age,
                _CACHE_TTL_SECONDS,
            )
            return cached["analytics"]
        else:
            logger.info(
                "Cache STALE for handle '%s' (age=%.1fs). Refreshing.",
                handle,
                age,
            )

    # ------------------------------------------------------------------
    # 2. Cache Miss — fetch raw data from Codeforces concurrently
    # ------------------------------------------------------------------
    logger.info("Cache MISS for handle '%s'. Fetching from Codeforces.", handle)

    base_url = "https://codeforces.com/api"
    info_url = f"{base_url}/user.info?handles={handle}"
    rating_url = f"{base_url}/user.rating?handle={handle}"
    status_url = f"{base_url}/user.status?handle={handle}&from=1&count=10000"

    try:
        results = await asyncio.gather(
            fetch_endpoint(client, info_url),
            fetch_endpoint(client, rating_url),
            fetch_endpoint(client, status_url),
            return_exceptions=True,
        )
    except Exception as exc:
        logger.error("Unexpected error gathering Codeforces data for '%s': %s", handle, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to the Codeforces API. Please try again later.",
        )

    # Bubble up the first HTTPException or unexpected error from gather results
    for res in results:
        if isinstance(res, HTTPException):
            raise res
        if isinstance(res, Exception):
            logger.error(
                "Unexpected exception fetching Codeforces data for '%s': %s", handle, res
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="An error occurred while fetching data from the Codeforces API.",
            )

    info_data, _rating_data, status_data = results

    # ------------------------------------------------------------------
    # 3. Extract profile metadata required by CodeforcesDataProcessor
    # ------------------------------------------------------------------
    info_result = info_data.get("result", [])
    if not info_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Codeforces user '{handle}' not found.",
        )

    user_info = info_result[0]
    current_rating: int = user_info.get("rating", 0)
    max_rating: int = user_info.get("maxRating", 0)
    rank: str = user_info.get("rank", "unrated")

    # ------------------------------------------------------------------
    # 4. Instantiate processor and run single-pass O(N) transformation
    # ------------------------------------------------------------------
    processor = CodeforcesDataProcessor(
        handle=handle,
        current_rating=current_rating,
        max_rating=max_rating,
        rank=rank,
    )

    submissions = status_data.get("result", [])

    try:
        analytics, potd, roadmap = processor.process_submissions(submissions=submissions)
    except Exception as exc:
        logger.error(
            "Data transformation failed for handle '%s': %s", handle, exc
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process submission data.",
        )

    # ------------------------------------------------------------------
    # 5. Store all three contracts in the cache with a fresh timestamp
    # ------------------------------------------------------------------
    SERVER_CACHE[handle] = {
        "timestamp": time.monotonic(),
        "analytics": analytics,
        "potd": potd,
        "roadmap": roadmap,
    }

    logger.info("Cache STORED for handle '%s'.", handle)
    return analytics


@app.get(
    "/api/v1/summary/{handle}/ai-coach",
    response_model=Dict[str, str],
    summary="Get AI Coach diagnostic summary",
    description=(
        "Generates a personalised diagnostic summary from the perspective of an "
        "elite Competitive Programming Coach. Requires the base /summary/{handle} "
        "endpoint to have been called first to populate the analytics cache."
    ),
)
async def get_ai_coach_summary(
    handle: str = Path(..., description="The Codeforces handle of the user"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if handle.lower() != current_user.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own Codeforces profile.",
        )
    # ------------------------------------------------------------------
    # 1. Verify primary cache exists and is fresh
    # ------------------------------------------------------------------
    cached = SERVER_CACHE.get(handle)
    if cached is None or (time.monotonic() - cached["timestamp"] > _CACHE_TTL_SECONDS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Analytics data missing or expired. "
                "Please request base summary first to populate cache."
            ),
        )

    # ------------------------------------------------------------------
    # 2. Check if the AI coach response itself is already cached
    # ------------------------------------------------------------------
    if "ai_coach_summary" in cached:
        logger.info("AI Coach cache HIT for handle '%s'.", handle)
        return {"summary": cached["ai_coach_summary"]}

    # ------------------------------------------------------------------
    # 3. Cache miss — pull the cached Pydantic analytics object
    # ------------------------------------------------------------------
    analytics_data: AnalyticsSummaryResponse = cached["analytics"]

    try:
        # 4. Trigger the LLM orchestration pass
        ai_summary_text = await generate_coach_summary(analytics_data)

        # 5. Commit the generated text back into the handle's cache entry
        SERVER_CACHE[handle]["ai_coach_summary"] = ai_summary_text

        logger.info("AI Coach summary STORED in cache for handle '%s'.", handle)
        return {"summary": ai_summary_text}

    except Exception as exc:
        logger.error("Gemini Generation Error for handle '%s': %s", handle, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Coaching generation temporarily unavailable.",
        )


@app.post(
    "/api/v1/sync/{handle}",
    response_model=AnalyticsSummaryResponse,
    summary="Synchronise a Codeforces user profile to the database",
    description=(
        "Fetches fresh data from the Codeforces API for the given handle, runs it "
        "through the analytics transformation pipeline, persists the result to the "
        "PostgreSQL database via the sync service, and returns the processed "
        "AnalyticsSummaryResponse to the caller."
    ),
    status_code=status.HTTP_200_OK,
)
async def sync_user(
    handle: str = Path(..., description="The Codeforces handle of the user"),
    client: httpx.AsyncClient = Depends(get_http_client),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> AnalyticsSummaryResponse:
    if handle.lower() != current_user.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own Codeforces profile.",
        )
    # ------------------------------------------------------------------
    # String Normalisation — trim whitespace; Codeforces handles are
    # case-preserving in their API responses but callers may send them
    # with surrounding spaces or mixed casing.
    # ------------------------------------------------------------------
    handle = handle.strip()

    # ------------------------------------------------------------------
    # Step 1: Raw Data Retrieval
    # Fetch user profile info and full submission history concurrently.
    # ------------------------------------------------------------------
    base_url = "https://codeforces.com/api"
    info_url = f"{base_url}/user.info?handles={handle}"
    status_url = f"{base_url}/user.status?handle={handle}&from=1&count=10000"

    try:
        results = await asyncio.gather(
            fetch_endpoint(client, info_url),
            fetch_endpoint(client, status_url),
            return_exceptions=True,
        )
    except Exception as exc:
        logger.error(
            "Unexpected error gathering Codeforces data for sync of '%s': %s",
            handle,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to the Codeforces API. Please try again later.",
        )

    # Inspect each gather result — propagate 404s cleanly, wrap everything
    # else as 503 so the client always receives a meaningful error message.
    for res in results:
        if isinstance(res, HTTPException):
            # A 404 from fetch_endpoint signals the handle does not exist on Codeforces.
            if res.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Codeforces handle '{handle}' does not exist.",
                )
            # 429 rate-limit / 502 bad-gateway / other upstream errors → 503
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Codeforces API is temporarily overloaded or unavailable. Please try again shortly.",
            )
        if isinstance(res, Exception):
            logger.error(
                "Unexpected exception during Codeforces fetch for sync of '%s': %s",
                handle,
                res,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Codeforces API is temporarily overloaded or unavailable. Please try again shortly.",
            )

    info_data, submissions_data = results

    # Extract user profile fields from the info response.
    info_result = info_data.get("result", [])
    if not info_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Codeforces user '{handle}' not found.",
        )

    user_info = info_result[0]
    current_rating: int = user_info.get("rating", 0)
    max_rating: int = user_info.get("maxRating", 0)
    rank: str = user_info.get("rank", "unrated")
    # Use the canonical handle returned by Codeforces (preserves original casing).
    canonical_handle: str = user_info.get("handle", handle)

    # ------------------------------------------------------------------
    # Step 2: Processing and Transformation
    # Run the O(N) single-pass pipeline to produce AnalyticsSummaryResponse.
    # ------------------------------------------------------------------
    processor = CodeforcesDataProcessor(
        handle=canonical_handle,
        current_rating=current_rating,
        max_rating=max_rating,
        rank=rank,
    )

    submissions = submissions_data.get("result", [])

    try:
        summary_response, _potd, _roadmap = processor.process_submissions(
            submissions=submissions
        )
    except Exception as exc:
        # Log the full traceback to stderr so the error can be diagnosed in
        # server logs without exposing internal details to the API client.
        logger.error(
            "Data transformation failed during sync for handle '%s': %s",
            handle,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Internal ingestion data parsing mismatch occurred.",
        )

    # ------------------------------------------------------------------
    # Step 3: Database Synchronisation
    # Upsert the user row and insert a fresh analytics snapshot.
    # ------------------------------------------------------------------
    try:
        db_user = await sync_user_data(db=db, summary=summary_response)
        logger.info(
            "Database sync completed for handle '%s' (user_id=%s).",
            canonical_handle,
            db_user.id,
        )
    except Exception as exc:
        # Explicitly roll back the session in the route layer to guarantee no
        # hung transaction lock remains on the connection pool, even if
        # sync_user_data has already attempted a rollback internally.
        await db.rollback()
        logger.error(
            "Database engine failure during sync for handle '%s': %s",
            canonical_handle,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloud persistence layer failed to save user snapshot securely.",
        )

    # ------------------------------------------------------------------
    # Step 4: Serialisation
    # Return the processed analytics payload to the caller.
    # ------------------------------------------------------------------
    return summary_response


@app.get(
    "/api/v1/potd/{handle}",
    summary="Generate or get today's Problem of the Day",
)
async def get_potd(
    handle: str = Path(..., description="The Codeforces handle of the user"),
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_http_client),
    current_user: str = Depends(get_current_user),
):
    if handle.lower() != current_user.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own Codeforces profile.",
        )
    handle = handle.strip()

    # 1. Fetch User
    from sqlalchemy.future import select
    user_result = await db.execute(select(User).where(User.cf_handle == handle))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{handle}' not found. Please sync the profile first.",
        )

    # 2. Fetch Latest Analytics
    analytics_result = await db.execute(
        select(HistoricalAnalytics)
        .where(HistoricalAnalytics.user_id == user.id)
        .order_by(HistoricalAnalytics.recorded_at.desc())
    )
    analytics = analytics_result.scalars().first()
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analytics found for '{handle}'. Please sync the profile first.",
        )

    # 3. Fetch Solved IDs from Codeforces
    status_url = f"https://codeforces.com/api/user.status?handle={handle}"
    try:
        response = await client.get(status_url)
        response.raise_for_status()
        status_data = response.json()
    except Exception as exc:
        logger.error("Failed to fetch CF status for POTD solved_ids: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Codeforces API is unavailable.",
        )
    
    solved_ids = set()
    for sub in status_data.get("result", []):
        if sub.get("verdict") == "OK":
            prob = sub.get("problem", {})
            prob_id = f"{prob.get('contestId', '')}{prob.get('index', '')}"
            solved_ids.add(prob_id)

    # 4. Generate/Get POTD
    try:
        potd = await generate_or_get_potd(db, user, analytics, solved_ids)
        
        # Calculate daily streak from ledger history
        import datetime
        try:
            from .models import PotdLedger
        except ImportError:
            from models import PotdLedger

        result = await db.execute(
            select(PotdLedger)
            .where(PotdLedger.user_id == user.id)
            .order_by(PotdLedger.assigned_date.desc())
        )
        all_records = result.scalars().all()

        streak = 0
        if all_records:
            today = datetime.datetime.now(datetime.timezone.utc).date()
            yesterday = today - datetime.timedelta(days=1)
            
            record_map = {r.assigned_date: r for r in all_records}
            today_record = record_map.get(today)
            
            start_date = today
            if today_record is None or today_record.status != "SOLVED":
                start_date = yesterday
                
            current_expected = start_date
            while True:
                r = record_map.get(current_expected)
                if r is not None and r.status == "SOLVED":
                    streak += 1
                    current_expected -= datetime.timedelta(days=1)
                else:
                    break

        tags_list = [t.strip() for t in potd.problem_tag.split(",") if t.strip()]
        return {
            "problem_id": potd.problem_id,
            "problem_title": potd.problem_title,
            "problem_tag": tags_list[0] if tags_list else potd.problem_tag,
            "problem_tags": tags_list,
            "difficulty": potd.difficulty,
            "status": potd.status,
            "assigned_date": str(potd.assigned_date),
            "streak": streak,
        }
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Database failure during POTD generation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate POTD due to an internal error.",
        )


@app.post(
    "/api/v1/potd/{handle}/verify",
    summary="Verify if the user has solved today's POTD",
)
async def verify_potd(
    handle: str = Path(..., description="The Codeforces handle of the user"),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    if handle.lower() != current_user.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own Codeforces profile.",
        )
    """
    Verifies if the user has solved today's assigned POTD on Codeforces.
    
    FRONTEND INTEGRATION NOTE (DERIVED STATE STREAK):
    This backend intentionally does NOT return a "+1 Streak" integer to avoid state desynchronization. 
    To calculate the user's current streak, the frontend should query the user's historical POTD ledger 
    and count consecutive days with a "SOLVED" status counting backward from today. 
    If this endpoint returns "NEWLY_SOLVED" or "ALREADY_SOLVED", the frontend can safely render the +1 animation.
    """
    # Sanitise the path parameter — trim any surrounding whitespace before any
    # lookup or external call (consistent with all other routes on this gateway).
    handle = handle.strip()

    try:
        result = await verify_user_potd(db=db, handle=handle)
        return result

    except ValueError as exc:
        # Raised by verify_user_potd when the handle does not exist in users table.
        logger.warning("verify_potd: User not found for handle '%s': %s", handle, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except httpx.HTTPError as exc:
        # Covers HTTPStatusError (4xx/5xx from CF) and RequestError (network/timeout).
        # Both indicate the Codeforces API is unavailable — surface as 503.
        logger.error(
            "verify_potd: Codeforces API error for handle '%s': %s", handle, exc
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Codeforces API is temporarily unavailable. Please try again shortly.",
        )

    except Exception as exc:
        # Database write failure — verify_user_potd already called db.rollback().
        # Log the exception and surface as 500.
        logger.error(
            "verify_potd: Database failure for handle '%s': %s",
            handle,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update POTD verification status. Please try again.",
        )


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("DEBUG", "True").lower() == "true"

    print(f"Starting server on http://{host}:{port}")
    # Note: When running directly from Server/, uvicorn should reload the main 'server:app'
    # Adding Server directory to path or specifying correct reload module target.
    # Uvicorn supports running the module name directly.
    uvicorn.run("server:app", host=host, port=port, reload=reload)
