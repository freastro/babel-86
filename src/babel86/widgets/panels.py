"""Glowing display windows: the language code, the source readout and the text panels."""

from __future__ import annotations

from babel86 import theme
from babel86.textfit import newest_lines
from babel86.widgets.common import Painter

PANEL_MIN_HEIGHT = 70
PANEL_PADDING_X = 14
PANEL_PADDING_Y = 8
LINE_HEIGHT = 1.35


def draw_well(
    p: Painter, x: float, y: float, w: float, h: float, border: str, radius: float = 4
) -> None:
    """A black inset window with a 2 px border."""
    p.box(x, y, x + w, y + h, theme.DISPLAY_BG, radius, border, 2)


def code_box_width(p: Painter, code: str) -> float:
    """Width of the 38 px language-code window: text plus 10 px padding and 2 px border."""
    return p.text_width(code, "mono", 38) + 20 + 4


def draw_text_panel(
    p: Painter,
    x: float,
    y: float,
    w: float,
    text: str,
    *,
    colour: str,
    size: float,
    border: str,
    glow: bool = True,
) -> None:
    """Two-line text window that keeps the newest text and trims from the start."""
    draw_well(p, x, y, w, PANEL_MIN_HEIGHT, border)
    if not text:
        return
    font = p.font("mono", size)
    inner = w - 2 * (PANEL_PADDING_X + 2)
    lines = newest_lines(text, lambda s: font.measure(s) / p.scale, inner)
    line_h = size * LINE_HEIGHT
    top = y + PANEL_MIN_HEIGHT / 2 - line_h * len(lines) / 2
    for i, line in enumerate(lines):
        p.text(
            x + 2 + PANEL_PADDING_X,
            top + line_h * (i + 0.5),
            line,
            "mono",
            size,
            colour,
            glow=theme.DISPLAY_BG if glow else None,
        )
