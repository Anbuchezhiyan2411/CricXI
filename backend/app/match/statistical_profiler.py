"""
CricXI Statistical Profiler and Feature Engineering Engine (Phase 4.2).
Provides:
1. Z-score normalization and percentile transformation (Normal CDF).
2. Multi-feature weighted player strength evaluation.
3. Fully automated, data-driven batting and bowling style classification.
4. Pitch condition, weather, and dynamic fielding placement models.
"""

import math
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BattingStyle(str, Enum):
    AGGRESSIVE_OPENER = "Aggressive Opener"
    ANCHOR = "Anchor"
    STROKE_MAKER = "Stroke Maker"
    FINISHER = "Finisher"
    ACCUMULATOR = "Accumulator"
    POWER_HITTER = "Power Hitter"
    LOWER_ORDER = "Lower Order"
    TAILENDER = "Tailender"


class BowlingStyle(str, Enum):
    SWING_BOWLER = "Swing Bowler"
    FAST_STRIKE_BOWLER = "Fast Strike Bowler"
    DEFENSIVE_SEAMER = "Defensive Seamer"
    FINGER_SPINNER = "Finger Spinner"
    LEG_SPINNER = "Leg Spinner"
    MYSTERY_SPINNER = "Mystery Spinner"
    PART_TIMER = "Part Timer"


class PitchCondition(str, Enum):
    GREEN = "Green Pitch"
    FLAT = "Flat Batting Pitch"
    TURNING = "Dry Turning Pitch"
    BALANCED = "Balanced Pitch"


class WeatherCondition(str, Enum):
    SUNNY = "Sunny"
    CLOUDY = "Cloudy"
    HUMID = "Humid"
    OVERCAST = "Overcast"


class FieldSetting(str, Enum):
    ATTACKING = "Attacking"
    BALANCED = "Balanced"
    BOUNDARY_PROTECTION = "Boundary Protection"


