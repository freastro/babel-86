from babel86 import devices, languages, state


def test_mock_rack_matches_the_canvas_defaults():
    rack = state.mock_rack()
    assert rack.power  # overrides design.md: power starts on at launch
    assert rack.display == "vfd"
    assert rack.source.gain_db == 4.0
    assert [(u.code, u.model, u.colour, u.mock_status) for u in rack.units] == [
        ("ES", "gemini", "jade", "xlate"),
        ("FR", "qwen", "saffron", "idle"),
        ("DE", "gemini", "plum", "error"),
        ("PT", "qwen", "coral", "xlate"),
    ]
    assert [u.level_db for u in rack.units] == [-2.0, 0.0, 3.5, -6.0]
    assert all(u.route.startswith("Interpreter Desk · CH ") for u in rack.units)
    assert [u.channel for u in rack.units] == [1, 2, 3, 4]


def test_mock_rack_can_show_fewer_units():
    assert len(state.mock_rack(1).units) == 1
    assert len(state.mock_rack(0).units) == 1
    assert len(state.mock_rack(9).units) == 4


def test_default_rack_is_the_input_unit_alone():
    rack = state.default_rack()
    assert rack.units == []
    assert rack.can_add
    assert (rack.source.code, rack.source.language) == ("EN", "ENGLISH")
    assert rack.source.route == "Microphone · CH 1"
    assert state.input_meter_db(rack) is None  # no audio yet
    assert state.hear_line(rack) == state.IDLE_LINE


def test_power_off_idles_every_mock_unit_except_errors():
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
    assert state.unit_line(rack, es) == "▸ " + languages.by_tag("es").sample
    assert state.unit_line(rack, fr) == state.IDLE_LINE
    assert state.unit_line(rack, de) == state.ERROR_LINE
    assert state.unit_has_error(rack, de)
    es.model = "pass"
    assert state.unit_line(rack, es) == state.PASS_THRU_LINE
    assert state.unit_meter_db(rack, es) == -9.0  # pass-thru always plays


def _real_unit(**changes):
    unit = state.LanguageUnit(
        "u1", "es", "Español", "gemini", "mock:speakers", "Speakers", 1, "jade"
    )
    for name, value in changes.items():
        setattr(unit, name, value)
    return unit


def test_a_real_unit_idles_with_an_empty_meter_until_audio_exists():
    rack = state.default_rack()
    unit = _real_unit()
    rack.units.append(unit)
    assert state.unit_status(rack, unit) == "idle"
    assert state.unit_line(rack, unit) == state.IDLE_LINE
    assert state.unit_meter_db(rack, unit) is None
    assert not state.unit_has_error(rack, unit)
    unit.model = "pass"
    assert state.unit_status(rack, unit) == "idle"
    assert state.unit_line(rack, unit) == state.PASS_THRU_LINE


def test_a_unit_whose_device_is_missing_shows_error_and_disconnected():
    rack = state.default_rack()
    unit = _real_unit(device_id="usb:gone", device_name="Old Desk", channel=3)
    rack.units.append(unit)
    assert state.unit_status(rack, unit) == "error"
    assert state.unit_has_error(rack, unit)
    assert unit.route == "Old Desk (disconnected) · CH 3"
    assert state.unit_line(rack, unit) == state.DEVICE_ERROR_LINE
    unit.model = "pass"
    assert state.unit_status(rack, unit) == "error"  # pass-thru needs its device too
    assert state.unit_meter_db(rack, unit) is None


def test_rack_full_after_four_units():
    rack = state.mock_rack()
    assert not rack.can_add
    assert state.mock_rack(3).can_add


def test_add_draft_picks_the_first_free_language_colour_and_slot():
    rack = state.mock_rack(3)
    draft = state.language_draft(rack, "add")
    assert (draft.mode, draft.language, draft.code, draft.label) == (
        "add",
        "pt-BR",
        "PT",
        "Português",
    )
    assert draft.colour == "coral"  # chartreuse is unused too, but coral comes first
    assert draft.slot == draft.channel == 4
    assert draft.title == "ADD LANGUAGE"
    assert draft.confirm_label == "ADD TO RACK"
    assert draft.kicker == "OUTPUT 04 · SETUP"


def test_add_draft_uses_the_next_unused_channel_and_the_last_devices():
    rack = state.mock_rack(3)
    rack.units[0].channel = 5
    rack.units[1].channel = 2
    rack.units[2].channel = 3
    draft = state.language_draft(rack, "add")
    assert draft.channel == 1  # 5, 2 and 3 are taken, so the lowest free one is 1
    assert draft.device_id == "mock:interpreter-desk"  # the last language's device
    assert draft.slot == 4


