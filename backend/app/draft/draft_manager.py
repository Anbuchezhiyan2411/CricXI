"""
CricXI Live Draft Manager (Phase 3).
Coordinates real-time pick timers, auto-selection countdowns,
and WebSocket event broadcasts for all active draft rooms.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.draft.draft_service import DraftService
from app.websocket.connection_manager import ws_manager

logger = logging.getLogger(__name__)


class DraftManager:
    """Manages background countdown timers and WebSocket broadcasts per room."""

    def __init__(self) -> None:
        # room_code -> asyncio.Task
        self._active_timers: Dict[str, asyncio.Task] = {}

    def is_timer_running(self, room_code: str) -> bool:
        task = self._active_timers.get(room_code.strip().upper())
        return task is not None and not task.done()

    def start_room_timer(self, room_code: str) -> None:
        """Starts or restarts the 30-second countdown task for a room."""
        code = room_code.strip().upper()
        self.stop_room_timer(code)
        try:
            loop = asyncio.get_running_loop()
            self._active_timers[code] = loop.create_task(self._timer_loop(code))
            logger.info("Timer task started for draft room %s", code)
        except RuntimeError:
            logger.info("No running event loop; room timer for %s deferred", code)

    def stop_room_timer(self, room_code: str) -> None:
        """Cancels any running countdown task for a room."""
        code = room_code.strip().upper()
        task = self._active_timers.pop(code, None)
        if task and not task.done():
            task.cancel()
            logger.info("Timer task stopped for draft room %s", code)

    async def _timer_loop(self, room_code: str) -> None:
        """Asynchronous countdown loop ticking every second."""
        code = room_code.strip().upper()

        try:
            # Broadcast initial timer_started event
            db: Session = SessionLocal()
            try:
                state_resp = DraftService.get_draft_state_response(db, code)
                await ws_manager.broadcast_to_room(
                    code,
                    {
                        "type": "timer_started",
                        "room_code": code,
                        "remaining": state_resp.remaining_seconds,
                        "current_picker_id": state_resp.current_picker_id,
                    },
                )
            finally:
                db.close()

            while True:
                await asyncio.sleep(1.0)

                db = SessionLocal()
                try:
                    state_resp = DraftService.get_draft_state_response(db, code)

                    if state_resp.is_finished:
                        logger.info("Room %s draft is finished. Stopping timer loop.", code)
                        break

                    remaining = state_resp.remaining_seconds

                    # Broadcast timer_tick
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "timer_tick",
                            "room_code": code,
                            "remaining": remaining,
                            "current_picker_id": state_resp.current_picker_id,
                        },
                    )

                    if remaining <= 0:
                        # Timer expired -> execute auto-pick
                        logger.info("Timer expired for room %s. Executing auto-pick.", code)
                        pick, is_draft_finished = DraftService.execute_auto_pick(db, code)

                        if pick:
                            pick_dict = {
                                "id": pick.id,
                                "round_number": pick.round_number,
                                "user_id": pick.user_id,
                                "player_id": pick.player_id,
                                "player_name": pick.player_name,
                                "batting_position": pick.batting_position,
                                "selected_country": pick.selected_country,
                                "selected_decade": pick.selected_decade,
                            }
                            # Broadcast auto-selection events
                            await ws_manager.broadcast_to_room(
                                code,
                                {
                                    "type": "player_auto_selected",
                                    "room_code": code,
                                    "user_id": pick.user_id,
                                    "pick": pick_dict,
                                },
                            )
                            await ws_manager.broadcast_to_room(
                                code,
                                {
                                    "type": "player_locked",
                                    "room_code": code,
                                    "user_id": pick.user_id,
                                    "pick": pick_dict,
                                },
                            )
                        else:
                            logger.error(
                                "Auto-pick returned None for room %s. Draft cannot legally complete.", code
                            )
                            await ws_manager.broadcast_to_room(
                                code,
                                {
                                    "type": "draft_cancelled",
                                    "room_code": code,
                                    "message": "Draft cancelled: Unable to complete legal XIs with remaining player pool.",
                                },
                            )
                            fresh_state = DraftService.get_draft_state_response(db, code)
                            fresh_payload = fresh_state.model_dump(mode="json")
                            await ws_manager.broadcast_to_room(
                                code,
                                {
                                    "type": "draft_state_updated",
                                    "room_code": code,
                                    "draft_state": fresh_payload,
                                },
                            )
                            break

                        # Fetch fresh state after auto-pick
                        fresh_state = DraftService.get_draft_state_response(db, code)
                        fresh_payload = fresh_state.model_dump(mode="json")

                        if is_draft_finished:
                            try:
                                from app.toss.toss_service import TossService
                                toss_state_resp = TossService.initialize_or_get_toss(db, code)
                                toss_payload = toss_state_resp.model_dump(mode="json")
                            except Exception as toss_init_err:
                                logger.warning("Error initializing toss in auto pick: %s", toss_init_err)
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
                            break
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

                            await ws_manager.broadcast_to_room(
                                code,
                                {
                                    "type": "timer_started",
                                    "room_code": code,
                                    "remaining": fresh_state.remaining_seconds,
                                    "current_picker_id": fresh_state.current_picker_id,
                                },
                            )
                            await ws_manager.broadcast_to_room(
                                code,
                                {
                                    "type": "draft_state_updated",
                                    "room_code": code,
                                    "draft_state": fresh_payload,
                                },
                            )
                finally:
                    db.close()

        except asyncio.CancelledError:
            logger.info("Timer loop cancelled for room %s", code)
        except Exception as e:
            logger.exception("Unexpected error in timer loop for room %s: %s", code, e)


# Singleton manager
draft_manager = DraftManager()

