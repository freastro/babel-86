"""Sprite loading. The PNGs are pre-rendered by `tools/make_sprites.py`; see ADR 0002."""

from __future__ import annotations

import base64
import logging
import time
import tkinter as tk
from pathlib import Path

from babel86 import layout

log = logging.getLogger(__name__)

SPRITE_DIR = Path(__file__).parent / "assets" / "sprites"
LOAD_ATTEMPTS = 4


def sprite_path(name: str, scale: float) -> Path:
    return SPRITE_DIR / f"{name}@{scale:g}x.png"


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
