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
APP_DATA_DIR = (APP_DIR / "data").resolve()
CANONICAL_DATASET_PATH = (APP_DATA_DIR / "master_players.csv").resolve()

# Load environment variables
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")


def resolve_dataset_path(raw_path: Optional[str] = None) -> Path:
    """
    Robustly resolves the master_players.csv dataset absolute path.
    Guarantees exactly ONE canonical location bundled with the backend package.
    Supports local dev, Railway, Docker, and arbitrary working directories.
    Validates DATASET_PATH env var if provided; falls back to CANONICAL_DATASET_PATH.
    """
    env_val = (raw_path or os.getenv("DATASET_PATH", "")).strip()
    if env_val:
        # Check direct path (absolute or relative to current working dir)
        direct_cand = Path(env_val).resolve()
        if direct_cand.is_file():
            logger.info("Using valid configured DATASET_PATH: %s", direct_cand)
            return direct_cand

        # Check relative to base directories without leading/trailing slashes
        clean_rel = env_val.lstrip("/\\")
        for base in [APP_DATA_DIR, APP_DIR, BACKEND_DIR, ROOT_DIR]:
            rel_cand = (base / clean_rel).resolve()
            if rel_cand.is_file():
                logger.info("Resolved configured DATASET_PATH relative to %s: %s", base, rel_cand)
                return rel_cand

        logger.warning(
            "Configured DATASET_PATH '%s' does not exist or is unreadable. "
            "Automatically falling back to canonical bundled dataset: %s",
            env_val,
            CANONICAL_DATASET_PATH,
        )

    # Use single canonical bundled dataset path
    if CANONICAL_DATASET_PATH.is_file():
        logger.info("Using canonical bundled dataset: %s", CANONICAL_DATASET_PATH)
        return CANONICAL_DATASET_PATH

    # Check fallback in data directory
    alt_players = (APP_DATA_DIR / "players.csv").resolve()
    if alt_players.is_file():
        logger.warning("Using fallback players.csv at: %s", alt_players)
        return alt_players

    raise FileNotFoundError(
        f"CRITICAL: master_players.csv could not be found at canonical location: {CANONICAL_DATASET_PATH}"
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

    # Dataset path resolution - defaults to canonical bundled dataset
    DATASET_PATH: str = Field(default=str(CANONICAL_DATASET_PATH))

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
            resolved_dataset_path = str(CANONICAL_DATASET_PATH)

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
