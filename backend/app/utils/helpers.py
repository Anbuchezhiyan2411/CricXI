"""
General Utility and Helper Functions for CricXI.
"""

import random
import string
from typing import Optional


def generate_room_code(length: int = 6) -> str:
    """Generates an alphanumeric room code (uppercase, avoiding ambiguous characters like 0/O, 1/I)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choices(alphabet, k=length))


def format_rate(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Calculates a rate safely avoiding division by zero."""
    if denominator <= 0:
        return default
    return round(numerator / denominator, 2)

