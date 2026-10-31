"""Saving and loading the rack as `babel86.json`, in the schema from `docs/design.md`.

Pure standard library, with no Tk. Power and live status are never saved. A file that
cannot be read at all (bad JSON, a newer version, the wrong shape) is renamed to
`babel86.json.bad` and the app starts from defaults; a field that is merely out of range
is clamped or defaulted on its own, so one bad value never costs the whole rack.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from babel86 import devices, languages, meters, state, theme
from babel86.state import InputUnit, LanguageUnit, RackState

log = logging.getLogger(__name__)

VERSION = 1
FILE_NAME = "babel86.json"
APP_DIR = "babel86"


class ConfigError(ValueError):
    """The file is not a rack this version can read."""


def config_dir() -> Path:
    """The OS app-config folder: %APPDATA%, Application Support or $XDG_CONFIG_HOME."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_DIR
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / APP_DIR


def config_path() -> Path:
    return config_dir() / FILE_NAME


# -- JSON <-> state -------------------------------------------------------------------------


def to_json(rack: RackState) -> dict[str, Any]:
    src = rack.source
    return {
        "version": VERSION,
        "display": rack.display,
        "input": {
            "deviceId": src.device_id,
            "deviceName": src.device_name,
            "channel": src.channel,
            "sourceLanguage": src.source_language,
            "gainDb": src.gain_db,
            "muted": src.muted,
        },
        "outputs": [
            {
                "id": u.uid,
                "targetLanguage": u.language,
                "label": u.label,
                "model": u.model,
                "deviceId": u.device_id,
                "deviceName": u.device_name,
                "channel": u.channel,
                "color": u.colour,
                "levelDb": u.level_db,
                "muted": u.muted,
            }
            for u in rack.units
        ],
    }


def _str(obj: dict[str, Any], key: str, default: str) -> str:
    value = obj.get(key)
    return value if isinstance(value, str) and value else default


def _bool(obj: dict[str, Any], key: str) -> bool:
    value = obj.get(key)
    return value if isinstance(value, bool) else False


def _db(obj: dict[str, Any], key: str, default: float) -> float:
    value = obj.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float) or value != value:
        return default
    return meters.snap_db(float(value))


MAX_CHANNEL = 64  # the cap for a device that is not connected, so its count is unknown


def _channel(obj: dict[str, Any], device_id: str | None = None) -> int:
    """A channel from 1 to the device's channel count (clamped, as devices can shrink)."""
    value = obj.get("channel")
    channel = value if isinstance(value, int) and not isinstance(value, bool) else 1
    device = devices.find(device_id) if device_id else None
    return max(1, min(device.channels if device else MAX_CHANNEL, channel))


def _input(obj: dict[str, Any]) -> InputUnit:
    default = InputUnit()
    device_id = _str(obj, "deviceId", default.device_id)
    source = _str(obj, "sourceLanguage", default.source_language)
    return InputUnit(
        device_id=device_id,
        device_name=_str(obj, "deviceName", default.device_name),
        channel=_channel(obj),
        source_language=source if languages.by_tag(source) else default.source_language,
        gain_db=_db(obj, "gainDb", default.gain_db),
        muted=_bool(obj, "muted"),
    )


def _output(obj: dict[str, Any], rack: RackState) -> LanguageUnit:
    model = obj.get("model")
    model = model if model in state.MODELS else "gemini"
    tag = obj.get("targetLanguage")
    if not isinstance(tag, str) or languages.by_tag(tag) is None:
        tag = languages.next_free(model, rack.used_languages()).tag
    colour = obj.get("color")
    if colour not in theme.PASTELS:
        colour = rack.next_free_colour()
    uid = obj.get("id")
    if not isinstance(uid, str) or not uid or uid in {u.uid for u in rack.units}:
        uid = rack.next_uid()
    device_id = _str(obj, "deviceId", rack.last_device()[0])
    found = devices.find(device_id)
    label = obj.get("label")
    return LanguageUnit(
        uid=uid,
        language=tag,
        label=label[: state.MAX_LABEL] if isinstance(label, str) else "",
        model=model,
        device_id=device_id,
        device_name=_str(obj, "deviceName", found.name if found else device_id),
        channel=_channel(obj, device_id),
        colour=colour,  # type: ignore[arg-type]
        level_db=_db(obj, "levelDb", 0.0),
        muted=_bool(obj, "muted"),
    )


def from_json(data: object) -> RackState:
    """Build a rack, clamping or defaulting each field. Raises ConfigError on bad shape."""
    if not isinstance(data, dict):
        raise ConfigError("not a JSON object")
    version = data.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ConfigError(f"bad version: {version!r}")
    if version > VERSION:
        raise ConfigError(f"written by a newer version ({version})")
    source = data.get("input", {})
    outputs = data.get("outputs", [])
    if not isinstance(source, dict) or not isinstance(outputs, list):
        raise ConfigError("input must be an object and outputs a list")
    if not all(isinstance(o, dict) for o in outputs):
        raise ConfigError("every output must be an object")
    display = data.get("display")
    rack = RackState(display=display if display in theme.DISPLAYS else "vfd")
    rack.source = _input(source)
    for obj in outputs[: state.MAX_LANGUAGE_UNITS]:
        rack.units.append(_output(obj, rack))
    return rack


# -- files ------------------------------------------------------------------------------


def load(path: Path) -> RackState:
    """The saved rack; defaults when there is no file or it cannot be read."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return state.default_rack()
    except OSError as exc:
        log.warning("could not read %s: %s; starting with defaults", path, exc)
        return state.default_rack()
    try:
        return from_json(json.loads(text))
    except (ValueError, TypeError, KeyError) as exc:  # JSONDecodeError and ConfigError too
        bad = path.with_name(path.name + ".bad")
        log.warning("%s is unreadable (%s); moved it to %s, starting with defaults", path, exc, bad)
        try:
            os.replace(path, bad)
        except OSError as move_exc:
            log.warning("could not move %s aside: %s", path, move_exc)
        return state.default_rack()


def save(rack: RackState, path: Path) -> None:
    """Write atomically: a temp file in the same folder, then replace the real one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(to_json(rack), ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
