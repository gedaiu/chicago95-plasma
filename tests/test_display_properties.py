"""Display opens as its own window, as Windows 98's Display Properties did (tests/references/win98propertysheet.png,
the tech2u Display Properties pictures): a fixed property sheet titled "Display Properties" with the title bar's
? and close buttons only, the original's tabs, and OK, Cancel and Apply; the Control Panel stays where it was."""

import pytest
from conftest import load_script
from PySide6.QtCore import Qt


@pytest.fixture(scope="module")
def control_panel():
    return load_script("chicago95-control-panel")


@pytest.fixture
def window(control_panel, qt_app, tmp_path):
    actions = control_panel.Actions(
        start_process=lambda program, arguments: None,
        run_setup=lambda parent, command: None,
        show_message=lambda parent, title, text: None,
        ask_to_apply=lambda parent: "no",
        list_screensavers=lambda: [("pipes", "3D Pipes")],
        lock_timeout_minutes=lambda: 60,
    )
    panel = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
    panel.show()
    yield panel
    for sheet in panel.applet_windows.values():
        sheet.close()
    panel.close()


def test_display_opens_its_own_properties_window_and_the_control_panel_stays_home(window, control_panel, qt_app):
    window.open_applet("Display")
    qt_app.processEvents()
    sheet = window.applet_windows["Display"]

    assert (sheet.windowTitle(), sheet.isVisible(), window.pages.currentWidget() is window.icon_view) == (
        "Display Properties",
        True,
        True,
    )


def test_display_properties_has_the_originals_tabs(window, qt_app):
    window.open_applet("Display")

    assert window.applet_windows["Display"].page.tab_names() == [
        "Background",
        "Screen Saver",
        "Appearance",
        "Effects",
        "Settings",
    ]


def test_luna_display_themes_and_effects_share_the_parent_apply(control_panel, qt_app, tmp_path, monkeypatch):
    from PySide6.QtCore import QTimer

    monkeypatch.setattr(control_panel.chicago95ui, "widget_style", lambda: "luna")
    settings = tmp_path / "setup.conf"
    control_panel.write_settings(settings, {**control_panel.LOOK_PRESETS["luna"], "LOOK": "luna"})
    screen = control_panel.Screen("Monitor", "800x600", ["800x600"], {})
    actions = control_panel.Actions(
        current_screen=lambda: screen,
        list_screensavers=lambda: [],
        wallpapers=lambda: [],
        choose_color=lambda parent, current: "#123456",
    )
    panel = control_panel.ControlPanel(settings_path=settings, actions=actions)
    try:
        panel.open_applet("Display")
        page = panel.applet_windows["Display"].page
        assert page.tab_names() == ["Themes", "Desktop", "Screen Saver", "Appearance", "Settings"]
        themes, desktop, _, appearance, display = page.settings_tabs
        themes.selector.setCurrentIndex(themes.selector.findData("2000"))
        assert appearance.scheme.currentData() == "2000"
        assert themes.theme_preview.look == "2000"
        assert page.changed_values()["LOOK"] == "2000"
        page.discard_changes()
        assert themes.selector.currentData() == "luna"
        desktop.colour_button.click()
        assert appearance.color_edits["BACKGROUND_COLOR"].value() == "#123456"
        assert desktop.monitor.desktop_colour.name() == "#123456"
        assert page.changed_values()["BACKGROUND_COLOR"] == "#123456"
        page.discard_changes()

        def change_icons(accept):
            dialog = qt_app.activeModalWidget()
            effects = dialog.findChild(control_panel.SettingsTab)
            effects.load({"DESKTOP_ICONS": "computer,network,recycle"}, ["DESKTOP_ICONS"])
            dialog.done(int(accept))

        page.tabs.setCurrentIndex(page.tab_names().index("Appearance"))
        QTimer.singleShot(0, lambda: change_icons(False))
        appearance.effects_button.click()
        assert "DESKTOP_ICONS" not in page.changed_values()
        QTimer.singleShot(0, lambda: change_icons(True))
        appearance.effects_button.click()
        assert page.changed_values()["DESKTOP_ICONS"] == "computer,network,recycle"
        page.discard_changes()
        assert "DESKTOP_ICONS" not in page.changed_values()
        appearance.windows_style.setCurrentIndex(appearance.windows_style.findData("classic"))
        assert page.changed_values()["WIDGET_STYLE"] == "classic"
        page.discard_changes()
        assert appearance.windows_style.currentData() == "luna"

        def change_advanced(accept):
            dialog = qt_app.activeModalWidget()
            assert dialog.isAncestorOf(appearance.items)
            appearance.color_edits["BACKGROUND_COLOR"].set_value("#654321")
            dialog.done(int(accept))

        QTimer.singleShot(0, lambda: change_advanced(False))
        appearance.advanced_button.click()
        assert "BACKGROUND_COLOR" not in page.changed_values()
        QTimer.singleShot(0, lambda: change_advanced(True))
        appearance.advanced_button.click()
        assert page.changed_values()["BACKGROUND_COLOR"] == "#654321"
        page.discard_changes()
        page.tabs.setCurrentIndex(page.tab_index("Settings"))
        qt_app.processEvents()
        assert page.window().focusWidget() is display.screen_area.slider
    finally:
        for sheet in panel.applet_windows.values():
            sheet.close()
        panel.close()


