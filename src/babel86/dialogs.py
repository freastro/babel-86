"""The language setup dialog, drawn on its own canvas to match `OutputSetup.dc.html`.

Milestone 1 shows it display-only: Cancel and Esc close it, and every other control is
inert. Working fields arrive with the persistence milestone.
"""

from __future__ import annotations

import tkinter as tk

from babel86 import theme
from babel86.assets import Sprites
from babel86.fonts import FontBook
from babel86.state import LANGUAGES, MODEL_LABELS, LanguageDraft
from babel86.widgets.button import draw_button
from babel86.widgets.common import Painter

DIALOG_WIDTH = 560
PAD = 24
FIELD_GAP = 22
CONTROL_H = 48
LABEL_H = 12
LABEL_COLOUR = theme.TEXT_ROUTE
KICKER_COLOUR = theme.TEXT_SCALE
CODE_COLOUR = theme.DISPLAYS["vfd"]
PASS_NOTE = "Pass-thru sends the original speech to this output without translating it."


def dialog_height(draft: LanguageDraft) -> float:
    """Total logical height, which grows by one note line for Pass-thru."""
    return 98 + _body_height(draft) + 77


def _body_height(draft: LanguageDraft) -> float:
    note = 21 if draft.model == "pass" else 0
    # padding, language, label, model, device row, colours, padding, plus the 22 px gaps
    return PAD + 68 + 68 + 76 + note + 68 + 64 + PAD + 4 * FIELD_GAP