class StatisticalProfiler:
    """
    Computes dataset-wide moments (mean, std), Z-scores, normal cumulative percentiles,
    player strength scores, and statistical classifications.
    """

    _instance: Optional["StatisticalProfiler"] = None

    def __init__(self, players: Optional[List[Dict[str, Any]]] = None) -> None:
        self.stats_cache: Dict[str, Tuple[float, float]] = {}
        if players:
            self.fit(players)
        else:
            self._set_default_population_stats()

    @classmethod
    def get_instance(cls) -> "StatisticalProfiler":
        if cls._instance is None:
            cls._instance = StatisticalProfiler()
        return cls._instance

    def _set_default_population_stats(self) -> None:
        """Sets robust empirical population baselines from T20 cricket analytics."""
        self.stats_cache = {
            "batting_rating": (55.0, 27.0),
            "batting_average": (20.0, 11.5),
            "strike_rate": (115.0, 26.0),
            "boundary_frequency": (0.13, 0.05),
            "consistency": (18.0, 8.0),
            "bowling_rating": (45.0, 30.0),
            "economy": (8.10, 1.80),
            "bowling_strike_rate": (20.0, 7.5),
            "wicket_frequency": (0.05, 0.02),
        }

    def fit(self, players: List[Dict[str, Any]]) -> None:
        """
        Calculates exact population mean and standard deviation from dataset records.
        """
        if not players:
            self._set_default_population_stats()
            return

        def _calc_moments(values: List[float], fallback_mean: float, fallback_std: float) -> Tuple[float, float]:
            if not values:
                return (fallback_mean, fallback_std)
            n = len(values)
            mean = sum(values) / n
            variance = sum((x - mean) ** 2 for x in values) / max(1, n - 1)
            std = math.sqrt(variance)
            return (mean, std if std > 0.001 else fallback_std)

        # 1. Batting population metrics
        b_ratings = [float(p.get("batting_rating", 0) or 0) for p in players if float(p.get("batting_rating", 0) or 0) > 0]
        b_averages = [float(p.get("batting_average", 0) or 0) for p in players if float(p.get("batting_average", 0) or 0) > 0]
        b_srs = [float(p.get("strike_rate", 0) or 0) for p in players if float(p.get("strike_rate", 0) or 0) > 0]
        b_bounds = []
        for p in players:
            bf = float(p.get("balls_faced", 0) or 0)
            if bf >= 20:
                fours = float(p.get("fours", 0) or 0)
                sixes = float(p.get("sixes", 0) or 0)
                b_bounds.append((fours + sixes) / bf)

        # 2. Bowling population metrics
        bw_ratings = [float(p.get("bowling_rating", 0) or 0) for p in players if float(p.get("bowling_rating", 0) or 0) > 0]
        bw_econs = [float(p.get("economy", 0) or 0) for p in players if float(p.get("balls_bowled", 0) or 0) >= 30 and float(p.get("economy", 0) or 0) > 0]
        bw_srs = [float(p.get("bowling_strike_rate", 0) or 0) for p in players if float(p.get("balls_bowled", 0) or 0) >= 30 and float(p.get("bowling_strike_rate", 0) or 0) > 0]
        bw_wkt_freq = []
        for p in players:
            bb = float(p.get("balls_bowled", 0) or 0)
            if bb >= 30:
                wkts = float(p.get("wickets", 0) or 0)
                bw_wkt_freq.append(wkts / bb)

        self.stats_cache["batting_rating"] = _calc_moments(b_ratings, 55.0, 27.0)
        self.stats_cache["batting_average"] = _calc_moments(b_averages, 20.0, 11.5)
        self.stats_cache["strike_rate"] = _calc_moments(b_srs, 115.0, 26.0)
        self.stats_cache["boundary_frequency"] = _calc_moments(b_bounds, 0.13, 0.05)
        self.stats_cache["consistency"] = _calc_moments(b_averages, 18.0, 8.0)

        self.stats_cache["bowling_rating"] = _calc_moments(bw_ratings, 45.0, 30.0)
        self.stats_cache["economy"] = _calc_moments(bw_econs, 8.10, 1.80)
        self.stats_cache["bowling_strike_rate"] = _calc_moments(bw_srs, 20.0, 7.5)
        self.stats_cache["wicket_frequency"] = _calc_moments(bw_wkt_freq, 0.05, 0.02)

        logger.info("Statistical profiler fitted with %d player records.", len(players))

    def compute_z_score(self, feature_name: str, value: float) -> float:
        """Computes z = (x - mean) / std."""
        mean, std = self.stats_cache.get(feature_name, (50.0, 15.0))
        if std <= 0.0001:
            return 0.0
        return (value - mean) / std

    @staticmethod
    def z_to_percentile(z: float) -> float:
        """
        Converts a Z-score to a continuous percentile [0.001, 0.999] using
        the standard normal cumulative distribution function (CDF):
        Phi(z) = 0.5 * (1 + erf(z / sqrt(2)))
        """
        # Clamp Z to prevent extreme numerical overflow
        clamped_z = max(-4.0, min(4.0, z))
        return 0.5 * (1.0 + math.erf(clamped_z / math.sqrt(2.0)))

    def calculate_batting_strength(self, batter_stats: Dict[str, Any]) -> float:
        """
        Stage 1: Multi-feature weighted batting strength in [0.05, 0.95].
        Weights: Batting Rating 40%, Average 25%, Strike Rate 20%, Consistency 15%.
        """
        rating = float(batter_stats.get("batting_rating") or batter_stats.get("overall_rating") or 50.0)
        balls_faced = float(batter_stats.get("balls_faced", 0) or 0)
        avg = float(batter_stats.get("batting_average", 0) or 0)
        sr = float(batter_stats.get("strike_rate", 0) or 0)

        # For tailenders who rarely bat, penalize missing stats cleanly
        if balls_faced < 10 and rating < 45.0:
            avg = max(4.0, rating * 0.15)
            sr = max(60.0, rating * 1.5)

        z_rating = self.compute_z_score("batting_rating", rating)
        z_avg = self.compute_z_score("batting_average", avg)
        z_sr = self.compute_z_score("strike_rate", sr)

        fours = float(batter_stats.get("fours", 0) or 0)
        sixes = float(batter_stats.get("sixes", 0) or 0)
        bound_freq = (fours + sixes) / max(1.0, balls_faced) if balls_faced >= 15 else (sr / 1000.0)
        z_consistency = self.compute_z_score("boundary_frequency", bound_freq)

        p_rating = self.z_to_percentile(z_rating)
        p_avg = self.z_to_percentile(z_avg)
        p_sr = self.z_to_percentile(z_sr)
        p_cons = self.z_to_percentile(z_consistency)

        strength = (0.40 * p_rating) + (0.25 * p_avg) + (0.20 * p_sr) + (0.15 * p_cons)
        return max(0.05, min(0.95, strength))

    def calculate_bowling_strength(self, bowler_stats: Dict[str, Any]) -> float:
        """
        Stage 1: Multi-feature weighted bowling strength in [0.05, 0.95].
        Weights: Bowling Rating 35%, Economy 25%, Strike Rate 20%, Average 10%, Wicket Freq 10%.
        Economy and strike rates are inverted so lower is superior.
        """
        rating = float(bowler_stats.get("bowling_rating") or bowler_stats.get("overall_rating") or 40.0)
        balls_bowled = float(bowler_stats.get("balls_bowled", 0) or 0)
        econ = float(bowler_stats.get("economy", 0) or 0)
        bsr = float(bowler_stats.get("bowling_strike_rate", 0) or 0)
        b_avg = float(bowler_stats.get("bowling_average", 0) or 0)

        if balls_bowled < 12 and rating < 45.0:
            # Pure batter bowling part-time
            econ = 9.80
            bsr = 30.0
            b_avg = 40.0

        if econ <= 0.0:
            econ = 8.10
        if bsr <= 0.0:
            bsr = 20.0
        if b_avg <= 0.0:
            b_avg = 28.0

        z_rating = self.compute_z_score("bowling_rating", rating)
        # Invert economy and strike rate (lower is better for bowlers)
        z_econ = -self.compute_z_score("economy", econ)
        z_bsr = -self.compute_z_score("bowling_strike_rate", bsr)
        z_bavg = -self.compute_z_score("batting_average", b_avg)

        wkts = float(bowler_stats.get("wickets", 0) or 0)
        wkt_freq = wkts / max(1.0, balls_bowled) if balls_bowled >= 15 else (1.0 / max(1.0, bsr))
        z_wfreq = self.compute_z_score("wicket_frequency", wkt_freq)

        p_rating = self.z_to_percentile(z_rating)
        p_econ = self.z_to_percentile(z_econ)
        p_bsr = self.z_to_percentile(z_bsr)
        p_bavg = self.z_to_percentile(z_bavg)
        p_wfreq = self.z_to_percentile(z_wfreq)

        strength = (0.35 * p_rating) + (0.25 * p_econ) + (0.20 * p_bsr) + (0.10 * p_bavg) + (0.10 * p_wfreq)
        return max(0.05, min(0.95, strength))


