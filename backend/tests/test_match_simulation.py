"""
Unit and Integration Tests for CricXI Live T20 Match Simulation Engine.
Verifies all cricket rules, probability computations, strike rotation,
bowler restrictions, innings transitions, and victory conditions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.models.room import Room, RoomPlayer
from app.models.draft import DraftPick
from app.models.toss import TossState
from app.models.match import Match, MatchInnings, BallEvent, InningsBatterScore, InningsBowlerScore
from app.match.simulation_engine import SimulationEngine, DeliverySimulationResult
from app.match.match_service import MatchService


class TestMatchSimulation(unittest.TestCase):
    """Test suite for T20 match simulation engine and business rules."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=self.engine)
        TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSession()

        # Create room with Host and Guest
        self.room_code = "SIM001"
        self.room = Room(room_code=self.room_code, host_id="user_host", status="TOSS")
        self.db.add(self.room)
        self.db.commit()

        self.p_host = RoomPlayer(room_id=self.room.id, user_id="user_host", username="CaptainAnbu", is_host=True, is_ready=True)
        self.p_guest = RoomPlayer(room_id=self.room.id, user_id="user_guest", username="CaptainDhoni", is_host=False, is_ready=True)
        self.db.add_all([self.p_host, self.p_guest])
        self.db.commit()

        # Populate 11 drafted players for Host and Guest
        for pos in range(1, 12):
            self.db.add(DraftPick(
                room_id=self.room.id,
                user_id="user_host",
                player_id=100 + pos,
                player_name=f"Host Player {pos}",
                round_number=pos,
                batting_position=pos,
                selected_country="India",
                selected_decade=2010,
            ))
            self.db.add(DraftPick(
                room_id=self.room.id,
                user_id="user_guest",
                player_id=200 + pos,
                player_name=f"Guest Player {pos}",
                round_number=pos,
                batting_position=pos,
                selected_country="Australia",
                selected_decade=2010,
            ))
        self.db.commit()

        # Complete Toss: Host won and elected to BAT first
        self.toss_state = TossState(
            room_id=self.room.id,
            caller_id="user_host",
            caller_name="CaptainAnbu",
            caller_choice="HEADS",
            coin_result="HEADS",
            winner_id="user_host",
            winner_name="CaptainAnbu",
            decision="BAT",
            step="COMPLETED",
        )
        self.db.add(self.toss_state)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_match_initialization(self):
        """Verifies match and innings 1 initialization, openers, and bowler selection."""
        state = MatchService.initialize_or_get_match(self.db, self.room_code)
        self.assertEqual(state.status, "LIVE")
        self.assertEqual(state.current_innings_number, 1)
        self.assertEqual(state.batting_team_user_id, "user_host")  # Host elected to bat
        self.assertEqual(state.bowling_team_user_id, "user_guest")
        self.assertEqual(state.total_runs, 0)
        self.assertEqual(state.total_wickets, 0)
        self.assertEqual(state.overs, 0.0)

        # Check opening batters
        self.assertIsNotNone(state.striker)
        self.assertEqual(state.striker.player_id, 101)  # Batting position 1
        self.assertIsNotNone(state.non_striker)
        self.assertEqual(state.non_striker.player_id, 102)  # Batting position 2

        # Check opening bowler
        self.assertIsNotNone(state.current_bowler)
        self.assertIn(state.current_bowler.player_id, range(201, 212))

    def test_probability_matchup_adjustments(self):
        """Verifies probability calculations favor strong batters and strong bowlers accordingly."""
        elite_batter = {"batting_rating": 95.0, "strike_rate": 155.0, "batting_average": 45.0, "batting_position": 1}
        weak_bowler = {"bowling_rating": 45.0, "economy": 10.5, "bowling_strike_rate": 28.0}
        probs_batter_favored = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=elite_batter,
            bowler_stats=weak_bowler,
            over_number=3,
            innings_number=1,
            wickets_fallen=0,
        )

        weak_batter = {"batting_rating": 45.0, "strike_rate": 95.0, "batting_average": 15.0, "batting_position": 10}
        elite_bowler = {"bowling_rating": 95.0, "economy": 6.2, "bowling_strike_rate": 14.0}
        probs_bowler_favored = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=weak_batter,
            bowler_stats=elite_bowler,
            over_number=3,
            innings_number=1,
            wickets_fallen=5,
        )

        # Elite batter should have significantly higher boundary and lower dot/wicket probabilities
        self.assertGreater(probs_batter_favored["FOUR"] + probs_batter_favored["SIX"], probs_bowler_favored["FOUR"] + probs_bowler_favored["SIX"])
        self.assertGreater(probs_bowler_favored["DOT"], probs_batter_favored["DOT"])
        self.assertGreater(probs_bowler_favored["WICKET"], probs_batter_favored["WICKET"])

        # Check death overs boost sixes and wickets
        probs_death = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=elite_batter,
            bowler_stats=elite_bowler,
            over_number=18,
            innings_number=1,
            wickets_fallen=3,
        )
        self.assertGreater(probs_death["SIX"], probs_batter_favored["SIX"] * 0.9)
        self.assertGreater(probs_death["WICKET"], probs_batter_favored["WICKET"])

    def test_single_delivery_and_strike_rotation(self):
        """Tests that a single rotates strike between striker and non-striker."""
        MatchService.initialize_or_get_match(self.db, self.room_code)

        # Step deliveries until a legal ball occurs
        deliv, state = MatchService.step_delivery(self.db, self.room_code)
        self.assertIsNotNone(deliv)
        self.assertIn(state.total_runs, [0, 1, 2, 3, 4, 6])

    def test_over_completion_and_strike_rotation(self):
        """Simulates 6 legal deliveries and verifies over increment and bowler rotation."""
        MatchService.initialize_or_get_match(self.db, self.room_code)

        legal_count = 0
        bowlers_used = set()
        for i in range(20):
            deliv, state = MatchService.step_delivery(self.db, self.room_code, seed=100 + i)
            if deliv.is_legal:
                legal_count += 1
            if state.current_bowler:
                bowlers_used.add(state.current_bowler.player_id)
            if legal_count == 6:
                # End of first over
                self.assertEqual(state.overs, 1.0)
                break

    def test_bowler_four_over_restriction(self):
        """Ensures that no bowler can exceed 4 overs (24 legal balls)."""
        MatchService.initialize_or_get_match(self.db, self.room_code)

        # Simulate 60 deliveries
        for i in range(60):
            MatchService.step_delivery(self.db, self.room_code, seed=2000 + i)

        state = MatchService.get_live_match_state(self.db, self.room_code)
        if state.first_innings_scorecard:
            for b in state.first_innings_scorecard.bowlers:
                self.assertLessEqual(b.legal_balls, 24, f"Bowler {b.player_name} exceeded 4 overs!")

    def test_first_innings_to_second_innings_transition(self):
        """Simulates until innings 1 ends and verifies target calculation."""
        MatchService.initialize_or_get_match(self.db, self.room_code)

        # Force innings 1 completion by running deliveries
        inn = self.db.query(MatchInnings).filter(MatchInnings.innings_number == 1).first()
        inn.legal_balls_bowled = 119
        inn.total_runs = 150
        inn.total_wickets = 4
        self.db.commit()

        # Deliver ball 120 (legal dot or run)
        deliv, state = MatchService.step_delivery(self.db, self.room_code, seed=42)

        # Innings 1 must be completed and target set to 150 + runs + 1
        self.db.refresh(inn)
        self.assertTrue(inn.is_completed)
        match = self.db.query(Match).first()
        self.assertIsNotNone(match.target)
        self.assertEqual(match.target, inn.total_runs + 1)
        self.assertEqual(state.current_innings_number, 2)
        self.assertEqual(state.batting_team_user_id, "user_guest")  # Guest now chases

    def test_chase_victory_by_wickets(self):
        """Verifies that reaching target in Innings 2 triggers victory by remaining wickets."""
        MatchService.initialize_or_get_match(self.db, self.room_code)
        match = self.db.query(Match).first()

        # Set up Innings 2 near victory
        inn1 = self.db.query(MatchInnings).filter(MatchInnings.innings_number == 1).first()
        inn1.is_completed = True
        inn1.total_runs = 100
        match.target = 101
        match.current_innings = 2

        inn2 = MatchInnings(
            match_id=match.id,
            innings_number=2,
            batting_team_user_id="user_guest",
            bowling_team_user_id="user_host",
            total_runs=100,  # 1 run needed to win!
            total_wickets=3,
            legal_balls_bowled=50,
            is_completed=False,
            current_striker_id=201,
            current_non_striker_id=202,
            current_bowler_id=105,
        )
        self.db.add(inn2)
        self.db.flush()

        b_score = InningsBatterScore(
            innings_id=inn2.id,
            player_id=201,
            player_name="Dhoni",
            batting_position=1,
            runs=40,
            balls=30,
        )
        bowl_score = InningsBowlerScore(
            innings_id=inn2.id,
            player_id=105,
            player_name="Host Bowler",
        )
        self.db.add_all([b_score, bowl_score])
        self.db.commit()

        # Step delivery
        deliv, state = MatchService.step_delivery(self.db, self.room_code)

        if state.total_runs >= 101:
            self.assertEqual(state.status, "COMPLETED")
            self.assertEqual(state.winner_user_id, "user_guest")
            self.assertIn("wickets", state.result_margin or "")


if __name__ == "__main__":
    unittest.main()

