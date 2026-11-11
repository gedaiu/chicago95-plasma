import pytest
from conftest import REPO
from PySide6.QtWidgets import QApplication


@pytest.fixture
def menu_in_style(startmenu, tmp_path, monkeypatch, qt_app):
    settings = tmp_path / "chicago95rc"
    monkeypatch.setattr(startmenu, "SETTINGS_FILE", settings)
    monkeypatch.setattr(startmenu, "QApplication", lambda _argv: QApplication.instance())
    monkeypatch.setattr(startmenu, "apply_retro_look", lambda _app: None)
    monkeypatch.setattr(startmenu, "collect_applications", lambda: [])
    monkeypatch.setattr(startmenu, "recent_documents", lambda: [])
    monkeypatch.setattr(startmenu, "CACHE_FILE", tmp_path / "cache.json")

    def choose(style):
        settings.write_text(f"[StartMenu]\nstyle={style}\n")

    return choose


def test_drawn_root_menu_is_380_by_477_when_style_is_luna(startmenu, menu_in_style):
    menu_in_style("luna")

    _app, menu = startmenu.drawn_root_menu()

    assert (menu.width(), menu.height()) == (380, 477)


def test_root_menu_height_is_477_when_style_is_luna(startmenu, menu_in_style):
    menu_in_style("luna")

    assert startmenu.root_menu_height() == 477


def test_drawn_root_menu_is_the_banner_menu_when_style_is_1995(startmenu, menu_in_style):
    menu_in_style("1995")

    _app, menu = startmenu.drawn_root_menu()

    assert type(menu).__name__ == "RetroMenu"


def test_luna_launch_runs_gio_launch_of_the_desktop_file_when_item_is_an_app(startmenu, monkeypatch):
    launched = []
    monkeypatch.setattr(startmenu, "launch", launched.append)

    startmenu.launch_luna_item({"path": "/usr/share/applications/a.desktop"})
    startmenu.launch_luna_item(["khelpcenter"])

    assert launched == [["gio", "launch", "/usr/share/applications/a.desktop"], ["khelpcenter"]]


def test_luna_commands_cover_every_command_the_luna_menu_names(startmenu):
    import chicago95lunamenu

    assert sorted(startmenu.luna_commands()) == sorted(chicago95lunamenu.COMMAND_NAMES)
