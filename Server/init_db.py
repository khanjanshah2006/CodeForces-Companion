"""
init_db.py — Cloud Migration Hook for Supabase PostgreSQL
==========================================================
One-shot script that provisions all ORM-defined tables on the remote
Supabase database. Run this once when bootstrapping the project or
whenever the schema changes require a migration.

Usage (from project root):
    python -m Server.init_db
    # or, from inside the Server/ directory:
    python init_db.py

IMPORTANT: `import models` below MUST remain — even though `models` is
not referenced directly in this file. SQLAlchemy's MetaData registry is
populated as a side-effect of importing each model class. Without this
import, `Base.metadata.create_all` will find an empty registry and
create zero tables on the remote server.
"""

import asyncio
import sys

try:
    from .database import Base, engine
except ImportError:
    from database import Base, engine

# ⚠️  CRITICAL IMPORT — DO NOT REMOVE.
# Importing `models` causes Python to execute the module, which in turn
# causes each `class User(Base)`, `class HistoricalAnalytics(Base)`, and
# `class PotdLedger(Base)` declaration to register their `__table__`
# objects into `Base.metadata`. `create_all` reads from that registry.
try:
    from . import models  # noqa: F401  (imported for side-effect only)
except ImportError:
    import models  # noqa: F401  (imported for side-effect only)


async def initialize_cloud_database() -> None:
    """
    Asynchronously creates all tables defined in `Base.metadata` on the
    connected Supabase PostgreSQL instance.

    Lifecycle
    ---------
    1. Open a transactional connection via the async engine.
    2. Run the synchronous `create_all` inside `run_sync` (SQLAlchemy's
       bridge that executes blocking calls in a thread-pool executor so
       the event loop is never blocked).
    3. Print a confirmation table listing all provisioned table names.
    4. Always dispose the engine in `finally` to flush the connection pool
       and prevent the Python event loop from hanging after the script exits.
    """
    print("=" * 60)
    print("  Codeforces Companion — Database Provisioning Script")
    print("=" * 60)
    print("\n[1/3] Connecting to Supabase PostgreSQL instance...")

    try:
        async with engine.begin() as connection:
            print("[2/3] Connection established. Running schema migration...")

            # `run_sync` bridges the async connection to the synchronous
            # `create_all` call. SQLAlchemy inspects each table in
            # Base.metadata and emits CREATE TABLE IF NOT EXISTS statements,
            # so re-running this script on an already-provisioned DB is safe.
            await connection.run_sync(Base.metadata.create_all)

            provisioned = list(Base.metadata.tables.keys())
            print(f"\n[3/3] SUCCESS: Schema provisioned successfully!")
            print(f"      Tables created/verified ({len(provisioned)}):")
            for table_name in provisioned:
                print(f"        - {table_name}")

    except Exception as exc:
        print(f"\nCRITICAL ERROR: Database provisioning failed.")
        print(f"   Error Type : {type(exc).__name__}")
        print(f"   Detail     : {exc}")
        print("\n   Troubleshooting checklist:")
        print("     - Verify DATABASE_URL is set correctly in your .env file.")
        print("     - Confirm the Supabase project is active (not paused).")
        print("     - Ensure the asyncpg driver is installed: pip install asyncpg")
        sys.exit(1)

    finally:
        # `engine.dispose()` closes all pooled connections and tears down
        # the connection pool cleanly. Without this, the asyncio event loop
        # may hang for several seconds waiting for pool connections to time out.
        print("\nCleaning up: closing connection pool...")
        await engine.dispose()
        print("Connection pool closed. Exiting.")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(initialize_cloud_database())