def test_luna_screen_saver_tab_opens_monitor_power_settings(control_panel, qt_app, monkeypatch):
    from PySide6.QtWidgets import QPushButton

    monkeypatch.setattr(control_panel.chicago95ui, "widget_style", lambda: "luna")
    started = []
    messages = []
    actions = control_panel.Actions(
        list_screensavers=lambda: [("blank", "Blank Screen")],
        lock_timeout_minutes=lambda: 60,
        start_process=lambda program, arguments: started.append((program, arguments)),
        show_message=lambda parent, title, text: messages.append((title, text)),
    )
    tab = control_panel.screen_saver_tab({"SAVER": "blank"}, actions)
    controls = {button.text(): button for button in tab.findChildren(QPushButton)}
    controls["Preview"].click()
    controls["Po&wer..."].click()
    controls["&Settings"].click()
    assert messages == [("Blank Screen Saver", "This screen saver has no options that you can set.")]
    assert started == [
        (control_panel.tool_path("chicago95-screensaver"), ["--hack", "blank"]),
        ("kcmshell6", ["kcm_powerdevilprofilesconfig"]),
    ]


def test_display_properties_title_bar_has_only_help_and_close_and_the_window_keeps_its_size(window, qt_app):
    window.open_applet("Display")
    sheet = window.applet_windows["Display"]
    flags = sheet.windowFlags()

    assert (
        bool(flags & Qt.WindowContextHelpButtonHint),
        bool(flags & Qt.WindowCloseButtonHint),
        bool(flags & Qt.WindowMinimizeButtonHint),
        bool(flags & Qt.WindowMaximizeButtonHint),
        sheet.minimumSize() == sheet.maximumSize(),
    ) == (True, True, False, False, True)


def test_opening_display_again_brings_back_the_same_window(window, qt_app):
    window.open_applet("Display")
    first = window.applet_windows["Display"]
    window.open_applet("Display")

    assert window.applet_windows["Display"] is first


def test_cancel_closes_display_properties(window, qt_app):
    window.open_applet("Display")
    sheet = window.applet_windows["Display"]
    sheet.page.cancel_button.click()
    qt_app.processEvents()

    assert sheet.isVisible() is False


DOCTOR = {
    "outputs": [
        {"name": "HDMI-1", "enabled": False, "currentModeId": "", "modes": []},
        {
            "name": "DP-3",
            "enabled": True,
            "currentModeId": "1",
            "modes": [
                {"id": "1", "size": {"width": 3840, "height": 2160}, "refreshRate": 60.0},
                {"id": "11", "size": {"width": 1280, "height": 720}, "refreshRate": 50.0},
                {"id": "12", "size": {"width": 1280, "height": 720}, "refreshRate": 60.0},
                {"id": "14", "size": {"width": 1024, "height": 768}, "refreshRate": 60.0},
            ],
        },
    ]
}


def test_the_screen_is_the_enabled_output_with_its_sizes_smallest_first_at_their_fastest_refresh(control_panel):
    screen = control_panel.screen_from_doctor(DOCTOR)

    assert (screen.output, screen.current, screen.sizes, screen.modes) == (
        "DP-3",
        "3840x2160",
        ["1024x768", "1280x720", "3840x2160"],
        {"1024x768": "14", "1280x720": "12", "3840x2160": "1"},
    )


