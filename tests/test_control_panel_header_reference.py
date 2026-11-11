"""Pixel tests: the Control Panel's header against Windows 98's (tests/references/win98controlpanel.png).

The header is a stack of bands: the menu bar, the toolbar and the Address box, each under an etched line
(a shadow row over a white row) with a raised grip at its left. In the original the menu bar and the Address
box are each 22 rows between etched lines 24 rows apart, and the Address box is a sunken white field with
18 white rows inside its frame. Ours is rendered at 1x and measured the same way.
"""

import pytest
from conftest import load_script
from reference import qimage_to_pil, screenshot

PROBE_X = 300  # clear of the menu text, the toolbar buttons and the grips
TITLE_BAR_BOTTOM = 22  # the original's rows above this are its title bar
BAND_PITCH = 24  # 22 rows of band and the 2 of etched line above it
ADDRESS_WHITE_ROWS = 18  # inside the Address box's 2px frame, which is 22 rows high


def is_original_shadow(colour):
    return all(100 <= channel <= 150 for channel in colour)


def is_white(colour, floor=250):
    return all(channel >= floor for channel in colour)


def original_etched_rows(image, top, bottom):
    """Rows where a shadow row is followed by a white one, at PROBE_X."""
    return [
        row
        for row in range(top, bottom)
        if is_original_shadow(image.getpixel((PROBE_X, row))) and is_white(image.getpixel((PROBE_X, row + 1)), 240)
    ]


def white_rows_from(image, row):
    count = 0
    while is_white(image.getpixel((PROBE_X, row + count))):
        count += 1
    return count


@pytest.fixture(scope="session")
def original():
    return screenshot("win98controlpanel")


@pytest.fixture(scope="module")
def ours(qt_app, tmp_path_factory):
    import chicago95ui

    control_panel = load_script("chicago95-control-panel")
    window = control_panel.ControlPanel(settings_path=tmp_path_factory.mktemp("settings") / "setup.conf")
    window.show()
    qt_app.processEvents()
    face = window.palette().window().color()
    light_shadow = chicago95ui.bevel_shades(face)
    return window, qimage_to_pil(window.header.grab().toImage()), (face.getRgb()[:3], light_shadow[1].getRgb()[:3])


def our_etched_rows(image, shadow):
    return [
        row
        for row in range(image.height - 1)
        if image.getpixel((PROBE_X, row)) == shadow and image.getpixel((PROBE_X, row + 1)) == (255, 255, 255)
    ]


def test_the_original_menu_bar_and_address_box_are_bands_of_22_rows_between_etched_lines(original):
    rows = original_etched_rows(original, TITLE_BAR_BOTTOM, 76)

    assert [after - before for before, after in zip(rows, rows[1:])] == [BAND_PITCH, BAND_PITCH]


def test_the_originals_address_box_has_18_white_rows_inside_its_frame(original):
    rows = original_etched_rows(original, TITLE_BAR_BOTTOM, 76)

    assert white_rows_from(original, rows[1] + 4) == ADDRESS_WHITE_ROWS


def test_our_menu_bar_and_address_box_are_bands_of_22_rows_between_etched_lines(ours):
    _window, image, (_face, shadow) = ours
    rows = our_etched_rows(image, shadow)

    assert (rows[1] - rows[0], rows[-1] - rows[-2]) == (BAND_PITCH, BAND_PITCH)


def test_our_header_has_an_etched_line_above_every_band_and_one_closing_it(ours):
    _window, image, (_face, shadow) = ours

    assert len(our_etched_rows(image, shadow)) == 4


def test_our_address_box_has_18_white_rows_inside_its_frame(ours):
    window, image, (_face, shadow) = ours
    address_top = our_etched_rows(image, shadow)[2] + 2

    assert (white_rows_from(image, address_top + 2), window.address_bar.box.height()) == (ADDRESS_WHITE_ROWS, 22)


def test_our_drop_down_button_is_16_by_18_in_the_address_box(ours):
    window, _image, _colours = ours

    assert (window.address_bar.dropdown.width(), window.address_bar.dropdown.height()) == (16, 18)


TOOLBAR_HEIGHT = 40
TOOLBAR_PITCH = 42  # 40 rows of toolbar between etched lines, in Internet Explorer 4 (tests/references/ie4.png)


