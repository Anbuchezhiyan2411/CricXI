"""
Draft API Router for CricXI (Phase 3).
REST endpoints for starting draft, querying live draft state,
submitting player selections, and retrieving available pools.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_ws_manager
from app.draft.draft_service import DraftService
from app.draft.draft_manager import draft_manager
from app.schemas.common import ApiResponse
from app.schemas.draft import DraftPickCreate, DraftStateResponse
from app.schemas.player import PlayerResponse
from app.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/draft", tags=["Draft"])


@router.post("/{room_code}/start", response_model=ApiResponse[DraftStateResponse])
async def start_draft(
    room_code: str,
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[DraftStateResponse]:
    """Starts the 11-round player draft and initializes the live timer loop."""
    code = room_code.strip().upper()
    try:
        DraftService.initialize_draft(db, code)
        state_resp = DraftService.get_draft_state_response(db, code)

        # Start timer countdown loop
        draft_manager.start_room_timer(code)

        payload = state_resp.model_dump(mode="json")
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "draft_started",
                "room_code": code,
                "draft_state": payload,
            },
        )
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "round_generated",
                "room_code": code,
                "current_round": state_resp.current_round,
                "round_country": state_resp.round_country,
                "round_decade": state_resp.round_decade,
            },
        )
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "draft_state_updated",
                "room_code": code,
                "draft_state": payload,
            },
        )

        return ApiResponse(
            success=True,
            message="Draft started successfully.",
            data=state_resp,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error starting draft for room %s: %s", code, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to start draft.")


@router.get("/{room_code}/state", response_model=ApiResponse[DraftStateResponse])
def get_draft_state(
    room_code: str,
    db: Session = Depends(get_db),
) -> ApiResponse[DraftStateResponse]:
    """Retrieves full live draft state including Best XI squads and candidate pool."""
    code = room_code.strip().upper()
    try:
        state_resp = DraftService.get_draft_state_response(db, code)

        # Ensure timer is running if draft is active
        if not state_resp.is_finished and not draft_manager.is_timer_running(code):
            draft_manager.start_room_timer(code)

        return ApiResponse(
            success=True,
            message="Draft state retrieved.",
            data=state_resp,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception("Error fetching draft state for room %s: %s", code, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch draft state.")


@router.post("/{room_code}/pick", response_model=ApiResponse[DraftStateResponse])
async def make_draft_pick(
    room_code: str,
    payload: DraftPickCreate,
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> ApiResponse[DraftStateResponse]:
    """Locks a candidate player into a specified batting position for the active user."""
    code = room_code.strip().upper()
    try:
        pick, is_draft_finished = DraftService.make_pick(
            db=db,
            room_code=code,
            user_id=payload.user_id,
            player_id=payload.player_id,
            batting_position=payload.batting_position,
            is_auto=False,
        )

        pick_payload = {
            "id": pick.id,
            "round_number": pick.round_number,
            "user_id": pick.user_id,
            "player_id": pick.player_id,
            "player_name": pick.player_name,
            "batting_position": pick.batting_position,
            "selected_country": pick.selected_country,
            "selected_decade": pick.selected_decade,
        }

        # Broadcast player_selected and player_locked
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "player_selected",
                "room_code": code,
                "user_id": payload.user_id,
                "pick": pick_payload,
            },
        )
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "player_locked",
                "room_code": code,
                "user_id": payload.user_id,
                "pick": pick_payload,
            },
        )

        fresh_state = DraftService.get_draft_state_response(db, code)
        fresh_payload = fresh_state.model_dump(mode="json")

        if is_draft_finished:
            draft_manager.stop_room_timer(code)
            # Authoritatively initialize toss session
            try:
                from app.toss.toss_service import TossService
                toss_state_resp = TossService.initialize_or_get_toss(db, code)
                toss_payload = toss_state_resp.model_dump(mode="json")
            except Exception as toss_init_err:
                logger.warning("Error initializing toss after draft completion: %s", toss_init_err)
                toss_payload = None

            await ws_manager.broadcast_to_room(
                code,
                {
                    "type": "draft_finished",
                    "room_code": code,
                    "draft_state": fresh_payload,
                    "toss_state": toss_payload,
                },
            )
            if toss_payload:
                await ws_manager.broadcast_to_room(
                    code,
                    {
                        "type": "toss_started",
                        "room_code": code,
                        "toss_state": toss_payload,
                    },
                )
        else:
            # If new round generated
            if fresh_state.current_turn == 1:
                await ws_manager.broadcast_to_room(
                    code,
                    {
                        "type": "round_finished",
                        "room_code": code,
                        "round_number": fresh_state.current_round - 1,
                    },
                )
                await ws_manager.broadcast_to_room(
                    code,
                    {
                        "type": "round_generated",
                        "room_code": code,
                        "current_round": fresh_state.current_round,
                        "round_country": fresh_state.round_country,
                        "round_decade": fresh_state.round_decade,
                    },
                )

            # Restart timer for next turn
            draft_manager.start_room_timer(code)

        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "draft_state_updated",
                "room_code": code,
                "draft_state": fresh_payload,
            },
        )

        return ApiResponse(
            success=True,
            message="Player drafted successfully.",
            data=fresh_state,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error executing pick in room %s: %s", code, e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to execute pick.")


@router.get("/{room_code}/pool", response_model=ApiResponse[List[PlayerResponse]])
def get_round_pool(
    room_code: str,
    db: Session = Depends(get_db),
) -> ApiResponse[List[PlayerResponse]]:
    """Retrieves available candidate pool for current round's Country and Decade."""
    code = room_code.strip().upper()
    try:
        state_resp = DraftService.get_draft_state_response(db, code)
        return ApiResponse(
            success=True,
            message="Candidate pool retrieved.",
            data=state_resp.available_pool,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

