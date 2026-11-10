import os


def root_action(menu, text):
    return next(action for action in menu.actions() if action.text() == text)


def test_log_off_entry_launches_shutdown_tool_in_log_off_mode(startmenu, qt_app, monkeypatch):
    launched = []
    monkeypatch.setattr(startmenu, "launch", launched.append)

    menu = startmenu.build_root_menu()
    root_action(menu, "&Log Off...").trigger()

    assert launched == [[os.path.expanduser("~/.local/bin/chicago95-shutdown"), "--log-off"]]


def test_shut_down_entry_launches_shutdown_tool_with_all_choices(startmenu, qt_app, monkeypatch):
    launched = []
    monkeypatch.setattr(startmenu, "launch", launched.append)

    menu = startmenu.build_root_menu()
    root_action(menu, "Sh&ut Down...").trigger()

    assert launched == [[os.path.expanduser("~/.local/bin/chicago95-shutdown")]]


def test_banner_text_is_chicago95_without_a_settings_file(startmenu, tmp_path):
    assert startmenu.banner_text(tmp_path / "chicago95rc") == "Chicago95"


def test_banner_text_comes_from_start_menu_group_written_by_kwriteconfig6(startmenu, tmp_path):
    settings = tmp_path / "chicago95rc"
    settings.write_text("[StartMenu]\nbannerText=Linux 6.17\n")

    assert startmenu.banner_text(settings) == "Linux 6.17"
