"""
Unit and Integration Tests for 'Play Another Match' / Rematch synchronization flow.
Verifies:
1. Play Another Match generates a brand new Room and DraftState.
2. The new draft starts at Round 1, Turn 1 with is_finished=False and 0 picks.
3. Timer resets to 30s.
4. Candidates pool is freshly generated.
5. Old picks and draft state are never leaked or reused.
6. The REST API endpoint /api/rooms/{room_code}/play-again works end-to-end.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import unittest
from unittest.mock import patch, AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.models.room import Room, RoomPlayer
from app.models.draft import DraftState, DraftPick
from app.draft.draft_manager import DraftManager, draft_manager
from app.matchmaking.room_service import RoomService
from app.draft.draft_service import DraftService
from app.schemas.room import RoomPlayAgain
from app.api.routers.rooms import play_again as play_again_route
from app.websocket.connection_manager import ws_manager


class TestPlayAgainFlow(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSession()

        from app.matchmaking.room_service import _rematch_ready
        _rematch_ready.clear()

        # Create Match 1 room
        self.room_code = "OLD001"
        self.host_id = "host_uid_100"
        self.guest_id = "guest_uid_200"

        room = Room(room_code=self.room_code, host_id=self.host_id, status="COMPLETED")
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        self.old_room = room

        p1 = RoomPlayer(
            room_id=room.id,
            user_id=self.host_id,
            username="AliceHost",
            is_host=True,
            is_ready=False,
        )
        p2 = RoomPlayer(
            room_id=room.id,
            user_id=self.guest_id,
            username="BobGuest",
            is_host=False,
            is_ready=False,
        )
        self.db.add_all([p1, p2])
        self.db.commit()

        # Simulate Match 1 completed draft state (finished with picks)
        finished_draft = DraftState(
            room_id=room.id,
            current_round=11,
            current_turn=2,
            current_picker_id=self.guest_id,
            round_country="India",
            round_decade=2010,
            remaining_seconds=0,
            is_finished=True,
        )
        self.db.add(finished_draft)

        # Add 22 simulated picks for Match 1
        for i in range(1, 12):
            self.db.add(
                DraftPick(
                    room_id=room.id,
                    round_number=i,
                    user_id=self.host_id,
                    player_id=100 + i,
                    player_name=f"HostPlayer{i}",
                    batting_position=i,
                    selected_country="India",
                    selected_decade=2010,
                )
            )
            self.db.add(
                DraftPick(
                    room_id=room.id,
                    round_number=i,
                    user_id=self.guest_id,
                    player_id=200 + i,
                    player_name=f"GuestPlayer{i}",
                    batting_position=i,
                    selected_country="India",
                    selected_decade=2010,
                )
            )
        self.db.commit()

    def tearDown(self):
        from app.matchmaking.room_service import _rematch_ready
        _rematch_ready.clear()
        self.db.close()

    @patch.object(DraftManager, "start_room_timer")
    def test_multiplayer_ready_barrier_and_same_room_code_reuse(self, mock_start_timer):
        """
        Verify the mutual ready check barrier:
        - When Host clicks: barrier not met, room not reset.
        - When Guest clicks: barrier met, room code reused, state wiped, fresh Round 1 draft created.
        """
        # Step 1: Host clicks Play Again
        room, is_met, ready_ids = RoomService.request_play_again(
            self.db, self.room_code, self.host_id
        )
        self.assertFalse(is_met)
        self.assertEqual(ready_ids, [self.host_id])
        # Room is NOT reset yet
        picks_mid = self.db.query(DraftPick).filter(DraftPick.room_id == room.id).all()
        self.assertEqual(len(picks_mid), 22)
        self.assertEqual(room.status, "COMPLETED")

        # Step 2: Guest clicks Play Again -> Barrier met!
        room, is_met, ready_ids = RoomService.request_play_again(
            self.db, self.room_code, self.guest_id
        )
        self.assertTrue(is_met)
        self.assertEqual(len(ready_ids), 2)
        # Verify EXACT SAME room code is reused (DO NOT create a new room code)
        self.assertEqual(room.room_code, self.room_code)
        self.assertEqual(room.status, "DRAFTING")
        self.assertEqual(room.current_round, 1)

        # Verify old draft picks are completely wiped
        new_picks = self.db.query(DraftPick).filter(DraftPick.room_id == room.id).all()
        self.assertEqual(len(new_picks), 0)

        # Verify fresh Round 1 DraftState created
        draft_state = self.db.query(DraftState).filter(DraftState.room_id == room.id).first()
        self.assertIsNotNone(draft_state)
        self.assertEqual(draft_state.current_round, 1)
        self.assertEqual(draft_state.current_turn, 1)
        self.assertFalse(draft_state.is_finished)
        self.assertEqual(draft_state.remaining_seconds, 30)

        # Check candidate pool for the fresh draft
        resp = DraftService.get_draft_state_response(self.db, self.room_code)
        self.assertEqual(resp.current_round, 1)
        self.assertEqual(resp.current_turn, 1)
        self.assertFalse(resp.is_finished)
        self.assertGreaterEqual(len(resp.candidates), 11)
        self.assertEqual(resp.host_squad.picked_count, 0)
        self.assertEqual(resp.guest_squad.picked_count, 0)

    def test_play_again_api_endpoint_barrier(self):
        """Verify the /api/rooms/{code}/play-again endpoint with barrier."""
        mock_ws = AsyncMock()

        with patch.object(draft_manager, "start_room_timer"), \
             patch.object(DraftManager, "start_room_timer"):
            res1 = asyncio.run(
                play_again_route(
                    room_code=self.room_code,
                    payload=RoomPlayAgain(user_id=self.host_id),
                    db=self.db,
                    ws_manager=mock_ws,
                )
            )
            self.assertTrue(res1.success)
            self.assertFalse(res1.data.is_barrier_met)
            self.assertEqual(res1.data.new_room_code, self.room_code)
            self.assertEqual(res1.data.ready_user_ids, [self.host_id])

            res2 = asyncio.run(
                play_again_route(
                    room_code=self.room_code,
                    payload=RoomPlayAgain(user_id=self.guest_id),
                    db=self.db,
                    ws_manager=mock_ws,
                )
            )
            self.assertTrue(res2.success)
            self.assertTrue(res2.data.is_barrier_met)
            self.assertEqual(res2.data.new_room_code, self.room_code)
            self.assertEqual(res2.data.room.status, "DRAFTING")
            self.assertIsNotNone(res2.data.draft_state)
            self.assertEqual(res2.data.draft_state["current_round"], 1)

    def test_reset_room_for_new_match(self):
        """Verify RoomService.reset_room_for_new_match completely wipes old match/draft data."""
        RoomService.reset_room_for_new_match(self.db, self.room_code)

        remaining_picks = self.db.query(DraftPick).filter(DraftPick.room_id == self.old_room.id).all()
        self.assertEqual(len(remaining_picks), 0)

        remaining_draft = self.db.query(DraftState).filter(DraftState.room_id == self.old_room.id).first()
        self.assertIsNone(remaining_draft)


if __name__ == "__main__":
    unittest.main()
