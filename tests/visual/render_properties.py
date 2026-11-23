"""Render the production Control Panel and Display Properties in an isolated Qt process."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conftest import REPO, load_script  # noqa: E402
from PIL import Image  # noqa: E402
from PySide6.QtCore import QPoint, QRect, QSize  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QFrame, QPushButton, QTabWidget  # noqa: E402
from reference import installed_look, qimage_to_pil  # noqa: E402
from showcase import themed  # noqa: E402


def aero_style(app):
    config = Path(os.environ["XDG_CONFIG_HOME"]) / "Kvantum"
    theme = config / "Windows7Aero"
    theme.mkdir(parents=True)
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "chicago95" / "kvantum-f51ca15"
    for source, target in (
        ("Windows7Aero-paths.svg", "Windows7Aero.svg"),
        ("Windows7Aero.kvconfig", "Windows7Aero.kvconfig"),
    ):
        if not (cache / source).is_file():
            raise FileNotFoundError(f"Control Panel parity needs the Aero artwork installed by Setup: {cache / source}")
        (theme / target).symlink_to(cache / source)
    (config / "kvantum.kvconfig").write_text("[General]\ntheme=Windows7Aero\n")
    colours = (REPO / "aero/Chicago95Aero.colors").read_text()
    return installed_look(app, "[StartMenu]\nstyle=aero\n[Look]\nwidgetStyle=aero\n", colours)


def capture_hover(window, output):
    window.show()
    card = window.category_view.findChild(QFrame, "categoryCard")
    heading = card.findChild(QPushButton)
    # The Aero opening sample aligns with rows 28–35 of the Basic card's steady fill.
    region = QRect(card.mapTo(window, QPoint(card.width() - 36, 28)), QSize(8, 8))
    strip = Image.new("RGB", (40, 8))

    QTest.mouseMove(window.toolbar, window.toolbar.rect().center())
    idle = qimage_to_pil(window.grab(region).toImage())
    strip.paste(idle, (0, 0))
    QTest.mouseMove(heading, QPoint(12, 6))
    for index in range(1, 5):
        strip.paste(qimage_to_pil(window.grab(region).toImage()), (index * 8, 0))
        QTest.qWait(17)
    strip.save(Path(output).with_name("hover-opening.png"))
    assert window.grab(QRect(card.mapTo(window, QPoint()), card.size())).save(output)
    QTest.mouseMove(window.toolbar, window.toolbar.rect().center())
    assert qimage_to_pil(window.grab(region).toImage()).tobytes() == idle.tobytes()


def capture_hover_exit(window, output, scale):
    window.show()
    card = window.category_view.findChild(QFrame, "categoryCard")
    heading = card.findChild(QPushButton)
    # Sample 36 physical pixels before the right edge and 30 below the top.
    region = QRect(
        card.mapTo(window, QPoint(card.width() - round(36 / scale), round(30 / scale))),
        QSize(round(12 / scale), round(12 / scale)),
    )
    strip = Image.new("RGB", (60, 36))
    idle_position = window.toolbar.rect().center()
    QTest.mouseMove(window.toolbar, idle_position)
    for trial in range(3):
        QTest.mouseMove(heading, QPoint(12, 6))
        QTest.qWait(50)
        strip.paste(qimage_to_pil(window.grab(region).toImage()), (0, trial * 12))
        QTest.mouseMove(window.toolbar, idle_position)
        for frame in range(1, 5):
            sample = qimage_to_pil(window.grab(region).toImage())
            assert sample.size == (12, 12)
            strip.paste(sample, (frame * 12, trial * 12))
            QTest.qWait(17)
    strip.save(output)


def render(manifest, component, output, width, height):
    import chicago95ui

    metadata = json.loads(Path(manifest).read_text())
    look = metadata["look"]
    hover = component == "control-panel-hover"
    hover_exit = component == "control-panel-hover-exit"
    scale = metadata["control_panel_hover_scale" if hover else "properties_scale"]
    os.environ["QT_SCALE_FACTOR"] = str(scale)
    app = chicago95ui.make_app("Control Panel")
    context = aero_style(app) if look == "aero" else themed(app, look)
    with context:
        if look == "aero":
            chicago95ui.apply_style(app)
            QIcon.setThemeName("Windows-7-SVG")
        panel = load_script("chicago95-control-panel")
        resolution = metadata["display_resolution"]
        sizes = list(dict.fromkeys(("640x480", "800x600", "1024x768", resolution)))
        monitor = (
            "Generic Non-PnP Monitor"
            if look == "aero"
            else "Default Monitor on Cirrus Logic 5446 Compatible Graphics Adapter"
        )
        screen = panel.Screen(monitor, resolution, sizes, dict(zip(sizes, range(len(sizes)), strict=True)))
        actions = panel.Actions(current_screen=lambda: screen, list_screensavers=lambda: [], wallpapers=lambda: [])
        settings = Path(output).with_name("look.conf")
        panel.write_settings(settings, {**panel.LOOK_PRESETS[look], "LOOK": look})
        window = panel.ControlPanel(settings_path=settings, actions=actions)
        try:
            if hover:
                capture_hover(window, output)
                return
            if hover_exit:
                window.resize(round(int(width) / scale), round(int(height) / scale))
                capture_hover_exit(window, output, scale)
                return
            if component == "control-panel":
                window.resize(round(int(width) / scale), round(int(height) / scale))
                window.show()
                target = window
            else:
                window.open_applet("Display")
                target = window.applet_windows["Display"]
                tabs = target.page.tabs
                tabs.setCurrentIndex(target.page.tab_names().index(metadata["display_page"]))
            app.processEvents()
            shot = target.grab()
            assert shot.devicePixelRatio() == scale
            assert shot.save(output)
            if component == "display-properties":
                selected = tabs.currentIndex()
                area = tabs.widget(selected)
                assert area.horizontalScrollBar().maximum() == area.verticalScrollBar().maximum() == 0
                if isinstance(tabs, QTabWidget):
                    bar = tabs.tabBar()
                    assert bar.rect().contains(bar.tabRect(selected))
                else:
                    assert tabs.bar.rect().contains(tabs.bar.tab_rects()[selected])
        finally:
            for sheet in window.applet_windows.values():
                sheet.close()
            window.close()


if __name__ == "__main__":
    render(*sys.argv[1:])
