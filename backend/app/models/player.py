"""
SQLAlchemy Player Model.
Represents player records from master_players.csv.
"""

from sqlalchemy import Boolean, Column, Float, Integer, String
from app.database.base import Base


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    player_id = Column(Integer, index=True, nullable=False)
    player_name = Column(String(100), index=True, nullable=False)
    country = Column(String(50), index=True, nullable=False)
    decade = Column(Integer, index=True, nullable=False)

    # Playing attributes
    batting_hand = Column(String(20), nullable=False)
    bowling_hand = Column(String(20), nullable=False, default="None")
    bowling_type = Column(String(50), nullable=False, default="None")
    primary_role = Column(String(20), index=True, nullable=False)
    eligible_positions = Column(String(50), nullable=False)
    is_captain = Column(Boolean, default=False, nullable=False)
    is_wicketkeeper = Column(Boolean, default=False, nullable=False)

    # Batting statistics
    matches = Column(Integer, default=0, nullable=False)
    innings = Column(Integer, default=0, nullable=False)
    not_outs = Column(Integer, default=0, nullable=False)
    runs = Column(Integer, default=0, nullable=False)
    balls_faced = Column(Integer, default=0, nullable=False)
    highest_score = Column(String(20), default="0", nullable=False)
    fifties = Column(Integer, default=0, nullable=False)
    hundreds = Column(Integer, default=0, nullable=False)
    strike_rate = Column(Float, default=0.0, nullable=False)
    batting_average = Column(Float, default=0.0, nullable=False)
    fours = Column(Integer, default=0, nullable=False)
    sixes = Column(Integer, default=0, nullable=False)
    dot_balls = Column(Integer, default=0, nullable=False)
    dot_ball_percentage = Column(Float, default=0.0, nullable=False)

    # Bowling statistics
    wickets = Column(Integer, default=0, nullable=False)
    balls_bowled = Column(Integer, default=0, nullable=False)
    runs_conceded = Column(Integer, default=0, nullable=False)
    maidens = Column(Integer, default=0, nullable=False)
    economy = Column(Float, default=0.0, nullable=False)
    bowling_average = Column(Float, default=0.0, nullable=False)
    bowling_strike_rate = Column(Float, default=0.0, nullable=False)
    best_bowling = Column(String(20), default="0/0", nullable=False)

    # Fielding statistics
    catches = Column(Integer, default=0, nullable=False)
    stumpings = Column(Integer, default=0, nullable=False)
    run_outs = Column(Integer, default=0, nullable=False)

    # Normalized ratings (0 - 100)
    batting_rating = Column(Float, default=0.0, nullable=False)
    bowling_rating = Column(Float, default=0.0, nullable=False)
    fielding_rating = Column(Float, default=0.0, nullable=False)
    overall_rating = Column(Float, default=0.0, nullable=False)

