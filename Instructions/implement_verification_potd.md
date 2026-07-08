# SYSTEM DIRECTIVE: Implement POTD Verification Pipeline

**ROLE:** Principal Backend Architect.
**MISSION:** Implement the Problem of the Day (POTD) verification pipeline. This feature checks if a user has successfully solved their assigned daily problem on Codeforces and updates their database ledger accordingly.

---

## 🚫 CRITICAL ARCHITECTURAL CONSTRAINTS
1. **Lightweight Network Payload:** When querying Codeforces to check for completion, you MUST use the pagination parameters `from=1&count=20` to only fetch the most recent submissions. Do not fetch their entire history.
2. **Idempotency (Double-Click Safety):** If the user's POTD status in the database is already `SOLVED`, the function must return success immediately *without* making an HTTP request to Codeforces.
3. **Transactional Safety:** As always, any database state mutation (updating `PENDING` to `SOLVED`) must be wrapped in a `try...except` block with an explicit `await db.rollback()` on failure.

---

## FILE 1: `potd_service.py` (The Business Logic)

**1. Create the new async function:**
`async def verify_user_potd(db: AsyncSession, handle: str) -> dict:`

**2. Execution Flow:**
- **Step 1: Locate the User & Ledger.**
  - Query the `User` table for the normalized handle. (If not found, raise a `ValueError("User not found")`).
  - Query the `PotdLedger` where `user_id == user.id` and `assigned_date == today (UTC)`.
  - If no ledger exists for today, return `{"status": "NO_POTD_GENERATED"}`.
- **Step 2: Idempotency Guard.**
  - If the ledger's `status` is already `"SOLVED"`, return `{"status": "ALREADY_SOLVED"}` immediately.
- **Step 3: Fetch Codeforces Verification Data.**
  - Use `httpx.AsyncClient()` to call: `https://codeforces.com/api/user.status?handle={handle}&from=1&count=20`
  - Extract the `result` array from the JSON payload.
- **Step 4: Check for Completion.**
  - Loop through the recent submissions.
  - A submission is a match IF: `str(sub['problem']['contestId']) + str(sub['problem']['index']) == ledger.problem_id` AND `sub['verdict'] == "OK"`.
- **Step 5: Database State Mutation.**
  - If a match is found:
    - Update `ledger.status = "SOLVED"`.
    - Wrap the commit phase safely:
      ```python
      try:
          await db.commit()
          return {"status": "NEWLY_SOLVED", "problem_id": ledger.problem_id}
      except Exception:
          await db.rollback()
          raise
      ```
  - If no match is found, return `{"status": "STILL_PENDING"}`.

---

## FILE 2: `server.py` (The API Gateway)

**1. Create the new endpoint:**
- **Method:** `POST`
- **Path:** `/api/v1/potd/{handle}/verify`
- **Dependency:** `db: AsyncSession = Depends(get_db)`

**2. Execution Flow:**
- Sanitize the input: `handle = handle.strip()`.
- Wrap the logic in a `try...except` block to catch the standard pipeline failures:
  - Call `result = await verify_user_potd(db=db, handle=handle)`.
  - Return the `result` dictionary directly to the client.
- **Exception Catching:**
  - Catch `ValueError` (User not found) -> Raise `HTTPException(404)`.
  - Catch `httpx.HTTPError` (CF API down/throttled) -> Raise `HTTPException(503)`.
  - Catch standard `Exception` (Database write failure) -> Raise `HTTPException(500)` after verifying the rollback was triggered inside the service.

**3. Frontend Handoff Documentation (CRITICAL):**
You MUST include the following exact docstring block directly under the `@app.post("/api/v1/potd/{handle}/verify")` decorator. This acts as instructions for the frontend implementation:

```python
    """
    Verifies if the user has solved today's assigned POTD on Codeforces.
    
    FRONTEND INTEGRATION NOTE (DERIVED STATE STREAK):
    This backend intentionally does NOT return a "+1 Streak" integer to avoid state desynchronization. 
    To calculate the user's current streak, the frontend should query the user's historical POTD ledger 
    and count consecutive days with a "SOLVED" status counting backward from today. 
    If this endpoint returns "NEWLY_SOLVED" or "ALREADY_SOLVED", the frontend can safely render the +1 animation.
    """