"""Rack state, the rules derived from it, and the mock rack used for screenshots.

Pure data and rules, with no Tk, so it can be tested without a display. Power starts on,
which overrides `docs/design.md` (it asked for off) because the front panel has no audio
yet and an unlit rack looked broken; Milestone 3 switches it.

There are no provider sessions yet, so a real unit is IDLE, or ERROR when its output
device is missing. Only `mock_rack` units carry a fake `mock_status` and meter level.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from babel86 import devices, languages, theme

MODEL_LABELS = {"gemini": "GEMINI 3.5", "qwen": "QWEN 3.8", "pass": "PASS-THRU"}
MODELS = tuple(MODEL_LABELS)

MAX_LANGUAGE_UNITS = 4
HEAR_LINE = "▸ Good evening, and welcome to tonight's session."
PASS_THRU_LINE = "[ORIGINAL AUDIO PASSED THROUGH — NOT TRANSLATED]"
ERROR_LINE = "ERR · Translation engine not responding. Retrying…"
DEVICE_ERROR_LINE = "ERR · Output device disconnected."
IDLE_LINE = "— waiting for speech —"
MUTED_LINE = "— input muted · translations in progress will finish —"


@dataclass
class LanguageUnit:
    """One language unit: a translated output in one target language."""

    uid: str
    language: str  # BCP-47 tag from `languages.CATALOGUE`
    label: str
    model: str
    device_id: str
    device_name: str  # the last-seen name, shown when the device is missing
    channel: int
    colour: str
    level_db: float = 0.0  # the Level knob
    muted: bool = False
    mock_status: str | None = None  # "xlate" | "idle" | "error", mock rack only
    meter_db: float | None = None  # mock peak level shown on the meter

    @property
    def code(self) -> str:
        return languages.code_of(self.language)

    @property
    def name(self) -> str:
        return self.label or languages.native_of(self.language)

    @property
    def route(self) -> str:
        return f"{devices.route_name(self.device_id, self.device_name)} · CH {self.channel}"


@dataclass
class InputUnit:
    """The input unit: the one mono source."""

    device_id: str = devices.DEFAULT_INPUT_ID
    device_name: str = devices.DEFAULT_INPUT_NAME
    channel: int = 1
    source_language: str = "en"
    format: str = "MONO · 48kHz"
    gain_db: float = 4.0
    muted: bool = False
    meter_db: float | None = None  # mock peak level, mock rack only
    transcript: str | None = None  # mock transcript line, mock rack only

    @property
    def code(self) -> str:
        return languages.code_of(self.source_language)

    @property
    def language(self) -> str:
        return languages.native_of(self.source_language).upper()

    @property
    def route(self) -> str:
        return f"{self.device_name} · CH {self.channel}"


@dataclass
class RackState:
    power: bool = True
    display: str = "vfd"
    source: InputUnit = field(default_factory=InputUnit)
    units: list[LanguageUnit] = field(default_factory=list)

    @property
    def can_add(self) -> bool:
        return len(self.units) < MAX_LANGUAGE_UNITS

    def used_languages(self) -> set[str]:
        return {u.language for u in self.units}

    def last_device(self) -> tuple[str, str]:
        """The (id, name) of the last language unit's device, or the first output device."""
        if self.units:
            return self.units[-1].device_id, self.units[-1].device_name
        first = devices.list_outputs()[0]
        return first.id, first.name

    def next_free_channel(self, device_id: str) -> int:
        """The lowest channel of a device that no language unit uses yet, else 1."""
        used = {u.channel for u in self.units if u.device_id == device_id}
        device = devices.find(device_id)
        count = device.channels if device else max(used | {1})
        return next((c for c in range(1, count + 1) if c not in used), 1)

    def next_free_colour(self) -> str:
        used = {u.colour for u in self.units}
        return next((c for c in theme.CHANNEL_COLOUR_NAMES if c not in used), "rose")

    def next_uid(self) -> str:
        used = {u.uid for u in self.units}
        return next(f"u{i}" for i in range(1, 2 * MAX_LANGUAGE_UNITS + 2) if f"u{i}" not in used)


