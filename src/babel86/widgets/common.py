"""`Painter`: logical-pixel drawing primitives on a Tk canvas.

All coordinates passed to a Painter are logical pixels (the design's CSS pixels). It
multiplies by the UI scale and draws with plain canvas items: flat fills, chamfered
corners, text, and pre-rendered sprites. Rectangles use fill only, with no outline, so
edges land on exact pixels.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from babel86.assets import Sprites
from babel86.fonts import FontBook


def blend(fg: str, bg: str, alpha: float) -> str:
    """`fg` over `bg` at the given opacity, as a hex colour."""
    a = [int(fg[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(bg[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(b[i] + (a[i] - b[i]) * alpha):02x}" for i in range(3))


class Painter:
    def __init__(self, canvas: tk.Canvas, scale: float, fonts: FontBook, sprites: Sprites) -> None:
        self.cv = canvas
        self.scale = scale
        self.fonts = fonts
        self.sprites = sprites

    # -- units -------------------------------------------------------------------------

    def p(self, v: float) -> int:
        return round(v * self.scale)

    def font(self, role: str, size: float, bold: bool = False) -> tkfont.Font:
        return self.fonts.get(role, size, bold)

    def text_width(self, text: str, role: str, size: float, bold: bool = False) -> float:
        """Width of text in logical px."""
        return self.font(role, size, bold).measure(text) / self.scale

    def spaced_width(
        self, text: str, role: str, size: float, spacing: float, bold: bool = False
    ) -> float:
        """Logical width of text with CSS-style letter spacing (in em, trailing included)."""
        base = self.text_width(text, role, size, bold)
        return base + spacing * size * len(text)

    # -- shapes ------------------------------------------------------------------------

    def rect(self, x0: float, y0: float, x1: float, y1: float, fill: str) -> int:
        return self.cv.create_rectangle(
            self.p(x0), self.p(y0), self.p(x1), self.p(y1), fill=fill, outline=""
        )

    def box(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        fill: str,
        radius: float = 0,
        border: str | None = None,
        border_width: float = 0,
    ) -> None:
        """A filled box with chamfered corners and an optional solid border."""
        if border and border_width:
            self._chamfer(x0, y0, x1, y1, radius, border)
            inset = border_width
            self._chamfer(
                x0 + inset, y0 + inset, x1 - inset, y1 - inset, max(0, radius - inset), fill
            )
        else:
            self._chamfer(x0, y0, x1, y1, radius, fill)

    def _chamfer(
        self, x0: float, y0: float, x1: float, y1: float, radius: float, fill: str
    ) -> None:
        a, b, c, d = self.p(x0), self.p(y0), self.p(x1), self.p(y1)
        r = round(radius * self.scale * 0.6)
        if r <= 0:
            self.cv.create_rectangle(a, b, c, d, fill=fill, outline="")
            return
        pts = [a + r, b, c - r, b, c, b + r, c, d - r, c - r, d, a + r, d, a, d - r, a, b + r]
        self.cv.create_polygon(pts, fill=fill, outline="")

    def line(self, x0: float, y0: float, x1: float, y1: float, fill: str, width: float = 1) -> None:
        self.cv.create_line(
            self.p(x0),
            self.p(y0),
            self.p(x1),
            self.p(y1),
            fill=fill,
            width=max(1, self.p(width)),
            capstyle=tk.ROUND,
        )

    def oval_outline(self, cx: float, cy: float, r: float, colour: str, width: float) -> None:
        self.cv.create_oval(
            self.p(cx - r),
            self.p(cy - r),
            self.p(cx + r),
            self.p(cy + r),
            outline=colour,
            width=max(1, self.p(width)),
        )

    def outline(
        self, x0: float, y0: float, x1: float, y1: float, colour: str, width: float
    ) -> None:
        """A rectangle outline, centred on the given edges: used for focus rings."""
        self.cv.create_rectangle(
            self.p(x0),
            self.p(y0),
            self.p(x1),
            self.p(y1),
            outline=colour,
            width=max(1, self.p(width)),
        )

    def dashed_box(self, x0: float, y0: float, x1: float, y1: float, colour: str) -> None:
        d = max(1, self.p(1))
        self.cv.create_rectangle(
            self.p(x0),
            self.p(y0),
            self.p(x1) - d,
            self.p(y1) - d,
            outline=colour,
            width=d,
            dash=(self.p(4), self.p(3)),
        )

    def gradient_v(self, x0: float, y0: float, x1: float, y1: float, top: str, bottom: str) -> None:
        """A vertical linear gradient as horizontal bands, one per distinct colour step."""
        delta = max(abs(int(top[i : i + 2], 16) - int(bottom[i : i + 2], 16)) for i in (1, 3, 5))
        bands = max(1, min(delta + 1, self.p(y1 - y0)))
        for i in range(bands):
            t = (i + 0.5) / bands
            colour = blend(bottom, top, t)
            self.cv.create_rectangle(
                self.p(x0),
                self.p(y0 + (y1 - y0) * i / bands),
                self.p(x1),
                self.p(y0 + (y1 - y0) * (i + 1) / bands),
                fill=colour,
                outline="",
            )

    # -- sprites -----------------------------------------------------------------------

    def image(self, name: str, x: float, y: float, anchor: str = "center") -> None:
        """Draw a sprite; `anchor` is "center" or "nw" of the given logical point."""
        self.cv.create_image(self.p(x), self.p(y), image=self.sprites.get(name), anchor=anchor)

    # -- text --------------------------------------------------------------------------

    def text(
        self,
        x: float,
        y: float,
        text: str,
        role: str,
        size: float,
        fill: str,
        *,
        bold: bool = False,
        anchor: str = "w",
        spacing: float = 0.0,
        glow: str | None = None,
    ) -> float:
        """Draw one line vertically centred on `y`. `anchor` is "w", "center" or "e".

        `spacing` is CSS-style letter-spacing in em and is only for fixed Latin chrome:
        it places each character on its own, which would break shaping in complex scripts.
        `glow` is a background colour to fake a text-shadow halo over. Returns the width.
        """
        if not text:
            return 0.0
        font = self.font(role, size, bold)
        tk_anchor = {"w": "w", "e": "e", "center": "center"}[anchor]
        yy = self.p(y)
        if glow is not None:
            self._glow_text(x, yy, text, font, fill, glow, tk_anchor, spacing * size)
        return self._draw_text(self.p(x), yy, text, font, fill, tk_anchor, spacing * size)

    def _draw_text(
        self,
        px: float,
        py: int,
        text: str,
        font: tkfont.Font,
        fill: str,
        anchor: str,
        spacing_px_logical: float,
    ) -> float:
        if spacing_px_logical == 0:
            self.cv.create_text(px, py, text=text, font=font, fill=fill, anchor=anchor)
            return font.measure(text) / self.scale
        gap = spacing_px_logical * self.scale
        widths = [font.measure(ch) for ch in text]
        total = sum(widths) + gap * len(text)
        left = {"w": px, "center": px - total / 2, "e": px - total}[anchor]
        for ch, w in zip(text, widths, strict=True):
            self.cv.create_text(round(left), py, text=ch, font=font, fill=fill, anchor="w")
            left += w + gap
        return total / self.scale

    def _glow_text(
        self,
        x: float,
        py: int,
        text: str,
        font: tkfont.Font,
        fill: str,
        background: str,
        anchor: str,
        spacing: float,
    ) -> None:
        reach = max(1, round(self.scale * 0.75))
        for strength, dist in ((0.14, reach * 2), (0.3, reach)):
            halo = blend(fill, background, strength)
            for dx, dy in ((-dist, 0), (dist, 0), (0, -dist), (0, dist)):
                self._draw_text(self.p(x) + dx, py + dy, text, font, halo, anchor, spacing)
