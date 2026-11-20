from conftest import REPO, run_bash_with_steps
from PIL import Image
from PySide6.QtCore import QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

ORB = REPO / "aero/plasmoids/org.chicago95.start/contents/ui/aero/WindowsOrb.qml"


def test_orb_displays_the_middle_40_rows_of_each_frame_without_recolouring(qt_app, tmp_path):
    strip = Image.new("RGB", (54, 162))
    strip.putdata([(x * 4, y, (x + y) % 256) for y in range(162) for x in range(54)])
    strip.save(tmp_path / "frames.png")
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(str(ORB)))
    assert not view.errors()
    item = view.rootObject()
    item.setProperty("source", QUrl.fromLocalFile(str(tmp_path / "frames.png")))
    view.show()
    try:
        for hovered, engaged, frame in [
            (False, False, 0),
            (True, False, 1),
            (True, True, 2),
            (False, True, 2),
            (False, False, 0),
        ]:
            item.setProperty("hovered", hovered)
            item.setProperty("engaged", engaged)
            QTest.qWait(360)
            image = view.grabWindow()
            expected = strip.crop((0, frame * 54 + 7, 54, frame * 54 + 47))
            resized = expected.resize((image.width(), image.height()), Image.Resampling.BILINEAR)
            tolerance = 0 if image.devicePixelRatio() == 1 else 2
            for y in range(image.height()):
                for x in range(image.width()):
                    actual = image.pixelColor(x, y).getRgb()[:3]
                    assert max(abs(a - b) for a, b in zip(actual, resized.getpixel((x, y)), strict=True)) <= tolerance
    finally:
        view.close()


def test_setup_recognises_saved_copies_of_windows_logos_and_keeps_custom_art(tmp_path):
    saved = tmp_path / "start-logo.png"
    saved.write_bytes((REPO / "plasmoids/org.chicago95.start/contents/images/logo-xp-16.png").read_bytes())
    command = 'SETUP_TASKBAR_STYLE=aero SETUP_START_LOGO="$HOME/start-logo.png" panel_start_logo'
    assert run_bash_with_steps(tmp_path, command) == ["xp"]
    saved.write_bytes(b"custom")
    assert run_bash_with_steps(tmp_path, command) == [str(saved)]
