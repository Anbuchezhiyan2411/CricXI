"""
Introduction to Data Science (IDS) Core Statistical Calculations.
Implements hypothesis testing (One-Sample Proportion Z-Test),
bivariate Pearson correlation, univariate descriptive statistics,
standardized Z-scores for outlier detection, and correlation matrices.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats


def compute_toss_hypothesis_test(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Performs a One-Sample Proportion Z-Test on Toss Winner vs Match Winner:
    Null Hypothesis (H0): Winning the toss does NOT affect match outcome (p = 0.5).
    Alternative Hypothesis (H1): Winning the toss affects match outcome (p != 0.5).
    """
    n = len(matches)
    if n == 0:
        return {
            "total_matches": 0,
            "toss_winner_match_wins": 0,
            "observed_toss_win_rate": 0.0,
            "expected_win_rate": 50.0,
            "z_score": 0.0,
            "p_value": 1.0,
            "is_significant": False,
            "null_hypothesis": "Winning the toss does not affect winning the match (p = 0.50)",
            "alternative_hypothesis": "Winning the toss significantly affects winning the match (p ≠ 0.50)",
            "conclusion": "No match data available to evaluate hypothesis.",
            "explanation": "No completed matches recorded yet. Play games to test statistical significance.",
            "toss_decision_breakdown": {
                "BAT": {"count": 0, "wins": 0, "win_rate": 0.0},
                "BOWL": {"count": 0, "wins": 0, "win_rate": 0.0},
            },
        }

    toss_and_match_wins = sum(1 for m in matches if m.get("toss_winner_id") and m.get("toss_winner_id") == m.get("winner_user_id"))
    p_hat = toss_and_match_wins / n
    p_0 = 0.5

    # Standard error under H0
    se = np.sqrt((p_0 * (1 - p_0)) / n)
    z_score = float((p_hat - p_0) / se) if se > 0 else 0.0

    # Two-tailed p-value from standard normal distribution
    p_value = float(2 * stats.norm.sf(abs(z_score)))

    is_significant = p_value < 0.05

    if is_significant:
        conclusion = "Reject Null Hypothesis (H₀)"
        direction = "positive" if z_score > 0 else "negative"
        explanation = (
            f"Since the p-value ({p_value:.4f}) is less than the significance threshold α = 0.05 (Z = {z_score:+.2f}), "
            f"we reject the null hypothesis. Winning the toss has a statistically significant {direction} "
            f"relationship with winning the match in this sample of {n} matches."
        )
    else:
        conclusion = "Fail to Reject Null Hypothesis (H₀)"
        explanation = (
            f"Since the p-value ({p_value:.4f}) is greater than α = 0.05 (Z = {z_score:+.2f}), "
            f"we fail to reject the null hypothesis. There is insufficient statistical evidence to conclude that "
            f"winning the toss confers an unfair advantage in match outcomes."
        )

    # Breakdown by Toss Decision (BAT vs BOWL)
    bat_count = sum(1 for m in matches if str(m.get("toss_decision", "")).upper() == "BAT")
    bat_wins = sum(1 for m in matches if str(m.get("toss_decision", "")).upper() == "BAT" and m.get("toss_winner_id") == m.get("winner_user_id"))
    bowl_count = sum(1 for m in matches if str(m.get("toss_decision", "")).upper() == "BOWL")
    bowl_wins = sum(1 for m in matches if str(m.get("toss_decision", "")).upper() == "BOWL" and m.get("toss_winner_id") == m.get("winner_user_id"))

    return {
        "total_matches": n,
        "toss_winner_match_wins": toss_and_match_wins,
        "observed_toss_win_rate": round(p_hat * 100, 2),
        "expected_win_rate": 50.0,
        "z_score": round(z_score, 4),
        "p_value": round(p_value, 4),
        "is_significant": is_significant,
        "null_hypothesis": "Winning the toss does not affect winning the match (p = 0.50)",
        "alternative_hypothesis": "Winning the toss significantly affects winning the match (p ≠ 0.50)",
        "conclusion": conclusion,
        "explanation": explanation,
        "toss_decision_breakdown": {
            "BAT": {
                "count": bat_count,
                "wins": bat_wins,
                "win_rate": round((bat_wins / bat_count * 100), 2) if bat_count > 0 else 0.0,
            },
            "BOWL": {
                "count": bowl_count,
                "wins": bowl_wins,
                "win_rate": round((bowl_wins / bowl_count * 100), 2) if bowl_count > 0 else 0.0,
            },
        },
    }