def test_next_free_channel_counts_only_units_on_that_device():
    rack = state.mock_rack(2)  # Interpreter Desk CH 1 and 2
    assert rack.next_free_channel("mock:interpreter-desk") == 3
    assert rack.next_free_channel("mock:speakers") == 1


def test_add_draft_without_languages_uses_the_first_device():
    rack = state.default_rack()
    draft = state.language_draft(rack, "add")
    first = devices.list_outputs()[0]
    assert (draft.device_id, draft.channel, draft.slot) == (first.id, 1, 1)
    assert draft.language == "es"


def test_label_auto_fills_until_typed_and_is_capped():
    rack = state.default_rack()
    draft = state.add_draft(rack)
    state.set_language(draft, "fr")
    assert draft.label == "Français"
    assert state.set_label(draft, "Booth A") == "Booth A"
    state.set_language(draft, "de")
    assert draft.label == "Booth A"  # typed labels are kept
    state.set_label(draft, "")
    state.set_language(draft, "it")
    assert draft.label == "Italiano"  # clearing the field resumes auto-fill
    pasted = "x" * 30
    assert state.set_label(draft, pasted) == "x" * 24
    assert state.set_label(draft, "日本語" * 10) == ("日本語" * 10)[:24]


def test_an_empty_label_falls_back_to_the_native_name():
    rack = state.default_rack()
    draft = state.add_draft(rack)
    state.set_label(draft, "   ")
    unit = state.apply(rack, draft)
    assert unit.label == "Español"


def test_model_switch_falls_back_to_the_first_free_supported_language():
    rack = state.default_rack()
    draft = state.add_draft(rack)
    state.set_language(draft, "sw")  # Kiswahili: Gemini only
    state.set_model(rack, draft, "pass")
    assert draft.language == "sw"  # pass-thru speaks everything
    state.set_model(rack, draft, "qwen")
    assert (draft.language, draft.label) == ("es", "Español")
    state.set_model(rack, draft, "gemini")
    assert draft.language == "es"  # still supported, so unchanged


def test_model_switch_keeps_a_typed_label():
    rack = state.mock_rack(1)  # Spanish is in the rack
    draft = state.add_draft(rack)
    state.set_language(draft, "sw")
    state.set_label(draft, "Booth")
    state.set_model(rack, draft, "qwen")
    assert draft.language == "fr"  # first free language Qwen speaks
    assert draft.label == "Booth"


def test_set_device_clamps_the_channel():
    rack = state.default_rack()
    draft = state.add_draft(rack)
    draft.channel = 7
    state.set_device(draft, devices.find("mock:speakers"))
    assert (draft.device_id, draft.device_name, draft.channel) == (
        "mock:speakers",
        "Speakers",
        2,
    )
    assert state.channel_count(draft) == 2


def test_channel_clash_needs_the_same_device_and_channel():
    rack = state.mock_rack(2)  # Interpreter Desk CH 1 and 2
    draft = state.add_draft(rack)
    assert state.channel_clash(rack, draft) is None
    draft.channel = 2
    assert state.channel_clash(rack, draft) is rack.units[1]
    state.set_device(draft, devices.find("mock:speakers"))
    assert state.channel_clash(rack, draft) is None
    edit = state.edit_draft(rack, 1)
    assert state.channel_clash(rack, edit) is None  # a unit never clashes with itself


def test_in_rack_ignores_the_unit_being_edited():
    rack = state.mock_rack(2)
    assert state.in_rack(rack, state.add_draft(rack), "es")
    assert not state.in_rack(rack, state.edit_draft(rack, 0), "es")


def test_apply_adds_and_edits_and_remove_removes():
    rack = state.mock_rack(2)
    draft = state.add_draft(rack)
    unit = state.apply(rack, draft)
    assert rack.units[-1] is unit
    assert unit.uid not in {"a", "b"} and unit.mock_status is None
    assert (unit.language, unit.channel, unit.colour) == ("de", 3, "coral")
    edit = state.edit_draft(rack, 0)
    edit.colour = "rose"
    state.set_label(edit, "Sala 1")
    state.apply(rack, edit)
    assert (rack.units[0].colour, rack.units[0].label, len(rack.units)) == ("rose", "Sala 1", 3)
    state.remove(rack, 1)
    assert [u.uid for u in rack.units] == ["a", unit.uid]


def test_edit_draft_marks_a_custom_label():
    rack = state.mock_rack(1)
    assert not state.edit_draft(rack, 0).label_custom
    rack.units[0].label = "Booth"
    assert state.edit_draft(rack, 0).label_custom


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
