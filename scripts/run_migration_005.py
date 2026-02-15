#!/usr/bin/env python3
"""
Run database migration 005: Query History Separation
"""

import os
import sys
import psycopg2
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_migration():
    """Run migration 005"""
    # Database connection
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 40432)),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "acms_password"),
        database=os.getenv("DB_NAME", "acms_db")
    )

    try:
        # Read migration file
        migration_file = Path(__file__).parent.parent / "migrations" / "005_query_history_separation.sql"
        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        # Execute migration
        with conn.cursor() as cur:
            print(f"Running migration from {migration_file}...")
            cur.execute(migration_sql)
            conn.commit()
            print("Migration completed successfully!")

            # Verify tables exist
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('query_history', 'memory_items', 'query_feedback')
                ORDER BY table_name
            """)
            tables = cur.fetchall()
            print("\nVerified tables:")
            for table in tables:
                print(f"  - {table[0]}")

            # Check memory_type column
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'memory_items'
                AND column_name = 'memory_type'
            """)
            memory_type_col = cur.fetchone()
            if memory_type_col:
                print(f"\n  memory_items.memory_type: {memory_type_col[1]}")

            # Count queries marked for cleanup
            cur.execute("""
                SELECT COUNT(*)
                FROM memory_items
                WHERE metadata->>'migration_005_cleanup' = 'true'
            """)
            cleanup_count = cur.fetchone()[0]
            print(f"\nMarked for cleanup: {cleanup_count} query memories")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
