# SYSTEM DIRECTIVE: Implement Algorithmic POTD Engine (`potd_service.py`)

**ROLE:** Principal Backend Architect & Algorithms Expert.
**MISSION:** Implement `potd_service.py`, the core deterministic scheduling engine that selects a daily Codeforces problem based on the user's historical performance, the 50-30-20 day-of-week matrix, and an $O(1)$ exclusion filter.

---

## 🚫 CRITICAL ARCHITECTURAL CONSTRAINTS (ZERO-TOLERANCE)
1. **Idempotency (The Ledger Check):** The entry function MUST check the `potd_ledger` table for today's date BEFORE running any algorithm. If a problem is already assigned for today, return it immediately. Never overwrite an active daily assignment.
2. **Asynchronous I/O Only:** You must use `httpx.AsyncClient()` to fetch the Codeforces problemset. No synchronous `requests` calls are allowed.
3. **Graceful Degradation (Fallback Bounds):** If the strict rating filters result in an empty list of problems (0 matches), you MUST implement a fallback mechanism that widens the rating search bounds by `±200` and tries again.
4. **Timezone Safety:** When checking "today", use `datetime.datetime.now(datetime.timezone.utc).date()`.

---

## 📐 THE ALGORITHMIC PIPELINE (Implementation Blueprint)

You will build three distinct internal functions inside `potd_service.py` that cascade into each other.

### Step 1: `_calculate_daily_target(user: User, analytics: HistoricalAnalytics) -> tuple[list[str], int, int]`
This function determines WHAT we are looking for based on the current day of the week.
- Get the current UTC day of the week as an integer (0 = Monday, 6 = Sunday).
- **Rule A (Mon, Wed, Fri - Core Focus 50%):**
  - Target Rating: `user.current_rating + 100` to `user.current_rating + 200`.
  - Target Tags: Extract the top 3 tags from `analytics.weak_tags` (sort by highest failure index). If empty, default to `["implementation", "math"]`.
- **Rule B (Tue, Thu - Breadth 30%):**
  - Target Rating: `user.current_rating` to `user.current_rating + 100`.
  - Target Tags: Extract tags from `analytics.under_explored_tags`. If empty, pull from the middle of `weak_tags`.
- **Rule C (Sat, Sun - Speed 20%):**
  - Target Rating: `user.current_rating - 200` to `user.current_rating - 100`.
  - Target Tags: Extract top 3 tags from `analytics.strong_tags`.
- **Return:** A tuple containing `(target_tags_list, min_rating, max_rating)`.

### Step 2: `_fetch_and_filter_problems(target_tags: list[str], min_r: int, max_r: int, solved_ids: set[str]) -> dict`
This function hits the global Codeforces API and funnels the dataset.
- **Fetch:** `GET https://codeforces.com/api/problemset.problems`. Extract `response.json()['result']['problems']`.
- **Filter 1 (Tag Match):** Keep problems where at least one tag in `problem['tags']` exists in our `target_tags` list.
- **Filter 2 (Rating Match):** Keep problems where `problem.get('rating')` is between `min_r` and `max_r` (inclusive). Ignore problems with no rating.
- **Filter 3 (Exclusion):** Construct the CF unique ID: `f"{p['contestId']}{p['index']}"`. If this ID is in `solved_ids`, drop it.
- **Selection:** Use `random.choice()` on the remaining list. 
- **Edge Case (Empty List):** If the filtered list is empty, expand `min_r -= 200` and `max_r += 200` and run the filters one more time before selecting.

### Step 3: `generate_or_get_potd(db: AsyncSession, user: User, analytics: HistoricalAnalytics, solved_ids: set[str]) -> PotdLedger`
This is the main public function exposed to the FastAPI router.
- **Phase 1: Idempotency Check.** - Query `PotdLedger` where `user_id == user.id` AND `assigned_date == today`.
  - If a record exists, return it immediately.
- **Phase 2: Calculate & Fetch.**
  - Call `_calculate_daily_target(user, analytics)`.
  - Call `_fetch_and_filter_problems(...)` with the results.
- **Phase 3: Database Persistence.**
  - Create a new `PotdLedger` object.
  - Map fields: `problem_id = f"{prob['contestId']}{prob['index']}"`, `problem_title = prob['name']`, `problem_tag = target_tags[0]`, `difficulty = prob['rating']`.
  - Add to session (`db.add()`), commit (`await db.commit()`), and refresh (`await db.refresh()`).
  - Return the new ledger record.

---

## 🛠️ TECHNICAL REQUIREMENTS & IMPORTS
- `import random`, `import datetime`
- `import httpx`
- `from sqlalchemy.ext.asyncio import AsyncSession`
- `from sqlalchemy.future import select`
- `from models import User, HistoricalAnalytics, PotdLedger`

**OUTPUT REQUIREMENT:** Output the full, production-ready python code for `potd_service.py`. Include comprehensive inline comments explaining the day-of-week logic and the filtering funnel. Ensure strict type-hinting for all function signatures.