class LanguageDialog(tk.Toplevel):
    """A modal, display-only dialog. Close it with Cancel, Esc or the window's close button."""

    def __init__(
        self,
        master: tk.Misc,
        draft: LanguageDraft,
        scale: float,
        fonts: FontBook,
        sprites: Sprites,
    ) -> None:
        super().__init__(master, background=theme.PAGE)
        self.draft = draft
        self.scale = scale
        self.title(draft.title.title())
        self.resizable(False, False)
        self.transient(master)  # type: ignore[arg-type]
        height = dialog_height(draft)
        self.canvas = tk.Canvas(
            self,
            width=round(DIALOG_WIDTH * scale),
            height=round(height * scale),
            background=theme.FACE_OUTPUT[1],
            highlightthickness=0,
        )
        self.canvas.pack()
        self.painter = Painter(self.canvas, scale, fonts, sprites)
        self._cancel_box: tuple[float, float, float, float] | None = None
        self.draw(height)

        self.bind("<Escape>", lambda _e: self.close())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.canvas.bind("<ButtonRelease-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self._centre_over(master)
        self.grab_set()
        self.focus_set()

    def close(self) -> None:
        self.grab_release()
        parent = self.master
        self.destroy()
        parent.focus_set()

    def _centre_over(self, master: tk.Misc) -> None:
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + max(0, (master.winfo_height() - h) // 3)
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    # -- input -----------------------------------------------------------------------

    def _over_cancel(self, event: tk.Event) -> bool:
        if self._cancel_box is None:
            return False
        x0, y0, x1, y1 = self._cancel_box
        x, y = event.x / self.scale, event.y / self.scale
        return x0 <= x < x1 and y0 <= y < y1

    def _on_click(self, event: tk.Event) -> None:
        if self._over_cancel(event):
            self.close()

    def _on_motion(self, event: tk.Event) -> None:
        self.canvas.configure(cursor="hand2" if self._over_cancel(event) else "")

    # -- drawing ---------------------------------------------------------------------

    def draw(self, height: float) -> None:
        p, d = self.painter, self.draft
        p.gradient_v(0, 0, DIALOG_WIDTH, height, *theme.FACE_OUTPUT)
        hex_colour = theme.PASTELS[d.colour]

        # Header: kicker and title on the left, language code and colour bar on the right.
        p.text(PAD, 26, d.kicker, "caption", 10, KICKER_COLOUR, bold=True, spacing=0.22)
        p.text(PAD, 49, d.title, "logo", 18, theme.TEXT_OUTPUT, spacing=0.08)
        box_w = p.text_width(d.code, "mono", 38) + 24
        bar_x = DIALOG_WIDTH - PAD - 8
        box_x = bar_x - 12 - box_w
        p.box(box_x, 20, box_x + box_w, 74, theme.DISPLAY_BG, 4, "#000000", 2)
        p.text(box_x + 12, 47, d.code, "mono", 38, CODE_COLOUR, glow=theme.DISPLAY_BG)
        p.box(bar_x, 20, bar_x + 8, 74, hex_colour, 2)
        for i, name in enumerate(theme.CHANNEL_COLOUR_NAMES):
            p.rect(DIALOG_WIDTH * i / 6, 94, DIALOG_WIDTH * (i + 1) / 6, 98, theme.PASTELS[name])

        width = DIALOG_WIDTH - 2 * PAD
        y = 98 + PAD

        y = self._field(
            y,
            "TARGET LANGUAGE",
            width,
            f"{d.code} · {LANGUAGES[d.code][0]}",
            "mono",
            18,
            CODE_COLOUR,
            0.04,
            chevron=True,
        )
        y += FIELD_GAP
        y = self._field(y, "LABEL", width, d.label, "logo", 15, theme.TEXT_OUTPUT, 0.06)
        y += FIELD_GAP

        y = self._models(y, width)
        y += FIELD_GAP

        gap = 12
        col = (width - 2 * gap) / 3
        self._field(
            y,
            "OUTPUT DEVICE",
            2 * col + gap,
            d.device,
            "mono",
            16,
            theme.TEXT_BUTTON_DARK,
            0,
            chevron=True,
        )
        y = self._field(
            y,
            "CHANNEL",
            col,
            f"CH {d.channel}",
            "mono",
            16,
            theme.TEXT_BUTTON_DARK,
            0,
            chevron=True,
            x=PAD + 2 * col + 2 * gap,
        )
        y += FIELD_GAP

        self._swatches(y)
        footer_top = height - 77
        self._footer(footer_top, height)

    def _label(self, x: float, y: float, text: str) -> None:
        self.painter.text(
            x, y + LABEL_H / 2, text, "caption", 10, LABEL_COLOUR, bold=True, spacing=0.22
        )

    def _field(
        self,
        y: float,
        label: str,
        width: float,
        value: str,
        role: str,
        size: float,
        colour: str,
        spacing: float,
        *,
        chevron: bool = False,
        x: float = PAD,
    ) -> float:
        """A labelled inset well. Returns the y just below it."""
        p = self.painter
        self._label(x, y, label)
        top = y + LABEL_H + 8
        p.box(x, top, x + width, top + CONTROL_H, theme.DISPLAY_BG, 4, "#000000", 2)
        p.text(x + 16, top + CONTROL_H / 2, value, role, size, colour, spacing=spacing)
        if chevron:
            cx, cy = x + width - 22, top + CONTROL_H / 2
            p.cv.create_polygon(
                p.p(cx - 5),
                p.p(cy - 2.5),
                p.p(cx + 5),
                p.p(cy - 2.5),
                p.p(cx),
                p.p(cy + 3.5),
                fill=theme.TEXT_SCALE,
                outline="",
            )
        return top + CONTROL_H

    def _models(self, y: float, width: float) -> float:
        p, d = self.painter, self.draft
        self._label(PAD, y, "TRANSLATION MODEL")
        top = y + LABEL_H + 8 + 8
        p.box(PAD, top + 2, PAD + width, top + CONTROL_H + 2, "#000000", 3)
        p.box(PAD, top, PAD + width, top + CONTROL_H, "#000000", 3)
        seg_w = (width - 2) / 3
        hex_colour = d.colour
        for i, (key, label) in enumerate(MODEL_LABELS.items()):
            on = key == d.model
            x0 = PAD + 1 + i * seg_w
            face = "#d6cfbd" if on else theme.BUTTON_DARK_FACE
            fg = theme.INK if on else theme.TEXT_BUTTON_DARK
            right_edge = x0 + seg_w - (1 if i < 2 else 0)
            p.rect(x0, top + 1, right_edge, top + CONTROL_H - 1, face)
            if on:
                p.rect(x0, top + 1, right_edge, top + 2, "#e4ded0")
            text_w = p.spaced_width(label, "caption", 11, 0.14, bold=True)
            left = x0 + (seg_w - (8 + 8 + text_w)) / 2
            cy = top + CONTROL_H / 2
            p.image(f"led_{hex_colour}" if on else "led_off", left + 4, cy)
            p.text(left + 16, cy, label, "caption", 11, fg, bold=True, spacing=0.14)
        bottom = top + CONTROL_H
        if d.model == "pass":
            p.text(PAD, bottom + 8 + 6.5, PASS_NOTE, "caption", 13, theme.TEXT_ROUTE)
            bottom += 21
        return bottom

    def _swatches(self, y: float) -> float:
        p, d = self.painter, self.draft
        self._label(PAD, y, "CHANNEL COLOUR")
        top = y + LABEL_H + 8
        for i, name in enumerate(theme.CHANNEL_COLOUR_NAMES):
            x0 = PAD + i * 54
            if name == d.colour:
                p.box(x0 - 3, top - 3, x0 + 47, top + 47, theme.IVORY, 6)
            p.box(x0, top, x0 + 44, top + 44, theme.PASTELS[name], 4, "#000000", 2)
        return top + 44

    def _footer(self, top: float, height: float) -> None:
        p, d = self.painter, self.draft
        p.rect(0, top, DIALOG_WIDTH, height, theme.FACE_BLANK)
        p.rect(0, top, DIALOG_WIDTH, top + 1, "#050505")
        by = top + 1 + 16
        if d.mode == "edit":
            label = "REMOVE LANGUAGE"
            w = p.spaced_width(label, "caption", 11, 0.18, bold=True) + 34
            p.box(PAD, by, PAD + w, by + 44, "#6a2a24", 3)
            p.box(PAD + 1, by + 1, PAD + w - 1, by + 43, theme.FACE_BLANK, 2)
            p.text(PAD + 17, by + 22, label, "caption", 11, "#ff8a7a", bold=True, spacing=0.18)

        confirm_w = p.spaced_width(d.confirm_label, "caption", 11, 0.18, bold=True) + 42
        cancel_w = p.spaced_width("CANCEL", "caption", 11, 0.18, bold=True) + 38
        right = DIALOG_WIDTH - PAD
        confirm_x = right - confirm_w
        cancel_x = confirm_x - 10 - cancel_w
        draw_button(
            p,
            cancel_x,
            by,
            "CANCEL",
            face=theme.BUTTON_DARK_FACE,
            fg=theme.TEXT_BUTTON_DARK,
            shadow="#000000",
            border=theme.BUTTON_DARK_BORDER,
            width=cancel_w,
            spacing=0.18,
        )
        draw_button(
            p,
            confirm_x,
            by,
            d.confirm_label,
            face="#d6cfbd",
            fg=theme.INK,
            shadow="#000000",
            border="#000000",
            highlight="#e4ded0",
            width=confirm_w,
            spacing=0.18,
        )
        self._cancel_box = (cancel_x, by, cancel_x + cancel_w, by + 44)
