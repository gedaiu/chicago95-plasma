import importlib.util
from pathlib import Path

import pytest
from conftest import REPO
from PIL import Image
from PySide6.QtCore import QRect, QSize
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import (
    QProgressBar,
    QPushButton,
    QStyle,
    QStyleOptionButton,
    QStyleOptionComboBox,
    QStyleOptionMenuItem,
    QStyleOptionSpinBox,
    QTabWidget,
)
from reference import qimage_to_pil

from .luna_gallery import BUTTON_LEFT, BUTTON_ROW_TOP, BUTTON_SIZE, GALLERY_SIZE, luna_gallery, style_tree

spec = importlib.util.spec_from_file_location("chicago95luna", REPO / "luna/lib/chicago95luna.py")
luna_style = importlib.util.module_from_spec(spec)
spec.loader.exec_module(luna_style)

REFERENCES = REPO / "tests/references"
PREVIEW_DIR = Path(
    "/tmp/claude-1000/-home-gedaiu-workspace-chicago95-plasma/6679116e-4ef6-4478-b441-c6cd1dc95f4a/scratchpad/luna-preview"
)
OK_BUTTON_IN_DISPLAY_PROPERTIES = (158, 422, 233, 445)
OK_LABEL_MASK = (18, 5, 58, 18)
COLOUR_TOLERANCE = 12
PIXEL_BUDGET = 0.05
WINDOW_FACE = "#ECE9D8"


@pytest.fixture(scope="module")
def style(qt_app):
    return luna_style.LunaStyle()


@pytest.fixture(scope="module")
def gallery(qt_app, style):
    widget = luna_gallery()
    style_tree(widget, style)
    widget.setPalette(luna_style.luna_palette())
    widget.setFont(luna_style.luna_font())
    return widget


def painted(width, height, paint):
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(QColor(WINDOW_FACE))
    painter = QPainter(image)
    paint(painter)
    painter.end()
    return image


def hex_at(image, x, y):
    return image.pixelColor(x, y).name().upper()


def count_of(image, colour):
    return sum(hex_at(image, x, y) == colour for x in range(image.width()) for y in range(image.height()))


def button_option(style, rect, state):
    option = QStyleOptionButton()
    option.rect = rect
    option.state = state | QStyle.State_Enabled
    option.palette = luna_style.luna_palette()
    return option


def paint_button_option(style, state, features=QStyleOptionButton.ButtonFeature.None_):
    option = button_option(style, QRect(0, 0, 75, 23), state)
    option.features = features
    return painted(75, 23, lambda painter: style.drawControl(QStyle.CE_PushButtonBevel, option, painter))


def paint_indicator(style, element, state):
    option = button_option(style, QRect(0, 0, 13, 13), state)
    return painted(13, 13, lambda painter: style.drawPrimitive(element, option, painter))


def paint_menu_item(style, state, item_type=QStyleOptionMenuItem.MenuItemType.Normal):
    option = QStyleOptionMenuItem()
    option.rect = QRect(0, 0, 160, 23)
    option.state = state
    option.palette = luna_style.luna_palette()
    option.menuItemType = item_type
    option.text = "Open"
    return painted(160, 23, lambda painter: style.drawControl(QStyle.CE_MenuItem, option, painter))


def comparison_pixels(reference, ours, mask):
    differing = 0
    for y in range(reference.height):
        for x in range(reference.width):
            inside_mask = mask[0] <= x < mask[2] and mask[1] <= y < mask[3]
            channels = zip(reference.getpixel((x, y)), ours.getpixel((x, y)), strict=False)
            differing += not inside_mask and any(abs(a - b) > COLOUR_TOLERANCE for a, b in channels)
    return differing


@pytest.mark.parametrize(
    "metric, expected",
    [
        (QStyle.PM_ButtonMargin, 6),
        (QStyle.PM_DefaultFrameWidth, 1),
        (QStyle.PM_IndicatorWidth, 13),
        (QStyle.PM_IndicatorHeight, 13),
        (QStyle.PM_ExclusiveIndicatorWidth, 13),
        (QStyle.PM_ExclusiveIndicatorHeight, 13),
        (QStyle.PM_TabBarTabVSpace, 8),
        (QStyle.PM_TabBarBaseOverlap, 1),
        (QStyle.PM_MenuHMargin, 1),
        (QStyle.PM_MenuVMargin, 1),
    ],
)
def test_pixel_metric_returns_luna_value(style, metric, expected):
    assert style.pixelMetric(metric) == expected


