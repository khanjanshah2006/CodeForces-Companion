# SYSTEM DIRECTIVE: Implement Database Synchronization Service (`sync_service.py`)

**ROLE:** Principal Backend Architect.
**MISSION:** Create the database synchronization layer that writes processed Codeforces data into our PostgreSQL Supabase tables.

---

### Context
We have our SQLAlchemy 2.0 models defined in `models.py` (`User`, `HistoricalAnalytics`). We also have our Pydantic data contracts defined in `data_transformer.py` (specifically `AnalyticsSummaryResponse`). 

### Task
Create a new file called `sync_service.py`. This file will contain an asynchronous function that takes a fresh `AnalyticsSummaryResponse` and saves it to the database.

---

### Implementation Requirements (`sync_service.py`)

**1. Imports Required:**
- `from sqlalchemy.ext.asyncio import AsyncSession`
- `from sqlalchemy.future import select`
- `from models import User, HistoricalAnalytics`
- `from data_transformer import AnalyticsSummaryResponse` (Assume this exists)

**2. The Core Function:**
Define `async def sync_user_data(db: AsyncSession, summary: AnalyticsSummaryResponse) -> User:`

**3. The Upsert Logic:**
- **Find or Create User:**
  - Execute a `select(User).where(User.cf_handle == summary.handle)`.
  - If the user exists, update their `current_rating`, `max_rating`, `rank`, and set `last_synced_at` to the current UTC time.
  - If the user DOES NOT exist, instantiate a new `User` object with these fields and add it to the session (`db.add(new_user)`).
  - Flush the session (`await db.flush()`) so the `User.id` (UUID) is generated and available for the next step.

- **Create the Analytics Snapshot:**
  - Instantiate a new `HistoricalAnalytics` record.
  - Link it to the user using `user_id=user.id`.
  - Map the fields from the Pydantic `summary` object:
    - `overall_acceptance_rate = summary.overall_acceptance_rate`
    - `top_issue_verdict = summary.top_issue_verdict`
    - `weak_tags = summary.weak_tags` (SQLAlchemy JSONB will automatically handle the list/dict conversion).
    - `strong_tags = summary.strong_tags`
    - `under_explored_tags = summary.untried_tags` (Or map to your 2D matrix flags if available).
  - Add this record to the session (`db.add(analytics_record)`).

- **Commit & Return:**
  - `await db.commit()`
  - `await db.refresh(user)`
  - Return the `user` object.

### Quality Control & Safeguards:
- Ensure you use `await db.execute(select(...))` to execute the query, followed by `.scalars().first()` to extract the user object.
- Wrap the execution in a `try...except` block. If an exception occurs, trigger an `await db.rollback()` and re-raise the exception so the server doesn't crash with a hung transaction.
- Output ONLY the clean, production-ready Python code for `sync_service.py`.