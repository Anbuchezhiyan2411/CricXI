"""
Match Manager for CricXI Live T20 Multiplayer Simulation.
Coordinates background delivery loops, play/pause controls, speed adjustments,
and real-time WebSocket state broadcasts to all room members.
"""

import asyncio
import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.match.match_service import MatchService
from app.websocket.connection_manager import ws_manager

logger = logging.getLogger(__name__)


class MatchManager:
    """Manages automatic background delivery simulation loops per room."""

    def __init__(self) -> None:
        # room_code -> asyncio.Task
        self._active_simulations: Dict[str, asyncio.Task] = {}
        # room_code -> asyncio.Lock
        self._room_locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, room_code: str) -> asyncio.Lock:
        code = room_code.strip().upper()
        if code not in self._room_locks:
            self._room_locks[code] = asyncio.Lock()
        return self._room_locks[code]

    def is_simulation_running(self, room_code: str) -> bool:
        """Returns True if a background simulation worker is running."""
        code = room_code.strip().upper()
        task = self._active_simulations.get(code)
        return task is not None and not task.done()

    def start_match_simulation(self, room_code: str) -> None:
        """Starts or resumes the automatic delivery loop for the room."""
        code = room_code.strip().upper()
        if self.is_simulation_running(code):
            logger.info("Simulation loop is already running for room %s", code)
            return

        self.stop_match_simulation(code)
        self._active_simulations[code] = asyncio.create_task(self._simulation_loop(code))
        logger.info("Background simulation task launched for room %s", code)

    def stop_match_simulation(self, room_code: str) -> None:
        """Stops the automatic delivery loop for the room."""
        code = room_code.strip().upper()
        task = self._active_simulations.pop(code, None)
        if task and not task.done():
            task.cancel()
            logger.info("Simulation task stopped for room %s", code)

    async def _simulation_loop(self, room_code: str) -> None:
        """Authoritative background worker loop simulating deliveries at set speeds."""
        code = room_code.strip().upper()
        lock = self._get_lock(code)

        try:
            while True:
                # Calculate sleep duration based on simulation_speed
                db: Session = SessionLocal()
                try:
                    state = MatchService.get_live_match_state(db, code)
                finally:
                    db.close()

                if state.status in ("COMPLETED", "TIED"):
                    logger.info("Match in room %s is completed. Ending simulation loop.", code)
                    await ws_manager.broadcast_to_room(
                        code,
                        {
                            "type": "match_completed",
                            "room_code": code,
                            "match_state": state.model_dump(mode="json"),
                        },
                    )
                    break

                if state.is_paused:
                    # While paused, check every 0.5 seconds
                    await asyncio.sleep(0.5)
                    continue

                speed = state.simulation_speed or 1.0
                delay = 2.0 / max(0.2, speed)
                await asyncio.sleep(delay)

                # Acquire room lock to prevent race conditions
                async with lock:
                    db = SessionLocal()
                    try:
                        delivery_res, updated_state = MatchService.step_delivery(db, code)

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

                        # Broadcast ball result
                        await ws_manager.broadcast_to_room(
                            code,
                            {
                                "type": "ball_result",
                                "room_code": code,
                                "delivery": deliv_dict,
                                "match_state": payload,
                            },
                        )

                        # Broadcast full score update
                        await ws_manager.broadcast_to_room(
                            code,
                            {
                                "type": "match_state_updated",
                                "room_code": code,
                                "match_state": payload,
                            },
                        )

                        # If innings or match just completed, broadcast specific milestones
                        if updated_state.status in ("COMPLETED", "TIED"):
                            await ws_manager.broadcast_to_room(
                                code,
                                {
                                    "type": "match_completed",
                                    "room_code": code,
                                    "match_state": payload,
                                },
                            )
                            break

                    except Exception as err:
                        logger.exception("Error executing delivery step in room %s: %s", code, err)
                        await asyncio.sleep(2.0)
                    finally:
                        db.close()

        except asyncio.CancelledError:
            logger.info("Simulation loop cancelled for room %s", code)
        except Exception as e:
            logger.exception("Unexpected error in simulation loop for room %s: %s", code, e)
        finally:
            self._active_simulations.pop(code, None)


# Singleton manager instance
match_manager = MatchManager()

