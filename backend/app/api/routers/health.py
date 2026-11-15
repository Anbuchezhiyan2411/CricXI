"""
Health Check Router for CricXI.
"""

from fastapi import APIRouter, Depends
from app.config.settings import settings
from app.schemas.common import HealthStatus
from app.services.dataset_loader import DatasetLoader
from app.api.deps import get_dataset_service

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthStatus)
def check_health(dataset_loader: DatasetLoader = Depends(get_dataset_service)) -> HealthStatus:
    """Returns the operational status and environment diagnostics."""
    return HealthStatus(
        status="ok",
        app_name=settings.APP_NAME,
        version="1.0.0",
        environment=settings.APP_ENV,
        dataset_loaded=dataset_loader.is_loaded,
        players_count=dataset_loader.count,
    )

