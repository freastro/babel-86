"""Babel 86 main window: the rack on a single canvas.

Milestone 2: every control works by mouse, touch and keyboard, the setup dialog adds,
edits and removes languages, and the rack is saved to `babel86.json` and restored at
launch. There is no audio or network yet.
"""

from __future__ import annotations

import argparse
import logging
import sys
import tkinter as tk
from collections.abc import Sequence
from pathlib import Path

from babel86 import __version__, layout, persist, state, theme
from babel86.assets import Sprites
from babel86.dialogs import LanguageDialog
from babel86.fonts import FontBook, register_fonts, resolve_families
from babel86.rack import RackCanvas
from babel86.state import RackState

log = logging.getLogger(__name__)

SAVE_DELAY_MS = 500


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

    def __init__(
        self,
        root: tk.Tk,
        rack: RackState,
        scale: float | None = None,
        save_path: Path | None = None,
    ) -> None:
        self.root = root
        self.rack = rack
        self.save_path = save_path  # None: saving is off (the --units mock rack, tests)
        self._save_job: str | None = None
        if scale is None:
            # Fit a full rack, so adding units never pushes the window off the screen.
            n = max(len(rack.units), state.MAX_LANGUAGE_UNITS)
            scale = layout.choose_scale(
                display_scale(root), root.winfo_screenwidth(), root.winfo_screenheight(), n
            )
        self.scale = scale
        self.fonts = FontBook(root, resolve_families(root), scale)
        self.sprites = Sprites(root, scale)
        self.dialog: LanguageDialog | None = None

        root.title("Babel-86")
        root.configure(background=theme.PAGE)
        self.canvas = RackCanvas(
            root, rack, scale, self.fonts, self.sprites, self.open_dialog, self.changed
        )
        self.canvas.pack(fill="both", expand=True)
        logical_w = layout.initial_window_width(scale, root.winfo_screenwidth())
        self.fit_window(round(logical_w * scale))
        root.resizable(True, False)
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self.canvas.focus_set()

    def fit_window(self, width: int | None = None) -> None:
        """Size the window to the rack's height, after launch or after Add and Remove."""
        height = self.canvas.fit_height()
        if width is None:
            width = max(self.root.winfo_width(), 1)
        self.root.minsize(min(round(theme.MIN_WIDTH * self.scale), width), height)
        self.root.geometry(f"{width}x{height}")

    def changed(self) -> None:
        """Something saved in the rack changed: save 500 ms after the last change."""
        if self.save_path is None:
            return
        if self._save_job is not None:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(SAVE_DELAY_MS, self.save_pending)

    def save_pending(self) -> None:
        """Save now if a save is pending."""
        if self._save_job is None:
            return
        self.root.after_cancel(self._save_job)
        self._save_job = None
        self.save()

    def save(self) -> None:
        if self.save_path is None:
            return
        try:
            persist.save(self.rack, self.save_path)
        except OSError as exc:
            log.warning("could not save %s: %s", self.save_path, exc)

    def quit(self) -> None:
        """Window close: write any pending change, then go."""
        self.save_pending()
        self.root.destroy()

    def open_dialog(self, mode: str, index: int | None = None) -> None:
        """Open the language setup dialog; only one at a time."""
        if self.dialog is not None and self.dialog.winfo_exists():
            return
        if mode == "add" and not self.rack.can_add:
            return
        draft = state.language_draft(self.rack, mode, index)
        self.canvas.set_dimmed(True)
        self.dialog = LanguageDialog(
            self.root,
            draft,
            self.scale,
            self.fonts,
            self.sprites,
            on_close=self._dialog_closed,
            rack=self.rack,
            on_confirm=self._confirmed,
            on_remove=self._removed,
        )

    def _confirmed(self, draft: state.LanguageDraft) -> None:
        adding = draft.index is None
        state.apply(self.rack, draft)
        if adding:
            if not self.rack.can_add:  # the ADD key that opened the dialog is gone
                self.canvas.focus_key = ("setup", len(self.rack.units) - 1)
            self.fit_window()
        self.canvas.invalidate()
        self.changed()

    def _removed(self, index: int) -> None:
        state.remove(self.rack, index)
        # The opener went with its unit; ADD LANGUAGE OUTPUT is always there after a remove.
        self.canvas.focus_key = ("add", None)
        self.fit_window()
        self.canvas.invalidate()
        self.changed()

    def _dialog_closed(self) -> None:
        """Undo the dimming and give the keyboard back to the button that opened the dialog.

        The rack's focus key still names that button (Setup or Add), or its stand-in when
        Remove or a filling Add took it away, so its ring returns.
        """
        self.dialog = None
        self.canvas.set_dimmed(False)
        self.canvas.focus_set()


def build(
    root: tk.Tk,
    rack: RackState | None = None,
    scale: float | None = None,
    save_path: Path | None = None,
) -> App:
    """Set up the main window and return the app, ready to run."""
    register_fonts()
    return App(root, rack or state.mock_rack(), scale, save_path)


def load_rack(args: argparse.Namespace) -> tuple[RackState, Path | None]:
    """The rack to show and where to save it. `--units` shows the mock rack, unsaved."""
    if args.units is not None:
        rack, path = state.mock_rack(args.units), None
    else:
        path = Path(args.config) if args.config else persist.config_path()
        rack = persist.load(path)
    if args.display is not None:
        rack.display = args.display
        if path is not None:
            try:
                persist.save(rack, path)  # --display is remembered
            except OSError as exc:
                log.warning("could not save %s: %s", path, exc)
    rack.power = not args.power_off  # never saved
    return rack, path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="babel86", description="Babel-86 live translation rack")
    parser.add_argument("--version", action="version", version=f"babel86 {__version__}")
    parser.add_argument(
        "--display", choices=sorted(theme.DISPLAYS), help="display colour theme (saved)"
    )
    parser.add_argument(
        "--config", metavar="PATH", help="rack file to load and save instead of the default"
    )
    parser.add_argument("--power-off", action="store_true", help="start with the power off (dev)")
    parser.add_argument(
        "--units",
        type=int,
        choices=range(1, 5),
        help="show the mock rack with N language units; nothing is saved (dev)",
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
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    rack, path = load_rack(args)
    root = tk.Tk()
    app = build(root, rack, save_path=path)
    if args.dialog:
        mode, _, index = args.dialog.partition(":")
        root.after(300, lambda: app.open_dialog(mode, int(index) - 1 if index else None))
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
