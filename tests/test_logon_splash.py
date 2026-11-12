"""What KSplash shows after log on, while Plasma starts: not the boot page again, but what the originals
show after their log on. 9x and 2000: the desktop's colour with the hourglass pointer. The boot page stays
for the boot screen's picture and the Control Panel's preview, which ask for it with booting."""

from PIL import Image
from PySide6.QtCore import QObject, Qt
from test_loading_screen_reference import render_splash, splash_view

W2K_BLUE = (0x3A, 0x6E, 0xA5)
LUNA_BLUE = (0x00, 0x4E, 0x98)


def test_after_a_2000_log_on_the_screen_is_the_desktop_colour(qt_app, tmp_path):
    image = render_splash(qt_app, tmp_path, booting=False, logonStyle="2000", desktopColor="#3A6EA5")
    assert {image.convert("RGB").getpixel(point) for point in [(10, 10), (320, 240), (320, 420)]} == {W2K_BLUE}


def test_after_a_classic_log_on_the_xp_boot_style_gives_way_to_the_desktop_colour(qt_app, tmp_path):
    image = render_splash(qt_app, tmp_path, booting=False, style="luna", logonStyle="classic", desktopColor="#004E98")
    assert image.convert("RGB").getpixel((320, 240)) == LUNA_BLUE


def test_after_a_classic_log_on_the_boot_picture_is_not_shown(qt_app, tmp_path):
    Image.new("RGB", (8, 8), "#ff0000").save(tmp_path / "boot.png")
    image = render_splash(
        qt_app,
        tmp_path,
        booting=False,
        style="classic",
        logonStyle="classic",
        desktopColor="#008080",
        picture=str(tmp_path / "boot.png"),
    )
    assert image.convert("RGB").getpixel((320, 240)) == (0, 0x80, 0x80)


def test_after_log_on_the_pointer_is_the_hourglass(qt_app, tmp_path):
    with splash_view(qt_app, tmp_path, booting=False, logonStyle="2000", desktopColor="#3A6EA5") as view:
        pointer = view.rootObject().findChild(QObject, "waitPointer")
        assert pointer.property("cursorShape") == Qt.CursorShape.WaitCursor


def test_while_booting_the_2000_page_shows_over_the_desktop_colour(qt_app, tmp_path):
    image = render_splash(qt_app, tmp_path, booting=True, logonStyle="2000", desktopColor="#3A6EA5")
    assert image.convert("RGB").getpixel((10, 10)) == (247, 247, 247)