def classify_batting_style(batter_stats: Dict[str, Any], batting_strength: float) -> BattingStyle:
    """
    Stage 2 & 2.1: Automatic data-driven batting style profiling without manual labels.
    Inferred purely from dataset statistics.
    """
    rating = float(batter_stats.get("batting_rating") or 50.0)
    role = str(batter_stats.get("primary_role", "")).upper()
    sr = float(batter_stats.get("strike_rate", 0) or 0)
    avg = float(batter_stats.get("batting_average", 0) or 0)
    pos_str = str(batter_stats.get("eligible_positions", ""))
    fours = float(batter_stats.get("fours", 0) or 0)
    sixes = float(batter_stats.get("sixes", 0) or 0)
    balls = float(batter_stats.get("balls_faced", 0) or 0)
    six_ratio = sixes / max(1.0, fours)
    boundary_freq = (fours + sixes) / max(1.0, balls)

    # 1. Tailenders (positions 9-11 or weak bowling specialists)
    if rating < 35.0 or (role == "BOWL" and rating < 48.0 and batting_strength < 0.28):
        return BattingStyle.TAILENDER

    # 2. Lower Order (positions 7-8 or all-rounders with limited batting stats)
    if rating < 56.0 or (role in ("BOWL", "AR") and rating < 62.0 and batting_strength < 0.45):
        return BattingStyle.LOWER_ORDER

    # 3. Aggressive Openers (fast starters in top order)
    is_top_order = any(p in pos_str for p in ["1", "2"]) or int(batter_stats.get("batting_position") or 5) <= 2
    if is_top_order and (sr >= 135.0 or (boundary_freq >= 0.16 and sr >= 128.0)):
        return BattingStyle.AGGRESSIVE_OPENER

    # 4. Power Hitters (boundary clearers)
    if (six_ratio >= 0.45 and sr >= 135.0) or sr >= 148.0 or (boundary_freq >= 0.19 and sr >= 132.0):
        return BattingStyle.POWER_HITTER

    # 5. Finishers (lower middle order accelerator)
    is_finisher_pos = any(p in pos_str for p in ["5", "6", "7"]) or int(batter_stats.get("batting_position") or 4) in (5, 6, 7)
    if is_finisher_pos and (sr >= 130.0 or (avg >= 26.0 and sr >= 125.0)):
        return BattingStyle.FINISHER

    # 6. Anchors (high average, values wicket, lower strike rate)
    if avg >= 34.0 and sr < 128.0:
        return BattingStyle.ANCHOR

    # 7. Accumulators (strike rotators, steady boundaries)
    if avg >= 26.0 and sr < 132.0:
        return BattingStyle.ACCUMULATOR

    # 8. Stroke Maker (proficient top/middle order batter)
    return BattingStyle.STROKE_MAKER


