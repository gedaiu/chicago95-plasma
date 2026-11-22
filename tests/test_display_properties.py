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


@pytest.fixture
def settings_window(control_panel, qt_app, tmp_path):
    calls = {"modes": [], "started": [], "keep": False}
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo/install.sh").write_text("")
    (tmp_path / "setup.conf").write_text(f"REPO={tmp_path / 'repo'}\n")
    actions = control_panel.Actions(
        start_process=lambda program, arguments: calls["started"].append((program, arguments)),
        run_setup=lambda parent, command: None,
        list_screensavers=lambda: [("pipes", "3D Pipes")],
        lock_timeout_minutes=lambda: 60,
        current_screen=lambda: control_panel.screen_from_doctor(DOCTOR),
        set_screen_mode=lambda output, mode: calls["modes"].append((output, mode)),
        keep_screen_mode=lambda parent: calls["keep"],
    )
    panel = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
    panel.open_applet("Display")
    sheet = panel.applet_windows["Display"]
    yield sheet, calls, tmp_path
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


@pytest.mark.parametrize("tab_name", ["Background", "Screen Saver", "Appearance", "Effects", "Settings"])
def test_every_display_tab_fits_the_originals_window_without_scrolling(window, qt_app, tab_name):
    window.open_applet("Display")
    page = window.applet_windows["Display"].page
    index = page.tab_names().index(tab_name)
    page.tabs.setCurrentIndex(index)
    qt_app.processEvents()
    scroller = page.tabs.widget(index)

    assert (scroller.verticalScrollBar().maximum(), scroller.horizontalScrollBar().maximum()) == (0, 0)


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


@pytest.mark.parametrize("scale", ["1", "1.5", "2"])
@pytest.mark.parametrize("look", ["1998", "aero", "luna"])
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
panel.chicago95ui.widget_style = lambda: "classic" if look == "1998" else look
app = panel.chicago95ui.make_app("Display Properties")
assert app.devicePixelRatio() == float(sys.argv[2])
settings = {**panel.LOOK_PRESETS[look], "LOOK": look}
names = ("Background", "Screen Saver", "Appearance", "Effects", "Settings")
actions = panel.Actions(list_screensavers=lambda: [], lock_timeout_minutes=lambda: 60)
entries = [(name, panel.build_tab("Display", name, settings, actions)) for name in names]
page = panel.PropertiesPage("Display", entries, lambda _: True)
window = panel.PropertySheetWindow(page, None)
window.show()
for index, (name, tab) in enumerate(entries):
    page.tabs.setCurrentIndex(index)
    for item in range(tab.items.count()) if name == "Appearance" else [None]:
        if item is not None:
            tab.items.setCurrentIndex(item)
        app.processEvents()
        area = page.tabs.widget(index)
        bars = (area.horizontalScrollBar().maximum(), area.verticalScrollBar().maximum())
        assert bars == (0, 0), (name, item, bars, tab.minimumSizeHint())
    if look == "aero":
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
