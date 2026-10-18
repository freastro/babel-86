"""Design tokens for the rack: colours, type, and unit dimensions.

Everything visual lives here so the drawing code is about layout, not paint.
All sizes are in logical pixels (the design's CSS pixels); the renderer multiplies
them by the UI scale. Values come from `docs/design.md` and `docs/design.html`.
"""

from __future__ import annotations

from dataclasses import dataclass

# -- Brand and channel colours ---------------------------------------------------------
BLUE = "#2f5c9e"
IVORY = "#f4efe2"
GOLD = "#e2b23e"
INK = "#141210"
BLACK = "#000000"

PASTELS = {
    "coral": "#e8806a",
    "saffron": "#e9b04e",
    "chartreuse": "#bcc65a",
    "jade": "#5cb89f",
    "plum": "#ad8fd2",
    "rose": "#df84ab",
}
CHANNEL_COLOUR_NAMES = tuple(PASTELS)
KNOB_CAPS = {"blue": BLUE, **PASTELS}

# -- Faceplates and frame ----------------------------------------------------------------
PAGE = "#1e1e20"
RACK = "#0b0b0c"
FACE_INPUT = ("#d6cfbd", "#c4bca8")
FACE_OUTPUT = ("#232325", "#19191b")
FACE_BLANK = "#151516"

# Unit edges: (top highlight, bottom shadow, ear divider)
EDGE_INPUT = ("#ece6d6", "#7d7666", "#a69e8a")
EDGE_OUTPUT = ("#38383b", "#050505", "#0c0c0d")
EDGE_BLANK = ("#2c2c2e", "#050505", "#0c0c0d")

SLOT = "#050505"  # blank-panel vent slots
DASH = "#6a6a6e"
SCREW_SLOT_INPUT = "#5d584e"
SCREW_SLOT_OUTPUT = "#2a2926"
KNOB_POINTER = "#f7f3ea"
KNOB_POINTER_EDGE = "#2a2926"  # the pointer's 1 px shadow, as a flat colour
METER_BG_INPUT = "#0a0a0a"
METER_BG_OUTPUT = "#070707"

# -- Text colours --------------------------------------------------------------------------
INK_INPUT = "#2b2720"
INK_INPUT_SOFT = "#4a443a"
INK_LOGO = "#1d1a15"
RULE_INPUT = "#7d7666"
RULE_OUTPUT = "#4a4a4e"
TEXT_OUTPUT = "#f1ece0"
TEXT_OUTPUT_SOFT = "#d8d2c3"
TEXT_ROUTE = "#bdb7a8"
TEXT_SCALE = "#9c968a"
TEXT_BUTTON = "#ece6d6"
TEXT_BUTTON_DARK = "#e6e0d2"

# -- Displays (glowing windows) ----------------------------------------------------------
DISPLAYS = {
    "vfd": "#7df5dd",
    "led": "#ff4b3a",
    "lcd": "#ffb340",
}
DISPLAY_OFF = "#2a1f1d"
DISPLAY_BG = "#070707"
DISPLAY_BORDER_INPUT = "#3b372f"
DISPLAY_BORDER_OUTPUT = "#000000"
ERROR_TEXT = "#ff5a4a"

# -- Meaning colours (status, meters, mute lights) ----------------------------------------
OK = "#3ddc6a"
WARN_LAMP = "#f2c230"
WARN_METER = "#ffb020"
ALERT = "#ff3b2f"
LAMP_OFF = "#3a3633"
SEGMENT_OFF = "#24221f"

STATUS_COLOURS = {"xlate": OK, "idle": WARN_LAMP, "error": ALERT}
STATUS_LABELS = {"xlate": "TRANSLATING", "idle": "IDLE", "error": "ERROR"}

