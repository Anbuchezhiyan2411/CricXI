"""
Module: build_master_dataset.py
Description: Merges players.csv with player_decade_stats.csv, handles missing values
             safely, computes ratings, and outputs master_players.csv.
"""

import logging
from pathlib import Path
from typing import Optional
import pandas as pd

from calculate_ratings import add_ratings_to_dataframe

logger = logging.getLogger(__name__)

# Complete list of output columns in specified order
FINAL_COLUMNS = [
    "player_id",
    "player_name",
    "country",
    "decade",
    "batting_hand",
    "bowling_hand",
    "bowling_type",
    "primary_role",
    "eligible_positions",
    "is_captain",
    "is_wicketkeeper",
    "matches",
    "innings",
    "not_outs",
    "runs",
    "balls_faced",
    "highest_score",
    "fifties",
    "hundreds",
    "strike_rate",
    "batting_average",
    "fours",
    "sixes",
    "dot_balls",
    "dot_ball_percentage",
    "wickets",
    "balls_bowled",
    "runs_conceded",
    "maidens",
    "economy",
    "bowling_average",
    "bowling_strike_rate",
    "best_bowling",
    "catches",
    "stumpings",
    "run_outs",
    "batting_rating",
    "bowling_rating",
    "fielding_rating",
    "overall_rating",
]

BOWLING_COLUMNS = ["bowling_hand", "bowling_type"]


INVALID_BOWLING_VALUES = [
    "", "nan", "NaN", "NAN", "null", "NULL", "Null",
    "<NA>", "<na>", "none", "NONE", "NoneType", "None",
]


def clean_bowling_attributes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans bowling_hand and bowling_type columns.
    Replaces NaN, empty strings, whitespace-only strings, null, and NoneType
    with the literal string 'None'.
    """
    for col in BOWLING_COLUMNS:
        if col in df.columns:
            # Fill actual NaN / NoneType / null values with "None"
            df[col] = df[col].fillna("None")
            # Strip whitespace
            df[col] = df[col].astype(str).str.strip()
            # Replace whitespace-only, empty strings, and null/nan representations with 'None'
            df[col] = df[col].replace(INVALID_BOWLING_VALUES, "None")
            # Guarantee no remaining NaN / empty values
            df[col] = df[col].fillna("None")
            df[col] = df[col].replace("", "None")
    return df


def build_master_dataset(
    players_csv_path: Optional[Path] = None,
    stats_csv_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Merges players.csv with player_decade_stats.csv on [player_name, country, decade].
    Fills missing values safely for players with no T20I matches.
    Calculates normalized ratings (0-100) and writes output/master_players.csv.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if players_csv_path is None:
        players_csv_path = base_dir / "output" / "players.csv"
    if stats_csv_path is None:
        stats_csv_path = base_dir / "output" / "player_decade_stats.csv"
    if output_path is None:
        output_path = base_dir / "output" / "master_players.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not players_csv_path.exists():
        raise FileNotFoundError(f"Players file not found: {players_csv_path}")

    players_df = pd.read_csv(players_csv_path)
    # Clean bowling attributes on load
    players_df = clean_bowling_attributes(players_df)
    logger.info("Loaded %d players from %s", len(players_df), players_csv_path)

    # Standardize join key types
    players_df["decade"] = pd.to_numeric(players_df["decade"], errors="coerce").fillna(0).astype(int)
    players_df["player_name_clean"] = players_df["player_name"].str.strip().str.lower()
    players_df["country_clean"] = players_df["country"].str.strip().str.lower()

    if stats_csv_path.exists():
        stats_df = pd.read_csv(stats_csv_path)
        logger.info("Loaded %d stats rows from %s", len(stats_df), stats_csv_path)
        stats_df["decade"] = pd.to_numeric(stats_df["decade"], errors="coerce").fillna(0).astype(int)
        stats_df["player_name_clean"] = stats_df["player_name"].str.strip().str.lower()
        stats_df["country_clean"] = stats_df["country"].str.strip().str.lower()

        # Drop redundant player_name, country from stats to avoid duplicate columns after merge
        stats_to_merge = stats_df.drop(columns=["player_name", "country"])

        # Perform left merge
        master_df = pd.merge(
            players_df,
            stats_to_merge,
            on=["player_name_clean", "country_clean", "decade"],
            how="left",
        )
    else:
        logger.warning("Stats file %s not found. Proceeding with zeroed statistics.", stats_csv_path)
        master_df = players_df.copy()

    # Drop temporary join columns
    master_df = master_df.drop(columns=["player_name_clean", "country_clean"], errors="ignore")

    # Safe defaults for missing numeric & text statistics
    defaults = {
        "matches": 0,
        "innings": 0,
        "not_outs": 0,
        "runs": 0,
        "balls_faced": 0,
        "highest_score": "0",
        "fifties": 0,
        "hundreds": 0,
        "strike_rate": 0.0,
        "batting_average": 0.0,
        "fours": 0,
        "sixes": 0,
        "dot_balls": 0,
        "dot_ball_percentage": 0.0,
        "wickets": 0,
        "balls_bowled": 0,
        "runs_conceded": 0,
        "maidens": 0,
        "economy": 0.0,
        "bowling_average": 0.0,
        "bowling_strike_rate": 0.0,
        "best_bowling": "0/0",
        "catches": 0,
        "stumpings": 0,
        "run_outs": 0,
    }

    for col, default_val in defaults.items():
        if col not in master_df.columns:
            master_df[col] = default_val
        else:
            master_df[col] = master_df[col].fillna(default_val)

    # Cast integer columns safely
    int_cols = [
        "matches",
        "innings",
        "not_outs",
        "runs",
        "balls_faced",
        "fifties",
        "hundreds",
        "fours",
        "sixes",
        "dot_balls",
        "wickets",
        "balls_bowled",
        "runs_conceded",
        "maidens",
        "catches",
        "stumpings",
        "run_outs",
    ]
    for col in int_cols:
        master_df[col] = pd.to_numeric(master_df[col], errors="coerce").fillna(0).astype(int)

    # Compute ratings
    logger.info("Computing batting, bowling, fielding, and overall ratings...")
    master_df = add_ratings_to_dataframe(master_df)

    # Ensure all required columns exist and are ordered correctly
    for col in FINAL_COLUMNS:
        if col not in master_df.columns:
            master_df[col] = 0

    master_df = master_df[FINAL_COLUMNS]

    # Before saving master_players.csv, verify and guarantee that bowling_hand and bowling_type contain no missing values
    master_df = clean_bowling_attributes(master_df)

    # Save to master_players.csv
    master_df.to_csv(output_path, index=False)
    logger.info("Successfully generated master dataset at %s (%d rows)", output_path, len(master_df))

    return master_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    build_master_dataset()

