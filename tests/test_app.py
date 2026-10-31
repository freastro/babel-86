import os
import sys
import time

import pytest

import babel86
from babel86 import state, theme


def test_version_is_set():
    assert babel86.__version__


def _tk_root():
    tk = pytest.importorskip("tkinter")
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        pytest.skip("no display (try: xvfb-run pytest)")
    try:
        return tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk unavailable: {exc}")


@pytest.fixture(scope="session")
def tk_root():
    # One interpreter for the whole session: creating and destroying many Tk roots in one
    # process is flaky on Windows.
    root = _tk_root()
    root.geometry("+0+0")
    yield root
    root.destroy()


@pytest.fixture
def app(tk_root):
    from babel86.app import build

    rack = state.mock_rack(3)
    built = build(tk_root, rack, scale=1.0)
    tk_root.update()
    yield built
    for child in tk_root.winfo_children():
        child.destroy()
    tk_root.update()


def _hit(app, kind, arg=None):
    return next(h for h in app.canvas.hits if h.kind == kind and (arg is None or h.arg == arg))


def _click(app, hit):
    cv = app.canvas
    x, y = int((hit.x0 + hit.x1) / 2), int((hit.y0 + hit.y1) / 2)
    cv.event_generate("<ButtonPress-1>", x=x, y=y)
    cv.event_generate("<ButtonRelease-1>", x=x, y=y)
    app.root.update()


def test_rack_builds_and_records_every_control(app):
    kinds = [h.kind for h in app.canvas.hits]
    assert kinds.count("power") == 1
    assert kinds.count("mute_in") == kinds.count("setup_in") == 1
    assert kinds.count("mute") == kinds.count("setup") == 3
    assert kinds.count("knob") == 4  # gain plus three levels
    assert kinds.count("add") == 1  # three units leaves room for a fourth


def test_window_fits_the_rack_height(app):
    from babel86 import layout

    expected = round(layout.content_height(3) * app.scale)
    assert abs(app.root.winfo_height() - expected) <= 2


def test_power_button_toggles_state(app):
    assert app.rack.power
    _click(app, _hit(app, "power"))
    assert not app.rack.power
    _click(app, _hit(app, "power"))
    assert app.rack.power


def test_app_launches_with_the_power_on(tk_root):
    from babel86.app import build

    built = build(tk_root, scale=1.0)
    try:
        assert built.rack.power
    finally:
        for child in tk_root.winfo_children():
            child.destroy()


def test_power_on_is_the_default_of_the_dev_flags():
    from babel86.app import parse_args

    assert not parse_args([]).power_off
    assert parse_args(["--power-off"]).power_off


def test_mute_buttons_latch_independently(app):
    _click(app, _hit(app, "mute_in"))
    assert app.rack.source.muted
    _click(app, _hit(app, "mute", "b"))
    assert [u.muted for u in app.rack.units] == [False, True, False]
    _click(app, _hit(app, "mute", "b"))
    assert not app.rack.units[1].muted


def test_knob_responds_to_drag_wheel_keys_and_double_click(app):
    cv = app.canvas
    hit = _hit(app, "knob", ("out", "a"))
    x, y = int((hit.x0 + hit.x1) / 2), int((hit.y0 + hit.y1) / 2)
    unit = app.rack.units[0]
    start = unit.level_db

    cv.event_generate("<ButtonPress-1>", x=x, y=y)
    cv.event_generate("<B1-Motion>", x=x, y=y - 8)  # drag up 8 px = +2 dB
    cv.event_generate("<ButtonRelease-1>", x=x, y=y - 8)
    app.root.update()
    assert unit.level_db == pytest.approx(start + 2.0)

    cv.focus_force()
    app.root.update()
    cv.event_generate("<KeyPress>", keysym="Up")
    app.root.update()
    assert unit.level_db == pytest.approx(start + 3.0)
    cv.event_generate("<KeyPress>", keysym="Down", state=0x1)  # Shift: 0.1 dB
    app.root.update()
    assert unit.level_db == pytest.approx(start + 2.9)

    for sequence in (
        "<ButtonPress-1>",
        "<ButtonRelease-1>",
        "<ButtonPress-1>",
        "<ButtonRelease-1>",
    ):
        cv.event_generate(sequence, x=x, y=y)  # two quick clicks make a double-click
    app.root.update()
    assert unit.level_db == 0.0