# -- Buttons -------------------------------------------------------------------------------
BUTTON_INPUT_FACE = "#2b2720"
BUTTON_INPUT_SHADOW = "#6f6a5f"
BUTTON_MUTE_FACE = "#c9c2b0"
BUTTON_DARK_FACE = "#0f0f10"
BUTTON_DARK_BORDER = "#3a3a3d"
POWER_FACE = "#1d1b18"
POWER_BORDER = "#0e0d0b"
POWER_HIGHLIGHT = "#3a3835"
POWER_OFF_ICON = "#8b8579"
BUTTON_MUTE_HIGHLIGHT = "#d9d3c4"
BUTTON_CREAM_FACE = FACE_INPUT[0]
BUTTON_CREAM_HIGHLIGHT = "#e4ded0"
REMOVE_BORDER = "#6a2a24"
REMOVE_TEXT = "#ff8a7a"


@dataclass(frozen=True)
class ButtonStyle:
    """The colours of one kind of key, so they travel together."""

    face: str
    fg: str
    shadow: str
    border: str | None = None
    highlight: str | None = None


KEY_INPUT = ButtonStyle(BUTTON_INPUT_FACE, TEXT_BUTTON, BUTTON_INPUT_SHADOW)
KEY_MUTE = ButtonStyle(BUTTON_MUTE_FACE, INK, BLACK, BLACK, BUTTON_MUTE_HIGHLIGHT)
KEY_DARK = ButtonStyle(BUTTON_DARK_FACE, TEXT_BUTTON_DARK, BLACK, BUTTON_DARK_BORDER)
KEY_CONFIRM = ButtonStyle(BUTTON_CREAM_FACE, INK, BLACK, BLACK, BUTTON_CREAM_HIGHLIGHT)
KEY_ADD = ButtonStyle(FACE_BLANK, TEXT_OUTPUT, FACE_BLANK)

# -- Type -----------------------------------------------------------------------------------
# Logical families. `fonts.py` swaps these for fallbacks if registration fails.
FAMILY_LOGO = "Michroma"
FAMILY_CAPTION = "Archivo Narrow"
FAMILY_MONO = "Share Tech Mono"

# -- Geometry (logical px) ---------------------------------------------------------------
WINDOW_PADDING = 16
RACK_MAX_WIDTH = 1880
RACK_PADDING_Y = 8
UNIT_GAP = 3
EAR_WIDTH = 34
STRIPE_WIDTH = 8
UNIT_PADDING_X = 22
UNIT_PADDING_Y = 14
COLUMN_GAP = 32

UNIT_HEIGHT = 148  # 14 px padding + 118 px content + 1 px border each side
BLANK_HEIGHT = 52

COL_IDENTITY = 300
COL_CONTROL = 440
COL_LEVEL = (400, 300)  # flex basis, minimum
COL_TEXT = (480, 280)
GROW_LEVEL = 1.0
GROW_TEXT = 1.3

# Narrowest window the rack lays out without wrapping columns (wrapping is a later milestone).
MIN_WIDTH = 1570
DEFAULT_WIDTH = 1920

TAG_HEIGHT = 15
TAG_GAP = 8
BUTTON_WIDTH = 128
BUTTON_HEIGHT = 44
KNOB_DIAMETER = 46
KNOB_BLOCK = (84, 72)

# -- Language setup dialog ---------------------------------------------------------------
DIALOG_WIDTH = 560
DIALOG_PAD = 24
DIALOG_FIELD_GAP = 22
DIALOG_CONTROL_HEIGHT = 48
DIALOG_LABEL_HEIGHT = 12
DIALOG_LABEL_GAP = 8  # between a field's label and its well
DIALOG_NOTE_HEIGHT = 21  # the Pass-thru explanation under the model selector
DIALOG_CODE_TOP, DIALOG_CODE_BOTTOM = 20, 74  # the language code box in the header
DIALOG_STRIP_TOP, DIALOG_STRIP_HEIGHT = 94, 4  # the six-colour strip under the header
DIALOG_HEADER_HEIGHT = DIALOG_STRIP_TOP + DIALOG_STRIP_HEIGHT
DIALOG_FOOTER_HEIGHT = 77
DIALOG_SWATCH = 44
DIALOG_SWATCH_PITCH = 54
DIALOG_COLUMN_GAP = 12
DIALOG_KEY_GAP = 10  # between the Cancel and confirm keys
DIALOG_SCRIM_OPACITY = 0.6  # how far the rack behind the dialog is darkened
