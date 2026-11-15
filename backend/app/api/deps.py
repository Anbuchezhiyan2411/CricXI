"""
FastAPI Dependency Injections for CricXI.
"""

from typing import Generator
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.services.dataset_loader import DatasetLoader, dataset_service
from app.websocket.connection_manager import ConnectionManager, ws_manager


def get_db() -> Generator[Session, None, None]:
    """Yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_dataset_service() -> DatasetLoader:
    """Returns the singleton dataset loader service."""
    return dataset_service


def get_ws_manager() -> ConnectionManager:
    """Returns the singleton WebSocket connection manager."""
    return ws_manager

