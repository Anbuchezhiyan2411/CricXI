"""
Comprehensive Test Suite for CricXI Phase 4.2:
Advanced Statistical Match Simulation Engine.
Verifies Z-score normalization, style classifications, Monte Carlo sampling,
dynamic confidence, match momentum, pitch/weather, chase intelligence, and statistical reconciliation.
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from app.services.dataset_loader import dataset_service
from app.match.statistical_profiler import (
    StatisticalProfiler,
    BattingStyle,
    BowlingStyle,
    PitchCondition,
    WeatherCondition,
    classify_batting_style,
    classify_bowling_style,
    get_batting_style_modifiers,
    get_bowling_style_modifiers,
    get_pitch_for_match,
    get_weather_for_match,
    get_field_setting,
    FieldSetting,
)
from app.match.simulation_engine import SimulationEngine, BASE_PROBABILITIES


class TestAdvancedStatisticalSimulation(unittest.TestCase):
    """Test suite for Phase 4.2 data-driven cricket simulation engine."""

    @classmethod
    def setUpClass(cls):
        dataset_service.load()
        cls.profiler = StatisticalProfiler.get_instance()
        cls.profiler.fit(dataset_service.get_all_players())

    def test_01_z_score_computation_and_percentile_transformation(self):
        """Verify Z-score calculation and standard normal CDF percentile mapping."""
        # Test known standard normal properties:
        # z = 0.0 -> percentile 0.50
        self.assertAlmostEqual(self.profiler.z_to_percentile(0.0), 0.50, places=2)
        # z = +1.96 -> percentile ~0.975
        self.assertAlmostEqual(self.profiler.z_to_percentile(1.96), 0.975, places=2)
        # z = -1.96 -> percentile ~0.025
        self.assertAlmostEqual(self.profiler.z_to_percentile(-1.96), 0.025, places=2)

        # Test player strength outputs strictly bounded in [0.05, 0.95]
        for p in dataset_service.get_all_players()[:50]:
            bat_str = self.profiler.calculate_batting_strength(p)
            bowl_str = self.profiler.calculate_bowling_strength(p)
            self.assertGreaterEqual(bat_str, 0.05)
            self.assertLessEqual(bat_str, 0.95)
            self.assertGreaterEqual(bowl_str, 0.05)
            self.assertLessEqual(bowl_str, 0.95)

    def test_02_automatic_batting_style_classification(self):
        """Verify data-driven style classification without manual labels."""
        # 1. Tailender (e.g., pure bowler with minimal batting rating)
        tailender_p = {"player_name": "Number 11", "batting_rating": 20.0, "primary_role": "BOWL", "balls_faced": 10, "strike_rate": 60.0}
        t_str = self.profiler.calculate_batting_strength(tailender_p)
        t_style = classify_batting_style(tailender_p, t_str)
        self.assertEqual(t_style, BattingStyle.TAILENDER)

        # 2. Aggressive Opener (top order with high strike rate and boundary frequency)
        agg_p = {"player_name": "Opener", "batting_rating": 85.0, "primary_role": "BAT", "eligible_positions": "1|2", "balls_faced": 500, "fours": 60, "sixes": 30, "strike_rate": 145.0, "batting_average": 32.0}
        agg_str = self.profiler.calculate_batting_strength(agg_p)
        agg_style = classify_batting_style(agg_p, agg_str)
        self.assertEqual(agg_style, BattingStyle.AGGRESSIVE_OPENER)

        # 3. Anchor (high average, lower strike rate)
        anchor_p = {"player_name": "Anchor", "batting_rating": 88.0, "primary_role": "BAT", "balls_faced": 800, "strike_rate": 118.0, "batting_average": 45.0}
        anc_str = self.profiler.calculate_batting_strength(anchor_p)
        anc_style = classify_batting_style(anchor_p, anc_str)
        self.assertEqual(anc_style, BattingStyle.ANCHOR)

        # 4. Power Hitter (high six ratio, high strike rate)
        power_p = {"player_name": "Power", "batting_rating": 82.0, "primary_role": "BAT", "balls_faced": 300, "fours": 20, "sixes": 25, "strike_rate": 155.0, "batting_average": 28.0}
        pow_str = self.profiler.calculate_batting_strength(power_p)
        pow_style = classify_batting_style(power_p, pow_str)
        self.assertEqual(pow_style, BattingStyle.POWER_HITTER)

    def test_03_automatic_bowling_style_classification(self):
        """Verify data-driven bowling style classification."""
        # 1. Fast Strike Bowler (low bowling strike rate, high rating)
        fast_p = {"player_name": "Express Pacer", "bowling_rating": 88.0, "primary_role": "BOWL", "bowling_type": "Right-arm Fast", "balls_bowled": 500, "economy": 7.8, "bowling_strike_rate": 16.0}
        f_str = self.profiler.calculate_bowling_strength(fast_p)
        f_style = classify_bowling_style(fast_p, f_str)
        self.assertEqual(f_style, BowlingStyle.FAST_STRIKE_BOWLER)

        # 2. Defensive Seamer (tight economy, higher strike rate)
        def_p = {"player_name": "Miserly Seamer", "bowling_rating": 78.0, "primary_role": "BOWL", "bowling_type": "Right-arm Medium", "balls_bowled": 600, "economy": 6.8, "bowling_strike_rate": 24.0}
        d_str = self.profiler.calculate_bowling_strength(def_p)
        d_style = classify_bowling_style(def_p, d_str)
        self.assertEqual(d_style, BowlingStyle.DEFENSIVE_SEAMER)

        # 3. Leg Spinner (wrist spin)
        leg_p = {"player_name": "Wrist Spinner", "bowling_rating": 85.0, "primary_role": "BOWL", "bowling_type": "Right-arm Leg Spin", "balls_bowled": 400, "economy": 7.5, "bowling_strike_rate": 18.0}
        l_str = self.profiler.calculate_bowling_strength(leg_p)
        l_style = classify_bowling_style(leg_p, l_str)
        self.assertEqual(l_style, BowlingStyle.LEG_SPINNER)

        # 4. Part Timer (pure batter with weak bowling rating)
        pt_p = {"player_name": "Occasional Bowler", "bowling_rating": 30.0, "primary_role": "BAT", "bowling_type": "Right-arm Medium", "balls_bowled": 12, "economy": 9.5}
        pt_str = self.profiler.calculate_bowling_strength(pt_p)
        pt_style = classify_bowling_style(pt_p, pt_str)
        self.assertEqual(pt_style, BowlingStyle.PART_TIMER)

    def test_04_monte_carlo_performance_and_determinism(self):
        """
        Verify that 500-sample Monte Carlo simulation executes well under 20ms
        and produces deterministic results when a random seed is provided.
        """
        probs = dict(BASE_PROBABILITIES)

        # Benchmark computation speed across 50 simulated deliveries
        start_t = time.perf_counter()
        for _ in range(50):
            SimulationEngine.run_monte_carlo_sampling(probs, num_simulations=500, seed=42)
        end_t = time.perf_counter()

        avg_ms = ((end_t - start_t) / 50.0) * 1000.0
        # Must execute in under 20 milliseconds per ball
        self.assertLess(avg_ms, 20.0, f"Monte Carlo exceeded 20ms: {avg_ms:.2f}ms")

        # Determinism check: identical seed must yield identical sequence
        res_a = [SimulationEngine.run_monte_carlo_sampling(probs, num_simulations=500, seed=s) for s in range(10)]
        res_b = [SimulationEngine.run_monte_carlo_sampling(probs, num_simulations=500, seed=s) for s in range(10)]
        self.assertEqual(res_a, res_b)

    def test_05_dynamic_confidence_modifiers(self):
        """Verify dynamic confidence adjusts boundary and wicket probabilities."""
        batter = {"player_name": "Star Batter", "batting_rating": 85.0, "strike_rate": 135.0, "batting_average": 38.0}
        bowler = {"player_name": "Standard Bowler", "bowling_rating": 75.0, "economy": 7.5, "bowling_strike_rate": 20.0}

        # High confidence batter vs Low confidence batter
        probs_high_conf = SimulationEngine.calculate_delivery_probabilities(
            batter, bowler, over_number=8, innings_number=1, wickets_fallen=1, batter_confidence=85.0
        )
        probs_low_conf = SimulationEngine.calculate_delivery_probabilities(
            batter, bowler, over_number=8, innings_number=1, wickets_fallen=1, batter_confidence=25.0
        )

        # High confidence batter should have higher boundary chance and lower wicket risk
        self.assertGreater(probs_high_conf["FOUR"] + probs_high_conf["SIX"], probs_low_conf["FOUR"] + probs_low_conf["SIX"])
        self.assertLess(probs_high_conf["WICKET"], probs_low_conf["WICKET"])

    def test_06_match_momentum_and_partnership_engine(self):
        """Verify momentum surges and unbroken partnerships dampen dismissal risk."""
        batter = {"player_name": "Set Batter", "batting_rating": 80.0, "strike_rate": 130.0, "batting_average": 35.0}
        bowler = {"player_name": "Pressure Bowler", "bowling_rating": 80.0, "economy": 7.5, "bowling_strike_rate": 20.0}

        # Fresh partnership (0 runs) vs Settled partnership (75 runs)
        probs_0 = SimulationEngine.calculate_delivery_probabilities(
            batter, bowler, over_number=10, innings_number=1, wickets_fallen=2, partnership_runs=0
        )
        probs_75 = SimulationEngine.calculate_delivery_probabilities(
            batter, bowler, over_number=10, innings_number=1, wickets_fallen=2, partnership_runs=75
        )

        # 75-run partnership should reduce dismissal probability
        self.assertLess(probs_75["WICKET"], probs_0["WICKET"])

        # Positive momentum (+4.0) vs Negative momentum (-4.0)
        probs_pos_mom = SimulationEngine.calculate_delivery_probabilities(
            batter, bowler, over_number=10, innings_number=1, wickets_fallen=2, momentum=4.0
        )
        probs_neg_mom = SimulationEngine.calculate_delivery_probabilities(
            batter, bowler, over_number=10, innings_number=1, wickets_fallen=2, momentum=-4.0
        )
        self.assertGreater(probs_pos_mom["FOUR"] + probs_pos_mom["SIX"], probs_neg_mom["FOUR"] + probs_neg_mom["SIX"])
        self.assertLess(probs_pos_mom["WICKET"], probs_neg_mom["WICKET"])

    def test_07_chase_intelligence_second_innings(self):
        """Verify RRR pressure modulates aggression and risk in the 2nd innings."""
        batter = {"player_name": "Chasing Batter", "batting_rating": 80.0, "strike_rate": 130.0, "batting_average": 35.0}
        bowler = {"player_name": "Defending Bowler", "bowling_rating": 80.0, "economy": 7.5, "bowling_strike_rate": 20.0}

        # Desperate chase: 50 runs needed off 18 balls (RRR = 16.67)
        probs_desperate = SimulationEngine.calculate_delivery_probabilities(
            batter, bowler, over_number=17, innings_number=2, wickets_fallen=4,
            runs_required=50, balls_remaining=18
        )
        # Calm cruise: 10 runs needed off 30 balls (RRR = 2.0)
        probs_cruise = SimulationEngine.calculate_delivery_probabilities(
            batter, bowler, over_number=15, innings_number=2, wickets_fallen=2,
            runs_required=10, balls_remaining=30
        )

        # Desperate chase should boost sixes significantly but carry higher wicket risk
        self.assertGreater(probs_desperate["SIX"], probs_cruise["SIX"])
        self.assertGreater(probs_desperate["WICKET"], probs_cruise["WICKET"])
        # Cruise should emphasize safe singles
        self.assertGreater(probs_cruise["SINGLE"], probs_desperate["SINGLE"])

    def test_08_pitch_and_weather_determinism(self):
        """Verify pitch and weather generation remain constant for a match."""
        p1 = get_pitch_for_match(42)
        p2 = get_pitch_for_match(42)
        w1 = get_weather_for_match(42)
        w2 = get_weather_for_match(42)

        self.assertEqual(p1, p2)
        self.assertEqual(w1, w2)
        self.assertIn(p1, [PitchCondition.GREEN, PitchCondition.FLAT, PitchCondition.TURNING, PitchCondition.BALANCED])
        self.assertIn(w1, [WeatherCondition.SUNNY, WeatherCondition.CLOUDY, WeatherCondition.HUMID, WeatherCondition.OVERCAST])

    def test_09_full_delivery_simulation_result_attributes(self):
        """Verify simulate_delivery generates rich contextual outcomes and commentary."""
        batter = {"player_name": "Rohit Sharma", "batting_rating": 88.0, "strike_rate": 140.0, "batting_average": 33.0}
        bowler = {"player_name": "Mitchell Starc", "bowling_rating": 86.0, "economy": 7.5, "bowling_strike_rate": 18.0}

        res = SimulationEngine.simulate_delivery(
            batter_stats=batter,
            bowler_stats=bowler,
            over_number=1,
            ball_in_over=1,
            innings_number=1,
            wickets_fallen=0,
            seed=10,
        )

        self.assertIn(res.outcome, ["DOT", "SINGLE", "DOUBLE", "THREE", "FOUR", "SIX", "WICKET"])
        self.assertTrue(len(res.commentary) > 10)
        self.assertEqual(res.runs_scored, res.batter_runs + res.extras)


if __name__ == "__main__":
    unittest.main()