def test_palette_uses_luna_colours(qt_app):
    palette = luna_style.luna_palette()
    roles = [palette.window(), palette.button(), palette.base(), palette.highlight(), palette.highlightedText()]
    assert [role.color().name().upper() for role in roles] == ["#ECE9D8", "#ECE9D8", "#FFFFFF", "#316AC5", "#FFFFFF"]
    assert [palette.mid().color().name().upper(), palette.dark().color().name().upper()] == ["#7F9DB9", "#003C74"]
    assert [palette.toolTipBase().color().name().upper(), palette.link().color().name().upper()] == [
        "#FFFFE1",
        "#0000FF",
    ]


def test_ui_font_family_is_tahoma():
    assert luna_style.ui_font_family() == "Tahoma"


def test_push_button_has_blue_border_white_top_and_soft_corner(qt_app, style):
    button = QPushButton("OK")
    button.setStyle(style)
    button.setPalette(luna_style.luna_palette())
    button.resize(75, 23)
    image = button.grab().toImage()

    assert [hex_at(image, 1, 10), hex_at(image, 37, 2)] == ["#003C74", "#FFFFFF"]
    assert "#003C74" not in (hex_at(image, 0, 0), hex_at(image, 1, 1))


def test_push_button_halo_follows_the_rounded_corner_instead_of_squaring_it(style):
    image = paint_button_option(style, QStyle.State_None)

    assert [hex_at(image, x, y) for x, y in ((0, 0), (1, 0), (0, 1), (5, 0), (0, 11))] == [
        WINDOW_FACE,
        WINDOW_FACE,
        WINDOW_FACE,
        "#E1DDCA",
        "#E1DDCA",
    ]


def test_push_button_halo_at_one_and_a_half_scale_leaves_the_corner_to_the_window(style):
    image = default_button_at_scale(style, 1.5)

    assert [hex_at(image, x, y) for x, y in ((0, 0), (1, 0), (2, 0), (0, 2), (8, 0))] == [
        WINDOW_FACE,
        WINDOW_FACE,
        WINDOW_FACE,
        WINDOW_FACE,
        "#E1DDCA",
    ]


def test_push_button_hover_shows_orange_ring_inside_border(style):
    image = paint_button_option(style, QStyle.State_MouseOver)

    assert [hex_at(image, 2, 10), hex_at(image, 3, 10)] == ["#FFF0CF", "#FDD889"]


def test_push_button_hover_ring_is_darker_orange_on_the_bottom_edge(style):
    image = paint_button_option(style, QStyle.State_MouseOver)

    assert [hex_at(image, 37, image.height() - 4), hex_at(image, 37, image.height() - 3)] == ["#F8B330", "#E59700"]


def test_push_button_pressed_fills_with_pressed_face(style):
    image = paint_button_option(style, QStyle.State_Sunken)

    assert [hex_at(image, 37, 2), hex_at(image, 37, image.height() - 4)] == ["#D0CBBF", "#F0F0EC"]


def test_default_push_button_has_blue_ring_inside_border(style):
    image = paint_button_option(style, QStyle.State_None, QStyleOptionButton.DefaultButton)

    assert [hex_at(image, 37, 2), hex_at(image, 37, 3)] == ["#CEE7FF", "#BCD4F6"]


def painted_at_scale(scale, width, height, paint):
    image = QImage(round(width * scale), round(height * scale), QImage.Format_RGB32)
    image.setDevicePixelRatio(scale)
    image.fill(QColor(WINDOW_FACE))
    painter = QPainter(image)
    paint(painter)
    painter.end()
    return image


def default_button_at_scale(style, scale):
    option = button_option(style, QRect(0, 0, 76, 24), QStyle.State_None)
    option.features = QStyleOptionButton.DefaultButton
    return painted_at_scale(
        scale, 76, 24, lambda painter: style.drawControl(QStyle.CE_PushButtonBevel, option, painter)
    )


def test_default_push_button_at_one_and_a_half_scale_has_a_one_pixel_border_over_a_three_pixel_ring(style):
    image = default_button_at_scale(style, 1.5)

    assert [hex_at(image, 57, y) for y in range(0, 5)] == ["#E1DDCA", "#003C74", "#CEE7FF", "#CEE7FF", "#BCD4F6"]