def default_rack() -> RackState:
    """First launch: the input unit and no language units."""
    return RackState()


def mock_rack(units: int = MAX_LANGUAGE_UNITS) -> RackState:
    """The canvas defaults, with 1 to 4 language units and fake statuses and levels."""
    desk = "mock:interpreter-desk", "Interpreter Desk"
    defaults = [
        LanguageUnit("a", "es", "Español", "gemini", *desk, 1, "jade", -2.0, False, "xlate", -9.0),
        LanguageUnit("b", "fr", "Français", "qwen", *desk, 2, "saffron", 0.0, False, "idle", -12.0),
        LanguageUnit("c", "de", "Deutsch", "gemini", *desk, 3, "plum", 3.5, False, "error", -10.0),
        LanguageUnit(
            "d", "pt-BR", "Português", "qwen", *desk, 4, "coral", -6.0, False, "xlate", -14.0
        ),
    ]
    source = InputUnit(meter_db=-11.0, transcript=HEAR_LINE)
    return RackState(source=source, units=defaults[: max(1, min(MAX_LANGUAGE_UNITS, units))])


MAX_LABEL = 24  # code points


@dataclass
class LanguageDraft:
    """The language setup dialog's editing model: changed by the `set_*` rules below."""

    mode: str  # "add" | "edit"
    language: str
    label: str
    model: str
    device_id: str
    device_name: str
    channel: int
    colour: str
    slot: int  # 1-based position in the rack, for the "OUTPUT 01 · SETUP" kicker
    index: int | None = None  # the unit being edited
    label_custom: bool = False  # the user typed a label, so it no longer auto-fills

    @property
    def code(self) -> str:
        return languages.code_of(self.language)

    @property
    def native(self) -> str:
        return languages.native_of(self.language)

    @property
    def device_label(self) -> str:
        return devices.route_name(self.device_id, self.device_name)

    @property
    def title(self) -> str:
        return "EDIT LANGUAGE" if self.mode == "edit" else "ADD LANGUAGE"

    @property
    def confirm_label(self) -> str:
        return "SAVE" if self.mode == "edit" else "ADD TO RACK"

    @property
    def kicker(self) -> str:
        return f"OUTPUT {self.slot:02d} · SETUP"


def add_draft(rack: RackState) -> LanguageDraft:
    """Add mode: first free language, Gemini, the last unit's device, free channel, colour."""
    lang = languages.next_free("gemini", rack.used_languages())
    device_id, device_name = rack.last_device()
    return LanguageDraft(
        "add",
        lang.tag,
        lang.native,
        "gemini",
        device_id,
        device_name,
        rack.next_free_channel(device_id),
        rack.next_free_colour(),
        len(rack.units) + 1,
    )


def edit_draft(rack: RackState, index: int) -> LanguageDraft:
    """Edit mode: the unit's own settings. A label other than the native name is custom."""
    unit = rack.units[index]
    return LanguageDraft(
        "edit",
        unit.language,
        unit.name,
        unit.model,
        unit.device_id,
        unit.device_name,
        unit.channel,
        unit.colour,
        index + 1,
        index,
        label_custom=unit.name != languages.native_of(unit.language),
    )


def language_draft(rack: RackState, mode: str, index: int | None = None) -> LanguageDraft:
    """The dialog's starting values: the unit being edited, or the next free defaults."""
    if mode == "edit" and index is not None:
        return edit_draft(rack, index)
    return add_draft(rack)


def _others(rack: RackState, draft: LanguageDraft) -> list[LanguageUnit]:
    return [u for i, u in enumerate(rack.units) if i != draft.index]


def in_rack(rack: RackState, draft: LanguageDraft, tag: str) -> bool:
    """Another unit already outputs this language (shown as a dim "in rack" tag)."""
    return any(u.language == tag for u in _others(rack, draft))


