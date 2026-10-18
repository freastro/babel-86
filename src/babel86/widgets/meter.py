"""18-segment LED level meter with a dB scale underneath."""

from __future__ import annotations

from babel86 import theme
from babel86.meters import SEGMENT_DB, lit_segments, scale_labels, segment_colour
from babel86.widgets.common import Painter, blend

LABEL_H = 13
SEGMENT_GAP = 2
LABEL_GAP = 6

# kind -> (segment height, padding y, padding x, border, radius, background, border colour)
_KINDS = {
    "in": (18, 10, 12, 2, 4, "#0a0a0a", theme.DISPLAY_BORDER_INPUT),
    "out": (16, 8, 10, 0, 3, "#070707", "#070707"),
}


def meter_height(kind: str) -> float:
    seg_h, pad_y, _pad_x, border, _r, _bg, _bc = _KINDS[kind]
    return 2 * border + 2 * pad_y + seg_h + LABEL_GAP + LABEL_H


def draw_meter(p: Painter, x: float, y: float, width: float, db: float | None, kind: str) -> None:
    """Draw a meter well with its top-left at logical (x, y). `db` None is an empty meter."""
    seg_h, pad_y, pad_x, border, radius, bg, border_colour = _KINDS[kind]
    height = meter_height(kind)
    p.box(x, y, x + width, y + height, bg, radius, border_colour, border)

    n = len(SEGMENT_DB)
    inner_x = x + border + pad_x
    inner_w = width - 2 * (border + pad_x)
    seg_w = (inner_w - (n - 1) * SEGMENT_GAP) / n
    top = y + border + pad_y
    lit = lit_segments(db)
    for i, threshold in enumerate(SEGMENT_DB):
        sx = inner_x + i * (seg_w + SEGMENT_GAP)
        if lit[i]:
            colour = segment_colour(threshold)
            p.box(sx - 1.5, top - 1.5, sx + seg_w + 1.5, top + seg_h + 1.5, blend(colour, bg, 0.22))
            p.box(
                sx - 0.75, top - 0.75, sx + seg_w + 0.75, top + seg_h + 0.75, blend(colour, bg, 0.4)
            )
            p.box(sx, top, sx + seg_w, top + seg_h, colour)
        else:
            p.box(sx, top, sx + seg_w, top + seg_h, theme.SEGMENT_OFF)

    label_y = top + seg_h + LABEL_GAP + LABEL_H / 2
    for i, label in enumerate(scale_labels()):
        if label:
            sx = inner_x + i * (seg_w + SEGMENT_GAP) + seg_w / 2
            p.text(sx, label_y, label, "mono", 10, theme.TEXT_SCALE, anchor="center")
