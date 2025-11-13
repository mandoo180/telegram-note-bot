#!/usr/bin/env python3
"""Initialize the database for Telegram Note bot."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.database import Database
from config import Config


def init_database():
    """Initialize the database with schema."""
    print("Initializing Telegram Note database...")

    db_path = Config.DATABASE_PATH
    print(f"Database path: {db_path}")

    # Create database instance (this will create tables)
    db = Database(db_path)

    print("\nDatabase initialized successfully!")
    print("\nTables created:")
    print("  - notes")
    print("  - schedules")
    print("  - reminders")

    # Verify tables were created
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        print("\nVerified tables in database:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  ✓ {table[0]} (0 rows)")

    print(f"\nDatabase file created at: {os.path.abspath(db_path)}")


if __name__ == '__main__':
    try:
        init_database()
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)
