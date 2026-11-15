"""
CricXI Master Data Pipeline
Entry point for generating CricXI player databases from Cricsheet T20I records.

Usage:
    python main.py
    # or from project root: python Dataset/scripts/main.py
"""

import logging
import sys
import time
from pathlib import Path

# Add current scripts directory to sys.path so modules can be imported directly
SCRIPTS_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPTS_DIR.parent
ROOT_DIR = DATASET_DIR.parent

for p in [str(SCRIPTS_DIR), str(DATASET_DIR), str(ROOT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from merge_players import merge_player_datasets
from extract_stats import extract_decade_statistics
from build_master_dataset import build_master_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("CricXI.Main")


def run_pipeline() -> None:
    """Executes the end-to-end CricXI dataset generation pipeline."""
    start_time = time.time()
    logger.info("=" * 65)
    logger.info("Starting CricXI T20 Dataset Generation Pipeline")
    logger.info("=" * 65)

    players_dir = DATASET_DIR / "players"
    data_dir = DATASET_DIR / "data"
    output_dir = DATASET_DIR / "output"

    output_dir.mkdir(parents=True, exist_ok=True)

    players_csv = output_dir / "players.csv"
    stats_csv = output_dir / "player_decade_stats.csv"
    master_csv = output_dir / "master_players.csv"

    # -------------------------------------------------------------
    # STEP 1: Merge Country Player CSVs
    # -------------------------------------------------------------
    logger.info("[Step 1/3] Merging player CSVs into %s ...", players_csv.name)
    merged_players_df = merge_player_datasets(
        players_dir=players_dir,
        output_path=players_csv,
    )
    logger.info("Step 1 Complete: %d players cataloged.", len(merged_players_df))

    # -------------------------------------------------------------
    # STEP 2 & 4: Extract T20I Decade Statistics from Cricsheet
    # -------------------------------------------------------------
    logger.info("[Step 2/3] Extracting decade-wise T20I stats from Cricsheet JSON files...")
    stats_df = extract_decade_statistics(
        data_dir=data_dir,
        output_path=stats_csv,
        players_csv_path=players_csv,
    )
    logger.info("Step 2 Complete: %d player-decade records extracted.", len(stats_df))

    # -------------------------------------------------------------
    # STEP 3 & 5: Build Master Dataset with Normalized Ratings
    # -------------------------------------------------------------
    logger.info("[Step 3/3] Merging stats and computing normalized ratings for %s ...", master_csv.name)
    master_df = build_master_dataset(
        players_csv_path=players_csv,
        stats_csv_path=stats_csv,
        output_path=master_csv,
    )
    logger.info("Step 3 Complete: Master dataset assembled (%d rows).", len(master_df))

    elapsed = time.time() - start_time
    logger.info("=" * 65)
    logger.info("CricXI Pipeline Successfully Completed in %.2f seconds!", elapsed)
    logger.info("Generated outputs:")
    logger.info("  1. Players Catalog:        %s (%d rows)", players_csv, len(merged_players_df))
    logger.info("  2. Player Decade Stats:    %s (%d rows)", stats_csv, len(stats_df))
    logger.info("  3. Master Rated Dataset:   %s (%d rows)", master_csv, len(master_df))
    logger.info("=" * 65)


if __name__ == "__main__":
    run_pipeline()

