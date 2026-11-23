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

    def heading_origin(image):
        red, green, blue = np.moveaxis(np.asarray(image, dtype=int), 2, 0)
        y, x = np.where((green > red + 40) & (green > blue + 40))
        assert x.size > 50
        return (x.min(), y.min())

    if scale == 1:
        glass_home = screenshot("win7-sp1-aero-category").crop((130, 104, 930, 644))
        navigation = (0, 0, 220, 34)
        ours = np.asarray(home.crop(navigation), dtype=int)
        native = np.asarray(glass_home.crop(navigation), dtype=int)
        assert np.abs(ours - native).mean() < 23
        arrow_faces = np.s_[3:29, 2:56]
        assert np.abs(ours[arrow_faces] - native[arrow_faces]).mean() < 20
        for band in (ours, native):
            assert band[9, 65:74].mean(axis=1).argmin() + 65 == 71
            assert band[:9, 215].mean(axis=1).argmin() == 5

        for left in (129, 445):
            region = (left, 97, left + 180, 127)
            assert heading_origin(home.crop(region)) == pytest.approx(heading_origin(glass_home.crop(region)), abs=5)
    else:
        native_home = Image.open(REPO / "tests/references/themes/win7/control-panel.png").convert("RGB")
        # Use native pixels for the compact toolbar used at 144 DPI.
        navigation = (0, 0, 830, 39)
        ours = np.asarray(home.crop(navigation), dtype=int)
        native = np.asarray(native_home.crop(navigation), dtype=int)
        assert np.abs(ours - native).mean() < 39
        for left in (195, 670):
            region = (left, 145, left + 125, 177)
            assert heading_origin(home.crop(region)) == pytest.approx(heading_origin(native_home.crop(region)), abs=5)

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
    native_sheet = screenshot("win7-sp1-aero-taskbar-properties")
    assert action_centres(sheet.crop((0, 392, 398, 424))) == pytest.approx(
        action_centres(native_sheet.crop((0, 392, 398, 424))), abs=3
    )


def test_aero_search_navigation_and_taskbar_sheet(qt_app, tmp_path, monkeypatch):
    panel = load_script("chicago95-control-panel")
    monkeypatch.setattr(panel.chicago95ui, "widget_style", lambda: "aero")
    window = panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.show()
    try:
        from PySide6.QtWidgets import QToolButton

        arrow = next(
            b
            for b in window.address_bar.findChildren(QToolButton)
            if b.accessibleName() == "Locations in Control Panel"
        )
        next(a for a in arrow.menu().actions() if a.text() == "Hardware and Sound").trigger()
        assert window.history.current == panel.HOME_PAGE + ("Hardware and Sound",)
        window.back_action.trigger()
        window.search_applets("Taskbar")
        assert not window.icon_view.item(next(i for i, a in enumerate(panel.APPLETS) if a.name == "Taskbar")).isHidden()
        assert window.icon_view.item(0).isHidden()
        window.search.setText("Taskbar")
        refresh = window.address_bar.findChild(QToolButton, "aeroAddressRefresh")
        assert not refresh.icon().isNull()
        refresh.click()
        assert window.history.current == panel.HOME_PAGE and window.icon_view.item(0).isHidden()
        window.search.clear()
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
        window.set_view("Large Icons")
        view = window.icon_view
        rect = view.visualItemRect(view.item(0))
        QTest.mouseMove(view.viewport(), view.visualItemRect(view.item(1)).center())
        idle = view.viewport().grab(rect).toImage()
        QTest.mouseMove(view.viewport(), rect.center())
        assert view.viewport().grab(rect).toImage() != idle
    finally:
        window.close()


def test_aero_categories_open_applets_and_restore_home(qt_app, monkeypatch, tmp_path):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPushButton

    panel = load_script("chicago95-control-panel")
    monkeypatch.setattr(panel.chicago95ui, "widget_style", lambda: "aero")
    launched = []
    actions = panel.Actions(start_process=lambda program, arguments: launched.append(program))
    window = panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
    window.show()
    try:
        buttons = {button.text(): button for button in window.category_view.findChildren(QPushButton)}
        assert window.pages.currentWidget() is window.category_view
        assert {name for _, tasks in panel.AERO_CATEGORIES.values() for _, name, _ in tasks} == set(
            panel.APPLET_BY_NAME
        )
        category = "Appearance and Personalization"
        link = buttons["Change the theme"]
        QTest.mouseMove(window.toolbar, window.toolbar.rect().center())
        qt_app.processEvents()
        idle = link.grab().toImage()
        QTest.mouseMove(link, link.rect().center())
        qt_app.processEvents()
        assert link.grab().toImage() != idle
        buttons[category].setFocus()
        QTest.keyClick(buttons[category], Qt.Key_Return)
        assert window.address_bar.crumbs() == ["Control Panel", category]
        detail = window.pages.currentWidget()
        links = {button.text(): button for button in detail.findChildren(QPushButton)}
        assert {"Personalization", "Display", "Taskbar and Start Menu", "Fonts"} <= links.keys()
        links["Customize the Start menu"].click()
        taskbar = window.applet_windows["Taskbar"]
        assert taskbar.page.tabs.tabText(taskbar.page.tabs.currentIndex()) == "Start Menu"
        taskbar.reject()
        links["Hardware and Sound"].click()
        assert window.address_bar.crumbs()[-1] == "Hardware and Sound"
        window.back_action.trigger()
        assert window.pages.currentWidget() is detail
        window.back_action.trigger()
        assert window.pages.currentWidget() is window.category_view
        window.forward_action.trigger()
        window.up_action.trigger()
        QTest.mouseClick(buttons["Adjust screen resolution"], Qt.LeftButton)
        display = window.applet_windows["Display"]
        assert display.isVisible() and display.page.tabs.currentIndex() == display.page.tab_names().index("Settings")
        display.reject()
        buttons["Change the theme"].click()
        assert window.history.current == panel.HOME_PAGE + ("Themes",)
        window.back_action.trigger()
        window.search.setFocus()
        QTest.keyClicks(window.search, "Taskbar")
        assert window.pages.currentWidget() is window.icon_view
        window.search.selectAll()
        QTest.keyClick(window.search, Qt.Key_Backspace)
        assert window.pages.currentWidget() is window.category_view
        for action in window.view_menu.actions():
            action.trigger()
            assert window.pages.currentWidget() is (
                window.category_view if action.text() == "Category" else window.icon_view
            )
        window.set_view("Category")
        for _, tasks in panel.AERO_CATEGORIES.values():
            for label, name, tab in tasks:
                buttons[label].click()
                applet = panel.APPLET_BY_NAME[name]
                if applet.external_tool:
                    assert launched[-1] == panel.tool_path(applet.external_tool)
                    continue
                sheet = window.applet_sheet(name)
                assert sheet.isVisible()
                if tab:
                    assert sheet.tab_names()[sheet.tabs.currentIndex()] == tab
                if name in window.applet_windows:
                    window.applet_windows[name].reject()
                else:
                    window.navigate(panel.HOME_PAGE)
    finally:
        window.close()


