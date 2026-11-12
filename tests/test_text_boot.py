"""Text-loader geometry from the supplied 2000 video, plus preview phase ordering."""
import pytest
from conftest import REPO
from PIL import Image, ImageChops
from PySide6.QtCore import QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from reference import qimage_to_pil
from test_loading_screen_reference import splash_view


@pytest.mark.parametrize("nt,name", [(False, "Windows 95"), (False, "Windows 98"), (True, "Windows 2000")])
def test_text_boot_renders_black_console_and_expected_caption(qt_app, tmp_path, nt, name):
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(640, 480)
    view.setInitialProperties({"ntLoader": nt, "systemName": name, "progress": 1.0})
    view.setSource(QUrl.fromLocalFile(str(REPO / "splash/chicago95.splashscreen/contents/splash/TextBoot.qml")))
    assert not view.errors()
    view.show()
    QTest.qWait(50)
    actual = qimage_to_pil(view.grabWindow()).convert("RGB")
    actual.save(tmp_path / "text-boot.png")
    assert actual.getpixel((320, 240)) == (0, 0, 0)
    if nt:
        reference = Image.open(REPO / "tests/references/w2k-video-text-loader-523.png")
        # Isolate the actual loader bar, excluding the video's borders and text.
        expected = reference.crop((159, 586, 1120, 611)).resize((640, 16)).convert("L")
        ours = actual.crop((0, 384, 640, 400)).convert("L")
        def binary(im):
            return im.point(lambda pixel: 255 if pixel > 100 else 0)
        diff = ImageChops.difference(binary(expected), binary(ours))
        diff.save(tmp_path / "loader-bar-diff.png")
        assert diff.histogram()[255] / (640 * 16) < .25
    else:
        assert actual.crop((0, 0, 300, 25)).getbbox() is not None
        assert actual.crop((0, 32, 640, 480)).getbbox() is None
    view.close()


@pytest.mark.parametrize("style", ["classic", "2000"])
def test_preview_text_phase_precedes_bitmap_and_is_never_a_login_phase(qt_app, tmp_path, style):
    with splash_view(qt_app, tmp_path, style=style) as view:
        root = view.rootObject()
        assert not root.property("textBoot")
        root.setProperty("textBootDuration", 80)
        root.playBootPreview()
        assert root.property("textBoot")
        QTest.qWait(120)
        assert not root.property("textBoot")
        assert root.property("booting")
        root.setProperty("booting", False)
        assert not root.property("textBoot")
