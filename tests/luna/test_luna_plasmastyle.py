import importlib.util
import re
import sys

import pytest
from conftest import REPO
from framesvg import paint_frame
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from reference import close, qimage_to_pil, screenshot

from .luna_model import differing_fraction

sys.path.insert(0, str(REPO / "luna"))
from palette import PALETTE  # noqa: E402

GENERATOR = REPO / "luna/plasma-style/make_luna_plasmastyle.py"
COMMITTED = REPO / "luna/plasma-style/theme"
FLAT = REPO / "plasma-style/theme"
spec = importlib.util.spec_from_file_location("make_luna_plasmastyle", GENERATOR)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)

TASK_ROWS = range(3, 28)
PILL_BUDGET, BLURRED_PILL_BUDGET, START_BUDGET, BUTTON_BUDGET, BLURRED_BUTTON_BUDGET = 0.015, 0.01, 0.05, 0.16, 0.09
ICON_AND_LABEL = [(4, 5, 129, 24)]
BUTTON_TEXT = [(20, 5, 56, 18)]
START_FLAG_AND_TEXT = [(6, 4, 78, 26)]
NORMAL_TEXT_FREE_X, PRESSED_TEXT_FREE_X = 250, 560


def rgb(hex_colour):
    return tuple(int(hex_colour[index : index + 2], 16) for index in (1, 3, 5))


def rendered(theme, svg_name, prefix, width, height, background=None):
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(Qt.transparent if background is None else rgb_to_qcolor(background))
    painter = QPainter(image)
    paint_frame(painter, QSvgRenderer(str(theme / svg_name)), prefix.removesuffix("-"), QRectF(0, 0, width, height))
    painter.end()
    return image


def rgb_to_qcolor(hex_colour):
    from PySide6.QtGui import QColor

    return QColor(hex_colour)


def over_panel(theme, svg_name, prefix, width, height, top=0, panel_height=None):
    """The control drawn over the Luna panel, as a PIL image of the panel's size."""
    panel_height = panel_height or height
    backdrop = rendered(theme, "widgets/panel-background.svg", "", width, panel_height)
    painter = QPainter(backdrop)
    painter.drawImage(0, top, rendered(theme, svg_name, prefix, width, height))
    painter.end()
    return qimage_to_pil(backdrop)


def pixel(image, x, y):
    colour = image.pixelColor(x, y)
    return (colour.red(), colour.green(), colour.blue())


def alpha(image, x, y):
    return image.pixelColor(x, y).alpha()


def column(image, x, rows):
    return [pixel(image, x, row) for row in rows]


def reference_column(image, x, rows):
    return [image.getpixel((x, row)) for row in rows]


def columns_close(ours, expected):
    return all(close(a, b) for a, b in zip(ours, expected, strict=True))


def brightness(colour):
    return sum(colour)


@pytest.fixture(scope="module")
def theme(tmp_path_factory):
    out = tmp_path_factory.mktemp("luna-plasma-style") / "theme"
    generator.write_theme(out, FLAT)
    return out


@pytest.fixture(scope="module")
def running():
    return screenshot("xprunning")


@pytest.fixture(scope="module")
def taskbar():
    return screenshot("xptaskbar-1x")


def test_committed_theme_equals_the_generator_output(theme):
    def contents(root):
        return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}

    assert contents(COMMITTED) == contents(theme)


def test_metadata_names_the_theme_chicago95luna(theme):
    assert '"Id": "Chicago95Luna"' in (theme / "metadata.json").read_text()
    assert '"Name": "Chicago95 Luna"' in (theme / "metadata.json").read_text()


def element_image(theme, svg_name, element, width, height):
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(Qt.white)
    painter = QPainter(image)
    QSvgRenderer(str(theme / svg_name)).render(painter, element, QRectF(0, 0, width, height))
    painter.end()
    return image


def differing_from(ours, original):
    points = [(x, y) for x in range(original.width) for y in range(original.height)]
    return sum(not close(ours.getpixel(point), original.getpixel(point), 16) for point in points) / len(points)


STEPPER_BUDGET, THUMB_BUDGET = 0.25, 0.12


def test_scrollbar_up_button_matches_the_xpappearance_list_scrollbar_within_the_stepper_budget(theme):
    ours = qimage_to_pil(element_image(theme, "widgets/scrollbar.svg", "arrow-up", 17, 17))
    original = screenshot("xpappearance").crop((277, 265, 294, 282))
    assert differing_from(ours, original) < STEPPER_BUDGET


