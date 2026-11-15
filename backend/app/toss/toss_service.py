"""
Toss Service for CricXI (Pre-Match Toss Ceremony).
Coordinates the complete traditional cricket toss workflow:
1. Verify 11-player draft completion for both teams.
2. Select one toss caller using secure random generation (secrets.choice).
3. Caller calls HEADS or TAILS.
4. Backend randomly generates coin result (HEADS or TAILS).
5. Compare call with coin result to determine winner.
6. Winner chooses to BAT or BOWL first.
7. Record toss ceremony in database and update Match/Room status to LIVE.
"""

import logging
import secrets
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.services.dataset_loader import dataset_service
from app.models.draft import DraftPick, DraftState
from app.models.match import Match
from app.models.room import Room, RoomPlayer
from app.models.toss import TossState
from app.schemas.toss import TeamInfo, TossStateResponse

logger = logging.getLogger(__name__)


class TossService:
    """Service handling all business logic for the CricXI Toss Engine."""

    @classmethod
    def verify_draft_completed(cls, db: Session, room: Room) -> Tuple[bool, str]:
        """
        Verifies that both the host and guest have completed drafting exactly
        11 players, filled batting order 1-11, and that room is ready for toss.
        """
        if len(room.players) < 2:
            return False, "Two players are required before the toss can begin."

        host_player = next((p for p in room.players if p.is_host), None)
        guest_player = next((p for p in room.players if not p.is_host), None)

        if not host_player or not guest_player:
            return False, "Both Host and Guest must be present in the room."

        # Fetch picks for both players
        host_picks = (
            db.query(DraftPick)
            .filter(DraftPick.room_id == room.id, DraftPick.user_id == host_player.user_id)
            .all()
        )
        guest_picks = (
            db.query(DraftPick)
            .filter(DraftPick.room_id == room.id, DraftPick.user_id == guest_player.user_id)
            .all()
        )

        if len(host_picks) < 11:
            return False, f"Host has drafted {len(host_picks)}/11 players. Draft in progress."

        if len(guest_picks) < 11:
            return False, f"Guest has drafted {len(guest_picks)}/11 players. Draft in progress."

        # Verify all positions 1 to 11 are filled
        host_positions = {p.batting_position for p in host_picks}
        guest_positions = {p.batting_position for p in guest_picks}

        required_positions = set(range(1, 12))
        if host_positions != required_positions:
            return False, "Host lineup is missing batting positions."

        if guest_positions != required_positions:
            return False, "Guest lineup is missing batting positions."

        return True, "Draft successfully completed."

    @classmethod
    def _get_team_info(cls, db: Session, room: Room, player: RoomPlayer) -> TeamInfo:
        """Determines captain name, team name, and lineup details for a player."""
        if not dataset_service.is_loaded:
            dataset_service.load()

        picks = (
            db.query(DraftPick)
            .filter(DraftPick.room_id == room.id, DraftPick.user_id == player.user_id)
            .all()
        )

        captain_name = player.username
        highest_ovr_player = None
        highest_ovr = -1.0

        for pick in picks:
            p_data = dataset_service.get_player_by_id(pick.player_id) or {}
            ovr = float(p_data.get("overall_rating", 0.0))
            if ovr > highest_ovr:
                highest_ovr = ovr
                highest_ovr_player = p_data.get("player_name")

            if p_data.get("is_captain"):
                captain_name = p_data.get("player_name", player.username)
                break
        else:
            if highest_ovr_player:
                captain_name = highest_ovr_player

        team_name = f"{captain_name}'s XI"

        return TeamInfo(
            user_id=player.user_id,
            username=player.username,
            is_host=player.is_host,
            captain_name=captain_name,
            team_name=team_name,
            player_count=len(picks),
        )

    @classmethod
    def initialize_or_get_toss(
        cls,
        db: Session,
        room_code: str,
        current_user_id: Optional[str] = None,
    ) -> TossStateResponse:
        """
        Initializes the Toss session if not already created, or returns the
        persisted toss state. Selects caller randomly using secrets.choice.
        """
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        # Verify draft completion
        is_ready, reason = cls.verify_draft_completed(db, room)
        if not is_ready:
            # If draft is incomplete, return state with draft_completed=False
            host_player = next((p for p in room.players if p.is_host), None)
            guest_player = next((p for p in room.players if not p.is_host), None)
            host_info = cls._get_team_info(db, room, host_player) if host_player else TeamInfo(user_id="", username="Host", is_host=True, captain_name="Host", team_name="Host XI")
            guest_info = cls._get_team_info(db, room, guest_player) if guest_player else TeamInfo(user_id="", username="Guest", is_host=False, captain_name="Guest", team_name="Guest XI")

            return TossStateResponse(
                room_code=code,
                step="CALLING",
                caller_id="",
                caller_name="",
                host_team=host_info,
                guest_team=guest_info,
                draft_completed=False,
                message=reason,
            )

        # Check existing TossState
        toss_state = db.query(TossState).filter(TossState.room_id == room.id).first()

        if not toss_state:
            # Randomly select toss caller using secrets.choice
            host_player = next(p for p in room.players if p.is_host)
            guest_player = next(p for p in room.players if not p.is_host)
            selected_caller = secrets.choice([host_player, guest_player])

            # Ensure Match record exists
            match = db.query(Match).filter(Match.room_id == room.id).first()
            if not match:
                match = Match(
                    room_id=room.id,
                    team1_user_id=host_player.user_id,
                    team2_user_id=guest_player.user_id,
                    status="PENDING",
                )
                db.add(match)
                db.flush()

            toss_state = TossState(
                room_id=room.id,
                match_id=match.id,
                caller_id=selected_caller.user_id,
                caller_name=selected_caller.username,
                step="CALLING",
            )
            db.add(toss_state)

            if room.status != "TOSS":
                room.status = "TOSS"

            db.commit()
            db.refresh(toss_state)
            logger.info("Toss initialized for room %s: Caller is %s (%s)", code, toss_state.caller_name, toss_state.caller_id)

        return cls.get_toss_state_response(db, code, current_user_id)

    @classmethod
    def make_call(
        cls,
        db: Session,
        room_code: str,
        user_id: str,
        choice: str,
    ) -> TossStateResponse:
        """
        Processes the caller's choice (HEADS or TAILS), randomly generates the
        coin flip outcome on the backend, and determines the toss winner.
        """
        code = room_code.strip().upper()
        clean_choice = choice.strip().upper()
        if clean_choice not in ("HEADS", "TAILS"):
            raise ValueError("Invalid toss call. Must be 'HEADS' or 'TAILS'.")

        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        toss_state = db.query(TossState).filter(TossState.room_id == room.id).first()
        if not toss_state:
            raise ValueError(f"Toss has not been initialized for room '{code}'.")

        if toss_state.caller_choice is not None or toss_state.coin_result is not None:
            raise ValueError("The toss has already been called and flipped.")

        # Identity validation: only designated caller can make the call
        if user_id.strip() != toss_state.caller_id:
            raise PermissionError(f"Only the designated toss caller ({toss_state.caller_name}) can call Heads or Tails.")

        # Save caller choice
        toss_state.caller_choice = clean_choice

        # Backend securely flips the coin
        coin_result = secrets.choice(["HEADS", "TAILS"])
        toss_state.coin_result = coin_result

        # Determine winner
        host_player = next(p for p in room.players if p.is_host)
        guest_player = next(p for p in room.players if not p.is_host)

        if clean_choice == coin_result:
            # Caller wins!
            toss_state.winner_id = toss_state.caller_id
            toss_state.winner_name = toss_state.caller_name
        else:
            # Opponent wins!
            opponent = guest_player if toss_state.caller_id == host_player.user_id else host_player
            toss_state.winner_id = opponent.user_id
            toss_state.winner_name = opponent.username

        toss_state.step = "DECIDING"
        db.commit()
        db.refresh(toss_state)

        logger.info(
            "Toss flipped for room %s: Caller %s called %s, Coin landed on %s -> Winner is %s",
            code,
            toss_state.caller_name,
            clean_choice,
            coin_result,
            toss_state.winner_name,
        )

        return cls.get_toss_state_response(db, code, user_id)

    @classmethod
    def make_decision(
        cls,
        db: Session,
        room_code: str,
        user_id: str,
        decision: str,
    ) -> TossStateResponse:
        """
        Processes the toss winner's decision (BAT or BOWL first), completes the
        toss ceremony, and transitions the room and match to LIVE status.
        """
        code = room_code.strip().upper()
        clean_decision = decision.strip().upper()
        if clean_decision not in ("BAT", "BOWL"):
            raise ValueError("Invalid toss decision. Must be 'BAT' or 'BOWL'.")

        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        toss_state = db.query(TossState).filter(TossState.room_id == room.id).first()
        if not toss_state:
            raise ValueError(f"Toss has not been initialized for room '{code}'.")

        if toss_state.coin_result is None or toss_state.winner_id is None:
            raise ValueError("The coin toss must be flipped before making a pitch decision.")

        if toss_state.decision is not None:
            raise ValueError("Toss decision has already been submitted.")

        # Identity validation: only toss winner can decide to bat or bowl
        if user_id.strip() != toss_state.winner_id:
            raise PermissionError(f"Only the toss winner ({toss_state.winner_name}) can choose whether to Bat or Bowl first.")

        toss_state.decision = clean_decision
        toss_state.step = "COMPLETED"

        # Update Match record
        match = db.query(Match).filter(Match.room_id == room.id).first()
        if match:
            match.toss_winner_id = toss_state.winner_id
            match.toss_decision = clean_decision
            match.status = "LIVE"

        room.status = "LIVE"
        db.commit()
        db.refresh(toss_state)

        # Initialize match innings, batting order, and opening bowler
        from app.match.match_service import MatchService
        MatchService.initialize_or_get_match(db, code)

        logger.info(
            "Toss completed for room %s: %s elected to %s first. Match and innings initialized.",
            code,
            toss_state.winner_name,
            clean_decision,
        )

        return cls.get_toss_state_response(db, code, user_id)

    @classmethod
    def get_toss_state_response(
        cls,
        db: Session,
        room_code: str,
        current_user_id: Optional[str] = None,
    ) -> TossStateResponse:
        """Constructs the complete serializable TossStateResponse payload."""
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        toss_state = db.query(TossState).filter(TossState.room_id == room.id).first()
        if not toss_state:
            raise ValueError(f"Toss state not found for room '{code}'.")

        host_player = next((p for p in room.players if p.is_host), None)
        guest_player = next((p for p in room.players if not p.is_host), None)

        if not host_player or not guest_player:
            raise ValueError(f"Both players must be in room '{code}'.")

        host_team = cls._get_team_info(db, room, host_player)
        guest_team = cls._get_team_info(db, room, guest_player)

        uid = current_user_id.strip() if current_user_id else None
        is_caller = bool(uid and uid == toss_state.caller_id)
        is_winner = bool(uid and uid == toss_state.winner_id)

        return TossStateResponse(
            room_code=code,
            match_id=toss_state.match_id,
            step=toss_state.step,
            caller_id=toss_state.caller_id,
            caller_name=toss_state.caller_name,
            caller_choice=toss_state.caller_choice,
            coin_result=toss_state.coin_result,
            winner_id=toss_state.winner_id,
            winner_name=toss_state.winner_name,
            decision=toss_state.decision,
            host_team=host_team,
            guest_team=guest_team,
            is_current_user_caller=is_caller,
            is_current_user_winner=is_winner,
            draft_completed=True,
            created_at=toss_state.created_at,
            updated_at=toss_state.updated_at,
        )
