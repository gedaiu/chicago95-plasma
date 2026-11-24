"""Capture Device Manager chrome with a fixed device inventory and guest DPI."""

import argparse
import os
import sys
from pathlib import Path
from threading import Event

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import load_script  # noqa: E402
from PIL import Image  # noqa: E402
from PySide6.QtCore import QPoint, QRect, Qt  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtTest import QSignalSpy, QTest  # noqa: E402
from PySide6.QtWidgets import QToolBar  # noqa: E402
from reference import qimage_to_pil  # noqa: E402
from render_properties import aero_style  # noqa: E402
from showcase import themed  # noqa: E402
from test_devmgr import INVENTORY, wait_for_scan  # noqa: E402


def actions_bounds(window):
    layout = window.layout()
    row = next(
        item
        for i in range(layout.count())
        if (item := layout.itemAt(i).layout()) is not None and item.indexOf(window.properties_button) >= 0
    )
    bounds = QRect()
    for index in range(row.count()):
        button = row.itemAt(index).widget()
        if button is not None:
            bounds = bounds.united(button.geometry())
    return bounds.x(), bounds.y(), bounds.right() + 1, bounds.bottom() + 1


def capture_refresh_states(window, output):
    refresh = window.refresh_button
    outside = window.tree.viewport()
    scale = window.devicePixelRatioF()
    bounds = refresh.geometry()
    crop = tuple(round(value * scale) for value in (bounds.x(), bounds.y(), bounds.right() + 1, bounds.bottom() + 1))

    def grab():
        return qimage_to_pil(window.grab().toImage()).crop(crop)

    window.tree.setFocus()
    QTest.mouseMove(outside, outside.rect().center())
    idle = grab()
    strip = Image.new("RGB", (idle.width * 8, idle.height))
    strip.paste(idle, (0, 0))

    def sample(index):
        strip.paste(grab(), (index * idle.width, 0))

    QTest.mouseMove(refresh, refresh.rect().center())
    sample(1)
    QTest.mouseClick(refresh, Qt.LeftButton)
    QTest.mouseMove(outside, outside.rect().center())
    assert refresh.hasFocus()
    sample(2)
    QTest.keyPress(refresh, Qt.Key_Space)
    assert refresh.isDown()
    sample(3)
    QTest.keyRelease(refresh, Qt.Key_Space)
    assert not refresh.isDown()
    sample(4)

    camera = window.windowHandle()
    button_pos = refresh.mapTo(window, refresh.rect().center())
    outside_pos = outside.mapTo(window, outside.rect().center())
    clicks = QSignalSpy(refresh.clicked)
    QTest.mouseMove(camera, button_pos)
    QTest.mousePress(camera, Qt.LeftButton, pos=button_pos)
    assert refresh.isDown()
    sample(5)
    QTest.mouseMove(camera, outside_pos)
    assert not refresh.isDown()
    sample(6)
    QTest.mouseRelease(camera, Qt.LeftButton, pos=outside_pos)
    assert refresh.hasFocus() and clicks.count() == 0
    sample(7)
    strip.save(Path(output).with_name("refresh-states.png"))


def capture_toolbar_press(window, button, sample):
    camera = window.windowHandle()
    inside = button.mapTo(window, button.rect().center())
    outside = window.tree.mapTo(window, window.tree.rect().center())
    QTest.mouseMove(camera, outside)
    sample(0)
    QTest.mouseMove(camera, inside)
    sample(1)
    QTest.mousePress(camera, Qt.LeftButton, pos=inside)
    assert button.isDown()
    sample(2)
    QTest.mouseMove(camera, outside)
    assert not button.isDown()
    sample(3)
    QTest.mouseRelease(camera, Qt.LeftButton, pos=outside)
    sample(4)
    return inside, outside


def capture_console_tree_states(window, output, height, origin):
    toolbar = window.findChild(QToolBar)
    button = toolbar.widgetForAction(window.scope_action)
    scale = window.devicePixelRatioF()
    if origin is None:
        left = round(button.mapTo(window, QPoint()).x() * scale) - 4
        top = round(toolbar.mapTo(window, QPoint()).y() * scale)
    else:
        left, top = origin
    strip = Image.new("RGB", (27 * 7, height))

    def sample(index):
        picture = qimage_to_pil(window.grab().toImage())
        strip.paste(picture.crop((left, top, left + 27, top + height)), (27 * index, 0))

    inside, outside = capture_toolbar_press(window, button, sample)
    assert not window.scope_action.isChecked()
    QTest.mouseClick(window.windowHandle(), Qt.LeftButton, pos=inside)
    QTest.mouseMove(window.windowHandle(), outside)
    assert window.scope_action.isChecked() and window.scope_tree.isVisible()
    sample(5)
    QTest.mouseClick(window.windowHandle(), Qt.LeftButton, pos=inside)
    QTest.mouseMove(window.windowHandle(), outside)
    assert not window.scope_action.isChecked() and window.scope_tree.isHidden()
    sample(6)
    strip.save(output)


SCAN_BOUNDS = (135, 23, 162, 46)