def test_scrollbar_thumb_matches_the_xpappearance_list_scrollbar_within_the_thumb_budget(theme):
    ours = qimage_to_pil(rendered(theme, "widgets/scrollbar.svg", "slider-", 17, 15))
    original = screenshot("xpappearance").crop((277, 282, 294, 297))
    assert differing_from(ours, original) < THUMB_BUDGET


def test_scrollbar_track_is_f9f9f7_between_eeede5_lines(theme):
    track = rendered(theme, "widgets/scrollbar.svg", "background-vertical-", 17, 40)
    assert [pixel(track, 0, 20), pixel(track, 8, 20), pixel(track, 16, 20)] == [
        rgb("#EEEDE5"),
        rgb("#F9F9F7"),
        rgb("#EEEDE5"),
    ]


@pytest.mark.parametrize("prefix", ["slider-", "mouseover-slider-", "sunken-slider-"])
def test_scrollbar_thumb_has_a_7c9fd3_top_line_in_every_state(theme, prefix):
    thumb = rendered(theme, "widgets/scrollbar.svg", prefix, 17, 40)
    assert pixel(thumb, 8, 0) == rgb("#7C9FD3")


def test_scrollbar_thumb_is_lighter_when_hot_and_darker_when_pressed(theme):
    lightness = [
        brightness(pixel(rendered(theme, "widgets/scrollbar.svg", prefix, 17, 40), 8, 20))
        for prefix in ("sunken-slider-", "slider-", "mouseover-slider-")
    ]
    assert lightness == sorted(lightness)


@pytest.mark.parametrize("prefix", ["arrow-", "mouseover-arrow-", "sunken-arrow-"])
@pytest.mark.parametrize("direction", ["up", "down", "left", "right"])
def test_scrollbar_arrow_buttons_are_17_by_17_in_every_state_and_direction(theme, prefix, direction):
    bounds = QSvgRenderer(str(theme / "widgets/scrollbar.svg")).boundsOnElement(f"{prefix}{direction}")
    assert (bounds.width(), bounds.height()) == (17, 17)


def test_scrollbar_arrow_is_4d6185_at_the_buttons_centre_column(theme):
    button = element_image(theme, "widgets/scrollbar.svg", "arrow-up", 17, 17)
    assert any(pixel(button, 8, y) == rgb("#4D6185") for y in range(17))


@pytest.mark.parametrize("place", ["north", "south", "west", "east"])
def test_active_tab_in_every_place_is_the_pressed_task_blue_and_never_white(theme, place):
    tab = rendered(theme, "widgets/tabbar.svg", f"{place}-active-tab-", 60, 25)
    pressed = rendered(theme, "widgets/tasks.svg", "focus-", 60, 25)
    assert [close(pixel(tab, 30, row), pixel(pressed, 30, row), 12) for row in (2, 12, 22)] == [True] * 3


def test_heading_runs_from_white_to_ece9d8(theme):
    heading = rendered(theme, "widgets/plasmoidheading.svg", "header-", 40, 20)
    assert [close(pixel(heading, 20, 1), (255, 255, 255), 6), close(pixel(heading, 20, 17), rgb("#ECE9D8"), 12)] == [
        True,
        True,
    ]


def test_plain_frame_is_a_1px_7f9db9_outline_over_a_transparent_inside(theme):
    frame = rendered(theme, "widgets/frame.svg", "plain-", 30, 20)
    assert [pixel(frame, 0, 10), pixel(frame, 15, 0), alpha(frame, 15, 10)] == [rgb("#7F9DB9"), rgb("#7F9DB9"), 0]


def test_radio_button_symbol_is_green_and_its_hot_ring_is_orange(theme):
    symbol = element_image(theme, "widgets/radiobutton.svg", "symbol", 5, 5)
    hover = element_image(theme, "widgets/radiobutton.svg", "hover", 13, 13)
    assert (pixel(symbol, 2, 2)[1] > pixel(symbol, 2, 2)[0] + 60, pixel(hover, 6, 0)[0] > 200) == (True, True)