def _focus(app):
    app.canvas.focus_force()
    app.root.update()


def test_tab_walks_every_control_in_reading_order_and_wraps(app):
    _focus(app)
    cv = app.canvas
    seen = []
    for _ in range(len(cv.hits)):
        cv.event_generate("<Tab>")
        app.root.update()
        seen.append(cv.focus_key)
    assert seen == [
        ("power", None),
        ("mute_in", None),
        ("setup_in", None),
        ("knob", ("in",)),
        ("mute", "a"),
        ("setup", 0),
        ("knob", ("out", "a")),
        ("mute", "b"),
        ("setup", 1),
        ("knob", ("out", "b")),
        ("mute", "c"),
        ("setup", 2),
        ("knob", ("out", "c")),
        ("add", None),
    ]
    cv.event_generate("<Tab>")
    app.root.update()
    assert cv.focus_key == ("power", None)  # wraps forwards
    cv.event_generate("<Shift-Tab>")
    app.root.update()
    assert cv.focus_key == ("add", None)  # and backwards
    assert cv.show_ring


def test_focus_ring_is_drawn_after_tab_and_hidden_after_a_click(app):
    _focus(app)
    cv = app.canvas

    def rings():
        return [
            i
            for i in cv.find_all()
            if cv.type(i) == "rectangle" and cv.itemcget(i, "outline") == theme.GOLD
        ]

    assert rings() == []
    cv.event_generate("<Tab>")
    app.root.update()
    assert len(rings()) == 1  # one outline around the power key
    _click(app, _hit(app, "mute_in"))
    assert not cv.show_ring
    assert rings() == []


def test_space_and_enter_press_the_focused_button(app):
    _focus(app)
    cv = app.canvas
    cv.event_generate("<Tab>")
    cv.event_generate("<Tab>")  # Mute Input
    app.root.update()
    cv.event_generate("<KeyPress>", keysym="space")
    app.root.update()
    assert app.rack.source.muted
    cv.event_generate("<KeyPress>", keysym="Return")
    app.root.update()
    assert not app.rack.source.muted
    cv.focus_key = ("setup", 1)
    cv.event_generate("<KeyPress>", keysym="Return")
    app.root.update()
    assert app.dialog is not None and app.dialog.draft.mode == "edit"
    app.dialog.close()


def test_arrow_keys_turn_the_knob_that_has_keyboard_focus(app):
    _focus(app)
    cv = app.canvas
    for _ in range(4):  # power, mute input, input setup, gain
        cv.event_generate("<Tab>")
    app.root.update()
    start = app.rack.source.gain_db
    cv.event_generate("<KeyPress>", keysym="Right")
    cv.event_generate("<KeyPress>", keysym="Up", state=0x1)
    app.root.update()
    assert app.rack.source.gain_db == pytest.approx(start + 1.1)


def test_changes_notify_the_app(app):
    calls = []
    app.canvas.on_change = lambda: calls.append(1)
    _click(app, _hit(app, "mute", "a"))
    app.canvas.set_knob(("in",), 2.0)
    _click(app, _hit(app, "power"))  # power is never saved
    assert len(calls) == 2


def test_every_control_is_at_least_44_px(app):
    for hit in app.canvas.hits:
        assert hit.x1 - hit.x0 >= 44 and hit.y1 - hit.y0 >= 44, hit


def test_pointer_follows_the_knob_value(app):
    from babel86 import meters

    app.canvas.set_knob(("in",), 24.0)
    assert app.rack.source.gain_db == 24.0
    assert meters.knob_angle(app.rack.source.gain_db) == 135
    app.canvas.set_knob(("in",), 99.0)  # clamped
    assert app.rack.source.gain_db == 24.0


