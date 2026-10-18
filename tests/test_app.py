import os
import sys

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