def test_progress_bar_chunk_is_green_inside_a_white_track_with_a_686868_border(theme):
    inactive = rendered(theme, "widgets/bar_meter_horizontal.svg", "bar-inactive-", 40, 15)
    active = rendered(theme, "widgets/bar_meter_horizontal.svg", "bar-active-", 40, 15)
    assert [pixel(inactive, 20, 0), pixel(inactive, 20, 7), pixel(active, 20, 7)[1] > 180] == [
        rgb("#686868"),
        (255, 255, 255),
        True,
    ]


def test_active_switch_groove_is_blue_and_the_inactive_one_is_face(theme):
    active = rendered(theme, "widgets/switch.svg", "active-", 40, 16)
    inactive = rendered(theme, "widgets/switch.svg", "inactive-", 40, 16)
    assert [pixel(active, 20, 8), pixel(inactive, 20, 8)] == [rgb("#3C81F3"), rgb("#ECE9D8")]


def test_slider_hover_handle_has_a_316ac5_border_and_the_normal_one_a_919b9c_border(theme):
    renderer = QSvgRenderer(str(theme / "widgets/slider.svg"))
    handles = {name: element_image(theme, "widgets/slider.svg", name, 12, 22) for name in ("horizontal-slider-handle", "horizontal-slider-hover")}
    assert renderer.elementExists("hint-handle-size") and [
        pixel(handles["horizontal-slider-handle"], 6, 0),
        pixel(handles["horizontal-slider-hover"], 6, 0),
    ] == [rgb("#919B9C"), rgb("#316AC5")]


def test_pager_desktops_are_face_selected_blue_or_hot_orange_outlined(theme):
    cells = [rendered(theme, "widgets/pager.svg", prefix, 10, 10) for prefix in ("normal-", "active-", "hover-")]
    assert [pixel(cell, 0, 5) for cell in cells] == [rgb("#7F9DB9"), rgb("#316AC5"), rgb("#F5B700")]


def test_action_button_has_the_push_buttons_003c74_border_in_every_state(theme):
    borders = [pixel(rendered(theme, "widgets/actionbutton.svg", prefix, 40, 26), 20, 1) for prefix in ("normal-", "hover-", "pressed-")]
    assert borders == [rgb("#003C74")] * 3


def test_panel_column_x_400_of_an_800_by_30_panel_equals_the_palette_taskbar(theme):
    panel = rendered(theme, "widgets/panel-background.svg", "", 800, 30)
    assert columns_close(column(panel, 400, range(30)), [rgb(colour) for colour in PALETTE["taskbar"]])


def test_panel_column_equals_xptaskbar_column_x_1500(theme, taskbar):
    panel = rendered(theme, "widgets/panel-background.svg", "", 800, 30)
    assert columns_close(column(panel, 400, range(30)), reference_column(taskbar, 1500, range(30)))


def test_panel_is_opaque_at_the_corners(theme):
    panel = rendered(theme, "widgets/panel-background.svg", "", 800, 30)
    assert [alpha(panel, 0, 0), alpha(panel, 799, 29)] == [255, 255]


def test_normal_task_button_leaves_its_top_left_corner_pixel_almost_transparent(theme):
    button = rendered(theme, "widgets/tasks.svg", "normal-", 160, 24)
    assert alpha(button, 0, 0) < 20


def test_normal_task_button_is_opaque_on_its_left_edge_and_middle(theme):
    button = rendered(theme, "widgets/tasks.svg", "normal-", 160, 25)
    assert [alpha(button, 0, 12), alpha(button, 80, 12), alpha(button, 159, 12)] == [255, 255, 255]


def test_normal_task_button_column_x_80_equals_the_xprunning_column_x_250_within_12(theme, running):
    button = rendered(theme, "widgets/tasks.svg", "normal-", 160, 25)
    assert columns_close(column(button, 80, range(25)), reference_column(running, NORMAL_TEXT_FREE_X, TASK_ROWS))


def test_normal_task_button_left_outline_equals_the_xprunning_outline_within_12(theme, running):
    button = rendered(theme, "widgets/tasks.svg", "normal-", 160, 25)
    assert columns_close(column(button, 0, range(5, 22)), reference_column(running, 106, range(8, 25)))


def test_pressed_task_button_column_x_80_equals_the_xprunning_column_x_560_within_12(theme, running):
    button = rendered(theme, "widgets/tasks.svg", "focus-", 160, 25)
    assert columns_close(column(button, 80, range(25)), reference_column(running, PRESSED_TEXT_FREE_X, TASK_ROWS))


