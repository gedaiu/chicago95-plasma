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


def test_banner_is_chicago95_light_grey_on_grey_without_a_settings_file(startmenu, tmp_path):
    assert startmenu.banner_settings(tmp_path / "chicago95rc") == {
        "bannerText": "Chicago95", "bannerBackground": "#808080", "bannerTextColor": "#C0C0C0",
        "bannerNumberColor": "#FFFFFF", "style": "1995"}


def test_banner_text_and_gradient_come_from_start_menu_group(startmenu, tmp_path):
    settings = tmp_path / "chicago95rc"
    settings.write_text("[StartMenu]\nbannerText=Linux 6.17\nbannerBackground=#000000,#1084D0\nbannerTextColor=#FFFFFF\n")

    assert startmenu.banner_settings(settings) == {
        "bannerText": "Linux 6.17", "bannerBackground": "#000000,#1084D0", "bannerTextColor": "#FFFFFF",
        "bannerNumberColor": "#FFFFFF", "style": "1995"}


def test_banner_parts_set_words_bold_and_numbers_thin(startmenu):
    assert [startmenu.banner_parts(text) for text in ("Chicago95", "Windows 2000 Professional", "Linux")] == [
        [("Chicago", True), ("95", False)],
        [("Windows ", True), ("2000", False), (" Professional", True)],
        [("Linux", True)]]
