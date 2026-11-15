"""
CricXI FastAPI Application Entrypoint.
Initializes the backend server, middleware, routes, and dataset services.
"""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from app.config.logging_config import setup_logging
from app.config.settings import settings
from app.database.session import init_db
from app.services.dataset_loader import dataset_service
from app.draft.draft_manager import draft_manager
from app.api.routers import (
    health_router,
    players_router,
    rooms_router,
    draft_router,
    toss_router,
    matches_router,
    history_router,
    ws_router,
)

# Setup logging immediately
setup_logging()
logger = logging.getLogger("cricxi.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for application startup and shutdown."""
    logger.info("Initializing CricXI backend...")

    # Register running event loop with draft manager for cross-thread timers
    try:
        draft_manager.set_event_loop(asyncio.get_running_loop())
    except Exception as loop_err:
        logger.warning("Could not set draft_manager loop: %s", loop_err)

    # 1. Initialize SQLite database schemas
    init_db()
    logger.info("Database schemas initialized.")

    # 2. Load dataset into memory
    dataset_service.load()
    logger.info(
        "Dataset initialized. Loaded: %s (%d players)",
        dataset_service.is_loaded,
        dataset_service.count,
    )

    yield

    logger.info("Shutting down CricXI backend...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Multiplayer T20 Cricket Draft and Simulation Game Engine",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(health_router, prefix="/api")
app.include_router(players_router, prefix="/api")
app.include_router(rooms_router, prefix="/api")
app.include_router(draft_router, prefix="/api")
app.include_router(toss_router, prefix="/api")
app.include_router(matches_router, prefix="/api")
app.include_router(history_router, prefix="/api")
app.include_router(ws_router)


@app.get("/")
def root():
    """Root endpoint for health discovery."""
    return {
        "app": settings.APP_NAME,
        "status": "online",
        "docs": "/docs",
        "api": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
