# System Prompt: Implement FastAPI Endpoint with Smart In-Memory Caching

You are an expert backend engineer specializing in FastAPI and high-performance caching strategies. Your task is to update `server.py` to expose a clean REST API endpoint that exposes the Analytics Summary feature while utilizing an optimal in-memory caching mechanism to manage processing state.

### Context & Existing Files
You are working within an existing directory structure containing:
1. `data_transformer.py`: Contains `CodeforcesDataProcessor` which accepts profile data in its initializer and exposes `.process_submissions(submissions: List[Dict])`. It returns a 3-tuple: `(AnalyticsSummaryResponse, POTDContextResponse, RoadmapContextResponse)`.
2. `codeforces_helper.py` (or your existing fetching logic): Handles raw concurrent HTTP asynchronous calls to Codeforces public API endpoints (`user.info`, `user.rating`, `user.status`).

### Objective
Implement a single `GET` endpoint: `/api/v1/summary/{handle}` in `server.py`. 
This endpoint must return an `AnalyticsSummaryResponse` model payload. It must utilize a global, in-memory dictionary cache to ensure that the heavy single-pass $O(N)$ loop inside `data_transformer.py` and the external Codeforces network requests are executed **exactly once per user handle every 15 minutes**.

### State Management & Caching Requirements
FastAPI is stateless, so you must implement a simple global dictionary `SERVER_CACHE` with a Time-to-Live (TTL) constraint of 900 seconds (15 minutes). 

Follow this strict logical flow inside the endpoint:
1. **Cache Check:** When a request hits `/api/v1/summary/{handle}`, check if the `handle` exists inside `SERVER_CACHE`.
2. **Cache Hit ($O(1)$ Pass):** If the handle exists and `(current_time - cached_time) < 900`, retrieve the stored pre-computed `AnalyticsSummaryResponse` object and return it instantly. Bypass all external API network calls and data processing.
3. **Cache Miss:** If the cache is empty or stale:
   a. Call your existing async fetching mechanics to fetch the raw JSON lists from Codeforces.
   b. Instantiate `CodeforcesDataProcessor` using the fresh profile information.
   c. Execute `.process_submissions()` passing the raw submission data.
   d. **Cache Storage:** Store **all three resulting data contracts** (Summary, POTD, and Roadmap) inside the `SERVER_CACHE` payload dictionary under that specific user handle, along with a fresh timestamp.
   e. Return the newly calculated `AnalyticsSummaryResponse` to the user.

### Safety & Error Handling
* Wrap your external API fetches in explicit try-except loops. If a handle is invalid or Codeforces is completely down, raise a clean FastAPI `HTTPException(status_code=404, detail="...")` or `503` instead of letting the application crash or cache bad errors.
* Ensure thread-safe or safe concurrent dictionary dictionary lookups.

### Code Constraints
* Write asynchronous, non-blocking code using `async def`.
* Use explicit type hints for your router dependencies.
* Do not rewrite the `data_transformer.py` models or logic; import them directly.