import colorsys
import sys
from xml.etree import ElementTree

import pytest
from conftest import REPO
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from reference import close, qimage_to_pil, screenshot

from . import luna_sprites
from .luna_model import LunaWindow, build_luna_theme, differing_fraction

sys.path.insert(0, str(REPO / "luna"))
from palette import PALETTE  # noqa: E402

WIDTH, HEIGHT = 300, 200
TITLE_ROWS = 30
ICON_COLUMN = 7
TEXT_FREE_X = (160, 520)
CORNER_COLUMNS, CORNER_ROWS = 8, 12
CORNER_BUDGET, BUTTON_BUDGET, CLOSE_BUTTON_BUDGET = 0.16, 0.08, 0.15
FACE_BUDGET, BLURRED_BUTTON_BUDGET = 0.125, 0.045
HELP_WINDOW = (66, 53)
GLYPH_BOX = (4, 4, 17, 17)
BUTTON_CELL = 24
BUTTONS = {"minimize": (527, 6), "maximize": (550, 6), "close": (573, 6)}


def rgb(hex_colour):
    return tuple(int(hex_colour[index : index + 2], 16) for index in (1, 3, 5))


def column(image, x, rows):
    return [image.getpixel((x, row))[:3] for row in rows]


def saturation(colour):
    return colorsys.rgb_to_hsv(*(value / 255 for value in colour))[1]


def mean_saturation(colours):
    return sum(saturation(colour) for colour in colours) / len(colours)


def is_close_button_pixel(pixel):
    red, green, blue, alpha = pixel
    return alpha > 0 and ((red > blue + 60 and red > 150) or min(red, green, blue) > 240)


def is_white_pixel(pixel):
    return pixel[3] > 0 and min(pixel[:3]) > 160


def bounding_box(image, keep, x_range, y_range):
    points = [(x, y) for x in range(*x_range) for y in range(*y_range) if keep(image.getpixel((x, y)))]
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def white_column_groups(image, y_range):
    columns = [x for x in range(image.width) if any(is_white_pixel(image.getpixel((x, y))) for y in y_range)]
    groups = [[columns[0]]]
    for x in columns[1:]:
        if x == groups[-1][-1] + 1:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [(group[0], group[-1]) for group in groups]


def over_white(image):
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    background.alpha_composite(image)
    return background.convert("RGB")


@pytest.fixture(scope="module")
def theme(tmp_path_factory):
    return build_luna_theme(tmp_path_factory.mktemp("luna-theme"))


@pytest.fixture(scope="module")
def active(theme):
    return LunaWindow(WIDTH, HEIGHT, theme=theme).render_rgba()


@pytest.fixture(scope="module")
def inactive(theme):
    return LunaWindow(WIDTH, HEIGHT, theme=theme, active=False).render_rgba()


@pytest.fixture(scope="module")
def notepad(theme):
    return LunaWindow(600, 404, theme=theme).render_rgba()


def test_top_corners_are_transparent_and_the_top_edge_opaque_from_the_eighth_pixel(active):
    assert (
        active.getpixel((0, 0))[3],
        active.getpixel((WIDTH - 1, 0))[3],
        active.getpixel((8, 0))[3],
        active.getpixel((WIDTH - 9, 0))[3],
    ) == (0, 0, 255, 255)


def test_inactive_top_corners_are_transparent_too(inactive):
    assert (inactive.getpixel((0, 0))[3], inactive.getpixel((WIDTH - 1, 0))[3]) == (0, 0)


def test_bottom_corners_are_square(active):
    assert (active.getpixel((0, HEIGHT - 1))[3], active.getpixel((WIDTH - 1, HEIGHT - 1))[3]) == (255, 255)


def test_title_column_at_x_150_equals_the_palette_rows_within_12(active):
    title = column(active, 150, range(TITLE_ROWS))
    assert all(close(ours, rgb(expected)) for ours, expected in zip(title, PALETTE["title_active"], strict=True))


