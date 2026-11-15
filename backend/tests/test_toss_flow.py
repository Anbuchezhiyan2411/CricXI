"""
Unit and Integration Tests for CricXI Cricket Toss Engine.
Tests complete toss lifecycle:
1. Validation of 11-player draft completion
2. Random caller selection via secrets.choice (persisted in SQLite)
3. Heads / Tails call authorization & coin flip simulation
4. Determination of toss winner
5. Toss winner Bat / Bowl decision
6. Match & room status transition to LIVE
"""

import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.models.room import Room, RoomPlayer
from app.models.draft import DraftPick
from app.models.toss import TossState
from app.models.match import Match
from app.toss.toss_service import TossService


class TestTossEngine(unittest.TestCase):
    """Test suite for TossService business logic and state machine."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=self.engine)
        TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSession()

    def tearDown(self):
        self.db.close()

    def test_toss_blocked_if_draft_incomplete(self):
        """Verify that toss initialization is blocked until draft has 11 players for both."""
        room = Room(room_code="TEST01", host_id="user_host", status="DRAFTING")
        self.db.add(room)
        self.db.commit()

        p1 = RoomPlayer(room_id=room.id, user_id="user_host", username="HostAnbu", is_host=True, is_ready=True)
        p2 = RoomPlayer(room_id=room.id, user_id="user_guest", username="GuestVirat", is_host=False, is_ready=True)
        self.db.add_all([p1, p2])
        self.db.commit()

        # Attempt to init toss when 0 picks exist
        state = TossService.initialize_or_get_toss(self.db, "TEST01", "user_host")
        self.assertFalse(state.draft_completed)
        self.assertIn("Host has drafted 0/11 players", state.message or "")

    def test_complete_toss_workflow(self):
        """Tests the entire authentic cricket toss ceremony end-to-end."""
        room = Room(room_code="TOSS01", host_id="host_1", status="DRAFTING")
        self.db.add(room)
        self.db.commit()

        p_host = RoomPlayer(room_id=room.id, user_id="host_1", username="CaptainAnbu", is_host=True, is_ready=True)
        p_guest = RoomPlayer(room_id=room.id, user_id="guest_2", username="CaptainDhoni", is_host=False, is_ready=True)
        self.db.add_all([p_host, p_guest])
        self.db.commit()

        # Populate 11 picks for Host and Guest (positions 1-11)
        for pos in range(1, 12):
            pick_h = DraftPick(
                room_id=room.id,
                user_id="host_1",
                player_id=100 + pos,
                player_name=f"Host Player {pos}",
                round_number=pos,
                batting_position=pos,
                selected_country="India",
                selected_decade=2010,
            )
            pick_g = DraftPick(
                room_id=room.id,
                user_id="guest_2",
                player_id=200 + pos,
                player_name=f"Guest Player {pos}",
                round_number=pos,
                batting_position=pos,
                selected_country="Australia",
                selected_decade=2010,
            )
            self.db.add_all([pick_h, pick_g])
        self.db.commit()

        # 1. Initialize toss
        toss_init = TossService.initialize_or_get_toss(self.db, "TOSS01", "host_1")
        self.assertTrue(toss_init.draft_completed)
        self.assertEqual(toss_init.step, "CALLING")
        self.assertIn(toss_init.caller_id, ("host_1", "guest_2"))
        caller_id = toss_init.caller_id
        opponent_id = "guest_2" if caller_id == "host_1" else "host_1"

        # Idempotence: initializing again should return the exact same caller
        toss_reinit = TossService.initialize_or_get_toss(self.db, "TOSS01", opponent_id)
        self.assertEqual(toss_reinit.caller_id, caller_id)

        # 2. Opponent tries to call Heads/Tails -> should raise PermissionError
        with self.assertRaises(PermissionError) as cm:
            TossService.make_call(self.db, "TOSS01", opponent_id, "HEADS")
        self.assertIn("Only the designated toss caller", str(cm.exception))

        # 3. Caller calls HEADS
        toss_after_call = TossService.make_call(self.db, "TOSS01", caller_id, "HEADS")
        self.assertEqual(toss_after_call.step, "DECIDING")
        self.assertEqual(toss_after_call.caller_choice, "HEADS")
        self.assertIn(toss_after_call.coin_result, ("HEADS", "TAILS"))

        winner_id = toss_after_call.winner_id
        loser_id = "guest_2" if winner_id == "host_1" else "host_1"

        if toss_after_call.coin_result == "HEADS":
            self.assertEqual(winner_id, caller_id)
        else:
            self.assertEqual(winner_id, opponent_id)

        # Caller tries to call again -> should raise ValueError (already flipped)
        with self.assertRaises(ValueError) as cm:
            TossService.make_call(self.db, "TOSS01", caller_id, "TAILS")
        self.assertIn("already been called and flipped", str(cm.exception))

        # 4. Loser tries to make Bat/Bowl decision -> should raise PermissionError
        with self.assertRaises(PermissionError) as cm:
            TossService.make_decision(self.db, "TOSS01", loser_id, "BAT")
        self.assertIn("Only the toss winner", str(cm.exception))

        # 5. Winner chooses to BAT first
        toss_completed = TossService.make_decision(self.db, "TOSS01", winner_id, "BAT")
        self.assertEqual(toss_completed.step, "COMPLETED")
        self.assertEqual(toss_completed.decision, "BAT")
        self.assertEqual(toss_completed.winner_id, winner_id)

        # Verify Room and Match state transitions in DB
        self.db.refresh(room)
        self.assertEqual(room.status, "LIVE")

        match = self.db.query(Match).filter(Match.room_id == room.id).first()
        self.assertIsNotNone(match)
        self.assertEqual(match.status, "LIVE")
        self.assertEqual(match.toss_winner_id, winner_id)
        self.assertEqual(match.toss_decision, "BAT")

        # Verify Innings 1 is initialized
        from app.models.match import MatchInnings
        inn1 = self.db.query(MatchInnings).filter(MatchInnings.match_id == match.id, MatchInnings.innings_number == 1).first()
        self.assertIsNotNone(inn1)
        self.assertEqual(inn1.batting_team_user_id, winner_id)
        self.assertIsNotNone(inn1.current_striker_id)
        self.assertIsNotNone(inn1.current_bowler_id)


if __name__ == "__main__":
    unittest.main()
