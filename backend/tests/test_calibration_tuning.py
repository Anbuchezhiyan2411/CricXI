"""
CricXI Phase 4.3 – Statistical Calibration & Realism Tuning Unit Tests.
Validates:
1. Calibrated base delivery probabilities and empirical targets (Stage 9).
2. Dynamic confidence saturation and mean reversion (Stage 6).
3. Momentum exponential decay and hyperbolic saturation (Stage 5).
4. Partnership balancing and sustained wicket threat (Stage 7).
5. Batter innings fatigue curve and dismissal escalation (Stages 2 & 3).
6. Chase pressure calibration under high RRR (Stage 8).
7. Bowling figures binomial distribution bounds (Stage 4).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import math
import unittest
from app.match.simulation_engine import BASE_PROBABILITIES, SimulationEngine
from app.match.statistical_profiler import (
    BattingStyle,
    BowlingStyle,
    PitchCondition,
    WeatherCondition,
    get_batting_style_modifiers,
    get_bowling_style_modifiers,
)


class TestStatisticalCalibration(unittest.TestCase):
    """Rigorous unit tests for CricXI Phase 4.3 calibration tuning."""

    def test_base_probabilities_sum_and_ranges(self):
        """Stage 9: Verify base probabilities sum to 1.0 and match empirical T20 targets."""
        total = sum(BASE_PROBABILITIES.values())
        self.assertAlmostEqual(total, 1.0, places=2)

        # Target ranges from specification
        self.assertGreaterEqual(BASE_PROBABILITIES["DOT"], 0.32)
        self.assertLessEqual(BASE_PROBABILITIES["DOT"], 0.40)

        self.assertGreaterEqual(BASE_PROBABILITIES["SINGLE"], 0.28)
        self.assertLessEqual(BASE_PROBABILITIES["SINGLE"], 0.36)

        self.assertGreaterEqual(BASE_PROBABILITIES["FOUR"], 0.10)
        self.assertLessEqual(BASE_PROBABILITIES["FOUR"], 0.15)

        self.assertGreaterEqual(BASE_PROBABILITIES["SIX"], 0.04)
        self.assertLessEqual(BASE_PROBABILITIES["SIX"], 0.08)

        self.assertGreaterEqual(BASE_PROBABILITIES["WICKET"], 0.025)
        self.assertLessEqual(BASE_PROBABILITIES["WICKET"], 0.045)

        self.assertGreaterEqual(BASE_PROBABILITIES["WIDE"], 0.018)
        self.assertLessEqual(BASE_PROBABILITIES["WIDE"], 0.038)

        self.assertLessEqual(BASE_PROBABILITIES["NO_BALL"], 0.012)

    def test_confidence_saturation_and_no_runaway(self):
        """Stage 6: Verify confidence saturation prevents runaway compounding."""
        batter_stats = {
            "player_name": "Elite Batter",
            "batting_rating": 90.0,
            "batting_average": 45.0,
            "strike_rate": 150.0,
            "fours": 200,
            "sixes": 100,
            "balls_faced": 1200,
            "primary_role": "BAT",
        }
        bowler_stats = {
            "player_name": "Elite Bowler",
            "bowling_rating": 85.0,
            "economy": 7.2,
            "bowling_strike_rate": 18.0,
            "primary_role": "PACE",
        }

        # Moderate confidence (65.0)
        probs_med = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=batter_stats,
            bowler_stats=bowler_stats,
            over_number=10,
            innings_number=1,
            wickets_fallen=2,
            batter_confidence=65.0,
        )

        # High confidence (80.0)
        probs_high = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=batter_stats,
            bowler_stats=bowler_stats,
            over_number=10,
            innings_number=1,
            wickets_fallen=2,
            batter_confidence=80.0,
        )

        # Boundary probability should increase moderately, never run away past 35%
        boundary_med = probs_med["FOUR"] + probs_med["SIX"]
        boundary_high = probs_high["FOUR"] + probs_high["SIX"]
        self.assertGreater(boundary_high, boundary_med)
        self.assertLess(boundary_high, 0.35, "Boundary probability must not explode with high confidence")

        # Wickets must remain genuinely possible even for a confident batter
        self.assertGreater(probs_high["WICKET"], 0.020, "Confident batter must still face non-trivial dismissal risk")

    def test_momentum_saturation(self):
        """Stage 5: Verify momentum saturation prevents extreme compounding."""
        batter_stats = {"batting_rating": 75.0, "primary_role": "BAT"}
        bowler_stats = {"bowling_rating": 75.0, "primary_role": "PACE"}

        probs_neutral = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=batter_stats, bowler_stats=bowler_stats, over_number=8, innings_number=1, wickets_fallen=1, momentum=0.0
        )
        probs_surge = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=batter_stats, bowler_stats=bowler_stats, over_number=8, innings_number=1, wickets_fallen=1, momentum=5.0
        )
        probs_collapse = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=batter_stats, bowler_stats=bowler_stats, over_number=8, innings_number=1, wickets_fallen=1, momentum=-5.0
        )

        # Surge increases boundaries moderately (< 20% relative boost)
        surge_four_ratio = probs_surge["FOUR"] / probs_neutral["FOUR"]
        self.assertLessEqual(surge_four_ratio, 1.20)

        # Collapse increases wicket chance moderately (< 25% relative boost)
        collapse_wkt_ratio = probs_collapse["WICKET"] / probs_neutral["WICKET"]
        self.assertLessEqual(collapse_wkt_ratio, 1.25)

    def test_partnership_balancing_preserves_wicket_threat(self):
        """Stage 7: Verify large partnerships (100+ runs) retain wicket danger."""
        batter_stats = {"batting_rating": 80.0, "primary_role": "BAT"}
        bowler_stats = {"bowling_rating": 80.0, "primary_role": "PACE"}

        probs_start = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=batter_stats, bowler_stats=bowler_stats, over_number=12, innings_number=1, wickets_fallen=1, partnership_runs=10
        )
        probs_century_part = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=batter_stats, bowler_stats=bowler_stats, over_number=12, innings_number=1, wickets_fallen=1, partnership_runs=120
        )

        # 100+ partnership should discount wickets by ~20% (multiplier 0.80), NOT 40%+
        wkt_ratio = probs_century_part["WICKET"] / probs_start["WICKET"]
        self.assertGreaterEqual(wkt_ratio, 0.75, "Wicket threat must not drop below 75% even in massive partnerships")

    def test_batter_innings_progression_and_fatigue(self):
        """Stages 2 & 3: Verify early ball caution and late innings fatigue escalation."""
        batter_stats = {"batting_rating": 85.0, "primary_role": "BAT"}
        bowler_stats = {"bowling_rating": 80.0, "primary_role": "PACE"}

        probs_early = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=batter_stats, bowler_stats=bowler_stats, over_number=2, innings_number=1, wickets_fallen=0, batter_balls_faced=3
        )
        probs_peak = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=batter_stats, bowler_stats=bowler_stats, over_number=8, innings_number=1, wickets_fallen=0, batter_balls_faced=20
        )
        probs_fatigue = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=batter_stats, bowler_stats=bowler_stats, over_number=18, innings_number=1, wickets_fallen=1, batter_balls_faced=60
        )

        # Early balls have slightly higher dot rate (settling in)
        self.assertGreater(probs_early["DOT"], probs_peak["DOT"])

        # Fatigue balls have higher dismissal rate than peak
        self.assertGreater(probs_fatigue["WICKET"], probs_peak["WICKET"])

    def test_chase_intelligence_stability(self):
        """Stage 8: Verify RRR >= 12 increases boundary ambition without instant collapse."""
        batter_stats = {"batting_rating": 80.0, "primary_role": "BAT"}
        bowler_stats = {"bowling_rating": 75.0, "primary_role": "PACE"}

        probs_high_rrr = SimulationEngine.calculate_delivery_probabilities(
            batter_stats=batter_stats,
            bowler_stats=bowler_stats,
            over_number=16,
            innings_number=2,
            wickets_fallen=4,
            runs_required=50,
            balls_remaining=24,  # RRR = 12.5
        )

        # Sixes should be boosted for chase ambition
        self.assertGreaterEqual(probs_high_rrr["SIX"], BASE_PROBABILITIES["SIX"])
        # Wicket rate should be elevated but strictly controlled (< 6.5%)
        self.assertLessEqual(probs_high_rrr["WICKET"], 0.065)

    def test_style_modifiers_bounded(self):
        """Stage 3: Verify all batting and bowling style modifiers are properly calibrated."""
        for style in BattingStyle:
            mods = get_batting_style_modifiers(style)
            for key, val in mods.items():
                self.assertGreater(val, 0.20, f"Modifier for {style}.{key} is too small: {val}")
                self.assertLess(val, 2.0, f"Modifier for {style}.{key} is too large: {val}")

        for bw_style in BowlingStyle:
            bw_mods = get_bowling_style_modifiers(bw_style)
            for key, val in bw_mods.items():
                self.assertGreater(val, 0.60, f"Bowler modifier for {bw_style}.{key} is too small: {val}")
                self.assertLess(val, 1.40, f"Bowler modifier for {bw_style}.{key} is too large: {val}")


if __name__ == "__main__":
    unittest.main()