def test_default_push_button_at_one_and_a_half_scale_ends_in_a_one_pixel_border_under_the_ring(style):
    image = default_button_at_scale(style, 1.5)

    assert [hex_at(image, 57, y) for y in range(31, 36)] == ["#89ADE4", "#6982EE", "#6982EE", "#003C74", "#F8F7F0"]


def test_default_push_button_at_double_scale_has_a_two_pixel_border_and_a_four_row_ring(style):
    image = default_button_at_scale(style, 2)

    assert [hex_at(image, 76, y) for y in range(0, 8)] == [
        "#E1DDCA",
        "#E1DDCA",
        "#003C74",
        "#003C74",
        "#CEE7FF",
        "#CEE7FF",
        "#BCD4F6",
        "#BCD4F6",
    ]


def test_disabled_push_button_has_grey_border_and_flat_face(style):
    option = button_option(style, QRect(0, 0, 75, 23), QStyle.State_None)
    option.state = QStyle.State_None
    image = painted(75, 23, lambda painter: style.drawControl(QStyle.CE_PushButtonBevel, option, painter))

    assert [hex_at(image, 1, 10), hex_at(image, 37, 11)] == ["#C9C7BA", "#F5F4EA"]


def uniform_cells(rows, scale):
    """The device pixels a pixel-art pattern covers when every cell is the same whole number of device pixels:
    at 1.5x a cell is 2x2, as at 2x; at 1x it is the pixel itself. Alternating 1 and 2 pixel cells made the
    arrows' edges look broken."""
    return sum(row.count("#") for row in rows) * max(1, round(scale)) ** 2


def test_check_box_tick_at_one_and_a_half_scale_is_drawn_in_even_two_pixel_cells(style):
    option = button_option(style, QRect(0, 0, 13, 13), QStyle.State_On)
    image = painted_at_scale(
        1.5, 13, 13, lambda painter: style.drawPrimitive(QStyle.PE_IndicatorCheckBox, option, painter)
    )

    assert count_of(image, "#21A121") == uniform_cells(luna_style.CHECK_TICK, 1.5)


def test_spin_box_arrows_at_one_and_a_half_scale_are_whole_device_pixels_without_blended_edges(style):
    option = QStyleOptionSpinBox()
    option.rect = QRect(0, 0, 60, 21)
    option.state = QStyle.State_Enabled
    option.palette = luna_style.luna_palette()
    image = painted_at_scale(1.5, 60, 21, lambda painter: style.drawComplexControl(QStyle.CC_SpinBox, option, painter))

    assert count_of(image, "#4D6185") == uniform_cells(luna_style.ARROWS["up"], 1.5) + uniform_cells(
        luna_style.ARROWS["down"], 1.5
    )


def test_checked_check_box_is_13_square_with_border_and_green_tick(style):
    image = paint_indicator(style, QStyle.PE_IndicatorCheckBox, QStyle.State_On)

    assert [hex_at(image, 0, 0), hex_at(image, 12, 12), hex_at(image, 1, 1)] == ["#1C5180", "#1C5180", "#DCDCD7"]
    assert count_of(image, "#21A121") >= 12


def test_unchecked_check_box_has_no_green(style):
    image = paint_indicator(style, QStyle.PE_IndicatorCheckBox, QStyle.State_None)

    assert count_of(image, "#21A121") == 0


def test_selected_radio_button_has_round_border_and_green_dot(style):
    image = paint_indicator(style, QStyle.PE_IndicatorRadioButton, QStyle.State_On)

    assert [hex_at(image, 0, 0), hex_at(image, 6, 6)] == [WINDOW_FACE, "#21A121"]
    assert hex_at(image, 0, 6) != WINDOW_FACE


def test_combo_box_has_blue_drop_button_in_its_right_17_pixels(style):
    option = QStyleOptionComboBox()
    option.rect = QRect(0, 0, 120, 21)
    option.state = QStyle.State_Enabled
    option.palette = luna_style.luna_palette()
    image = painted(120, 21, lambda painter: style.drawComplexControl(QStyle.CC_ComboBox, option, painter))
    button_pixel = image.pixelColor(110, 5)

    assert [hex_at(image, 119, 10), hex_at(image, 50, 10), hex_at(image, 102, 10)] == ["#7F9DB9", "#FFFFFF", "#FFFFFF"]
    assert button_pixel.blue() > button_pixel.red() + 20
    assert count_of(image, "#4D6185") >= 9
    assert style.subControlRect(QStyle.CC_ComboBox, option, QStyle.SC_ComboBoxArrow).width() == 17


