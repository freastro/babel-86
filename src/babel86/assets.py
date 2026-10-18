"""Sprite loading. The PNGs are pre-rendered by `tools/make_sprites.py`; see ADR 0002."""

from __future__ import annotations

import base64
import logging
import struct
import time
import tkinter as tk
import zlib
from pathlib import Path

from babel86 import layout

log = logging.getLogger(__name__)

SPRITE_DIR = Path(__file__).parent / "assets" / "sprites"
LOAD_ATTEMPTS = 4


def sprite_path(name: str, scale: float) -> Path:
    return SPRITE_DIR / f"{name}@{scale:g}x.png"


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))


def scrim(root: tk.Misc, width: int, height: int, opacity: float) -> tk.PhotoImage:
    """A translucent black image of the given size, for dimming what sits behind a dialog.

    Built from a single RGBA pixel written with the standard library and stretched by Tk, so
    it needs no image library and no stipple (macOS ignores stipples).
    """
    alpha = round(max(0.0, min(1.0, opacity)) * 255)
    pixel = zlib.compress(b"\x00" + bytes((0, 0, 0, alpha)))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + _png_chunk(b"IDAT", pixel)
        + _png_chunk(b"IEND", b"")
    )
    pixel_image = tk.PhotoImage(master=root, data=base64.b64encode(png))
    return pixel_image.zoom(max(1, width), max(1, height))


class Sprites:
    """Loads and caches `tk.PhotoImage`s for one UI scale. Keep a reference while drawing."""

    def __init__(self, root: tk.Misc, ui_scale: float) -> None:
        self.root = root
        self.ui_scale = ui_scale
        self.sprite_scale = layout.sprite_scale(ui_scale)
        self._cache: dict[str, tk.PhotoImage] = {}

    def get(self, name: str) -> tk.PhotoImage:
        image = self._cache.get(name)
        if image is None:
            image = self._load(name)
            self._cache[name] = image
        return image

    def _load(self, name: str) -> tk.PhotoImage:
        """Read the PNG in Python and hand Tk the bytes.

        Tk's own `-file` loading failed sporadically on Windows with an empty error (about one
        load in a few thousand), so read the file here, retry if anything goes wrong, and fall
        back to an invisible pixel rather than crash the whole redraw.
        """
        path = sprite_path(name, self.sprite_scale)
        error: Exception | None = None
        for attempt in range(LOAD_ATTEMPTS):
            try:
                data = base64.b64encode(path.read_bytes())
                return tk.PhotoImage(master=self.root, data=data)
            except (OSError, tk.TclError) as exc:
                error = exc
                time.sleep(0.02 * (attempt + 1))
        log.warning("could not load sprite %s: %r", path.name, error)
        return tk.PhotoImage(master=self.root, width=1, height=1)
