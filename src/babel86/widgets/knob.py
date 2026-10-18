"""Rotary level knob: body and cap sprites, a drawn pointer, scale labels and a caption."""

from __future__ import annotations

import math

from babel86 import theme
from babel86.meters import knob_angle
from babel86.widgets.common import Painter

BLOCK_W, BLOCK_H = theme.KNOB_BLOCK
CAPTION_GAP = 4
CAPTION_H = 12
BLOCK_TOTAL_H = BLOCK_H + CAPTION_GAP + CAPTION_H  # scale labels and knob, then the caption
KNOB_LEFT, KNOB_TOP = 19, 13
POINTER_INNER, POINTER_OUTER = 6.0, 18.0


def knob_rect(x: float, y: float) -> tuple[float, float, float, float]:
    """Hit area for a knob whose block's top-left is (x, y): the whole 84 x 72 block."""
    return (x, y, x + BLOCK_W, y + BLOCK_H)


def draw_knob(
    p: Painter,
    x: float,
    y: float,
    db: float,
    *,
    output: bool,
    cap: str,
    caption: str,
    scale_colour: str,
    caption_colour: str,
    focused: bool = False,
) -> None:
    """Draw a knob block with its top-left at logical (x, y)."""
    p.text(x + BLOCK_W / 2, y + 6, "0", "mono", 10, scale_colour, anchor="center")
    p.text(x, y + BLOCK_H - 6, "\N{MINUS SIGN}24", "mono", 10, scale_colour)
    p.text(x + BLOCK_W, y + BLOCK_H - 6, "+24", "mono", 10, scale_colour, anchor="e")

    kx, ky = x + KNOB_LEFT, y + KNOB_TOP
    d = theme.KNOB_DIAMETER
    p.image("knob_out" if output else "knob_in", kx, ky, anchor="nw")
    p.image(f"cap_{cap}", kx + d / 2, ky + d / 2)

    # Pointer: 3 px wide, from 6 to 18 px out from the centre, rotated about the centre.
    cx, cy = kx + d / 2, ky + d / 2
    theta = math.radians(knob_angle(db))
    ux, uy = math.sin(theta), -math.cos(theta)
    r0, r1 = POINTER_INNER + 1.5, POINTER_OUTER - 1.5  # round caps add 1.5 px each end
    p.line(cx + ux * r0, cy + uy * r0, cx + ux * r1, cy + uy * r1, theme.KNOB_POINTER_EDGE, 5)
    p.line(cx + ux * r0, cy + uy * r0, cx + ux * r1, cy + uy * r1, theme.KNOB_POINTER, 3)

    if focused:
        p.oval_outline(cx, cy, d / 2 + 4, theme.GOLD, 2)

    p.text(
        x + BLOCK_W / 2,
        y + BLOCK_H + CAPTION_GAP + CAPTION_H / 2,
        caption,
        "caption",
        10,
        caption_colour,
        bold=True,
        anchor="center",
        spacing=0.14,
    )
