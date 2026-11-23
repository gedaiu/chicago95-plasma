"""Capture Device Manager chrome with a fixed device inventory and guest DPI."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import load_script  # noqa: E402
from PySide6.QtCore import QRect  # noqa: E402
from reference import installed_look, qimage_to_pil  # noqa: E402
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


def render(look, scale, output):
    import chicago95ui

    os.environ["QT_SCALE_FACTOR"] = scale
    app = chicago95ui.make_app("Device Manager")
    settings = "[StartMenu]\nstyle=aero\n[Look]\nwidgetStyle=aero\n"
    context = installed_look(app, settings) if look == "aero" else themed(app, look)
    with context:
        if look == "aero":
            chicago95ui.apply_style(app)
        module = load_script("chicago95-devmgr")
        snapshot = module.snapshot_from(INVENTORY)
        window = module.DeviceManagerWindow(load=lambda: snapshot)
        try:
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
        finally:
            window.close()


if __name__ == "__main__":
    render(*sys.argv[1:])