def get_batting_style_modifiers(style: BattingStyle) -> Dict[str, float]:
    """
    Returns calibrated outcome multiplier modifiers corresponding to the batting style (Phase 4.3).
    Ensures strike rates and boundary distributions strictly reflect authentic T20 roles.
    """
    if style == BattingStyle.AGGRESSIVE_OPENER:
        return {"DOT": 1.02, "SINGLE": 0.88, "DOUBLE": 0.92, "FOUR": 1.18, "SIX": 1.16, "WICKET": 1.12}
    elif style == BattingStyle.ANCHOR:
        return {"DOT": 0.88, "SINGLE": 1.18, "DOUBLE": 1.12, "FOUR": 0.96, "SIX": 0.72, "WICKET": 0.75}
    elif style == BattingStyle.STROKE_MAKER:
        return {"DOT": 0.94, "SINGLE": 1.04, "DOUBLE": 1.04, "FOUR": 1.08, "SIX": 1.06, "WICKET": 0.96}
    elif style == BattingStyle.FINISHER:
        return {"DOT": 0.90, "SINGLE": 1.05, "DOUBLE": 1.05, "FOUR": 1.15, "SIX": 1.25, "WICKET": 1.10}
    elif style == BattingStyle.ACCUMULATOR:
        return {"DOT": 0.86, "SINGLE": 1.20, "DOUBLE": 1.14, "FOUR": 0.94, "SIX": 0.76, "WICKET": 0.80}
    elif style == BattingStyle.POWER_HITTER:
        return {"DOT": 1.08, "SINGLE": 0.84, "DOUBLE": 0.88, "FOUR": 1.14, "SIX": 1.30, "WICKET": 1.22}
    elif style == BattingStyle.LOWER_ORDER:
        return {"DOT": 1.18, "SINGLE": 0.92, "DOUBLE": 0.90, "FOUR": 0.90, "SIX": 0.90, "WICKET": 1.30}
    else:  # TAILENDER
        return {"DOT": 1.45, "SINGLE": 0.75, "DOUBLE": 0.60, "FOUR": 0.55, "SIX": 0.35, "WICKET": 1.65}


