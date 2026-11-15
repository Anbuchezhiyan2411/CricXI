"""
CricXI Priority 5 — 100-Match Real Gameplay Validation Suite.

Executes 100 complete multiplayer matches end-to-end:
1. Room Creation (Host & Guest)
2. 11-Round Snake Draft with forward checking validation & intelligent auto-picks
3. Authentic Cricket Toss Ceremony
4. Full Ball-by-Ball Live T20 Match Simulation
5. Strict Invariant & Scorecard Validation for every match
6. Cumulative Telemetry (Bat First vs Chase win balance, Dismissal distributions, Phase scoring)
"""

import sys
import os
import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database.session import Base
from app.models.room import Room, RoomPlayer
from app.models.draft import DraftPick, DraftState
from app.models.toss import TossState
from app.models.match import Match, MatchInnings, BallEvent, InningsBatterScore, InningsBowlerScore
from app.draft.draft_service import DraftService, parse_eligible_positions
from app.toss.toss_service import TossService
from app.match.match_service import MatchService
from app.services.dataset_loader import dataset_service


class LongPlayValidator:
    """End-to-end validator running 100 complete gameplay matches."""

    def __init__(self):
        if not dataset_service.is_loaded:
            dataset_service.load()

        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        self.matches_played = 0
        self.first_innings_scores: List[int] = []
        self.second_innings_scores: List[int] = []
        self.bat_first_wins = 0
        self.chase_wins = 0
        self.ties = 0

        self.total_wickets_fallen = 0
        self.total_extras_conceded = 0
        self.total_balls_bowled = 0
        self.total_dots = 0
        self.total_fours = 0
        self.total_sixes = 0

        self.powerplay_runs: List[int] = []
        self.middle_runs: List[int] = []
        self.death_runs: List[int] = []

        self.dismissal_types: Dict[str, int] = {}
        self.player_runs: Dict[str, int] = {}
        self.player_balls: Dict[str, int] = {}
        self.player_wickets: Dict[str, int] = {}
        self.player_runs_conceded: Dict[str, int] = {}
        self.player_balls_bowled: Dict[str, int] = {}
        self.potm_awards: Dict[str, int] = {}

        self.centuries = 0
        self.fifers = 0
        self.ducks = 0

        self.bugs_found: List[Dict[str, Any]] = []
        self.match_summaries: List[Dict[str, Any]] = []

    def log_bug(self, bug_id: str, severity: str, area: str, desc: str, steps: str, expected: str, actual: str, fix: str):
        bug_entry = {
            "bug_id": bug_id,
            "severity": severity,
            "area": area,
            "description": desc,
            "steps": steps,
            "expected": expected,
            "actual": actual,
            "fix": fix,
        }
        self.bugs_found.append(bug_entry)
        print(f"\n[!BUG DETECTED] {bug_id} ({severity}): {desc}")

    def run_single_match(self, match_idx: int, config: Dict[str, Any]) -> Dict[str, Any]:
        db = self.Session()
        room_code = f"M{match_idx:03d}R"
        host_id = f"host_{match_idx}"
        guest_id = f"guest_{match_idx}"

        # 1. Create Room & Players
        room = Room(room_code=room_code, host_id=host_id, status="DRAFTING")
        db.add(room)
        db.commit()

        p1 = RoomPlayer(room_id=room.id, user_id=host_id, username=config["host_name"], is_host=True, is_ready=True)
        p2 = RoomPlayer(room_id=room.id, user_id=guest_id, username=config["guest_name"], is_host=False, is_ready=True)
        db.add_all([p1, p2])
        db.commit()
        db.refresh(room)

        # 2. Draft Phase
        country = config.get("country", "India")
        decade = config.get("decade", 2010)
        is_single_pool = config.get("is_single_pool", False)

        draft_state = DraftService.initialize_draft(
            db=db,
            room_code=room_code,
            country=country,
            decade=decade,
            is_single_pool=is_single_pool,
        )

        # In alternate matches, test full intelligent auto-picks vs tactical user picks
        use_auto_pick = (match_idx % 2 == 0)

        for r_num in range(1, 12):
            for t_num in (1, 2):
                if use_auto_pick:
                    pick, is_fin = DraftService.execute_auto_pick(db, room_code)
                    if not pick:
                        self.log_bug(
                            bug_id=f"AUTOPICK_FAIL_{match_idx}",
                            severity="CRITICAL",
                            area="Draft Auto Pick",
                            desc=f"Auto pick returned None at R{r_num}T{t_num} in room {room_code}",
                            steps=f"execute_auto_pick at R{r_num}T{t_num}",
                            expected="Valid auto pick returned",
                            actual="None returned",
                            fix="Inspect candidate scoring and forward checking",
                        )
                        db.close()
                        return {"status": "FAILED", "match_index": match_idx}
                else:
                    ds = db.query(DraftState).filter(DraftState.room_id == room.id).first()
                    uid = ds.current_picker_id
                    picks = db.query(DraftPick).filter(DraftPick.room_id == room.id).all()
                    user_picks = [p for p in picks if p.user_id == uid]
                    occ = set(p.batting_position for p in user_picks)
                    vacant = sorted(list(set(range(1, 12)) - occ))

                    has_wk = any(dataset_service.get_player_by_id(p.player_id).get("is_wicketkeeper") for p in user_picks)
                    bowlers = sum(1 for p in user_picks if DraftService.is_bowling_option(dataset_service.get_player_by_id(p.player_id)))
                    wk_needed = 0 if has_wk else 1
                    bowl_needed = max(0, 5 - bowlers)

                    cands = dataset_service.get_players_by_country_and_decade(ds.round_country, ds.round_decade)
                    drafted_ids = set(p.player_id for p in picks)
                    avail = [c for c in cands if int(c["player_id"]) not in drafted_ids]

                    avail.sort(
                        key=lambda x: (
                            100 if (wk_needed > 0 and x.get("is_wicketkeeper")) else 0,
                            80 if (bowl_needed >= len(vacant) and DraftService.is_bowling_option(x)) else 0,
                            30 if (bowl_needed > 0 and DraftService.is_bowling_option(x)) else 0,
                            float(x.get("overall_rating", 0.0)),
                        ),
                        reverse=True,
                    )

                    chosen = None
                    for c in avail:
                        c_slots = parse_eligible_positions(c.get("eligible_positions", ""))
                        valid_slots = sorted(list(c_slots - occ))

                        if bowl_needed >= len(vacant) and not DraftService.is_bowling_option(c):
                            continue
                        if wk_needed >= len(vacant) and not c.get("is_wicketkeeper"):
                            continue

                        for s in valid_slots:
                            is_valid, _ = DraftService.validate_forward_constraints(db, room, ds, uid, c, s)
                            if is_valid:
                                chosen = (c, s)
                                break
                        if chosen:
                            break

                    if not chosen:
                        self.log_bug(
                            bug_id=f"DRAFT_DEADLOCK_{match_idx}",
                            severity="CRITICAL",
                            area="Draft Engine",
                            desc=f"Unable to find valid draft pick at R{r_num}T{t_num} in room {room_code}",
                            steps=f"Draft in {ds.round_country} {ds.round_decade} at R{r_num}T{t_num}",
                            expected="Valid pick available",
                            actual="Deadlock encountered",
                            fix="Ensure pool regeneration and feasibility checks guarantee valid picks",
                        )
                        db.close()
                        return {"status": "FAILED", "match_index": match_idx}

                    DraftService.make_pick(db, room_code, uid, int(chosen[0]["player_id"]), chosen[1])

        db.refresh(room)
        db.refresh(draft_state)

        # Validate Draft Squad Invariants
        host_picks = db.query(DraftPick).filter(DraftPick.room_id == room.id, DraftPick.user_id == host_id).all()
        guest_picks = db.query(DraftPick).filter(DraftPick.room_id == room.id, DraftPick.user_id == guest_id).all()

        if len(host_picks) != 11 or len(guest_picks) != 11:
            self.log_bug(f"DRAFT_LEN_{match_idx}", "HIGH", "Draft", f"Incorrect squad size: Host={len(host_picks)}, Guest={len(guest_picks)}", "Inspect draft", "11 each", f"{len(host_picks)} and {len(guest_picks)}", "Fix draft loop")

        all_pids = [p.player_id for p in host_picks + guest_picks]
        if len(all_pids) != len(set(all_pids)):
            self.log_bug(f"DRAFT_DUP_{match_idx}", "CRITICAL", "Draft", "Duplicate player drafted in room!", "Check picks", "Unique players", f"{len(all_pids)} total, {len(set(all_pids))} unique", "Fix duplicate check")

        def check_squad(picks, uname):
            has_wk = False
            bowlers = 0
            for p in picks:
                meta = dataset_service.get_player_by_id(p.player_id) or {}
                if meta.get("is_wicketkeeper"):
                    has_wk = True
                if DraftService.is_bowling_option(meta):
                    bowlers += 1
            if not has_wk:
                self.log_bug(f"NO_WK_{match_idx}", "HIGH", "Draft", f"{uname} has 0 wicketkeepers!", "Check squad", ">= 1 WK", "0 WK", "Fix WK selection priority")
            if bowlers < 5:
                self.log_bug(f"LOW_BOWL_{match_idx}", "HIGH", "Draft", f"{uname} has only {bowlers} bowling options (needs 5)!", "Check squad", ">= 5 bowlers", f"{bowlers}", "Fix bowler selection priority")

        check_squad(host_picks, config["host_name"])
        check_squad(guest_picks, config["guest_name"])

        # 3. Toss Ceremony
        toss_resp = TossService.initialize_or_get_toss(db, room_code, host_id)
        caller_id = toss_resp.caller_id
        called_side = random.choice(["HEADS", "TAILS"])
        toss_resp = TossService.make_call(db, room_code, caller_id, called_side)

        winner_id = toss_resp.winner_id
        # Balanced toss choices: 50% bat, 50% bowl
        decision = random.choice(["BAT", "BOWL"])
        toss_resp = TossService.make_decision(db, room_code, winner_id, decision)

        db.refresh(room)
        if room.status != "LIVE":
            self.log_bug(f"TOSS_STATUS_{match_idx}", "HIGH", "Toss", f"Room status is {room.status} after toss, expected LIVE", "Complete toss", "LIVE", room.status, "Check room transition")

        # 4. Live Match Simulation
        live_state = MatchService.initialize_or_get_match(db, room_code)
        match_obj = db.query(Match).filter(Match.room_id == room.id).first()

        balls_count = 0
        max_balls = 320
        while live_state.status != "COMPLETED" and balls_count < max_balls:
            balls_count += 1
            res, live_state = MatchService.step_delivery(db, room_code, seed=match_idx * 1000 + balls_count)

        db.refresh(match_obj)
        if match_obj.status not in ("COMPLETED", "TIED"):
            self.log_bug(f"MATCH_TIMEOUT_{match_idx}", "CRITICAL", "Simulation", f"Match did not finish within {max_balls} deliveries!", "Simulate match", "COMPLETED", match_obj.status, "Inspect match termination condition")

        # 5. Deep Scorecard and Cricket Invariant Validation
        match_report = self._validate_completed_match(db, room_code, match_idx, config, match_obj)

        db.close()
        return match_report

    def _validate_completed_match(self, db, room_code, match_idx, config, match_obj) -> Dict[str, Any]:
        inn1 = db.query(MatchInnings).filter(MatchInnings.match_id == match_obj.id, MatchInnings.innings_number == 1).first()
        inn2 = db.query(MatchInnings).filter(MatchInnings.match_id == match_obj.id, MatchInnings.innings_number == 2).first()

        inn1_runs = inn1.total_runs if inn1 else 0
        inn2_runs = inn2.total_runs if inn2 else 0

        # Target check
        if inn1 and inn2:
            expected_target = inn1.total_runs + 1
            if match_obj.target != expected_target:
                self.log_bug(f"TARGET_MISMATCH_{match_idx}", "HIGH", "Match", f"Target {match_obj.target} != inn1 + 1 ({expected_target})", "Target check", str(expected_target), str(match_obj.target), "Fix target calc")

        # Winner and Margin check
        winner_id = match_obj.winner_user_id
        margin = match_obj.result_margin or ""

        team_names = {
            match_obj.team1_user_id: config["host_name"],
            match_obj.team2_user_id: config["guest_name"],
        }
        winner_name = team_names.get(winner_id, "Tied / Unknown")

        if inn2_runs > inn1_runs:
            if winner_id != inn2.batting_team_user_id:
                self.log_bug(f"WINNER_ERR_{match_idx}", "CRITICAL", "Match", f"Chase won ({inn2_runs} > {inn1_runs}) but winner is wrong!", "Winner check", inn2.batting_team_user_id, winner_id, "Fix winner logic")
            self.chase_wins += 1
        elif inn1_runs > inn2_runs:
            if winner_id != inn1.batting_team_user_id:
                self.log_bug(f"WINNER_ERR_{match_idx}", "CRITICAL", "Match", f"Defend won ({inn1_runs} > {inn2_runs}) but winner is wrong!", "Winner check", inn1.batting_team_user_id, winner_id, "Fix winner logic")
            self.bat_first_wins += 1
        else:
            self.ties += 1

        # Check immediate chase stop
        if inn2 and inn2_runs >= inn1_runs + 1:
            balls_inn2 = db.query(BallEvent).filter(BallEvent.innings_id == inn2.id).order_by(BallEvent.id.asc()).all()
            cum_runs = 0
            target_reached_idx = None
            for b_i, b in enumerate(balls_inn2):
                cum_runs += b.runs_scored
                if cum_runs >= match_obj.target and target_reached_idx is None:
                    target_reached_idx = b_i
            if target_reached_idx is not None and target_reached_idx < len(balls_inn2) - 1:
                self.log_bug(f"CHASE_OVERSHOOT_{match_idx}", "CRITICAL", "Simulation", f"Chase continued {len(balls_inn2) - 1 - target_reached_idx} balls after reaching target!", "Chase stop", "Immediate stop", f"{len(balls_inn2) - 1 - target_reached_idx} balls", "Fix chase termination check")

        # Invariant validations for both innings
        for inn in [inn1, inn2]:
            if not inn:
                continue
            self._validate_innings_scorecard(db, inn, match_idx)

        top_batter, top_bat_score, top_bat_balls = self._get_match_top_batter(db, match_obj)
        top_bowler, top_bowl_wkts, top_bowl_runs = self._get_match_top_bowler(db, match_obj)
        potm = self._determine_potm(db, match_obj, top_batter, top_bat_score, top_bowler, top_bowl_wkts)
        self.potm_awards[potm] = self.potm_awards.get(potm, 0) + 1

        self.first_innings_scores.append(inn1_runs)
        self.second_innings_scores.append(inn2_runs)
        self.total_wickets_fallen += (inn1.total_wickets if inn1 else 0) + (inn2.total_wickets if inn2 else 0)

        summary = {
            "match_number": match_idx,
            "host_team": config["host_name"],
            "guest_team": config["guest_name"],
            "winner": winner_name,
            "margin": margin,
            "inn1_score": f"{inn1_runs}/{inn1.total_wickets if inn1 else 0}",
            "inn1_overs": inn1.total_overs if inn1 else 0.0,
            "inn2_score": f"{inn2_runs}/{inn2.total_wickets if inn2 else 0}",
            "inn2_overs": inn2.total_overs if inn2 else 0.0,
            "top_batter": f"{top_batter} {top_bat_score} ({top_bat_balls})",
            "top_bowler": f"{top_bowler} {top_bowl_wkts}/{top_bowl_runs}",
            "potm": potm,
        }
        self.match_summaries.append(summary)
        return summary

    def _validate_innings_scorecard(self, db, inn: MatchInnings, match_idx: int):
        batters = db.query(InningsBatterScore).filter(InningsBatterScore.innings_id == inn.id).all()
        bowlers = db.query(InningsBowlerScore).filter(InningsBowlerScore.innings_id == inn.id).all()
        balls = db.query(BallEvent).filter(BallEvent.innings_id == inn.id).all()

        # 1. Total runs sum = batter runs + extras
        batter_runs_sum = sum(b.runs for b in batters)
        extras = sum(b.extras for b in balls)
        self.total_extras_conceded += extras
        if (batter_runs_sum + extras) != inn.total_runs:
            self.log_bug(f"SCORE_SUM_{match_idx}_INN{inn.innings_number}", "CRITICAL", "Scorecard", f"Inn {inn.innings_number} total {inn.total_runs} != batter runs ({batter_runs_sum}) + extras ({extras})", "Check sum", str(inn.total_runs), str(batter_runs_sum + extras), "Reconcile extras in innings tally")

        # 2. Total wickets = dismissed count
        out_batters = [b for b in batters if b.is_out]
        if len(out_batters) != inn.total_wickets:
            self.log_bug(f"WICKET_COUNT_{match_idx}_INN{inn.innings_number}", "CRITICAL", "Scorecard", f"Inn {inn.innings_number} wickets {inn.total_wickets} != dismissed count {len(out_batters)}", "Check wickets", str(inn.total_wickets), str(len(out_batters)), "Fix dismissal recording")

        # 3. Maximum 2 not outs
        not_outs = [b for b in batters if b.has_batted and not b.is_out]
        if len(not_outs) > 2:
            self.log_bug(f"NOT_OUTS_{match_idx}_INN{inn.innings_number}", "HIGH", "Scorecard", f"Inn {inn.innings_number} has {len(not_outs)} not-outs (max 2 allowed)", "Check not-outs", "<= 2", str(len(not_outs)), "Fix not-out state on wicket")

        # 4. Bowler figures & caps
        for bowl in bowlers:
            p_data = dataset_service.get_player_by_id(bowl.player_id) or {}
            if p_data.get("is_wicketkeeper"):
                self.log_bug(f"WK_BOWLED_{match_idx}", "CRITICAL", "Cricket Logic", f"Wicketkeeper {bowl.player_name} bowled overs!", "Bowling check", "WK never bowls", f"{bowl.overs}", "Block WK from bowling")

            if bowl.legal_balls > 24:
                self.log_bug(f"OVER_LIMIT_{match_idx}", "CRITICAL", "Cricket Rules", f"Bowler {bowl.player_name} bowled {bowl.legal_balls} balls (> 24)", "Bowler overs", "<= 24", str(bowl.legal_balls), "Enforce 4 over cap")

            self.player_wickets[bowl.player_name] = self.player_wickets.get(bowl.player_name, 0) + bowl.wickets
            self.player_runs_conceded[bowl.player_name] = self.player_runs_conceded.get(bowl.player_name, 0) + bowl.runs_conceded
            self.player_balls_bowled[bowl.player_name] = self.player_balls_bowled.get(bowl.player_name, 0) + bowl.legal_balls
            self.total_balls_bowled += bowl.legal_balls

            if bowl.wickets >= 5:
                self.fifers += 1

        # 5. Batter stats
        for b in batters:
            if b.has_batted:
                self.player_runs[b.player_name] = self.player_runs.get(b.player_name, 0) + b.runs
                self.player_balls[b.player_name] = self.player_balls.get(b.player_name, 0) + b.balls
                if b.runs >= 100:
                    self.centuries += 1
                if b.runs == 0 and b.is_out:
                    self.ducks += 1

        # 6. Balls telemetry: dots, boundaries, dismissals
        pp_r, mid_r, dth_r = 0, 0, 0
        for bl in balls:
            if bl.runs_scored == 0 and bl.extra_type is None:
                self.total_dots += 1
            if bl.batter_runs == 4:
                self.total_fours += 1
            elif bl.batter_runs == 6:
                self.total_sixes += 1

            if bl.is_wicket and bl.wicket_type:
                wtype = bl.wicket_type.strip().capitalize()
                self.dismissal_types[wtype] = self.dismissal_types.get(wtype, 0) + 1

            ov = bl.over_number
            if ov < 6:
                pp_r += bl.runs_scored
            elif ov < 16:
                mid_r += bl.runs_scored
            else:
                dth_r += bl.runs_scored

        self.powerplay_runs.append(pp_r)
        self.middle_runs.append(mid_r)
        self.death_runs.append(dth_r)

    def _get_match_top_batter(self, db, match_obj) -> Tuple[str, int, int]:
        score = (
            db.query(InningsBatterScore)
            .join(MatchInnings, InningsBatterScore.innings_id == MatchInnings.id)
            .filter(MatchInnings.match_id == match_obj.id)
            .order_by(InningsBatterScore.runs.desc())
            .first()
        )
        if score:
            return score.player_name, score.runs, score.balls
        return "Unknown", 0, 0

    def _get_match_top_bowler(self, db, match_obj) -> Tuple[str, int, int]:
        fig = (
            db.query(InningsBowlerScore)
            .join(MatchInnings, InningsBowlerScore.innings_id == MatchInnings.id)
            .filter(MatchInnings.match_id == match_obj.id)
            .order_by(InningsBowlerScore.wickets.desc(), InningsBowlerScore.runs_conceded.asc())
            .first()
        )
        if fig:
            return fig.player_name, fig.wickets, fig.runs_conceded
        return "Unknown", 0, 0

    def _determine_potm(self, db, match_obj, top_bat_name, top_bat_runs, top_bowl_name, top_bowl_wkts) -> str:
        candidates: Dict[str, float] = {}
        all_batters = (
            db.query(InningsBatterScore)
            .join(MatchInnings, InningsBatterScore.innings_id == MatchInnings.id)
            .filter(MatchInnings.match_id == match_obj.id)
            .all()
        )
        all_bowlers = (
            db.query(InningsBowlerScore)
            .join(MatchInnings, InningsBowlerScore.innings_id == MatchInnings.id)
            .filter(MatchInnings.match_id == match_obj.id)
            .all()
        )

        for b in all_batters:
            sr_bonus = (b.strike_rate - 100.0) * 0.1 if b.balls >= 15 else 0.0
            candidates[b.player_name] = candidates.get(b.player_name, 0.0) + (b.runs * 1.0) + sr_bonus

        for bw in all_bowlers:
            econ_bonus = max(0.0, (8.0 - bw.economy) * 3.0) if bw.legal_balls >= 12 else 0.0
            candidates[bw.player_name] = candidates.get(bw.player_name, 0.0) + (bw.wickets * 28.0) + econ_bonus

        if not candidates:
            return top_bat_name if top_bat_runs > 40 else top_bowl_name

        return max(candidates.items(), key=lambda x: x[1])[0]


