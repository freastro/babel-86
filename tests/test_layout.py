import pytest

from babel86 import layout, theme


def test_rack_is_about_820_tall_and_fits_1080p_with_four_languages():
    assert layout.rack_height(4) == pytest.approx(823)
    assert layout.content_height(4) <= 1080 - 90  # leaves room for the title bar and taskbar


def test_rack_is_capped_at_1880_and_centred():
    box = layout.rack_box(1920, 4)
    assert box.width == 1880
    assert box.x == 20
    wide = layout.rack_box(3000, 4)
    assert wide.width == theme.RACK_MAX_WIDTH
    assert wide.x == pytest.approx((3000 - theme.RACK_MAX_WIDTH) / 2)


def test_columns_at_1920_follow_the_flex_rules():
    cols = layout.columns(layout.rack_width(1920))
    assert cols.identity[1] == 300
    assert cols.control[1] == 440
    extra = cols.level[1] - 400, cols.text[1] - 480
    assert extra[1] / extra[0] == pytest.approx(1.3)
    # The columns plus gaps fill the unit's content area exactly.
    used = 300 + 440 + cols.level[1] + cols.text[1] + 3 * theme.COLUMN_GAP
    assert used == pytest.approx(layout.unit_content_width(cols.unit_width))


def test_columns_line_up_in_order_without_overlap():
    cols = layout.columns(1880)
    spans = [cols.identity, cols.control, cols.level, cols.text]
    for (x0, w0), (x1, _w1) in zip(spans, spans[1:], strict=False):
        assert x1 == pytest.approx(x0 + w0 + theme.COLUMN_GAP)


def test_columns_shrink_in_proportion_but_not_below_minimums():
    cols = layout.columns(layout.rack_width(theme.MIN_WIDTH))
    assert cols.level[1] >= 300
    assert cols.text[1] >= 280
    narrow = layout.columns(1000)
    assert narrow.level[1] == 300
    assert narrow.text[1] == 280


def test_unit_tops_stack_with_3px_gaps():
    tops = layout.unit_tops(4)
    assert tops[0] == theme.RACK_PADDING_Y
    assert tops[1] - tops[0] == theme.UNIT_HEIGHT + theme.UNIT_GAP
    assert tops[-1] - tops[-2] == theme.UNIT_HEIGHT + theme.UNIT_GAP
    assert len(tops) == 6  # input, four languages, blank panel
    assert tops[-1] + theme.BLANK_HEIGHT + theme.RACK_PADDING_Y == layout.rack_height(4)


@pytest.mark.parametrize(
    ("dpi_scale", "screen", "expected"),
    [
        (1.0, (1920, 1080), 1.0),
        (1.5, (3840, 2160), 1.5),  # 4K at 150%: plenty of room
        (2.0, (3840, 2160), 2.0),
        (3.0, (7680, 4320), 3.0),
    ],
)
def test_choose_scale_uses_the_display_scale_when_it_fits(dpi_scale, screen, expected):
    assert layout.choose_scale(dpi_scale, *screen) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("dpi_scale", "screen"), [(1.25, (1920, 1080)), (1.5, (1920, 1080)), (2.0, (2560, 1440))]
)
def test_choose_scale_shrinks_so_the_rack_fits_without_scrolling(dpi_scale, screen):
    scale = layout.choose_scale(dpi_scale, *screen)
    assert scale < dpi_scale
    assert scale * layout.content_height(4) <= screen[1] - 90 + 1e-6
    assert scale * theme.MIN_WIDTH <= screen[0]


def test_snap_only_rounds_down_to_a_sprite_scale():
    assert layout.snap_to_sprites(1.0) == 1.0
    assert layout.snap_to_sprites(1.3) == 1.25
    assert layout.snap_to_sprites(1.4) == 1.25
    assert layout.snap_to_sprites(1.22) == pytest.approx(1.22)  # 22% above 1x: keep as is
    assert layout.sprite_scale(1.22) == 1.25
    assert layout.sprite_scale(1.4) == 1.5


def test_window_opens_at_1920_but_never_wider_than_the_screen():
    assert layout.initial_window_width(1.0, 2560) == 1920
    assert layout.initial_window_width(1.0, 1600) == 1600
    assert layout.initial_window_width(1.5, 3840) == 1920
    assert layout.initial_window_width(1.0, 1280) == theme.MIN_WIDTH
