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
        assert diff.histogram()[255] / (640 * 16) < 0.25
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


def test_text_loader_visibly_fills_before_graphical_boot(qt_app, tmp_path):
    with splash_view(qt_app, tmp_path, style="2000") as view:
        root = view.rootObject()
        root.setProperty("textBootDuration", 250)
        root.setProperty("bitmapDuration", 100)
        root.playBootPreview()
        assert root.property("textBootProgress") == 0
        QTest.qWait(120)
        assert 0 < root.property("textBootProgress") < 1
        assert root.property("textBoot")
        QTest.qWait(170)
        assert root.property("textBootProgress") == 1
        assert not root.property("textBoot")
        assert root.property("booting")
        QTest.qWait(140)
        assert not root.property("booting")


def test_live_2000_dialog_waits_for_session_stage_not_elapsed_time(qt_app, tmp_path):
    from PySide6.QtCore import QObject

    with splash_view(qt_app, tmp_path, booting=False, logonStyle="2000") as view:
        root = view.rootObject()
        root.setProperty("statusBanner", QUrl.fromLocalFile(str(REPO / "data/2000-logon-banner.png")))
        label = root.findChild(QObject, "sessionStatusText")
        assert label.property("text") == "Starting your desktop..."
        QTest.qWait(150)
        assert label.property("text") == "Starting your desktop..."
        root.setProperty("stage", 5)
        assert label.property("text") == "Waiting for desktop readiness..."
        root.setProperty("sessionStatus", "Preparing network connections...")  # deterministic visual fixture only
        QTest.qWait(50)
        actual = qimage_to_pil(view.grabWindow()).convert("RGB").crop((111, 111, 529, 255))
        expected = Image.open(REPO / "tests/references/w2k-video-startup-dialog-544.png")
        expected = expected.crop((326, 166, 953, 382)).resize(actual.size).convert("RGB")
        from PIL import ImageDraw

        for im in (actual, expected):
            # The supplied video uses a different banner variant; compare frame and body.
            draw = ImageDraw.Draw(im)
            draw.rectangle((3, 3, 110, 20), fill="black")
            draw.rectangle((3, 21, 414, 98), fill="black")
            draw.rectangle((10, 108, 290, 132), fill="black")
            draw.rectangle((200, 125, 230, 144), fill="black")  # reference mouse pointer
        actual.save(tmp_path / "status-actual.png")
        expected.save(tmp_path / "status-expected.png")
        diff = ImageChops.difference(actual, expected)
        diff.save(tmp_path / "status-diff.png")
        worst = ImageChops.lighter(ImageChops.lighter(*diff.split()[:2]), diff.split()[2])
        assert sum(worst.histogram()[41:]) / (actual.width * actual.height) < 0.2


def test_control_panel_boot_rehearsal_uses_current_2000_settings(qt_app):
    from conftest import load_script

    panel = load_script("chicago95-control-panel")
    preview = panel.LoadingPreview()
    preview.refresh(
        {
            "BOOT_STYLE": "2000",
            "LOGIN_STYLE": "2000",
            "LOOK": "2000",
            "START_MENU_STYLE": "2000",
            "BANNER_TEXT": "Windows 2000",
            "COMPANY": "Microsoft",
        }
    )
    preview.open_boot_test()
    window = preview.boot_test_window
    screen = window.findChild(panel.LoadingPreview)
    assert screen.dialog().property("textBoot")
    assert screen.dialog().property("textBootDuration") == 2500
    assert not screen.errors()
    window.close()
    preview.close()
