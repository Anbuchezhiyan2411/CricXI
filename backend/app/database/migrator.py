"""
Database Schema Migrator for CricXI.
Safely and idempotently verifies SQLite schema and adds missing columns,
indexes, and tables introduced across project development phases.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Column specifications to ensure: table_name -> list of (column_name, column_type, default_clause)
REQUIRED_COLUMNS: Dict[str, List[Tuple[str, str, str]]] = {
    "matches": [
        ("current_innings", "INTEGER", "DEFAULT 1"),
        ("target", "INTEGER", "DEFAULT NULL"),
        ("is_paused", "BOOLEAN", "DEFAULT 0"),
        ("simulation_speed", "FLOAT", "DEFAULT 1.0"),
        ("player_of_the_match", "VARCHAR(100)", "DEFAULT NULL"),
        ("player_of_the_match_details", "VARCHAR(200)", "DEFAULT NULL"),
        ("scorecard_json", "TEXT", "DEFAULT NULL"),
    ],
    "match_innings": [
        ("legal_balls_bowled", "INTEGER", "DEFAULT 0"),
        ("current_striker_id", "INTEGER", "DEFAULT NULL"),
        ("current_non_striker_id", "INTEGER", "DEFAULT NULL"),
        ("current_bowler_id", "INTEGER", "DEFAULT NULL"),
    ],
    "ball_events": [
        ("match_id", "INTEGER", "DEFAULT NULL"),
        ("innings_number", "INTEGER", "DEFAULT 1"),
        ("legal_ball_number", "INTEGER", "DEFAULT 0"),
        ("batter_runs", "INTEGER", "DEFAULT 0"),
        ("extra_type", "VARCHAR(20)", "DEFAULT NULL"),
        ("dismissed_player_id", "INTEGER", "DEFAULT NULL"),
        ("commentary", "VARCHAR(300)", "DEFAULT NULL"),
        ("created_at", "DATETIME", "DEFAULT CURRENT_TIMESTAMP"),
    ],
    "innings_batter_scores": [
        ("has_batted", "BOOLEAN", "DEFAULT 0"),
        ("decade", "INTEGER", "DEFAULT NULL"),
    ],
    "innings_bowler_scores": [
        ("decade", "INTEGER", "DEFAULT NULL"),
    ],
}

REQUIRED_INDEXES: List[Tuple[str, str, str]] = [
    ("ix_matches_room_id", "matches", "room_id"),
    ("ix_match_innings_match_id", "match_innings", "match_id"),
    ("ix_ball_events_innings_id", "ball_events", "innings_id"),
    ("ix_ball_events_match_id", "ball_events", "match_id"),
    ("ix_ball_events_batsman_player_id", "ball_events", "batsman_player_id"),
    ("ix_ball_events_bowler_player_id", "ball_events", "bowler_player_id"),
    ("ix_innings_batter_scores_innings_id", "innings_batter_scores", "innings_id"),
    ("ix_innings_batter_scores_player_id", "innings_batter_scores", "player_id"),
    ("ix_innings_bowler_scores_innings_id", "innings_bowler_scores", "innings_id"),
    ("ix_innings_bowler_scores_player_id", "innings_bowler_scores", "player_id"),
]


def migrate_sqlite_database(db_path: str) -> Dict[str, List[str]]:
    """
    Safely inspects and migrates the specified SQLite database file.
    Returns a dictionary of changes applied (added_columns, created_indexes, created_tables).
    """
    path = Path(db_path)
    if not path.exists():
        logger.warning("Database file '%s' does not exist; skipping migration.", db_path)
        return {"added_columns": [], "created_indexes": [], "created_tables": []}

    changes = {
        "added_columns": [],
        "created_indexes": [],
        "created_tables": [],
    }

    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = OFF;")  # Safe column addition

    try:
        cur = conn.cursor()

        # 1. Fetch existing tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = set(row[0] for row in cur.fetchall())

        # 2. Verify and add missing columns
        for table, col_specs in REQUIRED_COLUMNS.items():
            if table not in existing_tables:
                continue

            cur.execute(f"PRAGMA table_info('{table}');")
            existing_cols = set(row[1] for row in cur.fetchall())

            for col_name, col_type, default_clause in col_specs:
                if col_name not in existing_cols:
                    alter_stmt = f"ALTER TABLE '{table}' ADD COLUMN '{col_name}' {col_type} {default_clause};"
                    logger.info("Applying migration to '%s': %s", db_path, alter_stmt)
                    cur.execute(alter_stmt)
                    changes["added_columns"].append(f"{table}.{col_name}")

        # 3. Create missing tables if needed
        # innings_batter_scores
        if "innings_batter_scores" not in existing_tables:
            create_stmt = """
            CREATE TABLE IF NOT EXISTS innings_batter_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                innings_id INTEGER NOT NULL REFERENCES match_innings(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL,
                player_name VARCHAR(100) NOT NULL,
                batting_position INTEGER NOT NULL,
                runs INTEGER NOT NULL DEFAULT 0,
                balls INTEGER NOT NULL DEFAULT 0,
                fours INTEGER NOT NULL DEFAULT 0,
                sixes INTEGER NOT NULL DEFAULT 0,
                strike_rate FLOAT NOT NULL DEFAULT 0.0,
                is_out BOOLEAN NOT NULL DEFAULT 0,
                has_batted BOOLEAN NOT NULL DEFAULT 0,
                decade INTEGER DEFAULT NULL,
                dismissal_text VARCHAR(150) NOT NULL DEFAULT 'DNB'
            );
            """
            cur.execute(create_stmt)
            changes["created_tables"].append("innings_batter_scores")

        # innings_bowler_scores
        if "innings_bowler_scores" not in existing_tables:
            create_stmt = """
            CREATE TABLE IF NOT EXISTS innings_bowler_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                innings_id INTEGER NOT NULL REFERENCES match_innings(id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL,
                player_name VARCHAR(100) NOT NULL,
                decade INTEGER DEFAULT NULL,
                overs FLOAT NOT NULL DEFAULT 0.0,
                legal_balls INTEGER NOT NULL DEFAULT 0,
                maidens INTEGER NOT NULL DEFAULT 0,
                runs_conceded INTEGER NOT NULL DEFAULT 0,
                wickets INTEGER NOT NULL DEFAULT 0,
                economy FLOAT NOT NULL DEFAULT 0.0,
                wides INTEGER NOT NULL DEFAULT 0,
                no_balls INTEGER NOT NULL DEFAULT 0
            );
            """
            cur.execute(create_stmt)
            changes["created_tables"].append("innings_bowler_scores")

        # 4. Fetch updated tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        updated_tables = set(row[0] for row in cur.fetchall())

        # 5. Create missing indexes
        for idx_name, table_name, column_name in REQUIRED_INDEXES:
            if table_name in updated_tables:
                idx_stmt = f"CREATE INDEX IF NOT EXISTS {idx_name} ON '{table_name}' ({column_name});"
                cur.execute(idx_stmt)
                changes["created_indexes"].append(idx_name)

        conn.commit()
        logger.info(
            "Migration completed for '%s': %d columns added, %d tables created.",
            db_path,
            len(changes["added_columns"]),
            len(changes["created_tables"]),
        )
    except Exception as e:
        conn.rollback()
        logger.exception("Failed to migrate database '%s': %s", db_path, e)
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.close()

    return changes

