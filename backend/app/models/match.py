"""
SQLAlchemy Match, MatchInnings, BallEvent, InningsBatterScore, and InningsBowlerScore Models.
Authoritative persistent data storage for CricXI Live T20 Matches.
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database.base import Base


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    team1_user_id = Column(String(100), nullable=False)
    team2_user_id = Column(String(100), nullable=False)
    toss_winner_id = Column(String(100), nullable=True)
    toss_decision = Column(String(10), nullable=True)  # "BAT" or "BOWL"
    status = Column(String(20), default="PENDING", nullable=False)  # "PENDING", "LIVE", "COMPLETED", "TIED"
    winner_user_id = Column(String(100), nullable=True)
    result_margin = Column(String(100), nullable=True)
    current_innings = Column(Integer, default=1, nullable=False)
    target = Column(Integer, nullable=True)
    is_paused = Column(Boolean, default=False, nullable=False)
    simulation_speed = Column(Float, default=1.0, nullable=False)  # Multiplier: 0.5 (slow), 1.0 (normal), 2.0 (fast)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    room = relationship("Room", back_populates="matches")
    innings = relationship("MatchInnings", back_populates="match", cascade="all, delete-orphan", order_by="MatchInnings.innings_number")


class MatchInnings(Base):
    __tablename__ = "match_innings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    innings_number = Column(Integer, nullable=False)  # 1 or 2
    batting_team_user_id = Column(String(100), nullable=False)
    bowling_team_user_id = Column(String(100), nullable=False)
    total_runs = Column(Integer, default=0, nullable=False)
    total_wickets = Column(Integer, default=0, nullable=False)
    total_overs = Column(Float, default=0.0, nullable=False)  # e.g., 3.4
    legal_balls_bowled = Column(Integer, default=0, nullable=False)  # 0 to 120
    is_completed = Column(Boolean, default=False, nullable=False)

    # State tracking during simulation
    current_striker_id = Column(Integer, nullable=True)
    current_non_striker_id = Column(Integer, nullable=True)
    current_bowler_id = Column(Integer, nullable=True)

    # Relationships
    match = relationship("Match", back_populates="innings")
    ball_events = relationship("BallEvent", back_populates="innings", cascade="all, delete-orphan", order_by="BallEvent.id")
    batters = relationship("InningsBatterScore", back_populates="innings", cascade="all, delete-orphan", order_by="InningsBatterScore.batting_position")
    bowlers = relationship("InningsBowlerScore", back_populates="innings", cascade="all, delete-orphan")


class BallEvent(Base):
    __tablename__ = "ball_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    innings_id = Column(Integer, ForeignKey("match_innings.id", ondelete="CASCADE"), nullable=False, index=True)
    match_id = Column(Integer, nullable=True, index=True)
    innings_number = Column(Integer, default=1, nullable=False)
    over_number = Column(Integer, nullable=False)  # 0 to 19
    ball_number = Column(Integer, nullable=False)  # 1 to 6+ in over
    legal_ball_number = Column(Integer, default=0, nullable=False)  # 1 to 120
    batsman_player_id = Column(Integer, nullable=False, index=True)  # striker_id
    non_striker_player_id = Column(Integer, nullable=False)
    bowler_player_id = Column(Integer, nullable=False, index=True)
    batter_runs = Column(Integer, default=0, nullable=False)
    extras = Column(Integer, default=0, nullable=False)
    runs_scored = Column(Integer, default=0, nullable=False)  # total runs on this ball (batter_runs + extras)
    extra_type = Column(String(20), nullable=True)  # "WIDE", "NO_BALL", "BYE", "LEG_BYE", "NONE"
    is_wicket = Column(Boolean, default=False, nullable=False)
    wicket_type = Column(String(50), nullable=True)  # "Bowled", "Caught", "LBW", "Run out", "Stumped", "Hit wicket"
    dismissed_player_id = Column(Integer, nullable=True)
    commentary = Column(String(300), nullable=True)
    description = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    innings = relationship("MatchInnings", back_populates="ball_events")


class InningsBatterScore(Base):
    __tablename__ = "innings_batter_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    innings_id = Column(Integer, ForeignKey("match_innings.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(Integer, nullable=False, index=True)
    player_name = Column(String(100), nullable=False)
    batting_position = Column(Integer, nullable=False)  # 1 to 11
    runs = Column(Integer, default=0, nullable=False)
    balls = Column(Integer, default=0, nullable=False)
    fours = Column(Integer, default=0, nullable=False)
    sixes = Column(Integer, default=0, nullable=False)
    strike_rate = Column(Float, default=0.0, nullable=False)
    is_out = Column(Boolean, default=False, nullable=False)
    has_batted = Column(Boolean, default=False, nullable=False)
    decade = Column(Integer, nullable=True)
    dismissal_text = Column(String(150), default="DNB", nullable=False)  # "not out", "b Starc", "c Dhoni b Ashwin", "DNB"

    @property
    def batting_status(self) -> str:
        if self.is_out:
            return "OUT"
        if self.has_batted:
            return "NOT_OUT"
        return "DNB"

    innings = relationship("MatchInnings", back_populates="batters")


class InningsBowlerScore(Base):
    __tablename__ = "innings_bowler_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    innings_id = Column(Integer, ForeignKey("match_innings.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(Integer, nullable=False, index=True)
    player_name = Column(String(100), nullable=False)
    decade = Column(Integer, nullable=True)
    overs = Column(Float, default=0.0, nullable=False)  # e.g., 3.4
    legal_balls = Column(Integer, default=0, nullable=False)  # e.g., 22
    maidens = Column(Integer, default=0, nullable=False)
    runs_conceded = Column(Integer, default=0, nullable=False)
    wickets = Column(Integer, default=0, nullable=False)
    economy = Column(Float, default=0.0, nullable=False)
    wides = Column(Integer, default=0, nullable=False)
    no_balls = Column(Integer, default=0, nullable=False)

    innings = relationship("MatchInnings", back_populates="bowlers")
