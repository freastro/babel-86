import os
import sys

import pytest

import babel86


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


def test_faceplate_builds_and_toggles_power():
    from babel86.app import build

    root = _tk_root()
    try:
        face = build(root)
        root.update_idletasks()
        assert face.powered
        face.toggle_power()
        assert not face.powered
        face.toggle_power()
        assert face.powered
    finally:
        root.destroy()