def test_focus_task_button_is_darker_than_normal_at_mid_height(theme):
    normal = rendered(theme, "widgets/tasks.svg", "normal-", 160, 25)
    focus = rendered(theme, "widgets/tasks.svg", "focus-", 160, 25)
    assert brightness(pixel(focus, 80, 12)) < brightness(pixel(normal, 80, 12))


def test_hover_task_button_is_lighter_than_normal_at_mid_height(theme):
    normal = rendered(theme, "widgets/tasks.svg", "normal-", 160, 25)
    hover = rendered(theme, "widgets/tasks.svg", "hover-", 160, 25)
    assert brightness(pixel(hover, 80, 12)) > brightness(pixel(normal, 80, 12))


def test_minimized_and_progress_task_buttons_equal_normal(theme):
    normal = rendered(theme, "widgets/tasks.svg", "normal-", 160, 25)
    others = [rendered(theme, "widgets/tasks.svg", prefix, 160, 25) for prefix in ("minimized-", "progress-")]
    assert [other == normal for other in others] == [True, True]


def test_attention_task_button_runs_from_orange_f8b048_to_e09020(theme):
    button = rendered(theme, "widgets/tasks.svg", "attention-", 160, 25)
    assert [close(pixel(button, 80, 2), rgb("#F8B048")), close(pixel(button, 80, 22), rgb("#E09020"))] == [True, True]


def test_task_button_label_starts_25_pixels_from_the_left(theme):
    renderer = QSvgRenderer(str(theme / "widgets/tasks.svg"))
    assert renderer.boundsOnElement("normal-hint-left-margin").width() == 25


def test_start_button_is_opaque_on_its_flat_left_edge_and_transparent_past_its_round_right_end(theme):
    button = rendered(theme, "widgets/startbutton.svg", "normal-", 98, 30)
    assert [alpha(button, 0, 15), alpha(button, 97, 0), alpha(button, 97, 29)] == [255, 0, 0]


def test_start_button_centre_column_equals_the_xptaskbar_column_x_30_within_12(theme, taskbar):
    button = rendered(theme, "widgets/startbutton.svg", "normal-", 98, 30)
    assert columns_close(column(button, 30, range(30)), reference_column(taskbar, 30, range(30)))


def test_start_button_over_the_taskbar_matches_xptaskbar_outside_the_flag_and_text_within_the_start_budget(
    theme, taskbar, tmp_path
):
    ours, reference = over_panel(theme, "widgets/startbutton.svg", "normal-", 98, 30), taskbar.crop((0, 0, 98, 30))
    assert differing_fraction(reference, ours, START_FLAG_AND_TEXT, tmp_path / "start.png") <= START_BUDGET


def test_start_button_right_end_over_the_taskbar_matches_xptaskbar_columns_78_to_97_within_the_start_budget(
    theme, taskbar, tmp_path
):
    ours = over_panel(theme, "widgets/startbutton.svg", "normal-", 98, 30).crop((78, 0, 98, 30))
    assert differing_fraction(taskbar.crop((78, 0, 98, 30)), ours, [], tmp_path / "start-end.png") <= START_BUDGET


def test_normal_task_button_over_the_taskbar_matches_xprunning_outside_the_icon_and_label_within_the_pill_budget(
    theme, running, tmp_path
):
    ours = over_panel(theme, "widgets/tasks.svg", "normal-", 160, 25, top=3, panel_height=30)
    assert (
        differing_fraction(running.crop((106, 0, 266, 30)), ours, ICON_AND_LABEL, tmp_path / "normal.png")
        <= PILL_BUDGET
    )


def test_normal_task_button_matches_xprunning_blurred_within_the_blurred_pill_budget(theme, running, tmp_path):
    ours = over_panel(theme, "widgets/tasks.svg", "normal-", 160, 25, top=3, panel_height=30)
    reference = running.crop((106, 0, 266, 30))
    assert differing_fraction(reference, ours, ICON_AND_LABEL, tmp_path / "normal-blurred.png", blur=True) <= (
        BLURRED_PILL_BUDGET
    )


def test_pressed_task_button_over_the_taskbar_matches_xprunning_outside_the_icon_and_label_within_the_pill_budget(
    theme, running, tmp_path
):
    ours = over_panel(theme, "widgets/tasks.svg", "focus-", 160, 25, top=3, panel_height=30)
    assert (
        differing_fraction(running.crop((426, 0, 586, 30)), ours, ICON_AND_LABEL, tmp_path / "pressed.png")
        <= PILL_BUDGET
    )