def set_language(draft: LanguageDraft, tag: str) -> None:
    draft.language = tag
    if not draft.label_custom:
        draft.label = languages.native_of(tag)


def set_label(draft: LanguageDraft, text: str) -> str:
    """Store what was typed, cut to 24 code points. An empty field auto-fills again."""
    text = text[:MAX_LABEL]
    draft.label = text
    draft.label_custom = bool(text.strip())
    return text


def set_model(rack: RackState, draft: LanguageDraft, model: str) -> None:
    """Switch model; if it cannot speak the language, fall back to its first free one."""
    draft.model = model
    if not languages.supports(model, draft.language):
        used = {u.language for u in _others(rack, draft)}
        set_language(draft, languages.next_free(model, used).tag)


def set_device(draft: LanguageDraft, device: devices.OutputDevice) -> None:
    draft.device_id, draft.device_name = device.id, device.name
    draft.channel = min(draft.channel, device.channels)


def channel_count(draft: LanguageDraft) -> int:
    """CH 1 to CH n for the draft's device; a missing device keeps its saved channel."""
    device = devices.find(draft.device_id)
    return device.channels if device else max(1, draft.channel)


def channel_clash(rack: RackState, draft: LanguageDraft) -> LanguageUnit | None:
    """Another unit on the same device and channel (a warning, not an error)."""
    return next(
        (
            u
            for u in _others(rack, draft)
            if u.device_id == draft.device_id and u.channel == draft.channel
        ),
        None,
    )


def apply(rack: RackState, draft: LanguageDraft) -> LanguageUnit:
    """Add the draft as a new unit, or write it back to the unit being edited."""
    label = draft.label.strip()[:MAX_LABEL] or draft.native
    fields = dict(
        language=draft.language,
        label=label,
        model=draft.model,
        device_id=draft.device_id,
        device_name=draft.device_name,
        channel=draft.channel,
        colour=draft.colour,
    )
    if draft.index is not None:
        unit = rack.units[draft.index]
        for name, value in fields.items():
            setattr(unit, name, value)
        return unit
    unit = LanguageUnit(rack.next_uid(), **fields)  # type: ignore[arg-type]
    rack.units.append(unit)
    return unit


def remove(rack: RackState, index: int) -> None:
    del rack.units[index]


# -- Rules derived from state --------------------------------------------------------------


def device_missing(unit: LanguageUnit) -> bool:
    """A real unit whose saved output device is not in the device list."""
    return unit.mock_status is None and devices.find(unit.device_id) is None


def unit_status(rack: RackState, unit: LanguageUnit) -> str:
    """IDLE, or ERROR when the device is missing. Mock units keep their fake status."""
    if unit.mock_status is None:
        return "error" if device_missing(unit) else "idle"
    if unit.mock_status != "error" and (not rack.power or unit.model == "pass"):
        return "idle"
    return unit.mock_status


def unit_is_playing(rack: RackState, unit: LanguageUnit) -> bool:
    if device_missing(unit):
        return False
    return unit_status(rack, unit) == "xlate" or unit.model == "pass"


def unit_has_error(rack: RackState, unit: LanguageUnit) -> bool:
    return device_missing(unit) or (unit_status(rack, unit) == "error" and unit.model != "pass")


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
    if device_missing(unit):
        return DEVICE_ERROR_LINE
    if unit.model == "pass":
        return PASS_THRU_LINE
    status = unit_status(rack, unit)
    if status == "error":
        return ERROR_LINE
    lang = languages.by_tag(unit.language)
    if status == "idle" or lang is None or lang.sample is None:
        return IDLE_LINE
    return "▸ " + lang.sample


def hear_line(rack: RackState) -> str:
    """The text shown in the TRANSCRIPT panel."""
    if not rack.power:
        return ""
    if rack.source.muted:
        return MUTED_LINE
    return rack.source.transcript or IDLE_LINE


def source_state_word(rack: RackState) -> str:
    return "MUTED" if rack.source.muted else "LIVE"
