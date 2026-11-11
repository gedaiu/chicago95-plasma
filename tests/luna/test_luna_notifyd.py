import pytest
from conftest import load_script
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from .luna_tools_support import differing_fraction, grab_picture, hex_rgb, reference, save_preview

BALLOON_BOX = (416, 487, 741, 564)
BALLOON_SIZE = (325, 77)
CREAM = "#FFFFE1"
TEXT_MASKS = [(10, 4, 296, 24), (8, 24, 320, 72)]
CLASSIC_BEVEL = {(0x80, 0x80, 0x80), (0x40, 0x40, 0x40), (0xDF, 0xDF, 0xDF), (0xC0, 0xC0, 0xC0)}
TITLE = "Take a tour of Windows XP"
BODY = "To learn about the exciting new features in XP now, click here. To take the tour later, click All Programs."


@pytest.fixture
def notifyd(luna_look):
    module = load_script("chicago95-notifyd")
    module.desktop_entry.cache_clear()
    yield module
    module.desktop_entry.cache_clear()


def make_popup(notifyd, host=None, **overrides):
    fields = {
        "notification_id": 1,
        "app_name": "Test",
        "app_icon": "",
        "summary": TITLE,
        "body": BODY,
        "actions": [],
        "hints": {},
        "timeout_ms": 0,
    }
    popup = notifyd.NotificationPopup(notifyd.Notification(**{**fields, **overrides}), host)
    popup.show()
    return popup


@pytest.fixture
def popup(notifyd):
    popup = make_popup(notifyd)
    yield popup
    popup.close()


@pytest.fixture
def popup_picture(popup):
    return grab_picture(popup)


def test_luna_look_dispatches_to_the_balloon_chrome(notifyd):
    assert notifyd.popup_chrome().title_bar_class.__name__ == "LunaTitleRow"


def test_classic_look_keeps_the_classic_chrome(qt_app):
    notifyd = load_script("chicago95-notifyd")
    assert notifyd.popup_chrome().title_bar_class.__name__ == "TitleBar"


def test_balloon_is_the_xp_tray_balloon_width(popup):
    assert popup.width() == 320


def test_balloon_fill_is_ffffe1_right_inside_the_border_on_every_side_with_no_bevel_ring(popup_picture):
    width, height = popup_picture.size
    inside = [
        popup_picture.getpixel(point)
        for point in ((width // 2, 1), (1, height // 2), (width - 2, height // 2), (width // 2, height - 2))
    ]
    assert inside == [hex_rgb(CREAM)] * 4


def test_balloon_edge_midpoints_are_one_pixel_black(popup_picture):
    width, height = popup_picture.size
    assert [
        popup_picture.getpixel(point)
        for point in ((width // 2, 0), (width // 2, height - 1), (0, height // 2), (width - 1, height // 2))
    ] == [(0, 0, 0)] * 4


def test_balloon_corner_is_rounded_so_the_corner_pixel_is_not_black(popup_picture):
    assert popup_picture.getpixel((0, 0)) != (0, 0, 0)


def test_balloon_pixel_inside_the_border_is_the_cream_fill(popup_picture):
    assert popup_picture.getpixel((20, 1)) == hex_rgb(CREAM)


def test_title_row_has_no_gradient_or_navy_band_above_the_lettering(popup_picture):
    row = {popup_picture.getpixel((x, 3)) for x in range(40, 280)}
    assert row == {hex_rgb(CREAM)}


def test_close_box_is_16_square_with_the_tan_border_and_light_face(popup):
    box = popup.title_bar.close_button
    picture = grab_picture(box)
    assert (box.size().toTuple(), picture.getpixel((8, 0)), picture.getpixel((3, 3))) == (
        (16, 16),
        hex_rgb("#C7BEA6"),
        hex_rgb("#FFFFF5"),
    )


def test_close_box_x_is_two_strokes_in_aa9c87(popup):
    picture = grab_picture(popup.title_bar.close_button)
    centre_diagonals = [picture.getpixel((8 + step, 8 + step)) for step in (-2, 0, 2)]
    assert all(pixel[0] < 0xD0 for pixel in centre_diagonals)


def test_close_box_press_dismisses_the_balloon(notifyd, popup):
    dismissed = []
    popup.dismissed.connect(dismissed.append)
    QTest.mouseClick(popup.title_bar.close_button, Qt.LeftButton)
    assert dismissed == [notifyd.CLOSED_DISMISSED]


def test_balloon_has_no_content_icon_column_only_the_small_info_icon(popup):
    assert not popup.icon_label.isVisible()


CORNER_PIXEL_BUDGET = 0.20
CORNER_MASK_BOXES = [(8, 0, 320, 24)]


def test_balloon_top_left_corner_matches_the_xp_tour_balloon_within_antialiasing(popup_picture):
    expected = reference("xpdesktop.png").crop(BALLOON_BOX)
    save_preview("notifyd", popup_picture, expected)
    assert (
        differing_fraction(popup_picture.crop((0, 0, 320, 24)), expected.crop((0, 0, 320, 24)), CORNER_MASK_BOXES)
        < CORNER_PIXEL_BUDGET
    )


def test_balloon_title_is_the_summary_and_the_summary_row_is_gone(popup):
    assert (popup.title_bar.title_label.text(), popup.summary_label.isVisible()) == (TITLE, False)


def test_balloon_left_column_below_the_icon_matches_the_reference_border(popup_picture):
    expected = reference("xpdesktop.png").crop(BALLOON_BOX)
    rows = range(14, 40)
    assert [popup_picture.getpixel((0, y)) for y in rows] == [expected.getpixel((0, y)) for y in rows]


def test_title_text_starts_where_the_reference_title_does(popup, notifyd):
    assert popup.title_bar.title_label.x() + popup.layout().contentsMargins().left() == 452 - 416
