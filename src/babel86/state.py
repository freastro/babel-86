"""Rack state and the mock data that drives Milestone 1.

Pure data and rules, with no Tk, so it can be tested without a display. The defaults
match the canvas in `docs/design.html`: power on, VFD display, four language units.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from babel86 import theme

MODEL_LABELS = {"gemini": "GEMINI 3.5", "qwen": "QWEN 3.8", "pass": "PASS-THRU"}
MODELS = tuple(MODEL_LABELS)

# Language code -> (native name, sample translated line)
LANGUAGES: dict[str, tuple[str, str]] = {
    "ES": ("Español", "Buenas noches y bienvenidos a la sesión de esta noche."),
    "FR": ("Français", "Bonsoir et bienvenue à la séance de ce soir."),
    "DE": ("Deutsch", "Guten Abend und willkommen zur heutigen Sitzung."),
    "PT": ("Português", "Boa noite e bem-vindos à sessão desta noite."),
    "IT": ("Italiano", "Buonasera e benvenuti alla sessione di stasera."),
    "NL": ("Nederlands", "Goedenavond en welkom bij de sessie van vanavond."),
    "PL": ("Polski", "Dobry wieczór i witamy na dzisiejszej sesji."),
    "SV": ("Svenska", "God kväll och välkomna till kvällens session."),
}

MAX_LANGUAGE_UNITS = 4
HEAR_LINE = "▸ Good evening, and welcome to tonight's session."
PASS_THRU_LINE = "[ORIGINAL AUDIO PASSED THROUGH — NOT TRANSLATED]"
ERROR_LINE = "ERR · Translation engine not responding. Retrying…"
IDLE_LINE = "— waiting for speech —"
MUTED_LINE = "— input muted · translations in progress will finish —"


@dataclass
class LanguageUnit:
    """One language unit: a translated output in one target language."""

    uid: str
    code: str
    label: str
    model: str
    device: str
    channel: int
    colour: str
    status: str  # "xlate" | "idle" | "error"
    level_db: float  # the Level knob
    meter_db: float  # mock peak level shown on the meter
    muted: bool = False

    @property
    def name(self) -> str:
        return self.label or LANGUAGES.get(self.code, (self.code, ""))[0]

    @property
    def route(self) -> str:
        return f"{self.device} · CH {self.channel}"


@dataclass
class InputUnit:
    """The input unit: the one mono source."""

    code: str = "EN"
    language: str = "ENGLISH"
    device: str = "[DEVICE]"
    channel: int = 1
    format: str = "MONO · 48kHz"
    gain_db: float = 4.0
    meter_db: float = -11.0
    muted: bool = False


@dataclass
class RackState:
    power: bool = True
    display: str = "vfd"
    source: InputUnit = field(default_factory=InputUnit)
    units: list[LanguageUnit] = field(default_factory=list)

    @property
    def can_add(self) -> bool:
        return len(self.units) < MAX_LANGUAGE_UNITS

    def next_free_code(self) -> str:
        used = {u.code for u in self.units}
        return next((c for c in LANGUAGES if c not in used), "IT")

    def next_free_colour(self) -> str:
        used = {u.colour for u in self.units}
        return next((c for c in theme.CHANNEL_COLOUR_NAMES if c not in used), "rose")


def mock_rack(units: int = MAX_LANGUAGE_UNITS) -> RackState:
    """The canvas defaults, with 1 to 4 language units."""
    defaults = [
        LanguageUnit("a", "ES", "Español", "gemini", "[DEVICE]", 1, "jade", "xlate", -2.0, -9.0),
        LanguageUnit("b", "FR", "Français", "qwen", "[DEVICE]", 2, "saffron", "idle", 0.0, -12.0),
        LanguageUnit("c", "DE", "Deutsch", "gemini", "[DEVICE]", 3, "plum", "error", 3.5, -10.0),
        LanguageUnit("d", "PT", "Português", "qwen", "[DEVICE]", 4, "coral", "xlate", -6.0, -14.0),
    ]
    return RackState(units=defaults[: max(1, min(MAX_LANGUAGE_UNITS, units))])


@dataclass(frozen=True)
class LanguageDraft:
    """What the language setup dialog shows when it opens."""

    mode: str  # "add" | "edit"
    code: str
    label: str
    model: str
    device: str
    channel: int
    colour: str
    slot: int  # 1-based position in the rack, for the "OUTPUT 01 · SETUP" kicker

    @property
    def title(self) -> str:
        return "EDIT LANGUAGE" if self.mode == "edit" else "ADD LANGUAGE"

    @property
    def confirm_label(self) -> str:
        return "SAVE" if self.mode == "edit" else "ADD TO RACK"

    @property
    def kicker(self) -> str:
        return f"OUTPUT {self.slot:02d} · SETUP"


def language_draft(rack: RackState, mode: str, index: int | None = None) -> LanguageDraft:
    """The dialog's starting values: the unit being edited, or the next free defaults."""
    if mode == "edit" and index is not None:
        unit = rack.units[index]
        return LanguageDraft(
            "edit",
            unit.code,
            unit.name,
            unit.model,
            unit.device,
            unit.channel,
            unit.colour,
            index + 1,
        )
    code = rack.next_free_code()
    slot = len(rack.units) + 1
    return LanguageDraft(
        "add", code, LANGUAGES[code][0], "gemini", "[DEVICE]", slot, rack.next_free_colour(), slot
    )


# -- Rules derived from state --------------------------------------------------------------


def unit_status(rack: RackState, unit: LanguageUnit) -> str:
    """The status shown for a unit: errors persist, everything else idles when off/pass-thru."""
    if unit.status != "error" and (not rack.power or unit.model == "pass"):
        return "idle"
    return unit.status


def unit_is_playing(rack: RackState, unit: LanguageUnit) -> bool:
    return unit_status(rack, unit) == "xlate" or unit.model == "pass"


def unit_has_error(rack: RackState, unit: LanguageUnit) -> bool:
    return unit_status(rack, unit) == "error" and unit.model != "pass"


def unit_meter_db(rack: RackState, unit: LanguageUnit) -> float | None:
    """Level to light on a unit's meter, or None when it is empty."""
    if rack.power and unit_is_playing(rack, unit) and not unit.muted:
        return unit.meter_db
    return None


def input_meter_db(rack: RackState) -> float | None:
    if rack.power and not rack.source.muted:
        return rack.source.meter_db
    return None


def unit_line(rack: RackState, unit: LanguageUnit) -> str:
    """The text shown in a unit's TRANSLATION panel."""
    if not rack.power:
        return ""
    if unit.model == "pass":
        return PASS_THRU_LINE
    status = unit_status(rack, unit)
    if status == "error":
        return ERROR_LINE
    if status == "idle":
        return IDLE_LINE
    return "▸ " + LANGUAGES.get(unit.code, ("", ""))[1]


def hear_line(rack: RackState) -> str:
    """The text shown in the TRANSCRIPT panel."""
    if not rack.power:
        return ""
    return MUTED_LINE if rack.source.muted else HEAR_LINE


def source_state_word(rack: RackState) -> str:
    return "MUTED" if rack.source.muted else "LIVE"
