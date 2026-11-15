"""
Players API Router for CricXI.
Serves real player statistics loaded from Cricsheet master dataset.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.deps import get_dataset_service
from app.config.constants import SUPPORTED_COUNTRIES, SUPPORTED_DECADES, PlayerRole
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.player import PlayerResponse
from app.services.dataset_loader import DatasetLoader

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("/meta/filters")
def get_player_filter_options() -> Dict[str, Any]:
    """Returns supported countries, decades, and roles for frontend filter menus."""
    return {
        "countries": SUPPORTED_COUNTRIES,
        "decades": SUPPORTED_DECADES,
        "roles": [r.value for r in PlayerRole],
    }


@router.get("", response_model=PaginatedResponse[PlayerResponse])
def list_players(
    country: Optional[str] = Query(default=None, description="Filter by country name"),
    decade: Optional[int] = Query(default=None, description="Filter by decade"),
    role: Optional[str] = Query(default=None, description="Filter by primary role (BAT, WK, AR, PACE, SPIN)"),
    search: Optional[str] = Query(default=None, description="Search player name"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    dataset_loader: DatasetLoader = Depends(get_dataset_service),
) -> PaginatedResponse[PlayerResponse]:
    """Retrieves a paginated list of players from the loaded master dataset with optional filtering."""
    players = dataset_loader.get_all_players()

    if country:
        c_low = country.strip().lower()
        players = [p for p in players if str(p.get("country", "")).strip().lower() == c_low]

    if decade is not None:
        players = [p for p in players if int(p.get("decade", 0)) == int(decade)]

    if role:
        r_up = role.strip().upper()
        players = [p for p in players if str(p.get("primary_role", "")).strip().upper() == r_up]

    if search:
        s_low = search.strip().lower()
        players = [p for p in players if s_low in str(p.get("player_name", "")).strip().lower()]

    total = len(players)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    items = players[start_idx:end_idx]

    return PaginatedResponse(
        items=[PlayerResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/country/{country}/decade/{decade}", response_model=List[PlayerResponse])
def get_players_by_country_and_decade(
    country: str,
    decade: int,
    dataset_loader: DatasetLoader = Depends(get_dataset_service),
) -> List[PlayerResponse]:
    """Returns the Best XI player candidates for a specific draft country and decade."""
    players = dataset_loader.get_players_by_country_and_decade(country, decade)
    if not players:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No players found for country '{country}' in decade {decade}.",
        )
    return [PlayerResponse.model_validate(p) for p in players]


@router.get("/{player_id}", response_model=PlayerResponse)
def get_player(
    player_id: int,
    dataset_loader: DatasetLoader = Depends(get_dataset_service),
) -> PlayerResponse:
    """Returns individual player statistics by unique player_id."""
    player = dataset_loader.get_player_by_id(player_id)
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with ID {player_id} not found.",
        )
    return PlayerResponse.model_validate(player)

