import pytest
from conftest import load_script
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication

from .luna_tools_support import grab_picture, hex_rgb, save_preview


@pytest.fixture
def startmenu_look(monkeypatch, tmp_path, qt_app):
    startmenu = load_script("chicago95-startmenu")
    settings = tmp_path / "chicago95rc"
    monkeypatch.setattr(startmenu, "SETTINGS_FILE", settings)
    yield startmenu, settings
    startmenu.apply_retro_look(qt_app)
    import chicago95ui

    chicago95ui.apply_style(qt_app)


def cascade(startmenu):
    menu = startmenu.RetroMenu()
    menu.addAction(QAction("Accessories", menu))
    menu.addAction(QAction("Games", menu))
    menu.addSeparator()
    menu.addAction(QAction("Startup", menu))
    menu.adjustSize()
    return menu


def test_luna_start_menu_style_puts_luna_style_on_the_cascades(startmenu_look, qt_app):
    startmenu, settings = startmenu_look
    settings.write_text("[StartMenu]\nstyle=luna\n")
    startmenu.apply_retro_look(qt_app)
    assert type(QApplication.style()).__name__ == "LunaStyle"


def test_luna_start_menu_style_uses_the_luna_font_for_the_cascades(startmenu_look, qt_app):
    startmenu, settings = startmenu_look
    settings.write_text("[StartMenu]\nstyle=luna\n")
    startmenu.apply_retro_look(qt_app)
    assert QApplication.font().family() == "Tahoma"


def test_classic_start_menu_style_keeps_the_retro_menu_style(startmenu_look, qt_app):
    startmenu, settings = startmenu_look
    settings.write_text("[StartMenu]\nstyle=1995\n")
    startmenu.apply_retro_look(qt_app)
    assert type(QApplication.style()).__name__ == "RetroMenuStyle"


def test_luna_cascade_is_white_with_no_classic_grey_face(startmenu_look, qt_app):
    startmenu, settings = startmenu_look
    settings.write_text("[StartMenu]\nstyle=luna\n")
    startmenu.apply_retro_look(qt_app)
    menu = cascade(startmenu)
    menu.show()
    picture = grab_picture(menu)
    save_preview("startmenu-cascade", picture)
    assert picture.getpixel((picture.width // 2, 6)) == hex_rgb("#FFFFFF")
    menu.close()
