"""
Unit and Integration Tests for CricXI Analytics & IDS Modules.
Validates:
1. One-Sample Proportion Z-Test and p-value computation.
2. Bat First vs Bowl First statistical comparisons.
3. Pearson Correlation and Linear Regression for Team Rating vs Outcome.
4. Standardized Z-Score Outlier Detection for Player Performance.
5. Univariate central tendency and dispersion calculations.
6. Pairwise Pearson correlation heatmap matrix.
7. Scikit-Learn Logistic Regression win probability predictor.
8. Empty dataset graceful handling (no division-by-zero or crashes).
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models.match import Match, MatchInnings
from app.models.room import Room, RoomPlayer
from app.models.draft import DraftPick
from app.analytics.statistics import (
    compute_toss_hypothesis_test,
    compute_bat_bowl_first_analysis,
    compute_team_rating_correlation,
    compute_player_outliers,
    compute_match_distributions,
    compute_correlation_matrix,
)
from app.analytics.prediction import WinPredictor
from app.analytics.analytics_service import AnalyticsService


class TestAnalyticsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        Session = sessionmaker(bind=self.engine)
        self.db = Session()

    def tearDown(self):
        self.db.close()

    def test_empty_dataset_handling(self):
        """Verifies analytics handle 0 completed matches without errors."""
        toss_res = compute_toss_hypothesis_test([])
        self.assertEqual(toss_res["total_matches"], 0)
        self.assertEqual(toss_res["p_value"], 1.0)
        self.assertFalse(toss_res["is_significant"])

        bat_res = compute_bat_bowl_first_analysis([])
        self.assertEqual(bat_res["total_matches"], 0)
        self.assertEqual(bat_res["best_strategy"], "Insufficient Data")

        rating_res = compute_team_rating_correlation([])
        self.assertEqual(rating_res["sample_size"], 0)
        self.assertEqual(rating_res["correlation_coefficient"], 0.0)

        outlier_res = compute_player_outliers([])
        self.assertEqual(outlier_res["total_players"], 0)

        dist_res = compute_match_distributions([])
        self.assertEqual(dist_res["total_matches"], 0)

        matrix_res = compute_correlation_matrix([])
        self.assertEqual(len(matrix_res["matrix"]), 6)

    def test_toss_hypothesis_z_test(self):
        """Verifies One-Sample Proportion Z-Test math on synthetic matches."""
        # Scenario: 40 matches, 30 toss winners won match (75% win rate)
        matches = []
        for i in range(40):
            toss_won = (i < 30)
            matches.append({
                "toss_winner_id": "u1",
                "winner_user_id": "u1" if toss_won else "u2",
                "toss_decision": "BAT" if i % 2 == 0 else "BOWL",
            })

        res = compute_toss_hypothesis_test(matches)
        self.assertEqual(res["total_matches"], 40)
        self.assertEqual(res["toss_winner_match_wins"], 30)
        self.assertEqual(res["observed_toss_win_rate"], 75.0)
        self.assertGreater(res["z_score"], 3.0)  # Z should be approx 3.16
        self.assertLess(res["p_value"], 0.01)    # p < 0.01
        self.assertTrue(res["is_significant"])
        self.assertIn("Reject Null Hypothesis", res["conclusion"])

    def test_bat_first_vs_bowl_first(self):
        """Verifies bat first vs bowl first win rates and score averages."""
        matches = [
            {"bat_first_user_id": "u1", "winner_user_id": "u1", "innings1_runs": 180, "innings2_runs": 160},
            {"bat_first_user_id": "u1", "winner_user_id": "u1", "innings1_runs": 190, "innings2_runs": 170},
            {"bat_first_user_id": "u1", "winner_user_id": "u2", "innings1_runs": 140, "innings2_runs": 142},
        ]
        res = compute_bat_bowl_first_analysis(matches)
        self.assertEqual(res["total_matches"], 3)
        self.assertEqual(res["bat_first_wins"], 2)
        self.assertEqual(res["bowl_first_wins"], 1)
        self.assertEqual(res["best_strategy"], "Bat First")
        self.assertAlmostEqual(res["avg_first_innings_score"], 170.0, places=1)

    def test_team_rating_correlation(self):
        """Verifies Pearson r correlation calculation."""
        matches = [
            {"id": 1, "team1_rating": 85.0, "team2_rating": 70.0, "team1_user_id": "u1", "team2_user_id": "u2", "winner_user_id": "u1"},
            {"id": 2, "team1_rating": 80.0, "team2_rating": 72.0, "team1_user_id": "u1", "team2_user_id": "u2", "winner_user_id": "u1"},
            {"id": 3, "team1_rating": 70.0, "team2_rating": 85.0, "team1_user_id": "u1", "team2_user_id": "u2", "winner_user_id": "u2"},
            {"id": 4, "team1_rating": 72.0, "team2_rating": 82.0, "team1_user_id": "u1", "team2_user_id": "u2", "winner_user_id": "u2"},
        ]
        res = compute_team_rating_correlation(matches)
        self.assertGreater(res["correlation_coefficient"], 0.70)
        self.assertEqual(res["strength"], "Strong")
        self.assertEqual(res["direction"], "Positive")
        self.assertEqual(len(res["scatter_points"]), 8)

    def test_player_outlier_detection_z_score(self):
        """Verifies standardized Z-Scores and outlier classification."""
        players = [
            {"player_id": 1, "player_name": "Elite Legend", "impact_points": 180.0},
            {"player_id": 2, "player_name": "Solid Player 1", "impact_points": 50.0},
            {"player_id": 3, "player_name": "Solid Player 2", "impact_points": 48.0},
            {"player_id": 4, "player_name": "Solid Player 3", "impact_points": 52.0},
            {"player_id": 5, "player_name": "Solid Player 4", "impact_points": 49.0},
            {"player_id": 6, "player_name": "Struggling Player", "impact_points": 2.0},
        ]
        res = compute_player_outliers(players)
        self.assertEqual(res["total_players"], 6)
        # Elite Legend should have Z > 2.0
        self.assertGreaterEqual(res["elite_count"], 1)
        top_player = res["players"][0]
        self.assertEqual(top_player["player_name"], "Elite Legend")
        self.assertEqual(top_player["category"], "Elite Performer")
        self.assertEqual(top_player["badge"], "emerald")

    def test_win_predictor_logistic_regression(self):
        """Verifies Scikit-Learn Logistic Regression prediction outputs."""
        predictor = WinPredictor()
        # Favorite with rating 88 vs 72, won toss and bat first
        pred = predictor.predict(team_a_rating=88.0, team_b_rating=72.0, toss_winner="team_a", toss_decision="BAT")
        self.assertGreater(pred["team_a_probability"], 65.0)
        self.assertEqual(pred["predicted_winner"], "Team A")
        self.assertAlmostEqual(pred["team_a_probability"] + pred["team_b_probability"], 100.0, places=1)
        self.assertIn("factors", pred)

    def test_analytics_service_e2e_summary(self):
        """Verifies AnalyticsService.get_summary() pipeline."""
        summary = AnalyticsService.get_summary(self.db)
        self.assertIn("total_matches", summary)
        self.assertIn("toss_analysis_summary", summary)
        self.assertIn("batting_strategy_summary", summary)
        self.assertIn("team_rating_summary", summary)
        self.assertIn("data_science_concepts", summary)


if __name__ == "__main__":
    unittest.main()
