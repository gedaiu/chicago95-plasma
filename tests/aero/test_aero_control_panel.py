"""The Control Panel shell and independent Taskbar property sheet at two desktop scales."""

import os
import shutil
import subprocess
import sys

import numpy as np
import pytest
from conftest import REPO, load_script
from PIL import Image
from reference import screenshot


def control_panel_config(tmp_path, aero_icons="Windows-7-SVG"):
    config = tmp_path / ".config"
    config.mkdir()
    (config / "chicago95rc").write_text("[Look]\nwidgetStyle=aero\n")
    from test_aero_imported_art import CACHE

    kvantum = config / "Kvantum"
    theme = kvantum / "Windows7Aero"
    source = CACHE / "kvantum-f51ca15"
    if not (source / "Windows7Aero-paths.svg").is_file():
        pytest.skip("needs the converted Windows7Aero Kvantum theme from Setup")
    theme.mkdir(parents=True)
    (theme / "Windows7Aero.svg").symlink_to(source / "Windows7Aero-paths.svg")
    (theme / "Windows7Aero.kvconfig").symlink_to(source / "Windows7Aero.kvconfig")
    (kvantum / "kvantum.kvconfig").write_text("[General]\ntheme=Windows7Aero\n")
    shutil.copyfile(REPO / "aero/Chicago95Aero.colors", config / "kdeglobals")
    with (config / "kdeglobals").open("a") as settings:
        settings.write(f"\n[Icons]\nTheme={aero_icons}\n")
    return config


@pytest.mark.parametrize("scale", [1, 1.5])
def test_control_panel_and_taskbar_against_windows_7(tmp_path, scale):
    config = control_panel_config(tmp_path)
    env = {**os.environ, "XDG_CONFIG_HOME": str(config), "QT_SCALE_FACTOR": str(scale)}
    tool = str(REPO / "bin/chicago95-control-panel")

    def render(name, args):
        out = tmp_path / f"{name}.png"
        subprocess.run([sys.executable, tool, *args, "--screenshot", str(out)], env=env, check=True, timeout=30)
        return Image.open(out).convert("RGB")

    home = render("home", [])
    navigation = home.resize((780, 540), Image.Resampling.LANCZOS).crop((0, 0, 220, 34))
    reference = screenshot("win7controlpanel").crop((9, 41, 229, 75))
    assert np.abs(np.asarray(navigation, dtype=float) - np.asarray(reference)).mean() < 39

    sheet = render("taskbar", ["--page", "taskbar"])
    assert sheet.size == (round(398 * scale), round(424 * scale))
    sheet = sheet.resize((398, 424), Image.Resampling.LANCZOS)
    original = screenshot("win7-taskbar-sheet-chrome")
    # Compare both bands and locate the long top outlines of all three action buttons.
    for top, source_y in ((0, 0), (392, 32)):
        actual = np.asarray(sheet.crop((0, top, 398, top + 32)), dtype=float)
        expected = np.asarray(original.crop((0, source_y, 398, source_y + 32)))
        assert np.abs(actual - expected).mean() < 32

    def action_centres(band):
        for row in np.asarray(band.convert("L"))[:9]:
            edges = np.diff(np.pad((row < 205).astype(int), 1))
            centres = [
                (a + b) / 2
                for a, b in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1), strict=True)
                if 60 <= b - a <= 80
            ]
            if len(centres) == 3:
                return centres
        pytest.fail("missing OK, Cancel or Apply outline")

    assert action_centres(sheet.crop((0, 392, 398, 424))) == pytest.approx(
        action_centres(original.crop((0, 32, 398, 64))), abs=3
    )


