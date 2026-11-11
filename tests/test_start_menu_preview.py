"""The Start Menu tab's preview: the Start button pressed on a strip of taskbar, with the Start menu open above it,
both drawn by the theme's own code with the tab's values before they are applied.

The menu comes from the Start menu itself (bin/chicago95-startmenu --screenshot) run offscreen on a scratch
chicago95rc, so its style and fonts never touch the Control Panel's; the button is the taskbar's StartButton.qml."""

import os
import subprocess
import sys

import pytest
from conftest import REPO, load_script, needs_ui_font
from PySide6.QtCore import QObject
from PySide6.QtGui import QImage

RED, YELLOW = "#ff0000", "#ffff00"


def banner_colours(image):
    """The colours along the bottom of the vertical banner, where its text sits."""
    return {image.pixelColor(x, y).name() for x in range(3, 20) for y in range(image.height() - 80, image.height() - 4)}


@needs_ui_font
def test_the_start_menu_screenshot_draws_the_banner_from_the_given_settings(tmp_path):
    (tmp_path / "chicago95rc").write_text(
        "[StartMenu]\nbannerText=Hello\nbannerBackground=#FF0000\nbannerTextColor=#FFFF00\nstyle=1998\n"
    )
    shot = tmp_path / "menu.png"
    subprocess.run(
        [sys.executable, str(REPO / "bin/chicago95-startmenu"), "--screenshot", str(shot)],
        env={**os.environ, "XDG_CONFIG_HOME": str(tmp_path), "QT_QPA_PLATFORM": "offscreen"},
        timeout=60,
        check=True,
    )
    image = QImage(str(shot))

    assert (image.isNull(), RED in banner_colours(image), YELLOW in banner_colours(image)) == (False, True, True)


@pytest.fixture(scope="module")
def control_panel():
    return load_script("chicago95-control-panel")


@needs_ui_font
def test_the_start_menu_tabs_preview_shows_the_typed_button_text_and_banner(control_panel, qt_app):
    preview = control_panel.StartMenuPreview()
    preview.refresh(
        {"START_TEXT": "Go", "START_LOGO": "penguin", "BANNER_TEXT": "Hello", "BANNER_BG": "#FF0000", "LOOK": "1998"}
    )
    preview.process.waitForFinished(60000)
    qt_app.processEvents()
    button = preview.button.rootObject().findChild(QObject, "startButton")
    menu = preview.menu_label.pixmap().toImage()

    assert (button.property("text"), button.property("held"), RED in banner_colours(menu)) == ("Go", True, True)


def test_the_start_menu_tab_has_the_preview_below_its_fields(control_panel, qt_app):
    tab = control_panel.build_tab("Taskbar", "Start Menu", {}, control_panel.Actions())

    assert [type(preview).__name__ for preview in tab.previews] == ["StartMenuPreview"]
