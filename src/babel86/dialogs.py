"""The language setup dialog, drawn on its own canvas to match `OutputSetup.dc.html`.

Milestone 1 shows it display-only: Cancel and Esc close it, and every other control is
inert. Working fields arrive with the persistence milestone.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from babel86 import theme
from babel86.assets import Sprites
from babel86.fonts import FontBook
from babel86.state import LANGUAGES, MODEL_LABELS, LanguageDraft
from babel86.widgets.button import draw_button
from babel86.widgets.common import Painter

DIALOG_WIDTH = theme.DIALOG_WIDTH
PAD = theme.DIALOG_PAD
FIELD_GAP = theme.DIALOG_FIELD_GAP
CONTROL_H = theme.DIALOG_CONTROL_HEIGHT
LABEL_H = theme.DIALOG_LABEL_HEIGHT
LABEL_GAP = theme.DIALOG_LABEL_GAP
FIELD_H = LABEL_H + LABEL_GAP + CONTROL_H  # a label above a well
MODEL_H = FIELD_H + 8  # the model selector sits 8 px lower than a plain well
SWATCH_BLOCK_H = LABEL_H + LABEL_GAP + theme.DIALOG_SWATCH
LABEL_COLOUR = theme.TEXT_ROUTE
KICKER_COLOUR = theme.TEXT_SCALE
CODE_COLOUR = theme.DISPLAYS["vfd"]
PASS_NOTE = "Pass-thru sends the original speech to this output without translating it."


def dialog_height(draft: LanguageDraft) -> float:
    """Total logical height, which grows by one note line for Pass-thru."""
    return theme.DIALOG_HEADER_HEIGHT + _body_height(draft) + theme.DIALOG_FOOTER_HEIGHT


def _body_height(draft: LanguageDraft) -> float:
    note = theme.DIALOG_NOTE_HEIGHT if draft.model == "pass" else 0
    # padding, language, label, model, device row, colours, padding, plus the gaps between
    return PAD + FIELD_H + FIELD_H + MODEL_H + note + FIELD_H + SWATCH_BLOCK_H + PAD + 4 * FIELD_GAP


class LanguageDialog(tk.Toplevel):
    """A modal, display-only dialog. Close it with Cancel, Esc or the window's close button.

    `on_close` runs once the dialog is gone, so the owner can undo whatever it did to open it.
    """

    def __init__(
        self,
        master: tk.Misc,
        draft: LanguageDraft,
        scale: float,
        fonts: FontBook,
        sprites: Sprites,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, background=theme.PAGE)
        self.draft = draft
        self.scale = scale
        self.on_close = on_close
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
        self.destroy()
        if self.on_close is not None:
            self.on_close()

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
        painter, draft = self.painter, self.draft
        painter.gradient_v(0, 0, DIALOG_WIDTH, height, *theme.FACE_OUTPUT)
        colour_hex = theme.PASTELS[draft.colour]

        # Header: kicker and title on the left, language code and colour bar on the right.
        code_top, code_bottom = theme.DIALOG_CODE_TOP, theme.DIALOG_CODE_BOTTOM
        painter.text(PAD, 26, draft.kicker, "caption", 10, KICKER_COLOUR, bold=True, spacing=0.22)
        painter.text(PAD, 49, draft.title, "logo", 18, theme.TEXT_OUTPUT, spacing=0.08)
        box_w = painter.text_width(draft.code, "mono", 38) + 24
        bar_x = DIALOG_WIDTH - PAD - 8
        box_x = bar_x - 12 - box_w
        painter.box(
            box_x, code_top, box_x + box_w, code_bottom, theme.DISPLAY_BG, 4, theme.BLACK, 2
        )
        painter.text(box_x + 12, 47, draft.code, "mono", 38, CODE_COLOUR, glow=theme.DISPLAY_BG)
        painter.box(bar_x, code_top, bar_x + 8, code_bottom, colour_hex, 2)
        strip_top = theme.DIALOG_STRIP_TOP
        strip_bottom = strip_top + theme.DIALOG_STRIP_HEIGHT
        for i, name in enumerate(theme.CHANNEL_COLOUR_NAMES):
            painter.rect(
                DIALOG_WIDTH * i / 6,
                strip_top,
                DIALOG_WIDTH * (i + 1) / 6,
                strip_bottom,
                theme.PASTELS[name],
            )

        width = DIALOG_WIDTH - 2 * PAD
        y = theme.DIALOG_HEADER_HEIGHT + PAD

        y = self._field(
            y,
            "TARGET LANGUAGE",
            width,
            f"{draft.code} · {LANGUAGES[draft.code][0]}",
            "mono",
            18,
            CODE_COLOUR,
            0.04,
            chevron=True,
        )
        y += FIELD_GAP
        y = self._field(y, "LABEL", width, draft.label, "logo", 15, theme.TEXT_OUTPUT, 0.06)
        y += FIELD_GAP

        y = self._models(y, width)
        y += FIELD_GAP

        gap = theme.DIALOG_COLUMN_GAP
        col = (width - 2 * gap) / 3
        self._field(
            y,
            "OUTPUT DEVICE",
            2 * col + gap,
            draft.device,
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
            f"CH {draft.channel}",
            "mono",
            16,
            theme.TEXT_BUTTON_DARK,
            0,
            chevron=True,
            x=PAD + 2 * col + 2 * gap,
        )
        y += FIELD_GAP

        self._swatches(y)
        self._footer(height - theme.DIALOG_FOOTER_HEIGHT, height)

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
        painter = self.painter
        self._label(x, y, label)
        top = y + LABEL_H + LABEL_GAP
        painter.box(x, top, x + width, top + CONTROL_H, theme.DISPLAY_BG, 4, theme.BLACK, 2)
        painter.text(x + 16, top + CONTROL_H / 2, value, role, size, colour, spacing=spacing)
        if chevron:
            cx, cy = x + width - 22, top + CONTROL_H / 2
            painter.cv.create_polygon(
                painter.p(cx - 5),
                painter.p(cy - 2.5),
                painter.p(cx + 5),
                painter.p(cy - 2.5),
                painter.p(cx),
                painter.p(cy + 3.5),
                fill=theme.TEXT_SCALE,
                outline="",
            )
        return top + CONTROL_H

    def _models(self, y: float, width: float) -> float:
        painter, draft = self.painter, self.draft
        self._label(PAD, y, "TRANSLATION MODEL")
        top = y + LABEL_H + 2 * LABEL_GAP
        painter.box(PAD, top + 2, PAD + width, top + CONTROL_H + 2, theme.BLACK, 3)
        painter.box(PAD, top, PAD + width, top + CONTROL_H, theme.BLACK, 3)
        seg_w = (width - 2) / 3
        for i, (key, label) in enumerate(MODEL_LABELS.items()):
            on = key == draft.model
            x0 = PAD + 1 + i * seg_w
            face = theme.BUTTON_CREAM_FACE if on else theme.BUTTON_DARK_FACE
            fg = theme.INK if on else theme.TEXT_BUTTON_DARK
            right_edge = x0 + seg_w - (1 if i < 2 else 0)
            painter.rect(x0, top + 1, right_edge, top + CONTROL_H - 1, face)
            if on:
                painter.rect(x0, top + 1, right_edge, top + 2, theme.BUTTON_CREAM_HIGHLIGHT)
            text_w = painter.spaced_width(label, "caption", 11, 0.14, bold=True)
            left = x0 + (seg_w - (8 + 8 + text_w)) / 2
            cy = top + CONTROL_H / 2
            painter.image(f"led_{draft.colour}" if on else "led_off", left + 4, cy)
            painter.text(left + 16, cy, label, "caption", 11, fg, bold=True, spacing=0.14)
        bottom = top + CONTROL_H
        if draft.model == "pass":
            painter.text(PAD, bottom + 8 + 6.5, PASS_NOTE, "caption", 13, theme.TEXT_ROUTE)
            bottom += theme.DIALOG_NOTE_HEIGHT
        return bottom

    def _swatches(self, y: float) -> float:
        painter, draft = self.painter, self.draft
        self._label(PAD, y, "CHANNEL COLOUR")
        top = y + LABEL_H + LABEL_GAP
        size = theme.DIALOG_SWATCH
        for i, name in enumerate(theme.CHANNEL_COLOUR_NAMES):
            x0 = PAD + i * theme.DIALOG_SWATCH_PITCH
            if name == draft.colour:
                painter.box(x0 - 3, top - 3, x0 + size + 3, top + size + 3, theme.IVORY, 6)
            painter.box(x0, top, x0 + size, top + size, theme.PASTELS[name], 4, theme.BLACK, 2)
        return top + size

    def _footer(self, top: float, height: float) -> None:
        painter, draft = self.painter, self.draft
        painter.rect(0, top, DIALOG_WIDTH, height, theme.FACE_BLANK)
        painter.rect(0, top, DIALOG_WIDTH, top + 1, theme.EDGE_OUTPUT[1])
        by = top + 1 + 16
        key_h = theme.BUTTON_HEIGHT
        if draft.mode == "edit":
            label = "REMOVE LANGUAGE"
            w = painter.spaced_width(label, "caption", 11, 0.18, bold=True) + 34
            painter.box(PAD, by, PAD + w, by + key_h, theme.REMOVE_BORDER, 3)
            painter.box(PAD + 1, by + 1, PAD + w - 1, by + key_h - 1, theme.FACE_BLANK, 2)
            painter.text(
                PAD + 17,
                by + key_h / 2,
                label,
                "caption",
                11,
                theme.REMOVE_TEXT,
                bold=True,
                spacing=0.18,
            )

        confirm_w = painter.spaced_width(draft.confirm_label, "caption", 11, 0.18, bold=True) + 42
        cancel_w = painter.spaced_width("CANCEL", "caption", 11, 0.18, bold=True) + 38
        right = DIALOG_WIDTH - PAD
        confirm_x = right - confirm_w
        cancel_x = confirm_x - theme.DIALOG_KEY_GAP - cancel_w
        draw_button(painter, cancel_x, by, "CANCEL", theme.KEY_DARK, width=cancel_w, spacing=0.18)
        draw_button(
            painter,
            confirm_x,
            by,
            draft.confirm_label,
            theme.KEY_CONFIRM,
            width=confirm_w,
            spacing=0.18,
        )
        self._cancel_box = (cancel_x, by, cancel_x + cancel_w, by + key_h)
