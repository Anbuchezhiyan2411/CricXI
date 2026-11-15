"""
WebSocket Connection and Room Manager for CricXI (Phase 6.2).
Handles active WebSocket connections, multi-client room broadcasting,
client heartbeat tracking, 30-second disconnect countdowns,
and slot reservation for seamless session recovery.
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections grouped by room and player."""

    def __init__(self) -> None:
        # room_code -> {player_id: WebSocket}
        self.active_rooms: Dict[str, Dict[str, WebSocket]] = {}
        # player_id -> WebSocket
        self.player_connections: Dict[str, WebSocket] = {}
        # room_code -> {player_id: float timestamp}
        self.last_heartbeat: Dict[str, Dict[str, float]] = {}
        # room_code -> {player_id: {"disconnected_at": float, "username": str}}
        self.disconnected_players: Dict[str, Dict[str, Dict[str, Any]]] = {}
        # room_code -> {player_id: asyncio.Task}
        self.disconnect_tasks: Dict[str, Dict[str, asyncio.Task]] = {}

    async def connect(self, websocket: WebSocket, room_code: str, player_id: str) -> None:
        """Accepts and registers a new WebSocket connection."""
        await websocket.accept()
        room_code = room_code.strip().upper()

        if room_code not in self.active_rooms:
            self.active_rooms[room_code] = {}

        # If this player already has an existing connection, close it gracefully
        old_ws = self.player_connections.get(player_id)
        if old_ws and old_ws != websocket:
            try:
                logger.info("Closing previous connection for player %s in room %s", player_id, room_code)
                await old_ws.close(code=1000)
            except Exception:
                pass

        self.active_rooms[room_code][player_id] = websocket
        self.player_connections[player_id] = websocket
        self.record_heartbeat(room_code, player_id)

        logger.info(
            "WebSocket connected: player %s in room %s (total active in room: %d)",
            player_id,
            room_code,
            len(self.active_rooms[room_code]),
        )

    def record_heartbeat(self, room_code: str, player_id: str) -> None:
        """Records the timestamp of the latest heartbeat or message from a player."""
        room_code = room_code.strip().upper()
        if room_code not in self.last_heartbeat:
            self.last_heartbeat[room_code] = {}
        self.last_heartbeat[room_code][player_id] = time.time()

    def get_last_heartbeat(self, room_code: str, player_id: str) -> Optional[float]:
        """Returns the timestamp of the last heartbeat received from a player."""
        room_code = room_code.strip().upper()
        return self.last_heartbeat.get(room_code, {}).get(player_id)

    def disconnect(self, room_code: str, player_id: str, websocket: Optional[WebSocket] = None) -> None:
        """Removes a registered WebSocket connection only if it matches current."""
        room_code = room_code.strip().upper()

        if room_code in self.active_rooms:
            if player_id in self.active_rooms[room_code]:
                if websocket is None or self.active_rooms[room_code][player_id] == websocket:
                    del self.active_rooms[room_code][player_id]

            if not self.active_rooms[room_code]:
                del self.active_rooms[room_code]

        if player_id in self.player_connections:
            if websocket is None or self.player_connections[player_id] == websocket:
                del self.player_connections[player_id]

        logger.info("WebSocket connection removed: player %s from room %s", player_id, room_code)

    def is_player_disconnected(self, room_code: str, player_id: str) -> bool:
        """Checks if a player is currently in the 30-second disconnect window."""
        room_code = room_code.strip().upper()
        return player_id in self.disconnected_players.get(room_code, {})

    def is_slot_reserved(self, room_code: str, candidate_player_id: str) -> bool:
        """
        Returns True if the room has a disconnected player whose slot is reserved
        for reconnection and does not belong to the candidate_player_id.
        """
        room_code = room_code.strip().upper()
        disconnected = self.disconnected_players.get(room_code, {})
        for pid in disconnected:
            if pid != candidate_player_id:
                return True
        return False

    def start_disconnect_timer(
        self,
        room_code: str,
        player_id: str,
        username: str,
        on_timeout_callback: Callable[[str, str], Coroutine[Any, Any, None]],
        timeout_seconds: int = 30,
    ) -> asyncio.Task:
        """
        Registers a player as disconnected, freezes game state, and starts an authoritative
        countdown ticker broadcasting every second down to 1.
        """
        room_code = room_code.strip().upper()
        if room_code not in self.disconnected_players:
            self.disconnected_players[room_code] = {}
        if room_code not in self.disconnect_tasks:
            self.disconnect_tasks[room_code] = {}

        # Cancel any preexisting timer for this player
        existing_task = self.disconnect_tasks[room_code].pop(player_id, None)
        if existing_task and not existing_task.done():
            existing_task.cancel()

        self.disconnected_players[room_code][player_id] = {
            "disconnected_at": time.time(),
            "username": username,
        }

        async def _countdown_loop():
            try:
                for remaining in range(timeout_seconds, 0, -1):
                    await asyncio.sleep(1.0)
                    # Broadcast server-authoritative countdown tick
                    await self.broadcast_to_room(
                        room_code,
                        {
                            "type": "disconnect_countdown_tick",
                            "room_code": room_code,
                            "user_id": player_id,
                            "username": username,
                            "seconds_remaining": remaining - 1,
                        },
                    )

                logger.info("Disconnect timeout expired for player %s in room %s", player_id, room_code)
                self.disconnected_players.get(room_code, {}).pop(player_id, None)
                self.disconnect_tasks.get(room_code, {}).pop(player_id, None)
                await on_timeout_callback(room_code, player_id)
            except asyncio.CancelledError:
                logger.info("Disconnect countdown cancelled for player %s in room %s (reconnected)", player_id, room_code)
            except Exception as e:
                logger.exception("Error in disconnect countdown loop for %s: %s", player_id, e)

        task = asyncio.create_task(_countdown_loop())
        self.disconnect_tasks[room_code][player_id] = task
        return task

    def cancel_disconnect_timer(self, room_code: str, player_id: str) -> bool:
        """
        Cancels any active disconnect countdown for the player upon reconnection.
        Returns True if the player was previously in a disconnected state.
        """
        room_code = room_code.strip().upper()
        was_disconnected = False

        if room_code in self.disconnected_players:
            if player_id in self.disconnected_players[room_code]:
                del self.disconnected_players[room_code][player_id]
                was_disconnected = True

        if room_code in self.disconnect_tasks:
            task = self.disconnect_tasks[room_code].pop(player_id, None)
            if task and not task.done():
                task.cancel()
                was_disconnected = True

        return was_disconnected

    async def send_personal_message(self, player_id: str, message: Dict[str, Any]) -> None:
        """Sends a JSON message to a specific connected player."""
        websocket = self.player_connections.get(player_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning("Failed to send message to player %s: %s", player_id, e)

    async def broadcast_to_room(
        self,
        room_code: str,
        message: Dict[str, Any],
        exclude_player: Optional[str] = None,
    ) -> None:
        """Broadcasts a JSON message to all connected players in a room."""
        room_code = room_code.strip().upper()
        room_connections = self.active_rooms.get(room_code, {})
        payload = json.dumps(message)
        dead_connections: List[str] = []

        for pid, ws in list(room_connections.items()):
            if exclude_player and pid == exclude_player:
                continue
            try:
                await ws.send_text(payload)
            except Exception as e:
                logger.warning("Failed to broadcast to player %s in room %s: %s", pid, room_code, e)
                dead_connections.append(pid)

        # Cleanup dropped connections
        for dead_pid in dead_connections:
            self.disconnect(room_code, dead_pid)

    def get_room_player_count(self, room_code: str) -> int:
        """Returns the number of connected players in a room."""
        room_code = room_code.strip().upper()
        return len(self.active_rooms.get(room_code, {}))

    def get_connected_player_ids(self, room_code: str) -> Set[str]:
        """Returns the set of currently connected player IDs in a room."""
        room_code = room_code.strip().upper()
        return set(self.active_rooms.get(room_code, {}).keys())

    def is_player_connected(self, player_id: str) -> bool:
        """Checks if a player has an active WebSocket connection."""
        return player_id in self.player_connections

    def destroy_room(self, room_code: str) -> None:
        """Removes all connection tracking and pending timers for a given room."""
        room_code = room_code.strip().upper()
        if room_code in self.disconnect_tasks:
            for task in self.disconnect_tasks[room_code].values():
                if task and not task.done():
                    task.cancel()
            del self.disconnect_tasks[room_code]

        if room_code in self.disconnected_players:
            del self.disconnected_players[room_code]

        if room_code in self.last_heartbeat:
            del self.last_heartbeat[room_code]

        if room_code in self.active_rooms:
            for pid in list(self.active_rooms[room_code].keys()):
                if pid in self.player_connections:
                    del self.player_connections[pid]
            del self.active_rooms[room_code]


# Singleton instance
ws_manager = ConnectionManager()