def compute_bat_bowl_first_analysis(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates historical win rates and average scores for batting 1st vs bowling 1st (chasing).
    """
    n = len(matches)
    if n == 0:
        return {
            "total_matches": 0,
            "bat_first_wins": 0,
            "bowl_first_wins": 0,
            "bat_first_win_rate": 0.0,
            "bowl_first_win_rate": 0.0,
            "avg_first_innings_score": 0.0,
            "avg_second_innings_score": 0.0,
            "best_strategy": "Insufficient Data",
            "explanation": "No completed matches recorded.",
            "comparison_chart": [],
        }

    bat_first_wins = 0
    bowl_first_wins = 0
    inn1_scores: List[int] = []
    inn2_scores: List[int] = []

    for m in matches:
        bat_first_team = m.get("bat_first_user_id")
        winner = m.get("winner_user_id")
        score1 = m.get("innings1_runs")
        score2 = m.get("innings2_runs")

        if score1 is not None and score1 > 0:
            inn1_scores.append(score1)
        if score2 is not None and score2 > 0:
            inn2_scores.append(score2)

        if winner and bat_first_team:
            if winner == bat_first_team:
                bat_first_wins += 1
            else:
                bowl_first_wins += 1

    decisive_matches = bat_first_wins + bowl_first_wins
    bat_first_pct = round((bat_first_wins / decisive_matches * 100), 2) if decisive_matches > 0 else 50.0
    bowl_first_pct = round((bowl_first_wins / decisive_matches * 100), 2) if decisive_matches > 0 else 50.0

    avg_inn1 = round(float(np.mean(inn1_scores)), 2) if inn1_scores else 0.0
    avg_inn2 = round(float(np.mean(inn2_scores)), 2) if inn2_scores else 0.0

    if bat_first_pct > bowl_first_pct:
        best_strategy = "Bat First"
        explanation = (
            f"Teams defending a target won {bat_first_pct}% of matches with an average first-innings score of {avg_inn1}. "
            f"Setting a defendable target is historically more advantageous."
        )
    elif bowl_first_pct > bat_first_pct:
        best_strategy = "Bowl First"
        explanation = (
            f"Teams chasing won {bowl_first_pct}% of matches with an average target of {avg_inn1}. "
            f"Chasing under controlled run-rate demands is historically the winning strategy."
        )
    else:
        best_strategy = "Balanced"
        explanation = (
            f"Both batting first and bowling first hold an identical 50.0% win rate across {decisive_matches} completed matches."
        )

    comparison_chart = [
        {"strategy": "Bat First", "wins": bat_first_wins, "win_rate": bat_first_pct, "avg_score": avg_inn1},
        {"strategy": "Bowl First (Chase)", "wins": bowl_first_wins, "win_rate": bowl_first_pct, "avg_score": avg_inn2},
    ]

    return {
        "total_matches": n,
        "decisive_matches": decisive_matches,
        "bat_first_wins": bat_first_wins,
        "bowl_first_wins": bowl_first_wins,
        "bat_first_win_rate": bat_first_pct,
        "bowl_first_win_rate": bowl_first_pct,
        "avg_first_innings_score": avg_inn1,
        "avg_second_innings_score": avg_inn2,
        "best_strategy": best_strategy,
        "explanation": explanation,
        "comparison_chart": comparison_chart,
    }


def compute_team_rating_correlation(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes Pearson Correlation between Team Rating (differential) and Winning probability.
    Also fits an Ordinary Least Squares (OLS) linear regression model.
    """
    n = len(matches)
    scatter_points: List[Dict[str, Any]] = []

    diffs: List[float] = []
    outcomes: List[float] = []

    for m in matches:
        t1_rating = float(m.get("team1_rating", 0.0))
        t2_rating = float(m.get("team2_rating", 0.0))
        winner = m.get("winner_user_id")
        t1_id = m.get("team1_user_id")
        t2_id = m.get("team2_user_id")
        margin = m.get("result_margin", "")

        if t1_rating > 0 and t2_rating > 0:
            t1_won = 1.0 if winner == t1_id else 0.0
            t2_won = 1.0 if winner == t2_id else 0.0

            # Record Team 1 perspective
            diff_1 = t1_rating - t2_rating
            diffs.append(diff_1)
            outcomes.append(t1_won)
            scatter_points.append({
                "match_id": m.get("id"),
                "team_rating": round(t1_rating, 2),
                "opponent_rating": round(t2_rating, 2),
                "rating_diff": round(diff_1, 2),
                "won": t1_won == 1.0,
                "team_name": m.get("team1_name", "Team 1"),
                "margin": margin,
            })

            # Record Team 2 perspective
            diff_2 = t2_rating - t1_rating
            diffs.append(diff_2)
            outcomes.append(t2_won)
            scatter_points.append({
                "match_id": m.get("id"),
                "team_rating": round(t2_rating, 2),
                "opponent_rating": round(t1_rating, 2),
                "rating_diff": round(diff_2, 2),
                "won": t2_won == 1.0,
                "team_name": m.get("team2_name", "Team 2"),
                "margin": margin,
            })

    if len(diffs) < 2:
        return {
            "sample_size": len(diffs),
            "correlation_coefficient": 0.0,
            "p_value": 1.0,
            "strength": "Insufficient Data",
            "direction": "None",
            "r_squared": 0.0,
            "regression_slope": 0.0,
            "regression_intercept": 0.5,
            "interpretation": "Insufficient match data to compute correlation between team ratings and victory.",
            "scatter_points": [],
        }

    diffs_arr = np.array(diffs)
    outcomes_arr = np.array(outcomes)

    # Check for zero variance
    if np.std(diffs_arr) == 0 or np.std(outcomes_arr) == 0:
        r, p_val = 0.0, 1.0
        slope, intercept = 0.0, 0.5
    else:
        r, p_val = stats.pearsonr(diffs_arr, outcomes_arr)
        slope, intercept, r_value, _, _ = stats.linregress(diffs_arr, outcomes_arr)

    abs_r = abs(r)
    if abs_r >= 0.70:
        strength = "Strong"
    elif abs_r >= 0.35:
        strength = "Moderate"
    elif abs_r >= 0.10:
        strength = "Weak"
    else:
        strength = "Negligible"

    direction = "Positive" if r > 0 else ("Negative" if r < 0 else "Zero")

    interpretation = (
        f"Pearson r = {r:.3f} indicates a {strength.lower()} {direction.lower()} relationship between "
        f"team rating advantage and match victory (R² = {r**2:.3f}, p = {p_val:.4f}). "
        f"{'Higher-rated teams consistently achieve higher victory probabilities.' if r > 0 else 'Team rating differences currently exhibit limited separation.'}"
    )

    return {
        "sample_size": len(diffs),
        "correlation_coefficient": round(float(r), 4),
        "p_value": round(float(p_val), 4),
        "strength": strength,
        "direction": direction,
        "r_squared": round(float(r ** 2), 4),
        "regression_slope": round(float(slope), 5),
        "regression_intercept": round(float(intercept), 4),
        "interpretation": interpretation,
        "scatter_points": scatter_points[:100],  # Return up to 100 points for crisp visual
    }


def compute_player_outliers(players_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Standardized Z-Score Anomaly & Outlier Detection across historical player performances.
    Categorizes players based on Z-Scores:
    Z > +2.0  -> Elite Performer (Upper Outlier)
    Z < -2.0  -> Underperformer (Lower Outlier)
    -2 <= Z <= 2 -> Consistent Performer
    """
    if not players_data:
        return {
            "total_players": 0,
            "mean_impact": 0.0,
            "std_impact": 0.0,
            "elite_count": 0,
            "underperformer_count": 0,
            "players": [],
        }

    # Extract Impact scores
    impact_scores = [float(p.get("impact_points", 0.0)) for p in players_data]
    mean_val = float(np.mean(impact_scores))
    std_val = float(np.std(impact_scores))

    processed_players = []
    elite_count = 0
    underperformer_count = 0

    for p in players_data:
        raw_val = float(p.get("impact_points", 0.0))
        z = (raw_val - mean_val) / std_val if std_val > 0 else 0.0

        if z > 2.0:
            category = "Elite Performer"
            badge = "emerald"
            elite_count += 1
        elif z < -2.0:
            category = "Underperformer"
            badge = "rose"
            underperformer_count += 1
        else:
            category = "Consistent Performer"
            badge = "sky"

        processed_players.append({
            "player_id": p.get("player_id"),
            "player_name": p.get("player_name"),
            "country": p.get("country", "Unknown"),
            "matches_played": p.get("matches_played", 1),
            "total_runs": p.get("total_runs", 0),
            "batting_avg": round(float(p.get("batting_avg", 0.0)), 2),
            "strike_rate": round(float(p.get("strike_rate", 0.0)), 2),
            "total_wickets": p.get("total_wickets", 0),
            "bowling_avg": round(float(p.get("bowling_avg", 0.0)), 2),
            "economy": round(float(p.get("economy", 0.0)), 2),
            "average_impact": round(raw_val, 2),
            "z_score": round(float(z), 3),
            "category": category,
            "badge": badge,
        })

    # Sort descending by Z-Score
    processed_players.sort(key=lambda x: x["z_score"], reverse=True)

    return {
        "total_players": len(processed_players),
        "mean_impact": round(mean_val, 2),
        "std_impact": round(std_val, 2),
        "elite_count": elite_count,
        "underperformer_count": underperformer_count,
        "players": processed_players,
    }


def compute_match_distributions(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes complete central tendency and dispersion metrics:
    Mean, Median, Mode, Variance, Standard Deviation, IQR, Min, Max.
    Includes binned score distributions (Histograms) and Box Plot quantiles.
    """
    if not matches:
        empty_dist = {
            "mean": 0.0, "median": 0.0, "mode": 0.0,
            "variance": 0.0, "std_dev": 0.0, "min": 0, "max": 0,
            "q1": 0.0, "q3": 0.0, "iqr": 0.0,
        }
        return {
            "total_matches": 0,
            "total_score": empty_dist,
            "first_innings_score": empty_dist,
            "second_innings_score": empty_dist,
            "total_wickets": empty_dist,
            "highest_score": 0,
            "lowest_score": 0,
            "average_strike_rate": 0.0,
            "average_run_rate": 0.0,
            "average_wickets": 0.0,
            "score_histogram": [],
            "boxplot_data": [],
        }

    total_scores = []
    inn1_scores = []
    inn2_scores = []
    wickets_list = []
    run_rates = []
    strike_rates = []

    for m in matches:
        s1 = m.get("innings1_runs", 0) or 0
        s2 = m.get("innings2_runs", 0) or 0
        w1 = m.get("innings1_wickets", 0) or 0
        w2 = m.get("innings2_wickets", 0) or 0
        o1 = float(m.get("innings1_overs", 20.0) or 20.0)
        o2 = float(m.get("innings2_overs", 20.0) or 20.0)

        tot = s1 + s2
        w_tot = w1 + w2

        if s1 > 0:
            inn1_scores.append(s1)
            if o1 > 0:
                run_rates.append(s1 / o1)
        if s2 > 0:
            inn2_scores.append(s2)
            if o2 > 0:
                run_rates.append(s2 / o2)

        if tot > 0:
            total_scores.append(tot)
            wickets_list.append(w_tot)

        # Average match batter SR
        sr_val = m.get("avg_match_strike_rate")
        if sr_val:
            strike_rates.append(float(sr_val))

    def get_stats_dict(data: List[int]) -> Dict[str, Any]:
        if not data:
            return {
                "mean": 0.0, "median": 0.0, "mode": 0.0,
                "variance": 0.0, "std_dev": 0.0, "min": 0, "max": 0,
                "q1": 0.0, "q3": 0.0, "iqr": 0.0,
            }
        arr = np.array(data, dtype=float)
        mode_res = stats.mode(arr, keepdims=False)
        mode_val = float(mode_res.mode) if hasattr(mode_res, "mode") else float(mode_res[0])
        q1 = float(np.percentile(arr, 25))
        q3 = float(np.percentile(arr, 75))

        return {
            "mean": round(float(np.mean(arr)), 2),
            "median": round(float(np.median(arr)), 2),
            "mode": round(mode_val, 2),
            "variance": round(float(np.var(arr, ddof=1 if len(arr) > 1 else 0)), 2),
            "std_dev": round(float(np.std(arr, ddof=1 if len(arr) > 1 else 0)), 2),
            "min": int(np.min(arr)),
            "max": int(np.max(arr)),
            "q1": round(q1, 2),
            "q3": round(q3, 2),
            "iqr": round(q3 - q1, 2),
        }

    total_dist = get_stats_dict(total_scores)
    inn1_dist = get_stats_dict(inn1_scores)
    inn2_dist = get_stats_dict(inn2_scores)
    wickets_dist = get_stats_dict(wickets_list)

    # Score distribution histogram (binned into 6 standard T20 intervals)
    all_innings = inn1_scores + inn2_scores
    bins = [0, 120, 140, 160, 180, 200, 300]
    bin_labels = ["< 120", "120 - 139", "140 - 159", "160 - 179", "180 - 199", "200+"]
    hist_counts, _ = np.histogram(all_innings if all_innings else [0], bins=bins)

    histogram_data = [
        {"range": label, "count": int(count), "percentage": round((count / len(all_innings) * 100), 1) if all_innings else 0.0}
        for label, count in zip(bin_labels, hist_counts)
    ]

    # Boxplot representation for Visualizations
    boxplot_data = [
        {"category": "1st Innings", **inn1_dist},
        {"category": "2nd Innings", **inn2_dist},
        {"category": "Match Total", **total_dist},
    ]

    highest_score = max(all_innings) if all_innings else 0
    lowest_score = min(all_innings) if all_innings else 0
    avg_sr = round(float(np.mean(strike_rates)), 2) if strike_rates else (round(float(np.mean(all_innings) / 120 * 100), 2) if all_innings else 125.0)
    avg_rr = round(float(np.mean(run_rates)), 2) if run_rates else (round(avg_sr / 100 * 6, 2))
    avg_wkts = round(float(np.mean(wickets_list)), 2) if wickets_list else 0.0

    return {
        "total_matches": len(matches),
        "total_score": total_dist,
        "first_innings_score": inn1_dist,
        "second_innings_score": inn2_dist,
        "total_wickets": wickets_dist,
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "average_strike_rate": avg_sr,
        "average_run_rate": avg_rr,
        "average_wickets": avg_wkts,
        "score_histogram": histogram_data,
        "boxplot_data": boxplot_data,
    }


def compute_correlation_matrix(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes pairwise Pearson correlation coefficients between 6 core cricket dimensions:
    1. Team Rating
    2. Toss Win
    3. Match Win
    4. Total Runs
    5. Wickets Fallen
    6. Strike Rate / Run Rate
    """
    labels = ["Team Rating", "Toss Won", "Match Won", "Total Runs", "Wickets", "Run Rate"]

    if len(matches) < 3:
        # Default identity matrix if insufficient samples
        matrix = [[1.0 if i == j else 0.0 for j in range(6)] for i in range(6)]
        return {"labels": labels, "matrix": matrix, "sample_size": len(matches)}

    rows = []
    for m in matches:
        t1_rating = float(m.get("team1_rating", 75.0))
        t2_rating = float(m.get("team2_rating", 75.0))
        winner = m.get("winner_user_id")
        toss_winner = m.get("toss_winner_id")
        t1_id = m.get("team1_user_id")
        t2_id = m.get("team2_user_id")
        s1 = float(m.get("innings1_runs", 150) or 150)
        s2 = float(m.get("innings2_runs", 145) or 145)
        w1 = float(m.get("innings1_wickets", 6) or 6)
        w2 = float(m.get("innings2_wickets", 6) or 6)
        o1 = float(m.get("innings1_overs", 20.0) or 20.0)
        o2 = float(m.get("innings2_overs", 20.0) or 20.0)

        # Team 1 vector
        rows.append([
            t1_rating,
            1.0 if toss_winner == t1_id else 0.0,
            1.0 if winner == t1_id else 0.0,
            s1,
            w1,
            round(s1 / max(1.0, o1), 2),
        ])
        # Team 2 vector
        rows.append([
            t2_rating,
            1.0 if toss_winner == t2_id else 0.0,
            1.0 if winner == t2_id else 0.0,
            s2,
            w2,
            round(s2 / max(1.0, o2), 2),
        ])

    df = pd.DataFrame(rows, columns=labels)
    corr_df = df.corr().fillna(0.0)

    matrix = []
    for i, row_label in enumerate(labels):
        row_vals = []
        for j, col_label in enumerate(labels):
            val = float(corr_df.loc[row_label, col_label])
            row_vals.append(round(val, 3))
        matrix.append(row_vals)

    return {
        "labels": labels,
        "matrix": matrix,
        "sample_size": len(rows),
    }