def smoothed(colours, radius=1):
    def window(index):
        part = colours[max(0, index - radius) : index + radius + 1]
        return tuple(sum(colour[channel] for colour in part) / len(part) for channel in range(3))

    return [window(index) for index in range(len(colours))]


def test_panel_over_xprunning_label_free_columns_matches_rows_0_to_29_after_a_3_row_moving_average(theme, running):
    panel = rendered(theme, "widgets/panel-background.svg", "", 800, 30)
    xs = range(600, 700)
    ours = smoothed([tuple(sum(pixel(panel, x, row)[c] for x in xs) / len(xs) for c in range(3)) for row in range(30)])
    reference = smoothed(
        [tuple(sum(running.getpixel((x, row))[c] for x in xs) / len(xs) for c in range(3)) for row in range(30)]
    )
    assert columns_close(ours, reference)


def test_panel_matches_xptaskbar_slices_of_the_same_width_within_the_pill_budget(theme, taskbar, tmp_path):
    panel = qimage_to_pil(rendered(theme, "widgets/panel-background.svg", "", 800, 30))
    assert differing_fraction(taskbar.crop((1000, 0, 1800, 30)), panel, [], tmp_path / "panel.png") <= PILL_BUDGET


def test_start_button_hover_is_lighter_and_pressed_darker_than_normal(theme):
    normal, hover, pressed = (
        rendered(theme, "widgets/startbutton.svg", prefix, 98, 30) for prefix in ("normal-", "hover-", "pressed-")
    )
    assert brightness(pixel(pressed, 30, 15)) < brightness(pixel(normal, 30, 15)) < brightness(pixel(hover, 30, 15))


def test_tooltip_is_yellow_fffe1_inside_a_black_border(theme):
    tooltip = rendered(theme, "widgets/tooltip.svg", "", 40, 20)
    assert [pixel(tooltip, 0, 10), pixel(tooltip, 20, 0), pixel(tooltip, 20, 10)] == [
        (0, 0, 0),
        (0, 0, 0),
        rgb("#FFFFE1"),
    ]


def test_solid_tooltip_equals_the_translucent_one(theme):
    assert (theme / "solid/widgets/tooltip.svg").read_text() == (theme / "widgets/tooltip.svg").read_text()


@pytest.mark.parametrize("name", ["widgets/background.svg", "dialogs/background.svg"])
def test_popup_background_is_white_inside_an_acaa99_border(theme, name):
    popup = rendered(theme, name, "", 40, 20)
    assert [pixel(popup, 0, 10), pixel(popup, 20, 0), pixel(popup, 20, 10)] == [
        rgb("#ACA899"),
        rgb("#ACA899"),
        (255, 255, 255),
    ]


def test_button_has_a_003c74_border_inside_a_transparent_ring_and_a_cut_corner(theme):
    button = rendered(theme, "widgets/button.svg", "normal-", 80, 26)
    assert [pixel(button, 40, 1), alpha(button, 40, 0), alpha(button, 0, 0), alpha(button, 1, 13)] == [
        rgb("#003C74"),
        0,
        0,
        255,
    ]


def test_button_at_75_by_23_matches_the_xpdisplayprop_cancel_button_outside_its_text_within_the_button_budget(
    theme, tmp_path
):
    reference = screenshot("xpdisplayprop-1x").crop((239, 422, 314, 445))
    ours = qimage_to_pil(rendered(theme, "widgets/button.svg", "normal-", 75, 23, background="#ECE9D8"))
    assert differing_fraction(reference, ours, BUTTON_TEXT, tmp_path / "button.png") <= BUTTON_BUDGET


def test_button_at_75_by_23_matches_the_xpdisplayprop_cancel_button_blurred_within_the_blurred_button_budget(
    theme, tmp_path
):
    reference = screenshot("xpdisplayprop-1x").crop((239, 422, 314, 445))
    ours = qimage_to_pil(rendered(theme, "widgets/button.svg", "normal-", 75, 23, background="#ECE9D8"))
    assert differing_fraction(reference, ours, BUTTON_TEXT, tmp_path / "button-blurred.png", blur=True) <= (
        BLURRED_BUTTON_BUDGET
    )


