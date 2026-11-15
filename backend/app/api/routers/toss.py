"""
Toss API Router for CricXI (Pre-Match Toss Ceremony).
Provides REST endpoints for initializing toss, querying live toss state,
submitting Heads/Tails calls, and making Bat/Bowl pitch decisions.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_ws_manager
from app.schemas.common import ApiResponse
from app.schemas.toss import TossCallRequest, TossDecisionRequest, TossStateResponse
from app.toss.toss_service import TossService
from app.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/toss", tags=["Toss"])


@router.post("/{room_code}/init", response_model=ApiResponse[TossStateResponse])
async def init_toss(
    room_code: str,
    user_id: Optional[str] = Query(None, description="Current user ID"),
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[TossStateResponse]:
    """
    Initializes the toss session for the room (if not already initialized).
    Randomly selects the caller between Host and Guest and broadcasts initial state.
    """
    code = room_code.strip().upper()
    try:
        from app.models.toss import TossState
        from app.models.room import Room
        existing_toss = db.query(TossState).join(Room).filter(Room.room_code == code).first()
        is_new = existing_toss is None

        toss_state = TossService.initialize_or_get_toss(db, code, user_id)

        # Broadcast toss state to room ONLY if newly initialized
        if is_new:
            payload = toss_state.model_dump(mode="json")
            await ws_manager.broadcast_to_room(
                code,
                {
                    "type": "toss_state_updated",
                    "room_code": code,
                    "toss_state": payload,
                },
            )

        return ApiResponse(
            success=True,
            data=toss_state,
            message="Toss session initialized.",
        )
    except ValueError as e:
        logger.warning("Error initializing toss for room %s: %s", code, str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error in init_toss for room %s: %s", code, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize toss session.",
        )


@router.get("/{room_code}/state", response_model=ApiResponse[TossStateResponse])
def get_toss_state(
    room_code: str,
    user_id: Optional[str] = Query(None, description="Current user ID"),
    db: Session = Depends(get_db),
) -> ApiResponse[TossStateResponse]:
    """Retrieves current toss state for the specified room."""
    code = room_code.strip().upper()
    try:
        toss_state = TossService.get_toss_state_response(db, code, user_id)
        return ApiResponse(
            success=True,
            data=toss_state,
            message="Toss state retrieved successfully.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error("Error retrieving toss state for room %s: %s", code, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve toss state.",
        )


@router.post("/{room_code}/call", response_model=ApiResponse[TossStateResponse])
async def call_toss(
    room_code: str,
    req: TossCallRequest,
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[TossStateResponse]:
    """
    Caller calls HEADS or TAILS. Backend flips coin, determines winner,
    and broadcasts the result along with flip animation trigger.
    """
    code = room_code.strip().upper()
    try:
        toss_state = TossService.make_call(
            db,
            code,
            user_id=req.user_id,
            choice=req.choice,
        )

        payload = toss_state.model_dump(mode="json")

        # Broadcast coin flipped event with outcome
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "toss_flipped",
                "room_code": code,
                "caller_id": toss_state.caller_id,
                "caller_name": toss_state.caller_name,
                "caller_choice": toss_state.caller_choice,
                "coin_result": toss_state.coin_result,
                "winner_id": toss_state.winner_id,
                "winner_name": toss_state.winner_name,
                "toss_state": payload,
            },
        )

        # Broadcast state update
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "toss_state_updated",
                "room_code": code,
                "toss_state": payload,
            },
        )

        return ApiResponse(
            success=True,
            data=toss_state,
            message=f"Toss called: {req.choice.upper()}. Coin landed on: {toss_state.coin_result}.",
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Error calling toss in room %s: %s", code, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process toss call.",
        )


@router.post("/{room_code}/decision", response_model=ApiResponse[TossStateResponse])
async def make_toss_decision(
    room_code: str,
    req: TossDecisionRequest,
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[TossStateResponse]:
    """
    Toss winner selects BAT or BOWL first.
    Completes the toss ceremony and transitions match status to LIVE.
    """
    code = room_code.strip().upper()
    try:
        toss_state = TossService.make_decision(
            db,
            code,
            user_id=req.user_id,
            decision=req.decision,
        )

        payload = toss_state.model_dump(mode="json")

        # Broadcast toss completed event
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "toss_completed",
                "room_code": code,
                "match_id": toss_state.match_id,
                "winner_id": toss_state.winner_id,
                "winner_name": toss_state.winner_name,
                "decision": toss_state.decision,
                "toss_state": payload,
            },
        )

        # Broadcast updated state
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "toss_state_updated",
                "room_code": code,
                "toss_state": payload,
            },
        )

        # Broadcast match started with initialized live match state
        from app.match.match_service import MatchService
        from app.match.match_manager import match_manager
        from app.matchmaking.room_service import build_room_response
        from app.models.room import Room

        match_state = MatchService.get_live_match_state(db, code)
        match_payload = match_state.model_dump(mode="json")

        room = db.query(Room).filter(Room.room_code == code).first()
        room_payload = build_room_response(room).model_dump(mode="json") if room else {}

        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "match_started",
                "room_code": code,
                "match_id": toss_state.match_id,
                "winner_id": toss_state.winner_id,
                "decision": toss_state.decision,
                "match_state": match_payload,
                "room": room_payload,
            },
        )

        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "room_updated",
                "room": room_payload,
            },
        )

        # Start match simulation in background
        if match_state.status == "LIVE" and not match_state.is_paused:
            match_manager.start_match_simulation(code)

        return ApiResponse(
            success=True,
            data=toss_state,
            message=f"{toss_state.winner_name} elected to {toss_state.decision} first.",
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error("Error submitting toss decision in room %s: %s", code, str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process toss decision.",
        )

