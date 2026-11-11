import pytest
from PySide6.QtGui import QAction, QColor, QIcon, QPixmap
from PySide6.QtWidgets import QMenu

from .luna_tools_support import grab_picture, hex_rgb, save_preview

ROW_HEIGHT = 21
SEPARATOR_HEIGHT = 6
ICON_COLUMN = 28


@pytest.fixture
def menu(luna_look):
    solid = QPixmap(16, 16)
    solid.fill(QColor("#FF0000"))
    menu = QMenu()
    menu.addAction(QAction(QIcon(solid), "Open", menu))
    disabled = QAction("Disabled", menu)
    disabled.setEnabled(False)
    menu.addAction(disabled)
    menu.addSeparator()
    checked = QAction("Checked", menu)
    checked.setCheckable(True)
    checked.setChecked(True)
    menu.addAction(checked)
    submenu = menu.addMenu("More")
    submenu.addAction("Inner")
    menu.setActiveAction(menu.actions()[0])
    menu.show()
    yield menu
    menu.close()


@pytest.fixture
def picture(menu):
    image = grab_picture(menu)
    save_preview("qmenu", image)
    return image


def row_centre(menu, index):
    return menu.actionGeometry(menu.actions()[index]).center().y()


def test_menu_border_is_one_pixel_acd899_on_every_side(menu, picture):
    width, height = picture.size
    sides = [picture.getpixel(point) for point in ((0, 40), (width - 1, 40), (40, 0), (40, height - 1))]
    assert sides == [hex_rgb("#ACA899")] * 4


def test_menu_panel_inside_the_border_is_white_with_no_bevel(menu, picture):
    width, height = picture.size
    inner = [picture.getpixel(point) for point in ((1, 40), (width - 2, 40), (40, 1), (40, height - 2))]
    assert inner == [hex_rgb("#FFFFFF")] * 4


def test_menu_rows_are_21_high_and_separators_6_high(menu):
    heights = [menu.actionGeometry(action).height() for action in menu.actions()[:3]]
    assert heights == [ROW_HEIGHT, ROW_HEIGHT, SEPARATOR_HEIGHT]


def test_highlighted_row_is_316ac5_to_the_edge_without_an_outline(menu, picture):
    geometry = menu.actionGeometry(menu.actions()[0])
    samples = [
        picture.getpixel((x, y))
        for x, y in ((geometry.left() + 1, geometry.top()), (geometry.right() - 2, geometry.bottom()))
    ]
    assert samples == [hex_rgb("#316AC5")] * 2


def test_icon_column_is_plain_white_below_the_highlight_with_no_gradient(menu, picture):
    geometry = menu.actionGeometry(menu.actions()[3])
    column = {
        picture.getpixel((x, geometry.top() + 2)) for x in range(geometry.left() + 2, geometry.left() + ICON_COLUMN - 2)
    }
    assert column == {hex_rgb("#FFFFFF")}


def darkest_channel_sum(picture, geometry):
    row = picture.crop((geometry.left() + ICON_COLUMN, geometry.top(), geometry.right() - 4, geometry.bottom()))
    return min(sum(colour) for _count, colour in row.getcolors(maxcolors=1 << 16))


def test_disabled_row_text_is_grey_where_an_enabled_row_is_black(menu, picture):
    disabled, enabled = (menu.actionGeometry(menu.actions()[index]) for index in (1, 3))
    assert (darkest_channel_sum(picture, disabled) > 420, darkest_channel_sum(picture, enabled) < 300) == (True, True)


def test_separator_is_grey_over_white_starting_after_the_icon_column(menu, picture):
    geometry = menu.actionGeometry(menu.actions()[2])
    x = geometry.left() + ICON_COLUMN + 10
    assert [picture.getpixel((x, geometry.top() + 2)), picture.getpixel((x, geometry.top() + 3))] == [
        hex_rgb("#ACA899"),
        hex_rgb("#FFFFFF"),
    ]
    assert picture.getpixel((geometry.left() + ICON_COLUMN - 6, geometry.top() + 2)) == hex_rgb("#FFFFFF")


def test_check_mark_is_drawn_inside_the_icon_column(menu, picture):
    geometry = menu.actionGeometry(menu.actions()[3])
    column = picture.crop((geometry.left() + 2, geometry.top(), geometry.left() + ICON_COLUMN - 2, geometry.bottom()))
    assert len(column.getcolors(maxcolors=1 << 16)) > 1


def test_submenu_arrow_is_black_on_a_plain_row(menu, picture):
    geometry = menu.actionGeometry(menu.actions()[4])
    strip = picture.crop((geometry.right() - 14, geometry.top(), geometry.right() - 2, geometry.bottom()))
    assert (0, 0, 0) in [colour for _count, colour in strip.getcolors(maxcolors=1 << 16)]