def moving_average(colours, radius=1):
    def window(index):
        part = colours[max(0, index - radius) : index + radius + 1]
        return tuple(sum(colour[channel] for colour in part) / len(part) for channel in range(3))

    return [window(index) for index in range(len(colours))]


def averaged_column(image, xs, rows):
    return [tuple(sum(image.getpixel((x, row))[channel] for x in xs) / len(xs) for channel in range(3)) for row in rows]


def test_title_averaged_over_x_160_to_329_equals_xpdisplayprop_within_12_after_a_3_row_moving_average(theme):
    window = over_white(LunaWindow(404, 455, theme=theme).render_rgba())
    rows, xs = range(25), range(160, 330)
    ours = moving_average(averaged_column(window, xs, rows))
    reference = moving_average(averaged_column(screenshot("xpdisplayprop-1x"), xs, rows))
    assert all(close(got, want) for got, want in zip(ours, reference, strict=True))


def test_inactive_title_column_at_x_150_equals_the_inactive_palette_rows_within_12(inactive):
    title = column(inactive, 150, range(TITLE_ROWS))
    assert all(close(ours, rgb(expected)) for ours, expected in zip(title, PALETTE["title_inactive"], strict=True))


def test_inactive_title_is_less_saturated_than_active(active, inactive):
    assert mean_saturation(column(inactive, 150, range(TITLE_ROWS))) < mean_saturation(
        column(active, 150, range(TITLE_ROWS))
    )


def test_close_button_is_21_by_21_and_6_pixels_from_the_right_edge(active):
    left, top, right, bottom = bounding_box(active, is_close_button_pixel, (WIDTH - 28, WIDTH), (0, TITLE_ROWS))
    assert (right - left + 1, bottom - top + 1, WIDTH - 1 - right, top) == (21, 21, 6, 6)


def test_minimize_maximize_and_close_are_21_wide_with_2_pixel_gaps(active):
    groups = white_column_groups(active, range(6, 27))
    assert [(right - left + 1) for left, right in groups] == [21, 21, 21]
    assert [groups[1][0] - groups[0][1] - 1, groups[2][0] - groups[1][1] - 1] == [2, 2]


def test_left_border_columns_0_to_3_equal_palette_border_left(active):
    border = [active.getpixel((x, 100))[:3] for x in range(4)]
    assert border == [rgb(colour) for colour in PALETTE["border_left"]]


def test_bottom_4_rows_equal_palette_border_bottom(active):
    border = [active.getpixel((150, HEIGHT - 4 + row))[:3] for row in range(4)]
    assert border == [rgb(colour) for colour in PALETTE["border_bottom"]]


def test_inactive_borders_are_paler_than_active(active, inactive):
    assert saturation(inactive.getpixel((0, 100))[:3]) < saturation(active.getpixel((0, 100))[:3])


def test_title_rows_match_xpnotepad_row_averages_within_12(notepad):
    reference = screenshot("xpnotepad")
    x_range = range(*TEXT_FREE_X)
    ours = over_white(notepad)

    def row_average(image, row):
        pixels = [image.getpixel((x, row)) for x in x_range]
        return tuple(sum(pixel[channel] for pixel in pixels) / len(pixels) for channel in range(3))

    assert all(close(row_average(ours, row), row_average(reference, row)) for row in range(TITLE_ROWS))


def coverage_by_row(alphas):
    """Rows of per-pixel coverage (0..1) summed along each row."""
    return [sum(row) for row in alphas]


def reference_coverage(reference, columns):
    return [[0 if reference.getpixel((x, y)) == (255, 255, 255) else 1 for x in columns] for y in range(CORNER_ROWS)]


def rendered_coverage(window, columns):
    return [[window.getpixel((x, y))[3] / 255 for x in columns] for y in range(CORNER_ROWS)]


