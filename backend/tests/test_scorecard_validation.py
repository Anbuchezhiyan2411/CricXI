"""
Comprehensive Validation Tests for CricXI Phase 4.1:
Match Scorecards, Statistics Reconciliation, Historical Era Display, and Cricket Rules.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.models.room import Room, RoomPlayer
from app.models.draft import DraftPick
from app.models.toss import TossState
from app.models.match import Match, MatchInnings, BallEvent, InningsBatterScore, InningsBowlerScore
from app.match.simulation_engine import DeliverySimulationResult
from app.match.match_service import MatchService


class TestScorecardValidation(unittest.TestCase):
    """Rigorous scorecard and cricket statistics validation suite."""

    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=self.engine)
        TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = TestingSession()

        # Create room with Host and Guest
        self.room_code = "SCVAL1"
        self.room = Room(room_code=self.room_code, host_id="user_host", status="TOSS")
        self.db.add(self.room)
        self.db.commit()

        self.p_host = RoomPlayer(room_id=self.room.id, user_id="user_host", username="HostCaptain", is_host=True, is_ready=True)
        self.p_guest = RoomPlayer(room_id=self.room.id, user_id="user_guest", username="GuestCaptain", is_host=False, is_ready=True)
        self.db.add_all([self.p_host, self.p_guest])
        self.db.commit()

        # Complete Toss: Host won and elected to BAT first
        self.toss_state = TossState(
            room_id=self.room.id,
            caller_id="user_host",
            caller_name="HostCaptain",
            caller_choice="HEADS",
            coin_result="HEADS",
            winner_id="user_host",
            winner_name="HostCaptain",
            decision="BAT",
            step="COMPLETED",
        )
        self.db.add(self.toss_state)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _setup_teams(self, host_picks_data, guest_picks_data):
        """Helper to populate draft picks."""
        for pick in host_picks_data:
            self.db.add(DraftPick(
                room_id=self.room.id,
                user_id="user_host",
                player_id=pick["player_id"],
                player_name=pick["player_name"],
                round_number=pick["batting_position"],
                batting_position=pick["batting_position"],
                selected_country="Afghanistan",
                selected_decade=pick.get("decade", 2010),
            ))
        for pick in guest_picks_data:
            self.db.add(DraftPick(
                room_id=self.room.id,
                user_id="user_guest",
                player_id=pick["player_id"],
                player_name=pick["player_name"],
                round_number=pick["batting_position"],
                batting_position=pick["batting_position"],
                selected_country="Australia",
                selected_decade=pick.get("decade", 2010),
            ))
        self.db.commit()

    def test_duplicate_player_names_with_different_ids(self):
        """
        BUG 1: Ensure identical player names from different historical eras
        (e.g., Rashid Khan [id=10, 2010] and Rashid Khan [id=22, 2020])
        are treated as separate players and aggregated strictly by player_id.
        """
        host_picks = [
            {"player_id": 10, "player_name": "Rashid Khan", "batting_position": 1, "decade": 2010},
            {"player_id": 22, "player_name": "Rashid Khan", "batting_position": 2, "decade": 2020},
        ] + [
            {"player_id": 100 + i, "player_name": f"Host Batter {i}", "batting_position": i, "decade": 2010}
            for i in range(3, 12)
        ]
        guest_picks = [
            {"player_id": 200 + i, "player_name": f"Guest Player {i}", "batting_position": i, "decade": 2010}
            for i in range(1, 12)
        ]
        self._setup_teams(host_picks, guest_picks)

        state = MatchService.initialize_or_get_match(self.db, self.room_code)
        self.assertIsNotNone(state.striker)
        self.assertIsNotNone(state.non_striker)
        self.assertEqual(state.striker.player_id, 10)
        self.assertEqual(state.non_striker.player_id, 22)
        self.assertEqual(state.striker.player_name, "Rashid Khan")
        self.assertEqual(state.non_striker.player_name, "Rashid Khan")
        self.assertEqual(state.striker.decade, 2010)
        self.assertEqual(state.non_striker.decade, 2020)

        # Check scorecard has both distinct entries
        inn1_card = state.first_innings_scorecard
        self.assertIsNotNone(inn1_card)
        rashid_entries = [b for b in inn1_card.batters if b.player_name == "Rashid Khan"]
        self.assertEqual(len(rashid_entries), 2)
        self.assertEqual({b.player_id for b in rashid_entries}, {10, 22})
        self.assertEqual({b.decade for b in rashid_entries}, {2010, 2020})

    def test_team_wickets_strictly_matches_dismissed_batters(self):
        """
        BUG 2: Verify total team wickets strictly equals the number of batters with is_out=True.
        Dismissed batter must NEVER be returned to the crease in the same innings,
        and next batters must enter the crease in order.
        """
        host_picks = [
            {"player_id": 100 + i, "player_name": f"Batter {i}", "batting_position": i, "decade": 2010}
            for i in range(1, 12)
        ]
        guest_picks = [
            {"player_id": 200 + i, "player_name": f"Bowler {i}", "batting_position": i, "decade": 2010}
            for i in range(1, 12)
        ]
        self._setup_teams(host_picks, guest_picks)

        MatchService.initialize_or_get_match(self.db, self.room_code)

        # Force delivery 1: Wicket (Bowled)
        wicket_res_1 = DeliverySimulationResult(
            outcome="WICKET",
            batter_runs=0,
            extras=0,
            extra_type=None,
            is_legal=True,
            is_wicket=True,
            wicket_type="Bowled",
            runs_scored=0,
            strike_changed=False,
            commentary="Clean bowled!",
            short_display="W",
        )
        with patch("app.match.simulation_engine.SimulationEngine.simulate_delivery", return_value=wicket_res_1):
            MatchService.step_delivery(self.db, self.room_code)

        # After 1st wicket:
        # Batter 1 is out. Incoming striker MUST be Batter 3!
        state_1 = MatchService.get_live_match_state(self.db, self.room_code)
        self.assertEqual(state_1.total_wickets, 1)
        self.assertEqual(state_1.striker.player_id, 103)
        self.assertEqual(state_1.non_striker.player_id, 102)

        card_1 = state_1.first_innings_scorecard
        out_batters_1 = [b for b in card_1.batters if b.is_out]
        self.assertEqual(len(out_batters_1), 1)
        self.assertEqual(out_batters_1[0].player_id, 101)
        self.assertTrue(out_batters_1[0].dismissal_text.startswith("b "))

        # Force delivery 2: Wicket (Caught) - Batter 3 is now on strike and gets out
        wicket_res_2 = DeliverySimulationResult(
            outcome="WICKET",
            batter_runs=0,
            extras=0,
            extra_type=None,
            is_legal=True,
            is_wicket=True,
            wicket_type="Caught",
            runs_scored=0,
            strike_changed=False,
            commentary="Caught at long-on!",
            short_display="W",
        )
        with patch("app.match.simulation_engine.SimulationEngine.simulate_delivery", return_value=wicket_res_2):
            MatchService.step_delivery(self.db, self.room_code)

        # After 2nd wicket:
        # Batter 3 is out. Incoming striker MUST be Batter 4!
        state_2 = MatchService.get_live_match_state(self.db, self.room_code)
        self.assertEqual(state_2.total_wickets, 2)
        self.assertEqual(state_2.striker.player_id, 104)
        self.assertEqual(state_2.non_striker.player_id, 102)

        card_2 = state_2.first_innings_scorecard
        out_batters_2 = [b for b in card_2.batters if b.is_out]
        self.assertEqual(len(out_batters_2), 2)
        self.assertEqual({b.player_id for b in out_batters_2}, {101, 103})
        self.assertEqual(len(out_batters_2), state_2.total_wickets)

    def test_batting_status_tri_state_out_not_out_dnb(self):
        """
        BUG 3: Verify the tri-state display:
        - Dismissed batters: OUT
        - Undefeated batters at crease: NOT OUT (at most 2)
        - Batters who never entered the crease: DNB (Did Not Bat)
        Total: OUT + NOT OUT + DNB == 11.
        """
        host_picks = [
            {"player_id": 100 + i, "player_name": f"Batter {i}", "batting_position": i, "decade": 2010}
            for i in range(1, 12)
        ]
        guest_picks = [
            {"player_id": 200 + i, "player_name": f"Bowler {i}", "batting_position": i, "decade": 2010}
            for i in range(1, 12)
        ]
        self._setup_teams(host_picks, guest_picks)

        MatchService.initialize_or_get_match(self.db, self.room_code)

        # Before any wicket:
        # 2 not out (openers), 9 DNB, 0 out
        init_state = MatchService.get_live_match_state(self.db, self.room_code)
        init_card = init_state.first_innings_scorecard
        outs = [b for b in init_card.batters if b.batting_status == "OUT"]
        not_outs = [b for b in init_card.batters if b.batting_status == "NOT_OUT"]
        dnbs = [b for b in init_card.batters if b.batting_status == "DNB"]
        self.assertEqual(len(outs), 0)
        self.assertEqual(len(not_outs), 2)
        self.assertEqual(len(dnbs), 9)
        self.assertEqual(len(outs) + len(not_outs) + len(dnbs), 11)

        # Simulate 2 wickets
        wicket_res = DeliverySimulationResult(
            outcome="WICKET",
            batter_runs=0,
            extras=0,
            extra_type=None,
            is_legal=True,
            is_wicket=True,
            wicket_type="Bowled",
            runs_scored=0,
            strike_changed=False,
            commentary="Bowled!",
            short_display="W",
        )
        with patch("app.match.simulation_engine.SimulationEngine.simulate_delivery", return_value=wicket_res):
            MatchService.step_delivery(self.db, self.room_code)
            MatchService.step_delivery(self.db, self.room_code)

        mid_state = MatchService.get_live_match_state(self.db, self.room_code)
        mid_card = mid_state.first_innings_scorecard
        outs = [b for b in mid_card.batters if b.batting_status == "OUT"]
        not_outs = [b for b in mid_card.batters if b.batting_status == "NOT_OUT"]
        dnbs = [b for b in mid_card.batters if b.batting_status == "DNB"]

        self.assertEqual(len(outs), 2)
        self.assertEqual(len(not_outs), 2)  # pos 2 and pos 4
        self.assertEqual(len(dnbs), 7)     # pos 5 to 11
        self.assertEqual(len(outs) + len(not_outs) + len(dnbs), 11)

    def test_batting_scorecard_and_extras_reconciliation(self):
        """
        BUG 4: Verify delivery reconciliation:
        1. Batter runs + extras == team total
        2. Balls faced counts legal deliveries + byes + leg-byes + no-balls; Wides do NOT count.
        3. 4s and 6s reconcile with BallEvents.
        """
        host_picks = [
            {"player_id": 100 + i, "player_name": f"Batter {i}", "batting_position": i, "decade": 2010}
            for i in range(1, 12)
        ]
        guest_picks = [
            {"player_id": 200 + i, "player_name": f"Bowler {i}", "batting_position": i, "decade": 2010}
            for i in range(1, 12)
        ]
        self._setup_teams(host_picks, guest_picks)

        MatchService.initialize_or_get_match(self.db, self.room_code)

        # Delivery 1: Wide (1 run extra, not faced by batter)
        wide_res = DeliverySimulationResult(
            outcome="DOT",
            batter_runs=0,
            extras=1,
            extra_type="WIDE",
            is_legal=False,
            is_wicket=False,
            wicket_type=None,
            runs_scored=1,
            strike_changed=False,
            commentary="Wide ball down leg",
            short_display="Wd",
        )
        with patch("app.match.simulation_engine.SimulationEngine.simulate_delivery", return_value=wide_res):
            MatchService.step_delivery(self.db, self.room_code)

        state = MatchService.get_live_match_state(self.db, self.room_code)
        striker = state.striker
        self.assertEqual(striker.balls, 0)  # Wide does NOT count as ball faced!
        self.assertEqual(striker.runs, 0)
        self.assertEqual(state.total_runs, 1)

        # Delivery 2: No Ball with 2 runs off the bat (1 extra + 2 batter runs = 3 runs)
        nb_res = DeliverySimulationResult(
            outcome="2",
            batter_runs=2,
            extras=1,
            extra_type="NO_BALL",
            is_legal=False,
            is_wicket=False,
            wicket_type=None,
            runs_scored=3,
            strike_changed=False,
            commentary="No ball! Front foot overstep, hit for two.",
            short_display="Nb",
        )
        with patch("app.match.simulation_engine.SimulationEngine.simulate_delivery", return_value=nb_res):
            MatchService.step_delivery(self.db, self.room_code)

        state = MatchService.get_live_match_state(self.db, self.room_code)
        striker = state.striker
        self.assertEqual(striker.balls, 1)  # No-ball counts as ball faced!
        self.assertEqual(striker.runs, 2)
        self.assertEqual(state.total_runs, 4)

        # Delivery 3: Boundary (FOUR)
        four_res = DeliverySimulationResult(
            outcome="FOUR",
            batter_runs=4,
            extras=0,
            extra_type=None,
            is_legal=True,
            is_wicket=False,
            wicket_type=None,
            runs_scored=4,
            strike_changed=False,
            commentary="Cracking cover drive for four!",
            short_display="4",
        )
        with patch("app.match.simulation_engine.SimulationEngine.simulate_delivery", return_value=four_res):
            MatchService.step_delivery(self.db, self.room_code)

        state = MatchService.get_live_match_state(self.db, self.room_code)
        striker = state.striker
        self.assertEqual(striker.balls, 2)
        self.assertEqual(striker.runs, 6)
        self.assertEqual(striker.fours, 1)
        self.assertEqual(state.total_runs, 8)

        # Delivery 4: Boundary (SIX)
        six_res = DeliverySimulationResult(
            outcome="SIX",
            batter_runs=6,
            extras=0,
            extra_type=None,
            is_legal=True,
            is_wicket=False,
            wicket_type=None,
            runs_scored=6,
            strike_changed=False,
            commentary="Dispatched into the stands for SIX!",
            short_display="6",
        )
        with patch("app.match.simulation_engine.SimulationEngine.simulate_delivery", return_value=six_res):
            MatchService.step_delivery(self.db, self.room_code)

        state = MatchService.get_live_match_state(self.db, self.room_code)
        card = state.first_innings_scorecard
        striker = state.striker
        self.assertEqual(striker.balls, 3)
        self.assertEqual(striker.runs, 12)
        self.assertEqual(striker.fours, 1)
        self.assertEqual(striker.sixes, 1)
        self.assertEqual(state.total_runs, 14)

        # Verify reconciliation: sum(batters) + extras == total_runs
        total_batter_runs = sum(b.runs for b in card.batters)
        self.assertEqual(total_batter_runs + card.extras, card.total_runs)
        self.assertEqual(card.wides, 1)
        self.assertEqual(card.no_balls, 1)
        self.assertEqual(card.extras, 2)

    def test_bowling_figures_and_run_out_crediting(self):
        """
        BUG 5: Verify bowling scorecard rules:
        - Run outs do NOT credit bowler with a wicket
        - Economy rate is accurate
        - Bowling figures strictly by player_id
        """
        host_picks = [
            {"player_id": 100 + i, "player_name": f"Batter {i}", "batting_position": i, "decade": 2010}
            for i in range(1, 12)
        ]
        guest_picks = [
            {"player_id": 200 + i, "player_name": f"Bowler {i}", "batting_position": i, "decade": 2010}
            for i in range(1, 12)
        ]
        self._setup_teams(host_picks, guest_picks)

        MatchService.initialize_or_get_match(self.db, self.room_code)

        # Delivery: Run out
        runout_res = DeliverySimulationResult(
            outcome="WICKET",
            batter_runs=0,
            extras=0,
            extra_type=None,
            is_legal=True,
            is_wicket=True,
            wicket_type="Run out",
            runs_scored=0,
            strike_changed=False,
            commentary="Run out by direct hit!",
            short_display="W",
        )
        with patch("app.match.simulation_engine.SimulationEngine.simulate_delivery", return_value=runout_res):
            MatchService.step_delivery(self.db, self.room_code)

        state = MatchService.get_live_match_state(self.db, self.room_code)
        self.assertEqual(state.total_wickets, 1)

        # Bowler should have 0 wickets!
        bowler = state.current_bowler
        self.assertEqual(bowler.wickets, 0)
        self.assertEqual(bowler.legal_balls, 1)

    def test_target_and_immediate_match_stop(self):
        """
        BUG 6: Verify chase victory stops simulation immediately and calculates correct wicket margin.
        """
        host_picks = [
            {"player_id": 100 + i, "player_name": f"Host {i}", "batting_position": i, "decade": 2010}
            for i in range(1, 12)
        ]
        guest_picks = [
            {"player_id": 200 + i, "player_name": f"Guest {i}", "batting_position": i, "decade": 2010}
            for i in range(1, 12)
        ]
        self._setup_teams(host_picks, guest_picks)

        # Initialize match
        MatchService.initialize_or_get_match(self.db, self.room_code)

        # Directly simulate completion of Innings 1 with 150 runs for 4 wickets
        inn1 = self.db.query(MatchInnings).filter(MatchInnings.innings_number == 1).first()
        inn1.total_runs = 150
        inn1.total_wickets = 4
        inn1.legal_balls_bowled = 120
        inn1.is_completed = True

        match = self.db.query(Match).first()
        match.target = 151
        match.current_innings = 2

        # Create Innings 2 with 148 runs for 2 wickets in 18 overs
        inn2 = MatchInnings(
            match_id=match.id,
            innings_number=2,
            batting_team_user_id="user_guest",
            bowling_team_user_id="user_host",
            total_runs=148,
            total_wickets=2,
            legal_balls_bowled=108,
            is_completed=False,
            current_striker_id=203,
            current_non_striker_id=202,
            current_bowler_id=105,
        )
        self.db.add(inn2)
        self.db.flush()

        for pos in range(1, 12):
            self.db.add(InningsBatterScore(
                innings_id=inn2.id,
                player_id=200 + pos,
                player_name=f"Guest {pos}",
                batting_position=pos,
                runs=30 if pos in (2, 3) else 0,
                balls=25 if pos in (2, 3) else 0,
                is_out=pos in (1, 4),
                has_batted=pos in (1, 2, 3, 4),
                dismissal_text="b Host" if pos in (1, 4) else "not out" if pos in (2, 3) else "DNB",
            ))
        self.db.add(InningsBowlerScore(
            innings_id=inn2.id,
            player_id=105,
            player_name="Host 5",
            legal_balls=18,
            overs=3.0,
            runs_conceded=20,
            wickets=1,
            economy=6.67,
        ))
        self.db.commit()

        # Step delivery: Batter hits a FOUR, reaching 152 runs (Target 151 met!)
        four_res = DeliverySimulationResult(
            outcome="FOUR",
            batter_runs=4,
            extras=0,
            extra_type=None,
            is_legal=True,
            is_wicket=False,
            wicket_type=None,
            runs_scored=4,
            strike_changed=False,
            commentary="Hit for FOUR to seal the victory!",
            short_display="4",
        )
        with patch("app.match.simulation_engine.SimulationEngine.simulate_delivery", return_value=four_res):
            _, final_state = MatchService.step_delivery(self.db, self.room_code)

        self.assertEqual(final_state.status, "COMPLETED")
        self.assertEqual(final_state.total_runs, 152)
        self.assertEqual(final_state.winner_user_id, "user_guest")
        # 10 - 2 = 8 wickets remaining!
        self.assertIn("won by 8 wickets", final_state.result_margin)

        # Ensure calling step_delivery again does NOT advance or crash
        dummy_res, post_state = MatchService.step_delivery(self.db, self.room_code)
        self.assertEqual(post_state.status, "COMPLETED")
        self.assertEqual(post_state.total_runs, 152)


if __name__ == "__main__":
    unittest.main()

