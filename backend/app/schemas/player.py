"""
Pydantic Schemas for Player Data in CricXI.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PlayerBase(BaseModel):
    """Base schema for Player attributes."""
    player_id: int
    player_name: str
    country: str
    decade: int
    batting_hand: str
    bowling_hand: str = "None"
    bowling_type: str = "None"
    primary_role: str
    eligible_positions: str
    is_captain: bool = False
    is_wicketkeeper: bool = False

    # Batting statistics
    matches: int = 0
    innings: int = 0
    not_outs: int = 0
    runs: int = 0
    balls_faced: int = 0
    highest_score: str = "0"
    fifties: int = 0
    hundreds: int = 0
    strike_rate: float = 0.0
    batting_average: float = 0.0
    fours: int = 0
    sixes: int = 0
    dot_balls: int = 0
    dot_ball_percentage: float = 0.0

    # Bowling statistics
    wickets: int = 0
    balls_bowled: int = 0
    runs_conceded: int = 0
    maidens: int = 0
    economy: float = 0.0
    bowling_average: float = 0.0
    bowling_strike_rate: float = 0.0
    four_wickets: int = 0
    five_wickets: int = 0
    dot_balls_bowled: int = 0
    dot_ball_percentage_bowled: float = 0.0

    # Ratings
    batting_rating: float = 0.0
    bowling_rating: float = 0.0
    fielding_rating: float = 0.0
    overall_rating: float = 0.0


class PlayerResponse(PlayerBase):
    """Detailed Player schema for API responses."""
    model_config = ConfigDict(from_attributes=True)


class PlayerFilterParams(BaseModel):
    """Query parameters schema for filtering players."""
    country: Optional[str] = Field(default=None, description="Country filter (e.g. India, Australia)")
    decade: Optional[int] = Field(default=None, description="Decade filter (1980, 1990, 2000, 2010, 2020)")
    role: Optional[str] = Field(default=None, description="Primary role filter (BAT, WK, AR, PACE, SPIN)")
    search: Optional[str] = Field(default=None, description="Search by player name substring")