def test_setup_buttons_open_the_dialog_and_escape_closes_it(app):
    _click(app, _hit(app, "setup", 1))
    dialog = app.dialog
    assert dialog is not None and dialog.winfo_exists()
    assert dialog.draft.mode == "edit"
    assert dialog.draft.code == "FR"
    dialog.focus_force()
    app.root.update()
    dialog.event_generate("<Escape>")
    app.root.update()
    assert not dialog.winfo_exists()
    assert app.dialog is None

    _click(app, _hit(app, "add"))
    assert app.dialog.draft.mode == "add"
    dialog = app.dialog
    dialog.close()
    assert not dialog.winfo_exists()
    assert app.dialog is None


def test_dialog_dims_the_rack_and_returns_focus_to_it(app):
    cv = app.canvas
    items_before = len(cv.find_all())
    _click(app, _hit(app, "setup", 0))
    app.root.update()
    assert len(cv.find_all()) == items_before + 1  # the scrim sits on top of the rack
    assert cv.type(cv.find_all()[-1]) == "image"

    app.dialog.close()
    app.root.update()
    assert len(cv.find_all()) == items_before
    assert app.root.focus_lastfor() is cv


def _dialog_hit(dialog, kind, arg=None):
    return next(h for h in dialog.hits if h.kind == kind and (arg is None or h.arg == arg))


def _dialog_click(app, kind, arg=None):
    dialog = app.dialog
    hit = _dialog_hit(dialog, kind, arg)
    x, y = int((hit.x0 + hit.x1) / 2 * dialog.scale), int((hit.y0 + hit.y1) / 2 * dialog.scale)
    dialog.canvas.event_generate("<ButtonPress-1>", x=x, y=y)
    dialog.canvas.event_generate("<ButtonRelease-1>", x=x, y=y)
    app.root.update()


def _dialog_key(app, keysym, widget=None, **kw):
    target = widget or app.dialog.canvas
    target.focus_force()
    app.root.update()
    target.event_generate(f"<{keysym}>", **kw)
    app.root.update()


def test_dialog_adds_a_unit_with_the_defaults(app):
    _click(app, _hit(app, "add"))
    dialog = app.dialog
    assert dialog.draft.code == "PT" and dialog.label_var.get() == "Português"
    _dialog_click(app, "confirm")
    assert app.dialog is None
    assert [u.code for u in app.rack.units] == ["ES", "FR", "DE", "PT"]
    added = app.rack.units[-1]
    assert (added.model, added.channel, added.colour, added.mock_status) == (
        "gemini",
        4,
        "coral",
        None,
    )
    app.root.update()
    from babel86 import layout

    assert abs(app.root.winfo_height() - round(layout.content_height(4) * app.scale)) <= 2
    assert not any(h.kind == "add" for h in app.canvas.hits)  # rack full
    assert app.canvas.focus_key == ("setup", 3)  # ADD is gone, so the new unit's SETUP


def test_language_dropdown_by_keyboard_updates_header_and_label(app):
    _click(app, _hit(app, "add"))
    dialog = app.dialog
    assert dialog.focus_key == ("language", None)
    _dialog_key(app, "space")
    popup = dialog.popup
    assert popup is not None and popup.winfo_exists()
    tags = [r.value for r in popup.rows]
    assert tags[popup.selected] == "pt-BR"
    rows = {r.value: r for r in popup.rows}
    assert rows["es"].note == "IN RACK" and rows["pt-BR"].note is None
    _dialog_key(app, "Down", widget=popup)
    _dialog_key(app, "Return", widget=popup)
    assert dialog.popup is None
    assert dialog.draft.language == tags[popup.selected + 1]
    assert dialog.label_var.get() == dialog.draft.native
    assert dialog.winfo_exists()  # Enter in the list picks; it does not confirm
    dialog.close()


