# SYSTEM DIRECTIVE: Implement Asynchronous API Route for Codeforces Profile Synchronization

**ROLE:** Principal Backend Architect.
**MISSION:** Integrate the sync service, data transformer, and database connection pool into a high-performance FastAPI endpoint.

---

### Context
We have our async database engine setup (`database.py`), our database schemas defined (`models.py`), and our synchronization engine ready (`sync_service.py`). We now need an exposed HTTP endpoint that coordinates these modules.

### Task
Implement or modify your FastAPI application entrypoint (e.g., `server.py` or `main.py`) to include a robust, dependency-injected data sync route.

---

### Implementation Requirements (`server.py` / `main.py`)

**1. Dependency Setup & Imports:**
- Import `FastAPI`, `Depends`, `HTTPException`, and `status` from `fastapi`.
- Import `AsyncSession` from `sqlalchemy.ext.asyncio`.
- Import `get_db` from `database.py`.
- Import `sync_user_data` from `sync_service.py`.
- Import your Codeforces data-fetching functions and `AnalyticsSummaryResponse` model from `data_transformer.py`.

**2. Define the Endpoint:**
- HTTP Method: `POST` or `GET` (Recommend `POST /api/v1/sync/{handle}` for state mutation operations).
- Path Parameter: `handle: str` (The user's Codeforces handle).
- Dependency Injection: Inject the database session using `db: AsyncSession = Depends(get_db)`.

**3. Execution Sequence Control Flow:**
- **Step 1: Raw Data Retrieval**
  - Call your external asynchronous Codeforces client wrapper using the incoming `handle`.
  - Wrap this in a `try...except` block. If the handle does not exist on Codeforces, raise an `HTTPException(status_code=404, detail="Codeforces handle not found")`.
- **Step 2: Processing and Transformation**
  - Run the raw response data through your `data_transformer.py` pipeline to produce a valid `AnalyticsSummaryResponse` object.
- **Step 3: Database Synchronization**
  - Await the synchronization service: `db_user = await sync_user_data(db=db, summary=summary_response)`.
- **Step 4: Serialization**
  - Return the processed summary response payload back to the client.

### Quality Control & Edge Cases:
- **Rate Limit Resilience:** Codeforces API responses can fail under heavy load or trigger 429 errors. Ensure the route catches generic HTTP client exceptions gracefully and bubbles up a clean `503 Service Unavailable` error instead of hard-crashing.
- **String Normalization:** Codeforces handles are case-insensitive when querying their API but case-preserving when returned. Ensure your database search handle handles trimming and consistent string formatting if necessary.