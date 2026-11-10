import subprocess

import pytest

from conftest import REPO, load_script, run_bash_with_steps


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


def test_read_settings_returns_saved_keys_and_values(control_panel, tmp_path):
    saved = tmp_path / "setup.conf"
    saved.write_text("SAVER=maze\nLOGIN_TITLE=Log On = %h\n")

    assert control_panel.read_settings(saved) == {"SAVER": "maze", "LOGIN_TITLE": "Log On = %h"}


def test_read_settings_returns_empty_dict_without_a_file(control_panel, tmp_path):
    assert control_panel.read_settings(tmp_path / "missing.conf") == {}


def test_write_then_read_settings_keeps_every_value_in_order(control_panel, tmp_path):
    saved = tmp_path / "config/chicago95/setup.conf"
    settings = {"LOOK": "2000", "SAVER": "maze", "LOGIN_TITLE": "Hello"}

    control_panel.write_settings(saved, settings)

    assert (list(control_panel.read_settings(saved).items()), saved.read_text()) == (list(settings.items()), "LOOK=2000\nSAVER=maze\nLOGIN_TITLE=Hello\n")


def test_components_for_login_title_and_saver_are_screensaver_then_sddm(control_panel):
    assert control_panel.components_for(["LOGIN_TITLE", "SAVER"]) == ["screensaver", "sddm"]


def test_components_for_look_are_look_taskbar_and_startmenu(control_panel):
    assert control_panel.components_for(["LOOK"]) == ["look", "taskbar", "startmenu"]


def test_components_for_login_style_are_splash_then_sddm_without_repeats(control_panel):
    assert control_panel.components_for(["LOGIN_STYLE", "LOGIN_LOGO", "EDITION"]) == ["splash", "sddm"]


def test_components_for_a_key_setup_does_not_know_is_empty(control_panel):
    assert control_panel.components_for(["REPO", "UNKNOWN"]) == []


def test_every_saved_key_maps_to_components_and_every_component_is_one_setup_runs(control_panel):
    setup_keys = run_bash_with_steps(REPO, "echo $SETTINGS_KEYS")[0].split()
    dispatched = subprocess.run(["sed", "-n", r"s/^        \(base|look.*\)) \"step_.*/\1/p", str(REPO / "install.sh")],
                                capture_output=True, text=True).stdout.strip().split("|")

    assert (sorted(control_panel.COMPONENTS_BY_KEY), set(control_panel.INSTALL_ORDER) - set(dispatched)) == (sorted(setup_keys), set())


def test_setup_command_runs_install_sh_plain_yes_with_settings_and_components_in_its_own_scope(control_panel, tmp_path):
    """Setup restarts plasmashell; the Control Panel may have been started by it. In its own systemd scope,
    Setup is not stopped with plasmashell's service halfway through."""
    command = control_panel.setup_command(tmp_path / "repo", tmp_path / "setup.conf", ["look", "sddm"])

    assert command == ["systemd-run", "--user", "--scope", "--quiet", "--collect",
                       f"{tmp_path}/repo/install.sh", "--plain", "--yes", f"--settings={tmp_path}/setup.conf", "--components=look,sddm"]


@pytest.mark.parametrize("text, expected", [("#000080", True), ("#0A246A,#A6CAF0", True), ("navy", False), ("#12345", False), ("#000080,", False), ("", False)])
def test_valid_colors_accepts_one_or_two_hex_colours_and_rejects_the_rest(control_panel, text, expected):
    assert control_panel.valid_colors(text) is expected


def test_parse_screensavers_reads_tab_separated_name_and_label_lines(control_panel):
    assert control_panel.parse_screensavers("deepstars\tDeep Stars\nmaze\tMaze\n\n") == [("deepstars", "Deep Stars"), ("maze", "Maze")]


def test_installed_sound_themes_lists_chicago95_first_then_names_and_only_themes_with_a_stereo_directory(control_panel, tmp_path):
    for theme_id, name, has_stereo in (("Windows98", "Windows 98", True), ("Chicago95", "Chicago95", True), ("Broken", "Broken", False), ("Plus98-Jungle", "Jungle", True)):
        (tmp_path / theme_id).mkdir()
        (tmp_path / theme_id / "index.theme").write_text(f"[Sound Theme]\nName={name}\n")
        if has_stereo:
            (tmp_path / theme_id / "stereo").mkdir()

    assert control_panel.installed_sound_themes([tmp_path]) == [("Chicago95", "Chicago95"), ("Plus98-Jungle", "Jungle"), ("Windows98", "Windows 98")]


def test_tasks_launchers_are_read_from_the_applets_config(control_panel, tmp_path):
    appletsrc = tmp_path / "plasma-org.kde.plasma.desktop-appletsrc"
    appletsrc.write_text("[Containments][2][Applets][5]\nplugin=org.chicago95.tasks\n\n"
                         "[Containments][2][Applets][5][Configuration][General]\nlaunchers=applications:firefox.desktop,applications:thunar.desktop\nlook=1998\n\n"
                         "[Containments][2][Applets][6]\nplugin=org.chicago95.clock\n")

    assert control_panel.read_launchers(appletsrc) == ["applications:firefox.desktop", "applications:thunar.desktop"]


