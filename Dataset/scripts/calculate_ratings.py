"""
Module: calculate_ratings.py
Description: Generates batting, bowling, fielding, and overall ratings (0-100)
             using sensible weighted formulas based on player roles and decade stats.
"""

import logging
from typing import Any, Dict
import pandas as pd

logger = logging.getLogger(__name__)


def clamp_rating(val: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Clamps a rating value between min_val and max_val and rounds to 1 decimal place."""
    return round(max(min_val, min(max_val, float(val))), 1)


def compute_batting_rating(row: Dict[str, Any]) -> float:
    """
    Computes batting rating (0-100) based on:
    - Runs volume
    - Batting Average
    - Strike Rate
    - Consistency (Fifties, Hundreds, low dot ball %)
    - Boundary %
    """
    matches = int(row.get("matches", 0) or 0)
    innings = int(row.get("innings", 0) or 0)
    runs = float(row.get("runs", 0) or 0)
    balls = float(row.get("balls_faced", 0) or 0)
    avg = float(row.get("batting_average", 0) or 0)
    sr = float(row.get("strike_rate", 0) or 0)
    fifties = int(row.get("fifties", 0) or 0)
    hundreds = int(row.get("hundreds", 0) or 0)
    fours = int(row.get("fours", 0) or 0)
    sixes = int(row.get("sixes", 0) or 0)
    dot_pct = float(row.get("dot_ball_percentage", 0) or 0)

    # For historic players with 0 T20I matches (pre-T20 era Best XI legends)
    if matches == 0 or innings == 0:
        role = str(row.get("primary_role", "")).upper()
        if role == "BAT":
            return 82.0
        elif role == "WK":
            return 78.0
        elif role == "AR":
            return 75.0
        elif role in {"PACE", "SPIN"}:
            return 25.0
        return 50.0

    # 1. Runs Volume Score (0-100): 1200+ runs in a decade is elite (~100)
    runs_score = min(100.0, (runs / 1200.0) * 100.0)

    # 2. Average Score (0-100): 35+ avg is world class in T20I
    avg_score = min(100.0, (avg / 35.0) * 100.0)

    # 3. Strike Rate Score (0-100): 140+ SR is elite in T20I, baseline at 90
    if sr <= 90.0:
        sr_score = max(0.0, (sr / 90.0) * 40.0)
    else:
        sr_score = min(100.0, 40.0 + ((sr - 90.0) / 55.0) * 60.0)

    # 4. Consistency Score (0-100): Milestones per innings + dot ball avoidance
    milestone_rate = (fifties * 1.5 + hundreds * 3.0) / max(1, innings)
    milestone_score = min(50.0, milestone_rate * 100.0)
    dot_avoidance_score = max(0.0, min(50.0, (60.0 - dot_pct) * 1.25))
    consistency_score = milestone_score + dot_avoidance_score

    # 5. Boundary Percentage Score (0-100): Boundary runs / total runs
    boundary_runs = fours * 4 + sixes * 6
    boundary_pct = (boundary_runs / max(1.0, runs)) * 100.0
    boundary_score = min(100.0, (boundary_pct / 70.0) * 100.0)

    # Weighted combination
    raw_rating = (
        runs_score * 0.25
        + avg_score * 0.25
        + sr_score * 0.25
        + consistency_score * 0.15
        + boundary_score * 0.10
    )

    # Small sample dampener: players with < 5 innings scaled down slightly
    if innings < 5:
        sample_factor = max(0.4, innings / 5.0)
        raw_rating *= sample_factor

    return clamp_rating(raw_rating)


def compute_bowling_rating(row: Dict[str, Any]) -> float:
    """
    Computes bowling rating (0-100) based on:
    - Wickets volume
    - Economy rate
    - Bowling Average
    - Bowling Strike Rate
    """
    matches = int(row.get("matches", 0) or 0)
    balls = float(row.get("balls_bowled", 0) or 0)
    wickets = float(row.get("wickets", 0) or 0)
    econ = float(row.get("economy", 0) or 0)
    avg = float(row.get("bowling_average", 0) or 0)
    sr = float(row.get("bowling_strike_rate", 0) or 0)
    maidens = int(row.get("maidens", 0) or 0)

    # For historic players with 0 T20I matches (pre-T20 era Best XI legends)
    if matches == 0 or balls == 0:
        role = str(row.get("primary_role", "")).upper()
        if role in {"PACE", "SPIN"}:
            return 84.0
        elif role == "AR":
            return 75.0
        elif role == "BAT":
            return 20.0
        elif role == "WK":
            return 5.0
        return 40.0

    # 1. Wickets Volume Score (0-100): 60+ wickets in a decade is elite
    wickets_score = min(100.0, (wickets / 60.0) * 100.0)

    # 2. Economy Score (0-100): < 6.5 is elite, > 10.0 is poor
    if econ <= 6.5:
        econ_score = 100.0
    elif econ >= 10.5:
        econ_score = max(0.0, (12.0 - econ) * 15.0)
    else:
        econ_score = max(0.0, min(100.0, ((10.5 - econ) / 4.0) * 100.0))

    # 3. Bowling Average Score (0-100): < 18 is elite, > 40 is poor
    if wickets == 0:
        avg_score = 15.0
    elif avg <= 18.0:
        avg_score = 100.0
    elif avg >= 40.0:
        avg_score = max(10.0, (50.0 - avg) * 2.0)
    else:
        avg_score = max(10.0, min(100.0, ((40.0 - avg) / 22.0) * 100.0))

    # 4. Bowling Strike Rate Score (0-100): < 16 balls/wicket is elite
    if wickets == 0:
        sr_score = 15.0
    elif sr <= 16.0:
        sr_score = 100.0
    elif sr >= 32.0:
        sr_score = max(10.0, (40.0 - sr) * 2.5)
    else:
        sr_score = max(10.0, min(100.0, ((32.0 - sr) / 16.0) * 100.0))

    # Maiden bonus (up to 5 points)
    maiden_bonus = min(5.0, maidens * 2.0)

    raw_rating = (
        wickets_score * 0.35
        + econ_score * 0.25
        + avg_score * 0.20
        + sr_score * 0.20
        + maiden_bonus
    )

    # Small sample dampener for bowlers with few overs
    overs = balls / 6.0
    if overs < 10:
        sample_factor = max(0.3, overs / 10.0)
        raw_rating *= sample_factor

    return clamp_rating(raw_rating)


def compute_fielding_rating(row: Dict[str, Any]) -> float:
    """
    Computes fielding rating (0-100) based on:
    - Catches
    - Stumpings
    - Run Outs
    """
    matches = int(row.get("matches", 0) or 0)
    catches = int(row.get("catches", 0) or 0)
    stumpings = int(row.get("stumpings", 0) or 0)
    run_outs = int(row.get("run_outs", 0) or 0)
    is_wk = str(row.get("is_wicketkeeper", "")).strip().upper() == "TRUE" or row.get("primary_role") == "WK"

    # Pre-T20 era default
    if matches == 0:
        return 82.0 if is_wk else 70.0

    # Total dismissals impacted
    dismissal_points = catches * 3.5 + stumpings * 5.0 + run_outs * 4.0
    volume_score = min(70.0, dismissal_points * 1.5)

    # Per match efficiency
    rate = (catches + stumpings + run_outs) / max(1, matches)
    rate_score = min(30.0, rate * 45.0)

    raw_rating = volume_score + rate_score

    # Baseline fielding competence for international players
    base_rating = 55.0 if is_wk else 45.0
    final_rating = max(base_rating, raw_rating)

    return clamp_rating(final_rating)


def compute_overall_rating(row: Dict[str, Any], bat_rat: float, bowl_rat: float, fld_rat: float) -> float:
    """
    Combines batting, bowling, and fielding ratings based on the player's primary role.
    Roles:
    - BAT: 80% Bat, 5% Bowl, 15% Field
    - WK: 65% Bat, 0% Bowl, 35% Field
    - AR: 45% Bat, 45% Bowl, 10% Field
    - PACE: 10% Bat, 80% Bowl, 10% Field
    - SPIN: 10% Bat, 80% Bowl, 10% Field
    """
    role = str(row.get("primary_role", "BAT")).strip().upper()

    if role == "BAT":
        overall = bat_rat * 0.80 + bowl_rat * 0.05 + fld_rat * 0.15
    elif role == "WK":
        overall = bat_rat * 0.65 + fld_rat * 0.35
    elif role == "AR":
        overall = bat_rat * 0.45 + bowl_rat * 0.45 + fld_rat * 0.10
    elif role in {"PACE", "SPIN"}:
        overall = bowl_rat * 0.80 + bat_rat * 0.10 + fld_rat * 0.10
    else:
        # Default balanced
        overall = bat_rat * 0.45 + bowl_rat * 0.45 + fld_rat * 0.10

    return clamp_rating(overall)


def add_ratings_to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Computes and appends batting_rating, bowling_rating, fielding_rating, overall_rating."""
    bat_ratings = []
    bowl_ratings = []
    fld_ratings = []
    ovr_ratings = []

    for _, row in df.iterrows():
        row_dict = row.to_dict()
        b_r = compute_batting_rating(row_dict)
        bw_r = compute_bowling_rating(row_dict)
        f_r = compute_fielding_rating(row_dict)
        o_r = compute_overall_rating(row_dict, b_r, bw_r, f_r)

        bat_ratings.append(b_r)
        bowl_ratings.append(bw_r)
        fld_ratings.append(f_r)
        ovr_ratings.append(o_r)

    df["batting_rating"] = bat_ratings
    df["bowling_rating"] = bowl_ratings
    df["fielding_rating"] = fld_ratings
    df["overall_rating"] = ovr_ratings

    return df

