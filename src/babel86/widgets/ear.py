"""Rack ears: the 34 px side flanges with a divider line and two screw heads."""

from __future__ import annotations

import math

from babel86 import theme
from babel86.widgets.common import Painter

# Screw slot angles in degrees: (top, bottom) for the left ear then the right ear.
SLOT_ANGLES = {
    "in": ((35, -20), (80, 10)),
    "out": ((25, -40), (70, 5)),
}
_STYLE = {
    # kind -> (screw sprite, slot colour, vertical padding)
    "in": ("screw_in", theme.SCREW_SLOT_INPUT, 14),
    "out": ("screw_out", theme.SCREW_SLOT_OUTPUT, 12),
}


def draw_ears(
    p: Painter, x: float, y: float, width: float, height: float, kind: str, divider: str
) -> None:
    """Draw both ears of a unit whose top-left is (x, y). `kind` is "in", "out" or "blank"."""
    ear = theme.EAR_WIDTH
    right = x + width - ear
    p.rect(x + ear - 1, y + 1, x + ear, y + height - 1, divider)
    p.rect(right, y + 1, right + 1, y + height - 1, divider)
    if kind not in _STYLE:
        return
    sprite, slot_colour, pad = _STYLE[kind]
    for ear_x, angles in ((x, SLOT_ANGLES[kind][0]), (right + 1, SLOT_ANGLES[kind][1])):
        cx = ear_x + (ear - 1) / 2
        for cy, angle in zip((y + 1 + pad + 7, y + height - 1 - pad - 7), angles, strict=True):
            p.image(sprite, cx, cy)
            theta = math.radians(angle)
            dx, dy = math.cos(theta) * 3.5, math.sin(theta) * 3.5
            p.line(cx - dx, cy - dy, cx + dx, cy + dy, slot_colour, 2)
