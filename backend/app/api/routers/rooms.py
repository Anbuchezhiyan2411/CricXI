"""
Rooms API Router for CricXI (Phase 2).
Provides full multiplayer lobby coordination endpoints:
- POST /api/rooms/create
- POST /api/rooms/join
- POST /api/rooms/leave
- GET /api/rooms/{room_code}
- POST /api/rooms/start
- GET /api/rooms/validate/{room_code}
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_ws_manager
from app.matchmaking.room_service import RoomService, build_room_response
from app.draft.draft_service import DraftService
from app.draft.draft_manager import draft_manager
from app.models.room import Room
from app.schemas.common import ApiResponse
from app.schemas.room import (
    PlayAgainResponse,
    RoomCreate,
    RoomJoin,
    RoomLeave,
    RoomPlayAgain,
    RoomResponse,
    RoomStart,
    RoomValidateResponse,
)
from app.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rooms", tags=["Rooms"])


@router.post("/create", response_model=ApiResponse[RoomResponse], status_code=status.HTTP_201_CREATED)
@router.post("", response_model=ApiResponse[RoomResponse], status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[RoomResponse]:
    """Creates a new multiplayer room with a unique 6-character room code."""
    try:
        room, host_id = RoomService.create_room(db, payload.username)
        room_resp = build_room_response(room, current_user_id=host_id)

        # Broadcast event
        await ws_manager.broadcast_to_room(
            room.room_code,
            {
                "type": "room_created",
                "room_code": room.room_code,
                "host_id": host_id,
                "room": room_resp.model_dump(mode="json"),
            },
        )

        return ApiResponse(
            success=True,
            message="Room created successfully.",
            data=room_resp,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error creating room: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create room.",
        )


@router.post("/join", response_model=ApiResponse[RoomResponse])
async def join_room(
    payload: RoomJoin,
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[RoomResponse]:
    """Joins an existing room using a 6-character friend code."""
    try:
        room, user_id = RoomService.join_room(db, payload.room_code, payload.username, payload.user_id)
        room_resp = build_room_response(room, current_user_id=user_id)

        # Broadcast events to all players in the room
        await ws_manager.broadcast_to_room(
            room.room_code,
            {
                "type": "player_joined",
                "player_id": user_id,
                "username": payload.username.strip(),
                "room": room_resp.model_dump(mode="json"),
            },
        )
        await ws_manager.broadcast_to_room(
            room.room_code,
            {
                "type": "room_updated",
                "room": room_resp.model_dump(mode="json"),
            },
        )

        return ApiResponse(
            success=True,
            message="Joined room successfully.",
            data=room_resp,
        )
    except ValueError as e:
        err_msg = str(e)
        if "does not exist" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        logger.exception("Error joining room: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join room.",
        )


@router.post("/leave", response_model=ApiResponse[dict])
async def leave_room(
    payload: RoomLeave,
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[dict]:
    """Leaves a multiplayer room. If everyone has left, the room is destroyed."""
    code = payload.room_code.strip().upper()
    try:
        updated_room = RoomService.leave_room(db, code, payload.user_id)

        if updated_room is None:
            # Room destroyed
            await ws_manager.broadcast_to_room(
                code,
                {
                    "type": "room_updated",
                    "room": None,
                    "message": "Room destroyed because all players left.",
                },
            )
            ws_manager.destroy_room(code)
            return ApiResponse(
                success=True,
                message="Left room. Room was destroyed as no players remained.",
                data={"room_destroyed": True},
            )

        # Room still active with remaining player
        room_resp = build_room_response(updated_room)
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "player_left",
                "player_id": payload.user_id,
                "room": room_resp.model_dump(mode="json"),
            },
        )
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "room_updated",
                "room": room_resp.model_dump(mode="json"),
            },
        )

        return ApiResponse(
            success=True,
            message="Left room successfully.",
            data={"room_destroyed": False, "room": room_resp.model_dump(mode="json")},
        )
    except Exception as e:
        logger.exception("Error leaving room: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to leave room.",
        )


@router.post("/start", response_model=ApiResponse[RoomResponse])
async def start_game(
    payload: RoomStart,
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[RoomResponse]:
    """Host starts the game when both players are ready."""
    try:
        room = RoomService.start_game(db, payload.room_code, payload.user_id)
        room_resp = build_room_response(room, current_user_id=payload.user_id)

        # Authoritatively initialize draft state and start draft timer loop
        try:
            DraftService.initialize_draft(db, room.room_code)
            draft_manager.start_room_timer(room.room_code)
        except Exception as draft_err:
            logger.warning("Draft initialization in start_game warning: %s", draft_err)

        # Broadcast game start
        await ws_manager.broadcast_to_room(
            room.room_code,
            {
                "type": "game_start",
                "room_code": room.room_code,
                "room": room_resp.model_dump(mode="json"),
            },
        )
        await ws_manager.broadcast_to_room(
            room.room_code,
            {
                "type": "room_updated",
                "room": room_resp.model_dump(mode="json"),
            },
        )

        return ApiResponse(
            success=True,
            message="Game started successfully.",
            data=room_resp,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        err_msg = str(e)
        if "does not exist" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        logger.exception("Error starting game: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start game.",
        )


@router.get("/validate/{room_code}", response_model=ApiResponse[RoomValidateResponse])
def validate_room(
    room_code: str,
    username: Optional[str] = None,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
) -> ApiResponse[RoomValidateResponse]:
    """Validates whether a room code is valid, exists, and is joinable or available for reconnect."""
    result = RoomService.validate_room(db, room_code, user_id=user_id, username=username)
    return ApiResponse(
        success=result.valid,
        message=result.message,
        data=result,
    )


@router.get("/{room_code}", response_model=ApiResponse[RoomResponse])
def get_room(
    room_code: str,
    db: Session = Depends(get_db),
) -> ApiResponse[RoomResponse]:
    """Fetches details, players, and live status of an existing room."""
    code = room_code.strip().upper()
    room = db.query(Room).filter(Room.room_code == code).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room '{code}' does not exist.",
        )

    return ApiResponse(
        success=True,
        message="Room details retrieved.",
        data=build_room_response(room),
    )


@router.post("/{room_code}/play-again", response_model=ApiResponse[PlayAgainResponse])
async def play_again(
    room_code: str,
    payload: RoomPlayAgain,
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[PlayAgainResponse]:
    """
    Handles Play Another Match / Rematch with a multiplayer synchronization barrier:
    - Player 1 clicks: marked ready, broadcasts 'rematch_status', waits for Player 2.
    - Player 2 clicks: barrier met! Room is wiped, existing room code reused, fresh draft generated,
      and 'room_reset' / 'new_match_ready' / 'play_again' broadcast to all players in the room.
    """
    code = room_code.strip().upper()
    try:
        room, is_barrier_met, ready_user_ids = RoomService.request_play_again(
            db, code, payload.user_id
        )
        room_resp = build_room_response(room, current_user_id=payload.user_id)
        room_payload = room_resp.model_dump(mode="json")

        if not is_barrier_met:
            # Broadcast rematch status to room so opponent sees rematch request
            await ws_manager.broadcast_to_room(
                code,
                {
                    "type": "rematch_status",
                    "room_code": code,
                    "ready_user_ids": ready_user_ids,
                    "ready_count": len(ready_user_ids),
                    "total_count": len(room.players),
                    "is_ready_barrier_met": False,
                },
            )

            return ApiResponse(
                success=True,
                message="Waiting for opponent to start another match...",
                data=PlayAgainResponse(
                    old_room_code=code,
                    new_room_code=code,
                    room=room_resp,
                    draft_state=None,
                    is_barrier_met=False,
                    ready_user_ids=ready_user_ids,
                ),
            )

        # Barrier met! Both players confirmed rematch.
        from app.draft.draft_service import DraftService
        draft_resp = DraftService.get_draft_state_response(db, code)
        draft_payload = draft_resp.model_dump(mode="json")

        reset_payload = {
            "type": "room_reset",
            "room_code": code,
            "new_room_code": code,
            "room": room_payload,
            "draft_state": draft_payload,
        }
        await ws_manager.broadcast_to_room(code, reset_payload)

        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "new_match_ready",
                "room_code": code,
                "new_room_code": code,
                "room": room_payload,
                "draft_state": draft_payload,
            },
        )

        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "play_again",
                "old_room_code": code,
                "new_room_code": code,
                "room": room_payload,
                "draft_state": draft_payload,
            },
        )

        return ApiResponse(
            success=True,
            message="Both players ready! Fresh rematch session initialized.",
            data=PlayAgainResponse(
                old_room_code=code,
                new_room_code=code,
                room=room_resp,
                draft_state=draft_payload,
                is_barrier_met=True,
                ready_user_ids=ready_user_ids,
            ),
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        err_msg = str(e)
        if "does not exist" in err_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
    except Exception as e:
        logger.exception("Error initiating play again: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate rematch.",
        )
