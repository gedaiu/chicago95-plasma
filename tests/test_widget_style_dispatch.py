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
