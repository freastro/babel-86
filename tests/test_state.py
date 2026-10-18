from babel86 import state


def test_mock_rack_matches_the_canvas_defaults():
    rack = state.mock_rack()
    assert rack.power  # overrides design.md: power starts on at launch
    assert rack.display == "vfd"
    assert rack.source.gain_db == 4.0
    assert [(u.code, u.model, u.colour, u.status) for u in rack.units] == [
        ("ES", "gemini", "jade", "xlate"),
        ("FR", "qwen", "saffron", "idle"),
        ("DE", "gemini", "plum", "error"),
        ("PT", "qwen", "coral", "xlate"),
    ]
    assert [u.level_db for u in rack.units] == [-2.0, 0.0, 3.5, -6.0]
    assert all(u.device == "[DEVICE]" for u in rack.units)
    assert [u.channel for u in rack.units] == [1, 2, 3, 4]


def test_mock_rack_can_show_fewer_units():
    assert len(state.mock_rack(1).units) == 1
    assert len(state.mock_rack(0).units) == 1
    assert len(state.mock_rack(9).units) == 4


def test_power_off_idles_every_unit_except_errors():
    rack = state.mock_rack()
    es, fr, de, _pt = rack.units
    assert state.unit_status(rack, es) == "xlate"
    rack.power = False
    assert state.unit_status(rack, es) == "idle"
    assert state.unit_status(rack, fr) == "idle"
    assert state.unit_status(rack, de) == "error"


def test_power_off_empties_meters_and_text():
    rack = state.mock_rack()
    rack.power = False
    assert state.input_meter_db(rack) is None
    assert all(state.unit_meter_db(rack, u) is None for u in rack.units)
    assert state.hear_line(rack) == ""
    assert all(state.unit_line(rack, u) == "" for u in rack.units)


def test_mute_input_empties_the_input_meter_and_changes_the_readout():
    rack = state.mock_rack()
    assert state.input_meter_db(rack) == -11.0
    assert state.source_state_word(rack) == "LIVE"
    rack.source.muted = True
    assert state.input_meter_db(rack) is None
    assert state.source_state_word(rack) == "MUTED"
    assert "input muted" in state.hear_line(rack)
    # Outputs keep playing until they drain.
    assert state.unit_meter_db(rack, rack.units[0]) == -9.0


def test_mute_empties_only_that_units_meter_and_keeps_its_text():
    rack = state.mock_rack()
    es, _fr, _de, pt = rack.units
    es.muted = True
    assert state.unit_meter_db(rack, es) is None
    assert state.unit_line(rack, es).startswith("▸ ")
    assert state.unit_meter_db(rack, pt) == -14.0


def test_idle_and_error_units_have_empty_meters():
    rack = state.mock_rack()
    _es, fr, de, _pt = rack.units
    assert state.unit_meter_db(rack, fr) is None
    assert state.unit_meter_db(rack, de) is None


def test_unit_lines():
    rack = state.mock_rack()
    es, fr, de, _pt = rack.units
    assert state.unit_line(rack, es) == "▸ " + state.LANGUAGES["ES"][1]
    assert state.unit_line(rack, fr) == state.IDLE_LINE
    assert state.unit_line(rack, de) == state.ERROR_LINE
    assert state.unit_has_error(rack, de)
    es.model = "pass"
    assert state.unit_line(rack, es) == state.PASS_THRU_LINE
    assert state.unit_meter_db(rack, es) == -9.0  # pass-thru always plays


def test_rack_full_after_four_units():
    rack = state.mock_rack()
    assert not rack.can_add
    assert state.mock_rack(3).can_add


def test_add_draft_picks_the_first_free_language_colour_and_slot():
    rack = state.mock_rack(3)
    draft = state.language_draft(rack, "add")
    assert (draft.mode, draft.code, draft.label) == ("add", "PT", "Português")
    assert draft.colour == "coral"  # chartreuse is unused too, but coral comes first
    assert draft.slot == draft.channel == 4
    assert draft.title == "ADD LANGUAGE"
    assert draft.confirm_label == "ADD TO RACK"
    assert draft.kicker == "OUTPUT 04 · SETUP"


def test_add_draft_uses_the_next_unused_channel_and_the_last_devices():
    rack = state.mock_rack(3)
    rack.units[0].channel = 5
    rack.units[2].channel = 2
    rack.units[2].device = "Speakers"
    draft = state.language_draft(rack, "add")
    assert draft.channel == 1  # 5, 2 and 3 are taken, so the lowest free one is 1
    assert draft.device == "Speakers"  # the last language's device
    assert draft.slot == 4


def test_add_draft_without_languages_falls_back_to_the_placeholder_device():
    rack = state.mock_rack()
    rack.units.clear()
    draft = state.language_draft(rack, "add")
    assert (draft.device, draft.channel, draft.slot) == (state.DEFAULT_DEVICE, 1, 1)


def test_edit_draft_mirrors_the_unit():
    rack = state.mock_rack()
    draft = state.language_draft(rack, "edit", 2)
    assert (draft.code, draft.label, draft.model, draft.colour) == (
        "DE",
        "Deutsch",
        "gemini",
        "plum",
    )
    assert draft.slot == 3
    assert draft.title == "EDIT LANGUAGE"
    assert draft.confirm_label == "SAVE"
    assert draft.kicker == "OUTPUT 03 · SETUP"
