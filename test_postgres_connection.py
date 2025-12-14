#!/usr/bin/env python3
"""
PostgreSQL Connection Test Script for KRIZZY OPS
Tests both SQLAlchemy engine and raw psycopg2 connectivity

USAGE:
    # Local testing with DATABASE_URL
    export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
    python test_postgres_connection.py

    # On Railway (DATABASE_URL is auto-injected)
    python test_postgres_connection.py

    # Make executable and run directly
    chmod +x test_postgres_connection.py
    ./test_postgres_connection.py

WHAT IT TESTS:
    1. SQLAlchemy engine connection (production pattern used in app_v2/database.py)
    2. Raw psycopg2 connection (lower-level verification with timeout)
    3. Database operations (table listing, query latency)

REQUIREMENTS:
    - SQLAlchemy>=2.0
    - psycopg2-binary>=2.9
    - DATABASE_URL environment variable (falls back to SQLite if not set)

EXIT CODES:
    0 - All tests passed
    1 - One or more tests failed or all tests skipped
"""
import os
import sys
from datetime import datetime

def test_sqlalchemy_connection():
    """Test SQLAlchemy engine connection (production pattern)"""
    print("\n🔍 Testing SQLAlchemy Engine Connection...")
    print("-" * 50)

    try:
        from app_v2.database import engine, SessionLocal

        # Test 1: Engine connectivity with pool_pre_ping
        print("  → Testing engine.connect()...")
        with engine.connect() as conn:
            result = conn.execute("SELECT version()")
            version = result.fetchone()[0]
            print(f"  ✅ Connection successful")
            print(f"  📊 PostgreSQL version: {version[:50]}...")

        # Test 2: Session creation and query
        print("\n  → Testing SessionLocal()...")
        db = SessionLocal()
        try:
            result = db.execute("SELECT current_database(), current_user")
            db_name, user = result.fetchone()
            print(f"  ✅ Session successful")
            print(f"  📊 Database: {db_name}")
            print(f"  👤 User: {user}")
        finally:
            db.close()

        # Test 3: Pool stats
        print("\n  → Connection pool stats:")
        print(f"  📊 Pool size: {engine.pool.size()}")
        print(f"  📊 Checked out: {engine.pool.checkedout()}")

        return True

    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ SQLAlchemy connection failed: {e}")
        return False


def test_raw_psycopg2_connection():
    """Test raw psycopg2 connection (lower-level verification)"""
    print("\n🔍 Testing Raw psycopg2 Connection...")
    print("-" * 50)

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        print("  ⚠️  DATABASE_URL not set, skipping raw connection test")
        return None

    # Skip if SQLite
    if database_url.startswith("sqlite"):
        print("  ⚠️  Using SQLite, skipping psycopg2 test")
        return None

    try:
        import psycopg2

        # Strip quotes
        database_url = database_url.strip().strip('"').strip("'")

        print(f"  → Connecting with 5s timeout...")
        conn = psycopg2.connect(database_url, connect_timeout=5)
        cur = conn.cursor()

        # Test query
        cur.execute("SELECT 1 as health_check")
        result = cur.fetchone()

        # Get connection info
        cur.execute("""
            SELECT
                current_database() as db,
                current_user as user,
                inet_server_addr() as server_ip,
                inet_server_port() as server_port
        """)
        db_info = cur.fetchone()

        print(f"  ✅ Connection successful: {result}")
        print(f"  📊 Database: {db_info[0]}")
        print(f"  👤 User: {db_info[1]}")
        print(f"  🌐 Server: {db_info[2]}:{db_info[3]}")

        # Cleanup
        cur.close()
        conn.close()

        return True

    except ImportError:
        print("  ⚠️  psycopg2 not installed, skipping raw connection test")
        return None
    except Exception as e:
        print(f"  ❌ Raw connection failed: {e}")
        return False


def test_database_operations():
    """Test basic database operations"""
    print("\n🔍 Testing Database Operations...")
    print("-" * 50)

    try:
        from app_v2.database import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            # Test table listing
            print("  → Checking existing tables...")
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

            if tables:
                print(f"  📊 Found {len(tables)} tables:")
                for table in tables[:10]:  # Show first 10
                    print(f"     - {table}")
                if len(tables) > 10:
                    print(f"     ... and {len(tables) - 10} more")
            else:
                print("  📊 No tables found (database is empty)")

            # Test connection latency
            print("\n  → Testing connection latency...")
            import time
            start = time.time()
            conn.execute(text("SELECT 1"))
            latency_ms = (time.time() - start) * 1000
            print(f"  ⚡ Query latency: {latency_ms:.2f}ms")

        return True

    except Exception as e:
        print(f"  ❌ Database operations failed: {e}")
        return False


def check_postgres_health():
    """
    Lightweight health check for use in OPS_HEALTH_SERVICE
    Returns dict with status and optional error message

    Usage in FastAPI:
        from test_postgres_connection import check_postgres_health

        @app.get("/health")
        async def health():
            return check_postgres_health()
    """
    try:
        from app_v2.database import engine

        with engine.connect() as conn:
            conn.execute("SELECT 1")

        return {
            "postgres": "healthy",
            "status": "ok",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "postgres": "unhealthy",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Run all connection tests"""
    print("=" * 50)
    print("🚀 KRIZZY OPS PostgreSQL Connection Test")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # Check DATABASE_URL
    database_url = os.environ.get("DATABASE_URL", "Not set")
    if database_url != "Not set":
        # Mask password in output
        if "@" in database_url:
            parts = database_url.split("@")
            user_part = parts[0].split("://")[-1]
            if ":" in user_part:
                masked = database_url.replace(user_part.split(":")[1], "****")
                database_url = masked

    print(f"🔗 DATABASE_URL: {database_url}")

    # Run tests
    results = {}
    results['sqlalchemy'] = test_sqlalchemy_connection()
    results['psycopg2'] = test_raw_psycopg2_connection()
    results['operations'] = test_database_operations()

    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print("=" * 50)

    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)

    for test_name, result in results.items():
        status = "✅ PASS" if result is True else ("❌ FAIL" if result is False else "⚠️  SKIP")
        print(f"  {test_name.ljust(20)}: {status}")

    print(f"\n  Total: {passed} passed, {failed} failed, {skipped} skipped")

    if failed > 0:
        print("\n❌ Some tests failed!")
        sys.exit(1)
    elif passed == 0:
        print("\n⚠️  No tests passed (all skipped)")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