def test_model_buttons_latch_and_pass_thru_grows_the_dialog(app):
    _click(app, _hit(app, "add"))
    dialog = app.dialog
    height = int(dialog.canvas.cget("height"))
    _dialog_click(app, "model", "pass")
    assert dialog.draft.model == "pass"
    assert int(dialog.canvas.cget("height")) > height
    dialog.close()


def test_channel_clash_adds_an_amber_note(app):
    _click(app, _hit(app, "add"))
    dialog = app.dialog
    height = int(dialog.canvas.cget("height"))
    _dialog_click(app, "channel")
    popup = dialog.popup
    assert [r.text for r in popup.rows] == [f"CH {n}" for n in range(1, 9)]
    popup.pick(1)  # CH 2, used by FR
    app.root.update()
    assert dialog.draft.channel == 2
    assert int(dialog.canvas.cget("height")) > height
    cv = dialog.canvas
    texts = [cv.itemcget(i, "text") for i in cv.find_all() if cv.type(i) == "text"]
    assert "CH 2 is also used by FR · Français" in texts
    _dialog_click(app, "confirm")  # still allowed
    assert app.rack.units[-1].channel == 2


def test_edit_saves_label_colour_and_device(app):
    _click(app, _hit(app, "setup", 0))
    dialog = app.dialog
    dialog.entry.delete(0, "end")
    dialog.entry.insert(0, "A label that is far too long to fit")
    app.root.update()
    assert dialog.label_var.get() == "A label that is far too "[:24]
    _dialog_click(app, "swatch", "rose")
    _dialog_click(app, "device")
    dialog.popup.pick(0)  # Speakers
    app.root.update()
    _dialog_key(app, "Return", widget=dialog.entry)  # Enter in the label confirms
    unit = app.rack.units[0]
    assert app.dialog is None
    assert (unit.label, unit.colour, unit.device_id, unit.channel) == (
        "A label that is far too",  # cut at 24, then trimmed
        "rose",
        "mock:speakers",
        1,
    )


def test_escape_cancels_without_changes(app):
    _click(app, _hit(app, "setup", 0))
    _dialog_click(app, "swatch", "rose")
    _dialog_key(app, "Escape")
    assert app.dialog is None
    assert app.rack.units[0].colour == "jade"


def test_tab_stays_inside_the_dialog(app):
    _click(app, _hit(app, "setup", 0))
    dialog = app.dialog
    keys = [h.key for h in dialog.hits]
    assert keys[0] == ("language", None) and keys[-1] == ("confirm", None)
    _dialog_key(app, "Tab")
    assert dialog.focus_key == ("label", None)
    app.root.update()
    assert dialog.focus_get() is dialog.entry
    _dialog_key(app, "Shift-Tab", widget=dialog.entry)
    _dialog_key(app, "Shift-Tab")
    assert dialog.focus_key == ("confirm", None)  # wraps
    dialog.close()
    app.root.update()
    assert app.canvas.focus_key == ("setup", 0)  # focus returns to the opener


def test_remove_asks_first_while_the_power_is_on(app):
    _click(app, _hit(app, "setup", 1))
    _dialog_click(app, "remove")
    dialog = app.dialog
    assert dialog.confirm_remove and len(app.rack.units) == 3
    _dialog_key(app, "Escape")  # backs out of the confirmation, not the dialog
    assert not dialog.confirm_remove and dialog.winfo_exists()
    _dialog_click(app, "remove")
    _dialog_click(app, "remove")
    assert app.dialog is None
    assert [u.uid for u in app.rack.units] == ["a", "c"]
    assert app.canvas.focus_key == ("add", None)  # the opener went with its unit


def test_remove_is_one_press_with_the_power_off(app):
    _click(app, _hit(app, "power"))
    _click(app, _hit(app, "setup", 0))
    _dialog_click(app, "remove")
    assert app.dialog is None
    assert [u.uid for u in app.rack.units] == ["b", "c"]


