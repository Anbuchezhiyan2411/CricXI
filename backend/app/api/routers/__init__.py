"""
API Routers Package for CricXI.
"""

from app.api.routers.health import router as health_router
from app.api.routers.players import router as players_router
from app.api.routers.rooms import router as rooms_router
from app.api.routers.draft import router as draft_router
from app.api.routers.toss import router as toss_router
from app.api.routers.matches import router as matches_router
from app.api.routers.history import router as history_router
from app.api.routers.websocket import router as ws_router

__all__ = [
    "health_router",
    "players_router",
    "rooms_router",
    "draft_router",
    "toss_router",
    "matches_router",
    "history_router",
    "ws_router",
]
