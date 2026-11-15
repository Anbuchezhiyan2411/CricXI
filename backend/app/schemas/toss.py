"""
Pydantic Schemas for the Multiplayer Cricket Toss System (CricXI).
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class TossCallRequest(BaseModel):
    """Payload when caller selects Heads or Tails."""
    user_id: str = Field(..., description="ID of the player calling the toss")
    choice: Literal["HEADS", "TAILS"] = Field(..., description="Coin call: HEADS or TAILS")


class TossDecisionRequest(BaseModel):
    """Payload when toss winner chooses to Bat or Bowl first."""
    user_id: str = Field(..., description="ID of the toss winner making the decision")
    decision: Literal["BAT", "BOWL"] = Field(..., description="Decision: BAT or BOWL")


class TeamInfo(BaseModel):
    """Details about a team and its captain for the toss ceremony."""
    user_id: str
    username: str
    is_host: bool
    captain_name: str
    team_name: str
    player_count: int = 11


class TossStateResponse(BaseModel):
    """Live synchronization state of the toss session."""
    room_code: str
    match_id: Optional[int] = None
    step: str = "CALLING"  # "CALLING", "FLIPPING", "DECIDING", "COMPLETED"
    caller_id: str
    caller_name: str
    caller_choice: Optional[str] = None
    coin_result: Optional[str] = None
    winner_id: Optional[str] = None
    winner_name: Optional[str] = None
    decision: Optional[str] = None
    host_team: TeamInfo
    guest_team: TeamInfo
    is_current_user_caller: bool = False
    is_current_user_winner: bool = False
    draft_completed: bool = True
    message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

