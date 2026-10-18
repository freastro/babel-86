"""Bundled fonts: private registration with the OS and the families the UI draws with.

Michroma, Archivo Narrow and Share Tech Mono ship in `assets/fonts` (SIL OFL 1.1). They
are registered for this process only, never installed system-wide. If registration fails,
or on Linux where it is not attempted, text falls back to a stock Tk family and the app
logs a warning instead of crashing.

User content (transcript, translations, language names) is drawn with the same Tk fonts.
Tk substitutes a system font per character when the design font lacks a glyph, which is
how Khmer, Arabic, CJK and other scripts get drawn. See ADR 0003.
"""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import font as tkfont

from babel86 import theme

log = logging.getLogger(__name__)

FONT_DIR = Path(__file__).parent / "assets" / "fonts"
FONT_FILES = (
    "Michroma-Regular.ttf",
    "ArchivoNarrow-Regular.ttf",
    "ArchivoNarrow-Bold.ttf",
    "ShareTechMono-Regular.ttf",
)

FALLBACKS = {
    theme.FAMILY_LOGO: "Helvetica",
    theme.FAMILY_CAPTION: "Helvetica",
    theme.FAMILY_MONO: "Courier",
}

_registered: bool | None = None


def register_fonts() -> bool:
    """Register the bundled TTFs privately with the OS. Returns True if all succeeded."""
    global _registered
    if _registered is not None:
        return _registered
    paths = [FONT_DIR / name for name in FONT_FILES]
    missing = [p.name for p in paths if not p.exists()]
    if missing:
        log.warning("bundled fonts missing: %s", ", ".join(missing))
        _registered = False
        return False
    try:
        if sys.platform == "win32":
            _registered = all(_register_windows(p) for p in paths)
        elif sys.platform == "darwin":
            _registered = all(_register_macos(p) for p in paths)
        else:
            log.warning("bundled fonts are not registered on this platform; using fallbacks")
            _registered = False
    except Exception:
        log.warning("font registration failed; using fallback fonts", exc_info=True)
        _registered = False
    return _registered


def _register_windows(path: Path) -> bool:
    import ctypes

    fr_private = 0x10
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    add = gdi32.AddFontResourceExW
    add.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_void_p]
    add.restype = ctypes.c_int
    return add(str(path), fr_private, None) > 0


def _register_macos(path: Path) -> bool:
    import ctypes
    import ctypes.util

    cf = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
    ct = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreText"))
    cf.CFURLCreateFromFileSystemRepresentation.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_long,
        ctypes.c_bool,
    ]
    cf.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
    ct.CTFontManagerRegisterFontsForURL.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    ct.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
    raw = str(path).encode()
    url = cf.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), False)
    scope_process = 1
    return bool(ct.CTFontManagerRegisterFontsForURL(url, scope_process, None))


@dataclass(frozen=True)
class Families:
    logo: str
    caption: str
    mono: str


def resolve_families(root: tk.Misc) -> Families:
    """Pick the design families if Tk can see them, otherwise stock fallbacks."""
    available = set(tkfont.families(root))

    def pick(name: str) -> str:
        if name in available:
            return name
        log.warning("font %r not available; falling back to %s", name, FALLBACKS[name])
        return FALLBACKS[name]

    return Families(
        logo=pick(theme.FAMILY_LOGO),
        caption=pick(theme.FAMILY_CAPTION),
        mono=pick(theme.FAMILY_MONO),
    )


class FontBook:
    """Caches `tkfont.Font` objects by role, size and weight at the current UI scale."""

    def __init__(self, root: tk.Misc, families: Families, scale: float) -> None:
        self.root = root
        self.families = families
        self.scale = scale
        self._cache: dict[tuple[str, float, bool], tkfont.Font] = {}

    def get(self, role: str, size: float, bold: bool = False) -> tkfont.Font:
        """`role` is "logo", "caption" or "mono"; `size` is in logical px."""
        key = (role, size, bold)
        font = self._cache.get(key)
        if font is None:
            font = tkfont.Font(
                root=self.root,
                family=getattr(self.families, role),
                size=-max(1, round(size * self.scale)),
                weight="bold" if bold else "normal",
            )
            self._cache[key] = font
        return font

    def set_scale(self, scale: float) -> None:
        if scale != self.scale:
            self.scale = scale
            self._cache.clear()
