"""
Dataset Loader Service.
Loads master_players.csv once on startup into memory and provides fast indexed lookups.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from app.config.settings import settings

logger = logging.getLogger(__name__)


class DatasetLoader:
    """In-memory service for player dataset operations."""

    def __init__(self, dataset_path: Optional[str] = None) -> None:
        self.dataset_path = dataset_path or settings.DATASET_PATH
        self._df: Optional[pd.DataFrame] = None
        self._players: List[Dict[str, Any]] = []
        self._by_id: Dict[int, Dict[str, Any]] = {}
        self._is_loaded: bool = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    @property
    def count(self) -> int:
        return len(self._players)

    def load(self) -> None:
        """Loads and parses the master player dataset."""
        path = Path(self.dataset_path)
        if not path.exists():
            # Try alternate paths
            candidates = [
                Path("Dataset/output/master_players.csv"),
                Path("dataset/output/master_players.csv"),
                Path("../Dataset/output/master_players.csv"),
                Path("../dataset/output/master_players.csv"),
            ]
            for cand in candidates:
                if cand.exists():
                    path = cand
                    break

        if not path.exists():
            logger.error("Dataset file could not be found at %s", self.dataset_path)
            self._is_loaded = False
            return

        logger.info("Loading master player dataset from %s", path)
        try:
            df = pd.read_csv(path)
            # Ensure proper handling of None/NaN strings for bowling columns
            df["bowling_hand"] = df["bowling_hand"].fillna("None").astype(str).replace({"": "None", "nan": "None", "NaN": "None"})
            df["bowling_type"] = df["bowling_type"].fillna("None").astype(str).replace({"": "None", "nan": "None", "NaN": "None"})
            
            # Fill other numerical NaNs
            numeric_cols = df.select_dtypes(include=["number"]).columns
            df[numeric_cols] = df[numeric_cols].fillna(0)

            # Convert to python dict records
            records = df.to_dict(orient="records")
            self._df = df
            self._players = records
            self._by_id = {int(rec["player_id"]): rec for rec in records if "player_id" in rec}
            self._is_loaded = True
            logger.info("Successfully loaded %d players into memory.", len(self._players))
        except Exception as e:
            logger.exception("Failed to load dataset: %s", e)
            self._is_loaded = False

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

