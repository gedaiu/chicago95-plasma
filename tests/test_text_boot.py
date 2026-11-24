"""Text-loader geometry from the supplied 2000 video, plus preview phase ordering."""

import pytest
from conftest import REPO
from PIL import ImageChops
from PySide6.QtCore import QPointF, QUrl
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
        # Fully loaded cells use █, a continuous solid bar.
        assert actual.crop((0, 384, 640, 400)).getextrema() == ((170, 170),) * 3
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
        root.setProperty("statusStripPhase", 0)
        label = root.findChild(QObject, "sessionStatusText")
        assert label.property("text") == "Loading your personal settings..."
        QTest.qWait(150)
        assert label.property("text") == "Loading your personal settings..."
        before = qimage_to_pil(view.grabWindow()).convert("RGB")
        root.setProperty("stage", 5)
        assert label.property("text") == "Waiting for desktop readiness..."
        QTest.qWait(50)
        dialog = root.findChild(QObject, "startupStatus")
        after = qimage_to_pil(view.grabWindow()).convert("RGB")
        bounds = ImageChops.difference(before, after).getbbox()
        assert bounds is not None
        assert bounds[1] >= label.mapToScene(QPointF()).y()
        assert bounds[3] < dialog.mapToScene(QPointF(0, dialog.height())).y()


def test_2000_status_dialog_fits_the_loading_preview(qt_app, tmp_path):
    from PySide6.QtCore import QObject

    with splash_view(qt_app, tmp_path, booting=False, size=(320, 240), logonStyle="2000") as view:
        dialog = view.rootObject().findChild(QObject, "startupStatus")
        top_left = dialog.mapToScene(QPointF())
        bottom_right = dialog.mapToScene(QPointF(dialog.width(), dialog.height()))
        assert 0 < top_left.x() < bottom_right.x() < view.width()
        assert 0 < top_left.y() < bottom_right.y() < view.height()


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
