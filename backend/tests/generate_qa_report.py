"""
Detailed QA simulation printer.
Runs 20 matches and emits the full verbose report for each match plus the summary statistics.
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.qa_simulation_runner import QASimulationRunner

def main():
    runner = QASimulationRunner()
    reports = runner.run_all_20_matches()

    # Calculate Summary Statistics
    total_matches = len(reports)
    avg_inn1 = sum(runner.all_first_innings_runs) / max(1, len(runner.all_first_innings_runs))
    avg_inn2 = sum(runner.all_second_innings_runs) / max(1, len(runner.all_second_innings_runs))
    highest_score = max(runner.all_first_innings_runs + runner.all_second_innings_runs)
    lowest_score = min(runner.all_first_innings_runs + runner.all_second_innings_runs)
    avg_wickets = sum(runner.all_innings_wickets) / max(1, len(runner.all_innings_wickets))
    avg_sr = sum(runner.all_strike_rates) / max(1, len(runner.all_strike_rates))
    avg_econ = sum(runner.all_economies) / max(1, len(runner.all_economies))

    most_succ_batter = max(runner.player_runs_tally.items(), key=lambda x: x[1]) if runner.player_runs_tally else ("None", 0)
    most_succ_bowler = max(runner.player_wickets_tally.items(), key=lambda x: x[1]) if runner.player_wickets_tally else ("None", 0)
    most_common_dismissal = max(runner.dismissal_counts.items(), key=lambda x: x[1]) if runner.dismissal_counts else ("None", 0)

    bound_balls = runner.total_fours + runner.total_sixes
    bound_pct = (bound_balls / max(1, runner.total_balls_bowled)) * 100.0
    dot_pct = (runner.total_dots / max(1, runner.total_balls_bowled)) * 100.0

    pp_avg = (sum(runner.powerplay_runs_list) / max(1, len(runner.all_first_innings_runs) + len(runner.all_second_innings_runs)))
    death_avg = (sum(runner.death_runs_list) / max(1, len(runner.all_first_innings_runs) + len(runner.all_second_innings_runs)))

    summary_data = {
        "matches": reports,
        "summary": {
            "total_matches": total_matches,
            "avg_inn1": round(avg_inn1, 1),
            "avg_inn2": round(avg_inn2, 1),
            "highest_score": highest_score,
            "lowest_score": lowest_score,
            "avg_wickets": round(avg_wickets, 1),
            "avg_sr": round(avg_sr, 1),
            "avg_econ": round(avg_econ, 2),
            "most_succ_batter": f"{most_succ_batter[0]} ({most_succ_batter[1]} runs)",
            "most_succ_bowler": f"{most_succ_bowler[0]} ({most_succ_bowler[1]} wickets)",
            "most_common_dismissal": f"{most_common_dismissal[0]} ({most_common_dismissal[1]} dismissals)",
            "bound_pct": f"{bound_pct:.1f}%",
            "dot_pct": f"{dot_pct:.1f}%",
            "pp_avg": f"{pp_avg:.1f} runs / innings",
            "death_avg": f"{death_avg:.1f} runs / innings",
        }
    }

    with open("backend/tests/qa_report_data.json", "w") as f:
        json.dump(summary_data, f, indent=2)

    print("QA Report data successfully generated in backend/tests/qa_report_data.json")

if __name__ == "__main__":
    main()

