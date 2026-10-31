"""The rack canvas: draws the whole `RackState` and turns pointer and key input into changes.

The canvas is redrawn from state on every change (cheap at this size), so drawing code
never has to patch individual items. Hit regions are recorded in logical pixels during
each draw and looked up when the pointer moves or clicks.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

from babel86 import layout, meters, state, theme
from babel86.assets import Sprites, scrim
from babel86.fonts import FontBook
from babel86.state import LanguageUnit, RackState
from babel86.textfit import ellipsize
from babel86.widgets import knob as knob_widget
from babel86.widgets.button import draw_button, draw_power_icon, draw_tag
from babel86.widgets.common import Painter, blend
from babel86.widgets.ear import draw_ears
from babel86.widgets.knob import draw_knob, knob_rect
from babel86.widgets.meter import draw_meter, meter_height
from babel86.widgets.panels import code_box_width, draw_text_panel, draw_well

SetupHandler = Callable[[str, int | None], None]
KnobKey = tuple[str, ...]  # ("in",) or ("out", unit uid)
FocusKey = tuple[str, object]  # a hit's (kind, arg), stable across redraws

CONTENT_TOP = 1 + theme.UNIT_PADDING_Y  # unit top border, then padding
ROW_TOP = CONTENT_TOP + theme.TAG_HEIGHT + theme.TAG_GAP  # below a section header
ROW_HEIGHT = 2 * theme.BUTTON_HEIGHT + 6  # the tallest row: two stacked 44 px buttons
DISPLAY_WIDTH = theme.COL_CONTROL - 10 - theme.BUTTON_WIDTH


@dataclass(frozen=True)
class Hit:
    x0: float
    y0: float
    x1: float
    y1: float
    kind: str
    arg: object = None

    def contains(self, x: float, y: float) -> bool:
        return self.x0 <= x < self.x1 and self.y0 <= y < self.y1

    @property
    def key(self) -> FocusKey:
        return (self.kind, self.arg)


class RackCanvas(tk.Canvas):
    """Draws the rack and handles its controls. Everything lives in `self.state`."""

    def __init__(
        self,
        master: tk.Misc,
        rack: RackState,
        scale: float,
        fonts: FontBook,
        sprites: Sprites,
        on_setup: SetupHandler | None = None,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, background=theme.PAGE, highlightthickness=0, takefocus=True)
        self.state = rack
        self.scale = scale
        self.painter = Painter(self, scale, fonts, sprites)
        self.on_setup = on_setup
        self.on_change = on_change
        self.hits: list[Hit] = []
        self.focus_key: FocusKey | None = None
        self.show_ring = False  # True after keyboard navigation, False after a click
        self._drag: tuple[KnobKey, int, float] | None = None
        self._pressed: Hit | None = None
        self._render_scheduled = False
        self._dimmed = False
        self._scrim: tuple[int, int, tk.PhotoImage] | None = None

        self.bind("<Configure>", lambda _e: self.invalidate())
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<Double-Button-1>", self._on_double)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Motion>", self._on_motion)
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Button-4>", lambda e: self._wheel(e, 1))
        self.bind("<Button-5>", lambda e: self._wheel(e, -1))
        self.bind("<KeyPress>", self._on_key)
        self.bind("<Tab>", lambda _e: self.move_focus(1))
        self.bind("<Shift-Tab>", lambda _e: self.move_focus(-1))
        if self.tk.call("tk", "windowingsystem") == "x11":
            self.bind("<ISO_Left_Tab>", lambda _e: self.move_focus(-1))

    @property
    def focus_knob(self) -> KnobKey | None:
        if self.focus_key is not None and self.focus_key[0] == "knob":
            return self.focus_key[1]  # type: ignore[return-value]
        return None

    def focus_hit(self) -> Hit | None:
        return next((h for h in self.hits if h.key == self.focus_key), None)

    def move_focus(self, step: int) -> str:
        """Tab and Shift+Tab: the next or previous control in reading order, wrapping."""
        keys = [h.key for h in self.hits]
        if keys:
            if self.focus_key in keys:
                i = (keys.index(self.focus_key) + step) % len(keys)
            else:
                i = 0 if step > 0 else len(keys) - 1
            self.focus_key = keys[i]
            self.show_ring = True
            self.invalidate()
        return "break"

    def _changed(self) -> None:
        if self.on_change is not None:
            self.on_change()

    # -- sizing and drawing --------------------------------------------------------------

    def fit_height(self) -> int:
        """Set the canvas height to fit the current units and return it, in pixels."""
        height = round(layout.content_height(len(self.state.units)) * self.scale)
        self.configure(height=height)
        return height

    def invalidate(self) -> None:
        """Redraw soon; many changes in one event-loop turn cost one redraw."""
        if not self._render_scheduled:
            self._render_scheduled = True
            self.after_idle(self.render)

    def set_dimmed(self, dimmed: bool) -> None:
        """Darken the whole rack, as a modal dialog does, or restore it."""
        if dimmed != self._dimmed:
            self._dimmed = dimmed
            self.invalidate()

    def _draw_scrim(self) -> None:
        width, height = self.winfo_width(), self.winfo_height()
        if self._scrim is None or self._scrim[:2] != (width, height):
            image = scrim(self, width, height, theme.DIALOG_SCRIM_OPACITY)
            self._scrim = (width, height, image)
        self.create_image(0, 0, image=self._scrim[2], anchor="nw")

    def render(self) -> None:
        self._render_scheduled = False
        self.delete("all")
        self.hits = []
        p = self.painter
        n = len(self.state.units)
        width = max(self.winfo_width() / self.scale, 1.0)
        box = layout.rack_box(max(width, theme.MIN_WIDTH), n)
        p.box(box.x, box.y, box.x + box.width, box.y + box.height, theme.RACK, 6)
        cols = layout.columns(box.width)
        tops = [box.y + t for t in layout.unit_tops(n)]
        self._draw_input(box.x, tops[0], cols)
        for i, unit in enumerate(self.state.units):
            self._draw_language(box.x, tops[1 + i], cols, i, unit)
        self._draw_blank(box.x, tops[-1], cols)
        self._draw_focus_ring()
        if self._dimmed:
            self._draw_scrim()
        else:
            self._scrim = None

    def _draw_focus_ring(self) -> None:
        """A gold ring around the focused button; knobs draw their own round ring."""
        hit = self.focus_hit()
        if hit is None or hit.kind == "knob" or not self.show_ring:
            return
        g = theme.FOCUS_RING_GAP
        self.painter.outline(
            hit.x0 - g, hit.y0 - g, hit.x1 + g, hit.y1 + g, theme.FOCUS_RING, theme.FOCUS_RING_WIDTH
        )

    # -- display colours -----------------------------------------------------------------

    def _display_colour(self) -> str:
        return theme.DISPLAYS[self.state.display] if self.state.power else theme.DISPLAY_OFF

    def _glow(self) -> str | None:
        return theme.DISPLAY_BG if self.state.power else None

    # -- input unit ----------------------------------------------------------------------

    def _draw_input(self, x: float, y: float, cols: layout.Columns) -> None:
        p, rack, src = self.painter, self.state, self.state.source
        w, h = cols.unit_width, theme.UNIT_HEIGHT
        top, bottom, divider = theme.EDGE_INPUT
        p.gradient_v(x, y, x + w, y + h, *theme.FACE_INPUT)
        p.rect(x, y, x + w, y + 1, top)
        p.rect(x, y + h - 1, x + w, y + h, bottom)
        draw_ears(p, x, y, w, h, "in", divider)
        p.rect(
            x + theme.EAR_WIDTH,
            y + 1,
            x + theme.EAR_WIDTH + theme.STRIPE_WIDTH,
            y + h - 1,
            theme.BLUE,
        )

        # Column 1: power key, logo, subtitle.
        cx0 = x + cols.identity[0]
        mid = y + h / 2
        p.box(cx0, mid - 24 + 2, cx0 + 48, mid + 24 + 2, theme.BUTTON_INPUT_SHADOW, 6)
        p.box(cx0, mid - 24, cx0 + 48, mid + 24, theme.POWER_FACE, 6, theme.POWER_BORDER, 2)
        p.rect(cx0 + 3, mid - 22, cx0 + 45, mid - 21, theme.POWER_HIGHLIGHT)
        draw_power_icon(p, cx0 + 24, mid, theme.GOLD if rack.power else theme.POWER_OFF_ICON)
        self.hits.append(Hit(cx0, mid - 24, cx0 + 48, mid + 24, "power"))

        lx, lw = cx0 + 64, 196
        ly = mid - 31.5
        p.rect(lx, ly, lx + lw, ly + 7, theme.BLUE)
        for i, name in enumerate(theme.CHANNEL_COLOUR_NAMES):
            p.rect(lx + lw * i / 6, ly + 9, lx + lw * (i + 1) / 6, ly + 12, theme.PASTELS[name])
        p.text(lx, ly + 12 + 5 + 14.5, "BABEL-86", "logo", 26, theme.INK_LOGO, spacing=0.06)
        p.text(
            lx,
            ly + 12 + 5 + 29 + 5 + 6,
            "REAL-TIME SPEECH TRANSLATOR",
            "caption",
            10,
            theme.INK_INPUT_SOFT,
            bold=True,
            spacing=0.22,
        )

        # Column 2: source display and its two keys.
        cx1, cw1 = cols.control
        cx1 += x
        cy = y + CONTENT_TOP
        draw_tag(p, cx1, cy, cw1, "SOURCE", theme.BLUE, theme.IVORY, theme.RULE_INPUT)
        row = y + ROW_TOP
        draw_well(p, cx1, row, DISPLAY_WIDTH, ROW_HEIGHT, theme.DISPLAY_BORDER_INPUT)
        colour, glow = self._display_colour(), self._glow()
        left, right = cx1 + 2 + 14, cx1 + DISPLAY_WIDTH - 2 - 14
        p.text(
            left,
            row + 36.5,
            f"{src.code} {src.language}",
            "mono",
            22,
            colour,
            glow=glow,  # no letter-spacing: the language name may be any script
        )
        p.text(
            right,
            row + 36.5,
            state.source_state_word(rack),
            "mono",
            22,
            colour,
            anchor="e",
            spacing=0.06,
            glow=glow,
        )
        dim = blend(colour, theme.DISPLAY_BG, 0.85)
        p.text(left, row + 62, src.route, "mono", 13, dim)
        p.text(right, row + 62, src.format, "mono", 13, dim, anchor="e")

        bx = cx1 + DISPLAY_WIDTH + 10
        lit = rack.power and src.muted
        draw_button(
            p,
            bx,
            row,
            "MUTE INPUT",
            theme.KEY_INPUT,
            led="led_red" if lit else "led_off",
        )
        self.hits.append(
            Hit(bx, row, bx + theme.BUTTON_WIDTH, row + theme.BUTTON_HEIGHT, "mute_in")
        )
        by = row + theme.BUTTON_HEIGHT + 6
        draw_button(
            p,
            bx,
            by,
            "SETUP",
            theme.KEY_INPUT,
            icon="sliders",
        )
        self.hits.append(Hit(bx, by, bx + theme.BUTTON_WIDTH, by + theme.BUTTON_HEIGHT, "setup_in"))

        # Column 3: gain knob and level meter.
        cx2, cw2 = cols.level
        cx2 += x
        draw_tag(p, cx2, cy, cw2, "INPUT", theme.BLUE, theme.IVORY, theme.RULE_INPUT)
        key: KnobKey = ("in",)
        draw_knob(
            p,
            cx2,
            row,
            src.gain_db,
            output=False,
            cap="blue",
            caption="GAIN",
            scale_colour=theme.INK_INPUT,
            caption_colour=theme.INK_INPUT,
            focused=self.focus_knob == key,
        )
        self.hits.append(Hit(*knob_rect(cx2, row), "knob", key))
        mh = meter_height("in")
        draw_meter(
            p,
            cx2 + 100,
            row + knob_widget.BLOCK_TOTAL_H / 2 - mh / 2,
            cw2 - 100,
            state.input_meter_db(rack),
            "in",
        )

        # Column 4: transcript.
        cx3, cw3 = cols.text
        cx3 += x
        draw_tag(p, cx3, cy, cw3, "TRANSCRIPT", theme.BLUE, theme.IVORY, theme.RULE_INPUT)
        draw_text_panel(
            p,
            cx3,
            row,
            cw3,
            state.hear_line(rack),
            colour=colour,
            size=18,
            border=theme.DISPLAY_BORDER_INPUT,
            glow=glow is not None,
        )

    # -- language units --------------------------------------------------------------------

    def _draw_language(
        self, x: float, y: float, cols: layout.Columns, index: int, unit: LanguageUnit
    ) -> None:
        p, rack = self.painter, self.state
        w, h = cols.unit_width, theme.UNIT_HEIGHT
        top, bottom, divider = theme.EDGE_OUTPUT
        hex_colour = theme.PASTELS[unit.colour]
        p.gradient_v(x, y, x + w, y + h, *theme.FACE_OUTPUT)
        p.rect(x, y, x + w, y + 1, top)
        p.rect(x, y + h - 1, x + w, y + h, bottom)
        draw_ears(p, x, y, w, h, "out", divider)
        p.rect(
            x + theme.EAR_WIDTH,
            y + 1,
            x + theme.EAR_WIDTH + theme.STRIPE_WIDTH,
            y + h - 1,
            hex_colour,
        )

        colour, glow = self._display_colour(), self._glow()
        status = state.unit_status(rack, unit)
        has_error = state.unit_has_error(rack, unit)

        # Column 1: language code, label, model, route.
        cx0, cw0 = cols.identity
        cx0 += x
        mid = y + h / 2
        box_w = code_box_width(p, unit.code)
        p.box(
            cx0,
            mid - 27,
            cx0 + box_w,
            mid + 27,
            theme.DISPLAY_BG,
            4,
            theme.DISPLAY_BORDER_OUTPUT,
            2,
        )
        p.text(cx0 + 12, mid, unit.code, "mono", 38, colour, glow=glow)
        tx = cx0 + box_w + 14
        avail = cw0 - box_w - 14
        top_y = mid - 28
        label = ellipsize(unit.name, lambda s: p.text_width(s, "logo", 16), avail)
        p.text(tx, top_y + 9.5, label, "logo", 16, theme.TEXT_OUTPUT)  # any script: no spacing
        p.text(
            tx,
            top_y + 19 + 5 + 6.5,
            state.MODEL_LABELS[unit.model],
            "caption",
            11,
            theme.TEXT_OUTPUT_SOFT,
            bold=True,
            spacing=0.18,
        )
        p.text(tx, top_y + 19 + 5 + 13 + 5 + 7, unit.route, "mono", 13, theme.TEXT_ROUTE)

        # Column 2: status lamp and the MUTE and SETUP keys.
        cx1, cw1 = cols.control
        cx1 += x
        cy = y + CONTENT_TOP
        band, band_fg = hex_colour, theme.INK
        draw_tag(p, cx1, cy, cw1, "STATUS", band, band_fg, theme.RULE_OUTPUT)
        row = y + ROW_TOP
        lamp = f"lamp_{status}" if rack.power else "lamp_off"
        p.image(lamp, cx1 + 4 + 9, row + ROW_HEIGHT / 2)
        word = theme.STATUS_LABELS[status] if rack.power else "OFF"
        p.text(
            cx1 + 4 + 18 + 14,
            row + ROW_HEIGHT / 2,
            word,
            "mono",
            22,
            theme.TEXT_OUTPUT,
            spacing=0.06,
        )

        bx = cx1 + DISPLAY_WIDTH + 10
        draw_button(
            p,
            bx,
            row,
            "MUTE",
            theme.KEY_MUTE,
            led="led_red" if rack.power and unit.muted else "led_off",
        )
        self.hits.append(
            Hit(bx, row, bx + theme.BUTTON_WIDTH, row + theme.BUTTON_HEIGHT, "mute", unit.uid)
        )
        by = row + theme.BUTTON_HEIGHT + 6
        draw_button(
            p,
            bx,
            by,
            "SETUP",
            theme.KEY_DARK,
            icon="sliders",
        )
        self.hits.append(
            Hit(bx, by, bx + theme.BUTTON_WIDTH, by + theme.BUTTON_HEIGHT, "setup", index)
        )

        # Column 3: level knob and meter.
        cx2, cw2 = cols.level
        cx2 += x
        draw_tag(p, cx2, cy, cw2, "OUTPUT", band, band_fg, theme.RULE_OUTPUT)
        key: KnobKey = ("out", unit.uid)
        draw_knob(
            p,
            cx2,
            row,
            unit.level_db,
            output=True,
            cap=unit.colour,
            caption="LEVEL",
            scale_colour=theme.TEXT_ROUTE,
            caption_colour=theme.TEXT_OUTPUT_SOFT,
            focused=self.focus_knob == key,
        )
        self.hits.append(Hit(*knob_rect(cx2, row), "knob", key))
        mh = meter_height("out")
        draw_meter(
            p,
            cx2 + 100,
            row + knob_widget.BLOCK_TOTAL_H / 2 - mh / 2,
            cw2 - 100,
            state.unit_meter_db(rack, unit),
            "out",
        )

        # Column 4: translation.
        cx3, cw3 = cols.text
        cx3 += x
        draw_tag(p, cx3, cy, cw3, "TRANSLATION", band, band_fg, theme.RULE_OUTPUT)
        text_colour = theme.ERROR_TEXT if has_error else colour
        draw_text_panel(
            p,
            cx3,
            row,
            cw3,
            state.unit_line(rack, unit),
            colour=text_colour,
            size=16,
            border=theme.DISPLAY_BORDER_OUTPUT,
            glow=rack.power,
        )

    # -- blank panel ----------------------------------------------------------------------------

    def _draw_blank(self, x: float, y: float, cols: layout.Columns) -> None:
        p, rack = self.painter, self.state
        w, h = cols.unit_width, theme.BLANK_HEIGHT
        top, bottom, divider = theme.EDGE_BLANK
        p.rect(x, y, x + w, y + h, theme.FACE_BLANK)
        p.rect(x, y, x + w, y + 1, top)
        p.rect(x, y + h - 1, x + w, y + h, bottom)
        draw_ears(p, x, y, w, h, "blank", divider)

        mid = y + h / 2
        sx = x + theme.EAR_WIDTH + theme.UNIT_PADDING_X
        for i in range(6):
            p.box(sx + i * 52, mid - 3, sx + i * 52 + 46, mid + 3, theme.SLOT, 3)

        right = x + w - theme.EAR_WIDTH - theme.UNIT_PADDING_X
        if rack.can_add:
            label = "ADD LANGUAGE OUTPUT"
            text_w = p.spaced_width(label, "caption", 11, 0.2, bold=True)
            bw = 18 * 2 + 16 + 10 + text_w + 2
            bx = right - bw
            draw_button(
                p,
                bx,
                mid - 22,
                label,
                theme.KEY_ADD,
                width=bw,
                height=44,
                spacing=0.2,
                icon="plus",
                dashed=theme.DASH,
            )
            self.hits.append(Hit(bx, mid - 22, bx + bw, mid + 22, "add"))
        else:
            label = f"RACK FULL · {state.MAX_LANGUAGE_UNITS} LANGUAGES"
            p.text(
                right,
                mid,
                label,
                "caption",
                11,
                theme.TEXT_SCALE,
                bold=True,
                anchor="e",
                spacing=0.2,
            )

    # -- input handling -------------------------------------------------------------------------

    def _hit_at(self, event_x: float, event_y: float) -> Hit | None:
        x, y = event_x / self.scale, event_y / self.scale
        return next((h for h in reversed(self.hits) if h.contains(x, y)), None)

    def knob_value(self, key: KnobKey) -> float:
        if key[0] == "in":
            return self.state.source.gain_db
        return self._unit(key[1]).level_db

    def set_knob(self, key: KnobKey, db: float) -> None:
        db = meters.snap_db(db)
        if key[0] == "in":
            self.state.source.gain_db = db
        else:
            self._unit(key[1]).level_db = db
        self.invalidate()
        self._changed()

    def _unit(self, uid: str) -> LanguageUnit:
        return next(u for u in self.state.units if u.uid == uid)

    def _on_motion(self, event: tk.Event) -> None:
        hit = self._hit_at(event.x, event.y)
        cursor = "" if hit is None else "sb_v_double_arrow" if hit.kind == "knob" else "hand2"
        if self._drag is None and str(self.cget("cursor")) != cursor:
            self.configure(cursor=cursor)

    def _on_press(self, event: tk.Event) -> None:
        self.focus_set()
        hit = self._hit_at(event.x, event.y)
        self._pressed = hit
        self.focus_key = hit.key if hit is not None else None
        self.show_ring = False
        if hit is not None and hit.kind == "knob":
            key: KnobKey = hit.arg  # type: ignore[assignment]
            self._drag = (key, event.y, self.knob_value(key))
            self.configure(cursor="sb_v_double_arrow")
        self.invalidate()

    def _on_double(self, event: tk.Event) -> None:
        hit = self._hit_at(event.x, event.y)
        if hit is not None and hit.kind == "knob":
            self._drag = None
            self.set_knob(hit.arg, 0.0)  # type: ignore[arg-type]
        else:
            self._on_press(event)

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag is None:
            return
        key, start_y, start_db = self._drag
        self.set_knob(key, meters.drag_to_db(start_db, (start_y - event.y) / self.scale))

    def _on_release(self, event: tk.Event) -> None:
        self._drag = None
        pressed, self._pressed = self._pressed, None
        hit = self._hit_at(event.x, event.y)
        if pressed is not None and hit == pressed and hit.kind != "knob":
            self._activate(hit)
        self._on_motion(event)

    def _activate(self, hit: Hit) -> None:
        rack = self.state
        if hit.kind == "power":
            rack.power = not rack.power
        elif hit.kind == "mute_in":
            rack.source.muted = not rack.source.muted
            self._changed()
        elif hit.kind == "mute":
            unit = self._unit(hit.arg)  # type: ignore[arg-type]
            unit.muted = not unit.muted
            self._changed()
        elif hit.kind == "setup" and self.on_setup:
            self.on_setup("edit", hit.arg)  # type: ignore[arg-type]
        elif hit.kind == "add" and self.on_setup:
            self.on_setup("add", None)
        # "setup_in" is inert until the Input Setup dialog is designed.
        self.invalidate()

    def _on_wheel(self, event: tk.Event) -> None:
        self._wheel(event, 1 if event.delta > 0 else -1)

    def _wheel(self, event: tk.Event, notches: int) -> None:
        hit = self._hit_at(event.x, event.y)
        if hit is not None and hit.kind == "knob":
            key: KnobKey = hit.arg  # type: ignore[assignment]
            self.focus_key = hit.key
            fine = bool(event.state & 0x1)
            self.set_knob(key, meters.step_db(self.knob_value(key), notches, fine))

    def _on_key(self, event: tk.Event) -> str | None:
        """Space or Enter presses the focused button; arrows (Shift: fine) turn a knob."""
        hit = self.focus_hit()
        if hit is None:
            return None
        if hit.kind != "knob":
            if event.keysym in ("space", "Return", "KP_Enter"):
                self.show_ring = True
                self._activate(hit)
                return "break"
            return None
        notches = {"Up": 1, "Right": 1, "Down": -1, "Left": -1}.get(event.keysym)
        if notches is None:
            return None
        key: KnobKey = hit.arg  # type: ignore[assignment]
        fine = bool(event.state & 0x1)
        self.set_knob(key, meters.step_db(self.knob_value(key), notches, fine))
        return "break"
