"""Rendered regression checks for loader fill, aspect ratio and live status content.

The external video comparison is in test_text_boot.py. These checks cover states
that the reference still does not contain, without approving generated goldens.
"""

from contextlib import contextmanager

import pytest
from conftest import REPO
from PIL import Image, ImageChops
from PySide6.QtCore import QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from reference import qimage_to_pil
from test_loading_screen_reference import splash_view

SPLASH = REPO / "splash/chicago95.splashscreen/contents/splash"


@contextmanager
def rendered(qt_app, name, size, properties):
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(*size)
    view.setInitialProperties(properties)
    view.setSource(QUrl.fromLocalFile(str(SPLASH / name)))
    assert not view.errors(), [error.toString() for error in view.errors()]
    view.show()
    QTest.qWait(50)
    try:
        yield view
    finally:
        view.close()


def grab(view, path):
    image = qimage_to_pil(view.grabWindow()).convert("RGB")
    image.save(path)
    return image


def assert_image(actual, expected, folder, name, tolerance=0):
    actual.save(folder / f"{name}-actual.png")
    expected.save(folder / f"{name}-expected.png")
    diff = ImageChops.difference(actual, expected)
    diff.save(folder / f"{name}-diff.png")
    assert max(channel[1] for channel in diff.getextrema()) <= tolerance


@pytest.mark.parametrize("size", [(640, 480), (1280, 960), (1280, 720)])
@pytest.mark.parametrize("progress", [0, 0.25, 0.5, 1])
def test_loader_fill_pixels_and_letterboxing(qt_app, tmp_path, size, progress):
    with rendered(qt_app, "TextBoot.qml", size, {"ntLoader": True, "progress": progress}) as view:
        actual = grab(view, tmp_path / "screen.png")
        scale = min(size[0] / 640, size[1] / 480)
        left = (size[0] - 640 * scale) / 2
        top = (size[1] - 480 * scale) / 2
        # Sample each segment's interior, independent of subpixel edge rasterization.
        row = Image.new("RGB", (71, 1))
        expected = Image.new("RGB", (71, 1))
        for index in range(71):
            row.putpixel((index, 0), actual.getpixel((round(left + (index * 9 + 2) * scale), round(top + 392 * scale))))
            expected.putpixel((index, 0), (170, 170, 170) if index < int(progress * 72) else (51, 51, 51))
            gap = actual.getpixel((round(left + (index * 9 + 7) * scale), round(top + 392 * scale)))
            assert gap == (0, 0, 0), f"Filled gap after segment {index}"
        assert_image(row, expected, tmp_path, "segment-faces")
        if left:
            assert actual.crop((0, 0, int(left), size[1])).getbbox() is None
            assert actual.crop((size[0] - int(left), 0, size[0], size[1])).getbbox() is None


def test_loader_progress_changes_only_the_bar(qt_app, tmp_path):
    with rendered(qt_app, "TextBoot.qml", (640, 480), {"ntLoader": True, "progress": 0}) as view:
        before = grab(view, tmp_path / "empty.png")
        view.rootObject().setProperty("progress", 1)
        QTest.qWait(50)
        after = grab(view, tmp_path / "full.png")
        diff = ImageChops.difference(before, after)
        diff.save(tmp_path / "fill-diff.png")
        assert diff.getbbox() == (0, 384, 640, 400)


def test_status_banner_is_visible_and_not_stretched(qt_app, tmp_path):
    banner = REPO / "data/2000-logon-banner.png"
    with rendered(qt_app, "StartupStatus.qml", (417, 144), {"banner": QUrl.fromLocalFile(str(banner))}) as view:
        image = grab(view, tmp_path / "status.png")
        # Same 411px width: PreserveAspectCrop should remove 8 rows at each end,
        # never compress the wordmark vertically to fit the 77px status slot.
        expected = Image.open(banner).convert("RGB").crop((0, 8, 411, 85))
        assert_image(image.crop((3, 21, 414, 98)), expected, tmp_path, "banner")


def test_live_status_update_changes_only_the_message(qt_app, tmp_path):
    banner = QUrl.fromLocalFile(str(REPO / "data/2000-logon-banner.png"))
    with rendered(
        qt_app, "StartupStatus.qml", (417, 144), {"banner": banner, "statusText": "Starting your desktop..."}
    ) as view:
        before = grab(view, tmp_path / "starting.png")
        view.rootObject().setProperty("statusText", "Waiting for desktop readiness...")
        QTest.qWait(50)
        after = grab(view, tmp_path / "waiting.png")
        diff = ImageChops.difference(before, after)
        diff.save(tmp_path / "status-update-diff.png")
        box = diff.getbbox()
        assert box is not None, "Status update was not painted"
        assert box[0] >= 14 and box[1] >= 113 and box[2] < 414 and box[3] < 141


def test_text_overlay_disappears_before_graphical_boot(qt_app, tmp_path):
    with splash_view(qt_app, tmp_path / "theme", style="2000") as view:
        root = view.rootObject()
        graphical = grab(view, tmp_path / "graphical.png")
        root.setProperty("textBoot", True)
        root.setProperty("textBootProgress", 0.5)
        QTest.qWait(50)
        text = grab(view, tmp_path / "text.png")
        assert text.getpixel((320, 240)) == (0, 0, 0)
        assert graphical.getpixel((320, 240)) != (0, 0, 0)
        root.setProperty("textBoot", False)
        QTest.qWait(50)
        restored = grab(view, tmp_path / "restored.png")
        assert_image(restored, graphical, tmp_path, "graphical-restored")
