"""
Dataset Loader Service.
Loads master_players.csv once on startup into memory and provides fast indexed lookups.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from app.config.settings import settings, resolve_dataset_path

logger = logging.getLogger(__name__)


class DatasetLoader:
    """In-memory service for player dataset operations."""

    def __init__(self, dataset_path: Optional[str] = None) -> None:
        self.dataset_path = dataset_path or settings.DATASET_PATH
        self._df: Optional[pd.DataFrame] = None
        self._players: List[Dict[str, Any]] = []
        self._by_id: Dict[int, Dict[str, Any]] = {}
        self._is_loaded: bool = False
        self._resolved_path: Optional[Path] = None

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @property
    def count(self) -> int:
        return len(self._players)

    @property
    def resolved_path(self) -> Optional[Path]:
        return self._resolved_path

    def load(self) -> None:
        """
        Loads and parses the master player dataset.
        Enforces startup validation:
        - verifies dataset file exists
        - verifies dataset is readable
        - logs resolved absolute path and player count
        - raises RuntimeError on failure instead of allowing silent crashes
        """
        try:
            resolved = resolve_dataset_path(self.dataset_path)
            self._resolved_path = resolved
        except Exception as e:
            logger.critical("Failed to resolve master player dataset path: %s", e)
            self._is_loaded = False
            raise RuntimeError(f"CRITICAL: Dataset resolution failed: {e}") from e

        if not resolved.is_file():
            err_msg = f"CRITICAL: Dataset file does not exist at resolved path: {resolved}"
            logger.critical(err_msg)
            self._is_loaded = False
            raise RuntimeError(err_msg)

        # Verify readability
        try:
            with open(resolved, "r", encoding="utf-8") as f:
                header = f.readline()
                if not header or "player_id" not in header:
                    raise ValueError("Dataset file header is missing required 'player_id' column.")
        except Exception as read_err:
            logger.critical("CRITICAL: Dataset file at %s is not readable: %s", resolved, read_err)
            self._is_loaded = False
            raise RuntimeError(f"CRITICAL: Dataset file at {resolved} cannot be read: {read_err}") from read_err

        logger.info("Loading master player dataset from absolute path: %s", resolved)
        print(f"[STARTUP] Master player dataset resolving from: {resolved}", flush=True)
        try:
            df = pd.read_csv(resolved)
            # Ensure proper handling of None/NaN strings for bowling columns
            df["bowling_hand"] = df["bowling_hand"].fillna("None").astype(str).replace({"": "None", "nan": "None", "NaN": "None"})
            df["bowling_type"] = df["bowling_type"].fillna("None").astype(str).replace({"": "None", "nan": "None", "NaN": "None"})
            
            # Fill other numerical NaNs
            numeric_cols = df.select_dtypes(include=["number"]).columns
            df[numeric_cols] = df[numeric_cols].fillna(0)

            # Convert to python dict records
            records = df.to_dict(orient="records")
            if not records:
                raise ValueError(f"Dataset at {resolved} contains 0 player records.")

            self._df = df
            self._players = records
            self._by_id = {int(rec["player_id"]): rec for rec in records if "player_id" in rec}
            self._is_loaded = True
            logger.info("Successfully loaded %d players into memory from %s.", len(self._players), resolved)
            print(f"[STARTUP] Master player dataset loaded successfully: {resolved} ({len(self._players)} players)", flush=True)
        except Exception as e:
            logger.exception("Failed to load and parse dataset from %s: %s", resolved, e)
            self._is_loaded = False
            raise RuntimeError(f"CRITICAL: Failed to parse player dataset from '{resolved}': {e}") from e

    def get_all_players(self) -> List[Dict[str, Any]]:
        """Returns all player records."""
        return list(self._players)

    def get_players_by_country(self, country: str) -> List[Dict[str, Any]]:
        """Returns all players for a given country (case-insensitive)."""
        target = country.strip().lower()
        return [p for p in self._players if str(p.get("country", "")).strip().lower() == target]

    def get_players_by_decade(self, decade: int) -> List[Dict[str, Any]]:
        """Returns all players for a given decade."""
        return [p for p in self._players if int(p.get("decade", 0)) == int(decade)]

    def get_players_by_country_and_decade(self, country: str, decade: int) -> List[Dict[str, Any]]:
        """Returns all players for a given country and decade combination."""
        target_country = country.strip().lower()
        target_decade = int(decade)
        return [
            p for p in self._players
            if str(p.get("country", "")).strip().lower() == target_country
            and int(p.get("decade", 0)) == target_decade
        ]

    def get_player_by_id(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Returns a single player record by player_id."""
        return self._by_id.get(int(player_id))


# Singleton instance
dataset_service = DatasetLoader()
