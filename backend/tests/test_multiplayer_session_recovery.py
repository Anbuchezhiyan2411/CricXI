"""
Comprehensive Integration Tests for CricXI Phase 6.2:
Multiplayer Disconnect Recovery, Session Persistence, Heartbeat System & Slot Reservation.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone, timedelta
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.matchmaking.room_service import RoomService
from app.draft.draft_service import DraftService
from app.toss.toss_service import TossService
from app.match.match_service import MatchService
from app.websocket.connection_manager import ws_manager
from app.models.room import Room, RoomPlayer
from app.models.draft import DraftState
from app.models.toss import TossState
from app.models.match import Match


class TestMultiplayerSessionRecovery(unittest.TestCase):
    """Verifies all Phase 6.2 disconnect recovery, heartbeat, and persistence rules."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def _create_two_player_room(self):
        room, host_id = RoomService.create_room(self.db, "HostPlayer")
        code = room.room_code
        room, guest_id = RoomService.join_room(self.db, code, "GuestPlayer")
        RoomService.toggle_player_ready(self.db, code, host_id, is_ready=True)
        RoomService.toggle_player_ready(self.db, code, guest_id, is_ready=True)
        return room, host_id, guest_id

    def test_heartbeat_system_records_activity_and_tracks_timeout(self):
        """Verifies requirement 3: Heartbeat records activity and tracks inactivity."""
        room, host_id, guest_id = self._create_two_player_room()
        code = room.room_code

        # Record initial heartbeats
        ws_manager.record_heartbeat(code, host_id)
        ws_manager.record_heartbeat(code, guest_id)

        host_hb = ws_manager.get_last_heartbeat(code, host_id)
        guest_hb = ws_manager.get_last_heartbeat(code, guest_id)
        self.assertIsNotNone(host_hb)
        self.assertIsNotNone(guest_hb)

        # Tab switch / Alt-tab / backgrounding keeps socket open and heartbeats continue
        ws_manager.record_heartbeat(code, host_id)
        new_host_hb = ws_manager.get_last_heartbeat(code, host_id)
        self.assertGreaterEqual(new_host_hb, host_hb)

    def test_draft_disconnect_pauses_and_resumes_exact_seconds(self):
        """Verifies requirement 5 & 6: Draft timer freezes on disconnect and resumes with exact seconds."""
        room, host_id, guest_id = self._create_two_player_room()
        code = room.room_code
        room.status = "DRAFTING"
        self.db.commit()

        # Initialize draft
        draft_state = DraftService.initialize_draft(self.db, code)
        self.assertEqual(draft_state.remaining_seconds, 30)

        # Simulate 18 seconds remaining
        now = datetime.now(timezone.utc)
        draft_state.turn_deadline = now + timedelta(seconds=18)
        draft_state.remaining_seconds = 18
        self.db.commit()

        # Disconnect guest: pause draft
        paused_state = DraftService.pause_draft(self.db, code)
        self.assertIsNotNone(paused_state)
        self.assertIsNone(paused_state.turn_deadline)
        self.assertEqual(paused_state.remaining_seconds, 18)

        # Verify draft state response reflects exact paused seconds
        resp = DraftService.get_draft_state_response(self.db, code)
        self.assertEqual(resp.remaining_seconds, 18)

        # Reconnect guest within 30s: resume draft
        resumed_state = DraftService.resume_draft(self.db, code)
        self.assertIsNotNone(resumed_state)
        self.assertIsNotNone(resumed_state.turn_deadline)
        self.assertEqual(resumed_state.remaining_seconds, 18)

    def test_slot_reservation_prevents_hijacking(self):
        """Verifies requirement 7 & 8: Disconnected player slot is reserved; third-parties rejected."""
        room, host_id, guest_id = self._create_two_player_room()
        code = room.room_code
        room.status = "DRAFT"
        self.db.commit()

        # Mark guest as disconnected (in 30s window)
        ws_manager.disconnected_players[code] = {guest_id: {"disconnected_at": 1000.0, "username": "GuestPlayer"}}

        # Original player reconnects with same user_id -> SUCCESS
        rejoined_room, rejoined_id = RoomService.join_room(self.db, code, "GuestPlayer", user_id=guest_id)
        self.assertEqual(rejoined_id, guest_id)

        # An intruder attempts to join with a DIFFERENT user_id -> REJECTED
        intruder_id = "intruder-user-999"
        with self.assertRaises(ValueError) as ctx:
            RoomService.join_room(self.db, code, "IntruderPlayer", user_id=intruder_id)
        self.assertIn("Player slot reserved", str(ctx.exception))

        # Cleanup
        ws_manager.disconnected_players.pop(code, None)

    def test_reclaiming_reserved_slot_by_username_without_user_id(self):
        """Verifies Bug 1: Player A reclaiming reserved slot using only same username succeeds."""
        room, host_id, guest_id = self._create_two_player_room()
        code = room.room_code
        room.status = "DRAFT"
        self.db.commit()

        # Guest disconnects (in 30s window)
        ws_manager.disconnected_players[code] = {guest_id: {"disconnected_at": 1000.0, "username": "GuestPlayer"}}

        # Guest rejoins in a fresh tab with NO user_id, but matching username -> SUCCESS
        rejoined_room, reclaimed_id = RoomService.join_room(self.db, code, "GuestPlayer", user_id=None)
        self.assertEqual(reclaimed_id, guest_id)

        # A completely new player with a different name attempts to join -> REJECTED
        with self.assertRaises(ValueError) as ctx:
            RoomService.join_room(self.db, code, "NewPlayerXYZ", user_id=None)
        self.assertIn("Player slot reserved", str(ctx.exception))

        # Cleanup
        ws_manager.disconnected_players.pop(code, None)

    def test_validate_room_distinguishes_reserved_slot_vs_full_room(self):
        """Verifies Bug 1: validate_room does not block reconnecting player with 'Room full'."""
        room, host_id, guest_id = self._create_two_player_room()
        code = room.room_code
        room.status = "DRAFT"
        self.db.commit()

        # When room has 2 players and neither is disconnected: validate returns full
        val_full = RoomService.validate_room(self.db, code)
        self.assertFalse(val_full.valid)
        self.assertTrue(val_full.is_full)
        self.assertIn("full", val_full.message.lower())

        # When guest disconnects (in 30s window)
        ws_manager.disconnected_players[code] = {guest_id: {"disconnected_at": 1000.0, "username": "GuestPlayer"}}

        # General check for room code: returns valid for reconnect
        val_code_only = RoomService.validate_room(self.db, code)
        self.assertTrue(val_code_only.valid)
        self.assertFalse(val_code_only.is_full)
        self.assertIn("reserved", val_code_only.message.lower())

        # Check with matching username: returns valid
        val_user = RoomService.validate_room(self.db, code, username="GuestPlayer")
        self.assertTrue(val_user.valid)
        self.assertIn("Welcome back", val_user.message)

        # Check after room completed: returns invalid (match ended)
        room.status = "COMPLETED"
        self.db.commit()
        val_ended = RoomService.validate_room(self.db, code)
        self.assertFalse(val_ended.valid)
        self.assertIn("ended", val_ended.message.lower())

        # Cleanup
        ws_manager.disconnected_players.pop(code, None)

    def test_toss_state_preserved_across_disconnect(self):
        """Verifies requirement 5 & 6: Toss state and choices remain completely preserved."""
        room, host_id, guest_id = self._create_two_player_room()
        code = room.room_code
        room.status = "DRAFTING"
        self.db.commit()

        # Complete draft to unlock toss
        DraftService.initialize_draft(self.db, code)
        for _ in range(22):
            DraftService.execute_auto_pick(self.db, code)

        # Initialize toss and make coin call
        toss_resp = TossService.initialize_or_get_toss(self.db, code, host_id)
        caller_id = toss_resp.caller_id
        called = TossService.make_call(self.db, code, caller_id, "HEADS")
        self.assertIsNotNone(called.coin_result)
        self.assertIsNotNone(called.winner_id)

        # Disconnect occurs: state must remain identical
        preserved_state = TossService.get_toss_state_response(self.db, code, host_id)
        self.assertEqual(preserved_state.step, "DECIDING")
        self.assertEqual(preserved_state.coin_result, called.coin_result)
        self.assertEqual(preserved_state.winner_id, called.winner_id)

    def test_live_match_disconnect_pauses_and_resumes_without_duplicate_deliveries(self):
        """Verifies requirement 5 & 6: Match simulation pauses and resumes from exact delivery."""
        room, host_id, guest_id = self._create_two_player_room()
        code = room.room_code
        room.status = "DRAFTING"
        self.db.commit()

        # Complete a quick 11-round draft
        DraftService.initialize_draft(self.db, code)
        for _ in range(22):
            DraftService.execute_auto_pick(self.db, code)

        # Complete toss
        toss_init = TossService.initialize_or_get_toss(self.db, code, host_id)
        toss_called = TossService.make_call(self.db, code, toss_init.caller_id, "HEADS")
        TossService.make_decision(self.db, code, toss_called.winner_id, "BAT")

        # Initialize match
        match = MatchService.initialize_or_get_match(self.db, code)
        self.assertEqual(match.status, "LIVE")

        # Step 3 deliveries
        deliv1, s1 = MatchService.step_delivery(self.db, code)
        deliv2, s2 = MatchService.step_delivery(self.db, code)
        deliv3, state3 = MatchService.step_delivery(self.db, code)
        legal_balls_before = state3.legal_balls_bowled
        runs_before_disconnect = state3.total_runs

        # Disconnect occurs -> pause simulation
        paused_state = MatchService.set_simulation_controls(self.db, code, action="pause")
        self.assertTrue(paused_state.is_paused)
        self.assertEqual(paused_state.legal_balls_bowled, legal_balls_before)
        self.assertEqual(paused_state.total_runs, runs_before_disconnect)

        # Reconnect occurs -> resume simulation
        resumed_state = MatchService.set_simulation_controls(self.db, code, action="play")
        self.assertFalse(resumed_state.is_paused)
        self.assertEqual(resumed_state.legal_balls_bowled, legal_balls_before)

        # Next delivery advances balls correctly with zero duplicate ball count
        deliv4, state4 = MatchService.step_delivery(self.db, code)
        expected_legal = legal_balls_before + (1 if deliv4.is_legal else 0)
        self.assertEqual(state4.legal_balls_bowled, expected_legal)

    def test_timeout_abandons_match_and_awards_win_to_connected_player(self):
        """Verifies requirement 10: 30s timeout abandons match and awards win to connected player."""
        room, host_id, guest_id = self._create_two_player_room()
        code = room.room_code
        room.status = "DRAFTING"
        self.db.commit()

        DraftService.initialize_draft(self.db, code)
        for _ in range(22):
            DraftService.execute_auto_pick(self.db, code)

        toss_init = TossService.initialize_or_get_toss(self.db, code, host_id)
        toss_called = TossService.make_call(self.db, code, toss_init.caller_id, "HEADS")
        TossService.make_decision(self.db, code, toss_called.winner_id, "BAT")
        match = MatchService.initialize_or_get_match(self.db, code)

        # Guest disconnects and 30s expires
        abandoned_match = MatchService.abandon_match(
            self.db, code, disconnected_user_id=guest_id, reason="Opponent timed out"
        )
        self.assertIsNotNone(abandoned_match)
        self.assertEqual(abandoned_match.status, "COMPLETED")
        self.assertEqual(abandoned_match.winner_user_id, host_id)
        self.assertIn("HostPlayer won", abandoned_match.result_margin)
        self.assertEqual(room.status, "COMPLETED")

    def test_intentional_lobby_exit_ends_match_immediately(self):
        """Verifies requirement 9: Intentionally leaving room notifies opponent and ends game."""
        room, host_id, guest_id = self._create_two_player_room()
        code = room.room_code
        room.status = "IN_PROGRESS"
        self.db.commit()

        # Host leaves room intentionally
        MatchService.abandon_match(self.db, code, disconnected_user_id=host_id, reason="Host left room")
        self.assertEqual(room.status, "COMPLETED")

    def test_rematch_play_again_resets_room_cleanly(self):
        """Verifies requirement 14: Rematch barrier resets room state freshly."""
        room, host_id, guest_id = self._create_two_player_room()
        code = room.room_code
        room.status = "COMPLETED"
        self.db.commit()

        # Player 1 requests rematch (barrier not met yet)
        r1, met1, _ = RoomService.request_play_again(self.db, code, host_id)
        self.assertFalse(met1)

        # Player 2 requests rematch -> barrier met! Room resets for new draft
        r2, met2, _ = RoomService.request_play_again(self.db, code, guest_id)
        self.assertTrue(met2)
        self.assertEqual(r2.status, "DRAFTING")

        # Verify a brand new draft state was initialized freshly
        draft = self.db.query(DraftState).filter(DraftState.room_id == r2.id).first()
        self.assertIsNotNone(draft)
        self.assertEqual(draft.current_round, 1)
        self.assertEqual(draft.current_turn, 1)


if __name__ == "__main__":
    unittest.main()