def test_category_hover_fill_matches_clean_sp1(qt_app, monkeypatch, tmp_path):
    from PySide6.QtCore import QEvent, QPoint
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QFrame, QPushButton

    panel = load_script("chicago95-control-panel")
    monkeypatch.setattr(panel.chicago95ui, "widget_style", lambda: "aero")
    window = panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.show()
    try:
        card = window.category_view.findChild(QFrame, "categoryCard")
        heading = card.findChild(QPushButton)
        native = screenshot("win7-sp1-category-hover")
        motion = screenshot("win7-sp1-category-hover-opening")
        patch = card.mapTo(window, QPoint(card.width() - 8, card.height() // 2))
        QTest.mouseMove(window.toolbar, window.toolbar.rect().center())
        assert window.grab().toImage().pixelColor(patch).getRgb()[:3] == motion.getpixel((4, 4))
        QTest.mouseMove(heading, QPoint(12, 6))
        qt_app.processEvents()
        for frame in range(1, 5):
            actual = window.grab().toImage().pixelColor(patch).getRgb()[:3]
            assert actual == pytest.approx(motion.getpixel((frame * 8 + 4, 4)), abs=3)
            QTest.qWait(17)
        image = card.grab().toImage()
        for fraction in (0, 0.2, 0.5, 0.8, 1):
            actual = image.pixelColor(image.width() - 8, round(fraction * (image.height() - 1))).getRgb()[:3]
            expected = native.getpixel((native.width - 8, round(fraction * (native.height - 1))))
            assert actual == pytest.approx(expected, abs=3)
        qt_app.sendEvent(card, QEvent(QEvent.Leave))
        qt_app.processEvents()
        idle = window.grab().toImage()
        point = card.mapTo(window, QPoint(card.width() - 8, card.height() // 2))
        assert idle.pixelColor(point).name() == "#ffffff"
    finally:
        window.close()


@pytest.mark.parametrize("scale", [1, 1.5])
def test_display_pages_fit_without_changing_pixels_when_scrollbars_are_hidden(tmp_path, scale):
    config = control_panel_config(tmp_path)
    subprocess.run(
        [sys.executable, str(REPO / "tests/aero/render_display_pages.py"), str(tmp_path)],
        env={
            **os.environ,
            "XDG_CONFIG_HOME": str(config),
            "QT_SCALE_FACTOR": str(scale),
            "QT_QPA_PLATFORM": "offscreen",
        },
        check=True,
        timeout=45,
    )


@pytest.mark.parametrize("scale", [1, 1.5])
def test_category_detail_sidebar_and_heading_against_sp1(tmp_path, scale, exact_original):
    config = control_panel_config(tmp_path)
    program = """
import runpy, sys
from PySide6.QtWidgets import QScrollArea
panel = runpy.run_path(sys.argv[1])
app = panel['chicago95ui'].make_app('Control Panel')
window = panel['ControlPanel']()
window.show()
window.navigate(panel['HOME_PAGE'] + ('Appearance and Personalization',))
app.processEvents()
page = window.pages.currentWidget()
area = page.findChild(QScrollArea)
assert area.horizontalScrollBar().maximum() == area.verticalScrollBar().maximum() == 0
assert page.grab().save(sys.argv[2])
"""
    current = tmp_path / "category-detail.png"
    subprocess.run(
        [sys.executable, "-c", program, str(REPO / "bin/chicago95-control-panel"), str(current)],
        env={**os.environ, "XDG_CONFIG_HOME": str(config), "QT_SCALE_FACTOR": str(scale)},
        check=True,
        timeout=30,
    )
    original = screenshot("win7-sp1-aero-category-detail")
    image = Image.open(current).convert("RGB")
    image = image.resize(tuple(round(length / scale) for length in image.size), Image.Resampling.LANCZOS)
    for picture in (image, original):
        row = np.asarray(picture)[350, :250]
        assert np.flatnonzero(row.min(axis=1) > 249)[0] == pytest.approx(199, abs=1)

    def heading_origin(picture):
        r, g, b = np.moveaxis(np.asarray(picture.crop((256, 10, 425, 44))), 2, 0).astype(int)
        y, x = np.where((g - r > 45) & (g - b > 45))
        return x.min(), y.min()

    assert heading_origin(image) == pytest.approx(heading_origin(original), abs=5)
    if scale == 1:
        sidebar = (10, 310, 190, 454)
        exact_original(original.crop(sidebar), image.crop(sidebar))
