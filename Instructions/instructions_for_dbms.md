# SYSTEM DIRECTIVE: PostgreSQL Architecture Implementation (FastAPI + Supabase)

**ROLE:** You are a Principal Backend Architect specializing in asynchronous Python, FastAPI, and PostgreSQL. 
**MISSION:** Implement the persistence layer for the "Codeforces Companion Platform" using a cloud Supabase PostgreSQL instance.

---

## 🚫 CRITICAL AGENT DIRECTIVES (DO NOT IGNORE)
Before writing any code, you must adhere to these strict constraints to avoid common AI hallucinations:
1. **Strict SQLAlchemy 2.0 Syntax:** You MUST use the new 2.0 typed paradigm (`Mapped[Type] = mapped_column(...)`). Do NOT use the legacy `db.Column(...)` syntax.
2. **PostgreSQL Specifics:** You MUST use `from sqlalchemy.dialects.postgresql import UUID, JSONB`. Do not use generic string types for UUIDs or JSON.
3. **Async Exclusivity:** You MUST use `async_sessionmaker` and `create_async_engine`. No synchronous DB calls are permitted.
4. **Timezone Safety:** All datetime columns MUST use `DateTime(timezone=True)` to prevent UTC offset crashes across cloud servers.
5. **Metadata Registration:** In `init_db.py`, you MUST explicitly `import models` before calling `create_all`, otherwise the metadata registry will be completely empty and no tables will be created.

---

## FILE 1: `database.py` (The Async Connection Pool)

**Purpose:** Manage the asynchronous connection lifecycle to the Supabase cloud instance.

**Exact Implementation Requirements:**
1. **Imports:**
   - `os`, `sys`
   - `from dotenv import load_dotenv`
   - `from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession`
   - `from sqlalchemy.orm import declarative_base`
2. **Environment Loading:** - Call `load_dotenv()`.
   - Retrieve `DATABASE_URL = os.getenv("DATABASE_URL")`. 
   - *Error Handling:* If `DATABASE_URL` is missing, raise a critical `ValueError`.
3. **The Engine:**
   - Initialize `engine = create_async_engine(...)`.
   - *Complex Params:* Pass `DATABASE_URL`, `echo=False`, `pool_size=5` (for standard traffic), and `max_overflow=10` (to absorb spikes).
4. **The Session Factory:**
   - Initialize `AsyncSessionLocal = async_sessionmaker(...)`.
   - *Complex Params:* Pass `bind=engine`, `class_=AsyncSession`, `expire_on_commit=False` (prevents DetachedInstanceErrors), and `autoflush=False`.
5. **Base Class:**
   - `Base = declarative_base()`
6. **The Dependency (`get_db`):**
   - Create an `async def get_db()` generator.
   - Use `async with AsyncSessionLocal() as session:`
   - Yield the session inside a `try` block.
   - Close the session explicitly in a `finally` block using `await session.close()`.

---

## FILE 2: `models.py` (The Schema Blueprint)

**Purpose:** Define the relational PostgreSQL tables using strict typed mapping.

**Exact Implementation Requirements:**
1. **Imports:**
   - `import uuid`, `import datetime`
   - `from typing import List, Dict, Any`
   - `from sqlalchemy import String, Integer, Float, DateTime, Date, ForeignKey`
   - `from sqlalchemy.dialects.postgresql import UUID, JSONB`
   - `from sqlalchemy.orm import Mapped, mapped_column, relationship`
   - `from database import Base`

2. **Table 1: `User`**
   - `__tablename__ = "users"`
   - `id`: `Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
   - `cf_handle`: `Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)`
   - `current_rating`: `Mapped[int] = mapped_column(Integer, default=0)`
   - `max_rating`: `Mapped[int] = mapped_column(Integer, default=0)`
   - `rank`: `Mapped[str] = mapped_column(String(50), default="unrated")`
   - `last_synced_at`: `Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))`
   - *Relationships:* - `analytics_history: Mapped[List["HistoricalAnalytics"]] = relationship("HistoricalAnalytics", back_populates="user", cascade="all, delete-orphan")`
     - `potd_records: Mapped[List["PotdLedger"]] = relationship("PotdLedger", back_populates="user", cascade="all, delete-orphan")`

3. **Table 2: `HistoricalAnalytics`**
   - `__tablename__ = "historical_analytics"`
   - `id`: `Mapped[uuid.UUID]` (UUID, PK, default uuid4).
   - `user_id`: `Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)` *(Note: ondelete="CASCADE" ensures DB-level cleanliness).*
   - `recorded_at`: `Mapped[datetime.datetime]` (DateTime with timezone, default UTC now).
   - `overall_acceptance_rate`: `Mapped[float]`
   - `top_issue_verdict`: `Mapped[str] = mapped_column(String(50))`
   - `weak_tags`: `Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)`
   - `strong_tags`: `Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)`
   - `under_explored_tags`: `Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)`
   - *Relationships:* `user: Mapped["User"] = relationship("User", back_populates="analytics_history")`

4. **Table 3: `PotdLedger`**
   - `__tablename__ = "potd_ledger"`
   - `id`: `Mapped[uuid.UUID]` (UUID, PK, default uuid4).
   - `user_id`: `Mapped[uuid.UUID]` (ForeignKey to `users.id`, `ondelete="CASCADE"`).
   - `assigned_date`: `Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today, index=True)`
   - `problem_id`: `Mapped[str] = mapped_column(String(20), nullable=False)`
   - `problem_title`: `Mapped[str] = mapped_column(String(200), nullable=False)`
   - `problem_tag`: `Mapped[str] = mapped_column(String(50), nullable=False)`
   - `difficulty`: `Mapped[int]`
   - `status`: `Mapped[str] = mapped_column(String(20), default="PENDING", index=True)`
   - *Relationships:* `user: Mapped["User"] = relationship("User", back_populates="potd_records")`

---

## FILE 3: `init_db.py` (The Cloud Migration Hook)

**Purpose:** Provision the database tables securely on the remote Supabase server.

**Exact Implementation Requirements:**
1. **Imports:**
   - `import asyncio`, `import sys`
   - `from database import engine, Base`
   - `import models` **(CRITICAL: Do not omit this. SQLAlchemy needs to read the models to generate the metadata).**
2. **The Async Provisioning Function (`async def initialize_cloud_database():`):**
   - Wrap the logic in a `try...except...finally` block to catch and print connection errors clearly.
   - Open the connection: `async with engine.begin() as connection:`
   - Create tables: `await connection.run_sync(Base.metadata.create_all)`
   - Print success messages to the terminal.
   - In the `finally` block, explicitly close the engine to prevent hanging event loops: `await engine.dispose()`.
3. **Execution Block:**
   - Create the standard `if __name__ == "__main__":` block.
   - Use `asyncio.run(initialize_cloud_database())` to execute the async function.

**OUTPUT REQUIREMENT:** Generate the raw, production-ready python code for all three files. Separate each file clearly using markdown code blocks. Add inline comments explaining the complex lifecycle events (like `expire_on_commit` and `JSONB` usage).