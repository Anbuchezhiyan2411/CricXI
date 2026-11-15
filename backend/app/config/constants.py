"""
CricXI Application Constants.
Defines domain constants, game rules, roles, and status enums.
"""

from enum import Enum
from typing import Final, List, Set

# Supported Decades in CricXI
SUPPORTED_DECADES: Final[List[int]] = [1980, 1990, 2000, 2010, 2020]

# Supported Countries in CricXI
SUPPORTED_COUNTRIES: Final[List[str]] = [
    "Afghanistan",
    "Australia",
    "Bangladesh",
    "England",
    "India",
    "New Zealand",
    "Pakistan",
    "South Africa",
    "Sri Lanka",
    "West Indies",
    "Zimbabwe",
]

# Primary Player Roles
class PlayerRole(str, Enum):
    BAT = "BAT"
    WK = "WK"
    AR = "AR"
    PACE = "PACE"
    SPIN = "SPIN"

# Batting Hand
class BattingHand(str, Enum):
    RIGHT = "Right"
    LEFT = "Left"

# Bowling Hand
class BowlingHand(str, Enum):
    RIGHT = "Right"
    LEFT = "Left"
    NONE = "None"

# Bowling Types
class BowlingType(str, Enum):
    NONE = "None"
    RIGHT_ARM_FAST = "Right Arm Fast"
    LEFT_ARM_FAST = "Left Arm Fast"
    RIGHT_ARM_FAST_MEDIUM = "Right Arm Fast Medium"
    LEFT_ARM_FAST_MEDIUM = "Left Arm Fast Medium"
    RIGHT_ARM_MEDIUM = "Right Arm Medium"
    LEFT_ARM_MEDIUM = "Left Arm Medium"
    OFF_SPIN = "Off Spin"
    LEG_SPIN = "Leg Spin"
    LEFT_ARM_ORTHODOX = "Left Arm Orthodox"
    LEFT_ARM_CHINAMAN = "Left Arm Chinaman"

# Room Status
class RoomStatus(str, Enum):
    WAITING = "WAITING"
    DRAFTING = "DRAFTING"
    TOSS = "TOSS"
    LIVE = "LIVE"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"

# Match Status
class MatchStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    FIRST_INNINGS = "FIRST_INNINGS"
    INNINGS_BREAK = "INNINGS_BREAK"
    SECOND_INNINGS = "SECOND_INNINGS"
    COMPLETED = "COMPLETED"
    TIED = "TIED"

# Toss Choice
class TossDecision(str, Enum):
    BAT = "BAT"
    BOWL = "BOWL"

# Draft Constants
TOTAL_DRAFT_ROUNDS: Final[int] = 11
SQUAD_SIZE: Final[int] = 11
MAX_ROOM_PLAYERS: Final[int] = 2