@pytest.mark.parametrize(
    "columns", [range(CORNER_COLUMNS), range(600 - CORNER_COLUMNS, 600)], ids=["top-left", "top-right"]
)
def test_corner_coverage_per_row_is_within_15_percent_of_the_reference_stair(notepad, columns):
    expected = coverage_by_row(reference_coverage(screenshot("xpnotepad"), columns))
    ours = coverage_by_row(rendered_coverage(notepad, columns))
    assert all(abs(got - want) <= 0.15 * CORNER_COLUMNS for got, want in zip(ours, expected, strict=True))


@pytest.mark.parametrize(
    "columns", [range(CORNER_COLUMNS), range(600 - CORNER_COLUMNS, 600)], ids=["top-left", "top-right"]
)
def test_corner_total_coverage_is_within_5_percent_of_the_reference_stair(notepad, columns):
    expected = sum(coverage_by_row(reference_coverage(screenshot("xpnotepad"), columns)))
    ours = sum(coverage_by_row(rendered_coverage(notepad, columns)))
    assert abs(ours - expected) <= 0.05 * expected


def test_top_left_corner_piece_matches_xpnotepad_apart_from_the_window_icon_within_the_corner_budget(notepad, tmp_path):
    box = (0, 0, 8, TITLE_ROWS)
    ours, reference = over_white(notepad).crop(box), screenshot("xpnotepad").crop(box)
    assert differing_fraction(reference, ours, [(ICON_COLUMN, 9, 8, 25)], tmp_path / "top-left.png") <= CORNER_BUDGET


def test_top_right_corner_piece_matches_xpnotepad_apart_from_the_close_button_columns_within_the_corner_budget(
    notepad, tmp_path
):
    box = (594, 0, 600, TITLE_ROWS)
    ours, reference = over_white(notepad).crop(box), screenshot("xpnotepad").crop(box)
    assert differing_fraction(reference, ours, [], tmp_path / "top-right.png") <= CORNER_BUDGET


def button_crop(image, name):
    left, top = BUTTONS[name]
    return image.crop((left, top, left + 21, top + 21))


@pytest.mark.parametrize("name", ["minimize", "maximize"])
def test_blue_caption_button_matches_xpnotepad_raw_within_the_button_budget(notepad, tmp_path, name):
    ours, reference = button_crop(over_white(notepad), name), button_crop(screenshot("xpnotepad"), name)
    assert differing_fraction(reference, ours, [], tmp_path / f"{name}.png") <= BUTTON_BUDGET


def test_close_button_matches_xpnotepad_raw_within_the_close_button_budget(notepad, tmp_path):
    ours, reference = button_crop(over_white(notepad), "close"), button_crop(screenshot("xpnotepad"), "close")
    assert differing_fraction(reference, ours, [], tmp_path / "close.png") <= CLOSE_BUTTON_BUDGET


@pytest.mark.parametrize("name", list(BUTTONS))
def test_caption_button_matches_xpnotepad_blurred_within_the_blurred_budget(notepad, tmp_path, name):
    ours, reference = button_crop(over_white(notepad), name), button_crop(screenshot("xpnotepad"), name)
    assert differing_fraction(reference, ours, [], tmp_path / f"{name}-blurred.png", blur=True) <= BLURRED_BUTTON_BUDGET


@pytest.mark.parametrize("name", list(BUTTONS))
def test_caption_button_face_outside_the_glyph_box_matches_xpnotepad_within_the_face_budget(notepad, tmp_path, name):
    ours, reference = button_crop(over_white(notepad), name), button_crop(screenshot("xpnotepad"), name)
    assert differing_fraction(reference, ours, [GLYPH_BOX], tmp_path / f"{name}-face.png") <= FACE_BUDGET


def white_glyph_box(button):
    return bounding_box(button.convert("RGBA"), lambda pixel: min(pixel[:3]) > 200 and pixel[3] > 0, (2, 19), (2, 19))


@pytest.mark.parametrize("name", list(BUTTONS))
def test_caption_glyph_bounding_box_equals_the_xpnotepad_glyph_within_a_pixel(notepad, name):
    ours = white_glyph_box(button_crop(over_white(notepad), name))
    reference = white_glyph_box(button_crop(screenshot("xpnotepad"), name))
    assert all(abs(got - want) <= 1 for got, want in zip(ours, reference, strict=True))


