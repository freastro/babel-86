"""Render the rack's sprites (knob bodies and caps, screws, lamps) as PNGs.

Tk's canvas cannot draw anti-aliased circles, radial gradients or glows, so these are
rendered once here with Pillow and committed. The app loads them with `tk.PhotoImage`
and never imports Pillow. Pillow is a dev-only dependency (see ADR 0002).

    python tools/make_sprites.py            # write src/babel86/assets/sprites/
    python tools/make_sprites.py --check    # fail if the committed PNGs are stale

Every sprite is rendered at each scale in `layout.SPRITE_SCALES` and named
`<name>@<scale>x.png`, for example `knob_in@1.25x.png`.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from babel86 import theme  # noqa: E402
from babel86.layout import SPRITE_SCALES  # noqa: E402

OUT = ROOT / "src" / "babel86" / "assets" / "sprites"
SUPERSAMPLE = 4
TOLERANCE = 3  # per-channel difference allowed by --check, to absorb library rounding

Colour = tuple[int, int, int, int]


def rgba(hex_colour: str, alpha: float = 1.0) -> Colour:
    h = hex_colour.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), round(alpha * 255))


def lerp(a: Colour, b: Colour, t: float) -> Colour:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(4))  # type: ignore[return-value]


class Canvas:
    """A supersampled RGBA canvas addressed in logical pixels."""

    def __init__(self, width: float, height: float, scale: float) -> None:
        self.k = scale * SUPERSAMPLE
        self.scale = scale
        self.size = (round(width * self.k), round(height * self.k))
        self.img = Image.new("RGBA", self.size, (0, 0, 0, 0))

    def px(self, v: float) -> float:
        return v * self.k

    def disc_mask(self, cx: float, cy: float, r: float) -> Image.Image:
        mask = Image.new("L", self.size, 0)
        ImageDraw.Draw(mask).ellipse(
            (self.px(cx - r), self.px(cy - r), self.px(cx + r), self.px(cy + r)), fill=255
        )
        return mask

    def fill_disc(self, cx: float, cy: float, r: float, colour: Colour) -> None:
        layer = Image.new("RGBA", self.size, colour)
        self.img.alpha_composite(_masked(layer, self.disc_mask(cx, cy, r)))

    def radial_disc(
        self,
        cx: float,
        cy: float,
        r: float,
        focus: tuple[float, float],
        inner: Colour,
        outer: Colour,
        stop_radius: float,
    ) -> None:
        """A disc filled with a CSS-style radial gradient centred on `focus`."""
        layer = Image.new("RGBA", self.size, outer)
        draw = ImageDraw.Draw(layer)
        steps = max(8, round(self.px(stop_radius)))
        for i in range(steps, -1, -1):
            t = i / steps
            rr = stop_radius * t
            draw.ellipse(
                (
                    self.px(focus[0] - rr),
                    self.px(focus[1] - rr),
                    self.px(focus[0] + rr),
                    self.px(focus[1] + rr),
                ),
                fill=lerp(inner, outer, t),
            )
        self.img.alpha_composite(_masked(layer, self.disc_mask(cx, cy, r)))

    def glow(self, cx: float, cy: float, r: float, colour: Colour, blur: float) -> None:
        """A box-shadow style glow: a solid disc blurred by `blur` logical pixels."""
        mask = self.disc_mask(cx, cy, r).filter(ImageFilter.GaussianBlur(self.px(blur) / 2))
        layer = Image.new("RGBA", self.size, colour)
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
        self.img.alpha_composite(layer)

    def inset_shadow(
        self, cx: float, cy: float, r: float, dy: float, blur: float, colour: Colour
    ) -> None:
        """CSS `inset 0 dy blur colour` inside the disc."""
        inside = self.disc_mask(cx, cy, r)
        shifted = self.disc_mask(cx, cy + dy, r)
        edge = ImageChops.subtract(inside, shifted)
        edge = edge.filter(ImageFilter.GaussianBlur(self.px(blur) / 2))
        edge = ImageChops.multiply(edge, inside)
        layer = Image.new("RGBA", self.size, colour)
        alpha = ImageChops.multiply(layer.getchannel("A"), edge)
        layer.putalpha(alpha)
        self.img.alpha_composite(layer)

    def finish(self) -> Image.Image:
        w = round(self.size[0] / SUPERSAMPLE)
        h = round(self.size[1] / SUPERSAMPLE)
        return self.img.resize((w, h), Image.Resampling.LANCZOS)


def _masked(layer: Image.Image, mask: Image.Image) -> Image.Image:
    out = layer.copy()
    out.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    return out


# -- Sprite recipes ----------------------------------------------------------------------


def knob_body(scale: float, core: tuple[str, str], border: str, shadow: str) -> Image.Image:
    """46 px knob: radial-gradient face, 2 px border, hard 3 px drop shadow."""
    d = theme.KNOB_DIAMETER
    c = Canvas(d, d + 3, scale)
    r = d / 2
    c.fill_disc(r, r + 3, r, rgba(shadow))
    c.fill_disc(r, r, r, rgba(border))
    inner = r - 2
    focus = (0.38 * (d - 4) + 2, 0.30 * (d - 4) + 2)
    far = ((d - 2 - focus[0]) ** 2 + (d - 2 - focus[1]) ** 2) ** 0.5
    c.radial_disc(r, r, inner, focus, rgba(core[0]), rgba(core[1]), far * 0.72)
    return c.finish()


def knob_cap(scale: float, colour: str) -> Image.Image:
    c = Canvas(24, 24, scale)
    c.fill_disc(12, 12, 12, rgba(colour))
    c.inset_shadow(12, 12, 12, 2, 2, rgba("#ffffff", 0.35))
    c.inset_shadow(12, 12, 12, -2, 3, rgba("#000000", 0.35))
    return c.finish()


def screw(scale: float, light: bool) -> Image.Image:
    c = Canvas(14, 14, scale)
    if light:
        c.fill_disc(7, 7, 7, rgba("#6f6a5f"))
        inner, outer = rgba("#f4f1ea"), rgba("#8b8579")
        radius = 6
    else:
        inner, outer = rgba("#c9c6bf"), rgba("#55524c")
        radius = 7
    focus = (0.4 * 14, 0.35 * 14)
    far = ((14 - focus[0]) ** 2 + (14 - focus[1]) ** 2) ** 0.5
    c.radial_disc(7, 7, radius, focus, inner, outer, far * 0.75)
    return c.finish()


def lamp(scale: float, colour: str | None, size: int, border: str, glow_blur: float) -> Image.Image:
    """A round indicator: border ring, flat colour, top highlight and an outer glow."""
    pad = glow_blur + 2
    total = size + 2 * pad
    c = Canvas(total, total, scale)
    mid = total / 2
    r = size / 2
    lit = colour is not None and colour != theme.LAMP_OFF
    face = colour or theme.LAMP_OFF
    if lit:
        c.glow(mid, mid, r, rgba(face), glow_blur)
    c.fill_disc(mid, mid, r, rgba(border, 0.6 if size <= 8 else 1.0))
    ring = 1 if size <= 8 else 2
    c.fill_disc(mid, mid, r - ring, rgba(face))
    c.inset_shadow(mid, mid, r - ring, 2, 2, rgba("#ffffff", 0.5 if lit else 0.08))
    return c.finish()


Recipe = Callable[[float], Image.Image]


def recipes() -> dict[str, Recipe]:
    out: dict[str, Recipe] = {
        "knob_in": lambda s: knob_body(s, ("#4a4844", "#121110"), "#0c0b0a", "#6f6a5f"),
        "knob_out": lambda s: knob_body(s, ("#4e4e52", "#0f0f10"), "#000000", "#000000"),
        "screw_in": lambda s: screw(s, True),
        "screw_out": lambda s: screw(s, False),
    }
    for key, hex_colour in {**theme.KNOB_CAPS, "classic": "#2c2b29"}.items():
        out[f"cap_{key}"] = lambda s, h=hex_colour: knob_cap(s, h)
    for key, hex_colour in theme.STATUS_COLOURS.items():
        out[f"lamp_{key}"] = lambda s, h=hex_colour: lamp(s, h, 18, "#000000", 10)
    out["lamp_off"] = lambda s: lamp(s, None, 18, "#000000", 10)
    out["led_red"] = lambda s: lamp(s, theme.ALERT, 8, "#000000", 6)
    out["led_off"] = lambda s: lamp(s, None, 8, "#000000", 6)
    for key, hex_colour in theme.PASTELS.items():
        out[f"led_{key}"] = lambda s, h=hex_colour: lamp(s, h, 8, "#000000", 6)
    return out


def filename(name: str, scale: float) -> str:
    return f"{name}@{scale:g}x.png"


def render_all(dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    written = []
    for name, recipe in recipes().items():
        for scale in SPRITE_SCALES:
            path = dest / filename(name, scale)
            recipe(scale).save(path, optimize=True)
            written.append(path)
    return written


def differs(a: Path, b: Path) -> bool:
    if not b.exists():
        return True
    with Image.open(a) as ia, Image.open(b) as ib:
        if ia.size != ib.size:
            return True
        diff = ImageChops.difference(ia.convert("RGBA"), ib.convert("RGBA"))
        return max(hi for _lo, hi in diff.getextrema()) > TOLERANCE


def check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        fresh = render_all(Path(tmp))
        stale = [p.name for p in fresh if differs(p, OUT / p.name)]
        extra = sorted(p.name for p in OUT.glob("*.png") if p.name not in {f.name for f in fresh})
    if stale or extra:
        print("Sprites are stale. Run: python tools/make_sprites.py")
        for name in stale + extra:
            print("  ", name)
        return 1
    print(f"{len(fresh)} sprites up to date")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare, do not write")
    args = parser.parse_args()
    if args.check:
        return check()
    written = render_all(OUT)
    print(f"wrote {len(written)} sprites to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
