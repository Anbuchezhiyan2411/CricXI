"""
Pydantic Schemas for CricXI Match History & Archives.
Defines rich DTOs for historical match listings, innings summaries, and full scorecards.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.match import LiveMatchStateResponse


class InningsSummaryInfo(BaseModel):
    """Compact summary of an innings in a completed match."""
    innings_number: int
    team_name: str
    team_user_id: str
    total_runs: int = 0
    total_wickets: int = 0
    total_overs: float = 0.0
    run_rate: float = 0.0
    display_score: str = ""  # e.g., "178/5 (20.0 ov)"

    model_config = ConfigDict(from_attributes=True)


class MatchHistoryItemResponse(BaseModel):
    """Detailed record for historical match list cards."""
    id: int
    room_id: int
    room_code: str
    match_date: Optional[datetime] = None
    status: str
    team1_user_id: str
    team2_user_id: str
    team1_name: str
    team2_name: str
    toss_winner_name: Optional[str] = None
    toss_decision: Optional[str] = None
    winner_user_id: Optional[str] = None
    winner_name: Optional[str] = None
    result_margin: Optional[str] = None
    innings1: Optional[InningsSummaryInfo] = None
    innings2: Optional[InningsSummaryInfo] = None
    player_of_the_match: Optional[str] = None
    player_of_the_match_details: Optional[str] = None
    has_full_scorecard: bool = True

    model_config = ConfigDict(from_attributes=True)


class MatchHistoryDetailResponse(BaseModel):
    """Full detail response including scorecard and telemetry."""
    match_id: int
    room_code: str
    match_info: MatchHistoryItemResponse
    scorecard: Optional[LiveMatchStateResponse] = None

    model_config = ConfigDict(from_attributes=True)
