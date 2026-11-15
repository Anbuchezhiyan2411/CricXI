"""
SQLAlchemy Draft Models: DraftPick and DraftState.
Tracks player selection, locked batting positions, and live draft session state.
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database.base import Base


class DraftPick(Base):
    __tablename__ = "draft_picks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    round_number = Column(Integer, nullable=False)
    user_id = Column(String(100), nullable=False, index=True)
    player_id = Column(Integer, nullable=False)
    player_name = Column(String(100), nullable=False)
    batting_position = Column(Integer, nullable=False)
    selected_country = Column(String(50), nullable=False)
    selected_decade = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    room = relationship("Room", back_populates="draft_picks")


class DraftState(Base):
    __tablename__ = "draft_states"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    current_round = Column(Integer, default=1, nullable=False)
    current_turn = Column(Integer, default=1, nullable=False)  # 1 = first picker in round, 2 = second picker
    current_picker_id = Column(String(100), nullable=False)
    round_country = Column(String(50), nullable=True)
    round_decade = Column(Integer, nullable=True)
    country_history = Column(Text, default="[]", nullable=False)  # JSON encoded list of [country, decade]
    turn_deadline = Column(DateTime, nullable=True)
    remaining_seconds = Column(Integer, default=30, nullable=False)
    is_finished = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    room = relationship("Room", back_populates="draft_state")
