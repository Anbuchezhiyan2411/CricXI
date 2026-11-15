"""
Pydantic Schemas for Multiplayer Room Operations in CricXI (Phase 2).
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlayerInRoom(BaseModel):
    """Schema representing a player inside a multiplayer room."""
    user_id: str
    username: str
    is_host: bool = False
    is_ready: bool = False
    is_connected: bool = False
    joined_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RoomCreate(BaseModel):
    """Request payload to create a new multiplayer room."""
    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="Host user's display name (3-20 characters)",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 3:
            raise ValueError("Player name must be at least 3 characters.")
        if len(trimmed) > 20:
            raise ValueError("Player name cannot exceed 20 characters.")
        return trimmed


class RoomJoin(BaseModel):
    """Request payload to join an existing multiplayer room."""
    room_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-character room code",
    )
    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="Joining user's display name (3-20 characters)",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional persistent client user_id for reconnects",
    )

    @field_validator("room_code")
    @classmethod
    def validate_room_code(cls, v: str) -> str:
        code = v.strip().upper()
        if len(code) != 6:
            raise ValueError("Room code must be exactly 6 alphanumeric characters.")
        return code

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        trimmed = v.strip()
        if len(trimmed) < 3:
            raise ValueError("Player name must be at least 3 characters.")
        if len(trimmed) > 20:
            raise ValueError("Player name cannot exceed 20 characters.")
        return trimmed


class RoomLeave(BaseModel):
    """Request payload to leave a multiplayer room."""
    room_code: str = Field(..., min_length=6, max_length=6)
    user_id: str = Field(..., min_length=1)


class RoomStart(BaseModel):
    """Request payload for the host to start the game."""
    room_code: str = Field(..., min_length=6, max_length=6)
    user_id: str = Field(..., min_length=1)


class RoomPlayAgain(BaseModel):
    """Request payload to initiate a rematch / play another match."""
    user_id: str = Field(..., min_length=1)


class PlayAgainResponse(BaseModel):
    """Response payload when starting a rematch / playing another match."""
    old_room_code: str
    new_room_code: str
    room: "RoomResponse"
    draft_state: Optional[dict] = None
    is_barrier_met: bool = True
    ready_user_ids: List[str] = Field(default_factory=list)


class RoomValidateResponse(BaseModel):
    """Response payload for pre-join room validation."""
    valid: bool
    exists: bool
    is_full: bool
    player_count: int
    status: str
    message: str


class RoomResponse(BaseModel):
    """Multiplayer room details schema."""
    room_code: str
    host_id: str
    status: str
    current_round: int
    players: List[PlayerInRoom] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_full: bool = False
    current_user_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
