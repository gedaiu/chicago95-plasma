import json

import pytest
import xdg.Menu
from conftest import load_script
from PySide6.QtCore import QTimer


@pytest.fixture
def startmenu(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    return load_script("chicago95-startmenu")


def test_collect_applications_rescans_when_the_cache_stamp_is_stale(startmenu, tmp_path, monkeypatch):
    applications = tmp_path / "applications"
    applications.mkdir()
    (applications / "tool.desktop").write_text("[Desktop Entry]\nType=Application\nName=Tool\nExec=tool\n")
    cache_file = tmp_path / "cache.json"
    cache_file.write_text(json.dumps({"stamp": {"stale": 0}, "apps": [{"name": "Old"}]}))
    monkeypatch.setattr(startmenu, "APPLICATION_DIRS", [applications])
    monkeypatch.setattr(startmenu, "CACHE_FILE", cache_file)

    names = [app["name"] for app in startmenu.collect_applications()]

    assert names == ["Tool"]


def test_load_menu_tree_reads_the_prefixed_menu_file_when_it_exists(startmenu, monkeypatch):
    monkeypatch.setenv("XDG_MENU_PREFIX", "plasma-")
    startmenu._menu_tree_cache.update(stamp=None, tree=None)

    assert set(startmenu.load_menu_tree()) == {"folders", "entries"}


def test_show_with_debug_keys_schedules_one_key_press_per_name(startmenu, qt_app, monkeypatch, tmp_path):
    monkeypatch.setenv("CHICAGO95_DEBUG_KEYS", "Down,Escape")
    monkeypatch.setattr(startmenu, "SETTINGS_FILE", tmp_path / "chicago95rc")
    scheduled_delays = []
    monkeypatch.setattr(QTimer, "singleShot", lambda delay, _callback: scheduled_delays.append(delay))
    controller = startmenu.StartMenu(qt_app)

    controller.show()
    controller.hide()

    assert [delay for delay in scheduled_delays if delay] == [400, 800]


def test_load_menu_tree_skips_submenus_without_entries(startmenu, monkeypatch):
    root = xdg.Menu.Menu()
    root.Entries = [xdg.Menu.Menu()]
    monkeypatch.setattr(xdg.Menu, "parse", lambda _menu_file: root)
    startmenu._menu_tree_cache.update(stamp=None, tree=None)

    assert startmenu.load_menu_tree() == {"folders": [], "entries": []}
