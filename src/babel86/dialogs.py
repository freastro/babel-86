"""The language setup dialog, drawn on its own canvas to match `OutputSetup.dc.html`.

The fields are canvas drawings, except the Label, which is a restyled `tk.Entry` so Tk
handles typing, the cursor, IME input and complex scripts. Dropdowns open a borderless
popup list. Every rule about what the fields may hold lives in `state`; this module only
draws the draft and routes pointer and key input to those rules.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from babel86 import devices, languages, state, theme
from babel86.assets import Sprites
from babel86.fonts import FontBook
from babel86.rack import FocusKey, Hit
from babel86.state import MODEL_LABELS, LanguageDraft, RackState
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
IN_RACK = "IN RACK"
DROPDOWNS = ("language", "device", "channel")
BUTTONS = ("remove", "cancel", "confirm")


def clash_note(unit: state.LanguageUnit) -> str:
    return f"CH {unit.channel} is also used by {unit.code} · {unit.name}"


def dialog_height(draft: LanguageDraft, clash: bool = False) -> float:
    """Total logical height, which grows by one note line each for Pass-thru and a clash."""
    return theme.DIALOG_HEADER_HEIGHT + _body_height(draft, clash) + theme.DIALOG_FOOTER_HEIGHT


def _body_height(draft: LanguageDraft, clash: bool = False) -> float:
    notes = (draft.model == "pass") + clash
    # padding, language, label, model, device row, colours, padding, plus the gaps between
    return (
        PAD
        + FIELD_H
        + FIELD_H
        + MODEL_H
        + FIELD_H
        + SWATCH_BLOCK_H
        + PAD
        + 4 * FIELD_GAP
        + notes * theme.DIALOG_NOTE_HEIGHT
    )


@dataclass(frozen=True)
class Row:
    value: object
    text: str
    note: str | None = None  # a dim tag on the right, such as IN RACK


class Dropdown(tk.Toplevel):
    """A borderless popup list. Click, or Up/Down then Enter or Space, picks a row.

    Esc, Tab or a click outside closes it without picking. It holds the grab while open,
    so the dialog underneath ignores keys and clicks until it closes.
    """

    def __init__(
        self,
        master: tk.Misc,
        rows: list[Row],
        selected: int,
        x: int,
        y: int,
        width: float,
        scale: float,
        fonts: FontBook,
        sprites: Sprites,
        on_pick: Callable[[object], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(master, background=theme.BLACK)
        self.overrideredirect(True)
        self.rows = rows
        self.scale = scale
        self.highlight = max(0, selected)
        self.selected = selected
        self.top = 0
        self.visible = min(len(rows), theme.DROPDOWN_MAX_ROWS)
        self.width = width
        self.on_pick = on_pick
        self.on_close = on_close
        height = self.visible * theme.DROPDOWN_ROW_HEIGHT + 4
        self.canvas = tk.Canvas(
            self,
            width=round(width * scale),
            height=round(height * scale),
            background=theme.DISPLAY_BG,
            highlightthickness=0,
        )
        self.canvas.pack()
        self.painter = Painter(self.canvas, scale, fonts, sprites)
        self._scroll_into_view()
        self.render()

        # Open below the field, or above it when the screen runs out.
        px_h = round(height * scale)
        if y + px_h > self.winfo_screenheight():
            y = max(0, y - px_h - round((CONTROL_H + 4) * scale))
        self.geometry(f"+{x}+{y}")

        self.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<MouseWheel>", lambda e: self.scroll(-1 if e.delta > 0 else 1))
        self.canvas.bind("<Button-4>", lambda _e: self.scroll(-1))
        self.canvas.bind("<Button-5>", lambda _e: self.scroll(1))
        for keysym, step in (("Up", -1), ("Down", 1), ("Prior", -self.visible)):
            self.bind(f"<{keysym}>", lambda _e, s=step: self.move(s))
        self.bind("<Next>", lambda _e: self.move(self.visible))
        self.bind("<Home>", lambda _e: self.move(-len(self.rows)))
        self.bind("<End>", lambda _e: self.move(len(self.rows)))
        for keysym in ("Return", "KP_Enter", "space"):
            self.bind(f"<{keysym}>", lambda _e: self.pick(self.highlight))
        self.bind("<Escape>", lambda _e: self.close())
        self.bind("<Tab>", lambda _e: self.close())
        self.update_idletasks()
        self.grab_set()
        self.focus_force()

    # -- behaviour ---------------------------------------------------------------------

    def move(self, step: int) -> str:
        self.highlight = max(0, min(len(self.rows) - 1, self.highlight + step))
        self._scroll_into_view()
        self.render()
        return "break"

    def scroll(self, step: int) -> None:
        self.top = max(0, min(len(self.rows) - self.visible, self.top + step))
        self.render()

    def pick(self, index: int) -> str:
        if 0 <= index < len(self.rows):
            value = self.rows[index].value
            self.close()
            self.on_pick(value)
        return "break"

    def close(self) -> str:
        if self.winfo_exists():
            self.grab_release()
            self.destroy()
            self.on_close()
        return "break"

    def _scroll_into_view(self) -> None:
        if self.highlight < self.top:
            self.top = self.highlight
        elif self.highlight >= self.top + self.visible:
            self.top = self.highlight - self.visible + 1

    def row_at(self, y_px: int) -> int | None:
        row = int((y_px / self.scale - 2) // theme.DROPDOWN_ROW_HEIGHT)
        if 0 <= row < self.visible:
            return self.top + row
        return None

    def _inside(self, event: tk.Event) -> bool:
        x, y = event.x_root - self.winfo_rootx(), event.y_root - self.winfo_rooty()
        return 0 <= x < self.winfo_width() and 0 <= y < self.winfo_height()

    def _on_press(self, event: tk.Event) -> None:
        if not self._inside(event):
            self.close()

    def _on_release(self, event: tk.Event) -> None:
        index = self.row_at(event.y)
        if index is not None:
            self.pick(index)

    def _on_motion(self, event: tk.Event) -> None:
        index = self.row_at(event.y)
        if index is not None and index != self.highlight:
            self.highlight = index
            self.render()

    # -- drawing ---------------------------------------------------------------------

    def render(self) -> None:
        p, cv = self.painter, self.canvas
        cv.delete("all")
        row_h = theme.DROPDOWN_ROW_HEIGHT
        height = self.visible * row_h + 4
        p.box(0, 0, self.width, height, theme.DISPLAY_BG, 4, theme.BLACK, 2)
        for slot in range(self.visible):
            index = self.top + slot
            row = self.rows[index]
            y0 = 2 + slot * row_h
            if index == self.highlight:
                p.rect(2, y0, self.width - 2, y0 + row_h, theme.DROPDOWN_HIGHLIGHT)
            colour = CODE_COLOUR if index == self.selected else theme.TEXT_BUTTON_DARK
            p.text(16, y0 + row_h / 2, row.text, "mono", 16, colour)
            if row.note:
                p.text(
                    self.width - 22,
                    y0 + row_h / 2,
                    row.note,
                    "caption",
                    10,
                    theme.TEXT_SCALE,
                    bold=True,
                    anchor="e",
                    spacing=0.18,
                )
        if len(self.rows) > self.visible:
            track = height - 8
            thumb = max(16, track * self.visible / len(self.rows))
            y = 4 + (track - thumb) * self.top / (len(self.rows) - self.visible)
            p.box(self.width - 8, y, self.width - 4, y + thumb, theme.TEXT_SCALE, 2)


class LanguageDialog(tk.Toplevel):
    """The modal Add/Edit language dialog. Esc cancels; Enter confirms.

    `on_confirm(draft)` runs when Add to rack or Save is pressed, `on_remove(index)` when
    the unit is removed, and `on_close` once the dialog is gone, whatever closed it.
    """

    def __init__(
        self,
        master: tk.Misc,
        draft: LanguageDraft,
        scale: float,
        fonts: FontBook,
        sprites: Sprites,
        on_close: Callable[[], None] | None = None,
        *,
        rack: RackState | None = None,
        on_confirm: Callable[[LanguageDraft], None] | None = None,
        on_remove: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(master, background=theme.PAGE)
        self.draft = draft
        self.rack = rack if rack is not None else RackState()
        self.scale = scale
        self.fonts = fonts
        self.sprites = sprites
        self.on_close = on_close
        self.on_confirm = on_confirm
        self.on_remove = on_remove
        self.hits: list[Hit] = []
        self.focus_key: FocusKey | None = ("language", None)
        self.show_ring = False
        self.confirm_remove = False
        self.popup: Dropdown | None = None
        self._height = 0.0
        self._syncing = False

        self.title(draft.title.title())
        self.resizable(False, False)
        self.transient(master)  # type: ignore[arg-type]
        self.canvas = tk.Canvas(
            self,
            width=round(DIALOG_WIDTH * scale),
            background=theme.FACE_OUTPUT[1],
            highlightthickness=0,
            takefocus=True,
        )
        self.canvas.pack()
        self.painter = Painter(self.canvas, scale, fonts, sprites)

        self.label_var = tk.StringVar(self, value=draft.label)
        self.label_var.trace_add("write", self._on_label_typed)
        self.entry = tk.Entry(
            self.canvas,
            textvariable=self.label_var,
            font=fonts.get("logo", 15),
            background=theme.DISPLAY_BG,
            foreground=theme.TEXT_OUTPUT,
            insertbackground=theme.TEXT_OUTPUT,
            selectbackground=theme.BLUE,
            selectforeground=theme.IVORY,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        self.entry.bind("<FocusIn>", self._on_entry_focus)
        self.render()

        self.bind("<Escape>", self._on_escape)
        for keysym in ("Return", "KP_Enter"):
            self.bind(f"<{keysym}>", self._on_enter)
        self.bind("<KeyPress-space>", self._on_space)
        self.bind("<Tab>", lambda _e: self.move_focus(1))
        self.bind("<Shift-Tab>", lambda _e: self.move_focus(-1))
        if self.tk.call("tk", "windowingsystem") == "x11":
            self.bind("<ISO_Left_Tab>", lambda _e: self.move_focus(-1))
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.canvas.bind("<ButtonRelease-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self._centre_over(master)
        self.grab_set()
        self.canvas.focus_set()

    # -- lifecycle -------------------------------------------------------------------

    def close(self) -> None:
        if not self.winfo_exists():
            return
        if self.popup is not None and self.popup.winfo_exists():
            self.popup.destroy()
        self.grab_release()
        self.destroy()
        if self.on_close is not None:
            self.on_close()

    def confirm(self) -> None:
        if self.on_confirm is not None:
            self.on_confirm(self.draft)
        self.close()

    def press_remove(self) -> None:
        """Live (power on): the first press asks, the second removes. Off: one press."""
        if self.draft.index is None:
            return
        if self.rack.power and not self.confirm_remove:
            self.confirm_remove = True
            self.render()
            return
        if self.on_remove is not None:
            self.on_remove(self.draft.index)
        self.close()

    def _centre_over(self, master: tk.Misc) -> None:
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + max(0, (master.winfo_height() - h) // 3)
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    # -- focus -----------------------------------------------------------------------

    def focus_hit(self) -> Hit | None:
        return next((h for h in self.hits if h.key == self.focus_key), None)

    def set_focus(self, key: FocusKey | None) -> None:
        if key != ("remove", None) and self.confirm_remove:
            self.confirm_remove = False
        self.focus_key = key
        if key == ("label", None):
            self.entry.focus_set()
        elif self.focus_get() is not self.canvas:
            self.canvas.focus_set()
        self.render()

    def move_focus(self, step: int) -> str:
        """Tab and Shift+Tab cycle through the dialog's controls only: focus stays inside."""
        keys = [h.key for h in self.hits]
        if self.focus_key in keys:
            i = (keys.index(self.focus_key) + step) % len(keys)
        else:
            i = 0 if step > 0 else len(keys) - 1
        self.show_ring = True
        self.set_focus(keys[i])
        return "break"

    def _on_entry_focus(self, _event: tk.Event) -> None:
        if self.focus_key != ("label", None):
            self.set_focus(("label", None))

    # -- input -----------------------------------------------------------------------

    def _hit_at(self, event: tk.Event) -> Hit | None:
        x, y = event.x / self.scale, event.y / self.scale
        return next((h for h in reversed(self.hits) if h.contains(x, y)), None)

    def _on_click(self, event: tk.Event) -> None:
        hit = self._hit_at(event)
        if hit is None:
            return
        self.show_ring = False
        self.set_focus(hit.key)
        self.activate(hit)

    def _on_motion(self, event: tk.Event) -> None:
        self.canvas.configure(cursor="hand2" if self._hit_at(event) else "")

    def _on_escape(self, _event: tk.Event) -> str:
        if self.confirm_remove:
            self.confirm_remove = False
            self.render()
        else:
            self.close()
        return "break"

    def _on_enter(self, _event: tk.Event) -> str:
        """Enter opens a focused dropdown or presses a focused footer key; else it confirms."""
        hit = self.focus_hit()
        if hit is not None and hit.kind in DROPDOWNS + BUTTONS:
            self.show_ring = True
            self.activate(hit)
        else:
            self.confirm()
        return "break"

    def _on_space(self, _event: tk.Event) -> str | None:
        if self.focus_get() is self.entry:
            return None  # a space typed in the label
        hit = self.focus_hit()
        if hit is not None:
            self.show_ring = True
            self.activate(hit)
        return "break"

    def activate(self, hit: Hit) -> None:
        draft = self.draft
        if hit.kind in DROPDOWNS:
            self.open_dropdown(hit)
        elif hit.kind == "label":
            self.entry.focus_set()
        elif hit.kind == "model":
            state.set_model(self.rack, draft, hit.arg)  # type: ignore[arg-type]
            self._sync_label()
            self.render()
        elif hit.kind == "swatch":
            draft.colour = hit.arg  # type: ignore[assignment]
            self.render()
        elif hit.kind == "remove":
            self.press_remove()
        elif hit.kind == "cancel":
            self.close()
        elif hit.kind == "confirm":
            self.confirm()

    def _on_label_typed(self, *_args: object) -> None:
        if self._syncing:
            return
        text = self.label_var.get()
        kept = state.set_label(self.draft, text)
        if kept != text:  # a paste longer than 24 code points is cut off
            self._syncing = True
            self.label_var.set(kept)
            self._syncing = False
            self.entry.icursor("end")

    def _sync_label(self) -> None:
        """Show an auto-filled label in the entry without marking it as typed."""
        if self.label_var.get() != self.draft.label:
            self._syncing = True
            self.label_var.set(self.draft.label)
            self._syncing = False

    # -- dropdowns -------------------------------------------------------------------

    def dropdown_rows(self, kind: str) -> tuple[list[Row], int]:
        """The rows a dropdown offers and the index of the current choice."""
        draft = self.draft
        if kind == "language":
            langs = languages.for_model(draft.model)
            rows = [
                Row(
                    lang.tag,
                    f"{lang.code2} · {lang.native}",
                    IN_RACK if state.in_rack(self.rack, draft, lang.tag) else None,
                )
                for lang in langs
            ]
            current = draft.language
        elif kind == "device":
            outputs = devices.list_outputs()
            rows = [Row(d, d.name) for d in outputs]
            if devices.find(draft.device_id) is None:
                rows.insert(0, Row(None, draft.device_label))
            current = next((d for d in outputs if d.id == draft.device_id), None)
        else:
            rows = [Row(n, f"CH {n}") for n in range(1, state.channel_count(draft) + 1)]
            current = draft.channel
        selected = next((i for i, r in enumerate(rows) if r.value == current), 0)
        return rows, selected

    def open_dropdown(self, hit: Hit) -> None:
        if self.popup is not None and self.popup.winfo_exists():
            return
        rows, selected = self.dropdown_rows(hit.kind)
        x = self.canvas.winfo_rootx() + round(hit.x0 * self.scale)
        y = self.canvas.winfo_rooty() + round((hit.y1 + 4) * self.scale)
        self.popup = Dropdown(
            self,
            rows,
            selected,
            x,
            y,
            hit.x1 - hit.x0,
            self.scale,
            self.fonts,
            self.sprites,
            on_pick=lambda value: self._picked(hit.kind, value),
            on_close=self._popup_closed,
        )

    def _popup_closed(self) -> None:
        self.popup = None
        if self.winfo_exists():
            self.grab_set()
            self.canvas.focus_set()

    def _picked(self, kind: str, value: object) -> None:
        draft = self.draft
        if kind == "language":
            state.set_language(draft, value)  # type: ignore[arg-type]
            self._sync_label()
        elif kind == "device" and isinstance(value, devices.OutputDevice):
            state.set_device(draft, value)
        elif kind == "channel":
            draft.channel = value  # type: ignore[assignment]
        self.render()

    # -- drawing ---------------------------------------------------------------------

    def render(self) -> None:
        clash = state.channel_clash(self.rack, self.draft)
        height = dialog_height(self.draft, clash is not None)
        if height != self._height:
            self._height = height
            self.canvas.configure(height=round(height * self.scale))
        self.canvas.delete("all")
        self.hits = []
        self.draw(height, clash)
        hit = self.focus_hit()
        if hit is not None and (self.show_ring or hit.kind == "label"):
            g = theme.FOCUS_RING_GAP_SWATCH if hit.kind == "swatch" else theme.FOCUS_RING_GAP
            colour = theme.FOCUS_RING if self.show_ring else theme.BUTTON_DARK_BORDER
            self.painter.outline(
                hit.x0 - g, hit.y0 - g, hit.x1 + g, hit.y1 + g, colour, theme.FOCUS_RING_WIDTH
            )

    def draw(self, height: float, clash: state.LanguageUnit | None = None) -> None:
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
            f"{draft.code} · {draft.native}",
            "mono",
            18,
            CODE_COLOUR,
            0,  # native names may be any script, so no letter-spacing
            kind="language",
        )
        y += FIELD_GAP
        y = self._field(y, "LABEL", width, "", "logo", 15, theme.TEXT_OUTPUT, 0.06, kind="label")
        self.canvas.create_window(
            painter.p(PAD + 16),
            painter.p(y - CONTROL_H / 2),
            window=self.entry,
            anchor="w",
            width=painter.p(width - 32),
        )
        y += FIELD_GAP

        y = self._models(y, width)
        y += FIELD_GAP

        gap = theme.DIALOG_COLUMN_GAP
        col = (width - 2 * gap) / 3
        self._field(
            y,
            "OUTPUT DEVICE",
            2 * col + gap,
            draft.device_label,
            "mono",
            16,
            theme.TEXT_BUTTON_DARK,
            0,
            kind="device",
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
            kind="channel",
            x=PAD + 2 * col + 2 * gap,
        )
        if clash is not None:
            painter.text(PAD, y + 8 + 6.5, clash_note(clash), "caption", 13, theme.DIALOG_NOTE_WARN)
            y += theme.DIALOG_NOTE_HEIGHT
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
        kind: str,
        x: float = PAD,
    ) -> float:
        """A labelled inset well, with a chevron when it is a dropdown. Returns its bottom."""
        painter = self.painter
        self._label(x, y, label)
        top = y + LABEL_H + LABEL_GAP
        painter.box(x, top, x + width, top + CONTROL_H, theme.DISPLAY_BG, 4, theme.BLACK, 2)
        if value:
            painter.text(x + 16, top + CONTROL_H / 2, value, role, size, colour, spacing=spacing)
        if kind in DROPDOWNS:
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
        self.hits.append(Hit(x, top, x + width, top + CONTROL_H, kind))
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
            self.hits.append(Hit(x0, top, right_edge, top + CONTROL_H, "model", key))
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
            self.hits.append(Hit(x0, top, x0 + size, top + size, "swatch", name))
        return top + size

    def _footer(self, top: float, height: float) -> None:
        painter, draft = self.painter, self.draft
        painter.rect(0, top, DIALOG_WIDTH, height, theme.FACE_BLANK)
        painter.rect(0, top, DIALOG_WIDTH, top + 1, theme.EDGE_OUTPUT[1])
        by = top + 1 + 16
        key_h = theme.BUTTON_HEIGHT
        if draft.mode == "edit":
            label = "CONFIRM REMOVE" if self.confirm_remove else "REMOVE LANGUAGE"
            w = painter.spaced_width("REMOVE LANGUAGE", "caption", 11, 0.18, bold=True) + 34
            if self.confirm_remove:
                painter.box(PAD, by, PAD + w, by + key_h, theme.REMOVE_CONFIRM_FACE, 3)
                fg = theme.INK
            else:
                painter.box(PAD, by, PAD + w, by + key_h, theme.REMOVE_BORDER, 3)
                painter.box(PAD + 1, by + 1, PAD + w - 1, by + key_h - 1, theme.FACE_BLANK, 2)
                fg = theme.REMOVE_TEXT
            painter.text(
                PAD + 17, by + key_h / 2, label, "caption", 11, fg, bold=True, spacing=0.18
            )
            self.hits.append(Hit(PAD, by, PAD + w, by + key_h, "remove"))

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
        self.hits.append(Hit(cancel_x, by, cancel_x + cancel_w, by + key_h, "cancel"))
        self.hits.append(Hit(confirm_x, by, confirm_x + confirm_w, by + key_h, "confirm"))