def test_hovered_button_has_an_orange_ring_outside_its_border(theme):
    button = rendered(theme, "widgets/button.svg", "hover-", 80, 26)
    assert [pixel(button, 40, 0), pixel(button, 40, 1)] == [rgb("#FFC73C"), rgb("#003C74")]


def test_pressed_button_is_filled_e3e3db(theme):
    button = rendered(theme, "widgets/button.svg", "pressed-", 80, 26)
    assert pixel(button, 40, 12) == rgb("#E3E3DB")


def test_line_edit_is_white_inside_a_7f9db9_border(theme):
    field = rendered(theme, "widgets/lineedit.svg", "base-", 60, 22)
    assert [pixel(field, 0, 10), pixel(field, 30, 10)] == [rgb("#7F9DB9"), (255, 255, 255)]


def test_selected_view_item_is_filled_316ac5(theme):
    item = rendered(theme, "widgets/viewitem.svg", "selected-", 40, 20)
    assert pixel(item, 20, 10) == rgb("#316AC5")


def test_hovered_view_item_is_outlined_316ac5_over_a_transparent_inside(theme):
    item = rendered(theme, "widgets/viewitem.svg", "hover-", 40, 20)
    assert [pixel(item, 0, 10), alpha(item, 20, 10)] == [rgb("#316AC5"), 0]


@pytest.mark.parametrize("element, x, y", [("horizontal-line", 5, 0), ("vertical-line", 0, 5)])
def test_menu_separator_is_c6d7f1(theme, element, x, y):
    image = QImage(48, 32, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer = QSvgRenderer(str(theme / "widgets/line.svg"))
    renderer.render(painter, element, renderer.boundsOnElement(element))
    painter.end()
    bounds = renderer.boundsOnElement(element)
    assert pixel(image, int(bounds.x()) + x, int(bounds.y()) + y) == rgb("#C6D7F1")


def test_colors_use_the_xp_face_white_clock_text_and_selection_blue(theme):
    colors = (theme / "colors").read_text()
    groups = {}
    group = None
    for line in colors.splitlines():
        group = line if line.startswith("[") else group
        if "=" in line:
            key, value = line.split("=", 1)
            groups[group, key] = value
    assert (
        groups["[Colors:Window]", "BackgroundNormal"],
        groups["[Colors:Button]", "BackgroundNormal"],
        groups["[Colors:Complementary]", "ForegroundNormal"],
        groups["[Colors:Selection]", "BackgroundNormal"],
    ) == ("236,233,216", "236,233,216", "255,255,255", "49,106,197")


DRAWN_ELEMENT = re.compile(r"<(?:path|rect|use|ellipse|circle)\b")
GRADIENT = re.compile(r"<(?:linear|radial)Gradient\b")
SIZE_BUDGETS = {
    "widgets/tasks.svg": (57, 8000, 6),
    "widgets/startbutton.svg": (40, 5800, 6),
    "widgets/button.svg": (92, 16500, 32),
    "widgets/lineedit.svg": (42, 3200, 0),
    "widgets/tooltip.svg": (42, 3100, 0),
    "widgets/viewitem.svg": (70, 5200, 0),
    "widgets/background.svg": (46, 3400, 0),
    "dialogs/background.svg": (42, 3100, 0),
    "widgets/panel-background.svg": (12, 1600, 1),
    "widgets/scrollbar.svg": (101, 16850, 28),
    "widgets/slider.svg": (33, 3100, 2),
    "widgets/tabbar.svg": (34, 4150, 2),
    "widgets/plasmoidheading.svg": (28, 2950, 2),
    "widgets/frame.svg": (14, 1150, 0),
    "widgets/arrows.svg": (4, 500, 0),
    "widgets/radiobutton.svg": (6, 1100, 3),
    "widgets/bar_meter_horizontal.svg": (33, 7200, 16),
    "widgets/switch.svg": (30, 5600, 17),
    "widgets/pager.svg": (42, 3200, 0),
    "widgets/actionbutton.svg": (48, 10500, 24),
}


@pytest.mark.parametrize("name", list(SIZE_BUDGETS))
def test_svg_stays_within_its_element_byte_and_gradient_budget(theme, name):
    text = (theme / name).read_text()
    elements, size, gradients = SIZE_BUDGETS[name]
    assert (
        len(DRAWN_ELEMENT.findall(text)) <= elements,
        len(text.encode()) <= size,
        len(GRADIENT.findall(text)) <= gradients,
    ) == (True, True, True)
