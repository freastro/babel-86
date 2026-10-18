"""Rack geometry as a function of window size. Pure functions, no Tk.

All values are logical pixels. The four columns follow the flex rules in the design:
identity 300 and control 440 are fixed, level grows 1 from a 400 base, text grows 1.3
from a 480 base, and both shrink in proportion to their base when space is short.
"""

from __future__ import annotations

from dataclasses import dataclass

from babel86 import theme

SPRITE_SCALES = (1.0, 1.25, 1.5, 2.0, 3.0)


@dataclass(frozen=True)
class Columns:
    """Column x offsets and widths, relative to a unit's left edge."""

    identity: tuple[float, float]
    control: tuple[float, float]
    level: tuple[float, float]
    text: tuple[float, float]
    unit_width: float


@dataclass(frozen=True)
class RackBox:
    """Where the rack sits inside the window."""

    x: float
    y: float
    width: float
    height: float


def unit_content_width(unit_width: float) -> float:
    ears = 2 * theme.EAR_WIDTH + theme.STRIPE_WIDTH
    return unit_width - ears - 2 * theme.UNIT_PADDING_X


def rack_width(window_width: float) -> float:
    return min(window_width - 2 * theme.WINDOW_PADDING, theme.RACK_MAX_WIDTH)


def columns(unit_width: float) -> Columns:
    gaps = 3 * theme.COLUMN_GAP
    free = unit_content_width(unit_width) - gaps - theme.COL_IDENTITY - theme.COL_CONTROL
    (b3, m3), (b4, m4) = theme.COL_LEVEL, theme.COL_TEXT
    extra = free - (b3 + b4)
    if extra >= 0:
        w3 = b3 + extra * theme.GROW_LEVEL / (theme.GROW_LEVEL + theme.GROW_TEXT)
        w4 = b4 + extra * theme.GROW_TEXT / (theme.GROW_LEVEL + theme.GROW_TEXT)
    else:  # shrink in proportion to base size, never below the minimums
        w3 = max(m3, b3 + extra * b3 / (b3 + b4))
        w4 = max(m4, b4 + extra * b4 / (b3 + b4))
    x0 = theme.EAR_WIDTH + theme.STRIPE_WIDTH + theme.UNIT_PADDING_X
    x1 = x0 + theme.COL_IDENTITY + theme.COLUMN_GAP
    x2 = x1 + theme.COL_CONTROL + theme.COLUMN_GAP
    x3 = x2 + w3 + theme.COLUMN_GAP
    return Columns(
        identity=(x0, theme.COL_IDENTITY),
        control=(x1, theme.COL_CONTROL),
        level=(x2, w3),
        text=(x3, w4),
        unit_width=unit_width,
    )


def rack_height(language_units: int) -> float:
    """Height of the rack frame: input unit, language units, then the 1U blank panel."""
    units = 1 + language_units
    children = units + 1
    return (
        2 * theme.RACK_PADDING_Y
        + units * theme.UNIT_HEIGHT
        + theme.BLANK_HEIGHT
        + (children - 1) * theme.UNIT_GAP
    )


def content_height(language_units: int) -> float:
    """Height of the whole window content, including the window padding."""
    return rack_height(language_units) + 2 * theme.WINDOW_PADDING


def rack_box(window_width: float, language_units: int) -> RackBox:
    width = rack_width(window_width)
    x = (window_width - width) / 2
    return RackBox(x, theme.WINDOW_PADDING, width, rack_height(language_units))


def unit_tops(language_units: int) -> list[float]:
    """Top y of the input unit, each language unit and the blank panel, in rack coordinates."""
    ys: list[float] = []
    y = theme.RACK_PADDING_Y
    for height in [theme.UNIT_HEIGHT] * (1 + language_units) + [theme.BLANK_HEIGHT]:
        ys.append(y)
        y += height + theme.UNIT_GAP
    return ys


def choose_scale(
    dpi_scale: float, screen_w: float, screen_h: float, language_units: int = 4
) -> float:
    """UI scale: the display's, reduced so the whole rack fits on screen without scrolling."""
    chrome = 90  # title bar and taskbar allowance
    fit_w = screen_w / theme.MIN_WIDTH
    fit_h = (screen_h - chrome) / content_height(language_units)
    scale = max(0.5, min(dpi_scale, fit_w, fit_h))
    return snap_to_sprites(scale)


def snap_to_sprites(scale: float) -> float:
    """Use a pre-rendered sprite scale when one is at most 15% below the scale.

    Only ever rounds down, so a scale chosen to fit the screen still fits.
    """
    below = [s for s in SPRITE_SCALES if s <= scale + 1e-6]
    if below and scale / max(below) < 1.15:
        return max(below)
    return scale


def sprite_scale(scale: float) -> float:
    """The sprite set to load for a UI scale: the nearest rendered scale."""
    return min(SPRITE_SCALES, key=lambda s: abs(s - scale))


def initial_window_width(scale: float, screen_w: float) -> float:
    """Logical width to open at: 1920, but never wider than the screen."""
    return max(theme.MIN_WIDTH, min(theme.DEFAULT_WIDTH, screen_w / scale))
