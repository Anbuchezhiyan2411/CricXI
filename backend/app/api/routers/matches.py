"""
Matches API Router for CricXI Live T20 Simulation.
Provides REST endpoints for match initialization, live state retrieval,
simulation playback controls (play, pause, resume, speed), and stepping.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_ws_manager
from app.match.match_service import MatchService
from app.match.match_manager import match_manager
from app.models.match import Match
from app.models.room import Room
from app.schemas.common import ApiResponse
from app.schemas.match import (
    LiveMatchStateResponse,
    SimulationControlRequest,
    MatchResponse,
)
from app.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.post("/{room_code}/init", response_model=ApiResponse[LiveMatchStateResponse])
async def init_match(
    room_code: str,
    auto_start: bool = Query(True, description="Automatically start background simulation loop"),
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[LiveMatchStateResponse]:
    """
    Initializes the T20 match from the room's drafted squads and completed toss.
    Launches the authoritative background delivery simulation loop.
    """
    code = room_code.strip().upper()
    try:
        match_rec = db.query(Match).join(Room).filter(Room.room_code == code).first()
        is_new = match_rec is None or match_rec.status == "PENDING"

        state = MatchService.initialize_or_get_match(db, code)

        if auto_start and state.status == "LIVE" and not state.is_paused:
            match_manager.start_match_simulation(code)

        # Broadcast match initialized to room ONLY if newly initialized
        if is_new:
            payload = state.model_dump(mode="json")
            await ws_manager.broadcast_to_room(
                code,
                {
                    "type": "match_initialized",
                    "room_code": code,
                    "match_state": payload,
                },
            )

        return ApiResponse(
            success=True,
            data=state,
            message="Match initialized successfully.",
        )
    except ValueError as e:
        logger.warning("Error initializing match in room %s: %s", code, str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error in init_match for room %s: %s", code, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize live match.",
        )


@router.get("/{room_code}/state", response_model=ApiResponse[LiveMatchStateResponse])
def get_match_state(
    room_code: str,
    db: Session = Depends(get_db),
) -> ApiResponse[LiveMatchStateResponse]:
    """Retrieves current authoritative live match state, figures, and scorecards."""
    code = room_code.strip().upper()
    try:
        state = MatchService.get_live_match_state(db, code)
        return ApiResponse(
            success=True,
            data=state,
            message="Match state retrieved successfully.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving match state for room %s: %s", code, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve match state.",
        )


@router.post("/{room_code}/step", response_model=ApiResponse[LiveMatchStateResponse])
async def step_match_delivery(
    room_code: str,
    seed: Optional[int] = Query(None, description="Optional seed for deterministic simulation"),
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[LiveMatchStateResponse]:
    """Advances simulation by exactly one delivery."""
    code = room_code.strip().upper()
    try:
        delivery_res, updated_state = MatchService.step_delivery(db, code, seed=seed)
        payload = updated_state.model_dump(mode="json")

        deliv_dict = {
            "outcome": delivery_res.outcome,
            "batter_runs": delivery_res.batter_runs,
            "extras": delivery_res.extras,
            "extra_type": delivery_res.extra_type,
            "runs_scored": delivery_res.runs_scored,
            "is_wicket": delivery_res.is_wicket,
            "wicket_type": delivery_res.wicket_type,
            "is_legal": delivery_res.is_legal,
            "commentary": delivery_res.commentary,
            "short_display": delivery_res.short_display,
        }

        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "ball_result",
                "room_code": code,
                "delivery": deliv_dict,
                "match_state": payload,
            },
        )
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "match_state_updated",
                "room_code": code,
                "match_state": payload,
            },
        )

        return ApiResponse(
            success=True,
            data=updated_state,
            message=delivery_res.commentary,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Error stepping match in room %s: %s", code, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to advance match simulation.",
        )


@router.post("/{room_code}/control", response_model=ApiResponse[LiveMatchStateResponse])
async def control_simulation(
    room_code: str,
    req: SimulationControlRequest,
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[LiveMatchStateResponse]:
    """Controls simulation playback: play, pause, resume, or set speed."""
    code = room_code.strip().upper()
    try:
        action = req.action.strip().lower()

        if action in ("pause", "stop"):
            match_manager.stop_match_simulation(code)
            updated_state = MatchService.set_simulation_controls(db, code, action="pause", speed=req.speed)
        elif action in ("play", "resume"):
            updated_state = MatchService.set_simulation_controls(db, code, action="play", speed=req.speed)
            if updated_state.status == "LIVE":
                match_manager.start_match_simulation(code)
        elif action == "set_speed":
            updated_state = MatchService.set_simulation_controls(db, code, action="none", speed=req.speed)
        else:
            raise ValueError(f"Unknown simulation action: '{req.action}'")

        payload = updated_state.model_dump(mode="json")
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "match_control_updated",
                "room_code": code,
                "action": action,
                "speed": req.speed,
                "match_state": payload,
            },
        )
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "match_state_updated",
                "room_code": code,
                "match_state": payload,
            },
        )

        return ApiResponse(
            success=True,
            data=updated_state,
            message=f"Simulation control updated: {action}.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Error updating simulation control in room %s: %s", code, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update simulation controls.",
        )


@router.get("/summary/{match_id}", response_model=ApiResponse[MatchResponse])
def get_match_summary(
    match_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[MatchResponse]:
    """Legacy summary endpoint by match_id."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Match {match_id} not found.")

    return ApiResponse(
        success=True,
        data=MatchResponse.model_validate(match),
        message="Match summary retrieved.",
    )
