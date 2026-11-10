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
