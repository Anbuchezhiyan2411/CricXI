"""
Room Service for CricXI Multiplayer Matchmaking (Phase 2).
Handles business rules, state persistence, room lifecycle, and validation.
"""

from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Optional, Tuple
import uuid
from sqlalchemy.orm import Session

from app.models.room import Room, RoomPlayer
from app.schemas.room import PlayerInRoom, RoomResponse, RoomValidateResponse
from app.utils.helpers import generate_room_code
from app.websocket.connection_manager import ws_manager

logger = logging.getLogger(__name__)

INACTIVE_ROOM_TIMEOUT_MINUTES = 120  # 2 hours

# Cache for rematch ready synchronization barrier: room_code -> set of user_ids ready for rematch
_rematch_ready: dict[str, set[str]] = {}


def build_room_response(room: Room, current_user_id: Optional[str] = None) -> RoomResponse:
    """Constructs a RoomResponse schema enriched with live connection status."""
    connected_ids = ws_manager.get_connected_player_ids(room.room_code)
    players_data = []

    for p in room.players:
        players_data.append(
            PlayerInRoom(
                user_id=p.user_id,
                username=p.username,
                is_host=p.is_host,
                is_ready=p.is_ready,
                is_connected=(p.user_id in connected_ids),
                joined_at=p.joined_at,
            )
        )

    return RoomResponse(
        room_code=room.room_code,
        host_id=room.host_id,
        status=room.status,
        current_round=room.current_round,
        players=players_data,
        created_at=room.created_at,
        updated_at=room.updated_at,
        is_full=(len(players_data) >= 2),
        current_user_id=current_user_id,
    )


