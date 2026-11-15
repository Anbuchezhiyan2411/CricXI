"""
Pydantic Schemas for CricXI Live T20 Match Simulation.
Defines rich data transfer objects for live delivery events,
scoreboards, player figures, commentary, and full match scorecards.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class BatterLiveInfo(BaseModel):
    """Real-time figures for an active batter at the crease."""
    player_id: int
    player_name: str = Field(alias="player_name", default="")
    batting_position: int
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    strike_rate: float = 0.0
    is_out: bool = False
    has_batted: bool = False
    decade: Optional[int] = None
    dismissal_text: str = "DNB"
    batting_status: str = "DNB"  # "OUT", "NOT_OUT", "DNB"

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BowlerLiveInfo(BaseModel):
    """Real-time figures for the active bowler."""
    player_id: int
    player_name: str = ""
    decade: Optional[int] = None
    overs: float = 0.0  # e.g., 3.2
    legal_balls: int = 0
    maidens: int = 0
    runs_conceded: int = 0
    wickets: int = 0
    economy: float = 0.0
    wides: int = 0
    no_balls: int = 0

    model_config = ConfigDict(from_attributes=True)


class BallEventDetail(BaseModel):
    """Details of a single simulated ball delivery."""
    id: Optional[int] = None
    innings_number: int
    over_number: int
    ball_number: int
    legal_ball_number: int
    batsman_player_id: int
    batsman_name: str = ""
    non_striker_player_id: int
    non_striker_name: str = ""
    bowler_player_id: int
    bowler_name: str = ""
    batter_runs: int = 0
    extras: int = 0
    runs_scored: int = 0
    extra_type: Optional[str] = None
    is_wicket: bool = False
    wicket_type: Optional[str] = None
    dismissed_player_id: Optional[int] = None
    dismissed_player_name: Optional[str] = None
    commentary: str = ""
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CommentaryEntry(BaseModel):
    """Item in live match commentary timeline."""
    id: Optional[int] = None
    innings_number: int
    over_display: str  # e.g., "14.3"
    short_outcome: str  # e.g., "4", "W", "1", "•", "Wd"
    text: str
    is_wicket: bool = False
    is_boundary: bool = False
    timestamp: Optional[datetime] = None


class InningsScorecard(BaseModel):
    """Complete batting and bowling records for one innings."""
    innings_number: int
    batting_team_user_id: str
    batting_team_name: str
    bowling_team_user_id: str
    bowling_team_name: str
    total_runs: int
    total_wickets: int
    total_overs: float
    legal_balls_bowled: int
    is_completed: bool
    extras: int = 0
    wides: int = 0
    no_balls: int = 0
    byes: int = 0
    leg_byes: int = 0
    fall_of_wickets: List[str] = Field(default_factory=list)
    batters: List[BatterLiveInfo] = Field(default_factory=list)
    bowlers: List[BowlerLiveInfo] = Field(default_factory=list)


class TeamMatchInfo(BaseModel):
    """Metadata for a team participating in the match."""
    user_id: str
    username: str
    is_host: bool
    captain_name: str
    team_name: str


class LiveMatchStateResponse(BaseModel):
    """Authoritative snapshot of the live match state."""
    match_id: int
    room_code: str
    status: str  # "PENDING", "LIVE", "INNINGS_BREAK", "COMPLETED", "TIED"
    current_innings_number: int  # 1 or 2
    host_team: TeamMatchInfo
    guest_team: TeamMatchInfo
    batting_team_user_id: str
    bowling_team_user_id: str
    batting_team_name: str
    bowling_team_name: str

    total_runs: int = 0
    total_wickets: int = 0
    overs: float = 0.0  # e.g., 5.4
    legal_balls_bowled: int = 0
    current_run_rate: float = 0.0

    target: Optional[int] = None
    runs_required: Optional[int] = None
    balls_remaining: Optional[int] = None
    required_run_rate: Optional[float] = None

    striker: Optional[BatterLiveInfo] = None
    non_striker: Optional[BatterLiveInfo] = None
    current_bowler: Optional[BowlerLiveInfo] = None

    recent_deliveries: List[str] = Field(default_factory=list)  # Last 6-12 balls
    last_ball: Optional[BallEventDetail] = None
    commentary: List[CommentaryEntry] = Field(default_factory=list)

    is_paused: bool = False
    simulation_speed: float = 1.0

    winner_user_id: Optional[str] = None
    winner_name: Optional[str] = None
    result_margin: Optional[str] = None
    player_of_the_match: Optional[str] = None
    player_of_the_match_details: Optional[str] = None

    first_innings_scorecard: Optional[InningsScorecard] = None
    second_innings_scorecard: Optional[InningsScorecard] = None

    model_config = ConfigDict(from_attributes=True)


class SimulationControlRequest(BaseModel):
    """Request payload to control simulation playback."""
    action: str  # "play", "pause", "resume", "step", "set_speed"
    speed: Optional[float] = None  # 0.5 (slow), 1.0 (normal), 2.0 (fast)


class MatchResponse(BaseModel):
    """Original basic schema maintained for backwards compatibility."""
    id: int
    room_id: int
    team1_user_id: str
    team2_user_id: str
    toss_winner_id: Optional[str] = None
    toss_decision: Optional[str] = None
    status: str
    winner_user_id: Optional[str] = None
    result_margin: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
