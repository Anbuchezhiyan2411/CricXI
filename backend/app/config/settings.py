"""
CricXI Application Settings.
Loads and validates environment variables.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

logger = logging.getLogger("cricxi.settings")

# Locate root and backend directories using strict absolute pathlib resolution
APP_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = APP_DIR.parent
ROOT_DIR = BACKEND_DIR.parent
APP_DATA_DIR = APP_DIR / "data"

# Load environment variables
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")


def resolve_dataset_path(raw_path: Optional[str] = None) -> Path:
    """
    Robustly resolves the master_players.csv dataset absolute path.
    Supports local dev, Railway, Docker, and arbitrary working directories.
    Validates DATASET_PATH env var if provided; falls back to bundled datasets.
    """
    # Priority candidate locations for the bundled dataset
    bundled_candidates = [
        APP_DATA_DIR / "master_players.csv",
        BACKEND_DIR / "dataset" / "output" / "master_players.csv",
        BACKEND_DIR / "Dataset" / "output" / "master_players.csv",
        ROOT_DIR / "Dataset" / "output" / "master_players.csv",
        ROOT_DIR / "dataset" / "output" / "master_players.csv",
    ]

    env_val = (raw_path or os.getenv("DATASET_PATH", "")).strip()
    if env_val:
        # Check direct path (absolute or relative to current working dir)
        direct_cand = Path(env_val)
        if direct_cand.is_file():
            logger.info("Using valid configured DATASET_PATH: %s", direct_cand.resolve())
            return direct_cand.resolve()

        # Check relative to base directories without leading/trailing slashes
        clean_rel = env_val.lstrip("/\\")
        for base in [ROOT_DIR, BACKEND_DIR, APP_DIR, APP_DATA_DIR]:
            rel_cand = (base / clean_rel).resolve()
            if rel_cand.is_file():
                logger.info("Resolved configured DATASET_PATH relative to %s: %s", base, rel_cand)
                return rel_cand

        logger.warning(
            "Configured DATASET_PATH '%s' does not exist or is unreadable. "
            "Automatically falling back to bundled dataset.",
            env_val,
        )

    # Check bundled dataset candidate locations
    for cand in bundled_candidates:
        if cand.is_file():
            resolved = cand.resolve()
            logger.info("Resolved bundled dataset from: %s", resolved)
            return resolved

    # Search upward directory hierarchy for master_players.csv as last resort
    curr = Path(__file__).resolve()
    for parent in [curr] + list(curr.parents):
        for sub in [
            parent / "Dataset" / "output" / "master_players.csv",
            parent / "dataset" / "output" / "master_players.csv",
            parent / "data" / "master_players.csv",
            parent / "app" / "data" / "master_players.csv",
        ]:
            if sub.is_file():
                resolved = sub.resolve()
                logger.info("Resolved dataset from parent hierarchy: %s", resolved)
                return resolved

    raise FileNotFoundError(
        "CRITICAL: master_players.csv could not be found in any expected location. "
        f"Checked candidates: {[str(c) for c in bundled_candidates]}"
    )


class Settings(BaseModel):
    """Application configuration settings."""

    APP_NAME: str = Field(default="CricXI")
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # CORS origins
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    # Database
    DATABASE_URL: str = Field(default="sqlite:///./cricxi.db")

    # Dataset path resolution
    DATASET_PATH: str = Field(default="dataset/output/master_players.csv")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    @classmethod
    def load(cls) -> "Settings":
        """Instantiates Settings from environment variables with fallback defaults."""
        raw_cors = os.getenv("CORS_ORIGINS", "")
        cors_list = [origin.strip() for origin in raw_cors.split(",") if origin.strip()]
        if not cors_list:
            cors_list = [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "https://cric-xi-eta.vercel.app",
            ]

        # Resolve dataset file location robustly
        try:
            resolved_dataset_path = str(resolve_dataset_path())
        except Exception as e:
            logger.error("Error during dataset path resolution: %s", e)
            resolved_dataset_path = str((APP_DATA_DIR / "master_players.csv").resolve())

        # Resolve database URL to canonical absolute path if using relative SQLite
        raw_db_url = os.getenv("DATABASE_URL", "sqlite:///./cricxi.db")
        if raw_db_url.startswith("sqlite:///./") or raw_db_url == "sqlite:///cricxi.db":
            canonical_db = (ROOT_DIR / "cricxi.db").resolve()
            resolved_db_url = f"sqlite:///{canonical_db.as_posix()}"
        elif raw_db_url.startswith("sqlite:///") and not raw_db_url.startswith("sqlite:////") and ":" not in raw_db_url[10:]:
            rel_part = raw_db_url[len("sqlite:///"):]
            resolved_db_url = f"sqlite:///{((ROOT_DIR / rel_part)).resolve().as_posix()}"
        else:
            resolved_db_url = raw_db_url

        return cls(
            APP_NAME=os.getenv("APP_NAME", "CricXI"),
            APP_ENV=os.getenv("APP_ENV", "development"),
            DEBUG=os.getenv("DEBUG", "True").lower() in {"true", "1", "yes"},
            HOST=os.getenv("HOST", "0.0.0.0"),
            PORT=int(os.getenv("PORT", "8000")),
            CORS_ORIGINS=cors_list,
            DATABASE_URL=resolved_db_url,
            DATASET_PATH=resolved_dataset_path,
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        )


settings = Settings.load()