def test_aero_search_navigation_and_taskbar_sheet(qt_app, tmp_path, monkeypatch):
    panel = load_script("chicago95-control-panel")
    monkeypatch.setattr(panel.chicago95ui, "widget_style", lambda: "aero")
    window = panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.show()
    try:
        window.search_applets("Taskbar")
        assert not window.icon_view.item(next(i for i, a in enumerate(panel.APPLETS) if a.name == "Taskbar")).isHidden()
        assert window.icon_view.item(0).isHidden()
        window.search_applets("")
        window.open_applet("Taskbar")
        sheet = window.applet_windows["Taskbar"]
        assert sheet.isVisible() and window.history.current == panel.HOME_PAGE
        assert sheet.page.tab_names() == ["Taskbar", "Start Menu", "Toolbars"]
        assert "TASKBAR_AUTOHIDE" in sheet.page.settings_tabs[0].fields
        assert "TASK_BUTTON_WIDTH" in sheet.page.settings_tabs[2].fields
        sheet.reject()
        window.navigate(panel.HOME_PAGE + ("Taskbar",))
        assert window.applet_windows["Taskbar"] is sheet and sheet.isVisible()
        window.open_applet("Explorer")
        assert window.back_action.isEnabled()
        window.back_action.trigger()
        assert window.history.current == panel.HOME_PAGE
    finally:
        window.close()


@pytest.mark.parametrize("widget_style", ["classic", "aero"])
def test_icon_only_taskbar_hides_sizing_rows(qt_app, monkeypatch, widget_style):
    panel = load_script("chicago95-control-panel")
    monkeypatch.setattr(panel.chicago95ui, "widget_style", lambda: widget_style)
    builder = panel.quick_launch_tab if widget_style == "aero" else panel.taskbar_options_tab
    tab = builder({"TASKBAR_STYLE": "aero", "PANEL": "44", "TASK_BUTTON_WIDTH": "156"}, panel.Actions())
    tab.show()
    try:
        from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel

        style = next(box for box in tab.findChildren(QComboBox) if box.findData("aero") >= 0)
        width = tab.findChild(panel.ButtonWidthField)
        form = next(layout for layout in tab.findChildren(QFormLayout) if layout.labelForField(width))
        labels = [
            label for label in tab.findChildren(QLabel) if label.text() in ("Taskbar height:", "Taskbar button width:")
        ]
        assert len(labels) == 2
        for look in ("aero", "classic", "aero"):
            style.setCurrentIndex(style.findData(look))
            qt_app.processEvents()
            for label in labels:
                row, _ = form.getWidgetPosition(label)
                field = form.itemAt(row, QFormLayout.FieldRole).widget()
                assert field.isVisible() == label.isVisible() == (look != "aero")
            assert tab.values()["TASK_BUTTON_WIDTH"] == "156"
            assert tab.values()["PANEL"] == "44"
    finally:
        tab.close()


def test_aero_navigation_glow_and_applet_hover(qt_app, monkeypatch, tmp_path):
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QEnterEvent
    from PySide6.QtTest import QTest

    panel = load_script("chicago95-control-panel")
    monkeypatch.setattr(panel.chicago95ui, "widget_style", lambda: "aero")
    window = panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.show()
    try:
        window.open_applet("Explorer")
        button = window.toolbar_buttons["Back"]
        assert button.isEnabled()
        qt_app.sendEvent(button, QEnterEvent(QPointF(3, 3), QPointF(3, 3), QPointF(3, 3)))
        button.glow.pause()
        frames = []
        for time in (0, 70, 140):
            button.glow.setCurrentTime(time)
            frames.append(button.grab().toImage())
        assert frames[0] != frames[1] != frames[2]
        qt_app.sendEvent(button, QEvent(QEvent.Leave))
        button.glow.setCurrentTime(0)
        assert button.grab().toImage() == frames[0]
        button.click()
        view = window.icon_view
        rect = view.visualItemRect(view.item(0))
        QTest.mouseMove(view.viewport(), view.visualItemRect(view.item(1)).center())
        idle = view.viewport().grab(rect).toImage()
        QTest.mouseMove(view.viewport(), rect.center())
        assert view.viewport().grab(rect).toImage() != idle
    finally:
        window.close()
