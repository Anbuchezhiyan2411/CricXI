"""
SQLAlchemy Room and RoomPlayer Models.
"""

from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.database.base import Base


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_code = Column(String(8), unique=True, index=True, nullable=False)
    host_id = Column(String(100), nullable=False)
    status = Column(String(20), default="WAITING", nullable=False)
    current_round = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    players = relationship("RoomPlayer", back_populates="room", cascade="all, delete-orphan")
    draft_picks = relationship("DraftPick", back_populates="room", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="room", cascade="all, delete-orphan")
    draft_state = relationship("DraftState", back_populates="room", uselist=False, cascade="all, delete-orphan")
    toss_state = relationship("TossState", back_populates="room", uselist=False, cascade="all, delete-orphan")


class RoomPlayer(Base):
    __tablename__ = "room_players"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    username = Column(String(50), nullable=False)
    is_host = Column(Boolean, default=False, nullable=False)
    is_ready = Column(Boolean, default=False, nullable=False)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    room = relationship("Room", back_populates="players")

