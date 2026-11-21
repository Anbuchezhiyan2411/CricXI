"""
CricXI Analytics Service.
Queries completed match history and aggregates data for:
- Executive Summary
- Toss vs Match Winner (Hypothesis Testing)
- Bat First vs Bowl First Strategy
- Team Rating vs Winning (Correlation & Regression)
- Player Performance & Outlier Detection (Z-scores)
- Univariate Match Score & Wicket Distributions
- Correlation Matrix Heatmap
- Win Probability Prediction (Logistic Regression)
- Optional Demo Match Simulation Generator
"""

import logging
import random
import uuid
from typing import Any, Dict, List, Optional
import numpy as np
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.models.match import Match, MatchInnings, InningsBatterScore, InningsBowlerScore
from app.models.room import Room, RoomPlayer
from app.models.draft import DraftPick
from app.services.dataset_loader import dataset_service
from app.analytics.statistics import (
    compute_toss_hypothesis_test,
    compute_bat_bowl_first_analysis,
    compute_team_rating_correlation,
    compute_player_outliers,
    compute_match_distributions,
    compute_correlation_matrix,
)
from app.analytics.prediction import predictor

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Core domain service for computing sports analytics on completed CricXI matches."""

    @classmethod
    def _extract_completed_matches_data(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Extracts and normalizes completed match records from the database
        along with derived metrics like innings scores, team ratings, and names.
        """
        matches = (
            db.query(Match)
            .filter(Match.status.in_(["COMPLETED", "TIED"]))
            .order_by(Match.completed_at.desc())
            .all()
        )

        results = []
        for m in matches:
            # Sort innings
            inn_list = sorted(m.innings, key=lambda x: x.innings_number)
            inn1 = inn_list[0] if len(inn_list) > 0 else None
            inn2 = inn_list[1] if len(inn_list) > 1 else None

            s1 = inn1.total_runs if inn1 else 0
            s2 = inn2.total_runs if inn2 else 0
            w1 = inn1.total_wickets if inn1 else 0
            w2 = inn2.total_wickets if inn2 else 0
            o1 = inn1.total_overs if inn1 else 20.0
            o2 = inn2.total_overs if inn2 else 20.0

            bat_first_user = inn1.batting_team_user_id if inn1 else m.team1_user_id

            # Determine Team Names
            room = m.room
            team1_name = "Team 1"
            team2_name = "Team 2"
            if room and room.players:
                for rp in room.players:
                    if rp.user_id == m.team1_user_id:
                        team1_name = rp.username
                    elif rp.user_id == m.team2_user_id:
                        team2_name = rp.username

            # Determine Team Ratings from Draft Picks
            t1_rating = cls._compute_team_rating(db, m.room_id, m.team1_user_id, inn1, inn2)
            t2_rating = cls._compute_team_rating(db, m.room_id, m.team2_user_id, inn1, inn2)

            # Calculate match strike rate
            total_balls = 0
            total_batter_runs = 0
            if inn1:
                for b in inn1.batters:
                    total_balls += b.balls
                    total_batter_runs += b.runs
            if inn2:
                for b in inn2.batters:
                    total_balls += b.balls
                    total_batter_runs += b.runs

            avg_match_sr = (total_batter_runs / total_balls * 100.0) if total_balls > 0 else 125.0

            results.append({
                "id": m.id,
                "room_id": m.room_id,
                "team1_user_id": m.team1_user_id,
                "team2_user_id": m.team2_user_id,
                "team1_name": team1_name,
                "team2_name": team2_name,
                "team1_rating": t1_rating,
                "team2_rating": t2_rating,
                "toss_winner_id": m.toss_winner_id,
                "toss_decision": m.toss_decision or "BAT",
                "winner_user_id": m.winner_user_id,
                "result_margin": m.result_margin or "Decisive Victory",
                "status": m.status,
                "bat_first_user_id": bat_first_user,
                "innings1_runs": s1,
                "innings2_runs": s2,
                "innings1_wickets": w1,
                "innings2_wickets": w2,
                "innings1_overs": o1,
                "innings2_overs": o2,
                "avg_match_strike_rate": avg_match_sr,
                "completed_at": m.completed_at or m.created_at,
            })

        return results

    @classmethod
    def _compute_team_rating(
        cls,
        db: Session,
        room_id: int,
        user_id: str,
        inn1: Optional[MatchInnings],
        inn2: Optional[MatchInnings],
    ) -> float:
        """Computes the average player rating for a team in a match."""
        # 1. Try draft picks
        picks = db.query(DraftPick).filter(DraftPick.room_id == room_id, DraftPick.user_id == user_id).all()
        ratings = []
        if picks:
            for p in picks:
                p_data = dataset_service.get_player_by_id(p.player_id)
                if p_data:
                    ratings.append(float(p_data.get("overall_rating", 75.0) or 75.0))

        # 2. If no draft picks (e.g. wiped in rematch), use participating players
        if not ratings:
            innings_list = [inn for inn in [inn1, inn2] if inn is not None]
            for inn in innings_list:
                if inn.batting_team_user_id == user_id:
                    for b in inn.batters:
                        p_data = dataset_service.get_player_by_id(b.player_id)
                        if p_data:
                            ratings.append(float(p_data.get("overall_rating", 75.0) or 75.0))

        if ratings:
            return round(float(sum(ratings) / len(ratings)), 2)

        return 75.0

    @classmethod
    def _extract_player_performance_data(cls, db: Session) -> List[Dict[str, Any]]:
        """Aggregates all batter and bowler scores across completed matches."""
        batters = (
            db.query(InningsBatterScore)
            .join(MatchInnings, InningsBatterScore.innings_id == MatchInnings.id)
            .join(Match, MatchInnings.match_id == Match.id)
            .filter(Match.status.in_(["COMPLETED", "TIED"]))
            .all()
        )

        bowlers = (
            db.query(InningsBowlerScore)
            .join(MatchInnings, InningsBowlerScore.innings_id == MatchInnings.id)
            .join(Match, MatchInnings.match_id == Match.id)
            .filter(Match.status.in_(["COMPLETED", "TIED"]))
            .all()
        )

        players_dict: Dict[int, Dict[str, Any]] = {}

        for b in batters:
            pid = b.player_id
            if pid not in players_dict:
                p_info = dataset_service.get_player_by_id(pid) or {}
                players_dict[pid] = {
                    "player_id": pid,
                    "player_name": b.player_name,
                    "country": p_info.get("country", "International"),
                    "bat_innings": 0,
                    "total_runs": 0,
                    "total_balls": 0,
                    "outs": 0,
                    "fours": 0,
                    "sixes": 0,
                    "bowl_innings": 0,
                    "total_overs": 0.0,
                    "total_wickets": 0,
                    "runs_conceded": 0,
                    "maidens": 0,
                }

            if b.has_batted:
                players_dict[pid]["bat_innings"] += 1
                players_dict[pid]["total_runs"] += b.runs
                players_dict[pid]["total_balls"] += b.balls
                players_dict[pid]["fours"] += b.fours
                players_dict[pid]["sixes"] += b.sixes
                if b.is_out:
                    players_dict[pid]["outs"] += 1

        for bw in bowlers:
            pid = bw.player_id
            if pid not in players_dict:
                p_info = dataset_service.get_player_by_id(pid) or {}
                players_dict[pid] = {
                    "player_id": pid,
                    "player_name": bw.player_name,
                    "country": p_info.get("country", "International"),
                    "bat_innings": 0,
                    "total_runs": 0,
                    "total_balls": 0,
                    "outs": 0,
                    "fours": 0,
                    "sixes": 0,
                    "bowl_innings": 0,
                    "total_overs": 0.0,
                    "total_wickets": 0,
                    "runs_conceded": 0,
                    "maidens": 0,
                }

            if bw.overs > 0:
                players_dict[pid]["bowl_innings"] += 1
                players_dict[pid]["total_overs"] += bw.overs
                players_dict[pid]["total_wickets"] += bw.wickets
                players_dict[pid]["runs_conceded"] += bw.runs_conceded
                players_dict[pid]["maidens"] += bw.maidens

        # Compute derived rates and impact points
        results = []
        for pid, data in players_dict.items():
            matches_count = max(data["bat_innings"], data["bowl_innings"], 1)
            runs = data["total_runs"]
            balls = data["total_balls"]
            outs = data["outs"]
            wkts = data["total_wickets"]
            overs = data["total_overs"]
            conceded = data["runs_conceded"]
            fours = data["fours"]
            sixes = data["sixes"]
            maidens = data["maidens"]

            bat_avg = (runs / outs) if outs > 0 else float(runs)
            sr = (runs / balls * 100.0) if balls > 0 else 0.0
            bowl_avg = (conceded / wkts) if wkts > 0 else (conceded if conceded > 0 else 0.0)
            econ = (conceded / overs) if overs > 0 else 0.0

            # Fantasy & Impact score formula
            # Runs: 1 pt each | Wickets: 20 pts each | Fours: 1 bonus | Sixes: 2 bonus | Maidens: 12 bonus
            impact_total = (runs * 1.0) + (wkts * 20.0) + (fours * 1.0) + (sixes * 2.0) + (maidens * 12.0)
            avg_impact = impact_total / matches_count

            results.append({
                "player_id": pid,
                "player_name": data["player_name"],
                "country": data["country"],
                "matches_played": matches_count,
                "total_runs": runs,
                "batting_avg": bat_avg,
                "strike_rate": sr,
                "total_wickets": wkts,
                "bowling_avg": bowl_avg,
                "economy": econ,
                "impact_points": avg_impact,
            })

        return results

    # =========================================================================
    # Public Analytics API Endpoints Implementations
    # =========================================================================

    @classmethod
    def get_summary(cls, db: Session) -> Dict[str, Any]:
        """Returns executive KPI summary of the analytics repository."""
        matches = cls._extract_completed_matches_data(db)
        toss_analysis = compute_toss_hypothesis_test(matches)
        bat_analysis = compute_bat_bowl_first_analysis(matches)
        rating_corr = compute_team_rating_correlation(matches)
        match_stats = compute_match_distributions(matches)

        return {
            "total_matches": len(matches),
            "toss_analysis_summary": {
                "observed_toss_win_rate": toss_analysis["observed_toss_win_rate"],
                "p_value": toss_analysis["p_value"],
                "is_significant": toss_analysis["is_significant"],
                "conclusion": toss_analysis["conclusion"],
            },
            "batting_strategy_summary": {
                "best_strategy": bat_analysis["best_strategy"],
                "bat_first_win_rate": bat_analysis["bat_first_win_rate"],
                "bowl_first_win_rate": bat_analysis["bowl_first_win_rate"],
                "avg_first_innings_score": bat_analysis["avg_first_innings_score"],
            },
            "team_rating_summary": {
                "correlation_coefficient": rating_corr["correlation_coefficient"],
                "strength": rating_corr["strength"],
                "direction": rating_corr["direction"],
            },
            "match_highlights": {
                "highest_score": match_stats["highest_score"],
                "lowest_score": match_stats["lowest_score"],
                "average_strike_rate": match_stats["average_strike_rate"],
                "average_run_rate": match_stats["average_run_rate"],
                "average_wickets": match_stats["average_wickets"],
            },
            "data_science_concepts": [
                "Hypothesis Testing (One-Sample Proportion Z-Test)",
                "Bivariate Correlation Analysis (Pearson r)",
                "Outlier Detection (Standardized Z-Scores)",
                "Descriptive Statistics (Central Tendency & Dispersion)",
                "Predictive Analytics (Binary Logistic Regression)",
            ],
        }

    @classmethod
    def get_toss_analysis(cls, db: Session) -> Dict[str, Any]:
        """Returns Section 1: Toss vs Match Winner hypothesis testing analysis."""
        matches = cls._extract_completed_matches_data(db)
        return compute_toss_hypothesis_test(matches)

    @classmethod
    def get_batting_analysis(cls, db: Session) -> Dict[str, Any]:
        """Returns Section 2: Bat First vs Bowl First comparative analytics."""
        matches = cls._extract_completed_matches_data(db)
        return compute_bat_bowl_first_analysis(matches)

    @classmethod
    def get_team_rating_analysis(cls, db: Session) -> Dict[str, Any]:
        """Returns Section 3: Team Rating vs Winning correlation and regression."""
        matches = cls._extract_completed_matches_data(db)
        return compute_team_rating_correlation(matches)

    @classmethod
    def get_player_performance(cls, db: Session) -> Dict[str, Any]:
        """Returns Section 4: Player Performance and Z-score outlier detection."""
        players_data = cls._extract_player_performance_data(db)
        return compute_player_outliers(players_data)

    @classmethod
    def get_match_statistics(cls, db: Session) -> Dict[str, Any]:
        """Returns Section 5: Univariate descriptive statistics, histograms, and boxplots."""
        matches = cls._extract_completed_matches_data(db)
        return compute_match_distributions(matches)

    @classmethod
    def get_correlation_matrix(cls, db: Session) -> Dict[str, Any]:
        """Returns Section 7: Pairwise Pearson correlation heatmap matrix."""
        matches = cls._extract_completed_matches_data(db)
        return compute_correlation_matrix(matches)

    @classmethod
    def predict_win_probability(
        cls,
        team_a_rating: float,
        team_b_rating: float,
        toss_winner: str = "team_a",
        toss_decision: str = "BAT",
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Returns Section 6: Logistic Regression match win probability prediction."""
        if db is not None:
            matches = cls._extract_completed_matches_data(db)
            predictor.train_on_matches(matches)

        return predictor.predict(
            team_a_rating=team_a_rating,
            team_b_rating=team_b_rating,
            toss_winner=toss_winner,
            toss_decision=toss_decision,
        )

    @classmethod
    def generate_demo_matches(cls, db: Session, count: int = 15) -> Dict[str, Any]:
        """
        Synthesizes realistic historical completed matches into the database
        so users can explore rich analytics immediately without manual play.
        """
        all_players = dataset_service.get_all_players()
        if not all_players:
            return {"success": False, "message": "Player dataset not loaded."}

        countries = ["India", "Australia", "England", "South Africa", "Pakistan", "New Zealand", "West Indies"]
        created_matches = []

        now = datetime.now(timezone.utc)

        for i in range(1, count + 1):
            room_code = f"D{uuid.uuid4().hex[:5].upper()}"
            # Create room
            room = Room(
                room_code=room_code,
                host_id=f"user_demo_host_{i}",
                status="COMPLETED",
                current_round=11,
            )
            db.add(room)
            db.commit()
            db.refresh(room)

            c1 = random.choice(countries)
            c2 = random.choice([c for c in countries if c != c1])
            p1_name = f"{c1} Masters"
            p2_name = f"{c2} Champions"

            rp1 = RoomPlayer(room_id=room.id, user_id=room.host_id, username=p1_name, is_host=True, is_ready=True)
            guest_id = f"user_demo_guest_{i}"
            rp2 = RoomPlayer(room_id=room.id, user_id=guest_id, username=p2_name, is_host=False, is_ready=True)
            db.add_all([rp1, rp2])
            db.commit()

            # Pick 11 random players for each team
            team1_players = random.sample(all_players, 11)
            remaining = [p for p in all_players if p not in team1_players]
            team2_players = random.sample(remaining, 11)

            # Store draft picks for rating calculation
            for idx, p in enumerate(team1_players, 1):
                db.add(DraftPick(
                    room_id=room.id,
                    round_number=idx,
                    user_id=room.host_id,
                    player_id=int(p["player_id"]),
                    player_name=p["player_name"],
                    batting_position=idx,
                    selected_country=p.get("country", "India"),
                    selected_decade=int(p.get("decade", 2010)),
                ))
            for idx, p in enumerate(team2_players, 1):
                db.add(DraftPick(
                    room_id=room.id,
                    round_number=idx,
                    user_id=guest_id,
                    player_id=int(p["player_id"]),
                    player_name=p["player_name"],
                    batting_position=idx,
                    selected_country=p.get("country", "Australia"),
                    selected_decade=int(p.get("decade", 2010)),
                ))
            db.commit()

            # Randomize toss
            toss_winner_id = room.host_id if random.random() < 0.5 else guest_id
            toss_decision = "BAT" if random.random() < 0.55 else "BOWL"

            if (toss_winner_id == room.host_id and toss_decision == "BAT") or (toss_winner_id == guest_id and toss_decision == "BOWL"):
                bat_first_id = room.host_id
                bowl_first_id = guest_id
                bat_first_players = team1_players
                bowl_first_players = team2_players
            else:
                bat_first_id = guest_id
                bowl_first_id = room.host_id
                bat_first_players = team2_players
                bowl_first_players = team1_players

            # Generate realistic 1st innings score (130 - 215)
            s1 = int(np.random.normal(168, 18))
            s1 = max(115, min(235, s1))
            w1 = min(10, max(2, int(np.random.normal(6, 2))))

            # Match target
            target = s1 + 1

            # Second innings
            # Chasing outcome: 52% chase win rate
            chase_won = random.random() < 0.52
            if chase_won:
                s2 = target
                w2 = min(9, max(2, int(np.random.normal(5, 2))))
                winner_id = bowl_first_id
                margin = f"{10 - w2} wickets"
            else:
                s2 = target - random.randint(3, 35)
                s2 = max(80, s2)
                w2 = min(10, max(4, int(np.random.normal(7, 2))))
                winner_id = bat_first_id
                margin = f"{s1 - s2} runs"

            match_time = now - timedelta(days=count - i, hours=random.randint(1, 12))

            match = Match(
                room_id=room.id,
                team1_user_id=room.host_id,
                team2_user_id=guest_id,
                toss_winner_id=toss_winner_id,
                toss_decision=toss_decision,
                status="COMPLETED",
                winner_user_id=winner_id,
                result_margin=margin,
                current_innings=2,
                target=target,
                created_at=match_time - timedelta(minutes=45),
                completed_at=match_time,
            )
            db.add(match)
            db.commit()
            db.refresh(match)

            # Create innings 1
            inn1 = MatchInnings(
                match_id=match.id,
                innings_number=1,
                batting_team_user_id=bat_first_id,
                bowling_team_user_id=bowl_first_id,
                total_runs=s1,
                total_wickets=w1,
                total_overs=20.0,
                legal_balls_bowled=120,
                is_completed=True,
            )
            db.add(inn1)
            db.commit()
            db.refresh(inn1)

            # Create innings 2
            inn2 = MatchInnings(
                match_id=match.id,
                innings_number=2,
                batting_team_user_id=bowl_first_id,
                bowling_team_user_id=bat_first_id,
                total_runs=s2,
                total_wickets=w2,
                total_overs=19.3 if chase_won else 20.0,
                legal_balls_bowled=117 if chase_won else 120,
                is_completed=True,
            )
            db.add(inn2)
            db.commit()
            db.refresh(inn2)

            # Seed batter scores for innings 1
            rem_runs1 = s1
            rem_balls1 = 120
            for pos, p in enumerate(bat_first_players[:min(11, w1 + 2)], 1):
                b_runs = int(rem_runs1 * random.uniform(0.15, 0.45)) if pos <= 4 else int(rem_runs1 * random.uniform(0.05, 0.25))
                b_runs = min(rem_runs1, max(0, b_runs))
                rem_runs1 -= b_runs
                b_balls = max(1, min(rem_balls1, int(b_runs * random.uniform(0.65, 0.95))))
                rem_balls1 = max(0, rem_balls1 - b_balls)
                fours = b_runs // 10
                sixes = b_runs // 18
                is_out = pos <= w1
                sr = (b_runs / b_balls * 100.0) if b_balls > 0 else 0.0

                db.add(InningsBatterScore(
                    innings_id=inn1.id,
                    player_id=int(p["player_id"]),
                    player_name=p["player_name"],
                    batting_position=pos,
                    runs=b_runs,
                    balls=b_balls,
                    fours=fours,
                    sixes=sixes,
                    strike_rate=sr,
                    is_out=is_out,
                    has_batted=True,
                    decade=int(p.get("decade", 2010)),
                    dismissal_text="c & b Bowler" if is_out else "not out",
                ))

            # Seed bowler scores for innings 1
            bowl_options1 = [p for p in bowl_first_players if p.get("primary_role") in ("PACE", "SPIN", "AR") or float(p.get("bowling_rating", 0) or 0) >= 40][:5]
            if len(bowl_options1) < 5:
                bowl_options1 = bowl_first_players[6:11]
            rem_wkts1 = w1
            for bw in bowl_options1:
                bw_wkts = min(rem_wkts1, random.choice([0, 1, 1, 2, 3]))
                rem_wkts1 -= bw_wkts
                bw_runs = s1 // len(bowl_options1) + random.randint(-8, 8)
                db.add(InningsBowlerScore(
                    innings_id=inn1.id,
                    player_id=int(bw["player_id"]),
                    player_name=bw["player_name"],
                    decade=int(bw.get("decade", 2010)),
                    overs=4.0,
                    legal_balls=24,
                    maidens=1 if bw_runs < 20 else 0,
                    runs_conceded=max(12, bw_runs),
                    wickets=bw_wkts,
                    economy=round(max(12, bw_runs) / 4.0, 2),
                ))

            # Seed batter scores for innings 2
            rem_runs2 = s2
            rem_balls2 = 120
            for pos, p in enumerate(bowl_first_players[:min(11, w2 + 2)], 1):
                b_runs = int(rem_runs2 * random.uniform(0.15, 0.45)) if pos <= 4 else int(rem_runs2 * random.uniform(0.05, 0.25))
                b_runs = min(rem_runs2, max(0, b_runs))
                rem_runs2 -= b_runs
                b_balls = max(1, min(rem_balls2, int(b_runs * random.uniform(0.65, 0.95))))
                rem_balls2 = max(0, rem_balls2 - b_balls)
                fours = b_runs // 10
                sixes = b_runs // 18
                is_out = pos <= w2
                sr = (b_runs / b_balls * 100.0) if b_balls > 0 else 0.0

                db.add(InningsBatterScore(
                    innings_id=inn2.id,
                    player_id=int(p["player_id"]),
                    player_name=p["player_name"],
                    batting_position=pos,
                    runs=b_runs,
                    balls=b_balls,
                    fours=fours,
                    sixes=sixes,
                    strike_rate=sr,
                    is_out=is_out,
                    has_batted=True,
                    decade=int(p.get("decade", 2010)),
                    dismissal_text="b Stumps" if is_out else "not out",
                ))

            # Seed bowler scores for innings 2
            bowl_options2 = [p for p in bat_first_players if p.get("primary_role") in ("PACE", "SPIN", "AR") or float(p.get("bowling_rating", 0) or 0) >= 40][:5]
            if len(bowl_options2) < 5:
                bowl_options2 = bat_first_players[6:11]
            rem_wkts2 = w2
            for bw in bowl_options2:
                bw_wkts = min(rem_wkts2, random.choice([0, 1, 1, 2, 3]))
                rem_wkts2 -= bw_wkts
                bw_runs = s2 // len(bowl_options2) + random.randint(-8, 8)
                db.add(InningsBowlerScore(
                    innings_id=inn2.id,
                    player_id=int(bw["player_id"]),
                    player_name=bw["player_name"],
                    decade=int(bw.get("decade", 2010)),
                    overs=4.0,
                    legal_balls=24,
                    maidens=1 if bw_runs < 20 else 0,
                    runs_conceded=max(12, bw_runs),
                    wickets=bw_wkts,
                    economy=round(max(12, bw_runs) / 4.0, 2),
                ))

            db.commit()
            created_matches.append(match.id)

        logger.info("Successfully generated %d realistic demo simulation matches.", len(created_matches))
        return {
            "success": True,
            "message": f"Successfully generated {len(created_matches)} completed demo simulation matches.",
            "match_ids": created_matches,
        }