def test_selected_tab_has_orange_top_rows(gallery):
    tab_bar = gallery.findChild(QTabWidget).tabBar()
    selected_rect = tab_bar.tabRect(tab_bar.currentIndex())
    image = tab_bar.grab().toImage()
    centre_x = selected_rect.center().x()

    assert [hex_at(image, centre_x, selected_rect.top() + row) for row in range(3)] == ["#E68B2C", "#FFC83C", "#FFC73C"]
    assert hex_at(image, tab_bar.tabRect(0).center().x(), selected_rect.top() + 2) != "#FFC73C"


def test_selected_menu_item_is_highlight_blue(style):
    image = paint_menu_item(style, QStyle.State_Enabled | QStyle.State_Selected)

    assert hex_at(image, 150, 3) == "#316AC5"


def test_unselected_menu_item_is_white_and_separator_is_grey(style):
    plain = paint_menu_item(style, QStyle.State_Enabled)
    separator = paint_menu_item(style, QStyle.State_Enabled, QStyleOptionMenuItem.MenuItemType.Separator)

    assert [hex_at(plain, 150, 3), hex_at(separator, 100, 2), hex_at(separator, 100, 3)] == [
        "#FFFFFF",
        "#ACA899",
        "#FFFFFF",
    ]


def test_menu_row_is_21_high_and_separator_6_high(style):
    option = QStyleOptionMenuItem()
    option.text = "Open"
    separator = QStyleOptionMenuItem()
    separator.menuItemType = QStyleOptionMenuItem.MenuItemType.Separator
    heights = [style.sizeFromContents(QStyle.CT_MenuItem, item, QSize(80, 20)).height() for item in (option, separator)]

    assert heights == [21, 6]


def test_progress_bar_at_60_percent_draws_green_chunks_with_two_pixel_gaps(gallery):
    bar = gallery.findChild(QProgressBar)
    image = bar.grab().toImage()
    row = [hex_at(image, x, bar.height() // 2) for x in range(image.width())]
    runs = "".join("g" if colour == "#39E63A" else "." for colour in row)

    assert runs.count("gggggggg") == 9
    assert "gggggggg..gggggggg" in runs


def test_gallery_grab_is_one_to_one_with_requested_size(gallery):
    image = gallery.grab().toImage()

    assert (image.width(), image.height(), image.devicePixelRatio()) == (*GALLERY_SIZE, 1.0)


def test_ok_button_bevel_matches_display_properties_reference(gallery):
    reference = Image.open(REFERENCES / "xpdisplayprop-1x.png").convert("RGB").crop(OK_BUTTON_IN_DISPLAY_PROPERTIES)
    ours = qimage_to_pil(gallery.grab().toImage()).crop(
        (BUTTON_LEFT, BUTTON_ROW_TOP, BUTTON_LEFT + BUTTON_SIZE[0], BUTTON_ROW_TOP + BUTTON_SIZE[1])
    )

    assert comparison_pixels(reference, ours, OK_LABEL_MASK) <= PIXEL_BUDGET * reference.width * reference.height


def test_previews_are_written(gallery):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    ours = qimage_to_pil(gallery.grab().toImage())
    ours.resize((ours.width * 2, ours.height * 2), Image.NEAREST).save(PREVIEW_DIR / "gallery.png")
    display = Image.open(REFERENCES / "xpdisplayprop-1x.png").convert("RGB")
    time_date = Image.open(REFERENCES / "xptimedate.png").convert("RGB")
    crops = [display.crop((0, 30, 404, 130)), display.crop((0, 300, 404, 455)), time_date.crop((0, 60, 404, 130))]
    sheet = Image.new("RGB", (404, ours.height + sum(crop.height for crop in crops)), WINDOW_FACE)
    sheet.paste(ours, (0, 0))
    offset = ours.height
    for crop in crops:
        sheet.paste(crop, (0, offset))
        offset += crop.height
    sheet.save(PREVIEW_DIR / "controls-compare.png")

    assert (PREVIEW_DIR / "gallery.png").exists() and (PREVIEW_DIR / "controls-compare.png").exists()