@pytest.fixture(params=["1998", "2001", "luna"])
def settings_window(control_panel, qt_app, tmp_path, request):
    from showcase import themed

    calls = {"modes": [], "started": [], "keep": False}
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo/install.sh").write_text("")
    (tmp_path / "setup.conf").write_text(f"REPO={tmp_path / 'repo'}\nLOOK={request.param}\n")
    actions = control_panel.Actions(
        start_process=lambda program, arguments: calls["started"].append((program, arguments)),
        run_setup=lambda parent, command: None,
        list_screensavers=lambda: [("pipes", "3D Pipes")],
        lock_timeout_minutes=lambda: 60,
        current_screen=lambda: control_panel.screen_from_doctor(DOCTOR),
        set_screen_mode=lambda output, mode: calls["modes"].append((output, mode)),
        keep_screen_mode=lambda parent: calls["keep"],
        display_depth=lambda _output: 16,
    )
    with themed(qt_app, request.param):
        panel = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
        panel.open_applet("Display")
        sheet = panel.applet_windows["Display"]
        try:
            yield sheet, calls, tmp_path
        finally:
            sheet.close()
            panel.close()


def test_the_settings_tab_shows_the_screen_area_as_the_original_words_it(settings_window):
    sheet, _calls, _folder = settings_window
    tab = sheet.page.settings_tabs[4]

    assert (tab.values(), tab.screen_area.label.text(), tab.display_name.text()) == (
        {"SCREEN_AREA": "3840x2160"},
        "3840 by 2160 pixels",
        "DP-3",
    )


def test_settings_displays_the_detected_color_depth(settings_window):
    from PySide6.QtWidgets import QComboBox

    sheet, _calls, _folder = settings_window
    tab = sheet.page.settings_tabs[4]
    assert tab.findChild(QComboBox).currentText() == (
        "True Color (32 bit)" if tab.saved["LOOK"] == "1998" else "Medium (16 bit)"
    )


def test_a_new_screen_area_not_kept_goes_back_to_the_old_one_and_is_never_saved(settings_window):
    sheet, calls, folder = settings_window
    sheet.page.settings_tabs[4].screen_area.slider.setValue(0)
    sheet.page.apply_button.click()

    assert (calls["modes"], "SCREEN_AREA" in (folder / "setup.conf").read_text()) == (
        [("DP-3", "14"), ("DP-3", "1")],
        False,
    )


def test_a_new_screen_area_kept_stays(settings_window):
    sheet, calls, _folder = settings_window
    calls["keep"] = True
    sheet.page.settings_tabs[4].screen_area.slider.setValue(1)
    sheet.page.apply_button.click()

    assert calls["modes"] == [("DP-3", "12")]


def test_advanced_opens_kdes_display_settings(settings_window):
    sheet, calls, _folder = settings_window
    sheet.page.settings_tabs[4].advanced_button.click()

    assert calls["started"] == [("kcmshell6", ["kcm_kscreen"])]


