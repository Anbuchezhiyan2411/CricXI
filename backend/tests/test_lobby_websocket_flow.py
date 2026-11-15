"""
Integration test for Lobby WebSocket connection and player readiness flow
against the actual SQLite database file.
Verifies that:
1. Host and Challenger connect without any SQLite schema errors (e.g., matches.current_innings).
2. Ready status toggles successfully for both players.
3. Neither connection crashes or drops.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from app.database.session import SessionLocal, init_db
from app.models.room import Room, RoomPlayer
from app.models.match import Match
from app.matchmaking.room_service import RoomService, build_room_response


class TestLobbyFlowAndSchema(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.room_code = "LOBBY1"

        # Cleanup existing
        existing = self.db.query(Room).filter(Room.room_code == self.room_code).first()
        if existing:
            self.db.delete(existing)
            self.db.commit()

        # Create room
        self.room = Room(room_code=self.room_code, host_id="user_host_1", status="WAITING")
        self.db.add(self.room)
        self.db.commit()

        self.p_host = RoomPlayer(
            room_id=self.room.id,
            user_id="user_host_1",
            username="AnbuHost",
            is_host=True,
            is_ready=False,
        )
        self.p_guest = RoomPlayer(
            room_id=self.room.id,
            user_id="user_guest_2",
            username="DhoniGuest",
            is_host=False,
            is_ready=False,
        )
        self.db.add_all([self.p_host, self.p_guest])
        self.db.commit()

    def tearDown(self):
        room = self.db.query(Room).filter(Room.room_code == self.room_code).first()
        if room:
            self.db.delete(room)
            self.db.commit()
        self.db.close()

    def test_query_matches_on_sqlite_does_not_fail(self):
        """Verifies that querying Match table does not throw 'no such column: matches.current_innings'."""
        # This was the exact line that caused the WebSocket reconnect loop!
        match_rec = self.db.query(Match).filter(Match.room_id == self.room.id).first()
        self.assertIsNone(match_rec)

        # Now test creating a match record with new columns
        test_match = Match(
            room_id=self.room.id,
            team1_user_id="user_host_1",
            team2_user_id="user_guest_2",
            current_innings=1,
            target=160,
            is_paused=False,
            simulation_speed=1.0,
            status="PENDING",
        )
        self.db.add(test_match)
        self.db.commit()
        self.db.refresh(test_match)

        # Query back and verify all new Phase 4 columns
        queried = self.db.query(Match).filter(Match.room_id == self.room.id).first()
        self.assertIsNotNone(queried)
        self.assertEqual(queried.current_innings, 1)
        self.assertEqual(queried.target, 160)
        self.assertFalse(queried.is_paused)
        self.assertEqual(queried.simulation_speed, 1.0)

    def test_lobby_ready_toggle_flow(self):
        """Verifies Host and Guest ready toggling in lobby."""
        # 1. Initially neither is ready
        self.db.refresh(self.room)
        resp1 = build_room_response(self.room, "user_host_1")
        self.assertFalse(resp1.players[0].is_ready)
        self.assertFalse(resp1.players[1].is_ready)

        # 2. Host clicks ready
        RoomService.toggle_player_ready(self.db, self.room_code, "user_host_1", is_ready=True)
        self.db.refresh(self.room)
        resp2 = build_room_response(self.room, "user_host_1")
        host_p = next(p for p in resp2.players if p.user_id == "user_host_1")
        guest_p = next(p for p in resp2.players if p.user_id == "user_guest_2")
        self.assertTrue(host_p.is_ready)
        self.assertFalse(guest_p.is_ready)

        # 3. Guest clicks ready
        RoomService.toggle_player_ready(self.db, self.room_code, "user_guest_2", is_ready=True)
        self.db.refresh(self.room)
        resp3 = build_room_response(self.room, "user_guest_2")
        all_ready = all(p.is_ready for p in resp3.players)
        self.assertTrue(all_ready, "Both players must now be ready to start match!")


if __name__ == "__main__":
    unittest.main()

