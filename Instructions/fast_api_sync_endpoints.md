# SYSTEM DIRECTIVE: Implement FastAPI Sync Endpoint Integration

**ROLE:** Principal Backend & Systems Architect.
**MISSION:** Integrate the external Codeforces client wrapper, the data processing pipeline (`data_transformer.py`), and the database persistence layer (`sync_service.py`) into a unified, asynchronous FastAPI endpoint inside `server.py` (or your main application file).

---

## 🚫 CRITICAL ARCHITECTURAL CONSTRAINTS (ZERO-TOLERANCE)
1. **Dependency Injection Session Control:** You MUST use FastAPI’s dependency injection system via `Depends(get_db)` to manage the database connection pool. Never open, close, or commit database sessions manually inside the route function block.
2. **Strict Transaction Safety:** Ensure that if any cloud database persistence operation fails during execution, an automatic `await db.rollback()` is invoked on the session before bubbling up the exception to prevent hung locks or corrupt data snapshots.
3. **Preserve Existing App Context:** Do not overwrite, modify, or break any existing CORS setups, authentication configurations, middleware layers, or independent routes already established inside `server.py`. 

---

## ⚙️ INPUT SANITIZATION REQUIREMENTS
Codeforces handles are case-insensitive during API data lookups but case-preserving upon response. 
- You MUST sanitize the incoming path parameter by running whitespace stripping: `handle = handle.strip()`.
- Pass this normalized handle directly to the external wrapper functions and the synchronization utility.

---

## 🛑 EXCEPTION HANDLING & HTTP STATUS MAPPING
The route must catch specific failures across the distributed pipeline and translate them into explicit, semantic HTTP status codes:

1. **User Profile Missing (Upstream 404):**
   - *Catch:* The specific user-not-found exception thrown by your Codeforces fetching module.
   - *Action:* Raise `HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Codeforces handle '{handle}' does not exist.")`.

2. **Upstream Throttling / Outage (Upstream 429 / 503):**
   - *Catch:* Client connection timeouts, HTTP status errors, or rate limits triggered by Codeforces.
   - *Action:* Raise `HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Codeforces API is temporarily overloaded or unavailable. Please try again shortly.")`.

3. **Data Mutation or Parsing Failure:**
   - *Catch:* Schema errors or internal exceptions thrown during data processing inside `data_transformer.py`.
   - *Action:* Log the traceback to system standard error, and raise `HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Internal ingestion data parsing mismatch occurred.")`.

4. **Supabase / Database Engine Failures:**
   - *Catch:* Database connection drops, pool exhaustion, or transactional errors during execution.
   - *Action:* Execute `await db.rollback()`, log the exact database exception, and raise `HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Cloud persistence layer failed to save user snapshot securely.")`.

---

## 📐 ENDPOINT SPECIFICATIONS
- **HTTP Method:** `POST`
- **Path:** `/api/v1/sync/{handle}`
- **Response Model:** `AnalyticsSummaryResponse`
- **Default Success Code:** `200 OK`

### Execution Pipeline Sequence:
1. Parse and sanitize the incoming `handle` path parameter.
2. Inject the asynchronous database session dependency using `db: AsyncSession = Depends(get_db)`.
3. Invoke the asynchronous Codeforces client method to fetch raw user profiles and historical submission blocks.
4. Process the raw payloads through the data transformer logic to build a validated `AnalyticsSummaryResponse` Pydantic model.
5. Invoke the database synchronization logic: `await sync_user_data(db=db, summary=transformed_summary)`.
6. Return the fully generated `AnalyticsSummaryResponse` directly back to the client.

**OUTPUT REQUIREMENT:** Output the full code implementation file for `server.py` showing all necessary package imports, cleanly structured exception boundaries, and detailed code comments describing the exact request-response lifecycle.