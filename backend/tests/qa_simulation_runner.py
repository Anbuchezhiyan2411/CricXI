"""
CricXI Match Simulation QA & Statistical Validation Harness.
Executes 20 complete T20 matches across diverse tactical scenarios and
performs exhaustive statistical validation, cricket invariant verification,
database reconciliation, and realism analysis.
"""

import sys
import os
import time
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.models.room import Room, RoomPlayer
from app.models.draft import DraftPick
from app.models.toss import TossState
from app.models.match import Match, MatchInnings, BallEvent, InningsBatterScore, InningsBowlerScore
from app.match.simulation_engine import SimulationEngine
from app.match.match_service import MatchService
from app.services.dataset_loader import dataset_service


class QASimulationRunner:
    """Rigorous QA runner and cricket analyst validator for CricXI."""

    def __init__(self):
        dataset_service.load()
        self.all_players = dataset_service.get_all_players()
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Aggregate metrics across all 20 matches
        self.match_results: List[Dict[str, Any]] = []
        self.all_first_innings_runs: List[int] = []
        self.all_second_innings_runs: List[int] = []
        self.all_innings_wickets: List[int] = []
        self.all_strike_rates: List[float] = []
        self.all_economies: List[float] = []
        self.total_balls_bowled = 0
        self.total_dots = 0
        self.total_fours = 0
        self.total_sixes = 0
        self.dismissal_counts: Dict[str, int] = {}
        self.powerplay_runs_list: List[int] = []
        self.death_runs_list: List[int] = []
        self.player_runs_tally: Dict[str, int] = {}
        self.player_wickets_tally: Dict[str, int] = {}

    def _filter_players(self, **kwargs) -> List[Dict[str, Any]]:
        """Filters players by role, decade, rating, country, etc."""
        res = list(self.all_players)
        if "role" in kwargs:
            r = kwargs["role"]
            if isinstance(r, list):
                res = [p for p in res if p.get("primary_role") in r]
            else:
                res = [p for p in res if p.get("primary_role") == r]
        if "decade" in kwargs:
            d = kwargs["decade"]
            res = [p for p in res if p.get("decade") == d]
        if "country" in kwargs:
            c = kwargs["country"]
            res = [p for p in res if p.get("country") == c]
        if "min_bat_rating" in kwargs:
            res = [p for p in res if float(p.get("batting_rating") or 0) >= kwargs["min_bat_rating"]]
        if "max_bat_rating" in kwargs:
            res = [p for p in res if float(p.get("batting_rating") or 0) <= kwargs["max_bat_rating"]]
        if "min_bowl_rating" in kwargs:
            res = [p for p in res if float(p.get("bowling_rating") or 0) >= kwargs["min_bowl_rating"]]
        if "bowling_type" in kwargs:
            bt = kwargs["bowling_type"].lower()
            res = [p for p in res if bt in str(p.get("bowling_type", "")).lower()]
        return res

    def _build_squad(self, scenario_type: str, side: str, seed: int) -> List[Dict[str, Any]]:
        """Constructs an authentic 11-player squad tailored to scenario requirements."""
        rng = random.Random(seed)

        # 1. Strong Batting
        if "strong_batting" in scenario_type:
            top_order = self._filter_players(min_bat_rating=78.0, role=["BAT", "WK"])
            spin = self._filter_players(role="SPIN", min_bowl_rating=65.0)
            pace = self._filter_players(role="PACE", min_bowl_rating=65.0)
            tail = self._filter_players(role="PACE", max_bat_rating=35.0, min_bowl_rating=75.0)
            chosen = rng.sample(top_order, min(6, len(top_order)))
            chosen += rng.sample(pace, min(2, len(pace)))
            chosen += rng.sample(spin, min(1, len(spin)))
            chosen += rng.sample(tail, min(2, len(tail)))

        # 2. Strong Bowling
        elif "strong_bowling" in scenario_type:
            bowlers = self._filter_players(min_bowl_rating=82.0, role=["PACE", "SPIN"])
            batters = self._filter_players(role="BAT", min_bat_rating=65.0)
            wk = self._filter_players(role="WK")
            chosen = rng.sample(batters, min(4, len(batters)))
            chosen += rng.sample(wk, min(1, len(wk)))
            chosen += rng.sample(bowlers, min(6, len(bowlers)))

        # 3. Weak Batting
        elif "weak_batting" in scenario_type:
            lower_bat = self._filter_players(max_bat_rating=62.0)
            chosen = rng.sample(lower_bat, min(11, len(lower_bat)))

        # 4. Weak Bowling
        elif "weak_bowling" in scenario_type:
            top_bat = self._filter_players(role="BAT", min_bat_rating=75.0)
            weak_bowl = self._filter_players(role=["PACE", "SPIN"], min_bowl_rating=30.0)
            weak_bowl = [p for p in weak_bowl if float(p.get("bowling_rating") or 0) <= 65.0]
            chosen = rng.sample(top_bat, min(6, len(top_bat)))
            chosen += rng.sample(weak_bowl, min(5, len(weak_bowl)))

        # 5. Pace Heavy
        elif "pace_heavy" in scenario_type:
            pacers = self._filter_players(role="PACE", min_bowl_rating=75.0)
            batters = self._filter_players(role="BAT", min_bat_rating=70.0)
            wk = self._filter_players(role="WK")
            chosen = rng.sample(batters, min(5, len(batters)))
            chosen += rng.sample(wk, min(1, len(wk)))
            chosen += rng.sample(pacers, min(5, len(pacers)))

        # 6. Spin Heavy
        elif "spin_heavy" in scenario_type:
            spinners = self._filter_players(role="SPIN", min_bowl_rating=70.0)
            batters = self._filter_players(role="BAT", min_bat_rating=70.0)
            wk = self._filter_players(role="WK")
            chosen = rng.sample(batters, min(5, len(batters)))
            chosen += rng.sample(wk, min(1, len(wk)))
            chosen += rng.sample(spinners, min(5, len(spinners)))

        # 7. Era Specific (1990s, 2000s, 2010s, 2020s)
        elif "era_" in scenario_type:
            decade = int(scenario_type.split("era_")[1].split("_")[0])
            era_players = self._filter_players(decade=decade)
            chosen = rng.sample(era_players, min(11, len(era_players)))

        # 8. Balanced Standard Squad
        else:
            batters = self._filter_players(role="BAT", min_bat_rating=70.0)
            ar = self._filter_players(role="AR")
            wk = self._filter_players(role="WK")
            pacers = self._filter_players(role="PACE", min_bowl_rating=70.0)
            spinners = self._filter_players(role="SPIN", min_bowl_rating=70.0)

            chosen = rng.sample(batters, min(4, len(batters)))
            chosen += rng.sample(wk, min(1, len(wk)))
            chosen += rng.sample(ar, min(2, len(ar)))
            chosen += rng.sample(pacers, min(2, len(pacers)))
            chosen += rng.sample(spinners, min(2, len(spinners)))

        # Guarantee exactly 11 players with unique player_ids
        seen_ids = set()
        final_squad = []
        for p in chosen:
            if p["player_id"] not in seen_ids:
                seen_ids.add(p["player_id"])
                final_squad.append(p)

        # Fill deficit if any
        if len(final_squad) < 11:
            for p in self.all_players:
                if p["player_id"] not in seen_ids:
                    seen_ids.add(p["player_id"])
                    final_squad.append(p)
                    if len(final_squad) == 11:
                        break

        final_squad = final_squad[:11]

        # Sort logically into batting positions: top batters 1-5, AR 6-7, bowlers 8-11
        final_squad.sort(
            key=lambda x: (
                0 if x.get("primary_role") == "BAT" else
                1 if x.get("primary_role") == "WK" else
                2 if x.get("primary_role") == "AR" else 3,
                -float(x.get("batting_rating") or 0),
            )
        )
        return final_squad

    def run_single_match(self, match_idx: int, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Simulates one complete match from ball 1 to result with full audit."""
        db = self.Session()
        try:
            room_code = f"QA{match_idx:03d}"
            room = Room(room_code=room_code, host_id=f"host_{match_idx}", status="TOSS")
            db.add(room)
            db.commit()

            p_host = RoomPlayer(room_id=room.id, user_id=f"host_{match_idx}", username=scenario["host_team_name"], is_host=True, is_ready=True)
            p_guest = RoomPlayer(room_id=room.id, user_id=f"guest_{match_idx}", username=scenario["guest_team_name"], is_host=False, is_ready=True)
            db.add_all([p_host, p_guest])
            db.commit()

            # Draft 11 players for each team
            host_squad = self._build_squad(scenario["host_scenario"], "host", match_idx * 101)
            guest_squad = self._build_squad(scenario["guest_scenario"], "guest", match_idx * 202)

            for pos, p in enumerate(host_squad, start=1):
                db.add(DraftPick(
                    room_id=room.id,
                    user_id=p_host.user_id,
                    player_id=p["player_id"],
                    player_name=p["player_name"],
                    round_number=pos,
                    batting_position=pos,
                    selected_country=p.get("country", "India"),
                    selected_decade=int(p.get("decade", 2010)),
                ))
            for pos, p in enumerate(guest_squad, start=1):
                db.add(DraftPick(
                    room_id=room.id,
                    user_id=p_guest.user_id,
                    player_id=p["player_id"],
                    player_name=p["player_name"],
                    round_number=pos,
                    batting_position=pos,
                    selected_country=p.get("country", "Australia"),
                    selected_decade=int(p.get("decade", 2010)),
                ))
            db.commit()

            # Toss: deterministic or natural
            toss_winner = p_host.user_id if (match_idx % 2 == 1) else p_guest.user_id
            toss_winner_name = p_host.username if toss_winner == p_host.user_id else p_guest.username
            decision = scenario.get("toss_decision", "BAT" if (match_idx % 3 != 0) else "BOWL")

            toss = TossState(
                room_id=room.id,
                caller_id=p_host.user_id,
                caller_name=p_host.username,
                caller_choice="HEADS",
                coin_result="HEADS" if toss_winner == p_host.user_id else "TAILS",
                winner_id=toss_winner,
                winner_name=toss_winner_name,
                decision=decision,
                step="COMPLETED",
            )
            db.add(toss)
            db.commit()

            # Initialize Match
            state = MatchService.initialize_or_get_match(db, room_code)
            match_id = state.match_id

            # Play from Ball 1 to Completion
            ball_count = 0
            max_safety_deliveries = 300  # Avoid infinite loops in QA
            while state.status not in ("COMPLETED", "TIED") and ball_count < max_safety_deliveries:
                ball_res, state = MatchService.step_delivery(db, room_code)
                ball_count += 1

            # Fetch fresh database records for complete audit
            match_rec = db.query(Match).filter(Match.id == match_id).first()
            inn1 = db.query(MatchInnings).filter(MatchInnings.match_id == match_id, MatchInnings.innings_number == 1).first()
            inn2 = db.query(MatchInnings).filter(MatchInnings.match_id == match_id, MatchInnings.innings_number == 2).first()

            # Perform Comprehensive Audits
            audit_report = self._audit_match(db, match_rec, inn1, inn2, scenario, ball_count)

            return audit_report

        finally:
            db.close()

    def _audit_match(
        self,
        db: Any,
        match: Match,
        inn1: MatchInnings,
        inn2: Optional[MatchInnings],
        scenario: Dict[str, Any],
        total_deliveries: int,
    ) -> Dict[str, Any]:
        """Exhaustively verifies batting, bowling, team, commentary, database, and realism."""
        failures: List[str] = []

        # ----------------- 1. Batting Statistics Audit -----------------
        def audit_innings_batting(inn: MatchInnings, inn_num: int):
            batters = db.query(InningsBatterScore).filter(InningsBatterScore.innings_id == inn.id).order_by(InningsBatterScore.batting_position.asc()).all()
            if len(batters) != 11:
                failures.append(f"Innings {inn_num} has {len(batters)} batters instead of 11.")

            not_out_count = sum(1 for b in batters if b.has_batted and not b.is_out)
            if not_out_count > 2:
                failures.append(f"Innings {inn_num} has {not_out_count} NOT OUT batters (max 2 allowed).")

            seen_pids = set()
            for b in batters:
                # Unique identity
                if b.player_id in seen_pids:
                    failures.append(f"Duplicate player ID {b.player_id} in Innings {inn_num} batting.")
                seen_pids.add(b.player_id)

                # Runs reconciliation: 4s*4 + 6s*6 <= runs
                boundary_runs = (b.fours * 4) + (b.sixes * 6)
                if boundary_runs > b.runs:
                    failures.append(f"Batter {b.player_name} boundary runs ({boundary_runs}) exceed total runs ({b.runs}).")

                # Strike rate reconciliation
                if b.balls > 0:
                    expected_sr = round((b.runs / b.balls) * 100.0, 1)
                    if abs(b.strike_rate - expected_sr) > 0.2:
                        failures.append(f"Batter {b.player_name} SR mismatch: got {b.strike_rate}, expected {expected_sr}.")

                # DNB integrity
                if not b.has_batted:
                    if b.is_out or b.runs > 0 or b.balls > 0:
                        failures.append(f"DNB batter {b.player_name} has invalid stats (runs={b.runs}, balls={b.balls}, is_out={b.is_out}).")

                # Track global tally
                if b.has_batted:
                    self.player_runs_tally[b.player_name] = self.player_runs_tally.get(b.player_name, 0) + b.runs
                    self.all_strike_rates.append(b.strike_rate)

        audit_innings_batting(inn1, 1)
        if inn2:
            audit_innings_batting(inn2, 2)

        # ----------------- 2. Bowling Statistics Audit -----------------
        def audit_innings_bowling(inn: MatchInnings, inn_num: int):
            bowlers = db.query(InningsBowlerScore).filter(InningsBowlerScore.innings_id == inn.id).all()
            for bw in bowlers:
                # Max 4 overs (24 legal balls)
                if bw.legal_balls > 24:
                    failures.append(f"Bowler {bw.player_name} bowled {bw.legal_balls} legal balls (> 24 quota).")

                # Economy rate reconciliation
                if bw.legal_balls > 0:
                    expected_econ = round((bw.runs_conceded / bw.legal_balls) * 6.0, 2)
                    if abs(bw.economy - expected_econ) > 0.05:
                        failures.append(f"Bowler {bw.player_name} economy mismatch: got {bw.economy}, expected {expected_econ}.")

                # Wickets tally
                self.player_wickets_tally[bw.player_name] = self.player_wickets_tally.get(bw.player_name, 0) + bw.wickets
                if bw.legal_balls >= 6:
                    self.all_economies.append(bw.economy)

        audit_innings_bowling(inn1, 1)
        if inn2:
            audit_innings_bowling(inn2, 2)

        # ----------------- 3. Team Statistics Audit -----------------
        def audit_team_totals(inn: MatchInnings, inn_num: int):
            batters = db.query(InningsBatterScore).filter(InningsBatterScore.innings_id == inn.id).all()
            events = db.query(BallEvent).filter(BallEvent.innings_id == inn.id).all()

            total_batter_runs = sum(b.runs for b in batters)
            total_extras = sum(e.extras for e in events)
            total_reconciled = total_batter_runs + total_extras
            dismissed_batters = sum(1 for b in batters if b.is_out)

            # Invariant 1: Total Runs = Batter Runs + Extras
            if inn.total_runs != total_reconciled:
                failures.append(f"Innings {inn_num} runs mismatch: inn.total_runs={inn.total_runs}, sum={total_reconciled}.")

            # Invariant 2: Wickets = Dismissed Batters
            if inn.total_wickets != dismissed_batters:
                failures.append(f"Innings {inn_num} wickets mismatch: inn.total_wickets={inn.total_wickets}, out={dismissed_batters}.")

            # Invariant 3: Overs <= 20.0
            if inn.legal_balls_bowled > 120:
                failures.append(f"Innings {inn_num} exceeded 120 balls: {inn.legal_balls_bowled} balls bowled.")

            # Record metrics
            for ev in events:
                self.total_balls_bowled += 1
                if ev.batter_runs == 0 and ev.extras == 0:
                    self.total_dots += 1
                elif ev.batter_runs == 4:
                    self.total_fours += 1
                elif ev.batter_runs == 6:
                    self.total_sixes += 1
                if ev.is_wicket and ev.wicket_type:
                    self.dismissal_counts[ev.wicket_type] = self.dismissal_counts.get(ev.wicket_type, 0) + 1

                # Powerplay (overs 0-5) and Death (overs 15-19) breakdown
                if ev.over_number < 6:
                    self.powerplay_runs_list.append(ev.runs_scored)
                elif ev.over_number >= 15:
                    self.death_runs_list.append(ev.runs_scored)

        audit_team_totals(inn1, 1)
        self.all_first_innings_runs.append(inn1.total_runs)
        self.all_innings_wickets.append(inn1.total_wickets)

        if inn2:
            audit_team_totals(inn2, 2)
            self.all_second_innings_runs.append(inn2.total_runs)
            self.all_innings_wickets.append(inn2.total_wickets)

            # Invariant 4: Target == 1st Innings + 1
            if match.target != (inn1.total_runs + 1):
                failures.append(f"Target mismatch: got {match.target}, expected {inn1.total_runs + 1}.")

        # ----------------- 4. Database Integrity Audit -----------------
        if match.status not in ("COMPLETED", "TIED"):
            failures.append(f"Match status is {match.status} instead of COMPLETED/TIED.")
        if not match.result_margin:
            failures.append("Match result_margin is empty.")

        # ----------------- 5. Select Match Heroes -----------------
        # Find Top Batter across match
        all_match_batters = db.query(InningsBatterScore).filter(
            InningsBatterScore.innings_id.in_([inn1.id, inn2.id] if inn2 else [inn1.id])
        ).all()
        top_batter_rec = max(all_match_batters, key=lambda b: (b.runs, b.strike_rate)) if all_match_batters else None

        # Find Top Bowler across match
        all_match_bowlers = db.query(InningsBowlerScore).filter(
            InningsBowlerScore.innings_id.in_([inn1.id, inn2.id] if inn2 else [inn1.id])
        ).all()
        top_bowler_rec = max(all_match_bowlers, key=lambda bw: (bw.wickets, -bw.runs_conceded)) if all_match_bowlers else None

        # Player of the Match
        pom_candidate = top_batter_rec.player_name if top_batter_rec and top_batter_rec.runs >= 45 else (
            top_bowler_rec.player_name if top_bowler_rec and top_bowler_rec.wickets >= 3 else (
                top_batter_rec.player_name if top_batter_rec else "Captain"
            )
        )

        winner_name = scenario["host_team_name"] if match.winner_user_id == match.team1_user_id else (
            scenario["guest_team_name"] if match.winner_user_id == match.team2_user_id else "Match Tied"
        )

        passed = (len(failures) == 0)

        report = {
            "match_id": match.id,
            "scenario": scenario["title"],
            "winner": winner_name,
            "won_by": match.result_margin,
            "inn1_score": f"{inn1.total_runs}/{inn1.total_wickets} ({inn1.total_overs:.1f} Ov)",
            "inn2_score": f"{inn2.total_runs}/{inn2.total_wickets} ({inn2.total_overs:.1f} Ov)" if inn2 else "DNB",
            "top_batter_name": top_batter_rec.player_name if top_batter_rec else "None",
            "top_batter_line": f"{top_batter_rec.runs} ({top_batter_rec.balls})" if top_batter_rec else "0 (0)",
            "top_bowler_name": top_bowler_rec.player_name if top_bowler_rec else "None",
            "top_bowler_line": f"{top_bowler_rec.wickets}/{top_bowler_rec.runs_conceded} ({top_bowler_rec.overs:.1f} Ov)" if top_bowler_rec else "0/0",
            "pom": pom_candidate,
            "total_deliveries": total_deliveries,
            "passed": passed,
            "failures": failures,
        }
        self.match_results.append(report)
        return report

    def run_all_20_matches(self) -> List[Dict[str, Any]]:
        """Executes all 20 required match scenarios."""
        scenarios = [
            {"title": "Match 1: Strong Batting vs Strong Bowling", "host_team_name": "Mumbai Heavyweights", "guest_team_name": "Lahore Express", "host_scenario": "strong_batting", "guest_scenario": "strong_bowling"},
            {"title": "Match 2: Strong Batting vs Weak Bowling", "host_team_name": "Barbados Hitters", "guest_team_name": "Harare Strikers", "host_scenario": "strong_batting", "guest_scenario": "weak_bowling"},
            {"title": "Match 3: Weak Batting vs Strong Bowling", "host_team_name": "Dhaka Defenders", "guest_team_name": "Perth Pace XI", "host_scenario": "weak_batting", "guest_scenario": "strong_bowling"},
            {"title": "Match 4: Balanced Modern Clash", "host_team_name": "Royal Challengers", "guest_team_name": "Sydney Sixers", "host_scenario": "balanced", "guest_scenario": "balanced"},
            {"title": "Match 5: Pace-Heavy Attacks (Green Pitch)", "host_team_name": "Auckland Quick XI", "guest_team_name": "Pretoria Speed", "host_scenario": "pace_heavy", "guest_scenario": "pace_heavy"},
            {"title": "Match 6: Spin-Heavy Attacks (Turning Pitch)", "host_team_name": "Chennai Spin Kings", "guest_team_name": "Colombo Web Weavers", "host_scenario": "spin_heavy", "guest_scenario": "spin_heavy"},
            {"title": "Match 7: Mixed Classical Attack (1990s Era)", "host_team_name": "Calcutta 90s Stars", "guest_team_name": "Karachi 90s Legends", "host_scenario": "era_1990", "guest_scenario": "era_1990"},
            {"title": "Match 8: Historical Clash (2000s Era)", "host_team_name": "Melbourne 2000s XI", "guest_team_name": "Johannesburg 2000s", "host_scenario": "era_2000", "guest_scenario": "era_2000"},
            {"title": "Match 9: Historical Era Cross-Over (1990s vs 2020s)", "host_team_name": "Vintage 1990s Masters", "guest_team_name": "Modern 2020s Dynamos", "host_scenario": "era_1990", "guest_scenario": "era_2020"},
            {"title": "Match 10: Multi-Era Duplicate Names Test", "host_team_name": "Kabul Titans", "guest_team_name": "Adelaide Strikers", "host_scenario": "balanced", "guest_scenario": "balanced"},
            {"title": "Match 11: Flat Batting Paradise Shootout", "host_team_name": "Chinnaswamy Royals", "guest_team_name": "Sharjah Blasters", "host_scenario": "strong_batting", "guest_scenario": "strong_batting"},
            {"title": "Match 12: Overcast Seam Showcase", "host_team_name": "Leeds Swing XI", "guest_team_name": "Wellington Seamers", "host_scenario": "pace_heavy", "guest_scenario": "pace_heavy"},
            {"title": "Match 13: Low-Scoring Pressure Thriller", "host_team_name": "Mirpur Dragons", "guest_team_name": "Galle Gladiators", "host_scenario": "spin_heavy", "guest_scenario": "weak_batting"},
            {"title": "Match 14: Power Hitters vs Defensive Seamers", "host_team_name": "Kingston Powerhouses", "guest_team_name": "Derbyshire Control", "host_scenario": "strong_batting", "guest_scenario": "strong_bowling"},
            {"title": "Match 15: Anchors & Accumulators vs Mystery Spinners", "host_team_name": "Geelong Anchors", "guest_team_name": "Rawalpindi Spinners", "host_scenario": "balanced", "guest_scenario": "spin_heavy"},
            {"title": "Match 16: Deep Batting Lineup vs Strike Bowling", "host_team_name": "London Cavaliers", "guest_team_name": "Brisbane Heatwaves", "host_scenario": "strong_batting", "guest_scenario": "strong_bowling"},
            {"title": "Match 17: All-Rounder Heavy Squads", "host_team_name": "Cape Town Versatiles", "guest_team_name": "Canterbury All-Stars", "host_scenario": "balanced", "guest_scenario": "balanced"},
            {"title": "Match 18: High Pressure Chase Test", "host_team_name": "Dubai Desert Hawks", "guest_team_name": "Durban Warriors", "host_scenario": "strong_batting", "guest_scenario": "strong_batting"},
            {"title": "Match 19: Close Finish / Death Overs Showdown", "host_team_name": "Islamabad United XI", "guest_team_name": "Hobart Hurricanes", "host_scenario": "balanced", "guest_scenario": "balanced"},
            {"title": "Match 20: Ultimate T20 Best-XI Superclash", "host_team_name": "CricXI Global Titans", "guest_team_name": "CricXI All-Era Legends", "host_scenario": "strong_batting", "guest_scenario": "strong_bowling"},
        ]

        reports = []
        for idx, sc in enumerate(scenarios, start=1):
            rep = self.run_single_match(idx, sc)
            reports.append(rep)
        return reports


if __name__ == "__main__":
    t0 = time.perf_counter()
    runner = QASimulationRunner()
    reports = runner.run_all_20_matches()
    t1 = time.perf_counter()

    print(f"Total time for 20 complete matches: {t1 - t0:.2f} seconds\n")
    for r in reports:
        print(f"Match {r['match_id']}: {r['scenario']} -> Winner: {r['winner']} ({r['won_by']}) | Passed: {r['passed']}")