def test_changes_are_saved_after_a_pause_and_restored(tk_root, tmp_path):
    from babel86 import persist
    from babel86.app import App, build

    path = tmp_path / "babel86.json"
    built = build(tk_root, state.default_rack(), scale=1.0, save_path=path)
    try:
        tk_root.update()
        _click(built, _hit(built, "add"))
        built.dialog.confirm()
        tk_root.update()
        _click(built, _hit(built, "mute", built.rack.units[0].uid))
        built.canvas.set_knob(("in",), -6.0)
        assert not path.exists()  # debounced
        assert built._save_job is not None
        time.sleep(0.6)
        tk_root.update()
        assert path.exists()
        restored = persist.load(path)
        assert [(u.language, u.muted) for u in restored.units] == [("es", True)]
        assert restored.source.gain_db == -6.0
    finally:
        for child in tk_root.winfo_children():
            child.destroy()
        tk_root.update()

    # A pending save is written at once by save_pending(), which closing the window calls.
    rebuilt = App(tk_root, persist.load(path), scale=1.0, save_path=path)
    try:
        tk_root.update()
        assert [u.code for u in rebuilt.rack.units] == ["ES"]
        rebuilt.canvas.set_knob(("in",), 3.0)
        rebuilt.save_pending()
        assert persist.load(path).source.gain_db == 3.0
    finally:
        for child in tk_root.winfo_children():
            child.destroy()
        tk_root.update()


def test_launch_flags_choose_the_rack_and_saving(tmp_path):
    from babel86.app import load_rack, parse_args

    path = tmp_path / "rack.json"
    rack, save_to = load_rack(parse_args(["--config", str(path)]))
    assert save_to == path and rack.units == [] and rack.power  # first launch
    assert not path.exists()

    rack, save_to = load_rack(parse_args(["--config", str(path), "--display", "led"]))
    assert rack.display == "led" and path.exists()  # --display is saved
    rack, _ = load_rack(parse_args(["--config", str(path)]))
    assert rack.display == "led"

    other = tmp_path / "mock.json"
    rack, save_to = load_rack(
        parse_args(["--config", str(other), "--units", "2", "--display", "lcd"])
    )
    assert save_to is None and len(rack.units) == 2
    assert not other.exists()  # --units never writes
    rack, _ = load_rack(parse_args(["--config", str(path), "--power-off"]))
    assert not rack.power


def test_scrim_has_the_requested_size(tk_root):
    from babel86.assets import scrim

    image = scrim(tk_root, 40, 30, 0.5)
    assert (image.width(), image.height()) == (40, 30)


def test_input_setup_is_inert_until_its_dialog_is_designed(app):
    _click(app, _hit(app, "setup_in"))
    assert app.dialog is None


def test_every_display_theme_has_a_colour():
    assert set(theme.DISPLAYS) == {"vfd", "led", "lcd"}


@pytest.mark.skipif(sys.platform.startswith("linux"), reason="fonts are not registered on Linux")
def test_bundled_fonts_register_and_resolve(app):
    from tkinter import font as tkfont

    from babel86.fonts import register_fonts, resolve_families

    assert register_fonts()
    families = resolve_families(app.root)
    assert (families.logo, families.caption, families.mono) == (
        theme.FAMILY_LOGO,
        theme.FAMILY_CAPTION,
        theme.FAMILY_MONO,
    )
    assert {families.logo, families.caption, families.mono} <= set(tkfont.families(app.root))


def test_font_book_scales_sizes_in_pixels(app):
    font = app.fonts.get("mono", 22)
    assert int(font.cget("size")) == -round(22 * app.scale)


def test_content_font_measures_complex_scripts_without_error(app):
    font = app.fonts.get("mono", 18)
    for sample in ("សួស្តី ពិភពលោក", "مرحبا بالعالم", "你好，世界", "हिन्दी भाषा", "ภาษาไทย"):
        assert font.measure(sample) > 0