def test_aero_screen_resolution_applies_reverts_and_discards_changes(control_panel, qt_app, tmp_path, monkeypatch):
    from PySide6.QtCore import QSize
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QPushButton, QScrollArea, QToolButton

    monkeypatch.setattr(control_panel.chicago95ui, "widget_style", lambda: "aero")
    current = control_panel.screen_from_doctor(DOCTOR)
    calls = []
    keep = False

    def set_mode(output, mode):
        calls.append((output, mode))

    actions = control_panel.Actions(
        current_screen=lambda: current,
        set_screen_mode=set_mode,
        keep_screen_mode=lambda _parent: keep,
    )
    panel = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
    panel.show()
    panel.activateWindow()
    qt_app.processEvents()
    try:
        panel.open_applet("Display")
        page = panel.screen_resolution
        assert panel.pages.currentWidget() is page
        assert page.isVisible() and not page.findChildren(QScrollArea)
        assert page.display.currentText() == "1. DP-3"
        assert page.resolutions.currentData() == "3840x2160"
        assert not page.apply_button.isEnabled()

        resolutions = page.resolutions
        resolutions.setFocus()
        QTest.keyClick(resolutions, Qt.Key_Down, Qt.AltModifier)
        qt_app.processEvents()
        popup = qt_app.activePopupWidget()
        assert popup is resolutions.popup
        QTest.keyClick(popup.focusWidget(), Qt.Key_Down)
        assert resolutions.currentData() == "1280x720"
        assert page.monitor.size() == QSize(128, 72)
        QTest.keyClick(popup.focusWidget(), Qt.Key_Escape)
        qt_app.processEvents()
        assert qt_app.activePopupWidget() is None
        assert resolutions.currentData() == "1280x720"
        assert page.apply_button.isEnabled()
        assert calls == []

        QTest.keyClick(resolutions, Qt.Key_Down, Qt.AltModifier)
        qt_app.processEvents()
        popup = qt_app.activePopupWidget()
        label = next(button for button in popup.findChildren(QToolButton) if button.text() == "1024 × 768")
        QTest.mouseClick(label, Qt.LeftButton)
        assert popup.isVisible() and resolutions.currentData() == "1024x768"
        QTest.keyClick(popup.focusWidget(), Qt.Key_Return)
        qt_app.processEvents()
        assert qt_app.activePopupWidget() is None and page.apply_button.isEnabled()
        assert calls == []
        page.apply_button.click()
        assert calls == [("DP-3", "14"), ("DP-3", "1")]
        assert page.resolutions.currentData() == "3840x2160"
        assert not page.apply_button.isEnabled()

        page.resolutions.setCurrentIndex(page.resolutions.findData("1024x768"))
        page.cancel_button.click()
        assert panel.pages.currentWidget() is panel.category_view
        panel.forward_action.trigger()
        assert page.resolutions.currentData() == "3840x2160"
        assert calls == [("DP-3", "14"), ("DP-3", "1")]

        keep = True
        page.resolutions.setCurrentIndex(page.resolutions.findData("1280x720"))
        page.apply_button.click()
        assert calls[-1] == ("DP-3", "12")
        assert page.resolutions.currentData() == "1280x720"
        assert not page.apply_button.isEnabled()
        assert not (tmp_path / "setup.conf").exists()

        current = None
        next(button for button in page.findChildren(QPushButton) if button.text() == "Detect").click()
        assert not page.resolutions.isEnabled() and not page.identify.isEnabled()
    finally:
        panel.close()


@pytest.mark.parametrize("tab_name", ["Background", "Screen Saver", "Appearance", "Effects", "Settings"])
def test_every_display_tab_fits_the_originals_window_without_scrolling(window, qt_app, tab_name):
    window.open_applet("Display")
    page = window.applet_windows["Display"].page
    index = page.tab_names().index(tab_name)
    page.tabs.setCurrentIndex(index)
    qt_app.processEvents()
    scroller = page.tabs.widget(index)

    assert (scroller.verticalScrollBar().maximum(), scroller.horizontalScrollBar().maximum()) == (0, 0)


@pytest.mark.parametrize("look", ["1995", "1998", "2000", "2001"])
def test_classic_display_matches_guest_size_without_scrolling(control_panel, qt_app, tmp_path, monkeypatch, look):
    from PySide6.QtCore import QSize

    monkeypatch.setattr(control_panel.chicago95ui, "widget_style", lambda: "classic")
    settings = tmp_path / "setup.conf"
    control_panel.write_settings(settings, {**control_panel.LOOK_PRESETS[look], "LOOK": look})
    actions = control_panel.Actions(
        current_screen=lambda: None, list_screensavers=lambda: [], wallpapers=lambda: []
    )
    panel = control_panel.ControlPanel(settings_path=settings, actions=actions)
    panel.open_applet("Display")
    sheet = panel.applet_windows["Display"]
    try:
        assert sheet.size() == QSize(422, 415)
        page = sheet.page
        appearance = page.tab_names().index("Appearance")
        for index, tab in enumerate(page.settings_tabs):
            page.tabs.setCurrentIndex(index)
            area = page.tabs.widget(index)
            for item in range(tab.items.count()) if index == appearance else [None]:
                if item is not None:
                    tab.items.setCurrentIndex(item)
                qt_app.processEvents()
                assert (area.horizontalScrollBar().maximum(), area.verticalScrollBar().maximum()) == (0, 0)
    finally:
        sheet.close()
        panel.close()


