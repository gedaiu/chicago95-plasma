import pytest
from conftest import load_script
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFont, QKeyEvent
from PySide6.QtTest import QTest

from .luna_tools_support import grab_picture, hex_rgb, save_preview

TEXT = "It looks like you're writing a letter. Would you like help?"
FACE, BORDER = hex_rgb("#FFFFE1"), hex_rgb("#000000")
BUTTON_BORDER = hex_rgb("#003C74")
EXPECTED_FACE_ENDS = ((252, 252, 251), (240, 240, 234))
BEVEL_GREYS = {(0x80, 0x80, 0x80), (0x40, 0x40, 0x40)}


@pytest.fixture
def clippy_script(luna_look):
    return load_script("chicago95-clippy")


@pytest.fixture
def balloon(clippy_script):
    balloon = clippy_script.make_balloon(QFont())
    balloon.show_tip(TEXT, QPoint(300, 400))
    yield balloon
    balloon.hide()


@pytest.fixture
def picture(balloon):
    return grab_picture(balloon)


def body_height(balloon):
    return balloon.ok_button.geometry().bottom() + 9


def pixels(image):
    return {(x, y): image.getpixel((x, y)) for x in range(image.width) for y in range(image.height)}


def test_luna_look_builds_the_luna_balloon(balloon):
    assert type(balloon).__name__ == "LunaBalloon"


def test_classic_look_builds_the_classic_balloon(qt_app):
    assert type(load_script("chicago95-clippy").make_balloon(QFont())).__name__ == "Balloon"


def test_balloon_face_is_the_xp_cream(balloon, picture):
    assert picture.getpixel((100, 4)) == FACE


def test_balloon_border_is_one_black_pixel(balloon, picture):
    top_edge = [picture.getpixel((100, y)) for y in range(3)]
    assert top_edge == [BORDER, FACE, FACE]


def test_balloon_corner_pixel_is_transparent_because_the_corner_is_rounded(balloon):
    assert balloon.grab().toImage().pixelColor(0, 0).alpha() == 0


def test_shadow_darkens_the_pixels_right_of_the_balloon(balloon, picture):
    edge_x = balloon.width() - 1
    assert picture.getpixel((edge_x, 40)) != (255, 255, 255)


def test_tail_hangs_below_the_body_toward_the_character(balloon, picture):
    tail_row = body_height(balloon) + 4
    assert BORDER in [picture.getpixel((x, tail_row)) for x in range(35, 49)]


def test_text_is_antialiased_with_intermediate_greys(balloon, picture):
    text_area = balloon.text_rect
    greys = {
        picture.getpixel((x, y))
        for x in range(text_area.left(), text_area.right())
        for y in range(text_area.top(), text_area.bottom())
        if picture.getpixel((x, y)) not in (FACE, BORDER)
    }
    assert len(greys) > 4


def test_ok_button_is_75_by_23_at_the_bottom_right(balloon):
    geometry = balloon.ok_button.geometry()
    assert (geometry.width(), geometry.height(), geometry.right() + 1 + 8 + 2) == (75, 23, balloon.width())


def test_ok_button_border_is_the_luna_blue(balloon, picture):
    geometry = balloon.ok_button.geometry()
    assert picture.getpixel((geometry.center().x(), geometry.top() + 1)) == BUTTON_BORDER


def test_ok_button_face_runs_from_white_to_f0f0ea(balloon, picture):
    geometry = balloon.ok_button.geometry()
    column = geometry.center().x() - 12
    top, bottom = geometry.top() + 4, geometry.top() + 17
    assert (picture.getpixel((column, top)), picture.getpixel((column, bottom))) == EXPECTED_FACE_ENDS


def test_no_classic_bevel_greys_anywhere(picture):
    assert not BEVEL_GREYS & set(pixels(picture).values())


@pytest.mark.parametrize("key", [Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter])
def test_key_closes_the_balloon(balloon, key):
    balloon.keyPressEvent(QKeyEvent(QKeyEvent.KeyPress, key, Qt.NoModifier))
    assert not balloon.isVisible()


def test_ok_click_closes_the_balloon(balloon):
    QTest.mouseClick(balloon.ok_button, Qt.LeftButton)
    assert not balloon.isVisible()


def test_balloon_preview_is_saved(balloon, picture):
    save_preview("clippy-luna", picture.resize((picture.width * 2, picture.height * 2)))
