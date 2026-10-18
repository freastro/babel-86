import subprocess
import sys
from pathlib import Path

import pytest

from babel86 import layout
from babel86.assets import SPRITE_DIR, sprite_path

ROOT = Path(__file__).resolve().parents[1]


def test_every_sprite_the_ui_uses_exists_at_every_scale():
    names = ["knob_in", "knob_out", "screw_in", "screw_out", "cap_blue", "cap_classic"]
    names += [f"cap_{c}" for c in ("coral", "saffron", "chartreuse", "jade", "plum", "rose")]
    names += [f"lamp_{s}" for s in ("xlate", "idle", "error", "off")]
    names += ["led_red", "led_off"] + [
        f"led_{c}" for c in ("coral", "saffron", "chartreuse", "jade", "plum", "rose")
    ]
    for scale in layout.SPRITE_SCALES:
        for name in names:
            assert sprite_path(name, scale).exists(), (name, scale)


def test_sprite_folder_has_no_strays():
    assert all(p.name.endswith("x.png") and "@" in p.name for p in SPRITE_DIR.glob("*.png"))


def test_committed_sprites_are_up_to_date():
    pytest.importorskip("PIL")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "make_sprites.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
