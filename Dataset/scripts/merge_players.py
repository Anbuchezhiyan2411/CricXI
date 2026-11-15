"""
Module: merge_players.py
Description: Merges all player CSV files from dataset/players/ into a single
             deduplicated, sorted players.csv in dataset/output/.
"""

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
except ImportError:
    pd = None

logger = logging.getLogger(__name__)

TARGET_COLUMNS = [
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


def merge_player_datasets(
    players_dir: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> Any:
    """
    Reads all player CSV files from the players directory, merges them,
    removes duplicates, sorts by Country, Decade, Player Name, and renumbers
    player_id sequentially starting from 1.

    Args:
        players_dir: Directory containing individual country CSVs.
        output_path: Destination path for the merged players.csv.

    Returns:
        pd.DataFrame or List[Dict[str, Any]]: Merged and renumbered player dataset.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if players_dir is None:
        players_dir = base_dir / "players"
    if output_path is None:
        output_path = base_dir / "output" / "players.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(list(players_dir.glob("players_*.csv")))
    if not csv_files:
        # Fallback to root workspace if dataset/players is not populated
        root_dir = base_dir.parent
        csv_files = sorted(list(root_dir.glob("players_*.csv")))

    if not csv_files:
        raise FileNotFoundError(f"No player CSV files found in {players_dir}")

    logger.info("Found %d player files to merge.", len(csv_files))

    if pd is not None:
        dfs = []
        for csv_file in csv_files:
            logger.debug("Reading %s", csv_file.name)
            df = pd.read_csv(csv_file)
            # Replace NaN, empty string, whitespace, null with literal 'None' upon reading
            df = clean_bowling_attributes(df)
            dfs.append(df)

        merged_df = pd.concat(dfs, ignore_index=True)
        merged_df = clean_bowling_attributes(merged_df)

        for col in TARGET_COLUMNS:
            if col not in merged_df.columns:
                raise ValueError(f"Missing required column in merged data: {col}")

        content_cols = [c for c in TARGET_COLUMNS if c != "player_id"]
        initial_len = len(merged_df)
        merged_df = merged_df.drop_duplicates(subset=content_cols).copy()
        logger.info("Removed %d duplicate rows. %d rows remaining.", initial_len - len(merged_df), len(merged_df))

        merged_df["decade"] = pd.to_numeric(merged_df["decade"], errors="coerce").fillna(0).astype(int)

        merged_df = merged_df.sort_values(
            by=["country", "decade", "player_name"],
            ascending=[True, True, True],
        ).reset_index(drop=True)

        merged_df["player_id"] = range(1, len(merged_df) + 1)
        merged_df = merged_df[TARGET_COLUMNS]

        # Final guarantee before saving players.csv: bowling_hand and bowling_type never contain NaN or blanks
        merged_df = clean_bowling_attributes(merged_df)
        merged_df.to_csv(output_path, index=False)
        logger.info("Saved merged players dataset to %s (%d rows)", output_path, len(merged_df))
        return merged_df

    # Fallback to standard library csv
    raw_rows: List[Dict[str, Any]] = []
    for csv_file in csv_files:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                # Clean bowling attributes upon reading
                for b_col in BOWLING_COLUMNS:
                    val = r.get(b_col)
                    if val is None:
                        r[b_col] = "None"
                    else:
                        val_str = str(val).strip()
                        if val_str == "" or val_str.lower() in {"nan", "null", "<na>", "none"}:
                            r[b_col] = "None"
                        else:
                            r[b_col] = val_str
                raw_rows.append(r)

    # Deduplicate by content keys
    seen = set()
    deduped_rows = []
    content_cols = [c for c in TARGET_COLUMNS if c != "player_id"]
    for r in raw_rows:
        key = tuple(r.get(c, "") for c in content_cols)
        if key not in seen:
            seen.add(key)
            deduped_rows.append(r)

    # Sort by country, decade (int), player_name
    def sort_key(row: Dict[str, Any]):
        try:
            d_val = int(row.get("decade", 0))
        except (ValueError, TypeError):
            d_val = 0
        return (str(row.get("country", "")).lower(), d_val, str(row.get("player_name", "")).lower())

    deduped_rows.sort(key=sort_key)

    # Renumber player_id sequentially starting from 1
    for idx, r in enumerate(deduped_rows, start=1):
        r["player_id"] = idx

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TARGET_COLUMNS)
        writer.writeheader()
        for r in deduped_rows:
            writer.writerow({col: r.get(col, "") for col in TARGET_COLUMNS})

    logger.info("Saved merged players dataset to %s (%d rows)", output_path, len(deduped_rows))
    return deduped_rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    merge_player_datasets()