def test_without_a_compositor_the_screen_is_unknown_and_kscreen_doctor_is_never_run(
    control_panel, tmp_path, monkeypatch
):
    called = tmp_path / "called"
    fake = tmp_path / "kscreen-doctor"
    fake.write_text(f"#!/bin/sh\ntouch {called}\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)

    assert (control_panel.live_screen(), called.exists()) == (None, False)


@pytest.mark.parametrize("scale", ["1", "1.25", "1.5", "2"])
@pytest.mark.parametrize("look", ["1998", "2001", "aero", "luna"])
def test_display_tabs_fit_at_desktop_scales(tmp_path, scale, look):
    import os
    import subprocess
    import sys

    from conftest import REPO

    program = r"""
import sys
from pathlib import Path
root = Path.cwd()
sys.path[:0] = [str(root / "tests"), str(root / "lib"), str(root / "luna/lib")]
import conftest
import os
os.environ["QT_SCALE_FACTOR"] = sys.argv[2]
panel = conftest.load_script("chicago95-control-panel")
look = sys.argv[3]
panel.chicago95ui.widget_style = lambda: "classic" if look in ("1998", "2001") else look
app = panel.chicago95ui.make_app("Display Properties")
assert app.devicePixelRatio() == float(sys.argv[2])
settings = {**panel.LOOK_PRESETS[look], "LOOK": look}
names = ("Background", "Screen Saver", "Appearance", "Effects", "Settings")
actions = panel.Actions(list_screensavers=lambda: [], lock_timeout_minutes=lambda: 60)
entries = (
    panel.xp_display_tabs(settings, actions) if look in ("2001", "luna")
    else [(name, panel.build_tab("Display", name, settings, actions)) for name in names]
)
page = panel.PropertiesPage("Display", entries, lambda _: True)
window = panel.PropertySheetWindow(page, None)
window.show()
if look == "luna":
    assert (window.width(), window.height()) == (422, 414), window.size()
for index, (name, tab) in enumerate(entries):
    page.tabs.setCurrentIndex(index)
    for item in range(tab.items.count()) if name == "Appearance" else [None]:
        if item is not None:
            tab.items.setCurrentIndex(item)
        app.processEvents()
        area = page.tabs.widget(index)
        bars = (area.horizontalScrollBar().maximum(), area.verticalScrollBar().maximum())
        assert bars == (0, 0), (name, item, bars, tab.minimumSizeHint())
    if look in ("aero", "luna"):
        bar = page.tabs.tabBar()
        assert bar.rect().contains(bar.tabRect(page.tabs.count() - 1))
        assert bar.rect().contains(bar.tabRect(0))
    window.grab().save(str(Path(sys.argv[1]) / f"{name}.png"))
window.close()
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(tmp_path), scale, look],
        cwd=REPO,
        check=False,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_SCALE_FACTOR": scale},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_windows_98_appearance_preview_matches_guest_window_positions(control_panel, qt_app):
    from reference import qimage_to_pil, screenshot

    switch = control_panel.AppearanceSwitch()
    switch.show_style("classic")
    switch.show_colors("#000080", "#808080", "#008080", "1998")
    actual = qimage_to_pil(switch.grab().toImage()).convert("RGB")
    native = screenshot("win98-se-appearance").convert("RGB")
    assert actual.size == native.size
    # The neutral VGA chrome can differ by palette. Compare the uninterrupted
    # navy title rows and the teal desktop silhouette, including their boundaries.
    for colour in ((0, 0, 128), (0, 128, 128)):
        for y in (8, 12, 32, 37, 54, 57, 115, 123, 163, 187):
            for x in (5, 11, 15, 23, 105, 170, 235, 310, 340, 350):
                assert (actual.getpixel((x, y)) == colour) == (native.getpixel((x, y)) == colour), (x, y, colour)
    import numpy as np

    def colour_mask(image, rgb):
        return (np.asarray(image) == rgb).all(axis=2)

    assert np.array_equal(colour_mask(actual, (0, 128, 128)), colour_mask(native, (0, 128, 128)))
    # Include both scroll arrows inside the sample window. The arrowheads are four rows high.
    for box in ((328, 80, 342, 88), (328, 146, 342, 159)):
        assert np.array_equal(colour_mask(actual.crop(box), (0, 0, 0)), colour_mask(native.crop(box), (0, 0, 0)))
    for band in ((116, 56, 170, 57), (116, 72, 170, 73), (92, 157, 164, 158), (92, 180, 164, 181)):
        assert actual.crop(band).tobytes() == native.crop(band).tobytes(), band
