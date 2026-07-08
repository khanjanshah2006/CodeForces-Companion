import asyncio
from datetime import datetime, timezone
import logging
from collections import Counter
from typing import Dict, List, Any
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# --- Pydantic Data Models ---

class ProfileSummary(BaseModel):
    rank: str = Field(..., description="Current rank of the user on Codeforces")
    rating: int = Field(..., description="Current rating of the user")
    maxRating: int = Field(..., description="Maximum rating achieved by the user")
    maxRank: str = Field(..., description="Maximum rank achieved by the user")
    avatar: str = Field(..., description="URL to the user's avatar image")
    contribution: int = Field(..., description="Contribution score of the user")

class RatingHistoryItem(BaseModel):
    contestName: str = Field(..., description="Name of the contest")
    date: str = Field(..., description="ISO 8601 UTC timestamp of rating update")
    rating: int = Field(..., description="New rating after the contest")

class TagCount(BaseModel):
    tag: str = Field(..., description="Problem tag name")
    count: int = Field(..., description="Absolute attempt count of problems with this tag")

class SubmissionAnalytics(BaseModel):
    verdicts: Dict[str, int] = Field(
        ...,
        description="Frequencies of unique verdicts in recent submissions"
    )
    topTags: List[TagCount] = Field(
        ...,
        description="Top 5 attempted problem tags"
    )

class CodeforcesStatsResponse(BaseModel):
    handle: str = Field(..., description="Codeforces handle of the user")
    profile: ProfileSummary = Field(..., description="Profile summary of the user")
    ratingHistory: List[RatingHistoryItem] = Field(..., description="Chronological rating history")
    submissionAnalytics: SubmissionAnalytics = Field(..., description="Diagnostics of recent submissions")

# --- Helper functions ---

async def fetch_endpoint(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    """Helper function to fetch a single Codeforces endpoint and handle errors."""
    try:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "FAILED":
            comment = data.get("comment", "Unknown Codeforces API error")
            logger.warning(f"Codeforces API call failed: {comment} on url: {url}")
            
            from fastapi import HTTPException, status
            if "not found" in comment.lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=comment)
            elif "limit exceeded" in comment.lower():
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
                    detail="Codeforces API call limit exceeded. Please try again later."
                )
            else:
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Codeforces API error: {comment}")
        return data
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        try:
            error_data = exc.response.json()
            comment = error_data.get("comment", "")
        except Exception:
            comment = ""
        
        from fastapi import HTTPException, status
        logger.error(f"HTTP error {status_code} occurred calling Codeforces API: {exc}")
        if status_code == 400 and "not found" in comment.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Codeforces user not found.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="External Codeforces API returned an error.")
    except httpx.RequestError as exc:
        from fastapi import HTTPException, status
        logger.error(f"Network error occurred calling Codeforces API: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Failed to connect to Codeforces API.")

async def get_codeforces_stats(handle: str, client: httpx.AsyncClient) -> CodeforcesStatsResponse:
    """Asynchronously gathers, parses, and aggregates all Codeforces metrics for a handle."""
    from fastapi import HTTPException, status
    
    base_url = "https://codeforces.com/api"
    info_url = f"{base_url}/user.info?handles={handle}"
    rating_url = f"{base_url}/user.rating?handle={handle}"
    status_url = f"{base_url}/user.status?handle={handle}&from=1&count=1000"

    # Concurrently fetch endpoints
    results = await asyncio.gather(
        fetch_endpoint(client, info_url),
        fetch_endpoint(client, rating_url),
        fetch_endpoint(client, status_url),
        return_exceptions=True
    )

    for res in results:
        if isinstance(res, HTTPException):
            raise res
        elif isinstance(res, Exception):
            logger.error(f"Unexpected exception during Codeforces fetch: {res}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal error processing external API request."
            )

    info_data, rating_data, status_data = results

    # 1. Process Profile
    info_result = info_data.get("result", [])
    if not info_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Codeforces user info empty.")
    user_info = info_result[0]

    profile = ProfileSummary(
        rank=user_info.get("rank", "unrated"),
        rating=user_info.get("rating", 0),
        maxRating=user_info.get("maxRating", 0),
        maxRank=user_info.get("maxRank", "unrated"),
        avatar=user_info.get("avatar", ""),
        contribution=user_info.get("contribution", 0)
    )

    # 2. Process Rating History
    rating_result = rating_data.get("result", [])
    rating_history = []
    for rate_change in rating_result:
        update_seconds = rate_change.get("ratingUpdateTimeSeconds")
        date_iso = ""
        if update_seconds:
            dt = datetime.fromtimestamp(update_seconds, tz=timezone.utc)
            date_iso = dt.isoformat().replace("+00:00", "Z")
        
        rating_history.append(
            RatingHistoryItem(
                contestName=rate_change.get("contestName", ""),
                date=date_iso,
                rating=rate_change.get("newRating", 0)
            )
        )

    # 3. Process Submission Analytics
    submissions = status_data.get("result", [])
    verdict_counts = Counter()
    all_tags = []

    for sub in submissions:
        verdict = sub.get("verdict")
        if verdict:
            verdict_counts[verdict] += 1
        
        problem = sub.get("problem", {})
        tags = problem.get("tags", [])
        for tag in tags:
            all_tags.append(tag)

    # Standard verdicts representation
    verdicts_dict = {
        "OK": 0,
        "WRONG_ANSWER": 0,
        "TIME_LIMIT_EXCEEDED": 0,
        "RUNTIME_ERROR": 0
    }
    for k, v in verdict_counts.items():
        verdicts_dict[k] = v

    # Extract all tags (sorted descending by count, ascending alphabetically for ties)
    tag_counter = Counter(all_tags)
    sorted_tags = sorted(tag_counter.items(), key=lambda item: (-item[1], item[0]))

    top_tags = [
        TagCount(tag=tag, count=count) for tag, count in sorted_tags
    ]

    submission_analytics = SubmissionAnalytics(
        verdicts=verdicts_dict,
        topTags=top_tags
    )

    return CodeforcesStatsResponse(
        handle=handle,
        profile=profile,
        ratingHistory=rating_history,
        submissionAnalytics=submission_analytics
    )