@pytest.mark.parametrize("config", ["", "[Containments][2][Applets][5]\nplugin=org.chicago95.tasks\n"])
def test_tasks_launchers_are_unknown_when_the_applet_never_saved_any(control_panel, tmp_path, config):
    appletsrc = tmp_path / "appletsrc"
    appletsrc.write_text(config)

    assert control_panel.read_launchers(appletsrc) is None


@pytest.mark.parametrize("look", ["1995", "1998", "2000"])
def test_look_presets_match_what_setup_applies_for_that_look(control_panel, tmp_path, look):
    applied = run_bash_with_steps(tmp_path, f'apply_look {look}; echo "$SETUP_TITLE_ACTIVE|$SETUP_TITLE_INACTIVE|$SETUP_BANNER_BG|$SETUP_BANNER_FG|$SETUP_ICONS"')[0].split("|")
    preset = control_panel.LOOK_PRESETS[look]

    assert [preset[key] for key in ("TITLE_ACTIVE", "TITLE_INACTIVE", "BANNER_BG", "BANNER_FG", "ICONS")] == applied


@pytest.mark.parametrize("idle, lock, hidden", [(5, 5, True), (6, 5, True), (4, 5, False)])
def test_screensaver_is_hidden_by_the_lock_screen_unless_it_starts_first(control_panel, idle, lock, hidden):
    assert control_panel.screensaver_hidden_by_lock(idle, lock) is hidden


HOME_PAGE = ("Control Panel",)
TASKBAR_PAGE = ("Control Panel", "Taskbar")
QUICK_LAUNCH_TAB = ("Control Panel", "Taskbar", "Quick Launch")


def test_navigation_starts_at_the_control_panel_with_nowhere_to_go(control_panel):
    history = control_panel.NavigationHistory(HOME_PAGE)

    assert (history.current, history.can_go_back, history.can_go_forward) == (HOME_PAGE, False, False)


def test_visit_then_back_returns_to_the_control_panel_and_enables_forward(control_panel):
    history = control_panel.NavigationHistory(HOME_PAGE)
    history.visit(TASKBAR_PAGE)

    returned_to = history.back()

    assert (returned_to, history.current, history.can_go_back, history.can_go_forward) == (HOME_PAGE, HOME_PAGE, False, True)


def test_forward_after_back_returns_to_the_page_left(control_panel):
    history = control_panel.NavigationHistory(HOME_PAGE)
    history.visit(TASKBAR_PAGE)
    history.back()

    assert (history.forward(), history.can_go_forward) == (TASKBAR_PAGE, False)


def test_visiting_after_back_clears_the_forward_history(control_panel):
    history = control_panel.NavigationHistory(HOME_PAGE)
    history.visit(TASKBAR_PAGE)
    history.back()
    history.visit(("Control Panel", "Sounds"))

    assert (history.can_go_forward, history.back()) == (False, HOME_PAGE)


def test_visiting_the_page_already_shown_adds_no_history(control_panel):
    history = control_panel.NavigationHistory(HOME_PAGE)
    history.visit(TASKBAR_PAGE)
    history.visit(TASKBAR_PAGE)

    assert (history.back(), history.can_go_back) == (HOME_PAGE, False)


def test_back_and_forward_at_the_ends_stay_on_the_current_page(control_panel):
    history = control_panel.NavigationHistory(HOME_PAGE)

    assert (history.back(), history.forward(), history.current) == (HOME_PAGE, HOME_PAGE, HOME_PAGE)


def test_history_lists_pages_for_the_back_and_forward_drop_downs_nearest_first(control_panel):
    history = control_panel.NavigationHistory(HOME_PAGE)
    history.visit(TASKBAR_PAGE)
    history.visit(QUICK_LAUNCH_TAB)
    history.back()
    history.back()

    assert (history.pages_before, history.pages_after) == ([], [TASKBAR_PAGE, QUICK_LAUNCH_TAB])


def test_up_from_quick_launch_tab_is_the_taskbar_page_and_from_the_control_panel_stays(control_panel):
    assert (control_panel.parent_location(QUICK_LAUNCH_TAB), control_panel.parent_location(HOME_PAGE)) == (TASKBAR_PAGE, HOME_PAGE)


def test_breadcrumb_text_joins_the_path_with_arrows(control_panel):
    assert control_panel.breadcrumb_text(QUICK_LAUNCH_TAB) == "Control Panel > Taskbar > Quick Launch"


@pytest.mark.parametrize("text, expected", [
    ("#808080", True), ("#000000,#000021@200,#000081@120,#0000FF@0", True), ("#00007B@95", True),
    ("navy", False), ("#12345", False), ("#000000@", False), ("#000000,", False), ("", False)])
def test_valid_banner_colors_accept_gradient_stops_with_pixel_offsets(control_panel, text, expected):
    assert control_panel.valid_banner_colors(text) is expected
