"""Buttons, section tags and the small icons drawn on them."""

from __future__ import annotations

from babel86 import theme
from babel86.widgets.common import Painter

BUTTON_SPACING = 0.16


def draw_tag(
    p: Painter, x: float, y: float, width: float, label: str, bg: str, fg: str, rule: str
) -> None:
    """Section header: a coloured caps tag, then a 1 px rule to the end of the column."""
    spacing = 0.2
    tag_w = p.spaced_width(label, "caption", 10, spacing, bold=True) + 12
    p.box(x, y, x + tag_w, y + theme.TAG_HEIGHT, bg, 2)
    p.text(x + 6, y + theme.TAG_HEIGHT / 2, label, "caption", 10, fg, bold=True, spacing=spacing)
    p.rect(
        x + tag_w + 8,
        y + theme.TAG_HEIGHT / 2 - 0.5,
        x + width,
        y + theme.TAG_HEIGHT / 2 + 0.5,
        rule,
    )


def draw_button(
    p: Painter,
    x: float,
    y: float,
    label: str,
    style: theme.ButtonStyle,
    *,
    led: str | None = None,
    icon: str | None = None,
    width: float = theme.BUTTON_WIDTH,
    height: float = theme.BUTTON_HEIGHT,
    spacing: float = BUTTON_SPACING,
    dashed: str | None = None,
) -> None:
    """A 128 x 44 key with a hard 2 px bottom shadow. `led` names a sprite such as led_red."""
    if dashed:
        p.dashed_box(x, y, x + width, y + height, dashed)
    else:
        p.box(x, y + 2, x + width, y + height + 2, style.shadow, 4)
        p.box(x, y, x + width, y + height, style.face, 4, style.border, 1 if style.border else 0)
        if style.highlight:
            p.rect(x + 2, y + 1, x + width - 2, y + 2, style.highlight)

    mark = 8 if led else 14 if icon else 0
    gap = 8 if mark else 0
    text_w = p.spaced_width(label, "caption", 11, spacing, bold=True)
    left = x + (width - (mark + gap + text_w)) / 2
    cy = y + height / 2
    if led:
        p.image(led, left + 4, cy)
    elif icon:
        draw_icon(p, icon, left + 7, cy, 14, style.fg)
    p.text(left + mark + gap, cy, label, "caption", 11, style.fg, bold=True, spacing=spacing)


def draw_icon(p: Painter, name: str, cx: float, cy: float, size: float, colour: str) -> None:
    """Icons from the design, redrawn from their 24 x 24 SVG paths."""
    k = size / 24
    ox, oy = cx - size / 2, cy - size / 2

    def pt(x: float, y: float) -> tuple[float, float]:
        return ox + x * k, oy + y * k

    stroke = 2.0 * k if name != "plus" else 2.2 * k
    if name == "sliders":
        for (x0, y0), (x1, y1) in (
            ((4, 6), (13, 6)),
            ((19, 6), (20, 6)),
            ((4, 12), (7, 12)),
            ((13, 12), (20, 12)),
            ((4, 18), (15, 18)),
        ):
            p.line(*pt(x0, y0), *pt(x1, y1), colour, stroke)
        for kx, ky in ((16, 6), (10, 12), (18, 18)):
            px, py = pt(kx, ky)
            p.oval_outline(px, py, 2.5 * k, colour, stroke)
    elif name == "plus":
        p.line(*pt(12, 5), *pt(12, 19), colour, stroke)
        p.line(*pt(5, 12), *pt(19, 12), colour, stroke)


def draw_power_icon(p: Painter, cx: float, cy: float, colour: str) -> None:
    """The power symbol: a gapped ring with a stem, 20 px."""
    k = 20 / 24
    ox, oy = cx - 10, cy - 10
    width = max(1, p.p(2.4 * k))
    centre_x, centre_y, radius = ox + 12 * k, oy + 12.41 * k, 8 * k
    p.cv.create_arc(
        p.p(centre_x - radius),
        p.p(centre_y - radius),
        p.p(centre_x + radius),
        p.p(centre_y + radius),
        start=135,
        extent=270,
        style="arc",
        outline=colour,
        width=width,
    )
    p.line(ox + 12 * k, oy + 3 * k, ox + 12 * k, oy + 11 * k, colour, 2.4 * k)