def test_internet_explorer_4s_toolbar_band_is_40_rows_between_etched_lines():
    rows = original_etched_rows(screenshot("ie4"), TITLE_BAR_BOTTOM, 120)

    assert [after - before for before, after in zip(rows, rows[1:])] == [BAND_PITCH, TOOLBAR_PITCH, BAND_PITCH]


def test_our_toolbar_band_is_40_rows_between_etched_lines(ours):
    _window, image, (_face, shadow) = ours
    rows = our_etched_rows(image, shadow)

    assert (rows[2] - rows[1]) == TOOLBAR_PITCH


LOGO_BOX_WIDTH = 38  # the black logo box at the right of the original's menu band


def test_each_band_has_one_raised_grip_bar_white_then_face_then_shadow(ours):
    _window, image, (face, shadow) = ours
    etched = our_etched_rows(image, shadow)
    centres = [(top + bottom) // 2 for top, bottom in zip(etched, etched[1:])]
    columns = [tuple(image.getpixel((x, row)) for x in range(2, 10)) for row in centres]

    assert columns == [((255, 255, 255), face, face, face, shadow, face, face, face)] * 3


def test_band_contents_start_16_pixels_in_like_the_originals(ours):
    window, _image, _colours = ours

    assert (window.menu_bar.x(), window.address_bar.x()) == (16, 16)


def test_menu_band_ends_in_a_black_logo_box_as_wide_as_the_originals(ours):
    window, image, _colours = ours
    box = window.logo_box
    right_edge = image.getpixel((image.width - 3, box.y() + box.height() // 2))
    inside = {
        image.getpixel((x, y))
        for x in range(image.width - box.width() + 2, image.width - 2)
        for y in range(box.y() + 2, box.y() + box.height() - 2)
    }

    assert (box.width(), right_edge, len(inside) > 1) == (LOGO_BOX_WIDTH, (0, 0, 0), True)


def test_address_box_shows_a_16_pixel_icon_before_the_path(ours):
    window, _image, _colours = ours

    assert (window.address_bar.icon.pixmap().isNull(), window.address_bar.icon.width()) == (False, 16)


def test_address_drop_down_is_a_raised_button(ours):
    window, _image, (_face, shadow) = ours
    button = qimage_to_pil(window.address_bar.dropdown.grab().toImage())
    middle = button.height // 2

    assert (button.getpixel((0, middle)), button.getpixel((button.width - 1, middle))) == ((255, 255, 255), (0, 0, 0))


def ink_rows(image, left, right, top, bottom, face):
    """Rows with anything drawn on the button's face: an enabled label is black, a disabled one white over shadow."""
    return [y for y in range(top, bottom) if any(image.getpixel((x, y))[:3] != face for x in range(left, right))]


def test_toolbar_buttons_are_40_tall_at_least_48_wide_and_their_labels_are_not_cut(ours):
    window, _image, (face, _shadow) = ours
    report = []
    for name in ("Back", "Forward", "Up", "Views"):
        button = window.toolbar_buttons[name]
        picture = qimage_to_pil(button.grab().toImage())
        label_rows = ink_rows(picture, 2, button.main_width() - 2, 24, button.height(), face)
        report.append(
            (button.height(), button.main_width() >= 48, label_rows != [] and label_rows[-1] <= button.height() - 3)
        )

    assert report == [(TOOLBAR_HEIGHT, True, True)] * 4


def test_back_forward_and_views_carry_a_small_menu_arrow_and_up_does_not(ours):
    window, _image, _colours = ours

    assert [window.toolbar_buttons[name].has_menu for name in ("Back", "Forward", "Up", "Views")] == [
        True,
        True,
        False,
        True,
    ]


def test_toolbar_icons_sit_near_the_top_of_the_band_like_internet_explorers(ours):
    window, _image, (face, _shadow) = ours
    picture = qimage_to_pil(window.toolbar_buttons["Up"].grab().toImage())
    icon_rows = ink_rows(picture, 2, window.toolbar_buttons["Up"].main_width() - 2, 0, 24, face)

    assert (icon_rows != [], 2 <= icon_rows[0] <= 6) == (True, True)


def dark_runs_per_row(image, box):
    left, top, right, bottom = box
    rows = []
    for y in range(top, bottom):
        dark = [x for x in range(left, right) if sum(image.getpixel((x, y))[:3]) // 3 < 100]
        rows.append((dark[0], dark[-1]) if dark else None)
    return rows


def test_address_drop_down_arrow_is_a_centred_7_5_3_1_triangle_and_nothing_else(ours):
    window, _image, _colours = ours
    button = window.address_bar.dropdown
    image = qimage_to_pil(button.grab().toImage())
    inside = dark_runs_per_row(image, (1, 1, button.width() - 1, button.height() - 1))
    arrow = [run for run in inside if run]
    widths = [right - left + 1 for left, right in arrow]
    centres = {left + right for left, right in arrow}

    assert (widths, len(centres), sum(1 for run in inside if run)) == ([7, 5, 3, 1], 1, 4)


MENU_TEXT_ROW = 8  # the menu captions' first ink row below the band's etched shadow row, in the original (23 -> 31)


def test_the_original_menu_captions_start_8_rows_below_the_bands_etched_line(original):
    etched = original_etched_rows(original, TITLE_BAR_BOTTOM, 60)[0]
    file_rows = [
        y
        for y in range(etched, etched + BAND_PITCH)
        if any(sum(original.getpixel((x, y))) < 200 for x in range(23, 40))
    ]
    assert file_rows[0] == etched + MENU_TEXT_ROW, (etched, file_rows)


def test_our_menu_captions_start_8_rows_below_the_bands_etched_line_like_the_originals(ours):
    """Centred in the 22-row band, as the original's; Qt's menu bar sits them against the top otherwise."""
    window, image, (_face, shadow) = ours
    etched = our_etched_rows(image, shadow)[0]
    left = window.menu_bar.x() + window.menu_bar.actionGeometry(window.menu_bar.actions()[0]).left()
    file_rows = [
        y
        for y in range(etched, etched + BAND_PITCH)
        if any(image.getpixel((x, y)) == (0, 0, 0) for x in range(left, left + 24))
    ]
    assert file_rows[0] == etched + MENU_TEXT_ROW, (etched, file_rows)


def toolbar_picture(button, qt_app, **state):
    from PySide6.QtCore import Qt

    button.setAttribute(Qt.WA_UnderMouse, state.get("hover", False))
    button.setDown(state.get("down", False))
    qt_app.processEvents()
    picture = qimage_to_pil(button.grab().toImage())
    button.setAttribute(Qt.WA_UnderMouse, False)
    button.setDown(False)
    return picture


def icon_colours(picture, button, face):
    return {picture.getpixel((x, y))[:3] for x in range(2, button.main_width() - 2) for y in range(0, 24)} - {face}


def test_toolbar_icons_are_grey_until_the_pointer_is_over_them_as_internet_explorer_4_drew_them(ours, qt_app):
    window, _image, (face, _shadow) = ours
    button = window.toolbar_buttons["Views"]  # enabled at home, where Back, Forward and Up are not
    plain = icon_colours(toolbar_picture(button, qt_app), button, face)
    hovered = icon_colours(toolbar_picture(button, qt_app, hover=True), button, face)
    assert plain and all(r == g == b for r, g, b in plain), sorted(plain)[:5]
    assert any(not (r == g == b) for r, g, b in hovered), "the hovered icon is in colour"


def test_pressed_toolbar_button_sinks_like_a_push_button_and_its_picture_moves_a_pixel(ours, qt_app):
    """Held down: the raised frame turns sunken (shadow top-left, white bottom-right) and the icon and
    label move a pixel down and right, as the push buttons do."""
    window, _image, (face, shadow) = ours
    button = window.toolbar_buttons["Views"]
    raised = toolbar_picture(button, qt_app, hover=True)
    pressed = toolbar_picture(button, qt_app, hover=True, down=True)
    right, bottom = button.main_width() - 1, button.height() - 1
    assert (
        pressed.getpixel((0, 10))[:3],
        pressed.getpixel((right, 10))[:3],
        pressed.getpixel((10, 0))[:3],
        pressed.getpixel((10, bottom))[:3],
    ) == (shadow, (255, 255, 255), shadow, (255, 255, 255))
    assert (raised.getpixel((0, 10))[:3], raised.getpixel((right, 10))[:3]) == ((255, 255, 255), shadow)
    raised_rows = ink_rows(raised, 2, right - 1, 1, 24, face)  # below the frame's top row
    pressed_rows = ink_rows(pressed, 2, right - 1, 1, 24, face)
    assert (pressed_rows[0], pressed_rows[-1]) == (raised_rows[0] + 1, raised_rows[-1] + 1), (raised_rows, pressed_rows)
