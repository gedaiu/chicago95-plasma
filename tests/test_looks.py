from pathlib import Path

import pytest
from conftest import REPO, load_script, run_bash_with_steps, run_bash_with_steps_result
from test_install import run_setup

LOOKS_DIR = REPO / "looks"
LOOK_NAMES = ["1995", "1998", "2000", "2001", "aero", "luna"]
REPO_RELATIVE_KEYS = {"SPLASH_IMAGE", "BACKGROUND_IMAGE"}
LOOK_KEYS = {
    "CONTROL_PANEL_STYLE", "DECORATION", "WIDGET_STYLE", "TASKBAR_STYLE",
    "START_MENU_STYLE", "BEVEL", "FACE", "SELECTION", "TITLE_ACTIVE",
    "TITLE_INACTIVE", "BANNER_BG", "BANNER_FG", "ICONS",
    "START_LOGO", "BANNER_TEXT", "LOGIN_STYLE", "LOGIN_TITLE",
    "LOGIN_MESSAGE", "LOGIN_ICON", "LOGIN_LOGO", "EDITION", "TAGLINE",
    "COMPANY", "COMPANY_LOGO", "BOOT_STYLE", "SPLASH_IMAGE", "LOADING_TEXT",
    "LOADING_FOOTER", "SOUND_THEME", "BACKGROUND_MODE", "BACKGROUND_COLOR",
    "BACKGROUND_IMAGE", "BACKGROUND_FILL", "DESKTOP_ICONS", "QUICK_LAUNCH",
    "TASK_GROUPING", "ANIM_MINIMIZE", "ANIM_MAXIMIZE",
}


def parse_look(path):
    settings = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        settings[key] = value
    return settings


def test_looks_folder_holds_1995_1998_2000_2001_luna_and_aero():
    assert sorted(path.stem for path in LOOKS_DIR.glob("*.conf")) == LOOK_NAMES


@pytest.mark.parametrize("look_name", LOOK_NAMES)
def test_look_file_defines_every_look_key(look_name):
    assert set(parse_look(LOOKS_DIR / f"{look_name}.conf")) == LOOK_KEYS


def expected_setup_values(look_name):
    settings = parse_look(LOOKS_DIR / f"{look_name}.conf")
    values = {"LOOK": look_name}
    for key in sorted(LOOK_KEYS):
        is_repo_path = key in REPO_RELATIVE_KEYS and "/" in settings[key]
        values[key] = f"{REPO}/{settings[key]}" if is_repo_path else settings[key]
    return values


@pytest.mark.parametrize("look_name", LOOK_NAMES)
def test_apply_look_sets_every_value_of_that_looks_file(tmp_path, look_name):
    keys = " ".join(["LOOK", *sorted(LOOK_KEYS)])
    script = f'apply_look {look_name}; for key in {keys}; do variable=SETUP_$key; printf "%s=%s\\n" "$key" "${{!variable}}"; done'
    applied = dict(line.split("=", 1) for line in run_bash_with_steps(tmp_path, script))
    assert applied == expected_setup_values(look_name)


def test_apply_look_win2k_fails_naming_the_known_looks(tmp_path):
    result = run_bash_with_steps_result(tmp_path, "apply_look win2k")
    assert (result.returncode != 0, result.stderr.strip()) == (
        True,
        'Unknown look "win2k"; known looks: 1995 1998 2000 2001 aero luna',
    )


@pytest.mark.skipif(not Path("/usr/share/plasma/shells/org.kde.plasma.desktop").exists(), reason="Setup skips the lock screen step without the Plasma shell")
def test_look_2000_over_a_saved_1998_install_writes_the_2000_lock_screen(tmp_path):
    saved_settings = ["LOOK=1998", *(f"{key}={value}" for key, value in parse_look(LOOKS_DIR / "1998.conf").items())]
    saved_file = tmp_path / ".config/chicago95/setup.conf"
    saved_file.parent.mkdir(parents=True)
    saved_file.write_text("\n".join([*saved_settings, "COMPONENTS=base look lockscreen"]) + "\n")

    result = run_setup(tmp_path, "--look=2000", "--components=lockscreen")
    lock_screen_settings = tmp_path / ".local/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/settings.js"

    assert (result.returncode, lock_screen_settings.read_text()) == (
        0,
        '.pragma library\nvar look = "2000";\nvar desktopColor = "#3A6EA5";\n',
    )


def test_lock_screen_style_is_the_login_style_whatever_the_start_menu(tmp_path):
    cases = [
        ("classic", "1998"),
        ("classic", "2001"),
        ("classic", "2000"),
        ("2000", "1998"),
        ("luna", "2000"),
        ("aero", "1995"),
    ]
    script = "; ".join(
        f"SETUP_LOGIN_STYLE={login} SETUP_START_MENU_STYLE={menu}; lockscreen_style; echo" for login, menu in cases
    )

    assert run_bash_with_steps(tmp_path, script) == ["classic", "classic", "classic", "2000", "luna", "aero"]


@pytest.fixture(scope="module")
def control_panel():
    return load_script("chicago95-control-panel")


@pytest.mark.parametrize("look_name", LOOK_NAMES)
def test_control_panel_preset_is_that_looks_file(control_panel, look_name):
    assert control_panel.LOOK_PRESETS[look_name] == parse_look(LOOKS_DIR / f"{look_name}.conf")


def display_page_over_saved_1998_look(control_panel):
    saved_settings = {"LOOK": "1998", **parse_look(LOOKS_DIR / "1998.conf")}
    actions = control_panel.Actions()
    tabs = [
        (tab_name, control_panel.build_tab("Display", tab_name, saved_settings, actions))
        for tab_name in control_panel.PAGE_TABS["Display"]
    ]
    page = control_panel.PropertiesPage("Display", tabs, lambda changes: True)
    appearance = next(tab for tab_name, tab in tabs if tab_name == "Appearance")
    appearance.scheme.setCurrentIndex(appearance.scheme.findData("2000"))
    return page


def test_windows_2000_scheme_over_a_saved_1998_look_changes_every_value_the_two_looks_differ_in(control_panel, qt_app):
    saved_look = parse_look(LOOKS_DIR / "1998.conf")
    look_2000 = parse_look(LOOKS_DIR / "2000.conf")
    page = display_page_over_saved_1998_look(control_panel)

    look_keys = {*look_2000, "LOOK"}
    changed = {key: value for key, value in page.changed_values().items() if key in look_keys}

    assert changed == {
        "LOOK": "2000",
        **{key: value for key, value in look_2000.items() if value != saved_look[key]},
    }


def test_windows_2000_scheme_over_a_saved_1998_look_reruns_the_lock_screen_login_and_splash(control_panel, qt_app):
    page = display_page_over_saved_1998_look(control_panel)

    components = control_panel.components_for(page.changed_values())

    assert {"lockscreen", "sddm", "splash"} & set(components) == {"lockscreen", "sddm", "splash"}
