You are an expert backend engineer specializing in Python, FastAPI, and data aggregation. Your task is to build a highly optimized, clean, and asynchronous backend service that acts as a wrapper and aggregator for the public Codeforces API.

### Objective
Create a FastAPI application with a single GET endpoint (`/api/v1/stats/{handle}`) that takes a user's Codeforces handle, fetches raw data concurrently from three distinct external Codeforces endpoints, processes/aggregates the data, and returns a unified, clean JSON payload tailored for dashboard visualization.

### Dependencies to Use
- fastapi, uvicorn (for the web framework)
- httpx (for asynchronous, non-blocking HTTP requests)
- pydantic (for strict data validation and response structuring)

### External Codeforces Endpoints to Fetch Concurrently
1. Info: https://codeforces.com/api/user.info?handles={handle}
2. Rating: https://codeforces.com/api/user.rating?handle={handle}
3. Status: https://codeforces.com/api/user.status?handle={handle}&from=1&count=1000

### Data Processing & Aggregation Requirements
Your backend must process the raw responses as follows:

1. Profile Summary: Extract handle, current rating, max rating, current rank, max rank, contribution.
2. Rating History: Transform the rating chronological list into a clean array of objects containing only 'contestName', 'ratingUpdateTimeSeconds' (converted to ISO timestamp format), and 'newRating'.
3. Submission Diagnostics: 
   - Iterate through the recent submissions list.
   - Count the frequency of each unique 'verdict' (e.g., OK, WRONG_ANSWER, TIME_LIMIT_EXCEEDED, RUNTIME_ERROR).
   - Extract the 'tags' array from each problem. Flatten these tags and calculate the top 5 most frequently attempted problem tags, along with their absolute attempt counts.

### Edge Case Handling & Robustness
- Error Handling: Wrap external API requests in try-except blocks using httpx. If Codeforces returns a "FAILED" status, a user handle does not exist, or the API is rate-limited, catch the exception and raise a clean FastAPI `HTTPException` (e.g., 404 for User Not Found, 503 for External Service Unavailable).
- Performance: Do NOT fetch the three endpoints sequentially. Use `asyncio.gather` to perform all three HTTP requests concurrently to keep response latency minimal.

### Expected JSON Output Structure
The endpoint must return a response matching this exact schema:

{
  "handle": "string",
  "profile": {
    "rank": "string",
    "rating": 0,
    "maxRating": 0,
    "maxRank": "string",
    "avatar": "string",
    "contribution": 0
  },
  "ratingHistory": [
    {
      "contestName": "string",
      "date": "2026-03-15T18:30:00Z",
      "rating": 0
    }
  ],
  "submissionAnalytics": {
    "verdicts": {
      "OK": 0,
      "WRONG_ANSWER": 0,
      "TIME_LIMIT_EXCEEDED": 0,
      "RUNTIME_ERROR": 0
    },
    "topTags": [
      { "tag": "string", "count": 0 }
    ]
  }
}

Provide the complete, production-ready code with clean code organization, variable definitions, error checking, type hinting, and structural formatting.