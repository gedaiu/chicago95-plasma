import subprocess

import pytest
from conftest import REPO, load_script

COMPONENTS = load_script("chicago95-control-panel").INSTALL_ORDER


def apply_like_the_control_panel(home, components):
    settings_path = home / "setup.conf"
    settings_path.write_text(f"REPO={REPO}\n")
    return subprocess.run(
        [
            str(REPO / "install.sh"),
            "--plain",
            "--yes",
            "--dry-run",
            f"--settings={settings_path}",
            f"--components={components}",
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        timeout=120,
        env={"PATH": "/usr/bin:/bin", "HOME": str(home), "TMPDIR": str(home)},
        check=False,
    )


def terminal_complaints(result):
    return [line for line in (result.stdout + result.stderr).splitlines() if "/dev/tty" in line]


@pytest.mark.parametrize("component", COMPONENTS)
def test_applying_the_component_without_a_terminal_exits_0_and_never_opens_dev_tty(component, tmp_path):
    result = apply_like_the_control_panel(tmp_path, component)

    assert (result.returncode, terminal_complaints(result)) == (0, [])


def test_applying_every_component_at_once_without_a_terminal_exits_0_and_never_opens_dev_tty(tmp_path):
    result = apply_like_the_control_panel(tmp_path, ",".join(COMPONENTS))

    assert (result.returncode, terminal_complaints(result)) == (0, [])


CONTROL_PANEL = load_script("chicago95-control-panel")

A_CHANGED_VALUE_FOR = {
    "LOOK": "1998",
    "TITLE_ACTIVE": "#000080,#1084D0",
    "TITLE_INACTIVE": "#808080",
    "ICONS": "se98",
    "FONT": "MS W98 UI",
    "FONT_SCOPE": "desktop",
    "ANIM_WINDOWS": "none",
    "ANIM_MINIMIZE": "zoom",
    "ANIM_MAXIMIZE": "zoom",
    "ANIM_DIALOGS": "none",
    "ANIM_WOBBLY": "no",
    "ANIM_SHOW_DESKTOP": "none",
    "ANIM_DESKTOPS": "none",
    "ANIM_SESSION": "none",
    "ANIM_MENUS": "slide",
    "ANIM_NOTIFICATIONS": "none",
    "ANIM_TASKBAR": "none",
    "ANIM_SPEED": "0",
    "BANNER_BG": "#808080",
    "BANNER_FG": "#FFFFFF",
    "BANNER_TEXT": "Hello",
    "CURSOR": "48",
    "PANEL": "28",
    "TASK_BUTTON_WIDTH": "160",
    "QUICK_LAUNCH": "yes",
    "LAUNCHERS": "applications:org.kde.dolphin.desktop",
    "TASKBAR_AUTOHIDE": "yes",
    "TASKBAR_ON_TOP": "no",
    "CLOCK_SHOW": "no",
    "CLOCK_HOURS": "24",
    "START_TEXT": "Go",
    "SAVER": "maze",
    "IDLE_MIN": "10",
    "LOGIN_STYLE": "2000",
    "EDITION": "Professional",
    "TAGLINE": "Built on Linux",
    "COMPANY": "Chicago95",
    "LOGIN_TITLE": "Log On",
    "LOGIN_MESSAGE": "Welcome",
    "LOADING_TEXT": "Starting up...",
    "LOADING_FOOTER": "Chicago95",
    "SOUND_THEME": "Chicago95",
    "CLIPPY_AUTOSTART": "yes",
    "EXPLORER": "thunar",
    "BACKGROUND_MODE": "color",
    "BACKGROUND_COLOR": "#008080",
}


def a_changed_value(key):
    return A_CHANGED_VALUE_FOR.get(key, "")


def command_the_panel_runs_when_applying(tmp_path, qt_app, changes):
    ran = []
    actions = CONTROL_PANEL.Actions(run_setup=lambda parent, command: ran.append(command))
    panel = CONTROL_PANEL.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
    CONTROL_PANEL.write_settings(panel.settings_path, {"REPO": str(REPO)})
    panel.apply_changes(changes)
    return ran


@pytest.mark.parametrize("key", sorted(CONTROL_PANEL.COMPONENTS_BY_KEY))
def test_applying_a_changed_key_runs_setup_that_exits_0_without_a_terminal(key, tmp_path, qt_app):
    [command] = command_the_panel_runs_when_applying(tmp_path, qt_app, {key: a_changed_value(key)})
    setup_command = [argument for argument in command if argument not in CONTROL_PANEL.OWN_SCOPE]

    result = subprocess.run(
        [*setup_command, "--dry-run"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        timeout=120,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )

    assert (result.returncode, terminal_complaints(result)) == (0, [])
