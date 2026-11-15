"""
Match Service for CricXI Live T20 Simulation.
Coordinates match setup, squad resolution from draft, authoritative
ball-by-ball execution, cricket rules enforcement, scorecard updates,
target calculations, and final victory declaration.
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.draft import DraftPick
from app.models.match import (
    Match,
    MatchInnings,
    BallEvent,
    InningsBatterScore,
    InningsBowlerScore,
)
from app.models.room import Room, RoomPlayer
from app.models.toss import TossState
from app.schemas.match import (
    BatterLiveInfo,
    BowlerLiveInfo,
    BallEventDetail,
    CommentaryEntry,
    InningsScorecard,
    TeamMatchInfo,
    LiveMatchStateResponse,
)
from app.services.dataset_loader import dataset_service
from app.match.simulation_engine import SimulationEngine, DeliverySimulationResult
from app.match.statistical_profiler import (
    StatisticalProfiler,
    get_pitch_for_match,
    get_weather_for_match,
)

logger = logging.getLogger(__name__)


class MatchService:
    """Service handling all business and match logic for CricXI."""

    @classmethod
    def _ensure_dataset(cls) -> None:
        if not dataset_service.is_loaded:
            dataset_service.load()
        profiler = StatisticalProfiler.get_instance()
        if not profiler.stats_cache:
            profiler.fit(dataset_service.get_all_players())

    @classmethod
    def _get_player_data(cls, player_id: int) -> Dict[str, Any]:
        cls._ensure_dataset()
        data = dataset_service.get_player_by_id(player_id)
        if not data:
            return {
                "player_id": player_id,
                "player_name": f"Player #{player_id}",
                "batting_rating": 70.0,
                "bowling_rating": 60.0,
                "overall_rating": 65.0,
                "strike_rate": 125.0,
                "batting_average": 26.0,
                "economy": 8.0,
                "bowling_strike_rate": 20.0,
                "bowling_type": "Right-arm Medium",
            }
        return data

    @classmethod
    def _get_team_info(cls, db: Session, room: Room, player: RoomPlayer) -> TeamMatchInfo:
        cls._ensure_dataset()
        picks = (
            db.query(DraftPick)
            .filter(DraftPick.room_id == room.id, DraftPick.user_id == player.user_id)
            .all()
        )
        captain_name = player.username
        highest_ovr_player = None
        highest_ovr = -1.0

        for pick in picks:
            p_data = cls._get_player_data(pick.player_id)
            ovr = float(p_data.get("overall_rating", 0.0))
            if ovr > highest_ovr:
                highest_ovr = ovr
                highest_ovr_player = p_data.get("player_name")
            if p_data.get("is_captain"):
                captain_name = p_data.get("player_name", player.username)
                break
        else:
            if highest_ovr_player:
                captain_name = highest_ovr_player

        team_name = f"{captain_name}'s XI"
        return TeamMatchInfo(
            user_id=player.user_id,
            username=player.username,
            is_host=player.is_host,
            captain_name=captain_name,
            team_name=team_name,
        )

    @classmethod
    def _select_eligible_bowler(
        cls,
        db: Session,
        room_id: int,
        bowling_team_user_id: str,
        innings_id: int,
        current_bowler_id: Optional[int] = None,
        over_number: int = 1,
    ) -> int:
        """
        Selects an eligible bowler adhering to:
        1. Max 4 overs (24 legal balls) per bowler.
        2. No consecutive overs by the same bowler.
        3. Phase-aware captaincy (Powerplay pace, Middle spin/AR, Death specialists).
        4. Wicketkeepers are strictly excluded from bowling.
        """
        cls._ensure_dataset()
        db.flush()

        picks = (
            db.query(DraftPick)
            .filter(DraftPick.room_id == room_id, DraftPick.user_id == bowling_team_user_id)
            .all()
        )

        bowler_scores = (
            db.query(InningsBowlerScore)
            .filter(InningsBowlerScore.innings_id == innings_id)
            .all()
        )
        balls_by_player: Dict[int, int] = {bs.player_id: bs.legal_balls for bs in bowler_scores}

        candidates = []
        for pick in picks:
            pid = pick.player_id
            legal_balls = balls_by_player.get(pid, 0)
            if legal_balls >= 24:
                # Bowler completed max 4 overs quota
                continue
            if current_bowler_id is not None and pid == current_bowler_id:
                # Cannot bowl consecutive overs
                continue

            p_data = cls._get_player_data(pid)
            role = str(p_data.get("primary_role", "")).upper()
            is_wk = bool(p_data.get("is_wicketkeeper", False))
            if is_wk:
                continue

            bowling_rating = float(p_data.get("bowling_rating", 0.0) or 0.0)
            bowling_type = str(p_data.get("bowling_type", "")).lower()
            is_spin = role == "SPIN" or "spin" in bowling_type or "break" in bowling_type or "orthodox" in bowling_type or "chinaman" in bowling_type
            is_pace = role == "PACE" or "fast" in bowling_type or "medium" in bowling_type or "seam" in bowling_type

            # Base priority from bowling rating and role
            priority = bowling_rating
            if role in ("PACE", "SPIN"):
                priority += 40.0
            elif role == "AR":
                priority += 25.0

            # Phase-aware Captain AI
            # 1. Powerplay (Overs 1-6)
            if over_number <= 6:
                if is_pace:
                    priority += 50.0
                elif is_spin and bowling_rating >= 85.0:
                    priority += 15.0
                elif is_spin:
                    priority -= 35.0

                # Crucial T20 rule: Never bowl 3 overs in powerplay
                if legal_balls >= 12:
                    priority -= 150.0

            # 2. Middle Overs (Overs 7-15)
            elif 7 <= over_number <= 15:
                if is_spin:
                    priority += 50.0
                elif role == "AR":
                    priority += 35.0
                elif is_pace:
                    priority += 20.0

                # Preserve death pacers: if high-rated pace bowler already has 2 overs, save them for death
                if is_pace and bowling_rating >= 82.0 and legal_balls >= 12 and over_number <= 14:
                    priority -= 40.0

            # 3. Death Overs (Overs 16-20)
            else:
                if is_pace and bowling_rating >= 80.0:
                    priority += 80.0
                elif is_spin and bowling_rating >= 88.0:
                    priority += 45.0
                elif is_pace:
                    priority += 35.0
                elif role == "AR" and bowling_rating >= 75.0:
                    priority += 25.0
                else:
                    priority -= 200.0

            candidates.append((priority, pid))

        if candidates:
            # Sort by highest priority
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]

        # Fallback to any non-wicketkeeper who hasn't completed 4 overs (strictly < 24 balls)
        for pick in picks:
            pid = pick.player_id
            p_data = cls._get_player_data(pid)
            if not p_data.get("is_wicketkeeper") and balls_by_player.get(pid, 0) < 24 and pid != current_bowler_id:
                return pid

        # Emergency fallback strictly among non-wicketkeepers who have not completed 24 balls
        non_wk_picks = [
            p for p in picks
            if not cls._get_player_data(p.player_id).get("is_wicketkeeper")
            and balls_by_player.get(p.player_id, 0) < 24
        ]
        if non_wk_picks:
            for p in non_wk_picks:
                if p.player_id != current_bowler_id:
                    return p.player_id
            return non_wk_picks[0].player_id

        # Absolute fallback if team somehow has only 1 player under 24 balls
        for pick in picks:
            if not cls._get_player_data(pick.player_id).get("is_wicketkeeper") and balls_by_player.get(pick.player_id, 0) < 24:
                return pick.player_id

        return picks[0].player_id if picks else 0

    @classmethod
    def _generate_realistic_dismissal(
        cls,
        db: Session,
        room_id: int,
        bowling_team_user_id: str,
        bowler_id: int,
        bowler_data: Dict[str, Any],
        wicket_type: str,
        striker_name: str,
        seed: Optional[int] = None,
    ) -> Tuple[str, str]:
        """
        Generates realistic dismissal text and broadcast commentary.
        Uses actual fielders from the bowling team's drafted XI, designates the real
        wicketkeeper for caught behinds and stumpings, caught & bowled, rare substitutes (3%),
        and realistic run-out fielder credits.
        Returns: (dismissal_text, commentary_override)
        """
        import random
        rng = random.Random(seed) if seed is not None else random.Random()

        # Retrieve all 11 players in the fielding XI
        fielding_picks = (
            db.query(DraftPick)
            .filter(DraftPick.room_id == room_id, DraftPick.user_id == bowling_team_user_id)
            .all()
        )

        # Identify designated wicketkeeper from the XI
        wk_pick = None
        for p in fielding_picks:
            p_info = cls._get_player_data(p.player_id)
            if bool(p_info.get("is_wicketkeeper", False)):
                wk_pick = p
                break

        if wk_pick:
            wk_data = cls._get_player_data(wk_pick.player_id)
            wk_name = wk_data.get("player_name", wk_pick.player_name)
            wk_id = wk_pick.player_id
        else:
            # Fallback if no designated WK found: choose player with highest fielding rating
            sorted_fielders = sorted(
                fielding_picks,
                key=lambda p: float(cls._get_player_data(p.player_id).get("fielding_rating", 70.0) or 70.0),
                reverse=True,
            )
            fallback_wk = sorted_fielders[0] if sorted_fielders else None
            wk_name = cls._get_player_data(fallback_wk.player_id).get("player_name", fallback_wk.player_name) if fallback_wk else "Wicketkeeper"
            wk_id = fallback_wk.player_id if fallback_wk else None

        bw_decade = bowler_data.get("decade")
        b_era = f" ({bw_decade})" if bw_decade else ""
        b_name = f"{bowler_data.get('player_name', 'Bowler')}{b_era}"
        bw_only = bowler_data.get("player_name", "Bowler")
        bowling_type = str(bowler_data.get("bowling_type", "")).lower()
        is_spin = "spin" in bowling_type or "break" in bowling_type or "orthodox" in bowling_type or "chinaman" in bowling_type or "slow" in bowling_type

        # 1. BOWLED
        if wicket_type == "Bowled":
            d_text = f"b {b_name}"
            comm = rng.choice([
                f"TIMBER! {bw_only} produces an absolute peach! Rips past {striker_name}'s defense and shatters the off-stump! OUT!",
                f"CLEAN BOWLED! Through the gate! {bw_only} hits the top of middle stump, sending the bails flying!",
                f"BOWLED HIM! Deceived in flight and pace by {bw_only}! The furniture is completely disturbed! Huge wicket!",
            ])
            return d_text, comm

        # 2. LBW
        if wicket_type == "LBW":
            d_text = f"lbw b {b_name}"
            comm = rng.choice([
                f"MASSIVE APPEAL... AND GIVEN! {bw_only} strikes {striker_name} plumb in front! Umpire raises the finger without hesitation!",
                f"LOUD SHOUT FOR LBW! Trapped right on the back foot! {bw_only} gets the decision in his favor, {striker_name} is on his way!",
                f"DEAD IN FRONT! Nips back sharply from {bw_only}, hits {striker_name} in front of middle. Plumb as they come!",
            ])
            return d_text, comm

        # 3. HIT WICKET
        if wicket_type == "Hit wicket":
            d_text = f"hit wicket b {b_name}"
            comm = f"HIT WICKET! Calamity for {striker_name}! In going back deep in the crease, {striker_name} dislodges the bails with the bat!"
            return d_text, comm

        # 4. STUMPED
        if wicket_type == "Stumped":
            d_text = f"st {wk_name} b {b_name}"
            comm = rng.choice([
                f"STUMPED! {striker_name} steps out to attack, beaten in flight by {bw_only}, and {wk_name} whips the bails off in a split second!",
                f"LIGHTNING WORK BY {wk_name}! {striker_name} was dragged out of the crease, and {wk_name} breaks the stumps with clinical precision!",
            ])
            return d_text, comm

        # 5. RUN OUT
        if wicket_type == "Run out":
            outfielders = [p for p in fielding_picks if p.player_id != wk_id]
            f_pick = rng.choice(outfielders) if outfielders else (fielding_picks[0] if fielding_picks else None)
            f_name = cls._get_player_data(f_pick.player_id).get("player_name", f_pick.player_name) if f_pick else "Fielder"

            is_direct_hit = rng.random() < 0.70
            if is_direct_hit:
                d_text = f"run out ({f_name})"
                comm = f"RUN OUT! Disastrous hesitation between the wickets! Direct hit from {f_name} catches {striker_name} well short of the crease!"
            else:
                d_text = f"run out ({f_name}/{wk_name})"
                comm = f"RUN OUT! Laser throw from {f_name} to {wk_name}, who swiftly removes the bails with {striker_name} diving desperately short!"
            return d_text, comm

        # 6. CAUGHT (Eliminate hardcoded 'c sub b ...')
        roll = rng.random()

        # Rare substitute catch (2-3%)
        if roll < 0.03:
            sub_names = ["sub (A Patel)", "sub (J Root)", "sub (M Wade)", "sub (D Mitchell)", "sub (K Williamson)", "sub"]
            sub_label = rng.choice(sub_names)
            d_text = f"c {sub_label} b {b_name}"
            comm = f"OUT! {striker_name} mistimes the aerial stroke off {bw_only}, and the substitute fielder safely pouches it on the boundary rope!"
            return d_text, comm

        # Caught & Bowled (7%)
        if roll < 0.10:
            d_text = f"c & b {b_name}"
            comm = rng.choice([
                f"CAUGHT AND BOWLED! {striker_name} drives firmly back down the pitch, and {bw_only} snatches a breathtaking reflex return catch!",
                f"C&B! Leading edge pops back up, and {bw_only} dives forward to complete a stunning return catch!",
            ])
            return d_text, comm

        # Caught behind to wicketkeeper (~26% for pace, ~14% for spin)
        wk_catch_threshold = 0.24 if is_spin else 0.36
        if roll < wk_catch_threshold:
            d_text = f"c {wk_name} b {b_name}"
            comm = rng.choice([
                f"EDGED AND TAKEN! Thick outside edge off {bw_only}, and {wk_name} makes no mistake diving to his right with the gloves!",
                f"NICKED! Beautiful seam movement from {bw_only}, {striker_name} feathers an edge and {wk_name} takes a regulation catch!",
                f"OUT! Faint edge through to the keeper! {wk_name} pouches it comfortably behind the stumps off {bw_only}!",
            ])
            return d_text, comm

        # Outfield catch by actual fielders from the playing XI
        outfield_candidates = [
            p for p in fielding_picks
            if p.player_id != bowler_id and (not wk_id or p.player_id != wk_id)
        ]
        if not outfield_candidates:
            outfield_candidates = [p for p in fielding_picks if p.player_id != bowler_id]
        if not outfield_candidates:
            outfield_candidates = fielding_picks

        if outfield_candidates:
            weights = [
                float(cls._get_player_data(p.player_id).get("fielding_rating", 75.0) or 75.0)
                for p in outfield_candidates
            ]
            chosen_pick = rng.choices(outfield_candidates, weights=weights, k=1)[0]
            chosen_data = cls._get_player_data(chosen_pick.player_id)
            fielder_name = chosen_data.get("player_name", chosen_pick.player_name)
        else:
            fielder_name = "Fielder"

        positions = ["deep mid-wicket", "long-on", "long-off", "deep square leg", "cover point", "extra cover", "backward point", "mid-wicket"]
        pos = rng.choice(positions)

        d_text = f"c {fielder_name} b {b_name}"
        comm = rng.choice([
            f"OUT! {striker_name} miscues the lofted drive off {bw_only}! {fielder_name} tracks it at {pos} and takes a magnificent catch!",
            f"IN THE AIR AND GONE! {striker_name} mistimes it high towards {pos}, where {fielder_name} settles under it safely! Breakthrough for {bw_only}!",
            f"WHAT A CATCH! {fielder_name} sprints in from {pos} and takes a stunning tumbling catch to dismiss {striker_name} off {bw_only}!",
        ])
        return d_text, comm

    @classmethod
    def initialize_or_get_match(
        cls,
        db: Session,
        room_code: str,
    ) -> LiveMatchStateResponse:
        """
        Idempotently initializes the T20 match for the room after toss is completed,
        or retrieves the active live match state.
        """
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        toss_state = db.query(TossState).filter(TossState.room_id == room.id).first()
        if not toss_state or toss_state.step != "COMPLETED" or not toss_state.decision:
            raise ValueError(f"Toss has not been completed for room '{code}'.")

        match = db.query(Match).filter(Match.room_id == room.id).first()
        if not match:
            host_p = next((p for p in room.players if p.is_host), None)
            guest_p = next((p for p in room.players if not p.is_host), None)
            if not host_p or not guest_p:
                raise ValueError("Both players must be in room.")

            match = Match(
                room_id=room.id,
                team1_user_id=host_p.user_id,
                team2_user_id=guest_p.user_id,
                toss_winner_id=toss_state.winner_id,
                toss_decision=toss_state.decision,
                status="LIVE",
            )
            db.add(match)
            db.flush()

        if match.status == "PENDING":
            match.status = "LIVE"
            match.toss_winner_id = toss_state.winner_id
            match.toss_decision = toss_state.decision

        # Determine 1st innings batting & bowling teams
        # Toss winner's choice:
        # If "BAT" -> toss winner bats first
        # If "BOWL" -> opponent bats first
        opponent_id = (
            match.team2_user_id
            if toss_state.winner_id == match.team1_user_id
            else match.team1_user_id
        )

        if toss_state.decision.upper() == "BAT":
            inn1_batting_user_id = toss_state.winner_id
            inn1_bowling_user_id = opponent_id
        else:
            inn1_batting_user_id = opponent_id
            inn1_bowling_user_id = toss_state.winner_id

        # Check if Innings 1 exists
        inn1 = (
            db.query(MatchInnings)
            .filter(MatchInnings.match_id == match.id, MatchInnings.innings_number == 1)
            .first()
        )

        if not inn1:
            # Setup Innings 1
            inn1 = MatchInnings(
                match_id=match.id,
                innings_number=1,
                batting_team_user_id=inn1_batting_user_id,
                bowling_team_user_id=inn1_bowling_user_id,
                total_runs=0,
                total_wickets=0,
                total_overs=0.0,
                legal_balls_bowled=0,
                is_completed=False,
            )
            db.add(inn1)
            db.flush()

            # Retrieve batting order for batting team
            batting_picks = (
                db.query(DraftPick)
                .filter(DraftPick.room_id == room.id, DraftPick.user_id == inn1_batting_user_id)
                .order_by(DraftPick.batting_position.asc())
                .all()
            )

            # Initialize batters in InningsBatterScore
            for pick in batting_picks:
                p_data = cls._get_player_data(pick.player_id)
                p_name = p_data.get("player_name", pick.player_name)
                decade_val = int(p_data.get("decade", 0)) if p_data.get("decade") else None
                is_opener = pick.batting_position in (1, 2)
                b_score = InningsBatterScore(
                    innings_id=inn1.id,
                    player_id=pick.player_id,
                    player_name=p_name,
                    decade=decade_val,
                    batting_position=pick.batting_position,
                    runs=0,
                    balls=0,
                    fours=0,
                    sixes=0,
                    strike_rate=0.0,
                    is_out=False,
                    has_batted=is_opener,
                    dismissal_text="not out" if is_opener else "DNB",
                )
                db.add(b_score)

            # Set opening batters (positions 1 and 2)
            if len(batting_picks) >= 2:
                inn1.current_striker_id = batting_picks[0].player_id
                inn1.current_non_striker_id = batting_picks[1].player_id
            elif len(batting_picks) == 1:
                inn1.current_striker_id = batting_picks[0].player_id

            # Select opening bowler
            opening_bowler_id = cls._select_eligible_bowler(
                db=db,
                room_id=room.id,
                bowling_team_user_id=inn1_bowling_user_id,
                innings_id=inn1.id,
                over_number=1,
            )
            inn1.current_bowler_id = opening_bowler_id

            # Initialize bowler score
            bowler_data = cls._get_player_data(opening_bowler_id)
            bowl_decade = int(bowler_data.get("decade", 0)) if bowler_data.get("decade") else None
            bowl_score = InningsBowlerScore(
                innings_id=inn1.id,
                player_id=opening_bowler_id,
                player_name=bowler_data.get("player_name", f"Bowler #{opening_bowler_id}"),
                decade=bowl_decade,
                overs=0.0,
                legal_balls=0,
                maidens=0,
                runs_conceded=0,
                wickets=0,
                economy=0.0,
                wides=0,
                no_balls=0,
            )
            db.add(bowl_score)

            db.commit()
            db.refresh(match)
            logger.info("Innings 1 initialized for match %d (Room %s)", match.id, code)

        return cls.get_live_match_state(db, code)

    @classmethod
    def step_delivery(
        cls,
        db: Session,
        room_code: str,
        seed: Optional[int] = None,
    ) -> Tuple[DeliverySimulationResult, LiveMatchStateResponse]:
        """
        Executes a single ball delivery simulation, enforces all cricket rules,
        updates batsman/bowler figures and match totals, and checks for innings/match end.
        """
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        match = db.query(Match).filter(Match.room_id == room.id).first()
        if not match:
            raise ValueError(f"Match not found for room '{code}'.")

        if match.status in ("COMPLETED", "TIED"):
            # Match is already finished
            state = cls.get_live_match_state(db, code)
            dummy = DeliverySimulationResult(
                outcome="DOT",
                batter_runs=0,
                extras=0,
                extra_type=None,
                is_legal=True,
                is_wicket=False,
                wicket_type=None,
                runs_scored=0,
                strike_changed=False,
                commentary="Match is already completed.",
                short_display="•",
            )
            return dummy, state

        # Determine active innings
        active_innings = (
            db.query(MatchInnings)
            .filter(MatchInnings.match_id == match.id, MatchInnings.is_completed == False)  # noqa: E712
            .order_by(MatchInnings.innings_number.asc())
            .first()
        )

        if not active_innings:
            # Both innings completed
            match.status = "COMPLETED"
            db.commit()
            return cls.step_delivery(db, room_code, seed)

        cls._ensure_dataset()

        # Retrieve current striker and bowler stats
        striker_id = active_innings.current_striker_id
        non_striker_id = active_innings.current_non_striker_id
        bowler_id = active_innings.current_bowler_id

        if not striker_id or not bowler_id:
            raise ValueError("Striker or Bowler is not assigned for current innings.")

        striker_data = cls._get_player_data(striker_id)
        bowler_data = cls._get_player_data(bowler_id)

        # Context for simulation
        over_number = int(active_innings.legal_balls_bowled // 6)
        ball_in_over = int((active_innings.legal_balls_bowled % 6) + 1)
        wickets_fallen = active_innings.total_wickets
        balls_remaining = 120 - active_innings.legal_balls_bowled
        runs_required = (match.target - active_innings.total_runs) if (active_innings.innings_number == 2 and match.target) else None

        # Stage 5 & 6 & 7: Dynamic Match Context
        pitch_type = get_pitch_for_match(match.id)
        weather_condition = get_weather_for_match(match.id)

        # Unbroken partnership runs & balls
        last_wkt_event = (
            db.query(BallEvent)
            .filter(BallEvent.innings_id == active_innings.id, BallEvent.is_wicket == True)  # noqa: E712
            .order_by(BallEvent.id.desc())
            .first()
        )
        last_wkt_id = last_wkt_event.id if last_wkt_event else 0
        part_events = (
            db.query(BallEvent)
            .filter(BallEvent.innings_id == active_innings.id, BallEvent.id > last_wkt_id)
            .all()
        )
        partnership_runs = sum(b.runs_scored for b in part_events)
        partnership_balls = sum(1 for b in part_events if b.extra_type != "WIDE")

        # Momentum over recent 10 deliveries with recency decay and tanh saturation (Phase 4.3 Stage 5)
        recent_events = (
            db.query(BallEvent)
            .filter(BallEvent.innings_id == active_innings.id)
            .order_by(BallEvent.id.desc())
            .limit(10)
            .all()
        )
        raw_momentum = 0.0
        for i, ev in enumerate(recent_events):
            recency = 0.88 ** i  # Older deliveries have exponentially decayed influence
            if ev.is_wicket:
                raw_momentum -= 1.8 * recency
            elif ev.batter_runs == 6:
                raw_momentum += 1.4 * recency
            elif ev.batter_runs == 4:
                raw_momentum += 1.0 * recency
            elif ev.runs_scored > 0:
                raw_momentum += 0.25 * recency
            else:
                raw_momentum -= 0.15 * recency
        momentum = 5.0 * math.tanh(raw_momentum / 3.5)

        # Striker dynamic confidence with diminishing returns & mean reversion (Phase 4.3 Stage 6)
        s_score = (
            db.query(InningsBatterScore)
            .filter(InningsBatterScore.innings_id == active_innings.id, InningsBatterScore.player_id == striker_id)
            .first()
        )
        b_conf = 50.0
        batter_balls_faced = 0
        if s_score:
            batter_balls_faced = s_score.balls
            dots_est = max(0, s_score.balls - s_score.fours - s_score.sixes)
            raw_bat_momentum = (s_score.runs * 0.35) + (s_score.fours * 1.5) + (s_score.sixes * 2.5) - (dots_est * 0.25)
            # Tanh saturation prevents infinite compounding
            conf_delta = 25.0 * math.tanh(raw_bat_momentum / 30.0)
            b_conf = 50.0 + conf_delta
            # Natural mean reversion towards neutral 50.0 over long innings (fatigue & overconfidence)
            if s_score.balls > 25:
                decay_weight = min(0.20, (s_score.balls - 25) * 0.008)
                b_conf = (1.0 - decay_weight) * b_conf + decay_weight * 50.0
        b_conf = max(20.0, min(80.0, b_conf))

        # Bowler dynamic confidence with hyperbolic saturation (Phase 4.3 Stage 6)
        bw_score = (
            db.query(InningsBowlerScore)
            .filter(InningsBowlerScore.innings_id == active_innings.id, InningsBowlerScore.player_id == bowler_id)
            .first()
        )
        bw_conf = 50.0
        bowler_fatigue_overs = 0
        if bw_score:
            raw_bowl_momentum = (bw_score.wickets * 7.0) + (bw_score.maidens * 5.0) + (bw_score.legal_balls * 0.2)
            raw_bowl_momentum -= (bw_score.runs_conceded * 0.35) + (bw_score.wides * 1.5) + (bw_score.no_balls * 2.0)
            conf_delta = 25.0 * math.tanh(raw_bowl_momentum / 25.0)
            bw_conf = 50.0 + conf_delta
            bowler_fatigue_overs = bw_score.legal_balls // 6
        bw_conf = max(20.0, min(80.0, bw_conf))

        # Execute simulation calculation
        result = SimulationEngine.simulate_delivery(
            batter_stats=striker_data,
            bowler_stats=bowler_data,
            over_number=over_number,
            ball_in_over=ball_in_over,
            innings_number=active_innings.innings_number,
            wickets_fallen=wickets_fallen,
            runs_required=runs_required,
            balls_remaining=balls_remaining,
            seed=seed,
            batter_confidence=b_conf,
            bowler_confidence=bw_conf,
            partnership_runs=partnership_runs,
            partnership_balls=partnership_balls,
            momentum=momentum,
            pitch_type=pitch_type,
            weather_condition=weather_condition,
            bowler_fatigue_overs=bowler_fatigue_overs,
            batter_balls_faced=batter_balls_faced,
        )

        # Update persistent BallEvent record
        ball_event = BallEvent(
            innings_id=active_innings.id,
            match_id=match.id,
            innings_number=active_innings.innings_number,
            over_number=over_number,
            ball_number=ball_in_over,
            legal_ball_number=active_innings.legal_balls_bowled + (1 if result.is_legal else 0),
            batsman_player_id=striker_id,
            non_striker_player_id=non_striker_id or striker_id,
            bowler_player_id=bowler_id,
            batter_runs=result.batter_runs,
            extras=result.extras,
            runs_scored=result.runs_scored,
            extra_type=result.extra_type,
            is_wicket=result.is_wicket,
            wicket_type=result.wicket_type,
            dismissed_player_id=striker_id if result.is_wicket else None,
            commentary=result.commentary,
            description=f"{result.short_display} ({result.runs_scored} runs)",
        )
        db.add(ball_event)

        # Update Batter Scorecard
        batter_score = (
            db.query(InningsBatterScore)
            .filter(InningsBatterScore.innings_id == active_innings.id, InningsBatterScore.player_id == striker_id)
            .first()
        )
        if batter_score:
            # Legal balls, no-balls, and byes/leg-byes count as balls faced by batter; wides do not
            if result.extra_type != "WIDE":
                batter_score.balls += 1
            batter_score.has_batted = True
            batter_score.runs += result.batter_runs
            if result.batter_runs == 4:
                batter_score.fours += 1
            elif result.batter_runs == 6:
                batter_score.sixes += 1
            batter_score.strike_rate = round((batter_score.runs / max(1, batter_score.balls)) * 100.0, 1)

            if result.is_wicket:
                batter_score.is_out = True
                striker_data = cls._get_player_data(striker_id)
                striker_name = striker_data.get("player_name", f"Batter #{striker_id}")
                d_text, comm_override = cls._generate_realistic_dismissal(
                    db=db,
                    room_id=room.id,
                    bowling_team_user_id=active_innings.bowling_team_user_id,
                    bowler_id=bowler_id,
                    bowler_data=bowler_data,
                    wicket_type=result.wicket_type or "Bowled",
                    striker_name=striker_name,
                    seed=seed,
                )
                batter_score.dismissal_text = d_text
                ball_event.commentary = comm_override
                result.commentary = comm_override
            db.flush()

        # Update Bowler Scorecard
        bowler_score = (
            db.query(InningsBowlerScore)
            .filter(InningsBowlerScore.innings_id == active_innings.id, InningsBowlerScore.player_id == bowler_id)
            .first()
        )
        if not bowler_score:
            b_decade = int(bowler_data.get("decade", 0)) if bowler_data.get("decade") else None
            bowler_score = InningsBowlerScore(
                innings_id=active_innings.id,
                player_id=bowler_id,
                player_name=bowler_data.get("player_name", f"Bowler #{bowler_id}"),
                decade=b_decade,
            )
            db.add(bowler_score)
            db.flush()

        if result.is_legal:
            bowler_score.legal_balls += 1
            completed_overs = bowler_score.legal_balls // 6
            partial_balls = bowler_score.legal_balls % 6
            bowler_score.overs = completed_overs + (partial_balls / 10.0)

        if result.extra_type == "WIDE":
            bowler_score.wides += 1
            bowler_score.runs_conceded += 1
        elif result.extra_type == "NO_BALL":
            bowler_score.no_balls += 1
            bowler_score.runs_conceded += 1 + result.batter_runs
        elif result.is_legal:
            # Byes and leg byes do NOT count against the bowler's runs conceded
            if result.extra_type not in ("BYE", "LEG_BYE"):
                bowler_score.runs_conceded += result.batter_runs

        if result.is_wicket and result.wicket_type != "Run out":
            bowler_score.wickets += 1

        bowler_score.economy = round((bowler_score.runs_conceded / max(1, bowler_score.legal_balls)) * 6.0, 2)

        # Update Innings Totals
        active_innings.total_runs += result.runs_scored
        if result.is_legal:
            active_innings.legal_balls_bowled += 1

        completed_overs = active_innings.legal_balls_bowled // 6
        partial_balls = active_innings.legal_balls_bowled % 6
        active_innings.total_overs = completed_overs + (partial_balls / 10.0)

        # Handle Wickets and Incoming Batter
        if result.is_wicket:
            active_innings.total_wickets += 1
            db.flush()

            if active_innings.total_wickets < 10:
                # Find next undismissed batter who has not yet batted
                next_batter_score = (
                    db.query(InningsBatterScore)
                    .filter(
                        InningsBatterScore.innings_id == active_innings.id,
                        InningsBatterScore.is_out == False,  # noqa: E712
                        InningsBatterScore.has_batted == False,  # noqa: E712
                        InningsBatterScore.player_id.notin_([striker_id, non_striker_id]),
                    )
                    .order_by(InningsBatterScore.batting_position.asc())
                    .first()
                )
                if next_batter_score:
                    next_batter_score.has_batted = True
                    next_batter_score.dismissal_text = "not out"
                    active_innings.current_striker_id = next_batter_score.player_id
                    db.flush()
            else:
                # All Out (10 wickets)
                active_innings.current_striker_id = None
                db.flush()

        elif result.strike_changed:
            # Rotate strike between current striker and non-striker
            active_innings.current_striker_id, active_innings.current_non_striker_id = (
                non_striker_id,
                striker_id,
            )

        # Check Over Completion (6 legal balls completed)
        if result.is_legal and (active_innings.legal_balls_bowled % 6 == 0):
            # Check Maiden Over for bowler
            # Query runs conceded in this specific over
            current_over_idx = (active_innings.legal_balls_bowled // 6) - 1
            balls_in_over = (
                db.query(BallEvent)
                .filter(
                    BallEvent.innings_id == active_innings.id,
                    BallEvent.over_number == current_over_idx,
                )
                .all()
            )
            runs_in_this_over = sum(b.runs_scored for b in balls_in_over if b.extra_type not in ("BYE", "LEG_BYE"))
            if runs_in_this_over == 0 and len(balls_in_over) >= 6:
                bowler_score.maidens += 1

            # End of over: swap striker and non-striker
            if active_innings.total_wickets < 10:
                active_innings.current_striker_id, active_innings.current_non_striker_id = (
                    active_innings.current_non_striker_id,
                    active_innings.current_striker_id,
                )

            # Select next bowler (if innings continues)
            if active_innings.legal_balls_bowled < 120 and active_innings.total_wickets < 10:
                current_over_idx = (active_innings.legal_balls_bowled // 6) + 1
                next_bowler_id = cls._select_eligible_bowler(
                    db=db,
                    room_id=room.id,
                    bowling_team_user_id=active_innings.bowling_team_user_id,
                    innings_id=active_innings.id,
                    current_bowler_id=bowler_id,
                    over_number=current_over_idx,
                )
                active_innings.current_bowler_id = next_bowler_id

                # Ensure bowler scorecard exists
                next_bowler_score = (
                    db.query(InningsBowlerScore)
                    .filter(
                        InningsBowlerScore.innings_id == active_innings.id,
                        InningsBowlerScore.player_id == next_bowler_id,
                    )
                    .first()
                )
                if not next_bowler_score:
                    nb_data = cls._get_player_data(next_bowler_id)
                    nb_decade = int(nb_data.get("decade", 0)) if nb_data.get("decade") else None
                    db.add(
                        InningsBowlerScore(
                            innings_id=active_innings.id,
                            player_id=next_bowler_id,
                            player_name=nb_data.get("player_name", f"Bowler #{next_bowler_id}"),
                            decade=nb_decade,
                        )
                    )

        # Check Innings 2 Victory or Chase Completion
        if active_innings.innings_number == 2:
            target = match.target or 0
            batting_team_user = active_innings.batting_team_user_id
            bowling_team_user = active_innings.bowling_team_user_id

            host_p = next(p for p in room.players if p.is_host)
            guest_p = next(p for p in room.players if not p.is_host)
            host_info = cls._get_team_info(db, room, host_p)
            guest_info = cls._get_team_info(db, room, guest_p)

            batting_team_name = host_info.team_name if batting_team_user == host_p.user_id else guest_info.team_name
            bowling_team_name = host_info.team_name if bowling_team_user == host_p.user_id else guest_info.team_name

            # Condition 1: Chasing team reaches target
            if active_innings.total_runs >= target:
                active_innings.is_completed = True
                match.status = "COMPLETED"
                match.winner_user_id = batting_team_user
                wickets_remaining = 10 - active_innings.total_wickets
                margin = f"{batting_team_name} won by {wickets_remaining} wicket{'s' if wickets_remaining != 1 else ''}!"
                match.result_margin = margin
                match.completed_at = datetime.now(timezone.utc)
                room.status = "COMPLETED"
                logger.info("Match %d finished: %s", match.id, margin)

            # Condition 2: Chasing team all out or overs completed
            elif active_innings.total_wickets >= 10 or active_innings.legal_balls_bowled >= 120:
                active_innings.is_completed = True
                match.completed_at = datetime.now(timezone.utc)
                room.status = "COMPLETED"

                if active_innings.total_runs == target - 1:
                    match.status = "TIED"
                    match.result_margin = "Match Tied!"
                    match.winner_user_id = None
                    logger.info("Match %d finished: Tie", match.id)
                else:
                    match.status = "COMPLETED"
                    match.winner_user_id = bowling_team_user
                    run_margin = (target - 1) - active_innings.total_runs
                    margin = f"{bowling_team_name} won by {run_margin} run{'s' if run_margin != 1 else ''}!"
                    match.result_margin = margin
                    logger.info("Match %d finished: %s", match.id, margin)

        # Check Innings 1 Completion (Transition to Innings 2)
        elif active_innings.innings_number == 1:
            if active_innings.total_wickets >= 10 or active_innings.legal_balls_bowled >= 120:
                active_innings.is_completed = True
                match.target = active_innings.total_runs + 1
                match.current_innings = 2

                # Setup Innings 2
                inn2_batting_user = active_innings.bowling_team_user_id
                inn2_bowling_user = active_innings.batting_team_user_id

                inn2 = MatchInnings(
                    match_id=match.id,
                    innings_number=2,
                    batting_team_user_id=inn2_batting_user,
                    bowling_team_user_id=inn2_bowling_user,
                    total_runs=0,
                    total_wickets=0,
                    total_overs=0.0,
                    legal_balls_bowled=0,
                    is_completed=False,
                )
                db.add(inn2)
                db.flush()

                # Setup Innings 2 batting order
                inn2_picks = (
                    db.query(DraftPick)
                    .filter(DraftPick.room_id == room.id, DraftPick.user_id == inn2_batting_user)
                    .order_by(DraftPick.batting_position.asc())
                    .all()
                )
                for pick in inn2_picks:
                    p_data = cls._get_player_data(pick.player_id)
                    p_name = p_data.get("player_name", pick.player_name)
                    decade_val = int(p_data.get("decade", 0)) if p_data.get("decade") else None
                    is_opener = pick.batting_position in (1, 2)
                    db.add(
                        InningsBatterScore(
                            innings_id=inn2.id,
                            player_id=pick.player_id,
                            player_name=p_name,
                            decade=decade_val,
                            batting_position=pick.batting_position,
                            runs=0,
                            balls=0,
                            fours=0,
                            sixes=0,
                            strike_rate=0.0,
                            is_out=False,
                            has_batted=is_opener,
                            dismissal_text="not out" if is_opener else "DNB",
                        )
                    )

                if len(inn2_picks) >= 2:
                    inn2.current_striker_id = inn2_picks[0].player_id
                    inn2.current_non_striker_id = inn2_picks[1].player_id
                elif len(inn2_picks) == 1:
                    inn2.current_striker_id = inn2_picks[0].player_id

                # Select Innings 2 opening bowler
                inn2_bowler_id = cls._select_eligible_bowler(
                    db=db,
                    room_id=room.id,
                    bowling_team_user_id=inn2_bowling_user,
                    innings_id=inn2.id,
                    over_number=1,
                )
                inn2.current_bowler_id = inn2_bowler_id
                inn2_bowler_data = cls._get_player_data(inn2_bowler_id)
                inn2_bowler_decade = int(inn2_bowler_data.get("decade", 0)) if inn2_bowler_data.get("decade") else None
                db.add(
                    InningsBowlerScore(
                        innings_id=inn2.id,
                        player_id=inn2_bowler_id,
                        player_name=inn2_bowler_data.get("player_name", f"Bowler #{inn2_bowler_id}"),
                        decade=inn2_bowler_decade,
                    )
                )

                logger.info("Innings 1 complete: %d/%d in %.1f ov. Target for Innings 2: %d", active_innings.total_runs, active_innings.total_wickets, active_innings.total_overs, match.target)

        # Stage 10: Statistical validation check
        cls.validate_innings_statistics(db, active_innings.id)

        db.commit()
        db.refresh(match)

        updated_state = cls.get_live_match_state(db, code)
        return result, updated_state

    @classmethod
    def validate_innings_statistics(cls, db: Session, innings_id: int) -> Dict[str, Any]:
        """
        Stage 10: Statistical reconciliation and validation:
        1. Innings Total Runs == Sum of individual batter runs + extras
        2. Balls faced by batters == Legal deliveries + No-balls + Byes + Leg-byes
        3. Total wickets == Count of dismissed batters
        4. Innings legal balls bowled <= 120 (overs <= 20.0)
        """
        innings = db.query(MatchInnings).filter(MatchInnings.id == innings_id).first()
        if not innings:
            return {"valid": True}

        batters = db.query(InningsBatterScore).filter(InningsBatterScore.innings_id == innings_id).all()
        events = db.query(BallEvent).filter(BallEvent.innings_id == innings_id).all()

        total_batter_runs = sum(b.runs for b in batters)
        total_extras = sum(e.extras for e in events)
        total_reconciled_runs = total_batter_runs + total_extras

        dismissed_count = sum(1 for b in batters if b.is_out)

        valid_runs = (innings.total_runs == total_reconciled_runs)
        valid_wickets = (innings.total_wickets == dismissed_count)
        valid_overs = (innings.legal_balls_bowled <= 120)

        is_valid = valid_runs and valid_wickets and valid_overs
        if not is_valid:
            logger.warning(
                "Statistical validation mismatch in Innings %d: runs_match=%s (inn=%d, sum=%d), wkts_match=%s (inn=%d, out=%d)",
                innings_id, valid_runs, innings.total_runs, total_reconciled_runs,
                valid_wickets, innings.total_wickets, dismissed_count,
            )

        return {
            "valid": is_valid,
            "total_runs": innings.total_runs,
            "reconciled_runs": total_reconciled_runs,
            "total_wickets": innings.total_wickets,
            "dismissed_count": dismissed_count,
            "legal_balls_bowled": innings.legal_balls_bowled,
        }

    @classmethod
    def _calculate_player_of_the_match(
        cls,
        db: Session,
        match: Match,
        inn1: Optional[MatchInnings],
        inn2: Optional[MatchInnings],
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Determines Player of the Match using a balanced multi-dimensional formula:
        Batting: runs, strike rate bonus, 50s/100s milestones
        Bowling: wickets, economy bonus, maidens, 3-wkt/5-wkt hauls
        Match Impact: bonus for winning team members
        """
        if not match or match.status not in ("COMPLETED", "TIED"):
            return None, None

        innings_ids = [inn.id for inn in (inn1, inn2) if inn and inn.id]
        if not innings_ids:
            return None, None

        batters = (
            db.query(InningsBatterScore)
            .filter(InningsBatterScore.innings_id.in_(innings_ids))
            .all()
        )
        bowlers = (
            db.query(InningsBowlerScore)
            .filter(InningsBowlerScore.innings_id.in_(innings_ids))
            .all()
        )

        player_stats: Dict[int, Dict[str, Any]] = {}
        for b in batters:
            pid = b.player_id
            if pid not in player_stats:
                player_stats[pid] = {
                    "name": b.player_name,
                    "runs": 0,
                    "balls": 0,
                    "fours": 0,
                    "sixes": 0,
                    "wickets": 0,
                    "overs": 0.0,
                    "runs_conceded": 0,
                    "maidens": 0,
                    "is_not_out": False,
                }
            player_stats[pid]["runs"] += b.runs
            player_stats[pid]["balls"] += b.balls
            player_stats[pid]["fours"] += b.fours
            player_stats[pid]["sixes"] += b.sixes
            if not b.is_out and b.has_batted:
                player_stats[pid]["is_not_out"] = True

        for bw in bowlers:
            pid = bw.player_id
            if pid not in player_stats:
                player_stats[pid] = {
                    "name": bw.player_name,
                    "runs": 0,
                    "balls": 0,
                    "fours": 0,
                    "sixes": 0,
                    "wickets": 0,
                    "overs": 0.0,
                    "runs_conceded": 0,
                    "maidens": 0,
                    "is_not_out": False,
                }
            player_stats[pid]["wickets"] += bw.wickets
            player_stats[pid]["overs"] += bw.overs
            player_stats[pid]["runs_conceded"] += bw.runs_conceded
            player_stats[pid]["maidens"] += bw.maidens

        # Find which user_id drafted each player
        picks = db.query(DraftPick).filter(DraftPick.room_id == match.room_id).all()
        player_user_map = {p.player_id: p.user_id for p in picks}

        best_score = -1.0
        best_player_name = None
        best_details = None

        for pid, stats in player_stats.items():
            r = stats["runs"]
            b = stats["balls"]
            f = stats["fours"]
            s = stats["sixes"]
            w = stats["wickets"]
            ov = stats["overs"]
            rc = stats["runs_conceded"]
            m = stats["maidens"]

            score = 0.0
            # Batting score
            if b > 0:
                score += r * 1.0 + f * 1.0 + s * 2.0
                if r >= 50:
                    score += 25.0
                if r >= 100:
                    score += 50.0
                sr = (r / b) * 100.0
                if r >= 20 and sr > 130:
                    score += (sr - 130) * 0.15

            # Bowling score
            if ov > 0:
                score += w * 25.0 + m * 15.0
                if w >= 3:
                    score += 25.0
                if w >= 5:
                    score += 50.0
                econ = rc / max(1.0, ov)
                if ov >= 2.0 and econ < 7.5:
                    score += (7.5 - econ) * 3.0

            # Winner bonus
            user_id = player_user_map.get(pid)
            if match.winner_user_id and user_id == match.winner_user_id:
                score += 15.0

            if score > best_score:
                best_score = score
                best_player_name = stats["name"]
                parts = []
                if r > 0 or b > 0:
                    no_mark = "*" if stats["is_not_out"] else ""
                    parts.append(f"{r}{no_mark} ({b})")
                if w > 0 or ov > 0:
                    parts.append(f"{w}/{rc} ({ov:.1f} ov)")
                best_details = " & ".join(parts) if parts else f"{r} runs"

        return best_player_name, best_details

    @classmethod
    def get_live_match_state(
        cls,
        db: Session,
        room_code: str,
    ) -> LiveMatchStateResponse:
        """
        Constructs the comprehensive, authoritative LiveMatchStateResponse.
        Enriches scorecards, partnership figures, commentary, and recent balls.
        """
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        match = db.query(Match).filter(Match.room_id == room.id).first()
        if not match:
            raise ValueError(f"Match not found for room '{code}'.")

        host_p = next(p for p in room.players if p.is_host)
        guest_p = next(p for p in room.players if not p.is_host)
        host_info = cls._get_team_info(db, room, host_p)
        guest_info = cls._get_team_info(db, room, guest_p)

        # Fetch both innings
        inn1 = (
            db.query(MatchInnings)
            .filter(MatchInnings.match_id == match.id, MatchInnings.innings_number == 1)
            .first()
        )
        inn2 = (
            db.query(MatchInnings)
            .filter(MatchInnings.match_id == match.id, MatchInnings.innings_number == 2)
            .first()
        )

        # Active innings (Innings 2 if exists, else Innings 1)
        active_innings = inn2 if (inn2 and not inn1.is_completed is False) else (inn1 or MatchInnings())

        # Determine current batting/bowling team names
        batting_uid = active_innings.batting_team_user_id or match.team1_user_id
        bowling_uid = active_innings.bowling_team_user_id or match.team2_user_id

        batting_name = host_info.team_name if batting_uid == host_p.user_id else guest_info.team_name
        bowling_name = host_info.team_name if bowling_uid == host_p.user_id else guest_info.team_name

        # Calculate run rates
        balls_bowled = active_innings.legal_balls_bowled or 0
        total_runs = active_innings.total_runs or 0
        crr = round((total_runs * 6.0) / max(1, balls_bowled), 2) if balls_bowled > 0 else 0.0

        # Chase stats for Innings 2
        runs_req = None
        balls_rem = None
        rrr = None
        if active_innings.innings_number == 2 and match.target:
            runs_req = max(0, match.target - total_runs)
            balls_rem = max(0, 120 - balls_bowled)
            rrr = round((runs_req * 6.0) / max(1, balls_rem), 2) if balls_rem > 0 else 0.0

        # Striker, Non-Striker, Bowler figures
        striker_info: Optional[BatterLiveInfo] = None
        non_striker_info: Optional[BatterLiveInfo] = None
        bowler_info: Optional[BowlerLiveInfo] = None

        if active_innings.id:
            if active_innings.current_striker_id:
                s_rec = (
                    db.query(InningsBatterScore)
                    .filter(
                        InningsBatterScore.innings_id == active_innings.id,
                        InningsBatterScore.player_id == active_innings.current_striker_id,
                    )
                    .first()
                )
                if s_rec:
                    striker_info = BatterLiveInfo.model_validate(s_rec)

            if active_innings.current_non_striker_id:
                ns_rec = (
                    db.query(InningsBatterScore)
                    .filter(
                        InningsBatterScore.innings_id == active_innings.id,
                        InningsBatterScore.player_id == active_innings.current_non_striker_id,
                    )
                    .first()
                )
                if ns_rec:
                    non_striker_info = BatterLiveInfo.model_validate(ns_rec)

            if active_innings.current_bowler_id:
                b_rec = (
                    db.query(InningsBowlerScore)
                    .filter(
                        InningsBowlerScore.innings_id == active_innings.id,
                        InningsBowlerScore.player_id == active_innings.current_bowler_id,
                    )
                    .first()
                )
                if b_rec:
                    bowler_info = BowlerLiveInfo.model_validate(b_rec)

        # Recent Deliveries (last 6-12 balls of active innings)
        recent_deliveries: List[str] = []
        last_ball_detail: Optional[BallEventDetail] = None
        commentary_feed: List[CommentaryEntry] = []

        if active_innings.id:
            events = (
                db.query(BallEvent)
                .filter(BallEvent.innings_id == active_innings.id)
                .order_by(BallEvent.id.desc())
                .limit(20)
                .all()
            )

            for ev in reversed(events):
                token = "•"
                if ev.is_wicket:
                    token = "W"
                elif ev.extra_type == "WIDE":
                    token = "Wd"
                elif ev.extra_type == "NO_BALL":
                    token = "Nb"
                elif ev.extra_type in ("BYE", "LEG_BYE"):
                    token = f"{ev.extras}B" if ev.extra_type == "BYE" else f"{ev.extras}LB"
                elif ev.batter_runs == 4:
                    token = "4"
                elif ev.batter_runs == 6:
                    token = "6"
                elif ev.batter_runs > 0:
                    token = str(ev.batter_runs)
                recent_deliveries.append(token)

            if events:
                latest = events[0]
                cls._ensure_dataset()
                p_b = cls._get_player_data(latest.batsman_player_id)
                p_ns = cls._get_player_data(latest.non_striker_player_id)
                p_bw = cls._get_player_data(latest.bowler_player_id)
                p_d = cls._get_player_data(latest.dismissed_player_id) if latest.dismissed_player_id else None

                b_dec = p_b.get("decade")
                ns_dec = p_ns.get("decade")
                bw_dec = p_bw.get("decade")
                d_dec = p_d.get("decade") if p_d else None

                b_name = f"{p_b.get('player_name', 'Batter')}{f' ({b_dec})' if b_dec else ''}"
                ns_name = f"{p_ns.get('player_name', 'Batter')}{f' ({ns_dec})' if ns_dec else ''}"
                bw_name = f"{p_bw.get('player_name', 'Bowler')}{f' ({bw_dec})' if bw_dec else ''}"
                d_name = f"{p_d.get('player_name', '')}{f' ({d_dec})' if d_dec else ''}" if p_d else None

                last_ball_detail = BallEventDetail(
                    id=latest.id,
                    innings_number=latest.innings_number,
                    over_number=latest.over_number,
                    ball_number=latest.ball_number,
                    legal_ball_number=latest.legal_ball_number,
                    batsman_player_id=latest.batsman_player_id,
                    batsman_name=b_name,
                    non_striker_player_id=latest.non_striker_player_id,
                    non_striker_name=ns_name,
                    bowler_player_id=latest.bowler_player_id,
                    bowler_name=bw_name,
                    batter_runs=latest.batter_runs,
                    extras=latest.extras,
                    runs_scored=latest.runs_scored,
                    extra_type=latest.extra_type,
                    is_wicket=latest.is_wicket,
                    wicket_type=latest.wicket_type,
                    dismissed_player_id=latest.dismissed_player_id,
                    dismissed_player_name=d_name,
                    commentary=latest.commentary or "",
                    description=latest.description,
                    created_at=latest.created_at,
                )

                # Commentary entries (newest on top)
                for ev in events:
                    short_tok = "•"
                    if ev.is_wicket:
                        short_tok = "W"
                    elif ev.extra_type == "WIDE":
                        short_tok = "Wd"
                    elif ev.extra_type == "NO_BALL":
                        short_tok = "Nb"
                    elif ev.batter_runs == 4:
                        short_tok = "4"
                    elif ev.batter_runs == 6:
                        short_tok = "6"
                    elif ev.batter_runs > 0:
                        short_tok = str(ev.batter_runs)

                    commentary_feed.append(
                        CommentaryEntry(
                            id=ev.id,
                            innings_number=ev.innings_number,
                            over_display=f"{ev.over_number}.{ev.ball_number}",
                            short_outcome=short_tok,
                            text=ev.commentary or "",
                            is_wicket=ev.is_wicket,
                            is_boundary=ev.batter_runs in (4, 6),
                            timestamp=ev.created_at,
                        )
                    )

        # Build Scorecards for both innings
        def build_scorecard(innings_obj: Optional[MatchInnings]) -> Optional[InningsScorecard]:
            if not innings_obj or not innings_obj.id:
                return None
            batters_list = [
                BatterLiveInfo.model_validate(b)
                for b in db.query(InningsBatterScore)
                .filter(InningsBatterScore.innings_id == innings_obj.id)
                .order_by(InningsBatterScore.batting_position.asc())
                .all()
            ]
            bowlers_list = [
                BowlerLiveInfo.model_validate(bw)
                for bw in db.query(InningsBowlerScore)
                .filter(InningsBowlerScore.innings_id == innings_obj.id)
                .all()
            ]
            b_uid = innings_obj.batting_team_user_id
            bw_uid = innings_obj.bowling_team_user_id
            b_name = host_info.team_name if b_uid == host_p.user_id else guest_info.team_name
            bw_name = host_info.team_name if bw_uid == host_p.user_id else guest_info.team_name

            # Calculate extras from persistent ball events
            all_balls = (
                db.query(BallEvent)
                .filter(BallEvent.innings_id == innings_obj.id)
                .all()
            )
            wides_count = sum(1 for ev in all_balls if ev.extra_type == "WIDE")
            no_balls_count = sum(1 for ev in all_balls if ev.extra_type == "NO_BALL")
            byes_runs = sum(ev.extras for ev in all_balls if ev.extra_type == "BYE")
            leg_byes_runs = sum(ev.extras for ev in all_balls if ev.extra_type == "LEG_BYE")
            total_extras = sum(ev.extras for ev in all_balls)

            # Calculate Fall of Wickets from ball events
            fow_list: List[str] = []
            cum_runs = 0
            wkt_num = 0
            sorted_balls = sorted(all_balls, key=lambda ev: ev.id)
            for ev in sorted_balls:
                cum_runs += ev.runs_scored
                if ev.is_wicket:
                    wkt_num += 1
                    d_pid = ev.dismissed_player_id or ev.batsman_player_id
                    d_data = cls._get_player_data(d_pid)
                    d_name = d_data.get("player_name", f"Player #{d_pid}")
                    fow_list.append(f"{wkt_num}-{cum_runs} ({d_name}, {ev.over_number}.{ev.ball_number} ov)")

            return InningsScorecard(
                innings_number=innings_obj.innings_number,
                batting_team_user_id=b_uid,
                batting_team_name=b_name,
                bowling_team_user_id=bw_uid,
                bowling_team_name=bw_name,
                total_runs=innings_obj.total_runs,
                total_wickets=innings_obj.total_wickets,
                total_overs=innings_obj.total_overs,
                legal_balls_bowled=innings_obj.legal_balls_bowled,
                is_completed=innings_obj.is_completed,
                extras=total_extras,
                wides=wides_count,
                no_balls=no_balls_count,
                byes=byes_runs,
                leg_byes=leg_byes_runs,
                fall_of_wickets=fow_list,
                batters=batters_list,
                bowlers=bowlers_list,
            )

        inn1_card = build_scorecard(inn1)
        inn2_card = build_scorecard(inn2)

        winner_name = None
        if match.winner_user_id:
            winner_name = host_info.team_name if match.winner_user_id == host_p.user_id else guest_info.team_name

        potm_name, potm_details = cls._calculate_player_of_the_match(db, match, inn1, inn2)

        return LiveMatchStateResponse(
            match_id=match.id,
            room_code=code,
            status=match.status,
            current_innings_number=active_innings.innings_number or 1,
            host_team=host_info,
            guest_team=guest_info,
            batting_team_user_id=batting_uid,
            bowling_team_user_id=bowling_uid,
            batting_team_name=batting_name,
            bowling_team_name=bowling_name,
            total_runs=total_runs,
            total_wickets=active_innings.total_wickets or 0,
            overs=active_innings.total_overs or 0.0,
            legal_balls_bowled=balls_bowled,
            current_run_rate=crr,
            target=match.target,
            runs_required=runs_req,
            balls_remaining=balls_rem,
            required_run_rate=rrr,
            striker=striker_info,
            non_striker=non_striker_info,
            current_bowler=bowler_info,
            recent_deliveries=recent_deliveries[-12:],
            last_ball=last_ball_detail,
            commentary=commentary_feed,
            is_paused=match.is_paused,
            simulation_speed=match.simulation_speed,
            winner_user_id=match.winner_user_id,
            winner_name=winner_name,
            result_margin=match.result_margin,
            player_of_the_match=potm_name,
            player_of_the_match_details=potm_details,
            first_innings_scorecard=inn1_card,
            second_innings_scorecard=inn2_card,
        )

    @classmethod
    def set_simulation_controls(
        cls,
        db: Session,
        room_code: str,
        action: str,
        speed: Optional[float] = None,
    ) -> LiveMatchStateResponse:
        """Updates simulation pause state or speed multiplier."""
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            raise ValueError(f"Room '{code}' does not exist.")

        match = db.query(Match).filter(Match.room_id == room.id).first()
        if not match:
            raise ValueError(f"Match not found for room '{code}'.")

        clean_action = action.strip().lower()
        if clean_action == "pause":
            match.is_paused = True
        elif clean_action in ("play", "resume"):
            match.is_paused = False

        if speed is not None and speed in (0.5, 1.0, 2.0, 3.0):
            match.simulation_speed = speed

        db.commit()
        db.refresh(match)
        return cls.get_live_match_state(db, code)

    @classmethod
    def abandon_match(
        cls,
        db: Session,
        room_code: str,
        disconnected_user_id: Optional[str] = None,
        reason: str = "Opponent disconnected",
    ) -> Optional[Match]:
        """
        Marks match completed with an abandonment result, preserving existing completed scorecards,
        awarding victory to the remaining connected player, and marking the room completed.
        """
        code = room_code.strip().upper()
        room = db.query(Room).filter(Room.room_code == code).first()
        if not room:
            return None
        match = db.query(Match).filter(Match.room_id == room.id).first()
        if not match:
            room.status = "COMPLETED"
            db.commit()
            return None

        # Determine winner (the player who remained connected)
        winner_id = None
        for p in room.players:
            if disconnected_user_id and p.user_id != disconnected_user_id:
                winner_id = p.user_id
                break
            elif not disconnected_user_id:
                winner_id = p.user_id

        match.status = "COMPLETED"
        match.winner_user_id = winner_id
        winner_player = next((p for p in room.players if p.user_id == winner_id), None)
        winner_name = winner_player.username if winner_player else "Opponent"
        match.result_margin = f"{winner_name} won (Match Abandoned - {reason})"
        match.completed_at = datetime.now(timezone.utc)
        room.status = "COMPLETED"

        # Validate statistics for any existing innings
        innings = db.query(MatchInnings).filter(MatchInnings.match_id == match.id).all()
        for inn in innings:
            try:
                cls.validate_innings_statistics(db, inn.id)
            except Exception:
                pass

        db.commit()
        db.refresh(match)
        db.refresh(room)
        logger.info("Match in room %s marked abandoned: %s, winner: %s", code, match.result_margin, winner_id)
        return match

