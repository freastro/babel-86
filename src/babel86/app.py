"""Hello-world faceplate for Babel 86.

Draws a 2U rack panel on a Tk canvas with a logo, a VFD-style display, and a
power switch with a pilot lamp. Click the switch (or press Space) to toggle
power; press Escape to quit.
"""

import tkinter as tk

from babel86 import __version__, theme

GREETING = "HELLO, WORLD"


class Faceplate(tk.Canvas):
    """The front panel. Owns all drawing and the power state."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(
            master,
            width=theme.WIDTH,
            height=theme.HEIGHT,
            background=theme.PANEL,
            highlightthickness=0,
        )
        self.powered = True
        self._draw_chassis()
        self._draw_logo()
        self._draw_display()
        self._draw_power()
        self._render_power_state()

    # -- static artwork -----------------------------------------------------

    def _draw_chassis(self) -> None:
        w, h, ear = theme.WIDTH, theme.HEIGHT, theme.EAR_WIDTH
        for x0 in (0, w - ear):
            self.create_rectangle(x0, 0, x0 + ear, h, fill=theme.EAR, outline=theme.PANEL_EDGE)
            for y in (h * 0.22, h * 0.78):
                self._screw(x0 + ear / 2, y)
        self.create_rectangle(ear, 0, w - ear, h, outline=theme.PANEL_EDGE, width=2)
        # Orange pinstripe along the bottom, very 1986.
        self.create_rectangle(ear + 1, h - 14, w - ear - 1, h - 10, fill=theme.ACCENT, width=0)

    def _screw(self, cx: float, cy: float, r: float = 7) -> None:
        self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=theme.SCREW, outline=theme.SCREW_SLOT)
        self.create_line(cx - r + 2, cy, cx + r - 2, cy, fill=theme.SCREW_SLOT, width=2)

    def _draw_logo(self) -> None:
        x = theme.EAR_WIDTH + 28
        self.create_text(x, 62, text="BABEL 86", anchor="w", font=theme.LOGO_FONT, fill=theme.INK)
        self.create_text(
            x + 2,
            96,
            text="LIVE TRANSLATION PROCESSOR",
            anchor="w",
            font=theme.SUBTITLE_FONT,
            fill=theme.ACCENT,
        )
        self.create_text(
            x + 2,
            116,
            text=f"MODEL 86  ·  v{__version__}",
            anchor="w",
            font=theme.LABEL_FONT,
            fill=theme.INK_DIM,
        )

    def _draw_display(self) -> None:
        x0, y0, x1, y1 = theme.DISPLAY_BOX
        self.create_rectangle(
            x0 - 4, y0 - 4, x1 + 4, y1 + 4, fill=theme.WELL, outline=theme.PANEL_EDGE
        )
        self.create_rectangle(x0, y0, x1, y1, fill=theme.VFD_BG, width=0)
        self.create_text(
            (x0 + x1) / 2, y1 + 18, text="OUTPUT", font=theme.LABEL_FONT, fill=theme.INK_DIM
        )
        self._vfd = self.create_text(
            (x0 + x1) / 2,
            (y0 + y1) / 2,
            text=GREETING,
            font=theme.VFD_FONT,
        )

    def _draw_power(self) -> None:
        cx = theme.WIDTH - theme.EAR_WIDTH - 90
        # Pilot lamp: an outer glow ring and the jewel itself.
        self._lamp_glow = self.create_oval(cx - 46, 46, cx - 18, 74, width=0)
        self._lamp = self.create_oval(cx - 40, 52, cx - 24, 68, outline=theme.WELL)
        # Toggle switch: a slot and a lever that moves up/down.
        self.create_rectangle(
            cx + 10, 40, cx + 34, 92, fill=theme.WELL, outline=theme.PANEL_EDGE
        )
        self._lever = self.create_rectangle(0, 0, 0, 0, fill=theme.SCREW, outline=theme.INK_DIM)
        self.create_text(cx + 22, 30, text="ON", font=theme.LABEL_FONT, fill=theme.INK_DIM)
        self.create_text(cx + 22, 102, text="OFF", font=theme.LABEL_FONT, fill=theme.INK_DIM)
        self.create_text(cx - 32, 118, text="POWER", font=theme.LABEL_FONT, fill=theme.INK)

        self._switch_x = cx + 22
        self._switch_hitbox = (cx + 4, 34, cx + 40, 98)
        self.bind("<Button-1>", self._on_click)

    # -- power state --------------------------------------------------------

    def toggle_power(self) -> None:
        self.powered = not self.powered
        self._render_power_state()

    def _render_power_state(self) -> None:
        on = self.powered
        self.itemconfigure(self._lamp, fill=theme.LAMP_ON if on else theme.LAMP_OFF)
        self.itemconfigure(self._lamp_glow, fill=theme.LAMP_GLOW if on else theme.PANEL)
        self.itemconfigure(self._vfd, fill=theme.VFD_ON if on else theme.VFD_OFF)
        x = self._switch_x
        if on:
            self.coords(self._lever, x - 8, 44, x + 8, 64)
        else:
            self.coords(self._lever, x - 8, 68, x + 8, 88)

    def _on_click(self, event: tk.Event) -> None:
        x0, y0, x1, y1 = self._switch_hitbox
        if x0 <= event.x <= x1 and y0 <= event.y <= y1:
            self.toggle_power()


def build(root: tk.Tk) -> Faceplate:
    """Set up the main window and return its faceplate."""
    root.title("Babel 86")
    root.configure(background=theme.PANEL)
    root.resizable(False, False)
    face = Faceplate(root)
    face.pack()
    root.bind("<space>", lambda _e: face.toggle_power())
    root.bind("<Escape>", lambda _e: root.destroy())
    return face


def main() -> int:
    root = tk.Tk()
    build(root)
    root.mainloop()
    return 0