def capture_scan_states(window, output):
    toolbar = window.findChild(QToolBar)
    button = toolbar.widgetForAction(window.scan_toolbar_action)
    assert button.isVisible()
    strip = Image.new("RGB", (27 * 5, 23))

    def sample(index):
        picture = qimage_to_pil(window.grab().toImage())
        strip.paste(picture.crop(SCAN_BOUNDS), (27 * index, 0))

    scans = QSignalSpy(window.scan_action.triggered)
    inside, _ = capture_toolbar_press(window, button, sample)
    assert scans.count() == 0
    release = Event()
    load = window.load

    def pending_inventory():
        if not release.wait(5):
            raise RuntimeError("Scan progress capture timed out")
        return load()

    window.load = pending_inventory
    try:
        QTest.mouseClick(window.windowHandle(), Qt.LeftButton, pos=inside)
        assert scans.count() == 1
        progress = window.scan_progress
        assert progress.isVisible()
        qimage_to_pil(progress.grab().toImage()).save(Path(output).with_name("scan-progress.png"))
    finally:
        release.set()
        wait_for_scan(window)
    strip.save(output)


def capture_aero_branches(window, output):
    bounds = ((6, 59, 19, 70), (26, 77, 39, 88))
    camera = window.windowHandle()
    child = window.tree.topLevelItem(0).child(0)
    strip = Image.new("RGB", (39, 11))

    def sample(box):
        return qimage_to_pil(window.grab().toImage()).convert("RGB").crop(box)

    for index, box in enumerate(bounds):
        # Use the bottom edge of the 18-pixel branch cell, below the reference crop.
        left, top, right, bottom = box
        idle = sample(box)
        QTest.mouseMove(camera, QPoint(right - 2, bottom + 1))
        hovered = sample(box)
        strip.paste(hovered, (index * 13, 0))
        QTest.mouseMove(camera, QPoint(86, top + 5))
        assert sample(box).tobytes() == idle.tobytes(), "Hovering the label must clear the branch glow"
        assert hovered.tobytes() != idle.tobytes(), "Hovering the branch must show the glow"

    QTest.mouseMove(camera, QPoint(32, 83))
    QTest.mousePress(camera, Qt.LeftButton, pos=QPoint(32, 83))
    assert child.isExpanded()
    QTest.mouseMove(camera, QPoint(37, 89))
    strip.paste(sample(bounds[1]), (26, 0))
    QTest.mouseMove(camera, QPoint(86, 83))
    held_outside = sample(bounds[1])
    QTest.mouseRelease(camera, Qt.LeftButton, pos=QPoint(86, 83))
    assert child.isExpanded()
    assert sample(bounds[1]).tobytes() == held_outside.tobytes()
    QTest.mouseClick(camera, Qt.LeftButton, pos=QPoint(32, 83))
    assert not child.isExpanded()
    strip.save(output)


def render(look, scale, output, width=None, height=None, *,
           refresh_states=False, console_tree_states=False, console_tree_origin=None,
           aero_branches=False, root_context=False, scan_states=False):
    import chicago95ui

    os.environ["QT_SCALE_FACTOR"] = scale
    app = chicago95ui.make_app("Device Manager")
    context = aero_style(app) if look == "aero" else themed(app, look)
    with context:
        if look == "aero":
            chicago95ui.apply_style(app)
            QIcon.setThemeName("Windows-7-SVG")
        module = load_script("chicago95-devmgr")
        snapshot = module.snapshot_from(INVENTORY)
        window = module.DeviceManagerWindow(load=lambda: snapshot)
        try:
            if width is not None:
                window.resize(round(int(width) / float(scale)), round(int(height) / float(scale)))
            window.show()
            window.refresh()
            app.processEvents()
            if scan_states:
                assert not window.scan_toolbar_action.isVisible()
                qimage_to_pil(window.grab().toImage()).crop(SCAN_BOUNDS).save(
                    Path(output).with_name("scan-unselected.png")
                )
            if root_context or scan_states:
                window.tree.setCurrentItem(window.tree.topLevelItem(0))
                app.processEvents()
            capture = window.grab()
            assert capture.devicePixelRatio() == float(scale)
            picture = qimage_to_pil(capture.toImage())
            if look in ("1995", "1998"):
                bounds = tuple(round(value * float(scale)) for value in actions_bounds(window))
                picture = picture.crop(bounds)
            picture.save(output)
            if refresh_states:
                capture_refresh_states(window, output)
            if console_tree_states:
                capture_console_tree_states(window, output, 25 if look == "2000" else 23, console_tree_origin)
            if aero_branches:
                capture_aero_branches(window, output)
            if scan_states:
                capture_scan_states(window, output)
        finally:
            window.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("look")
    parser.add_argument("scale")
    parser.add_argument("output")
    parser.add_argument("width", nargs="?")
    parser.add_argument("height", nargs="?")
    parser.add_argument("--refresh-states", action="store_true")
    parser.add_argument("--console-tree-states", action="store_true")
    parser.add_argument("--console-tree-origin", nargs=2, type=int)
    parser.add_argument("--aero-branches", action="store_true")
    parser.add_argument("--root-context", action="store_true")
    parser.add_argument("--scan-states", action="store_true")
    render(**vars(parser.parse_args()))
