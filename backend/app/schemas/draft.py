"""
Pydantic Schemas for Draft Engine in CricXI (Phase 3).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.player import PlayerResponse


class DraftPickCreate(BaseModel):
    """Payload to select a player for a specific batting position."""
    player_id: int = Field(..., description="ID of candidate player from round pool")
    batting_position: int = Field(..., ge=1, le=11, description="Chosen batting position (1-11)")
    user_id: str = Field(..., description="Identifier of the picking user")


class DraftPickResponse(BaseModel):
    """Schema for an individual locked draft pick."""
    id: Optional[int] = None
    round_number: int
    user_id: str
    player_id: int
    player_name: str
    batting_position: int
    selected_country: str
    selected_decade: int
    primary_role: Optional[str] = None
    is_captain: bool = False
    is_wicketkeeper: bool = False
    overall_rating: float = 0.0
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SquadSlot(BaseModel):
    """A slot in the user's Best XI (1 to 11)."""
    slot_number: int
    is_locked: bool = False
    pick: Optional[DraftPickResponse] = None


class UserSquad(BaseModel):
    """The 11-man lineup for a user."""
    user_id: str
    username: str
    is_host: bool
    slots: List[SquadSlot] = Field(default_factory=list)
    picked_count: int = 0
    total_rating: float = 0.0


class DraftStateResponse(BaseModel):
    """Complete live draft state payload for client synchronization."""
    room_code: str
    current_round: int
    total_rounds: int = 11
    current_turn: int  # 1 or 2
    current_picker_id: str
    current_picker_name: str
    round_country: Optional[str] = None
    round_decade: Optional[int] = None
    remaining_seconds: int = 30
    is_finished: bool = False
    country_history: List[List[Any]] = Field(default_factory=list)
    available_pool: List[PlayerResponse] = Field(default_factory=list)
    candidates: List[PlayerResponse] = Field(default_factory=list)
    drafted_player_ids: List[int] = Field(default_factory=list)
    host_squad: UserSquad
    guest_squad: UserSquad
    user_squads: Dict[str, UserSquad] = Field(default_factory=dict)
    all_picks: List[DraftPickResponse] = Field(default_factory=list)
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

