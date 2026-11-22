import chicago95ui
import pytest
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


@pytest.fixture
def look_in_rc(tmp_path, monkeypatch, qt_app):
    config = tmp_path / "chicago95rc"
    monkeypatch.setattr(chicago95ui, "CHICAGO95RC", str(config))

    def write(text):
        config.write_text(text)

    yield write
    chicago95ui.apply_style(qt_app)


def test_look_settings_taskbar_style_is_classic_when_missing(look_in_rc):
    look_in_rc("[Look]\nwidgetStyle=luna\n")

    assert chicago95ui.look_settings()["taskbarStyle"] == "classic"


def test_apply_style_installs_the_luna_controls_when_widget_style_is_luna(look_in_rc, qt_app):
    look_in_rc("[Look]\nwidgetStyle=luna\n")

    chicago95ui.apply_style(qt_app)

    assert (type(QApplication.style()).__name__, QApplication.palette().window().color().name()) == (
        "LunaStyle",
        "#ece9d8",
    )


def test_apply_style_installs_the_classic_controls_when_widget_style_is_classic(look_in_rc, qt_app):
    look_in_rc("[Look]\nwidgetStyle=classic\n")

    chicago95ui.apply_style(qt_app)

    assert type(QApplication.style()).__name__ == "ClassicStyle"


def test_ui_font_is_tahoma_11px_antialiased_when_widget_style_is_luna(look_in_rc):
    look_in_rc("[Look]\nwidgetStyle=luna\n")

    font = chicago95ui.ui_font()

    assert (font.family(), font.pixelSize(), font.styleStrategy()) == ("Tahoma", 11, QFont.PreferAntialias)


def test_ui_font_is_not_tahoma_when_widget_style_is_classic(look_in_rc):
    look_in_rc("[Look]\nwidgetStyle=classic\n")

    assert chicago95ui.ui_font().family() != "Tahoma"


@pytest.mark.parametrize(
    "override,expected", [("classic", "classic"), ("luna", "luna"), ("aero", "aero"), ("auto", "classic")]
)
def test_control_panel_style_is_scoped_to_the_panel(look_in_rc, qt_app, override, expected):
    look_in_rc(f"[Look]\nwidgetStyle=classic\ncontrolPanelStyle={override}\n")
    original_name = qt_app.applicationName()
    try:
        qt_app.setApplicationName("Control Panel")
        assert chicago95ui.widget_style() == expected
        qt_app.setApplicationName("Device Manager")
        assert chicago95ui.widget_style() == "classic"
    finally:
        qt_app.setApplicationName(original_name)


def test_installer_style_override_changes_the_rendered_themes_page(tmp_path):
    import os
    import subprocess
    import sys

    from conftest import REPO
    from PIL import Image, ImageChops

    env = {**os.environ, "XDG_CONFIG_HOME": str(tmp_path), "QT_QPA_PLATFORM": "offscreen", "QT_SCALE_FACTOR": "1"}
    renders = {}
    for style in ("auto", "classic", "luna", "aero"):
        (tmp_path / "chicago95rc").write_text(f"[Look]\nwidgetStyle=classic\ncontrolPanelStyle={style}\n")
        output = tmp_path / f"{style}.png"
        subprocess.run(
            [
                sys.executable,
                str(REPO / "bin/chicago95-control-panel"),
                "--page",
                "themes",
                "--screenshot",
                str(output),
            ],
            env=env,
            check=True,
            timeout=30,
        )
        with Image.open(output) as screenshot:
            renders[style] = screenshot.convert("RGB")
    assert renders["auto"].size == renders["classic"].size
    assert ImageChops.difference(renders["auto"], renders["classic"]).getbbox() is None
    assert ImageChops.difference(renders["luna"], renders["classic"]).getbbox()
    assert renders["aero"].width > renders["classic"].width