def generate_100_configs() -> List[Dict[str, Any]]:
    combos = DraftService.get_all_combinations()
    configs = []
    for i in range(1, 101):
        c1, d1 = combos[(i - 1) % len(combos)]
        is_single = (i == 33)  # Match 33 explicitly tests single-pool regeneration
        if i == 10:
            c1, d1 = "Zimbabwe", 2020  # Explicitly tests non-existent starting pool regeneration
        configs.append({
            "host_name": f"{c1} Stars ({d1})",
            "guest_name": f"Match {i:03d} Challenger",
            "country": c1,
            "decade": d1,
            "is_single_pool": is_single,
        })
    return configs


def main():
    print("=" * 70)
    print("CRICXI PRIORITY 5 — 100-MATCH REAL GAMEPLAY VALIDATION SUITE")
    print("=" * 70)

    validator = LongPlayValidator()
    configs = generate_100_configs()

    for idx, cfg in enumerate(configs, 1):
        summary = validator.run_single_match(idx, cfg)
        if summary.get("status") == "FAILED":
            print(f"Match {idx:03d} FAILED!", flush=True)
            sys.exit(1)

        print(f"[MATCH {idx:03d}/100] {summary['winner']} won ({summary['margin']}) | Inn1: {summary['inn1_score']} ({summary['inn1_overs']} ov) | Inn2: {summary['inn2_score']} ({summary['inn2_overs']} ov)", flush=True)

    n_matches = len(validator.match_summaries)
    avg_inn1 = sum(validator.first_innings_scores) / n_matches
    avg_inn2 = sum(validator.second_innings_scores) / n_matches
    win_bat1_pct = (validator.bat_first_wins / n_matches) * 100.0
    win_chase_pct = (validator.chase_wins / n_matches) * 100.0

    tot_runs = sum(validator.player_runs.values())
    tot_balls_batted = sum(validator.player_balls.values())
    avg_sr = (tot_runs / max(1, tot_balls_batted)) * 100.0

    tot_runs_conceded = sum(validator.player_runs_conceded.values())
    tot_balls_bowled = validator.total_balls_bowled
    avg_econ = (tot_runs_conceded / max(1.0, tot_balls_bowled / 6.0))

    dot_pct = (validator.total_dots / max(1, tot_balls_bowled)) * 100.0
    boundary_pct = ((validator.total_fours * 4 + validator.total_sixes * 6) / max(1, tot_runs)) * 100.0

    print("\n" + "=" * 70)
    print("100-MATCH COMPREHENSIVE VALIDATION REPORT")
    print("=" * 70)
    draft_bugs = [b for b in validator.bugs_found if "DRAFT" in b["bug_id"] or "DEADLOCK" in b["bug_id"] or "AUTOPICK" in b["bug_id"]]
    print(f"Completed Matches: {n_matches}/100 (100.0%)")
    print(f"Draft Deadlocks Encountered: {len(draft_bugs)}")
    print(f"Average 1st Innings Total: {avg_inn1:.1f}")
    print(f"Average 2nd Innings Total: {avg_inn2:.1f}")
    print(f"Batting First Wins: {validator.bat_first_wins} ({win_bat1_pct:.1f}%)")
    print(f"Chasing Wins: {validator.chase_wins} ({win_chase_pct:.1f}%)")
    print(f"Ties: {validator.ties}")
    print(f"Batting Strike Rate: {avg_sr:.1f}")
    print(f"Bowling Economy: {avg_econ:.2f}")
    print(f"Dot Ball %: {dot_pct:.1f}%")
    print(f"Boundary Run %: {boundary_pct:.1f}%")
    print(f"Centuries: {validator.centuries} | Fifers: {validator.fifers} | Ducks: {validator.ducks}")

    tot_d = sum(validator.dismissal_types.values())
    print("\nDismissal Distribution:")
    for dt, cnt in sorted(validator.dismissal_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {dt:12s}: {cnt:4d} ({(cnt / max(1, tot_d) * 100.0):.1f}%)")

    if validator.bugs_found:
        print("\nBugs Detected:")
        for b in validator.bugs_found:
            print(f"  [{b['bug_id']}] {b['description']}")
    else:
        print("\nALL INVARIANTS, DRAFTS, AUTO-PICKS, CHASES, AND SCORECARDS VERIFIED 100% CLEAN WITH ZERO BUGS!")


if __name__ == "__main__":
    main()