def classify_bowling_style(bowler_stats: Dict[str, Any], bowling_strength: float) -> BowlingStyle:
    """
    Stage 3: Automatic data-driven bowling style classification.
    """
    b_type = str(bowler_stats.get("bowling_type", "")).lower()
    role = str(bowler_stats.get("primary_role", "")).upper()
    rating = float(bowler_stats.get("bowling_rating", 0) or 0)
    econ = float(bowler_stats.get("economy", 0) or 0)
    bsr = float(bowler_stats.get("bowling_strike_rate", 0) or 0)

    # 1. Part Timer
    if (rating < 50.0 and role in ("BAT", "WK")) or bowling_strength < 0.25:
        return BowlingStyle.PART_TIMER

    # 2. Spin varieties
    if "spin" in b_type or "orthodox" in b_type:
        if "mystery" in b_type or (rating >= 85.0 and econ > 0 and econ < 6.8):
            return BowlingStyle.MYSTERY_SPINNER
        if "leg" in b_type or "wrist" in b_type:
            return BowlingStyle.LEG_SPINNER
        return BowlingStyle.FINGER_SPINNER

    # 3. Pace varieties
    if bsr > 0 and bsr <= 18.5 and rating >= 75.0:
        return BowlingStyle.FAST_STRIKE_BOWLER

    if econ > 0 and econ <= 7.4:
        return BowlingStyle.DEFENSIVE_SEAMER

    if "medium" in b_type or "swing" in b_type or rating >= 70.0:
        return BowlingStyle.SWING_BOWLER

    return BowlingStyle.DEFENSIVE_SEAMER


def get_bowling_style_modifiers(style: BowlingStyle) -> Dict[str, float]:
    """
    Returns calibrated outcome multiplier modifiers corresponding to the bowling style (Phase 4.3).
    Ensures economy rates, wicket rates, and discipline reflect realistic T20 bowling spells.
    """
    if style == BowlingStyle.SWING_BOWLER:
        return {"DOT": 1.10, "WICKET": 1.14, "FOUR": 0.94, "SIX": 0.94, "EXTRAS": 1.08}
    elif style == BowlingStyle.FAST_STRIKE_BOWLER:
        return {"DOT": 1.08, "WICKET": 1.20, "FOUR": 0.96, "SIX": 1.02, "EXTRAS": 1.10}
    elif style == BowlingStyle.DEFENSIVE_SEAMER:
        return {"DOT": 1.14, "WICKET": 0.90, "FOUR": 0.88, "SIX": 0.90, "EXTRAS": 0.85}
    elif style == BowlingStyle.FINGER_SPINNER:
        return {"DOT": 1.12, "WICKET": 0.94, "FOUR": 0.92, "SIX": 0.96, "EXTRAS": 0.75}
    elif style == BowlingStyle.LEG_SPINNER:
        return {"DOT": 1.06, "WICKET": 1.18, "FOUR": 1.02, "SIX": 1.06, "EXTRAS": 1.15}
    elif style == BowlingStyle.MYSTERY_SPINNER:
        return {"DOT": 1.22, "WICKET": 1.16, "FOUR": 0.84, "SIX": 0.86, "EXTRAS": 0.90}
    else:  # PART_TIMER
        return {"DOT": 0.85, "WICKET": 0.75, "FOUR": 1.22, "SIX": 1.25, "EXTRAS": 1.20}


def get_pitch_for_match(match_id: int) -> PitchCondition:
    """Stage 7.1: Deterministically generates a pitch condition for the match."""
    pitches = [PitchCondition.GREEN, PitchCondition.FLAT, PitchCondition.TURNING, PitchCondition.BALANCED]
    idx = (abs(int(match_id)) * 104729) % len(pitches)
    return pitches[idx]


def get_weather_for_match(match_id: int) -> WeatherCondition:
    """Stage 7.2: Deterministically generates weather condition for the match."""
    weathers = [WeatherCondition.SUNNY, WeatherCondition.CLOUDY, WeatherCondition.HUMID, WeatherCondition.OVERCAST]
    idx = (abs(int(match_id)) * 7919) % len(weathers)
    return weathers[idx]


def get_field_setting(over_number: int) -> FieldSetting:
    """Stage 7.4: Determines fielding placement corresponding to match phase."""
    if over_number < 6:
        return FieldSetting.ATTACKING
    elif over_number < 15:
        return FieldSetting.BALANCED
    else:
        return FieldSetting.BOUNDARY_PROTECTION

