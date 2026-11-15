"""
CLI Database Migration Script for CricXI.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import sqlite3
from app.database.migrator import migrate_sqlite_database

def run_migrations():
    targets = [
        Path(__file__).resolve().parent / "cricxi.db",
        Path(__file__).resolve().parent.parent / "cricxi.db",
    ]

    print("==================================================")
    print("CRICXI DATABASE MIGRATION ENGINE")
    print("==================================================")

    for db_path in targets:
        if not db_path.exists():
            print(f"Skipping non-existent database: {db_path}")
            continue

        print(f"\nMigrating SQLite database at: {db_path}")
        changes = migrate_sqlite_database(str(db_path))

        print(f"  - Added columns ({len(changes['added_columns'])}): {changes['added_columns']}")
        print(f"  - Created tables ({len(changes['created_tables'])}): {changes['created_tables']}")
        print(f"  - Verified indexes ({len(changes['created_indexes'])}).")

        # Verification
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        print("\n  [Verification Check]")
        for table in ["matches", "match_innings", "ball_events", "innings_batter_scores", "innings_bowler_scores"]:
            cur.execute(f"PRAGMA table_info('{table}');")
            cols = [c[1] for c in cur.fetchall()]
            print(f"  - Table '{table}' columns: {cols}")

        cur.execute("SELECT COUNT(*) FROM rooms;")
        print(f"  - Existing rooms preserved: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM room_players;")
        print(f"  - Existing players preserved: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM draft_picks;")
        print(f"  - Existing draft picks preserved: {cur.fetchone()[0]}")
        conn.close()

    print("\nMigration completed successfully for all active database files.")

if __name__ == "__main__":
    run_migrations()

