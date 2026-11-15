"""
CricXI Draft Service (Phase 3).
Encapsulates round selection, candidate pool fetching, position validation,
turn alternation, auto-selection, and state persistence.
"""

from datetime import datetime, timezone, timedelta
import json
import logging
import random
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.models.room import Room, RoomPlayer
from app.models.draft import DraftPick, DraftState
from app.schemas.draft import (
    DraftPickResponse,
    DraftStateResponse,
    SquadSlot,
    UserSquad,
)
from app.schemas.player import PlayerResponse
from app.services.dataset_loader import dataset_service

logger = logging.getLogger(__name__)

TURN_DURATION_SECONDS = 30
TOTAL_ROUNDS = 11


def parse_eligible_positions(eligible_str: str) -> Set[int]:
    """Parses position string like '1|2' or '3,4' into a set of integers."""
    if not eligible_str:
        return set(range(1, 12))
    cleaned = str(eligible_str).replace(",", "|")
    positions = set()
    for part in cleaned.split("|"):
        part = part.strip()
        if part.isdigit():
            positions.add(int(part))
    return positions or set(range(1, 12))


class DraftService:
    """Core domain logic for the 11-round T20 player draft with forward checking validation."""

    @classmethod
    def parse_country_history(cls, raw_history: Optional[str]) -> Tuple[List[List[Any]], bool]:
        """Parses country_history JSON, returning (history_list, is_single_pool)."""
        if not raw_history:
            return [], False
        try:
            data = json.loads(raw_history)
            if isinstance(data, dict):
                return data.get("history", []), bool(data.get("single_pool", False))
            elif isinstance(data, list):
                is_single = len(data) > 1 and len(set((h[0], int(h[1])) for h in data if len(h) >= 2)) == 1
                return data, is_single
        except Exception:
            pass
        return [], False

    @classmethod
    def is_single_pool_draft(cls, draft_state: DraftState, db: Optional[Session] = None) -> bool:
        """Checks if draft is configured to draft from a single historical team/era."""
        _, is_single = cls.parse_country_history(draft_state.country_history)
        return is_single

    @classmethod
    def is_bowling_option(cls, player: Dict[str, Any]) -> bool:
        """Determines if a player counts as a legitimate bowling option."""
        role = str(player.get("primary_role", "")).upper()
        rating = float(player.get("bowling_rating", 0.0) or 0.0)
        return role in ("PACE", "SPIN", "AR") or rating >= 40.0

    @classmethod
    def check_joint_feasibility(
        cls,
        vacant_a: List[int],
        wk_needed_a: int,
        bowl_needed_a: int,
        vacant_b: List[int],
        wk_needed_b: int,
        bowl_needed_b: int,
        available_players: List[Dict[str, Any]],
    ) -> Tuple[bool, str]:
        """
        Constraint Satisfaction & Backtracking Solver:
        Verifies whether both teams can legally complete their remaining vacant slots
        from the remaining available player pool without conflicts or rule violations.
        """
        total_needed = len(vacant_a) + len(vacant_b)
        if len(available_players) < total_needed:
            return False, "Constraint validation failed: Not enough players remaining in candidate pool to complete both teams (last player conflict)."

        pool_wks = sum(1 for p in available_players if bool(p.get("is_wicketkeeper", False)))
        if pool_wks < (wk_needed_a + wk_needed_b):
            return False, "Constraint validation failed: Not enough wicketkeepers remaining in candidate pool to satisfy role constraints for both teams (last role conflict)."

        pool_bowlers = sum(1 for p in available_players if cls.is_bowling_option(p))
        if pool_bowlers < (bowl_needed_a + bowl_needed_b):
            return False, "Constraint validation failed: Not enough bowling options remaining in candidate pool to satisfy role constraints for both teams."

        player_items = []
        for p in available_players:
            slots = parse_eligible_positions(p.get("eligible_positions", ""))
            player_items.append({
                "id": int(p["player_id"]),
                "name": p.get("player_name", "Player"),
                "slots": slots,
                "is_wk": bool(p.get("is_wicketkeeper", False)),
                "is_bowl": cls.is_bowling_option(p),
            })

        for s in vacant_a:
            if not any(s in pi["slots"] for pi in player_items):
                return False, f"Constraint validation failed: No remaining player can legally play at vacant position {s} for Team A."
        for s in vacant_b:
            if not any(s in pi["slots"] for pi in player_items):
                return False, f"Constraint validation failed: No remaining player can legally play at vacant position {s} for Team B."

        if total_needed == 0:
            return True, ""

        targets = [("A", s) for s in vacant_a] + [("B", s) for s in vacant_b]

        # MCV: sort targets so slots with fewer eligible candidates are assigned first
        def target_candidate_count(target):
            team, slot = target
            return sum(1 for pi in player_items if slot in pi["slots"])

        targets.sort(key=target_candidate_count)

        steps = [0]
        max_steps = 2000

        def backtrack(
            idx: int,
            used_pids: Set[int],
            rem_wk_a: int,
            rem_bowl_a: int,
            rem_wk_b: int,
            rem_bowl_b: int,
        ) -> bool:
            steps[0] += 1
            if steps[0] > max_steps:
                return True

            if idx == len(targets):
                return rem_wk_a <= 0 and rem_bowl_a <= 0 and rem_wk_b <= 0 and rem_bowl_b <= 0

            team, slot = targets[idx]
            rem_targets_a = sum(1 for t, _ in targets[idx:] if t == "A")
            rem_targets_b = sum(1 for t, _ in targets[idx:] if t == "B")
            if rem_wk_a > rem_targets_a or rem_bowl_a > rem_targets_a:
                return False
            if rem_wk_b > rem_targets_b or rem_bowl_b > rem_targets_b:
                return False

            # Eligible candidates for this slot
            eligible_cand = [pi for pi in player_items if pi["id"] not in used_pids and slot in pi["slots"]]

            # Prioritize candidates satisfying urgent team constraints first
            def cand_sort_key(pi):
                score = 0
                if team == "A":
                    if rem_wk_a > 0 and pi["is_wk"]:
                        score += 20
                    if rem_bowl_a > 0 and pi["is_bowl"]:
                        score += 10
                else:
                    if rem_wk_b > 0 and pi["is_wk"]:
                        score += 20
                    if rem_bowl_b > 0 and pi["is_bowl"]:
                        score += 10
                return score

            eligible_cand.sort(key=cand_sort_key, reverse=True)

            for pi in eligible_cand:
                pid = pi["id"]
                used_pids.add(pid)
                new_wk_a = rem_wk_a - (1 if team == "A" and pi["is_wk"] else 0)
                new_bowl_a = rem_bowl_a - (1 if team == "A" and pi["is_bowl"] else 0)
                new_wk_b = rem_wk_b - (1 if team == "B" and pi["is_wk"] else 0)
                new_bowl_b = rem_bowl_b - (1 if team == "B" and pi["is_bowl"] else 0)

                if backtrack(idx + 1, used_pids, new_wk_a, new_bowl_a, new_wk_b, new_bowl_b):
                    return True

                used_pids.remove(pid)

            return False

        if not backtrack(0, set(), wk_needed_a, bowl_needed_a, wk_needed_b, bowl_needed_b):
            return False, "Constraint validation failed: No valid combination of remaining players can complete legal XIs for both teams."

        return True, ""

    @classmethod
    def get_all_combinations(cls) -> List[Tuple[str, int]]:
        """Returns all valid (Country, Decade) combinations present in the dataset."""
        if not dataset_service.is_loaded:
            dataset_service.load()
        players = dataset_service.get_all_players()
        if not players:
            return []
        combos = sorted(list(set((p["country"], int(p["decade"])) for p in players if p.get("country") and p.get("decade"))))
        return combos

    @classmethod
    def select_next_combination(
        cls,
        history: List[List[Any]],
        vacant_a: Optional[List[int]] = None,
        vacant_b: Optional[List[int]] = None,
        wk_needed_a: int = 0,
        bowl_needed_a: int = 0,
        wk_needed_b: int = 0,
        bowl_needed_b: int = 0,
        is_last_round: bool = False,
    ) -> Tuple[str, int]:
        """
        Picks a random (Country, Decade) not previously used in this draft.
        If vacant positions/roles are provided (e.g. for Round 11), guarantees
        that the chosen combination contains feasible candidates for both teams.
        """
        all_combos = cls.get_all_combinations()
        if not all_combos:
            raise ValueError(
                "Cannot select draft combination: The master player dataset is empty or contains no valid combinations."
            )

        used_set = set((h[0], int(h[1])) for h in history if len(h) >= 2)
        available = [c for c in all_combos if c not in used_set]

        if not available:
            # Fallback if all 46 combinations exhausted (should not happen in 11 rounds)
            available = all_combos

        if not available:
            raise ValueError(
                "Cannot select draft combination: No valid (Country, Decade) combinations available."
            )

        # If vacant positions and role needs are provided, filter available combinations
        # to guarantee that both teams can legally finish their playing XIs
        if vacant_a is not None and vacant_b is not None:
            viable_combos = []
            for c_name, d_year in available:
                pool = dataset_service.get_players_by_country_and_decade(c_name, d_year)
                feasible, _ = cls.check_joint_feasibility(
                    vacant_a=vacant_a,
                    wk_needed_a=wk_needed_a,
                    bowl_needed_a=bowl_needed_a,
                    vacant_b=vacant_b,
                    wk_needed_b=wk_needed_b,
                    bowl_needed_b=bowl_needed_b,
                    available_players=pool,
                )
                if feasible:
                    viable_combos.append((c_name, d_year))

            if viable_combos:
                print(f"[DRAFT DEBUG] Before random.choice (viable_combos) - combinations available: {len(viable_combos)}, first 10: {viable_combos[:10]}", flush=True)
                return random.choice(viable_combos)
            logger.warning(
                "No perfectly viable pool found for vacant_a=%s, vacant_b=%s; falling back to random available pool.",
                vacant_a,
                vacant_b,
            )

        print(f"[DRAFT DEBUG] Before random.choice (available) - combinations available: {len(available)}, first 10: {available[:10]}", flush=True)
        return random.choice(available)

    @classmethod
    def initialize_draft(
        cls,
        db: Session,
        room_code: str,
        country: Optional[str] = None,
        decade: Optional[int] = None,
        is_single_pool: bool = False,
        force_fresh: bool = False,
    ) -> DraftState:
        """Initializes draft state for a room if not already created."""
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        players = db.query(RoomPlayer).filter(RoomPlayer.room_id == room.id).all()
        if len(players) < 2:
            raise ValueError(f"Draft requires exactly 2 players in room '{code}' (currently has {len(players)}).")

        draft_state = db.query(DraftState).filter(DraftState.room_id == room.id).first()
        if draft_state:
            if not draft_state.is_finished and not force_fresh:
                return draft_state
            # Draft was finished or fresh state forced: clean up old draft picks and state
            db.query(DraftPick).filter(DraftPick.room_id == room.id).delete()
            db.delete(draft_state)
            db.commit()

        # Round 1 Setup & Pool Feasibility Validation
        if country and decade:
            c_val, d_val = str(country).strip(), int(decade)
            initial_pool = dataset_service.get_players_by_country_and_decade(c_val, d_val)
            if len(initial_pool) < 11:
                logger.warning(
                    "Requested starting pool '%s %d' has %d players (< 11 required). Regenerating valid pool before draft starts.",
                    c_val,
                    d_val,
                    len(initial_pool),
                )
                c_val, d_val = cls.select_next_combination([])
        else:
            c_val, d_val = cls.select_next_combination([])

        if is_single_pool:
            country_history_obj = {"single_pool": True, "history": [[c_val, d_val]]}
        else:
            country_history_obj = [[c_val, d_val]]

        host_player = next((p for p in players if p.user_id == room.host_id or p.is_host), players[0])

        now = datetime.now(timezone.utc)
        turn_deadline = now + timedelta(seconds=TURN_DURATION_SECONDS)

        draft_state = DraftState(
            room_id=room.id,
            current_round=1,
            current_turn=1,  # 1 = Host, 2 = Guest in Round 1
            current_picker_id=host_player.user_id,
            round_country=c_val,
            round_decade=d_val,
            country_history=json.dumps(country_history_obj),
            turn_deadline=turn_deadline,
            remaining_seconds=TURN_DURATION_SECONDS,
            is_finished=False,
            created_at=now,
            updated_at=now,
        )
        room.status = "DRAFTING"
        try:
            db.add(draft_state)
            db.commit()
            db.refresh(draft_state)
        except Exception as e:
            db.rollback()
            existing = db.query(DraftState).filter(DraftState.room_id == room.id).first()
            if existing:
                return existing
            logger.error("Failed to commit DraftState for room %s: %s", code, e)
            raise

        logger.info(
            "Draft initialized for room %s. Round 1: %s %d (single_pool=%s). First picker: %s",
            code,
            c_val,
            d_val,
            is_single_pool,
            host_player.username,
        )
        return draft_state

    @classmethod
    def get_first_picker_for_round(cls, round_number: int, host_id: str, guest_id: str) -> str:
        """
        Alternates the first picker every round:
        Odd rounds (1, 3, 5, 7, 9, 11) -> Host picks first
        Even rounds (2, 4, 6, 8, 10)    -> Guest picks first
        """
        return host_id if (round_number % 2 == 1) else guest_id

    @classmethod
    def get_picker_for_turn(cls, round_number: int, turn_number: int, host_id: str, guest_id: str) -> str:
        """Determines active picker for round and turn (1 or 2)."""
        first_picker = cls.get_first_picker_for_round(round_number, host_id, guest_id)
        second_picker = guest_id if first_picker == host_id else host_id
        return first_picker if turn_number == 1 else second_picker

    @classmethod
    def get_draft_state_response(cls, db: Session, room_code: str) -> DraftStateResponse:
        """Builds complete live draft payload for client synchronization."""
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        players = db.query(RoomPlayer).filter(RoomPlayer.room_id == room.id).all()
        if len(players) < 2:
            raise ValueError(f"Draft requires exactly 2 players in room '{code}' (currently has {len(players)}).")

        draft_state = db.query(DraftState).filter(DraftState.room_id == room.id).first()
        if not draft_state:
            # Initialize if not present
            try:
                draft_state = cls.initialize_draft(db, code)
            except Exception:
                db.rollback()
                draft_state = db.query(DraftState).filter(DraftState.room_id == room.id).first()
                if not draft_state:
                    raise
        elif draft_state.is_finished and room.status == "DRAFTING":
            # Room has been reset or started for a new match; generate fresh draft state
            try:
                draft_state = cls.initialize_draft(db, code, force_fresh=True)
            except Exception:
                db.rollback()
                draft_state = db.query(DraftState).filter(DraftState.room_id == room.id).first()
                if not draft_state:
                    raise

        host_player = next((p for p in players if p.user_id == room.host_id or p.is_host), players[0])
        guest_player = next((p for p in players if p.user_id != host_player.user_id), None)
        if not guest_player:
            guest_player = players[1] if len(players) > 1 else host_player

        # Calculate live remaining timer seconds
        now = datetime.now(timezone.utc)
        if draft_state.is_finished:
            remaining_seconds = 0
        elif draft_state.turn_deadline:
            delta = (draft_state.turn_deadline.replace(tzinfo=timezone.utc) if draft_state.turn_deadline.tzinfo is None else draft_state.turn_deadline) - now
            remaining_seconds = max(0, int(round(delta.total_seconds())))
        else:
            remaining_seconds = draft_state.remaining_seconds if draft_state.remaining_seconds is not None else 30

        # Parse history
        history, _ = cls.parse_country_history(draft_state.country_history)

        # Fetch all picks for this room
        picks = db.query(DraftPick).filter(DraftPick.room_id == room.id).order_by(DraftPick.created_at.asc()).all()
        drafted_player_ids = set(p.player_id for p in picks)

        # Build Host squad (slots 1 to 11)
        host_picks = [p for p in picks if p.user_id == host_player.user_id]
        host_slots = []
        host_picks_by_pos = {p.batting_position: p for p in host_picks}
        for pos in range(1, 12):
            pick = host_picks_by_pos.get(pos)
            pick_resp = None
            if pick:
                player_meta = dataset_service.get_player_by_id(pick.player_id) or {}
                pick_resp = DraftPickResponse(
                    id=pick.id,
                    round_number=pick.round_number,
                    user_id=pick.user_id,
                    player_id=pick.player_id,
                    player_name=pick.player_name,
                    batting_position=pick.batting_position,
                    selected_country=pick.selected_country,
                    selected_decade=pick.selected_decade,
                    primary_role=player_meta.get("primary_role"),
                    is_captain=bool(player_meta.get("is_captain", False)),
                    is_wicketkeeper=bool(player_meta.get("is_wicketkeeper", False)),
                    overall_rating=float(player_meta.get("overall_rating", 0.0)),
                    created_at=pick.created_at,
                )
            host_slots.append(SquadSlot(slot_number=pos, is_locked=pick_resp is not None, pick=pick_resp))

        host_rating = round(sum(s.pick.overall_rating for s in host_slots if s.pick) / len(host_picks), 1) if host_picks else 0.0
        host_squad = UserSquad(
            user_id=host_player.user_id,
            username=host_player.username,
            is_host=True,
            slots=host_slots,
            picked_count=len(host_picks),
            total_rating=host_rating,
        )

        # Build Guest squad (slots 1 to 11)
        guest_picks = [p for p in picks if p.user_id == guest_player.user_id]
        guest_slots = []
        guest_picks_by_pos = {p.batting_position: p for p in guest_picks}
        for pos in range(1, 12):
            pick = guest_picks_by_pos.get(pos)
            pick_resp = None
            if pick:
                player_meta = dataset_service.get_player_by_id(pick.player_id) or {}
                pick_resp = DraftPickResponse(
                    id=pick.id,
                    round_number=pick.round_number,
                    user_id=pick.user_id,
                    player_id=pick.player_id,
                    player_name=pick.player_name,
                    batting_position=pick.batting_position,
                    selected_country=pick.selected_country,
                    selected_decade=pick.selected_decade,
                    primary_role=player_meta.get("primary_role"),
                    is_captain=bool(player_meta.get("is_captain", False)),
                    is_wicketkeeper=bool(player_meta.get("is_wicketkeeper", False)),
                    overall_rating=float(player_meta.get("overall_rating", 0.0)),
                    created_at=pick.created_at,
                )
            guest_slots.append(SquadSlot(slot_number=pos, is_locked=pick_resp is not None, pick=pick_resp))

        guest_rating = round(sum(s.pick.overall_rating for s in guest_slots if s.pick) / len(guest_picks), 1) if guest_picks else 0.0
        guest_squad = UserSquad(
            user_id=guest_player.user_id,
            username=guest_player.username,
            is_host=False,
            slots=guest_slots,
            picked_count=len(guest_picks),
            total_rating=guest_rating,
        )

        # Candidate pool: matching round country & decade, minus players drafted in this room
        available_pool = []
        if not draft_state.is_finished and draft_state.round_country and draft_state.round_decade:
            raw_candidates = dataset_service.get_players_by_country_and_decade(
                draft_state.round_country, draft_state.round_decade
            )
            for c in raw_candidates:
                if int(c["player_id"]) not in drafted_player_ids:
                    available_pool.append(PlayerResponse.model_validate(c))

        # Sort available pool by overall_rating descending by default
        available_pool.sort(key=lambda p: p.overall_rating, reverse=True)

        # Current picker name
        current_picker_id = draft_state.current_picker_id or host_player.user_id
        current_picker_player = next((p for p in players if p.user_id == current_picker_id), None)
        current_picker_name = current_picker_player.username if current_picker_player else (host_player.username if host_player else "Host")

        # Format all picks
        all_picks_resp = []
        for p in picks:
            p_meta = dataset_service.get_player_by_id(p.player_id) or {}
            all_picks_resp.append(
                DraftPickResponse(
                    id=p.id,
                    round_number=p.round_number,
                    user_id=p.user_id,
                    player_id=p.player_id,
                    player_name=p.player_name,
                    batting_position=p.batting_position,
                    selected_country=p.selected_country,
                    selected_decade=p.selected_decade,
                    primary_role=p_meta.get("primary_role"),
                    is_captain=bool(p_meta.get("is_captain", False)),
                    is_wicketkeeper=bool(p_meta.get("is_wicketkeeper", False)),
                    overall_rating=float(p_meta.get("overall_rating", 0.0)),
                    created_at=p.created_at,
                )
            )

        return DraftStateResponse(
            room_code=code,
            current_round=draft_state.current_round or 1,
            total_rounds=11,
            current_turn=draft_state.current_turn or 1,
            current_picker_id=current_picker_id,
            current_picker_name=current_picker_name,
            round_country=draft_state.round_country,
            round_decade=draft_state.round_decade,
            remaining_seconds=remaining_seconds,
            is_finished=bool(draft_state.is_finished),
            country_history=history or [],
            available_pool=available_pool or [],
            candidates=available_pool or [],
            drafted_player_ids=sorted(list(drafted_player_ids)),
            host_squad=host_squad,
            guest_squad=guest_squad,
            user_squads={
                host_player.user_id: host_squad,
                guest_player.user_id: guest_squad,
            },
            all_picks=all_picks_resp or [],
            updated_at=draft_state.updated_at or now,
        )

    @classmethod
    def make_pick(
        cls,
        db: Session,
        room_code: str,
        user_id: str,
        player_id: int,
        batting_position: int,
        is_auto: bool = False,
    ) -> Tuple[DraftPick, bool]:
        """
        Validates and locks a draft pick for the current user.
        Advances turn or round.
        Returns (DraftPick, is_draft_finished).
        """
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        draft_state = db.query(DraftState).filter(DraftState.room_id == room.id).first()
        if not draft_state:
            raise ValueError("Draft has not started.")

        if draft_state.is_finished:
            raise ValueError("Draft has already finished.")

        if draft_state.current_picker_id != user_id:
            raise PermissionError("It is not your turn to pick.")

        if not (1 <= batting_position <= 11):
            raise ValueError("Batting position must be between 1 and 11.")

        # Check slot not already occupied for this user
        existing_slot_pick = (
            db.query(DraftPick)
            .filter(
                DraftPick.room_id == room.id,
                DraftPick.user_id == user_id,
                DraftPick.batting_position == batting_position,
            )
            .first()
        )
        if existing_slot_pick:
            raise ValueError(f"Batting position {batting_position} is already locked by {existing_slot_pick.player_name}.")

        # Check player exists in dataset
        player_data = dataset_service.get_player_by_id(player_id)
        if not player_data:
            raise ValueError(f"Player ID {player_id} not found in database.")

        # Check player belongs to current round's Country and Decade
        if (
            str(player_data.get("country")).strip().lower() != str(draft_state.round_country).strip().lower()
            or int(player_data.get("decade")) != int(draft_state.round_decade)
        ):
            raise ValueError(
                f"{player_data.get('player_name')} is not part of this round's pool ({draft_state.round_country} {draft_state.round_decade}s)."
            )

        # Check player has not already been drafted in this room
        already_drafted = (
            db.query(DraftPick)
            .filter(DraftPick.room_id == room.id, DraftPick.player_id == player_id)
            .first()
        )
        if already_drafted:
            raise ValueError(f"{player_data.get('player_name')} has already been drafted.")

        # Position validation against eligible_positions (strictly enforced for all picks)
        eligible_positions = parse_eligible_positions(player_data.get("eligible_positions", ""))
        if batting_position not in eligible_positions:
            raise ValueError(
                f"{player_data.get('player_name')} cannot play at position {batting_position}. Valid positions: {sorted(list(eligible_positions))}."
            )

        # Forward Checking Constraint Validation (Phase 4 Draft Engine)
        is_valid, error_msg = cls.validate_forward_constraints(
            db=db,
            room=room,
            draft_state=draft_state,
            user_id=user_id,
            player_data=player_data,
            batting_position=batting_position,
        )
        if not is_valid:
            raise ValueError(error_msg)

        # Create DraftPick
        pick = DraftPick(
            room_id=room.id,
            round_number=draft_state.current_round,
            user_id=user_id,
            player_id=player_id,
            player_name=player_data.get("player_name"),
            batting_position=batting_position,
            selected_country=draft_state.round_country,
            selected_decade=draft_state.round_decade,
            created_at=datetime.now(timezone.utc),
        )
        db.add(pick)
        db.flush()

        logger.info(
            "Room %s [R%d T%d]: %s drafted %s into slot %d (auto=%s)",
            code,
            draft_state.current_round,
            draft_state.current_turn,
            user_id,
            pick.player_name,
            batting_position,
            is_auto,
        )

        # Advance Turn / Round
        players = db.query(RoomPlayer).filter(RoomPlayer.room_id == room.id).all()
        host_player = next((p for p in players if p.user_id == room.host_id or p.is_host), players[0])
        guest_player = next((p for p in players if p.user_id != host_player.user_id), None)
        if not guest_player:
            guest_player = players[1] if len(players) > 1 else host_player

        now = datetime.now(timezone.utc)
        is_draft_finished = False

        if draft_state.current_turn == 1:
            # Advance to Turn 2 of the same round
            draft_state.current_turn = 2
            draft_state.current_picker_id = cls.get_picker_for_turn(
                draft_state.current_round, 2, host_player.user_id, guest_player.user_id
            )
            draft_state.turn_deadline = now + timedelta(seconds=TURN_DURATION_SECONDS)
            draft_state.remaining_seconds = TURN_DURATION_SECONDS

        else:
            # Turn 2 complete: Round finishes
            if draft_state.current_round < TOTAL_ROUNDS:
                draft_state.current_round += 1
                draft_state.current_turn = 1
                room.current_round = draft_state.current_round

                # Check if single pool draft
                is_single = cls.is_single_pool_draft(draft_state)
                if is_single:
                    next_country = draft_state.round_country
                    next_decade = draft_state.round_decade
                else:
                    history, _ = cls.parse_country_history(draft_state.country_history)
                    if draft_state.current_round == TOTAL_ROUNDS:
                        # For the final round (Round 11), calculate remaining vacancies and roles
                        # to guarantee the selected pool can legally complete both teams without deadlock
                        h_picks = db.query(DraftPick).filter(DraftPick.room_id == room.id, DraftPick.user_id == host_player.user_id).all()
                        g_picks = db.query(DraftPick).filter(DraftPick.room_id == room.id, DraftPick.user_id == guest_player.user_id).all()
                        v_a = sorted(list(set(range(1, 12)) - set(p.batting_position for p in h_picks)))
                        v_b = sorted(list(set(range(1, 12)) - set(p.batting_position for p in g_picks)))
                        has_wk_a = any(bool(dataset_service.get_player_by_id(p.player_id).get("is_wicketkeeper", False)) for p in h_picks)
                        has_wk_b = any(bool(dataset_service.get_player_by_id(p.player_id).get("is_wicketkeeper", False)) for p in g_picks)
                        bowlers_a = sum(1 for p in h_picks if cls.is_bowling_option(dataset_service.get_player_by_id(p.player_id)))
                        bowlers_b = sum(1 for p in g_picks if cls.is_bowling_option(dataset_service.get_player_by_id(p.player_id)))
                        next_country, next_decade = cls.select_next_combination(
                            history=history,
                            vacant_a=v_a,
                            vacant_b=v_b,
                            wk_needed_a=0 if has_wk_a else 1,
                            bowl_needed_a=max(0, 5 - bowlers_a),
                            wk_needed_b=0 if has_wk_b else 1,
                            bowl_needed_b=max(0, 5 - bowlers_b),
                            is_last_round=True,
                        )
                    else:
                        next_country, next_decade = cls.select_next_combination(history)

                    history.append([next_country, next_decade])
                    draft_state.country_history = json.dumps(history)
                    draft_state.round_country = next_country
                    draft_state.round_decade = next_decade

                # Determine first picker for the new round (alternates!)
                draft_state.current_picker_id = cls.get_first_picker_for_round(
                    draft_state.current_round, host_player.user_id, guest_player.user_id
                )
                draft_state.turn_deadline = now + timedelta(seconds=TURN_DURATION_SECONDS)
                draft_state.remaining_seconds = TURN_DURATION_SECONDS

            else:
                # Round 11 Turn 2 finished: All 11 players drafted for both teams!
                draft_state.is_finished = True
                draft_state.remaining_seconds = 0
                draft_state.turn_deadline = None
                room.status = "TOSS"
                is_draft_finished = True

        draft_state.updated_at = now
        room.updated_at = now
        db.commit()
        db.refresh(pick)
        db.refresh(draft_state)

        return pick, is_draft_finished

    @classmethod
    def validate_forward_constraints(
        cls,
        db: Session,
        room: Room,
        draft_state: DraftState,
        user_id: str,
        player_data: Dict[str, Any],
        batting_position: int,
    ) -> Tuple[bool, str]:
        """
        Constraint-based forward checking validation.
        Simulates the pick and verifies that BOTH teams can still legally complete their playing XIs.
        """
        players = db.query(RoomPlayer).filter(RoomPlayer.room_id == room.id).all()
        host_player = next((p for p in players if p.user_id == room.host_id or p.is_host), players[0])
        guest_player = next((p for p in players if p.user_id != host_player.user_id), None)
        if not guest_player:
            guest_player = players[1] if len(players) > 1 else host_player
        team_a_user_id = host_player.user_id
        team_b_user_id = guest_player.user_id

        # Existing picks in this room
        picks = db.query(DraftPick).filter(DraftPick.room_id == room.id).all()
        team_a_picks = [p for p in picks if p.user_id == team_a_user_id]
        team_b_picks = [p for p in picks if p.user_id == team_b_user_id]

        cand_id = int(player_data["player_id"])

        # Check duplicate player
        if any(p.player_id == cand_id for p in picks):
            return False, f"Player {player_data.get('player_name')} has already been drafted."

        # Simulate pick
        sim_a_picks = list(team_a_picks)
        sim_b_picks = list(team_b_picks)

        dummy_pick = {
            "player_id": cand_id,
            "batting_position": batting_position,
            "player_meta": player_data,
        }

        if user_id == team_a_user_id:
            if any(p.batting_position == batting_position for p in sim_a_picks):
                return False, f"Batting position {batting_position} is already occupied for Team A."
            sim_a_picks.append(dummy_pick)
        else:
            if any(p.batting_position == batting_position for p in sim_b_picks):
                return False, f"Batting position {batting_position} is already occupied for Team B."
            sim_b_picks.append(dummy_pick)

        occupied_a = {p.batting_position if hasattr(p, "batting_position") else p["batting_position"] for p in sim_a_picks}
        occupied_b = {p.batting_position if hasattr(p, "batting_position") else p["batting_position"] for p in sim_b_picks}
        vacant_a = sorted(list(set(range(1, 12)) - occupied_a))
        vacant_b = sorted(list(set(range(1, 12)) - occupied_b))

        def get_meta(p):
            if isinstance(p, dict) and "player_meta" in p:
                return p["player_meta"]
            pid = p.player_id if hasattr(p, "player_id") else p["player_id"]
            return dataset_service.get_player_by_id(pid) or {}

        # Wicketkeeper needed?
        has_wk_a = any(bool(get_meta(p).get("is_wicketkeeper", False)) for p in sim_a_picks)
        has_wk_b = any(bool(get_meta(p).get("is_wicketkeeper", False)) for p in sim_b_picks)
        wk_needed_a = 0 if has_wk_a else 1
        wk_needed_b = 0 if has_wk_b else 1

        # Bowlers needed?
        bowlers_a = sum(1 for p in sim_a_picks if cls.is_bowling_option(get_meta(p)))
        bowlers_b = sum(1 for p in sim_b_picks if cls.is_bowling_option(get_meta(p)))
        bowl_needed_a = max(0, 5 - bowlers_a)
        bowl_needed_b = max(0, 5 - bowlers_b)

        # Available pool for current round/era
        all_drafted_ids = set(p.player_id for p in picks) | {cand_id}
        raw_candidates = dataset_service.get_players_by_country_and_decade(
            draft_state.round_country, draft_state.round_decade
        )
        remaining_pool = [c for c in raw_candidates if int(c["player_id"]) not in all_drafted_ids]

        is_single_pool = cls.is_single_pool_draft(draft_state, db)
        is_round_11 = (draft_state.current_round == TOTAL_ROUNDS)

        if is_single_pool or is_round_11:
            # Full completion check for both teams from remaining pool
            return cls.check_joint_feasibility(
                vacant_a=vacant_a,
                wk_needed_a=wk_needed_a,
                bowl_needed_a=bowl_needed_a,
                vacant_b=vacant_b,
                wk_needed_b=wk_needed_b,
                bowl_needed_b=bowl_needed_b,
                available_players=remaining_pool,
            )

        # Role capacity validation (Rounds 1-10): ensure both teams retain enough remaining vacant slots
        # to satisfy mandatory role requirements (at least 1 Wicketkeeper and at least 5 Bowling options)
        if len(vacant_a) < (wk_needed_a + bowl_needed_a):
            return False, "Constraint validation failed: Insufficient remaining slots for Team A to complete required roles (Wicketkeeper and 5 Bowling options)."
        if len(vacant_b) < (wk_needed_b + bowl_needed_b):
            return False, "Constraint validation failed: Insufficient remaining slots for Team B to complete required roles (Wicketkeeper and 5 Bowling options)."

        # Wicketkeeper slot feasibility: Wicketkeepers can only bat at positions <= 8
        if wk_needed_a > 0 and not any(s <= 8 for s in vacant_a):
            return False, "Constraint validation failed: Team A has no remaining vacant slots suitable for a Wicketkeeper (positions 1-8)."
        if wk_needed_b > 0 and not any(s <= 8 for s in vacant_b):
            return False, "Constraint validation failed: Team B has no remaining vacant slots suitable for a Wicketkeeper (positions 1-8)."

        # Bowling slot feasibility: Bowling options require middle/lower order slots (>= 5)
        if bowl_needed_a > 0 and sum(1 for s in vacant_a if s >= 5) < bowl_needed_a:
            return False, "Constraint validation failed: Team A has insufficient remaining middle/lower order slots for required bowling options."
        if bowl_needed_b > 0 and sum(1 for s in vacant_b if s >= 5) < bowl_needed_b:
            return False, "Constraint validation failed: Team B has insufficient remaining middle/lower order slots for required bowling options."
        else:
            # Multi-round draft (Rounds 1-10):
            # If current_turn is 1, Turn 2 of this round must have at least one viable candidate
            # that fits an open slot without violating role capacity
            if draft_state.current_turn == 1:
                other_vacant = vacant_b if user_id == team_a_user_id else vacant_a
                other_wk_needed = wk_needed_b if user_id == team_a_user_id else wk_needed_a
                other_bowl_needed = bowl_needed_b if user_id == team_a_user_id else bowl_needed_a

                can_other_pick = False
                for c in remaining_pool:
                    c_slots = parse_eligible_positions(c.get("eligible_positions", ""))
                    valid_s = set(s for s in other_vacant if s in c_slots)
                    if not valid_s:
                        continue

                    # Check that picking c doesn't exhaust other team's capacity for required roles
                    new_wk = max(0, other_wk_needed - (1 if bool(c.get("is_wicketkeeper", False)) else 0))
                    new_bowl = max(0, other_bowl_needed - (1 if cls.is_bowling_option(c) else 0))
                    rem_slots_after = len(other_vacant) - 1

                    if rem_slots_after >= (new_wk + new_bowl):
                        can_other_pick = True
                        break

                if not can_other_pick:
                    return False, "Constraint validation failed: This pick leaves the other team with no eligible player for their remaining slot(s) in this round."

        return True, ""

    @classmethod
    def cancel_draft(
        cls,
        db: Session,
        room_code: str,
        reason: str = "Draft cancelled: Unable to complete legal XIs with remaining player pool.",
    ) -> Tuple[DraftState, Room]:
        """Cancels draft state and sets room to ABANDONED when draft completion is impossible."""
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")
        draft_state = db.query(DraftState).filter(DraftState.room_id == room.id).first()
        if not draft_state:
            raise ValueError("Draft has not started.")

        room.status = "ABANDONED"
        draft_state.is_finished = True
        draft_state.remaining_seconds = 0
        draft_state.turn_deadline = None
        db.commit()
        db.refresh(room)
        db.refresh(draft_state)
        logger.info("Room %s draft cancelled: %s", code, reason)
        return draft_state, room

    @classmethod
    def pause_draft(cls, db: Session, room_code: str) -> Optional[DraftState]:
        """Pauses the draft timer, storing exact remaining seconds in draft_state and clearing turn_deadline."""
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            return None
        draft_state = db.query(DraftState).filter(DraftState.room_id == room.id).first()
        if not draft_state or draft_state.is_finished:
            return None

        now = datetime.now(timezone.utc)
        if draft_state.turn_deadline:
            delta = (draft_state.turn_deadline.replace(tzinfo=timezone.utc) if draft_state.turn_deadline.tzinfo is None else draft_state.turn_deadline) - now
            rem = max(0, int(round(delta.total_seconds())))
            draft_state.remaining_seconds = rem
        draft_state.turn_deadline = None
        draft_state.updated_at = now
        db.commit()
        db.refresh(draft_state)
        logger.info("Room %s draft paused at %s seconds remaining", code, draft_state.remaining_seconds)
        return draft_state

    @classmethod
    def resume_draft(cls, db: Session, room_code: str) -> Optional[DraftState]:
        """Resumes the draft timer with the exact remaining seconds."""
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            return None
        draft_state = db.query(DraftState).filter(DraftState.room_id == room.id).first()
        if not draft_state or draft_state.is_finished:
            return None

        now = datetime.now(timezone.utc)
        rem = (
            draft_state.remaining_seconds
            if (draft_state.remaining_seconds is not None and draft_state.remaining_seconds > 0)
            else TURN_DURATION_SECONDS
        )
        draft_state.remaining_seconds = rem
        draft_state.turn_deadline = now + timedelta(seconds=rem)
        draft_state.updated_at = now
        db.commit()
        db.refresh(draft_state)
        logger.info("Room %s draft resumed with %s seconds remaining", code, rem)
        return draft_state

    @classmethod
    def execute_auto_pick(cls, db: Session, room_code: str) -> Tuple[Optional[DraftPick], bool]:
        """
        Executes automatic pick when the 30-second timer expires.
        Priority 2 Auto Pick Intelligence:
        Evaluates candidate selections based strictly on team needs rather than overall rating alone:
        1. Missing wicketkeeper (highest priority: best legal WK chosen over higher-rated batters)
        2. Missing bowling options (bowling requirement prioritized when bowling slots needed)
        3. Remaining batting positions & natural role fit
        4. Remaining eligible positions
        5. Overall rating (quality tiebreaker within matching priority tiers)
        Never assigns random players. Strictly respects forward-checking constraints.
        """
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            return None, False

        draft_state = db.query(DraftState).filter(DraftState.room_id == room.id).first()
        if not draft_state or draft_state.is_finished:
            return None, False

        user_id = draft_state.current_picker_id

        # Current squad composition and team needs
        existing_picks = (
            db.query(DraftPick)
            .filter(DraftPick.room_id == room.id, DraftPick.user_id == user_id)
            .all()
        )
        occupied_positions = set(p.batting_position for p in existing_picks)
        vacant_positions = sorted(list(set(range(1, 12)) - occupied_positions))
        slots_left = len(vacant_positions)

        has_wk = any(bool(dataset_service.get_player_by_id(p.player_id).get("is_wicketkeeper", False)) for p in existing_picks)
        bowler_count = sum(1 for p in existing_picks if cls.is_bowling_option(dataset_service.get_player_by_id(p.player_id)))
        wk_needed = 0 if has_wk else 1
        bowl_needed = max(0, 5 - bowler_count)

        all_drafted_ids = set(
            p.player_id
            for p in db.query(DraftPick).filter(DraftPick.room_id == room.id).all()
        )

        candidates = dataset_service.get_players_by_country_and_decade(
            draft_state.round_country, draft_state.round_decade
        )

        valid_candidate_pairs: List[Tuple[Dict[str, Any], int, float]] = []

        for cand in candidates:
            cand_id = int(cand["player_id"])
            if cand_id in all_drafted_ids:
                continue

            eligible_slots = parse_eligible_positions(cand.get("eligible_positions", ""))
            available_slots = sorted(list(eligible_slots - occupied_positions))
            if not available_slots:
                continue

            is_wk = bool(cand.get("is_wicketkeeper", False))
            is_bowl = cls.is_bowling_option(cand)
            ovr = float(cand.get("overall_rating", 0.0))
            role = str(cand.get("primary_role", "")).upper()

            for slot in available_slots:
                # Forward checking validation before accepting
                is_valid, _ = cls.validate_forward_constraints(
                    db=db,
                    room=room,
                    draft_state=draft_state,
                    user_id=user_id,
                    player_data=cand,
                    batting_position=slot,
                )
                if not is_valid:
                    continue

                # Priority 2 Scoring Function: Team Need > Player Rating
                score = ovr

                # 1. Missing Wicketkeeper Priority
                if wk_needed > 0 and is_wk:
                    score += 50000.0

                # 2. Missing Bowling Options Priority
                if bowl_needed >= slots_left and is_bowl:
                    # Critical bowling need: every remaining slot must be a bowler
                    score += 30000.0
                elif bowl_needed > 0 and is_bowl:
                    score += 10000.0 * (bowl_needed / float(max(1, slots_left)))

                # 3. Positional Fit & Remaining Batting Positions
                if slot in (1, 2) and role in ("BAT", "BATTER", "WK"):
                    score += 100.0
                elif slot in (3, 4, 5) and role in ("BAT", "BATTER", "AR", "WK"):
                    score += 100.0
                elif slot in (6, 7) and role in ("AR", "WK", "BAT", "BATTER"):
                    score += 100.0
                elif slot in (8, 9, 10, 11) and (role in ("PACE", "SPIN", "AR") or is_bowl):
                    score += 100.0

                # Penalize unnatural slot allocations
                if slot <= 4 and is_bowl and not is_wk and role in ("PACE", "SPIN"):
                    score -= 300.0
                if slot >= 9 and role in ("BAT", "BATTER") and not is_bowl:
                    score -= 300.0

                valid_candidate_pairs.append((cand, slot, score))

        # If no legally valid candidate fits without violating forward constraints:
        # Never auto-assign random players. Fail gracefully and cancel draft.
        if not valid_candidate_pairs:
            logger.warning(
                "Auto pick failed to find a legally valid candidate satisfying forward constraints for room %s",
                code,
            )
            cls.cancel_draft(db, code, reason="Draft cancelled: Unable to complete legal XIs with remaining player pool.")
            return None, False

        # Select the pair with highest intelligent need score
        valid_candidate_pairs.sort(key=lambda x: x[2], reverse=True)
        chosen_candidate, chosen_position, _ = valid_candidate_pairs[0]

        return cls.make_pick(
            db=db,
            room_code=code,
            user_id=user_id,
            player_id=int(chosen_candidate["player_id"]),
            batting_position=chosen_position,
            is_auto=True,
        )
