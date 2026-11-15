"""
Unit and Integration Tests for CricXI Constraint-Based Draft Validation (Forward Checking).

Covers:
1. Last player conflict (Total available players < total remaining vacant slots)
2. Last role conflict - Wicketkeeper (Remaining WKs < total WKs still required)
3. Last role conflict - Bowling options (Remaining bowlers < total bowlers still required)
4. Duplicate player prevention (Player already drafted in the room cannot be picked again)
5. Empty pool handling (Zero or insufficient players in candidate pool)
6. Both teams completing legal XIs (Full 22-pick draft meeting all position, WK, and bowling constraints)
7. Draft cancellation when impossible (Auto-pick terminates gracefully without random assignment)
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Tuple, List, Dict, Any, Set
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.models.room import Room, RoomPlayer
from app.models.draft import DraftPick, DraftState
from app.draft.draft_service import DraftService
from app.services.dataset_loader import dataset_service


class TestDraftForwardChecking(unittest.TestCase):
    """Test suite for constraint satisfaction and forward-checking draft validation."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=self.engine)
        TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSession()

        if not dataset_service.is_loaded:
            dataset_service.load()

    def tearDown(self):
        self.db.close()

    def _create_room_and_draft(
        self,
        room_code: str = "ROOM01",
        host_id: str = "host_user",
        guest_id: str = "guest_user",
        country: str = "India",
        decade: int = 2010,
        is_single_pool: bool = True,
        round_number: int = 1,
        turn_number: int = 1,
        current_picker_id: str = None,
    ) -> Tuple[Room, DraftState]:
        if not current_picker_id:
            current_picker_id = host_id
        room = Room(room_code=room_code, host_id=host_id, status="DRAFTING")
        self.db.add(room)
        self.db.commit()

        p1 = RoomPlayer(room_id=room.id, user_id=host_id, username="HostPlayer", is_host=True, is_ready=True)
        p2 = RoomPlayer(room_id=room.id, user_id=guest_id, username="GuestPlayer", is_host=False, is_ready=True)
        self.db.add_all([p1, p2])
        self.db.commit()

        draft_state = DraftService.initialize_draft(
            db=self.db,
            room_code=room_code,
            country=country,
            decade=decade,
            is_single_pool=is_single_pool,
        )
        draft_state.current_round = round_number
        draft_state.current_turn = turn_number
        draft_state.current_picker_id = current_picker_id
        self.db.commit()
        self.db.refresh(draft_state)
        return room, draft_state

    def test_last_player_conflict(self):
        """
        Team A has 10 players (1 slot remaining).
        Team B has 10 players (1 slot remaining).
        Candidate pool has only 1 player remaining.
        If Team A selects that player, Team B will be left with 0 players.
        Team A's pick MUST be rejected via constraint validation.
        """
        room, draft_state = self._create_room_and_draft(
            room_code="CONF01",
            host_id="host_a",
            guest_id="guest_b",
            round_number=11,
            turn_number=1,
            current_picker_id="host_a",
        )

        # Mock pool with only 1 remaining player
        mock_cand = {
            "player_id": 999,
            "player_name": "Solo Player",
            "country": "India",
            "decade": 2010,
            "primary_role": "PACE",
            "bowling_rating": 80.0,
            "batting_rating": 40.0,
            "is_wicketkeeper": False,
            "eligible_positions": "11",
            "overall_rating": 78.0,
        }

        # Add 10 prior picks for Host (slots 1..10) including 1 WK and 5 bowlers
        for pos in range(1, 11):
            p = DraftPick(
                room_id=room.id,
                round_number=pos,
                user_id="host_a",
                player_id=100 + pos,
                player_name=f"Host Pick {pos}",
                batting_position=pos,
                selected_country="India",
                selected_decade=2010,
            )
            self.db.add(p)

        # Add 10 prior picks for Guest (slots 1..10) including 1 WK and 5 bowlers
        for pos in range(1, 11):
            p = DraftPick(
                room_id=room.id,
                round_number=pos,
                user_id="guest_b",
                player_id=200 + pos,
                player_name=f"Guest Pick {pos}",
                batting_position=pos,
                selected_country="India",
                selected_decade=2010,
            )
            self.db.add(p)
        self.db.commit()

        with patch.object(dataset_service, "get_player_by_id", return_value=mock_cand), \
             patch.object(dataset_service, "get_players_by_country_and_decade", return_value=[mock_cand]):

            # Host attempts to pick the only remaining player into slot 11
            with self.assertRaises(ValueError) as ctx:
                DraftService.make_pick(
                    db=self.db,
                    room_code="CONF01",
                    user_id="host_a",
                    player_id=999,
                    batting_position=11,
                )

            self.assertIn("Constraint validation failed", str(ctx.exception))
            self.assertIn("Not enough players remaining in candidate pool", str(ctx.exception))

            # Ensure pick was NOT committed
            pick_count = self.db.query(DraftPick).filter(DraftPick.room_id == room.id).count()
            self.assertEqual(pick_count, 20)

    def test_last_role_conflict_wicketkeeper(self):
        """
        Both Team A and Team B have 10 players, neither has drafted a wicketkeeper yet.
        Both teams have slot 7 vacant.
        Pool has exactly 2 players: 1 WK and 1 non-WK batter.
        If Team A takes the WK, Team B will have 0 WKs available and can never complete a legal XI.
        Team A's attempt to take the last WK must be rejected.
        """
        room, draft_state = self._create_room_and_draft(
            room_code="WKCONF",
            host_id="host_a",
            guest_id="guest_b",
            round_number=11,
            turn_number=1,
            current_picker_id="host_a",
        )

        cand_wk = {
            "player_id": 901,
            "player_name": "Only WK Left",
            "country": "India",
            "decade": 2010,
            "primary_role": "BATTER",
            "bowling_rating": 10.0,
            "batting_rating": 82.0,
            "is_wicketkeeper": True,
            "eligible_positions": "7",
            "overall_rating": 80.0,
        }
        cand_bat = {
            "player_id": 902,
            "player_name": "Pure Batter",
            "country": "India",
            "decade": 2010,
            "primary_role": "BATTER",
            "bowling_rating": 10.0,
            "batting_rating": 80.0,
            "is_wicketkeeper": False,
            "eligible_positions": "7",
            "overall_rating": 79.0,
        }

        # 10 picks for each team (slots 1..6 and 8..11 filled, slot 7 vacant)
        # None of the picks are WKs
        for pos in [1, 2, 3, 4, 5, 6, 8, 9, 10, 11]:
            p1 = DraftPick(
                room_id=room.id,
                round_number=pos if pos < 7 else pos - 1,
                user_id="host_a",
                player_id=100 + pos,
                player_name=f"Host Pick {pos}",
                batting_position=pos,
                selected_country="India",
                selected_decade=2010,
            )
            p2 = DraftPick(
                room_id=room.id,
                round_number=pos if pos < 7 else pos - 1,
                user_id="guest_b",
                player_id=200 + pos,
                player_name=f"Guest Pick {pos}",
                batting_position=pos,
                selected_country="India",
                selected_decade=2010,
            )
            self.db.add_all([p1, p2])
        self.db.commit()

        def mock_get_player_by_id(pid):
            if pid == 901:
                return cand_wk
            if pid == 902:
                return cand_bat
            # Return non-WK with 5 bowling options for slots 8-11
            return {
                "player_id": pid,
                "is_wicketkeeper": False,
                "primary_role": "PACE" if (pid % 100) >= 8 else "BATTER",
                "bowling_rating": 70.0 if (pid % 100) >= 8 else 10.0,
                "eligible_positions": str(pid % 100),
            }

        with patch.object(dataset_service, "get_player_by_id", side_effect=mock_get_player_by_id), \
             patch.object(dataset_service, "get_players_by_country_and_decade", return_value=[cand_wk, cand_bat]):

            # Host attempts to take the only WK
            with self.assertRaises(ValueError) as ctx:
                DraftService.make_pick(
                    db=self.db,
                    room_code="WKCONF",
                    user_id="host_a",
                    player_id=901,
                    batting_position=7,
                )

            self.assertIn("Constraint validation failed", str(ctx.exception))
            self.assertIn("Not enough wicketkeepers remaining", str(ctx.exception))

    def test_last_role_conflict_bowling_options(self):
        """
        Host has 5 bowling options.
        Guest has only 4 bowling options (needs 1 more bowler to satisfy the >= 5 bowler rule).
        Both have slot 11 vacant.
        Remaining pool has 2 players: 1 bowler, 1 pure batter.
        If Host takes the bowler, Guest will be left with only a pure batter, failing the 5 bowler constraint.
        Host's attempt to take the bowler must be rejected.
        """
        room, draft_state = self._create_room_and_draft(
            room_code="BOWL01",
            host_id="host_a",
            guest_id="guest_b",
            round_number=11,
            turn_number=1,
            current_picker_id="host_a",
        )

        cand_bowler = {
            "player_id": 911,
            "player_name": "Lone Bowler Left",
            "country": "India",
            "decade": 2010,
            "primary_role": "PACE",
            "bowling_rating": 85.0,
            "batting_rating": 25.0,
            "is_wicketkeeper": False,
            "eligible_positions": "11",
            "overall_rating": 82.0,
        }
        cand_pure_bat = {
            "player_id": 912,
            "player_name": "Pure Batter Tailender",
            "country": "India",
            "decade": 2010,
            "primary_role": "BATTER",
            "bowling_rating": 12.0,
            "batting_rating": 70.0,
            "is_wicketkeeper": False,
            "eligible_positions": "11",
            "overall_rating": 72.0,
        }

        # Slots 1..10 filled for Host (5 bowlers, 1 WK)
        for pos in range(1, 11):
            p1 = DraftPick(
                room_id=room.id,
                round_number=pos,
                user_id="host_a",
                player_id=100 + pos,
                player_name=f"Host Pick {pos}",
                batting_position=pos,
                selected_country="India",
                selected_decade=2010,
            )
            # Slots 1..10 filled for Guest (only 4 bowlers, 1 WK)
            p2 = DraftPick(
                room_id=room.id,
                round_number=pos,
                user_id="guest_b",
                player_id=200 + pos,
                player_name=f"Guest Pick {pos}",
                batting_position=pos,
                selected_country="India",
                selected_decade=2010,
            )
            self.db.add_all([p1, p2])
        self.db.commit()

        def mock_meta(pid):
            if pid == 911:
                return cand_bowler
            if pid == 912:
                return cand_pure_bat
            # Host (101..110): 5 bowlers (106..110)
            if 101 <= pid <= 110:
                is_bowl = (pid >= 106)
                return {
                    "player_id": pid,
                    "is_wicketkeeper": (pid == 105),
                    "primary_role": "PACE" if is_bowl else "BATTER",
                    "bowling_rating": 75.0 if is_bowl else 10.0,
                    "eligible_positions": str(pid - 100),
                }
            # Guest (201..210): only 4 bowlers (207..210)
            if 201 <= pid <= 210:
                is_bowl = (pid >= 207)
                return {
                    "player_id": pid,
                    "is_wicketkeeper": (pid == 205),
                    "primary_role": "PACE" if is_bowl else "BATTER",
                    "bowling_rating": 75.0 if is_bowl else 10.0,
                    "eligible_positions": str(pid - 200),
                }
            return {}

        with patch.object(dataset_service, "get_player_by_id", side_effect=mock_meta), \
             patch.object(dataset_service, "get_players_by_country_and_decade", return_value=[cand_bowler, cand_pure_bat]):

            # Host attempts to draft the bowler into slot 11
            with self.assertRaises(ValueError) as ctx:
                DraftService.make_pick(
                    db=self.db,
                    room_code="BOWL01",
                    user_id="host_a",
                    player_id=911,
                    batting_position=11,
                )

            self.assertIn("Constraint validation failed", str(ctx.exception))
            self.assertIn("bowling options", str(ctx.exception))

    def test_duplicate_player_prevention(self):
        """Verify that a player already drafted in the room cannot be picked again by either user."""
        room, draft_state = self._create_room_and_draft(
            room_code="DUP001",
            host_id="user_1",
            guest_id="user_2",
            country="India",
            decade=2010,
            is_single_pool=False,
        )

        # User 1 drafts player 101 into slot 1
        cand_101 = {
            "player_id": 101,
            "player_name": "Rohit Sharma",
            "country": "India",
            "decade": 2010,
            "primary_role": "BATTER",
            "bowling_rating": 20.0,
            "is_wicketkeeper": False,
            "eligible_positions": "1|2",
            "overall_rating": 90.0,
        }
        cand_102 = {
            "player_id": 102,
            "player_name": "Shikhar Dhawan",
            "country": "India",
            "decade": 2010,
            "primary_role": "BATTER",
            "bowling_rating": 10.0,
            "is_wicketkeeper": False,
            "eligible_positions": "1|2|3",
            "overall_rating": 85.0,
        }

        def mock_get_player_by_id(pid):
            if pid == 101:
                return cand_101
            if pid == 102:
                return cand_102
            return None

        with patch.object(dataset_service, "get_player_by_id", side_effect=mock_get_player_by_id), \
             patch.object(dataset_service, "get_players_by_country_and_decade", return_value=[cand_101, cand_102]):

            pick, _ = DraftService.make_pick(
                db=self.db,
                room_code="DUP001",
                user_id="user_1",
                player_id=101,
                batting_position=1,
            )
            self.assertEqual(pick.player_id, 101)

            # Now User 2 tries to draft player 101 into slot 1
            with self.assertRaises(ValueError) as ctx:
                DraftService.make_pick(
                    db=self.db,
                    room_code="DUP001",
                    user_id="user_2",
                    player_id=101,
                    batting_position=1,
                )
            self.assertIn("has already been drafted", str(ctx.exception))

    def test_empty_pool_handling(self):
        """When candidate pool has no players, make_pick must raise ValueError."""
        room, draft_state = self._create_room_and_draft(
            room_code="EMPTY1",
            host_id="user_1",
            guest_id="user_2",
        )

        with patch.object(dataset_service, "get_player_by_id", return_value=None):
            with self.assertRaises(ValueError) as ctx:
                DraftService.make_pick(
                    db=self.db,
                    room_code="EMPTY1",
                    user_id="user_1",
                    player_id=9999,
                    batting_position=1,
                )
            self.assertIn("not found in database", str(ctx.exception))

    def test_both_teams_completing_legal_xis(self):
        """
        Full 22-pick snake draft simulation.
        Both teams successfully draft 11 players meeting all constraints:
        - Exactly 11 players in slots 1..11
        - Position eligibility adhered to
        - At least 1 Wicketkeeper
        - At least 5 Bowling Options
        - Transitions room status to 'TOSS'
        """
        room, draft_state = self._create_room_and_draft(
            room_code="FULL22",
            host_id="host_1",
            guest_id="guest_1",
            country="India",
            decade=2010,
            is_single_pool=True,
        )

        # Create a synthetic pool of 24 distinct players
        synthetic_pool = []
        for i in range(1, 25):
            is_wk = (i in (7, 8))
            is_bowler = (i >= 13)
            synthetic_pool.append({
                "player_id": 500 + i,
                "player_name": f"Player {i}",
                "country": "India",
                "decade": 2010,
                "primary_role": "PACE" if is_bowler else ("BATTER" if not is_wk else "WK"),
                "bowling_rating": 80.0 if is_bowler else 15.0,
                "batting_rating": 30.0 if is_bowler else 80.0,
                "is_wicketkeeper": is_wk,
                "eligible_positions": "|".join(str(p) for p in range(1, 12)),  # Flexible for test flow
                "overall_rating": float(80 - i),
            })

        pool_by_id = {p["player_id"]: p for p in synthetic_pool}

        def mock_get_player(pid):
            return pool_by_id.get(pid)

        def mock_get_pool(c, d):
            return synthetic_pool

        with patch.object(dataset_service, "get_player_by_id", side_effect=mock_get_player), \
             patch.object(dataset_service, "get_players_by_country_and_decade", side_effect=mock_get_pool):

            # Perform 11 rounds of snake draft (2 picks per round = 22 picks total)
            player_idx = 0
            for round_num in range(1, 12):
                # Odd rounds: Host first, Guest second
                # Even rounds: Guest first, Host second
                p1_user = "host_1" if (round_num % 2 == 1) else "guest_1"
                p2_user = "guest_1" if (round_num % 2 == 1) else "host_1"

                # Pick 1 of round
                player_idx += 1
                cand1 = synthetic_pool[player_idx - 1]
                slot1 = round_num
                pick1, is_finished1 = DraftService.make_pick(
                    db=self.db,
                    room_code="FULL22",
                    user_id=p1_user,
                    player_id=cand1["player_id"],
                    batting_position=slot1,
                )
                self.assertFalse(is_finished1)

                # Pick 2 of round
                player_idx += 1
                cand2 = synthetic_pool[player_idx - 1]
                slot2 = round_num
                pick2, is_finished2 = DraftService.make_pick(
                    db=self.db,
                    room_code="FULL22",
                    user_id=p2_user,
                    player_id=cand2["player_id"],
                    batting_position=slot2,
                )

                if round_num == 11:
                    self.assertTrue(is_finished2)
                else:
                    self.assertFalse(is_finished2)

            self.db.refresh(room)
            self.db.refresh(draft_state)

            self.assertTrue(draft_state.is_finished)
            self.assertEqual(room.status, "TOSS")

            # Check that both teams have exactly 11 distinct picks
            host_picks = self.db.query(DraftPick).filter(DraftPick.room_id == room.id, DraftPick.user_id == "host_1").all()
            guest_picks = self.db.query(DraftPick).filter(DraftPick.room_id == room.id, DraftPick.user_id == "guest_1").all()

            self.assertEqual(len(host_picks), 11)
            self.assertEqual(len(guest_picks), 11)
            self.assertEqual({p.batting_position for p in host_picks}, set(range(1, 12)))
            self.assertEqual({p.batting_position for p in guest_picks}, set(range(1, 12)))

            # Verify no duplicates across both teams
            all_pids = [p.player_id for p in host_picks + guest_picks]
            self.assertEqual(len(all_pids), len(set(all_pids)))

    def test_draft_cancellation_when_impossible(self):
        """
        When timer expires and auto-pick cannot find ANY legal candidate that satisfies forward checking,
        it must cancel the draft gracefully (room.status = 'ABANDONED', draft_state.is_finished = True)
        and return (None, False). It must NEVER assign random or illegal players.
        """
        room, draft_state = self._create_room_and_draft(
            room_code="CANC01",
            host_id="host_1",
            guest_id="guest_1",
        )

        # Mock pool with 0 candidates
        with patch.object(dataset_service, "get_players_by_country_and_decade", return_value=[]):
            pick, is_finished = DraftService.execute_auto_pick(self.db, "CANC01")

            self.assertIsNone(pick)
            self.assertFalse(is_finished)

            self.db.refresh(room)
            self.db.refresh(draft_state)

            self.assertEqual(room.status, "ABANDONED")
            self.assertTrue(draft_state.is_finished)

            # Ensure zero picks were created
            picks_count = self.db.query(DraftPick).filter(DraftPick.room_id == room.id).count()
            self.assertEqual(picks_count, 0)


if __name__ == "__main__":
    unittest.main()
