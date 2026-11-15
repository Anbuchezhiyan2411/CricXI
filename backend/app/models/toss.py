"""
SQLAlchemy Toss Model for CricXI.
Tracks the live multiplayer toss state: caller selection, Heads/Tails call,
random coin flip, winner determination, and Bat/Bowl decision.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database.base import Base


class TossState(Base):
    __tablename__ = "toss_states"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True)

    caller_id = Column(String(100), nullable=False)
    caller_name = Column(String(50), nullable=False)
    caller_choice = Column(String(10), nullable=True)  # "HEADS" or "TAILS"
    coin_result = Column(String(10), nullable=True)    # "HEADS" or "TAILS"
    winner_id = Column(String(100), nullable=True)
    winner_name = Column(String(50), nullable=True)
    decision = Column(String(10), nullable=True)       # "BAT" or "BOWL"
    step = Column(String(20), default="CALLING", nullable=False)  # "CALLING", "FLIPPING", "DECIDING", "COMPLETED"

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    room = relationship("Room", back_populates="toss_state")

