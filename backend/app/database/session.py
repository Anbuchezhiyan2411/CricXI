"""
SQLAlchemy Database Session Management.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config.settings import settings
from app.database.base import Base

# Configure SQLite engine with connect_args for multithreaded FastAPI access
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy database session
    and ensures clean closure after the request lifecycle.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Creates all database tables and applies any missing column migrations."""
    # Import models so they register with Base.metadata before create_all
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Perform safe idempotent column migrations on SQLite database files
    try:
        from app.database.migrator import migrate_sqlite_database
        from pathlib import Path
        db_candidates = [
            Path("cricxi.db"),
            Path("backend/cricxi.db"),
            Path("../cricxi.db"),
        ]
        for cand in db_candidates:
            if cand.exists():
                migrate_sqlite_database(str(cand))
    except Exception as e:
        import logging
        logging.getLogger("cricxi.session").warning("Auto-migration notice: %s", e)


