"""
Module: extract_stats.py
Description: Extracts decade-wise T20 International statistics for all players
             from Cricsheet match JSON files using multiprocessing.
             Outputs dataset/output/player_decade_stats.csv.
"""

import json
import logging
import math
import os
from collections import defaultdict
from dataclasses import dataclass, field
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from tqdm import tqdm

logger = logging.getLogger(__name__)

# Wicket types credited to the bowler
BOWLER_WICKET_KINDS: Set[str] = {
    "bowled",
    "caught",
    "caught and bowled",
    "lbw",
    "stumped",
    "hit wicket",
}


@dataclass
class BattingInningsRecord:
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    dots: int = 0
    dismissed: bool = False


@dataclass
class BowlingInningsRecord:
    balls: int = 0
    runs: int = 0
    wickets: int = 0
    maidens: int = 0


def is_t20_international(info: Dict[str, Any]) -> bool:
    """Determine whether the match is a T20 International."""
    match_type = str(info.get("match_type", "")).strip().upper()
    team_type = str(info.get("team_type", "")).strip().lower()

    if match_type == "IT20":
        return True
    if match_type == "T20" and team_type == "international":
        return True
    return False


def get_match_decade(info: Dict[str, Any]) -> Optional[int]:
    """Extract match year and return the decade (e.g. 1980, 1990, 2000, 2010, 2020)."""
    dates = info.get("dates", [])
    if not dates or not isinstance(dates, list):
        return None
    try:
        first_date = str(dates[0])
        year = int(first_date.split("-")[0])
        decade = (year // 10) * 10
        if decade in {1980, 1990, 2000, 2010, 2020}:
            return decade
    except (ValueError, IndexError):
        return None
    return None


def parse_single_match(file_path: str) -> Optional[Dict[Tuple[str, str, int], Dict[str, Any]]]:
    """
    Parses a single Cricsheet JSON file for T20I matches and computes
    per-player match statistics.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            match_data = json.load(f)
    except Exception:
        return None

    if not isinstance(match_data, dict):
        return None

    info = match_data.get("info", {})
    if not is_t20_international(info):
        return None

    decade = get_match_decade(info)
    if decade is None:
        return None

    players_by_team = info.get("players", {})

    # Map player -> country for this match
    player_to_country: Dict[str, str] = {}
    for team, p_list in players_by_team.items():
        for p in p_list:
            player_to_country[p] = team

    # Tracking per player for this specific match
    match_batting: Dict[str, BattingInningsRecord] = {}
    match_bowling: Dict[str, BowlingInningsRecord] = {}
    match_fielding: Dict[str, Dict[str, int]] = defaultdict(lambda: {"catches": 0, "stumpings": 0, "run_outs": 0})
    batted_players: Set[str] = set()

    innings = match_data.get("innings", [])
    for inn in innings:
        if not isinstance(inn, dict):
            continue

        # Track bowler overs for maidens calculation: bowler -> over_num -> {runs: int, legal_balls: int}
        bowler_overs: Dict[str, Dict[int, Dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"runs": 0, "legal_balls": 0}))

        overs = inn.get("overs", [])
        for over_idx, over_obj in enumerate(overs):
            if not isinstance(over_obj, dict):
                continue
            over_num = over_obj.get("over", over_idx)
            deliveries = over_obj.get("deliveries", [])
            for deliv in deliveries:
                if not isinstance(deliv, dict):
                    continue

                batter = deliv.get("batter")
                bowler = deliv.get("bowler")
                runs_info = deliv.get("runs", {})
                extras_info = deliv.get("extras", {})

                batter_runs = int(runs_info.get("batter", 0))
                wides = int(extras_info.get("wides", 0))
                noballs = int(extras_info.get("noballs", 0))

                # Batting stats
                if batter:
                    batted_players.add(batter)
                    if batter not in match_batting:
                        match_batting[batter] = BattingInningsRecord()

                    if wides == 0:
                        match_batting[batter].balls += 1
                        if batter_runs == 0:
                            match_batting[batter].dots += 1

                    match_batting[batter].runs += batter_runs
                    if batter_runs == 4:
                        match_batting[batter].fours += 1
                    elif batter_runs == 6:
                        match_batting[batter].sixes += 1

                # Bowling stats
                if bowler:
                    if bowler not in match_bowling:
                        match_bowling[bowler] = BowlingInningsRecord()

                    bowler_runs_conceded = batter_runs + wides + noballs
                    match_bowling[bowler].runs += bowler_runs_conceded

                    is_legal_ball = (wides == 0 and noballs == 0)
                    if is_legal_ball:
                        match_bowling[bowler].balls += 1

                    bowler_overs[bowler][over_num]["runs"] += bowler_runs_conceded
                    if is_legal_ball:
                        bowler_overs[bowler][over_num]["legal_balls"] += 1

                # Wickets & Fielding
                wickets = deliv.get("wickets", [])
                for w in wickets:
                    if not isinstance(w, dict):
                        continue
                    kind = str(w.get("kind", "")).lower()
                    player_out = w.get("player_out")

                    if player_out:
                        batted_players.add(player_out)
                        if player_out not in match_batting:
                            match_batting[player_out] = BattingInningsRecord()
                        match_batting[player_out].dismissed = True

                    if bowler and kind in BOWLER_WICKET_KINDS:
                        match_bowling[bowler].wickets += 1

                    fielders = w.get("fielders", [])
                    if kind == "caught":
                        for f_info in fielders:
                            f_name = f_info.get("name") if isinstance(f_info, dict) else str(f_info)
                            if f_name:
                                match_fielding[f_name]["catches"] += 1
                    elif kind == "caught and bowled":
                        if bowler:
                            match_fielding[bowler]["catches"] += 1
                    elif kind == "stumped":
                        for f_info in fielders:
                            f_name = f_info.get("name") if isinstance(f_info, dict) else str(f_info)
                            if f_name:
                                match_fielding[f_name]["stumpings"] += 1
                    elif kind == "run out":
                        for f_info in fielders:
                            f_name = f_info.get("name") if isinstance(f_info, dict) else str(f_info)
                            if f_name:
                                match_fielding[f_name]["run_outs"] += 1

        # Calculate maidens for this innings
        for bowler_name, overs_dict in bowler_overs.items():
            for o_num, o_stats in overs_dict.items():
                if o_stats["legal_balls"] >= 6 and o_stats["runs"] == 0:
                    match_bowling[bowler_name].maidens += 1

    # Aggregate all players who took part in this match
    match_result: Dict[Tuple[str, str, int], Dict[str, Any]] = {}

    all_players: Set[str] = set()
    for team, p_list in players_by_team.items():
        for p in p_list:
            all_players.add(p)

    for p in set(match_batting.keys()) | set(match_bowling.keys()) | set(match_fielding.keys()):
        all_players.add(p)

    for p in all_players:
        country = player_to_country.get(p, "Unknown")
        key = (p, country, decade)

        bat_rec = match_batting.get(p)
        bowl_rec = match_bowling.get(p)
        fld_dict = match_fielding.get(p, {"catches": 0, "stumpings": 0, "run_outs": 0})

        match_result[key] = {
            "matches": 1,
            "batting": {
                "runs": bat_rec.runs,
                "balls": bat_rec.balls,
                "fours": bat_rec.fours,
                "sixes": bat_rec.sixes,
                "dots": bat_rec.dots,
                "dismissed": bat_rec.dismissed,
                "batted": p in batted_players,
            } if bat_rec or (p in batted_players) else None,
            "bowling": {
                "balls": bowl_rec.balls,
                "runs": bowl_rec.runs,
                "wickets": bowl_rec.wickets,
                "maidens": bowl_rec.maidens,
            } if bowl_rec else None,
            "fielding": fld_dict,
        }

    return match_result


def parse_batch_files(file_paths: List[str]) -> List[Dict[Tuple[str, str, int], Dict[str, Any]]]:
    """Parse a batch of files in a worker process."""
    results = []
    for fp in file_paths:
        res = parse_single_match(fp)
        if res:
            results.append(res)
    return results


class PlayerNameResolver:
    """
    Intelligently resolves scorecard player names to official Best XI player names
    using exact matches, initial+last name pairings, and unique country surname lookups.
    """
    def __init__(self, players_df: pd.DataFrame) -> None:
        self.exact_map: Dict[Tuple[str, str], str] = {}
        self.initial_last_map: Dict[Tuple[str, str, str], str] = {}
        self.unique_last_map: Dict[Tuple[str, str], str] = {}

        country_last_counts: Dict[Tuple[str, str], List[str]] = defaultdict(list)

        for _, row in players_df.iterrows():
            official_name = str(row["player_name"]).strip()
            country = str(row["country"]).strip().lower()
            self.exact_map[(official_name.lower(), country)] = official_name

            parts = official_name.split()
            if len(parts) >= 2:
                last_name = parts[-1].lower()
                first_initial = parts[0][0].lower()
                self.initial_last_map[(first_initial, last_name, country)] = official_name
                country_last_counts[(last_name, country)].append(official_name)

                # Special two-part surname handling (e.g. de Kock, de Silva, Al Hasan)
                if len(parts) >= 3 and parts[-2].lower() in {"de", "al", "van", "du"}:
                    compound_last = f"{parts[-2]} {parts[-1]}".lower()
                    self.initial_last_map[(first_initial, compound_last, country)] = official_name
                    country_last_counts[(compound_last, country)].append(official_name)

        # Build unique last name mapping
        for (last_name, country), names in country_last_counts.items():
            if len(set(names)) == 1:
                self.unique_last_map[(last_name, country)] = names[0]

    def resolve(self, scorecard_name: str, country: str) -> str:
        c_clean = country.strip().lower()
        sc_clean = scorecard_name.strip()
        sc_lower = sc_clean.lower()

        # 1. Exact match
        if (sc_lower, c_clean) in self.exact_map:
            return self.exact_map[(sc_lower, c_clean)]

        # 2. Match by Initial + Last Name
        parts = sc_clean.split()
        if len(parts) >= 2:
            first_initial = parts[0][0].lower()
            last_name = parts[-1].lower()

            key = (first_initial, last_name, c_clean)
            if key in self.initial_last_map:
                return self.initial_last_map[key]

            # Compound surname check
            if len(parts) >= 3 and parts[-2].lower() in {"de", "al", "van", "du"}:
                comp_key = (first_initial, f"{parts[-2]} {parts[-1]}".lower(), c_clean)
                if comp_key in self.initial_last_map:
                    return self.initial_last_map[comp_key]

            # 3. Unique surname within country check
            if (last_name, c_clean) in self.unique_last_map:
                return self.unique_last_map[(last_name, c_clean)]

        return sc_clean


def extract_decade_statistics(
    data_dir: Optional[Path] = None,
    output_path: Optional[Path] = None,
    players_csv_path: Optional[Path] = None,
    num_processes: Optional[int] = None,
) -> pd.DataFrame:
    """
    Scans all JSON files in data_dir, extracts T20I decade-wise stats using multiprocessing,
    and writes player_decade_stats.csv to output_path.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if data_dir is None:
        data_dir = base_dir / "data"
    if output_path is None:
        output_path = base_dir / "output" / "player_decade_stats.csv"
    if players_csv_path is None:
        players_csv_path = base_dir / "output" / "players.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    json_files = [str(p) for p in data_dir.glob("*.json")]
    logger.info("Found %d JSON files to inspect in %s", len(json_files), data_dir)

    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {data_dir}")

    # Build intelligent player name resolver
    resolver = None
    if players_csv_path.exists():
        try:
            p_df = pd.read_csv(players_csv_path)
            resolver = PlayerNameResolver(p_df)
            logger.info("Initialized intelligent player name resolver.")
        except Exception as e:
            logger.warning("Could not initialize name resolver: %s", e)

    cpu_cores = num_processes or max(1, cpu_count() - 1)
    batch_size = max(50, len(json_files) // (cpu_cores * 4))
    batches = [json_files[i : i + batch_size] for i in range(0, len(json_files), batch_size)]

    logger.info("Processing with %d processes across %d batches...", cpu_cores, len(batches))

    master_stats: Dict[Tuple[str, str, int], Dict[str, Any]] = defaultdict(lambda: {
        "matches": 0,
        "innings": 0,
        "not_outs": 0,
        "runs": 0,
        "balls_faced": 0,
        "fours": 0,
        "sixes": 0,
        "dot_balls": 0,
        "innings_scores": [],
        "wickets": 0,
        "balls_bowled": 0,
        "runs_conceded": 0,
        "maidens": 0,
        "bowling_innings_figs": [],
        "catches": 0,
        "stumpings": 0,
        "run_outs": 0,
    })

    with Pool(processes=cpu_cores) as pool:
        for batch_result in tqdm(pool.imap_unordered(parse_batch_files, batches), total=len(batches), desc="Parsing T20I Matches"):
            for match_dict in batch_result:
                for (p_name, country, decade), p_data in match_dict.items():
                    resolved_name = resolver.resolve(p_name, country) if resolver else p_name.strip()

                    key = (resolved_name, country, decade)
                    stats = master_stats[key]
                    stats["matches"] += p_data["matches"]

                    bat = p_data.get("batting")
                    if bat is not None:
                        stats["innings"] += 1
                        if not bat["dismissed"]:
                            stats["not_outs"] += 1
                        stats["runs"] += bat["runs"]
                        stats["balls_faced"] += bat["balls"]
                        stats["fours"] += bat["fours"]
                        stats["sixes"] += bat["sixes"]
                        stats["dot_balls"] += bat["dots"]
                        stats["innings_scores"].append((bat["runs"], not bat["dismissed"]))

                    bowl = p_data.get("bowling")
                    if bowl is not None:
                        stats["balls_bowled"] += bowl["balls"]
                        stats["runs_conceded"] += bowl["runs"]
                        stats["wickets"] += bowl["wickets"]
                        stats["maidens"] += bowl["maidens"]
                        stats["bowling_innings_figs"].append((bowl["wickets"], bowl["runs"]))

                    fld = p_data.get("fielding", {})
                    stats["catches"] += fld.get("catches", 0)
                    stats["stumpings"] += fld.get("stumpings", 0)
                    stats["run_outs"] += fld.get("run_outs", 0)

    rows = []
    for (player_name, country, decade), stats in master_stats.items():
        runs = stats["runs"]
        balls_faced = stats["balls_faced"]
        innings = stats["innings"]
        not_outs = stats["not_outs"]
        fours = stats["fours"]
        sixes = stats["sixes"]
        dot_balls = stats["dot_balls"]

        strike_rate = round((runs / balls_faced * 100.0), 2) if balls_faced > 0 else 0.0

        dismissals = innings - not_outs
        if dismissals > 0:
            batting_avg = round(runs / dismissals, 2)
        elif innings > 0 and runs > 0:
            batting_avg = float(runs)
        else:
            batting_avg = 0.0

        dot_pct = round((dot_balls / balls_faced * 100.0), 2) if balls_faced > 0 else 0.0

        fifties = 0
        hundreds = 0
        highest_score = "0"
        max_r = -1
        max_no = False

        for r, no in stats["innings_scores"]:
            if r >= 100:
                hundreds += 1
            elif r >= 50:
                fifties += 1
            if r > max_r or (r == max_r and no and not max_no):
                max_r = r
                max_no = no

        if max_r >= 0:
            highest_score = f"{max_r}*" if max_no else str(max_r)

        balls_bowled = stats["balls_bowled"]
        runs_conceded = stats["runs_conceded"]
        wickets = stats["wickets"]
        maidens = stats["maidens"]

        overs_bowled = balls_bowled / 6.0
        economy = round(runs_conceded / overs_bowled, 2) if overs_bowled > 0 else 0.0
        bowling_avg = round(runs_conceded / wickets, 2) if wickets > 0 else 0.0
        bowling_sr = round(balls_bowled / wickets, 2) if wickets > 0 else 0.0

        best_bowling = "0/0"
        if stats["bowling_innings_figs"]:
            sorted_figs = sorted(stats["bowling_innings_figs"], key=lambda x: (-x[0], x[1]))
            best_w, best_r = sorted_figs[0]
            best_bowling = f"{best_w}/{best_r}"

        row_dict = {
            "player_name": player_name,
            "country": country,
            "decade": decade,
            "matches": stats["matches"],
            "innings": innings,
            "not_outs": not_outs,
            "runs": runs,
            "balls_faced": balls_faced,
            "highest_score": highest_score,
            "fifties": fifties,
            "hundreds": hundreds,
            "strike_rate": strike_rate,
            "batting_average": batting_avg,
            "fours": fours,
            "sixes": sixes,
            "dot_balls": dot_balls,
            "dot_ball_percentage": dot_pct,
            "wickets": wickets,
            "balls_bowled": balls_bowled,
            "runs_conceded": runs_conceded,
            "maidens": maidens,
            "economy": economy,
            "bowling_average": bowling_avg,
            "bowling_strike_rate": bowling_sr,
            "best_bowling": best_bowling,
            "catches": stats["catches"],
            "stumpings": stats["stumpings"],
            "run_outs": stats["run_outs"],
        }
        rows.append(row_dict)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by=["country", "decade", "player_name"]).reset_index(drop=True)

    df.to_csv(output_path, index=False)
    logger.info("Saved %d player decade statistics to %s", len(df), output_path)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    extract_decade_statistics()
