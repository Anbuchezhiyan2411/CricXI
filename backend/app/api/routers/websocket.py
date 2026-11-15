"""
WebSocket Route for CricXI Real-time Multiplayer Communication (Phase 2).
Provides room-based bidirectional WebSocket event synchronization:
- room_created
- room_joined
- player_joined
- player_left
- player_ready
- player_not_ready
- room_updated
- game_start
- connection_error
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_ws_manager
from app.database.session import SessionLocal
from app.matchmaking.room_service import (
    RoomService,
    build_room_response,
)
from app.models.room import Room, RoomPlayer
from app.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/{room_code}/{player_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_code: str,
    player_id: str,
    ws_manager: ConnectionManager = Depends(get_ws_manager),
) -> None:
    """Handles real-time WebSocket connection for room members."""
    code = room_code.strip().upper()
    db: Session = SessionLocal()

    try:
        # 1. Validate room existence
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            await websocket.accept()
            await websocket.send_text(
                json.dumps({
                    "type": "connection_error",
                    "message": f"Room '{code}' does not exist.",
                })
            )
            await websocket.close(code=4004)
            return

        # If room is already completed or abandoned, notify client to return to lobby cleanly
        if room.status in ("COMPLETED", "ABANDONED"):
            await websocket.accept()
            await websocket.send_text(
                json.dumps({
                    "type": "match_abandoned",
                    "room_code": code,
                    "status": room.status,
                    "message": "This match has ended. Returning to lobby...",
                })
            )
            await websocket.close(code=1000)
            return

        # 2. Validate player identity
        player = (
            db.query(RoomPlayer)
            .filter(RoomPlayer.room_id == room.id, RoomPlayer.user_id == player_id)
            .first()
        )

        if not player:
            # Check if slots are reserved for a disconnected player or room is full
            is_reserved = any(
                ws_manager.is_player_disconnected(code, p.user_id) for p in room.players
            )
            if len(room.players) >= 2 or is_reserved or room.status in ("DRAFT", "DRAFTING", "TOSS", "IN_PROGRESS"):
                await websocket.accept()
                await websocket.send_text(
                    json.dumps({
                        "type": "connection_error",
                        "message": "Player slot reserved. Waiting for original player to reconnect." if (is_reserved or len(room.players) >= 2) else "Room is full. Spectators are not permitted.",
                    })
                )
                await websocket.close(code=4003)
                return

        # 3. Accept and register connection
        await ws_manager.connect(websocket, code, player_id)
        room.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(room)

        # Check if this player was previously disconnected (within 30s window)
        was_disconnected = ws_manager.cancel_disconnect_timer(code, player_id)
        if was_disconnected:
            logger.info("Player %s (%s) reconnected to room %s within disconnect window", player.username if player else "", player_id, code)
            await ws_manager.broadcast_to_room(
                code,
                {
                    "type": "player_reconnected",
                    "room_code": code,
                    "user_id": player_id,
                    "username": player.username if player else "",
                },
            )

        current_room_resp = build_room_response(room, current_user_id=player_id)
        room_payload = current_room_resp.model_dump(mode="json")

        # Send room_joined acknowledgment directly to connecting player
        await ws_manager.send_personal_message(
            player_id,
            {
                "type": "room_joined",
                "room_code": code,
                "player_id": player_id,
                "username": player.username if player else "",
                "room": room_payload,
            },
        )

        # Broadcast player_joined and room_updated to room members
        await ws_manager.broadcast_to_room(
            code,
            {
                "type": "player_joined",
                "player_id": player_id,
                "username": player.username if player else "",
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

        # If room is in drafting phase, send reconnected event with complete restored state
        from app.models.draft import DraftState
        from app.draft.draft_service import DraftService
        from app.draft.draft_manager import draft_manager

        draft_state_rec = db.query(DraftState).filter(DraftState.room_id == room.id).first()
        if room.status in ("DRAFT", "DRAFTING") and draft_state_rec and not draft_state_rec.is_finished:
            try:
                if was_disconnected:
                    DraftService.resume_draft(db, code)
                    draft_manager.start_room_timer(code)

                draft_state_resp = DraftService.get_draft_state_response(db, code)
                draft_payload = draft_state_resp.model_dump(mode="json")

                await ws_manager.send_personal_message(
                    player_id,
                    {
                        "type": "draft_state_updated",
                        "room_code": code,
                        "player_id": player_id,
                        "draft_state": draft_payload,
                    },
                )

                if was_disconnected:
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "draft_state_updated",
                            "room_code": code,
                            "draft_state": draft_payload,
                        },
                    )
                elif not draft_state_resp.is_finished and not draft_manager.is_timer_running(code):
                    draft_manager.start_room_timer(code)
            except Exception as e:
                logger.warning("Error restoring draft state on reconnect: %s", e)

        # If room is in toss phase, send toss_state_updated event
        from app.models.toss import TossState
        from app.toss.toss_service import TossService

        toss_rec = db.query(TossState).filter(TossState.room_id == room.id).first()
        if toss_rec:
            try:
                toss_state_resp = TossService.get_toss_state_response(db, code, player_id)
                toss_payload = toss_state_resp.model_dump(mode="json")
                await ws_manager.send_personal_message(
                    player_id,
                    {
                        "type": "toss_state_updated",
                        "room_code": code,
                        "player_id": player_id,
                        "toss_state": toss_payload,
                    },
                )
            except Exception as e:
                logger.warning("Error restoring toss state on reconnect: %s", e)

        # If room has a match (LIVE or COMPLETED), send match_state_updated event
        from app.models.match import Match
        from app.match.match_service import MatchService
        from app.match.match_manager import match_manager

        try:
            match_rec = db.query(Match).filter(Match.room_id == room.id).first()
            if match_rec and match_rec.status in ("LIVE", "COMPLETED", "TIED"):
                if was_disconnected and match_rec.status == "LIVE":
                    MatchService.set_simulation_controls(db, code, action="play")
                    match_manager.start_match_simulation(code)

                match_state_resp = MatchService.get_live_match_state(db, code)
                match_payload = match_state_resp.model_dump(mode="json")
                await ws_manager.send_personal_message(
                    player_id,
                    {
                        "type": "match_state_updated",
                        "room_code": code,
                        "player_id": player_id,
                        "match_state": match_payload,
                    },
                )
                if was_disconnected and match_rec.status == "LIVE":
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "match_state_updated",
                            "room_code": code,
                            "match_state": match_payload,
                        },
                    )
                elif match_rec.status == "LIVE" and not match_rec.is_paused and not match_manager.is_simulation_running(code):
                    match_manager.start_match_simulation(code)
        except Exception as e:
            logger.warning("Error checking or restoring match state on reconnect: %s", e)

        # 4. Event processing loop with Heartbeat timeout detection
        is_intentional_leave = False
        while True:
            try:
                # Wait up to 12.0 seconds for heartbeat/action from client
                data = await asyncio.wait_for(websocket.receive_text(), timeout=12.0)
            except asyncio.TimeoutError:
                logger.warning("Heartbeat timeout expired for player %s in room %s (>12s inactive)", player_id, code)
                break
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await ws_manager.send_personal_message(
                    player_id,
                    {"type": "connection_error", "message": "Invalid JSON format."},
                )
                continue

            event_type = msg.get("type") or msg.get("action", "")
            event_type = event_type.lower()

            # Refresh room state from DB
            db.refresh(room)
            ws_manager.record_heartbeat(code, player_id)

            if event_type in ("heartbeat", "ping"):
                await ws_manager.send_personal_message(
                    player_id,
                    {
                        "type": "heartbeat_ack" if event_type == "heartbeat" else "pong",
                        "timestamp": msg.get("timestamp"),
                    },
                )
                continue

            elif event_type == "player_left":
                is_intentional_leave = True
                logger.info("Player %s intentionally leaving room %s", player_id, code)
                break

            if event_type in {"player_ready", "ready"}:
                RoomService.toggle_player_ready(db, code, player_id, is_ready=True)
                updated_resp = build_room_response(room, current_user_id=player_id).model_dump(mode="json")
                await ws_manager.broadcast_to_room(
                    code,
                    {
                        "type": "player_ready",
                        "player_id": player_id,
                        "room": updated_resp,
                    },
                )
                await ws_manager.broadcast_to_room(
                    code,
                    {
                        "type": "room_updated",
                        "room": updated_resp,
                    },
                )

            elif event_type in {"player_not_ready", "not_ready"}:
                RoomService.toggle_player_ready(db, code, player_id, is_ready=False)
                updated_resp = build_room_response(room, current_user_id=player_id).model_dump(mode="json")
                await ws_manager.broadcast_to_room(
                    code,
                    {
                        "type": "player_not_ready",
                        "player_id": player_id,
                        "room": updated_resp,
                    },
                )
                await ws_manager.broadcast_to_room(
                    code,
                    {
                        "type": "room_updated",
                        "room": updated_resp,
                    },
                )

            elif event_type in {"toggle_ready", "ready_toggle"}:
                RoomService.toggle_player_ready(db, code, player_id)
                db.refresh(room)
                current_p = next((p for p in room.players if p.user_id == player_id), None)
                updated_resp = build_room_response(room, current_user_id=player_id).model_dump(mode="json")
                
                type_name = "player_ready" if (current_p and current_p.is_ready) else "player_not_ready"
                await ws_manager.broadcast_to_room(
                    code,
                    {
                        "type": type_name,
                        "player_id": player_id,
                        "room": updated_resp,
                    },
                )
                await ws_manager.broadcast_to_room(
                    code,
                    {
                        "type": "room_updated",
                        "room": updated_resp,
                    },
                )

            elif event_type in {"game_start", "start_game"}:
                try:
                    RoomService.start_game(db, code, player_id)
                    db.refresh(room)
                    updated_resp = build_room_response(room, current_user_id=player_id).model_dump(mode="json")
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "game_start",
                            "room_code": code,
                            "room": updated_resp,
                        },
                    )
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "room_updated",
                            "room": updated_resp,
                        },
                    )
                except (PermissionError, ValueError) as err:
                    await ws_manager.send_personal_message(
                        player_id,
                        {
                            "type": "connection_error",
                            "message": str(err),
                        },
                    )

            elif event_type in {"player_left", "leave_room"}:
                updated_room = RoomService.leave_room(db, code, player_id)
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
                else:
                    updated_resp = build_room_response(updated_room).model_dump(mode="json")
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "player_left",
                            "player_id": player_id,
                            "room": updated_resp,
                        },
                    )
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "room_updated",
                            "room": updated_resp,
                        },
                    )
                break

            elif event_type in {"make_pick", "pick_player"}:
                try:
                    player_id_to_pick = int(msg.get("player_id", 0))
                    batting_pos = int(msg.get("batting_position", 0))
                    pick, is_draft_finished = DraftService.make_pick(
                        db=db,
                        room_code=code,
                        user_id=player_id,
                        player_id=player_id_to_pick,
                        batting_position=batting_pos,
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

                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "player_selected",
                            "room_code": code,
                            "user_id": player_id,
                            "pick": pick_payload,
                        },
                    )
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "player_locked",
                            "room_code": code,
                            "user_id": player_id,
                            "pick": pick_payload,
                        },
                    )

                    fresh_state = DraftService.get_draft_state_response(db, code)
                    fresh_payload = fresh_state.model_dump(mode="json")

                    if is_draft_finished:
                        draft_manager.stop_room_timer(code)
                        try:
                            from app.toss.toss_service import TossService
                            toss_state_resp = TossService.initialize_or_get_toss(db, code)
                            toss_payload = toss_state_resp.model_dump(mode="json")
                        except Exception as toss_init_err:
                            logger.warning("Error initializing toss in ws pick: %s", toss_init_err)
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
                        draft_manager.start_room_timer(code)

                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "draft_state_updated",
                            "room_code": code,
                            "draft_state": fresh_payload,
                        },
                    )
                except Exception as err:
                    await ws_manager.send_personal_message(
                        player_id,
                        {
                            "type": "connection_error",
                            "message": str(err),
                        },
                    )

            elif event_type in {"request_draft_state", "get_draft_state"}:
                try:
                    fresh_state = DraftService.get_draft_state_response(db, code)
                    await ws_manager.send_personal_message(
                        player_id,
                        {
                            "type": "draft_state_updated",
                            "room_code": code,
                            "draft_state": fresh_state.model_dump(mode="json"),
                        },
                    )
                except Exception as err:
                    logger.warning("Error fetching draft state via WS: %s", err)

            elif event_type in {"toss_call", "call_toss"}:
                try:
                    choice = str(msg.get("choice", "")).strip().upper()
                    toss_state_resp = TossService.make_call(
                        db=db,
                        room_code=code,
                        user_id=player_id,
                        choice=choice,
                    )
                    payload = toss_state_resp.model_dump(mode="json")

                    # Broadcast coin flipped event with animation outcome
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "toss_flipped",
                            "room_code": code,
                            "caller_id": toss_state_resp.caller_id,
                            "caller_name": toss_state_resp.caller_name,
                            "caller_choice": toss_state_resp.caller_choice,
                            "coin_result": toss_state_resp.coin_result,
                            "winner_id": toss_state_resp.winner_id,
                            "winner_name": toss_state_resp.winner_name,
                            "toss_state": payload,
                        },
                    )
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "toss_state_updated",
                            "room_code": code,
                            "toss_state": payload,
                        },
                    )
                except Exception as err:
                    await ws_manager.send_personal_message(
                        player_id,
                        {
                            "type": "connection_error",
                            "message": str(err),
                        },
                    )

            elif event_type in {"toss_decision", "make_decision", "toss_choice"}:
                try:
                    decision = str(msg.get("decision", "")).strip().upper()
                    try:
                        toss_state_resp = TossService.make_decision(
                            db=db,
                            room_code=code,
                            user_id=player_id,
                            decision=decision,
                        )
                    except ValueError as ve:
                        if "already been submitted" in str(ve).lower():
                            toss_state_resp = TossService.get_toss_state_response(db, code, player_id)
                        else:
                            raise ve

                    payload = toss_state_resp.model_dump(mode="json")

                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "toss_completed",
                            "room_code": code,
                            "match_id": toss_state_resp.match_id,
                            "winner_id": toss_state_resp.winner_id,
                            "winner_name": toss_state_resp.winner_name,
                            "decision": toss_state_resp.decision,
                            "toss_state": payload,
                        },
                    )
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "toss_state_updated",
                            "room_code": code,
                            "toss_state": payload,
                        },
                    )

                    # Also broadcast match_started
                    try:
                        match_state_resp = MatchService.get_live_match_state(db, code)
                        match_payload = match_state_resp.model_dump(mode="json")
                        room_payload = build_room_response(room, current_user_id=player_id).model_dump(mode="json")

                        await ws_manager.broadcast_to_room(
                            code,
                            {
                                "type": "match_started",
                                "room_code": code,
                                "match_id": toss_state_resp.match_id,
                                "winner_id": toss_state_resp.winner_id,
                                "decision": toss_state_resp.decision,
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
                        if match_state_resp.status == "LIVE" and not match_state_resp.is_paused:
                            match_manager.start_match_simulation(code)
                    except Exception as err:
                        logger.warning("Error broadcasting match_started in WS: %s", err)
                except Exception as err:
                    await ws_manager.send_personal_message(
                        player_id,
                        {
                            "type": "connection_error",
                            "message": str(err),
                        },
                    )

            elif event_type in {"play_again", "rematch"}:
                try:
                    room, is_barrier_met, ready_user_ids = RoomService.request_play_again(
                        db, code, player_id
                    )
                    room_resp = build_room_response(room, current_user_id=player_id)
                    room_payload = room_resp.model_dump(mode="json")

                    if not is_barrier_met:
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
                    else:
                        draft_resp = DraftService.get_draft_state_response(db, code)
                        draft_payload = draft_resp.model_dump(mode="json")
                        reset_event = {
                            "type": "room_reset",
                            "room_code": code,
                            "new_room_code": code,
                            "room": room_payload,
                            "draft_state": draft_payload,
                        }
                        await ws_manager.broadcast_to_room(code, reset_event)
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
                except Exception as err:
                    await ws_manager.send_personal_message(
                        player_id,
                        {
                            "type": "connection_error",
                            "message": str(err),
                        },
                    )

            elif event_type in {"request_toss_state", "get_toss_state"}:
                try:
                    toss_state_resp = TossService.get_toss_state_response(db, code, player_id)
                    await ws_manager.send_personal_message(
                        player_id,
                        {
                            "type": "toss_state_updated",
                            "room_code": code,
                            "toss_state": toss_state_resp.model_dump(mode="json"),
                        },
                    )
                except Exception as err:
                    logger.warning("Error fetching toss state via WS: %s", err)

            elif event_type in {"request_match_state", "get_match_state"}:
                try:
                    match_state_resp = MatchService.get_live_match_state(db, code)
                    await ws_manager.send_personal_message(
                        player_id,
                        {
                            "type": "match_state_updated",
                            "room_code": code,
                            "match_state": match_state_resp.model_dump(mode="json"),
                        },
                    )
                except Exception as err:
                    logger.warning("Error fetching match state via WS: %s", err)

            elif event_type in {"match_control", "simulation_control"}:
                try:
                    action = str(msg.get("control_action") or msg.get("action_type") or "").strip().lower()
                    speed = msg.get("speed")
                    if action in ("pause", "stop"):
                        match_manager.stop_match_simulation(code)
                        updated_state = MatchService.set_simulation_controls(db, code, action="pause", speed=speed)
                    elif action in ("play", "resume"):
                        updated_state = MatchService.set_simulation_controls(db, code, action="play", speed=speed)
                        if updated_state.status == "LIVE":
                            match_manager.start_match_simulation(code)
                    elif action == "set_speed":
                        updated_state = MatchService.set_simulation_controls(db, code, action="none", speed=speed)
                    else:
                        continue

                    payload = updated_state.model_dump(mode="json")
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "match_control_updated",
                            "room_code": code,
                            "action": action,
                            "speed": speed,
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
                except Exception as err:
                    logger.warning("Error processing match control via WS: %s", err)

            elif event_type == "ping":
                await ws_manager.send_personal_message(player_id, {"type": "pong"})

            else:
                logger.debug("Received unhandled event type: %s", event_type)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for player %s in room %s", player_id, code)
    except Exception as e:
        logger.exception("Unexpected error in WebSocket loop: %s", e)
    finally:
        ws_manager.disconnect(code, player_id, websocket)

        # Check if the player is still connected via another active socket (e.g. rapid page refresh / duplicate tab)
        is_still_connected = ws_manager.is_player_connected(player_id)
        if not is_still_connected:
            try:
                room = db.query(Room).filter(Room.room_code == code).first()
                if room and len(room.players) > 1:
                    from app.match.match_service import MatchService
                    from app.draft.draft_service import DraftService
                    from app.match.match_manager import match_manager
                    from app.draft.draft_manager import draft_manager

                    username_str = player.username if player else "Opponent"

                    if is_intentional_leave:
                        # Intentional departure (e.g. clicked Lobby or Leave room)
                        logger.info("Player %s intentionally left room %s", player_id, code)
                        draft_manager.stop_room_timer(code)
                        match_manager.stop_match_simulation(code)

                        if room.status in ("DRAFT", "DRAFTING"):
                            DraftService.cancel_draft(db, code, reason="Opponent left the match")
                        elif room.status in ("IN_PROGRESS", "LIVE"):
                            MatchService.abandon_match(db, code, disconnected_user_id=player_id, reason="Opponent left the match")
                        else:
                            room.status = "COMPLETED"
                            db.commit()

                        await ws_manager.broadcast_to_room(
                            code,
                            {
                                "type": "player_left",
                                "room_code": code,
                                "player_id": player_id,
                                "user_id": player_id,
                                "intentional": True,
                                "message": f"{username_str} has left the match.",
                            },
                        )
                    else:
                        # Unexpected disconnect (browser closed, wifi dropped, process killed, heartbeat timeout)
                        # Immediately freeze game state
                        logger.info("Player %s unexpectedly disconnected from room %s. Freezing state and starting 30s countdown.", player_id, code)

                        if room.status in ("DRAFT", "DRAFTING"):
                            draft_manager.stop_room_timer(code)
                            DraftService.pause_draft(db, code)
                            draft_resp = DraftService.get_draft_state_response(db, code)
                            await ws_manager.broadcast_to_room(
                                code,
                                {
                                    "type": "draft_state_updated",
                                    "room_code": code,
                                    "draft_state": draft_resp.model_dump(mode="json"),
                                },
                            )
                        elif room.status in ("IN_PROGRESS", "LIVE"):
                            match_manager.stop_match_simulation(code)
                            MatchService.set_simulation_controls(db, code, action="pause")
                            match_resp = MatchService.get_live_match_state(db, code)
                            await ws_manager.broadcast_to_room(
                                code,
                                {
                                    "type": "match_state_updated",
                                    "room_code": code,
                                    "match_state": match_resp.model_dump(mode="json"),
                                },
                            )

                        # Broadcast player_disconnected with 30s countdown
                        await ws_manager.broadcast_to_room(
                            code,
                            {
                                "type": "player_disconnected",
                                "room_code": code,
                                "user_id": player_id,
                                "username": username_str,
                                "seconds_remaining": 30,
                            },
                        )

                        # 30-second abandonment callback
                        async def on_30s_timeout(r_code: str, p_id: str):
                            t_db = SessionLocal()
                            try:
                                r = t_db.query(Room).filter(Room.room_code == r_code).first()
                                if not r:
                                    return
                                remaining_p = next((p for p in r.players if p.user_id != p_id), None)
                                winner_id = remaining_p.user_id if remaining_p else None

                                draft_manager.stop_room_timer(r_code)
                                match_manager.stop_match_simulation(r_code)

                                if r.status in ("DRAFT", "DRAFTING"):
                                    DraftService.cancel_draft(t_db, r_code, reason="Opponent failed to reconnect within 30 seconds")
                                elif r.status in ("IN_PROGRESS", "LIVE"):
                                    MatchService.abandon_match(t_db, r_code, disconnected_user_id=p_id, reason="Opponent failed to reconnect within 30 seconds")
                                else:
                                    r.status = "COMPLETED"
                                    t_db.commit()

                                await ws_manager.broadcast_to_room(
                                    r_code,
                                    {
                                        "type": "disconnect_timeout",
                                        "room_code": r_code,
                                        "disconnected_user_id": p_id,
                                        "winner_id": winner_id,
                                        "abandoned": True,
                                        "title": "Opponent Disconnected",
                                        "message": "Match abandoned. You win by opponent disconnect.",
                                        "submessage": "Returning to lobby...",
                                    },
                                )
                                # Clean up all timers and connection references for this room
                                ws_manager.destroy_room(r_code)
                            except Exception as ex:
                                logger.exception("Error executing 30s disconnect timeout for room %s: %s", r_code, ex)
                            finally:
                                t_db.close()

                        ws_manager.start_disconnect_timer(
                            room_code=code,
                            player_id=player_id,
                            username=username_str,
                            on_timeout_callback=on_30s_timeout,
                            timeout_seconds=30,
                        )
            except Exception as e:
                logger.warning("Error during websocket disconnect handling: %s", e)
            finally:
                db.close()
        else:
            db.close()