def cleanup_inactive_rooms(db: Session) -> int:
    """Removes rooms that have been inactive longer than the timeout period."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=INACTIVE_ROOM_TIMEOUT_MINUTES)
    stale_rooms = db.query(Room).filter(Room.updated_at < cutoff).all()
    count = len(stale_rooms)

    for r in stale_rooms:
        ws_manager.destroy_room(r.room_code)
        db.delete(r)

    if count > 0:
        db.commit()
        logger.info("Purged %d inactive rooms past %d min timeout.", count, INACTIVE_ROOM_TIMEOUT_MINUTES)

    return count


class RoomService:
    """Encapsulates all room management business rules."""

    @staticmethod
    def create_room(db: Session, username: str) -> Tuple[Room, str]:
        """
        Creates a new room with a collision-free 6-character code and registers the host.
        Returns (Room, host_user_id).
        """
        cleanup_inactive_rooms(db)
        cleaned_username = username.strip()

        # Generate guaranteed unique 6-character room code
        room_code = generate_room_code(6)
        while db.query(Room).filter(Room.room_code == room_code).first() is not None:
            room_code = generate_room_code(6)

        host_id = str(uuid.uuid4())
        room = Room(
            room_code=room_code,
            host_id=host_id,
            status="WAITING",
            current_round=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(room)
        db.flush()

        host_player = RoomPlayer(
            room_id=room.id,
            user_id=host_id,
            username=cleaned_username,
            is_host=True,
            is_ready=False,
            joined_at=datetime.now(timezone.utc),
        )
        db.add(host_player)
        db.commit()
        db.refresh(room)

        logger.info("Room %s created by host %s (%s)", room_code, cleaned_username, host_id)
        return room, host_id

    @staticmethod
    def join_room(db: Session, room_code: str, username: str, user_id: Optional[str] = None) -> Tuple[Room, str]:
        """
        Validates room existence, capacity, and name uniqueness, then registers the guest.
        If an existing player is rejoining with their verified user_id, their session is resumed.
        """
        code = room_code.strip().upper()
        cleaned_username = username.strip()

        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        # 1. Check for reconnect by existing user_id
        if user_id:
            for existing in room.players:
                if existing.user_id == user_id:
                    room.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(room)
                    logger.info("Player %s (%s) reconnected by user_id to room %s", existing.username, user_id, code)
                    return room, existing.user_id

        # 2. Check for reconnect by matching username of a disconnected/reserved player
        for existing in room.players:
            if existing.username.strip().lower() == cleaned_username.lower():
                is_disconnected = ws_manager.is_player_disconnected(code, existing.user_id)
                if is_disconnected:
                    # Original player is reclaiming their reserved slot by username!
                    room.updated_at = datetime.now(timezone.utc)
                    db.commit()
                    db.refresh(room)
                    logger.info("Player %s (%s) reclaimed reserved slot by username in room %s", existing.username, existing.user_id, code)
                    return room, existing.user_id
                else:
                    # That player is currently connected and active! Reject duplicate name!
                    raise ValueError("A player with this name is currently active in this room. Please choose a different name.")

        # 3. Third-party new user: check if room is already full or slots reserved
        has_disconnected_reserved = any(
            ws_manager.is_player_disconnected(code, p.user_id) for p in room.players
        )
        if len(room.players) >= 2:
            if has_disconnected_reserved or room.status in ("DRAFT", "DRAFTING", "TOSS", "IN_PROGRESS"):
                raise ValueError("Player slot reserved. Waiting for original player to reconnect.")
            raise ValueError("Room is already full (maximum 2 players).")

        if room.status != "WAITING":
            if has_disconnected_reserved:
                raise ValueError("Player slot reserved. Waiting for original player to reconnect.")
            raise ValueError("Room is no longer accepting new players.")

        guest_id = user_id or str(uuid.uuid4())
        guest_player = RoomPlayer(
            room_id=room.id,
            user_id=guest_id,
            username=cleaned_username,
            is_host=False,
            is_ready=False,
            joined_at=datetime.now(timezone.utc),
        )
        db.add(guest_player)
        room.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(room)

        logger.info("Guest %s (%s) joined room %s", cleaned_username, guest_id, code)
        return room, guest_id

    @staticmethod
    def leave_room(db: Session, room_code: str, user_id: str) -> Optional[Room]:
        """
        Removes a player from a room.
        If all players have left, the room is deleted.
        Returns remaining Room, or None if room was deleted.
        """
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            return None

        # Check remaining players count
        current_players = list(room.players)
        remaining_players = [p for p in current_players if p.user_id != user_id]

        if len(remaining_players) == 0:
            # Everyone has left - destroy room immediately
            logger.info("All players left room %s. Destroying room.", code)
            ws_manager.destroy_room(code)
            db.delete(room)
            db.commit()
            return None

        # Remove leaving player
        player = next((p for p in current_players if p.user_id == user_id), None)
        if player:
            db.delete(player)

        # If host left and guest remains, promote guest to host
        if room.host_id == user_id and len(remaining_players) > 0:
            remaining_players[0].is_host = True
            room.host_id = remaining_players[0].user_id

        room.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(room)
        return room

    @staticmethod
    def start_game(db: Session, room_code: str, user_id: str) -> Room:
        """
        Validates host permissions, full squad, and readiness, then marks game as started.
        """
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        if room.host_id != user_id:
            raise PermissionError("Only the room Host can start the game.")

        if len(room.players) < 2:
            raise ValueError("Cannot start game: waiting for opponent to join.")

        not_ready_players = [p.username for p in room.players if not p.is_ready]
        if not_ready_players:
            raise ValueError(
                f"Cannot start game: {', '.join(not_ready_players)} is not ready."
            )

        # Clear any previous match/draft data if restarting a room
        RoomService.reset_room_for_new_match(db, code)

        room.status = "DRAFTING"
        room.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(room)

        logger.info("Game started in room %s by host %s", code, user_id)
        return room

    @staticmethod
    def validate_room(
        db: Session,
        room_code: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> RoomValidateResponse:
        """Validates if a room exists, is joinable, or has a reserved slot for reconnect."""
        code = room_code.strip().upper()
        cleanup_inactive_rooms(db)
        room = db.query(Room).filter(Room.room_code == code).first()

        if not room:
            return RoomValidateResponse(
                valid=False,
                exists=False,
                is_full=False,
                player_count=0,
                status="NOT_FOUND",
                message=f"Room '{code}' does not exist.",
            )

        if room.status in ("COMPLETED", "ABANDONED"):
            return RoomValidateResponse(
                valid=False,
                exists=True,
                is_full=True,
                player_count=len(room.players),
                status=room.status,
                message="This match has already ended.",
            )

        count = len(room.players)
        has_disconnected_reserved = any(
            ws_manager.is_player_disconnected(code, p.user_id)
            for p in room.players
        )

        # 1. Check if reconnecting by existing user_id
        if user_id:
            for p in room.players:
                if p.user_id == user_id:
                    return RoomValidateResponse(
                        valid=True,
                        exists=True,
                        is_full=False,
                        player_count=count,
                        status=room.status,
                        message="Reserved slot found. Ready to reconnect.",
                    )

        # 2. Check if reconnecting by username matching a disconnected player
        if username:
            cleaned_name = username.strip().lower()
            for p in room.players:
                if p.username.strip().lower() == cleaned_name:
                    is_disc = ws_manager.is_player_disconnected(code, p.user_id)
                    if is_disc:
                        return RoomValidateResponse(
                            valid=True,
                            exists=True,
                            is_full=False,
                            player_count=count,
                            status=room.status,
                            message=f"Welcome back, {p.username}! Ready to reclaim your slot.",
                        )
                    else:
                        return RoomValidateResponse(
                            valid=False,
                            exists=True,
                            is_full=False,
                            player_count=count,
                            status=room.status,
                            message="A player with this name is currently active in this room.",
                        )

        # 3. If room has 2 players, allow validation if a slot is reserved for reconnect
        if count >= 2:
            if has_disconnected_reserved:
                return RoomValidateResponse(
                    valid=True,
                    exists=True,
                    is_full=False,
                    player_count=count,
                    status=room.status,
                    message="Reserved slot available for reconnecting player.",
                )
            return RoomValidateResponse(
                valid=False,
                exists=True,
                is_full=True,
                player_count=count,
                status=room.status,
                message="Room is already full (maximum 2 players).",
            )

        if room.status != "WAITING":
            if has_disconnected_reserved:
                return RoomValidateResponse(
                    valid=True,
                    exists=True,
                    is_full=False,
                    player_count=count,
                    status=room.status,
                    message="Reserved slot available for reconnecting player.",
                )
            return RoomValidateResponse(
                valid=False,
                exists=True,
                is_full=False,
                player_count=count,
                status=room.status,
                message=f"Room is already {room.status.lower()}.",
            )

        return RoomValidateResponse(
            valid=True,
            exists=True,
            is_full=False,
            player_count=count,
            status=room.status,
            message="Room is ready to join.",
        )

    @staticmethod
    def toggle_player_ready(db: Session, room_code: str, user_id: str, is_ready: Optional[bool] = None) -> Room:
        """Toggles or sets player ready status."""
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        player = (
            db.query(RoomPlayer)
            .filter(RoomPlayer.room_id == room.id, RoomPlayer.user_id == user_id)
            .first()
        )
        if not player:
            raise ValueError("Player is not in this room.")

        if is_ready is None:
            player.is_ready = not player.is_ready
        else:
            player.is_ready = is_ready

        room.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(room)
        return room

    @staticmethod
    def reset_room_for_new_match(db: Session, room_code: str) -> Room:
        """Cleans up previous match, innings, ball events, toss, draft state and picks for a room so a new match can start freshly."""
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        from app.models.match import Match, MatchInnings, BallEvent, InningsBatterScore, InningsBowlerScore
        from app.models.toss import TossState
        from app.models.draft import DraftState, DraftPick

        matches = db.query(Match).filter(Match.room_id == room.id).all()
        for m in matches:
            innings = db.query(MatchInnings).filter(MatchInnings.match_id == m.id).all()
            for inn in innings:
                db.query(BallEvent).filter(BallEvent.innings_id == inn.id).delete()
                db.query(InningsBatterScore).filter(InningsBatterScore.innings_id == inn.id).delete()
                db.query(InningsBowlerScore).filter(InningsBowlerScore.innings_id == inn.id).delete()
            db.query(MatchInnings).filter(MatchInnings.match_id == m.id).delete()
        db.query(Match).filter(Match.room_id == room.id).delete()
        db.query(TossState).filter(TossState.room_id == room.id).delete()
        db.query(DraftPick).filter(DraftPick.room_id == room.id).delete()
        db.query(DraftState).filter(DraftState.room_id == room.id).delete()

        room.current_round = 1
        room.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(room)
        logger.info("Room %s reset for new match with full state wipe.", code)
        return room

    @staticmethod
    def request_play_again(
        db: Session,
        room_code: str,
        user_id: str,
    ) -> Tuple[Room, bool, list[str]]:
        """
        Multiplayer barrier for 'Play Another Match':
        - Tracks readiness per room.
        - When only 1 player is ready: records readiness, does NOT reset room.
        - When BOTH players in the room are ready: resets the room (reusing SAME room code),
          wipes old match/draft/toss data, initializes brand new draft, and marks barrier as met.
        Returns (room, is_barrier_met, ready_user_ids).
        """
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        matching_player = next((p for p in room.players if p.user_id == user_id), None)
        if not matching_player:
            raise PermissionError("Only players in this room can request a rematch.")

        if code not in _rematch_ready:
            _rematch_ready[code] = set()

        _rematch_ready[code].add(user_id)
        matching_player.is_ready = True
        db.commit()

        total_players = len(room.players)
        ready_count = len(_rematch_ready[code])

        if total_players >= 2 and ready_count >= total_players:
            # BOTH PLAYERS READY -> RESET ROOM FOR REMATCH
            _rematch_ready.pop(code, None)

            # Stop simulation and draft timers
            from app.match.match_manager import match_manager
            from app.draft.draft_manager import draft_manager
            from app.draft.draft_service import DraftService

            match_manager.stop_match_simulation(code)
            draft_manager.stop_room_timer(code)

            # Wipe old match, toss, draft state
            RoomService.reset_room_for_new_match(db, code)

            # Mark both players ready for draft
            for p in room.players:
                p.is_ready = True

            # Generate fresh draft with new country/decade & player pool (reusing SAME room code)
            draft_state = DraftService.initialize_draft(db, code, force_fresh=True)
            draft_manager.start_room_timer(code)

            room.status = "DRAFTING"
            room.current_round = 1
            room.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(room)

            logger.info("Rematch barrier met for room %s: room wiped and new draft initialized.", code)
            return room, True, [p.user_id for p in room.players]

        # Barrier NOT yet met: waiting for other player(s)
        logger.info(
            "Rematch requested for room %s by %s (%d/%d players ready).",
            code,
            matching_player.username,
            ready_count,
            total_players,
        )
        return room, False, list(_rematch_ready[code])

    @staticmethod
    def play_again(db: Session, old_room_code: str, user_id: str) -> Tuple[Room, Room, Any]:
        """Backward-compatible adapter that triggers request_play_again."""
        room, is_barrier_met, ready_ids = RoomService.request_play_again(db, old_room_code, user_id)
        from app.models.draft import DraftState
        draft_state = db.query(DraftState).filter(DraftState.room_id == room.id).first()
        return room, room, draft_state
