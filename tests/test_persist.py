import json

import pytest

from babel86 import persist, state


def _edited_rack():
    rack = state.mock_rack(3)
    for unit in rack.units:
        unit.mock_status, unit.meter_db = None, None  # live state is never saved
    rack.source.meter_db = rack.source.transcript = None
    rack.display = "lcd"
    rack.source.gain_db = -3.5
    rack.source.muted = True
    rack.units[1].muted = True
    rack.units[2].label = "Sala 3"
    return rack


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "babel86.json"
    rack = _edited_rack()
    persist.save(rack, path)
    loaded = persist.load(path)
    rack.power = loaded.power = True
    assert loaded == rack


def test_file_follows_the_design_schema(tmp_path):
    path = tmp_path / "babel86.json"
    persist.save(state.mock_rack(1), path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert set(data) == {"version", "display", "input", "outputs"}
    assert set(data["input"]) == {
        "deviceId",
        "deviceName",
        "channel",
        "sourceLanguage",
        "gainDb",
        "muted",
    }
    assert data["outputs"][0] == {
        "id": "a",
        "targetLanguage": "es",
        "label": "Español",
        "model": "gemini",
        "deviceId": "mock:interpreter-desk",
        "deviceName": "Interpreter Desk",
        "channel": 1,
        "color": "jade",
        "levelDb": -2.0,
        "muted": False,
    }


def test_power_and_status_are_never_written(tmp_path):
    path = tmp_path / "babel86.json"
    rack = state.mock_rack(1)
    rack.power = False
    persist.save(rack, path)
    text = path.read_text(encoding="utf-8")
    assert "power" not in text and "status" not in text and "meter" not in text
    assert persist.load(path).power  # still starts on until Milestone 3


def test_a_missing_file_gives_the_default_rack(tmp_path):
    rack = persist.load(tmp_path / "nope.json")
    assert rack == state.default_rack()
    assert not (tmp_path / "nope.json.bad").exists()


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        json.dumps({"version": 2, "outputs": []}),
        json.dumps({"version": 1, "outputs": {"a": 1}}),
        json.dumps({"version": 1, "outputs": ["x"]}),
        json.dumps([1, 2, 3]),
        json.dumps({"outputs": []}),
    ],
    ids=["corrupt", "newer", "outputs-not-list", "output-not-object", "not-object", "no-version"],
)
def test_unreadable_files_are_moved_aside(tmp_path, content, caplog):
    path = tmp_path / "babel86.json"
    path.write_text(content, encoding="utf-8")
    rack = persist.load(path)
    assert rack == state.default_rack()
    assert not path.exists()
    assert (tmp_path / "babel86.json.bad").read_text(encoding="utf-8") == content
    assert "unreadable" in caplog.text


def test_out_of_range_fields_are_clamped_or_defaulted_one_by_one():
    data = {
        "version": 1,
        "display": "plasma",
        "input": {"gainDb": 40, "channel": 0, "muted": "yes", "sourceLanguage": "xx"},
        "outputs": [
            {
                "id": "a",
                "targetLanguage": "fr",
                "label": "y" * 40,
                "model": "gpt",
                "deviceId": "mock:speakers",
                "channel": 7,
                "color": "teal",
                "levelDb": -99,
            },
            {"id": "a", "targetLanguage": "klingon", "color": "jade", "levelDb": "loud"},
        ],
    }
    rack = persist.from_json(data)
    assert rack.display == "vfd"
    assert (rack.source.gain_db, rack.source.channel, rack.source.muted) == (24.0, 1, False)
    assert rack.source.source_language == "en"
    first, second = rack.units
    assert (first.model, first.colour, first.level_db) == ("gemini", "coral", -24.0)
    assert first.channel == 2  # Speakers has two channels
    assert first.device_name == "Speakers"
    assert len(first.label) == state.MAX_LABEL
    assert second.uid != "a"  # duplicate IDs are replaced
    assert second.language == "es"  # unknown language: the first free one
    assert (second.colour, second.level_db) == ("jade", 0.0)


def test_more_than_four_outputs_keeps_the_first_four():
    unit = {"targetLanguage": "es", "color": "jade"}
    rack = persist.from_json({"version": 1, "outputs": [unit] * 6})
    assert len(rack.units) == 4
    assert len({u.uid for u in rack.units}) == 4


def test_a_missing_device_still_loads_and_shows_error(tmp_path):
    path = tmp_path / "babel86.json"
    data = {
        "version": 1,
        "outputs": [
            {
                "id": "x",
                "targetLanguage": "de",
                "deviceId": "usb:desk-2",
                "deviceName": "Desk 2",
                "channel": 12,
            }
        ],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    rack = persist.load(path)
    unit = rack.units[0]
    assert unit.route == "Desk 2 (disconnected) · CH 12"
    assert state.unit_status(rack, unit) == "error"
    assert persist.to_json(rack)["outputs"][0]["deviceId"] == "usb:desk-2"  # kept as saved


def test_save_is_atomic(tmp_path, monkeypatch):
    path = tmp_path / "sub" / "babel86.json"
    persist.save(state.mock_rack(1), path)
    before = path.read_text(encoding="utf-8")

    def boom(*_args):
        raise OSError("disk full")

    monkeypatch.setattr(persist.os, "replace", boom)
    with pytest.raises(OSError):
        persist.save(state.mock_rack(2), path)
    assert path.read_text(encoding="utf-8") == before  # the old file is untouched
    assert [p.name for p in path.parent.iterdir()] == ["babel86.json"]  # no temp left


def test_config_dir_per_platform(monkeypatch, tmp_path):
    monkeypatch.setattr(persist.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert persist.config_dir() == tmp_path / "babel86"
    monkeypatch.setattr(persist.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert persist.config_path() == tmp_path / "xdg" / "babel86" / "babel86.json"
    monkeypatch.delenv("XDG_CONFIG_HOME")
    assert persist.config_dir().parts[-2:] == (".config", "babel86")
    monkeypatch.setattr(persist.sys, "platform", "darwin")
    assert persist.config_dir().parts[-3:] == ("Library", "Application Support", "babel86")
