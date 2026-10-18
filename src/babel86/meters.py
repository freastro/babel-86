"""Level-meter and knob maths. Pure functions, no Tk."""

from __future__ import annotations

from babel86 import theme

GAIN_MIN_DB = -24.0
GAIN_MAX_DB = 24.0
KNOB_SWEEP_DEG = 135.0  # +/- from the top at the ends of the range

# dBFS thresholds of the 18 LED segments, quietest first.
SEGMENT_DB = (-48, -42, -36, -30, -24, -20, -16, -12, -10, -8, -6, -5, -4, -3, -2, -1, -0.5, 0)
LABELLED_DB = (-48, -24, -12, -6, -3, 0)


def clamp_db(db: float) -> float:
    return max(GAIN_MIN_DB, min(GAIN_MAX_DB, db))


def snap_db(db: float) -> float:
    """Clamp and round to the 0.1 dB the knob can express."""
    return round(clamp_db(db), 1) + 0.0


def knob_angle(db: float) -> float:
    """Pointer rotation in degrees clockwise from the top: -135 at -24 dB, +135 at +24 dB."""
    return round(clamp_db(db) / GAIN_MAX_DB * KNOB_SWEEP_DEG)


def format_db(db: float) -> str:
    sign = "+" if db > 0 else "\u2212" if db < 0 else ""
    return f"{sign}{abs(db):.1f} dB"


def lit_segments(db: float | None) -> list[bool]:
    """Which of the 18 segments are lit for a peak level; None means an empty meter."""
    if db is None:
        return [False] * len(SEGMENT_DB)
    return [db >= t for t in SEGMENT_DB]


def segment_colour(threshold_db: float) -> str:
    """Green below -6, amber from -6 to -2, red from -1."""
    if threshold_db >= -1:
        return theme.ALERT
    if threshold_db >= -6:
        return theme.WARN_METER
    return theme.OK


def scale_labels() -> list[str]:
    return [str(t) if t in LABELLED_DB else "" for t in SEGMENT_DB]


def drag_to_db(start_db: float, dy_logical_px: float, db_per_px: float = 0.25) -> float:
    """Knob value after dragging dy pixels; dragging up (positive dy) raises the level."""
    return snap_db(start_db + dy_logical_px * db_per_px)


def step_db(db: float, notches: int, fine: bool = False) -> float:
    """Knob value after arrow keys or wheel notches: 1 dB steps, or 0.1 dB when fine."""
    return snap_db(db + notches * (0.1 if fine else 1.0))