def rendered_button_state(theme, kind, index=0):
    renderer = QSvgRenderer(str(theme / f"{kind}.svg"))
    image = QImage(renderer.defaultSize(), QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    cell = BUTTON_CELL * index
    return qimage_to_pil(image).crop((cell, 0, cell + 21, 21))


def test_restore_glyph_is_two_overlapping_window_outlines_10_pixels_across(theme):
    glyph = white_glyph_box(rendered_button_state(theme, "restore"))
    assert (glyph[2] - glyph[0] + 1, glyph[3] - glyph[1] + 1) == (10, 10)


def test_restore_glyph_draws_the_back_and_front_outlines_and_leaves_the_gaps_between_them_open(theme):
    button = rendered_button_state(theme, "restore")
    inked = lambda point: min(button.getpixel(point)[:3]) > 185  # noqa: E731
    assert [inked(point) for point in ((10, 5), (14, 9), (7, 8), (10, 7), (12, 10), (12, 12))] == [True] * 3 + [
        False
    ] * 3


def test_maximized_window_draws_a_square_26_row_title_without_corners(theme):
    maximized = LunaWindow(WIDTH, HEIGHT, theme=theme, maximized=True).render_rgba()
    title = column(maximized, 150, range(26))
    assert maximized.getpixel((0, 0))[3] == 255
    assert all(close(ours, rgb(expected)) for ours, expected in zip(title, PALETTE["title_maximized"], strict=True))


def test_committed_theme_equals_the_generator_output(theme):
    committed = REPO / "luna/aurorae/theme"
    assert {path.name: path.read_text() for path in committed.iterdir()} == {
        path.name: path.read_text() for path in theme.iterdir()
    }


def test_close_glyph_white_pixels_equal_the_xpnotepad_x_pixel_for_pixel(notepad):
    white = (
        lambda image: {  # noqa: E731
            (x, y) for x in range(21) for y in range(21) if min(image.getpixel((x, y))[:3]) > 235
        }
    )
    ours = button_crop(over_white(notepad), "close")
    reference = button_crop(screenshot("xpnotepad"), "close")
    glyph_only = lambda pixels: {(x, y) for x, y in pixels if 4 <= x <= 16 and 4 <= y <= 16}  # noqa: E731
    assert glyph_only(white(ours)) == glyph_only(white(reference))


def test_inactive_left_border_columns_equal_xpfulldesktop_help_window_border(theme):
    window = over_white(LunaWindow(400, 402, theme=theme, active=False).render_rgba())
    reference = screenshot("xpfulldesktop")
    left, top = HELP_WINDOW
    assert [window.getpixel((x, 100)) for x in range(4)] == [reference.getpixel((left + x, 100)) for x in range(4)]


def test_inactive_title_rows_match_xpfulldesktop_help_window_row_averages_within_12(theme):
    window = over_white(LunaWindow(400, 402, theme=theme, active=False).render_rgba())
    reference = screenshot("xpfulldesktop")
    left, top = HELP_WINDOW
    columns = range(185, 240)
    ours = averaged_column(window, columns, range(TITLE_ROWS))
    expected = averaged_column(reference.crop((left, top, left + 400, top + TITLE_ROWS)), columns, range(TITLE_ROWS))
    assert all(close(got, want) for got, want in zip(ours, expected, strict=True))


def test_inactive_top_left_corner_matches_xpfulldesktop_help_window_within_the_corner_budget(theme, tmp_path):
    window = over_white(LunaWindow(400, 402, theme=theme, active=False).render_rgba())
    left, top = HELP_WINDOW
    reference = screenshot("xpfulldesktop").crop((left, top, left + 8, top + TITLE_ROWS))
    box, desktop_behind_the_corner = (0, 0, 8, TITLE_ROWS), (0, 0, 6, 6)
    masks = [desktop_behind_the_corner, (ICON_COLUMN, 9, 8, 25)]
    assert differing_fraction(reference, window.crop(box), masks, tmp_path / "inactive-corner.png") <= CORNER_BUDGET


DRAWN_TAGS = {"path", "rect", "use"}


def drawn_elements(root):
    return [
        element
        for element in root.iter()
        if element.tag.rpartition("}")[2] in DRAWN_TAGS and (element.get("fill") != "none" or element.get("stroke"))
    ]


def test_decoration_draws_fewer_than_60_elements_in_under_8_kb(theme):
    markup = (theme / "decoration.svg").read_text()
    assert (len(drawn_elements(ElementTree.fromstring(markup))) < 60, len(markup.encode()) < 8 * 1024) == (True, True)


@pytest.mark.parametrize("kind", ["minimize", "maximize", "restore", "close"])
def test_caption_button_art_is_fewer_than_10_elements(theme, kind):
    root = ElementTree.parse(theme / f"{kind}.svg").getroot()
    art = next(element for element in root.iter() if element.get("id") == "active-center")
    assert len(drawn_elements(art)) < 10


EXTRA_BUTTONS = ["help", "alldesktops", "keepabove", "keepbelow", "shade"]
BUTTON_STATE_IDS = [
    "active-center",
    "hover-center",
    "pressed-center",
    "deactivated-center",
    "inactive-center",
    "hover-inactive-center",
    "pressed-inactive-center",
    "deactivated-inactive-center",
]


@pytest.mark.parametrize("name", EXTRA_BUTTONS)
def test_extra_caption_button_has_every_state_and_white_ink_on_the_blue_face(name):
    path = REPO / f"luna/aurorae/theme/{name}.svg"
    renderer = QSvgRenderer(str(path))
    image = QImage(21, 21, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer.render(painter, "active-center")
    painter.end()
    white = [(x, y) for x in range(21) for y in range(21) if image.pixelColor(x, y).name() == "#ffffff" and 4 <= x <= 16 and 4 <= y <= 17]
    assert ([renderer.elementExists(state) for state in BUTTON_STATE_IDS], len(white) > 8) == (
        [True] * len(BUTTON_STATE_IDS),
        True,
    )


SPRITE_BUTTONS = {
    "close": "Window.CloseButton",
    "minimize": "Window.MinButton",
    "maximize": "Window.MaxButton",
    "restore": "Window.RestoreButton",
    "help": "Window.HelpButton",
}
STATE_NAMES = ["normal", "hot", "pressed", "disabled", "inactive", "hot-inactive", "pressed-inactive", "disabled-inactive"]
BOTTOM_MITRE_BUDGET = 0.01
FACE_BUDGETS = {"normal": 0.09, "hot": 0.13, "pressed": 0.09, "disabled": 0.10, "inactive": 0.06}
GLYPH_BOX_IN_BUTTON = (4, 4, 17, 17)


def frame_pixels(theme, active):
    window = LunaWindow(WIDTH, HEIGHT, theme=theme, active=active)
    image = QImage(WIDTH, HEIGHT, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    window.paint_frame(painter)
    painter.end()
    from .luna_model import qimage_to_rgba

    return qimage_to_rgba(image)


@luna_sprites.requires_sprites
@pytest.mark.parametrize("active", [True, False], ids=["active", "inactive"])
def test_title_row_columns_28_to_265_equal_the_stretched_caption_within_12(theme, active):
    state = 0 if active else 1
    ours = frame_pixels(theme, active).crop((28, 0, 266, TITLE_ROWS))
    expected = luna_sprites.stretched("Window.Caption", state, WIDTH, TITLE_ROWS).crop((28, 0, 266, TITLE_ROWS))
    assert luna_sprites.differing_fraction(ours, expected) == 0.0


@luna_sprites.requires_sprites
@pytest.mark.parametrize(("active", "budget"), [(True, 0.09), (False, 0.04)], ids=["active", "inactive"])
def test_left_corner_columns_0_to_27_match_the_stretched_caption_within_the_budget(theme, active, budget):
    state = 0 if active else 1
    box = (0, 0, 28, TITLE_ROWS)
    expected = luna_sprites.stretched("Window.Caption", state, WIDTH, TITLE_ROWS).crop(box)
    assert luna_sprites.differing_fraction(frame_pixels(theme, active).crop(box), expected) <= budget


@luna_sprites.requires_sprites
@pytest.mark.parametrize(("active", "budget"), [(True, 0.17), (False, 0.03)], ids=["active", "inactive"])
def test_right_corner_columns_272_to_299_match_the_stretched_caption_within_the_budget(theme, active, budget):
    state = 0 if active else 1
    box = (WIDTH - 28, 0, WIDTH, TITLE_ROWS)
    expected = luna_sprites.stretched("Window.Caption", state, WIDTH, TITLE_ROWS).crop(box)
    assert luna_sprites.differing_fraction(frame_pixels(theme, active).crop(box), expected) <= budget


@luna_sprites.requires_sprites
@pytest.mark.parametrize("active", [True, False], ids=["active", "inactive"])
def test_corner_transparency_equals_the_stretched_caption_stair(theme, active):
    state = 0 if active else 1
    box = (0, 0, 8, 8)
    expected = luna_sprites.stretched("Window.Caption", state, WIDTH, TITLE_ROWS).crop(box)
    assert list(frame_pixels(theme, active).crop(box).getchannel("A").getdata()) == list(
        expected.getchannel("A").getdata()
    )


@luna_sprites.requires_sprites
@pytest.mark.parametrize("active", [True, False], ids=["active", "inactive"])
def test_side_and_bottom_borders_equal_the_stretched_frame_sprites(theme, active):
    state = 0 if active else 1
    frame = frame_pixels(theme, active)
    rows = HEIGHT - TITLE_ROWS - 4
    differences = [
        luna_sprites.differing_fraction(
            frame.crop((0, TITLE_ROWS, 4, TITLE_ROWS + rows)), luna_sprites.stretched("Window.FrameLeft", state, 4, rows)
        ),
        luna_sprites.differing_fraction(
            frame.crop((WIDTH - 4, TITLE_ROWS, WIDTH, TITLE_ROWS + rows)),
            luna_sprites.stretched("Window.FrameRight", state, 4, rows),
        ),
        luna_sprites.differing_fraction(
            frame.crop((0, HEIGHT - 4, WIDTH, HEIGHT)), luna_sprites.stretched("Window.FrameBottom", state, WIDTH, 4)
        ),
    ]
    assert (differences[:2], differences[2] <= BOTTOM_MITRE_BUDGET) == ([0.0, 0.0], True)


@luna_sprites.requires_sprites
@pytest.mark.parametrize("kind", list(SPRITE_BUTTONS))
@pytest.mark.parametrize("state", range(5), ids=STATE_NAMES[:5])
def test_caption_button_state_matches_the_sprite_outside_the_glyph_within_the_budget(theme, kind, state):
    ours = rendered_button_state(theme, kind, state)
    expected = luna_sprites.sprite(SPRITE_BUTTONS[kind], state)
    differing = luna_sprites.differing_fraction(ours, expected, ignored=[GLYPH_BOX_IN_BUTTON])
    assert differing <= FACE_BUDGETS[STATE_NAMES[state]]


@luna_sprites.requires_sprites
@pytest.mark.parametrize("kind", list(SPRITE_BUTTONS))
@pytest.mark.parametrize(("state", "source"), [(5, 1), (6, 2)], ids=["hot-inactive", "pressed-inactive"])
def test_inactive_window_hot_and_pressed_buttons_equal_the_active_window_ones(theme, kind, state, source):
    assert luna_sprites.differing_fraction(
        rendered_button_state(theme, kind, state), rendered_button_state(theme, kind, source)
    ) == 0.0
