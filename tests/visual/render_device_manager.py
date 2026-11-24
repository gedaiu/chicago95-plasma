"""Capture Device Manager chrome with a fixed device inventory and guest DPI."""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import load_script  # noqa: E402
from PIL import Image  # noqa: E402
from PySide6.QtCore import QPoint, QRect, Qt  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QToolBar  # noqa: E402
from reference import qimage_to_pil  # noqa: E402
from render_properties import aero_style  # noqa: E402
from showcase import themed  # noqa: E402
from test_devmgr import INVENTORY  # noqa: E402


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
    strip = Image.new("RGB", (idle.width * 5, idle.height))
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
    strip.save(Path(output).with_name("refresh-states.png"))


def capture_console_tree_states(window, output):
    toolbar = window.findChild(QToolBar)
    button = toolbar.widgetForAction(window.scope_action)
    inside = button.mapTo(window, button.rect().center())
    outside = window.tree.mapTo(window, window.tree.rect().center())
    scale = window.devicePixelRatioF()
    left = round(button.mapTo(window, QPoint()).x() * scale) - 4
    top = round(toolbar.y() * scale)
    strip = Image.new("RGB", (27 * 7, 23))

    def sample(index):
        picture = qimage_to_pil(window.grab().toImage())
        strip.paste(picture.crop((left, top, left + 27, top + 23)), (27 * index, 0))

    QTest.mouseMove(window.windowHandle(), outside)
    sample(0)
    QTest.mouseMove(window.windowHandle(), inside)
    sample(1)
    QTest.mousePress(window.windowHandle(), Qt.LeftButton, pos=inside)
    assert button.isDown()
    sample(2)
    QTest.mouseMove(window.windowHandle(), outside)
    assert not button.isDown()
    sample(3)
    QTest.mouseRelease(window.windowHandle(), Qt.LeftButton, pos=outside)
    assert not window.scope_action.isChecked()
    sample(4)
    QTest.mouseClick(window.windowHandle(), Qt.LeftButton, pos=inside)
    QTest.mouseMove(window.windowHandle(), outside)
    assert window.scope_action.isChecked() and window.scope_tree.isVisible()
    sample(5)
    QTest.mouseClick(window.windowHandle(), Qt.LeftButton, pos=inside)
    QTest.mouseMove(window.windowHandle(), outside)
    assert not window.scope_action.isChecked() and window.scope_tree.isHidden()
    sample(6)
    strip.save(output)


def render(look, scale, output, width=None, height=None, *, refresh_states=False, console_tree_states=False):
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
                capture_console_tree_states(window, output)
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
    render(**vars(parser.parse_args()))
