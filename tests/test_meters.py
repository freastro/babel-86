import pytest

from babel86 import meters, theme


def test_there_are_18_segments_in_ascending_order():
    assert len(meters.SEGMENT_DB) == 18
    assert list(meters.SEGMENT_DB) == sorted(meters.SEGMENT_DB)


def test_empty_meter_lights_nothing():
    assert not any(meters.lit_segments(None))


def test_lit_segments_follow_the_peak_level():
    lit = meters.lit_segments(-12)
    assert lit.count(True) == meters.SEGMENT_DB.index(-12) + 1
    assert all(lit[: lit.index(False)])  # lit segments are contiguous from the bottom
    assert all(meters.lit_segments(0))
    assert not any(meters.lit_segments(-60))


@pytest.mark.parametrize(
    ("threshold", "colour"),
    [
        (-48, theme.OK),
        (-8, theme.OK),
        (-6, theme.WARN_METER),
        (-2, theme.WARN_METER),
        (-1, theme.ALERT),
        (-0.5, theme.ALERT),
        (0, theme.ALERT),
    ],
)
def test_segment_colours(threshold, colour):
    assert meters.segment_colour(threshold) == colour


def test_scale_labels_sit_under_their_own_segments():
    labels = dict(zip(meters.SEGMENT_DB, meters.scale_labels(), strict=True))
    assert {t for t, label in labels.items() if label} == {-48, -24, -12, -6, -3, 0}
    assert labels[-12] == "-12"


@pytest.mark.parametrize(
    ("db", "angle"), [(-24, -135), (0, 0), (24, 135), (12, 68), (-100, -135), (100, 135)]
)
def test_knob_angle_sweeps_135_degrees_each_way(db, angle):
    assert meters.knob_angle(db) == angle


def test_drag_up_raises_and_is_clamped_and_rounded():
    assert meters.drag_to_db(0, 8) == 2.0
    assert meters.drag_to_db(0, -8) == -2.0
    assert meters.drag_to_db(20, 400) == 24.0
    assert meters.drag_to_db(-20, -400) == -24.0
    assert meters.drag_to_db(0, 1.3) == 0.3


def test_arrow_steps_are_one_db_or_a_tenth_with_shift():
    assert meters.step_db(0, 1) == 1.0
    assert meters.step_db(0, -1) == -1.0
    assert meters.step_db(0, 1, fine=True) == 0.1
    assert meters.step_db(23.5, 1) == 24.0
    assert meters.step_db(-24, -1) == -24.0


def test_format_db_uses_a_real_minus_sign():
    assert meters.format_db(4) == "+4.0 dB"
    assert meters.format_db(-2) == "\u22122.0 dB"
    assert meters.format_db(0) == "0.0 dB"
