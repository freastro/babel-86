"""Babel 86 main window: the rack on a single canvas.

Milestone 1 is the front panel only: it shows mock state and lets you change power,
mutes and knobs in memory. There is no audio, network or persistence yet.
"""

from __future__ import annotations

import argparse
import logging
import sys
import tkinter as tk
from collections.abc import Sequence

from babel86 import __version__, layout, state, theme
from babel86.assets import Sprites
from babel86.dialogs import LanguageDialog
from babel86.fonts import FontBook, register_fonts, resolve_families
from babel86.rack import RackCanvas
from babel86.state import RackState

log = logging.getLogger(__name__)


def enable_dpi_awareness() -> None:
    """Windows: opt in to per-monitor DPI so text and layout are crisp, not bitmap-scaled.

    Must run before the first Tk window is created. Other platforms need nothing here.
    """
    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            log.warning("could not enable DPI awareness")


def display_scale(root: tk.Misc) -> float:
    """Physical pixels per logical (CSS) pixel. macOS draws in points, so it is 1."""
    if sys.platform == "darwin":
        return 1.0
    return max(0.5, root.winfo_fpixels("1i") / 96)


class App:
    """Owns the window, the shared fonts and sprites, and the setup dialog."""

    def __init__(self, root: tk.Tk, rack: RackState, scale: float | None = None) -> None:
        self.root = root
        self.rack = rack
        n = len(rack.units)
        if scale is None:
            scale = layout.choose_scale(
                display_scale(root), root.winfo_screenwidth(), root.winfo_screenheight(), n
            )
        self.scale = scale
        self.fonts = FontBook(root, resolve_families(root), scale)
        self.sprites = Sprites(root, scale)
        self.dialog: LanguageDialog | None = None

        root.title("Babel-86")
        root.configure(background=theme.PAGE)
        self.canvas = RackCanvas(root, rack, scale, self.fonts, self.sprites, self.open_dialog)
        self.canvas.pack(fill="both", expand=True)
        height = self.canvas.fit_height()
        logical_w = layout.initial_window_width(scale, root.winfo_screenwidth())
        width = round(logical_w * scale)
        root.geometry(f"{width}x{height}")
        root.minsize(min(round(theme.MIN_WIDTH * scale), width), height)
        root.resizable(True, False)
        self.canvas.focus_set()

    def open_dialog(self, mode: str, index: int | None = None) -> None:
        """Open the language setup dialog; only one at a time."""
        if self.dialog is not None and self.dialog.winfo_exists():
            return
        if mode == "add" and not self.rack.can_add:
            return
        draft = state.language_draft(self.rack, mode, index)
        self.canvas.set_dimmed(True)
        self.dialog = LanguageDialog(
            self.root, draft, self.scale, self.fonts, self.sprites, on_close=self._dialog_closed
        )

    def _dialog_closed(self) -> None:
        """Undo the dimming and give the keyboard back to the rack the dialog was opened from."""
        self.dialog = None
        self.canvas.set_dimmed(False)
        self.canvas.focus_set()


def build(root: tk.Tk, rack: RackState | None = None, scale: float | None = None) -> App:
    """Set up the main window and return the app, ready to run."""
    register_fonts()
    return App(root, rack or state.mock_rack(), scale)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="babel86", description="Babel-86 live translation rack")
    parser.add_argument("--version", action="version", version=f"babel86 {__version__}")
    parser.add_argument(
        "--display", choices=sorted(theme.DISPLAYS), default="vfd", help="display colour theme"
    )
    parser.add_argument(
        "--power-on", action="store_true", help="start with the power on, for screenshots (dev)"
    )
    parser.add_argument(
        "--units", type=int, choices=range(1, 5), default=4, help="language units to show (dev)"
    )
    parser.add_argument(
        "--dialog",
        metavar="add|edit:N",
        help="open the language setup dialog at launch, for screenshots (dev)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    enable_dpi_awareness()
    root = tk.Tk()
    rack = state.mock_rack(args.units)
    rack.display = args.display
    rack.power = args.power_on
    app = build(root, rack)
    if args.dialog:
        mode, _, index = args.dialog.partition(":")
        root.after(300, lambda: app.open_dialog(mode, int(index) - 1 if index else None))
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
