"""Capture each Aero Display Properties page at the requested toolkit scale."""

import os
import runpy
import sys
from pathlib import Path


def compare_display_pages(output):
    """Run in a separate Qt process so toolkit scale and installed style take effect."""
    from PySide6.QtCore import Qt

    panel = runpy.run_path(str(Path(__file__).resolve().parents[2] / "bin/chicago95-control-panel"))
    app = panel["chicago95ui"].make_app("Control Panel")
    assert panel["chicago95ui"].widget_style() == "aero"
    window = panel["ControlPanel"]()
    window.open_category_task("Display", "Appearance")
    sheet = window.applet_windows["Display"]
    tabs = sheet.page.tabs
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        app.processEvents()
        area = tabs.currentWidget()
        assert not area.horizontalScrollBar().maximum() and not area.verticalScrollBar().maximum()
        assert tabs.tabBar().rect().contains(tabs.tabBar().tabRect(index))
        normal = sheet.grab()
        assert normal.devicePixelRatio() == float(os.environ["QT_SCALE_FACTOR"])
        assert normal.save(str(output / f"display-{index}.png"))
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        app.processEvents()
        assert sheet.grab().toImage() == normal.toImage(), tabs.tabText(index)
    sheet.close()


if __name__ == "__main__":
    compare_display_pages(Path(sys.argv[1]))
