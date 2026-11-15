"""
CricXI Application Settings.
Loads and validates environment variables.
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Locate root and backend .env files
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent

# Load environment variables
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(ROOT_DIR / ".env")


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
            ]

        # Resolve dataset file location across common permutations (e.g. Dataset vs dataset)
        raw_dataset_path = os.getenv("DATASET_PATH", "dataset/output/master_players.csv")
        candidate_paths = [
            ROOT_DIR / raw_dataset_path,
            ROOT_DIR / "dataset" / "output" / "master_players.csv",
            ROOT_DIR / "Dataset" / "output" / "master_players.csv",
            BACKEND_DIR / raw_dataset_path,
        ]
        resolved_dataset_path = str(candidate_paths[0])
        for cp in candidate_paths:
            if cp.exists():
                resolved_dataset_path = str(cp)
                break

        return cls(
            APP_NAME=os.getenv("APP_NAME", "CricXI"),
            APP_ENV=os.getenv("APP_ENV", "development"),
            DEBUG=os.getenv("DEBUG", "True").lower() in {"true", "1", "yes"},
            HOST=os.getenv("HOST", "0.0.0.0"),
            PORT=int(os.getenv("PORT", "8000")),
            CORS_ORIGINS=cors_list,
            DATABASE_URL=os.getenv("DATABASE_URL", "sqlite:///./cricxi.db"),
            DATASET_PATH=resolved_dataset_path,
            LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        )


settings = Settings.load()

