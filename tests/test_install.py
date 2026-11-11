import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import REPO, run_bash_with_steps


def test_dry_run_of_sddm_component_writes_the_zz_override_without_asking_for_a_password(tmp_path):
    result = subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--components=sddm"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert (
        result.returncode,
        "Administrator password" in result.stdout,
        "would: sudo tee /etc/sddm.conf.d/zz-chicago95.conf" in log,
    ) == (0, False, True)


def run_setup(home, *arguments):
    stubs = home / "stubs"
    stubs.mkdir(exist_ok=True)
    for command in (
        "systemctl",
        "gdbus",
        "qdbus",
        "qdbus6",
        "kwriteconfig6",
        "plasma-apply-colorscheme",
        "plasma-apply-desktoptheme",
        "plasma-apply-cursortheme",
        "xrdb",
    ):
        (stubs / command).write_text("#!/bin/sh\nexit 0\n")
        (stubs / command).chmod(0o755)
    (stubs / "plasmashell").write_text("#!/bin/sh\necho plasmashell 6.8.2\n")
    (stubs / "plasmashell").chmod(0o755)
    return subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", *arguments],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=120,
        env={"PATH": f"{stubs}:/usr/bin:/bin", "HOME": str(home), "TMPDIR": str(home)},
        check=False,
    )


def test_reinstall_keeps_the_original_file_as_the_only_backup_and_lists_it_once(tmp_path):
    launcher = tmp_path / ".local/share/applications/qmmp.desktop"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("original launcher\n")

    first, second = (
        run_setup(tmp_path, "--components=winamp"),
        (time.sleep(1.1), run_setup(tmp_path, "--components=winamp"))[1],
    )
    backups = sorted(
        path.read_text()
        for path in (tmp_path / ".local/share/chicago95").glob("backup-*/.local/share/applications/qmmp.desktop")
    )
    manifest = (tmp_path / ".local/share/chicago95/installed-files.txt").read_text().splitlines()

    assert (first.returncode, second.returncode, backups, manifest.count(str(launcher))) == (
        0,
        0,
        ["original launcher\n"],
        1,
    )


def test_dry_run_of_the_2000_look_downloads_the_waving_flag_for_the_loading_screen(tmp_path):
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--look=2000", "--components=splash"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert f"would: python3 {REPO}/setup/fetch-waving-flag.py {tmp_path}/.local/share/chicago95/waving-flag.png" in log


def test_login_theme_settings_carry_title_message_and_picture_without_banner_texts(tmp_path):
    script = (
        f'REPO={REPO}; source {REPO}/setup/steps.sh; SETUP_LOGIN_TITLE="Welcome to %h"; '
        'SETUP_LOGIN_MESSAGE="Hi & welcome"; SETUP_LOGIN_ICON=padlock; sddm_theme_conf'
    )
    settings = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
        check=False,
    ).stdout.splitlines()

    assert (
        {"loginTitle=Welcome to %h", "loginMessage=Hi & welcome", "loginIcon=login-icon.svg"} <= set(settings),
        [line for line in settings if line.startswith("brand")],
    ) == (True, [])


def test_dry_run_of_the_2000_login_draws_the_banner_with_the_shut_down_code(tmp_path):
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--login-style=2000", "--components=sddm"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert (
        f"would: env QT_QPA_PLATFORM=offscreen python3 {REPO}/bin/chicago95-shutdown "
        f"--login-banner {tmp_path}/.local/share/chicago95/login-banner.png"
    ) in log


def test_dry_run_of_the_2000_look_alone_writes_the_look_before_redrawing_the_bevels(tmp_path):
    """chicago95-sync-colors draws the decoration and the taskbar with the look's bevel colours, read from
    chicago95rc: the look step writes it even without the Start menu."""
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--look=2000", "--components=look"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()
    style = log.find("would: kwriteconfig6 --file chicago95rc --group StartMenu --key style 2000")
    redraw = log.find("chicago95-sync-colors --force")

    assert -1 < style < redraw, (style, redraw)


def test_dry_run_of_the_base_theme_selects_chicago95_for_gtk_3_and_4(tmp_path):
    """GTK programs draw their own widgets, and GTK 4 its own title bars: both take the classic theme."""
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--components=base"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
            "TMPDIR": str(tmp_path),
            "CHICAGO95_SRC": str(Path.home() / "src/Chicago95"),
        },
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert [
        f"would: kwriteconfig6 --file {tmp_path}/.config/gtk-{version}/settings.ini "
        "--group Settings --key gtk-theme-name Chicago95" in log
        for version in ("3.0", "4.0")
    ] == [True, True]


def test_dry_run_of_the_windows_2000_sounds_selects_that_theme_for_plasma(tmp_path):
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--sounds=Windows2000", "--components=sounds"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert [
        line in log
        for line in (
            "would: kwriteconfig6 --file kdeglobals --group Sounds --key Theme Windows2000",
            f"would: cp -r {REPO}/data/sound-themes/Windows2000 {tmp_path}/.local/share/sounds/Windows2000",
        )
    ] == [True, True]


def test_dry_run_of_the_2000_look_puts_the_2000_toolbar_buttons_over_its_icon_set(tmp_path):
    subprocess.run(
        [
            str(REPO / "install.sh"),
            "--plain",
            "--yes",
            "--dry-run",
            "--look=2000",
            "--icons=chicago95",
            "--components=look",
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert [
        line in log
        for line in (
            f"would: cp -r {REPO}/data/toolbar-icons/2000 {tmp_path}/.local/share/icons/Chicago95-Toolbar/actions/22",
            "would: kwriteconfig6 --file kdeglobals --group Icons --key Theme Chicago95-Toolbar",
        )
    ] == [True, True]


def test_every_run_writes_the_look_into_each_taskbar_applet(tmp_path):
    """A taskbar built under one look follows the next: Start, the task list (its Quick Launch shows from
    1998 on), the tray and the clock each take the chosen look."""
    log = tmp_path / "setup.log"
    script = (
        f'REPO={REPO}; source {REPO}/setup/steps.sh; plasma_script() {{ printf "%s\\n" "$1"; }}; '
        f"SETUP_IN_PLASMA=1 SETUP_DRY_RUN=0 SETUP_LOG={log} SETUP_START_MENU_STYLE=2000 apply_taskbar"
    )
    subprocess.run(
        ["bash", "-c", script], timeout=30, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}, check=False
    )
    written = log.read_text()

    assert [
        f"'{applet}'" in written
        for applet in ("org.chicago95.start", "org.chicago95.tasks", "org.chicago95.trayframe", "org.chicago95.clock")
    ] == [True] * 4
    assert written.count("widget.writeConfig('look', \"2000\")") == 1  # one loop over the four applets


def test_an_empty_quick_launch_gets_the_default_programs_on_a_look_that_shows_it(tmp_path):
    """A taskbar first built under 1995 saved an empty Quick Launch; the defaults come from the task
    list's own settings file."""
    log = tmp_path / "setup.log"
    script = (
        f'REPO={REPO}; source {REPO}/setup/steps.sh; plasma_script() {{ printf "%s\\n" "$1"; }}; '
        f"SETUP_IN_PLASMA=1 SETUP_DRY_RUN=0 SETUP_LOG={log} SETUP_START_MENU_STYLE=1998 apply_taskbar"
    )
    subprocess.run(
        ["bash", "-c", script], timeout=30, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}, check=False
    )
    written = log.read_text()

    assert 'readConfig("launchers"' in written and '"applications:firefox.desktop"' in written


def test_load_settings_with_saved_login_title_puts_it_in_the_login_theme_conf(tmp_path):
    saved = tmp_path / "setup.conf"
    saved.write_text("LOGIN_TITLE=Hello from settings\n")

    theme_conf = run_bash_with_steps(tmp_path, f"load_settings {saved}; sddm_theme_conf")

    assert "loginTitle=Hello from settings" in theme_conf


def test_dry_run_with_settings_file_applies_the_saved_sound_theme(tmp_path):
    saved = tmp_path / "setup.conf"
    saved.write_text("SOUND_THEME=Windows2000\n")
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", f"--settings={saved}", "--components=sounds"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert "sounds=Windows2000" in log


def test_settings_file_with_command_substitution_and_unknown_keys_runs_nothing(tmp_path):
    saved = tmp_path / "setup.conf"
    saved.write_text(f"EVIL=$(touch {tmp_path}/unknown-key)\nLOGIN_TITLE=$(touch {tmp_path}/known-key)\n")

    theme_conf = run_bash_with_steps(tmp_path, f"load_settings {saved}; sddm_theme_conf")

    assert (
        (tmp_path / "unknown-key").exists(),
        (tmp_path / "known-key").exists(),
        f"loginTitle=$(touch {tmp_path}/known-key)" in theme_conf,
    ) == (False, False, True)


def test_settings_with_look_2000_and_custom_active_title_keep_the_looks_inactive_title(tmp_path):
    saved = tmp_path / "setup.conf"
    saved.write_text("LOOK=2000\nTITLE_ACTIVE=#FF0000\n")
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", f"--settings={saved}", "--components=look"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert "(title bars: active #FF0000, inactive #808080,#C0C0C0)" in log


def test_settings_with_custom_look_leave_the_default_look_s_colours(tmp_path):
    saved = tmp_path / "setup.conf"
    saved.write_text("LOOK=custom\n")

    look = run_bash_with_steps(
        tmp_path, f"apply_look 1998; load_settings {saved}; echo $SETUP_LOOK $SETUP_TITLE_ACTIVE"
    )

    assert look == ["custom #000080,#1084D0"]


def read_saved_settings(home):
    lines = (home / ".config/chicago95/setup.conf").read_text().splitlines()
    return dict(line.split("=", 1) for line in lines)


def test_install_saves_the_chosen_sound_theme_the_look_and_the_repo_to_setup_conf(tmp_path):
    run_setup(tmp_path, "--components=sounds", "--sounds=Windows98")

    saved = read_saved_settings(tmp_path)

    assert {key: saved.get(key) for key in ("SOUND_THEME", "REPO", "LOOK")} == {
        "SOUND_THEME": "Windows98",
        "REPO": str(REPO),
        "LOOK": "1995",
    }


def test_install_keeps_saved_keys_it_did_not_set_this_time(tmp_path):
    saved_file = tmp_path / ".config/chicago95/setup.conf"
    saved_file.parent.mkdir(parents=True)
    saved_file.write_text("LAUNCHERS=applications:firefox.desktop\n")

    run_setup(tmp_path, "--components=sounds", "--sounds=Windows98")

    assert read_saved_settings(tmp_path)["LAUNCHERS"] == "applications:firefox.desktop"


def test_saved_settings_load_back_to_the_same_values(tmp_path):
    reloaded = run_bash_with_steps(
        tmp_path,
        f"SETUP_DRY_RUN=0; MANIFEST={tmp_path}/manifest; STATE_DIR={tmp_path}; "
        'SETUP_LOGIN_TITLE="Log On = %h"; SETUP_SAVER=maze; save_settings; '
        "unset SETUP_LOGIN_TITLE SETUP_SAVER; "
        f'load_settings {tmp_path}/.config/chicago95/setup.conf; echo "$SETUP_LOGIN_TITLE|$SETUP_SAVER"',
    )

    assert reloaded == ["Log On = %h|maze"]


def taskbar_script_written(tmp_path, assignments=""):
    log = tmp_path / "setup.log"
    script = (
        f'REPO={REPO}; source {REPO}/setup/steps.sh; plasma_script() {{ printf "%s\\n" "$1"; }}; '
        f"SETUP_IN_PLASMA=1 SETUP_DRY_RUN=0 SETUP_LOG={log} {assignments} apply_taskbar"
    )
    subprocess.run(
        ["bash", "-c", script], timeout=30, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}, check=False
    )
    return log.read_text()


def test_task_button_width_220_is_written_to_each_task_list(tmp_path):
    written = taskbar_script_written(tmp_path, "SETUP_TASK_BUTTON_WIDTH=220")

    assert (
        "panel.widgets('org.chicago95.tasks').forEach(widget => { widget.currentConfigGroup = ['General']; "
        "widget.writeConfig('maxButtonWidth', 220); });" in " ".join(written.split())
    )


def test_task_button_width_is_left_alone_when_no_width_was_chosen(tmp_path):
    assert "maxButtonWidth" not in taskbar_script_written(tmp_path)


def test_task_button_width_flag_is_saved_with_the_other_choices(tmp_path):
    run_setup(tmp_path, "--components=sounds", "--task-button-width=220")

    assert read_saved_settings(tmp_path)["TASK_BUTTON_WIDTH"] == "220"


def test_panel_layout_for_a_new_taskbar_uses_the_chosen_task_button_width(tmp_path):
    layout = run_bash_with_steps(
        tmp_path, f"SETUP_TASK_BUTTON_WIDTH=220 PANEL_HEIGHT=28 panel_layout_script {REPO}/plasmoids/panel-layout.js"
    )

    assert 'tasks.writeConfig("maxButtonWidth", 220);' in layout


def test_saved_launchers_are_written_to_each_task_list_as_a_list(tmp_path):
    written = taskbar_script_written(
        tmp_path, "SETUP_LAUNCHERS=applications:firefox.desktop,applications:org.kde.konsole.desktop"
    )

    assert (
        'widget.writeConfig(\'launchers\', ["applications:firefox.desktop", "applications:org.kde.konsole.desktop"]);'
        in " ".join(written.split())
    )


def test_empty_saved_launchers_clear_the_quick_launch_instead_of_restoring_the_defaults(tmp_path):
    written = taskbar_script_written(tmp_path, "SETUP_START_MENU_STYLE=1998 SETUP_LAUNCHERS=")

    assert (
        "widget.writeConfig('launchers', []);" in " ".join(written.split()),
        "applications:thunar.desktop" in written,
    ) == (True, False)


def test_panel_layout_for_a_new_taskbar_starts_with_the_saved_launchers(tmp_path):
    layout = run_bash_with_steps(
        tmp_path,
        "SETUP_LAUNCHERS=applications:firefox.desktop PANEL_HEIGHT=28 "
        f"panel_layout_script {REPO}/plasmoids/panel-layout.js",
    )

    assert 'tasks.writeConfig("launchers", ["applications:firefox.desktop"]);' in layout


@pytest.mark.parametrize(
    "assignments",
    [
        "SETUP_START_MENU_STYLE=1998",
        "SETUP_START_MENU_STYLE=2000 SETUP_LAUNCHERS=applications:a.desktop SETUP_TASK_BUTTON_WIDTH=200",
    ],
)
def test_taskbar_script_parses_as_javascript(qt_app, tmp_path, assignments):
    """plasmashell runs the script; the engine here stops at the first undefined name,
    panels(), once it has parsed it."""
    from PySide6.QtQml import QJSEngine, QJSValue

    engine = QJSEngine()
    outcome = engine.evaluate(taskbar_script_written(tmp_path, assignments))

    assert outcome.errorType() == QJSValue.ErrorType.ReferenceError


def squeezed(text):
    return " ".join(text.split())


@pytest.mark.parametrize(
    "assignments, hiding",
    [
        ("SETUP_TASKBAR_AUTOHIDE=yes", "autohide"),
        ("SETUP_TASKBAR_ON_TOP=no", "windowsgobelow"),
        ("SETUP_TASKBAR_AUTOHIDE=yes SETUP_TASKBAR_ON_TOP=no", "autohide"),
        ("SETUP_TASKBAR_AUTOHIDE=no SETUP_TASKBAR_ON_TOP=yes", "none"),
    ],
)
def test_taskbar_hiding_follows_the_saved_auto_hide_and_always_on_top_choices(tmp_path, assignments, hiding):
    written = squeezed(taskbar_script_written(tmp_path, assignments))

    assert f"if (panel.widgets('org.chicago95.tasks').length > 0) panel.hiding = \"{hiding}\";" in written


def test_taskbar_hiding_is_left_alone_when_nothing_was_chosen(tmp_path):
    assert "panel.hiding" not in taskbar_script_written(tmp_path)


def test_clock_hour_format_24_is_written_to_each_clock(tmp_path):
    written = squeezed(taskbar_script_written(tmp_path, "SETUP_CLOCK_HOURS=24"))

    assert (
        "panel.widgets('org.chicago95.clock').forEach(widget => { widget.currentConfigGroup = ['General']; "
        "widget.writeConfig('hourFormat', \"24\"); });" in written
    )


def test_unknown_clock_hour_format_is_not_written(tmp_path):
    assert "hourFormat" not in taskbar_script_written(tmp_path, "SETUP_CLOCK_HOURS='1); evil('")


def test_hiding_the_clock_removes_it_from_the_taskbar(tmp_path):
    written = squeezed(taskbar_script_written(tmp_path, "SETUP_CLOCK_SHOW=no"))

    assert "panel.widgets('org.chicago95.clock').forEach(widget => widget.remove());" in written


def test_showing_the_clock_adds_one_to_a_taskbar_without_it(tmp_path):
    written = squeezed(taskbar_script_written(tmp_path, "SETUP_CLOCK_SHOW=yes SETUP_START_MENU_STYLE=2000"))

    assert (
        "if (panel.widgets('org.chicago95.tasks').length > 0 && panel.widgets('org.chicago95.clock').length === 0) { "
        "const clock = panel.addWidget('org.chicago95.clock'); clock.currentConfigGroup = ['General']; "
        "clock.writeConfig('look', \"2000\"); clock.writeConfig('taskbarStyle', \"classic\"); "
        "clock.writeConfig('bevel', \"1995\"); }"
    ) in written


def test_panel_layout_for_a_new_taskbar_follows_hiding_clock_and_hour_format(tmp_path):
    layout = run_bash_with_steps(
        tmp_path,
        "SETUP_TASKBAR_AUTOHIDE=yes SETUP_CLOCK_HOURS=24 "
        f"PANEL_HEIGHT=28 panel_layout_script {REPO}/plasmoids/panel-layout.js",
    )

    assert ('panel.hiding = "autohide";' in layout, 'clock.writeConfig("hourFormat", "24");' in layout) == (True, True)


def test_panel_layout_for_a_new_taskbar_leaves_the_clock_out_when_hidden(tmp_path):
    layout = run_bash_with_steps(
        tmp_path,
        "SETUP_CLOCK_SHOW=no SETUP_CLOCK_HOURS=24 PANEL_HEIGHT=28 "
        f"panel_layout_script {REPO}/plasmoids/panel-layout.js",
    )

    assert [line for line in layout if "org.chicago95.clock" in line or line.startswith("clock.")] == []


@pytest.mark.parametrize(
    "assignments",
    [
        "SETUP_TASKBAR_AUTOHIDE=yes SETUP_CLOCK_SHOW=no",
        "SETUP_TASKBAR_ON_TOP=no SETUP_CLOCK_SHOW=yes SETUP_CLOCK_HOURS=12 SETUP_START_MENU_STYLE=2000",
    ],
)
def test_taskbar_script_with_behaviour_choices_parses_as_javascript(qt_app, tmp_path, assignments):
    from PySide6.QtQml import QJSEngine, QJSValue

    engine = QJSEngine()
    outcome = engine.evaluate(taskbar_script_written(tmp_path, assignments))

    assert outcome.errorType() == QJSValue.ErrorType.ReferenceError


@pytest.mark.parametrize("sudo_exit_code, expected", [(0, ("-A -v", "0")), (1, ("-A -v", "1"))])
def test_ui_sudo_with_sudo_askpass_asks_sudo_to_authenticate_through_it(tmp_path, sudo_exit_code, expected):
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    (stubs / "sudo").write_text(f'#!/bin/sh\necho "$@" >> {tmp_path}/sudo-calls\nexit {sudo_exit_code}\n')
    (stubs / "sudo").chmod(0o755)

    status = subprocess.run(
        [
            "bash",
            "-c",
            f'source {REPO}/setup/ui.sh; SETUP_DRY_RUN=0 SUDO_ASKPASS=/bin/true ui_sudo "why" "sudo cp a b"; echo $?',
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": f"{stubs}:/usr/bin:/bin", "HOME": str(tmp_path)},
        check=False,
    ).stdout.split()[-1]

    assert ((tmp_path / "sudo-calls").read_text().strip(), status) == expected


def dry_run_log(tmp_path, *arguments):
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", *arguments],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    return next(tmp_path.glob("chicago95-setup-*.log")).read_text()


def kwriteconfig(file, group, key, value):
    return f"would: kwriteconfig6 --file {file} --group {group} --key {key} {value}"


def plugin(effect, value):
    return kwriteconfig("kwinrc", "Plugins", f"{effect}Enabled", value)


def animations_log(tmp_path, settings):
    saved = tmp_path / "setup.conf"
    saved.write_text(settings)
    return dry_run_log(tmp_path, f"--settings={saved}", "--components=animations")


def written(log, lines):
    return {line: line in log for line in lines}


def test_minimize_with_magic_lamp_turns_it_on_and_the_events_other_effects_off(tmp_path):
    log = animations_log(tmp_path, "ANIM_MINIMIZE=magiclamp\n")
    lines = (
        plugin("magiclamp", "true"),
        plugin("squash", "false"),
        plugin("chicago95zoom", "false"),
        kwriteconfig("kwinrc", "Effect-chicago95zoom", "Minimize", "false"),
    )

    assert written(log, lines) == dict.fromkeys(lines, True)


def test_title_bar_zoom_for_minimize_only_keeps_the_zoom_effect_on_and_tells_it_which_events(tmp_path):
    log = animations_log(tmp_path, "ANIM_MINIMIZE=zoom\nANIM_MAXIMIZE=stretch\n")
    lines = (
        plugin("chicago95zoom", "true"),
        kwriteconfig("kwinrc", "Effect-chicago95zoom", "Minimize", "true"),
        kwriteconfig("kwinrc", "Effect-chicago95zoom", "Maximize", "false"),
        plugin("maximize", "true"),
        plugin("fullscreen", "true"),
        plugin("squash", "false"),
    )

    assert (written(log, lines), plugin("chicago95zoom", "false") in log) == (dict.fromkeys(lines, True), False)


def test_an_installed_effect_of_the_events_category_is_a_choice_and_turns_the_others_off(tmp_path):
    fire = tmp_path / ".local/share/kwin/effects/kwin6_effect_fire"
    fire.mkdir(parents=True)
    (fire / "metadata.json").write_text(
        '{"KPlugin": {"Id": "kwin6_effect_fire"}, "X-KWin-Exclusive-Category": "toplevel-open-close-animation"}'
    )
    log = animations_log(tmp_path, "ANIM_WINDOWS=kwin6_effect_fire\n")
    lines = (
        plugin("kwin6_effect_fire", "true"),
        plugin("scale", "false"),
        plugin("glide", "false"),
        plugin("fade", "false"),
    )

    assert written(log, lines) == dict.fromkeys(lines, True)


def test_events_without_a_saved_choice_are_left_as_kde_has_them(tmp_path):
    log = animations_log(tmp_path, "ANIM_MINIMIZE=squash\n")

    assert [
        effect for effect in ("scale", "slide", "slidingpopups", "wobblywindows") if f" {effect}Enabled " in log
    ] == []


def test_speed_off_makes_every_animation_instant(tmp_path):
    assert kwriteconfig("kdeglobals", "KDE", "AnimationDurationFactor", "0") in animations_log(
        tmp_path, "ANIM_SPEED=0\n"
    )


def test_our_own_menus_and_notifications_read_their_choice_from_chicago95rc(tmp_path):
    log = animations_log(tmp_path, "ANIM_MENUS=fade\nANIM_NOTIFICATIONS=none\n")
    lines = (
        kwriteconfig("chicago95rc", "Animations", "ANIM_MENUS", "fade"),
        kwriteconfig("chicago95rc", "Animations", "ANIM_NOTIFICATIONS", "none"),
        plugin("fadingpopups", "true"),
        plugin("slidingpopups", "false"),
        plugin("chicago95notifications", "false"),
    )

    assert written(log, lines) == dict.fromkeys(lines, True)


def test_a_saved_classic_effects_yes_turns_every_animation_off(tmp_path):
    log = animations_log(tmp_path, "CLASSIC_EFFECTS=yes\n")
    lines = (
        kwriteconfig("kdeglobals", "KDE", "AnimationDurationFactor", "0"),
        plugin("scale", "false"),
        plugin("squash", "false"),
        plugin("wobblywindows", "false"),
        plugin("slidingpopups", "false"),
    )

    assert written(log, lines) == dict.fromkeys(lines, True)


def test_animations_alone_reload_kwin_without_restarting_plasma_or_clearing_its_caches(tmp_path):
    log = animations_log(tmp_path, "ANIM_MINIMIZE=squash\n")

    assert ("org.kde.KWin.reconfigure" in log, "qmlcache" in log) == (True, False)


def test_the_animations_step_installs_the_title_bar_zoom_effect(tmp_path):
    log = animations_log(tmp_path, "ANIM_MINIMIZE=zoom\n")

    assert "kwin/effects/chicago95zoom" in log


def test_taskbar_buttons_without_animation_are_written_to_each_task_list(tmp_path):
    script = squeezed(taskbar_script_written(tmp_path, "SETUP_ANIM_TASKBAR=none"))

    assert "widget.writeConfig('animateButtons', false);" in script


def test_animations_are_left_alone_when_no_choice_was_saved(tmp_path):
    assert "AnimationDurationFactor" not in dry_run_log(tmp_path, "--components=look")


def test_uninstall_deletes_the_animation_settings_setup_wrote(tmp_path):
    state = tmp_path / ".local/share/chicago95"
    state.mkdir(parents=True)
    (state / "installed-files.txt").write_text(
        "kconf:kdeglobals:KDE:AnimationDurationFactor\nkconf:kwinrc:Plugins:kwin6_effect_fireEnabled\n"
        "kconf:kwinrc:Effect-chicago95zoom:Minimize\nkconf:chicago95rc:Animations:ANIM_MENUS\n"
    )
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    (stubs / "kwriteconfig6").write_text(f'#!/bin/sh\necho "$@" >> {tmp_path}/kwriteconfig6-calls\n')
    (stubs / "kwriteconfig6").chmod(0o755)

    subprocess.run(
        [str(REPO / "uninstall.sh")],
        capture_output=True,
        text=True,
        timeout=30,
        stdin=subprocess.DEVNULL,
        env={"PATH": f"{stubs}:/usr/bin:/bin", "HOME": str(tmp_path)},
        check=False,
    )

    assert sorted((tmp_path / "kwriteconfig6-calls").read_text().splitlines()) == [
        "--file chicago95rc --group Animations --key ANIM_MENUS --delete",
        "--file kdeglobals --group KDE --key AnimationDurationFactor --delete",
        "--file kwinrc --group Effect-chicago95zoom --key Minimize --delete",
        "--file kwinrc --group Plugins --key kwin6_effect_fireEnabled --delete",
    ]


def test_taskbar_height_36_is_written_to_the_panel_that_holds_the_task_list(tmp_path):
    written = squeezed(taskbar_script_written(tmp_path, "SETUP_PANEL=36"))

    assert "if (panel.widgets('org.chicago95.tasks').length > 0) panel.height = 36;" in written


def test_taskbar_height_is_left_alone_when_none_was_chosen(tmp_path):
    assert "panel.height" not in taskbar_script_written(tmp_path)


def test_taskbar_height_keeps_only_its_digits(tmp_path):
    written = squeezed(taskbar_script_written(tmp_path, "SETUP_PANEL='3); evil(6'"))

    assert ("panel.height = 36;" in written, "evil" in written) == (True, False)


def test_winamp_rule_drops_the_frame_of_the_skinned_player_only(tmp_path):
    """The skinned player draws its own frame; qmmp's visualizer windows (Goom, ProjectM) do not and keep KWin's."""
    import re

    script = (
        f'REPO={REPO}; source {REPO}/setup/steps.sh; kwin_rule() {{ printf "%s\\n" "$@"; }}; '
        f"put_file() {{ :; }}; run() {{ :; }}; "
        'SETUP_HAS_QMMP=1 SETUP_CHICAGO95_SRC="" step_winamp'
    )
    rule = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
        check=False,
    ).stdout.splitlines()
    settings = dict(line.split("=", 1) for line in rule[1:])
    pattern = re.compile(settings["wmclass"], re.I)

    assert (settings["wmclasscomplete"], settings["wmclassmatch"], settings["noborder"]) == ("true", "3", "true")
    assert [bool(pattern.search(window)) for window in ("player Qmmp", "qmmp qmmp")] == [True, False]


def test_dry_run_of_the_control_panel_component_installs_the_tool_the_password_prompt_and_the_menu_entry(tmp_path):
    log = dry_run_log(tmp_path, "--components=controlpanel")

    assert [
        line in log
        for line in (
            f"would: cp {REPO}/bin/chicago95-control-panel {tmp_path}/.local/bin/chicago95-control-panel",
            f"would: cp {REPO}/bin/chicago95-askpass {tmp_path}/.local/bin/chicago95-askpass",
            f"would: cp {REPO}/config/applications/chicago95-control-panel.desktop "
            f"{tmp_path}/.local/share/applications/chicago95-control-panel.desktop",
            f"would: chmod +x {tmp_path}/.local/bin/chicago95-control-panel",
        )
    ] == [True] * 4


def test_control_panel_desktop_entry_is_a_settings_program_that_starts_the_installed_tool():
    entry = dict(
        line.split("=", 1)
        for line in (REPO / "config/applications/chicago95-control-panel.desktop").read_text().splitlines()
        if "=" in line
    )

    assert (entry["Name"], entry["Exec"], entry["Categories"]) == (
        "Control Panel",
        "@HOME@/.local/bin/chicago95-control-panel",
        "Settings;",
    )


@pytest.mark.parametrize("applet", ["start", "tasks"])
def test_taskbar_applets_offer_a_properties_action_that_opens_the_control_panels_taskbar_page(applet):
    main_qml = (REPO / f"plasmoids/org.chicago95.{applet}/contents/ui/main.qml").read_text()

    assert (
        "Plasmoid.contextualActions" in main_qml,
        "@HOME@/.local/bin/chicago95-control-panel --page taskbar" in main_qml,
    ) == (True, True)


def test_setup_replaces_home_in_the_tasks_applet_as_it_does_in_the_start_applet():
    step_taskbar = (REPO / "setup/steps.sh").read_text().split("step_taskbar() {")[1].split("\n}\n")[0]

    assert "~/.local/share/plasma/plasmoids/org.chicago95.tasks" in next(
        line for line in step_taskbar.splitlines() if "substitute_home" in line
    )


def test_clippy_window_rule_keeps_it_above_other_windows_by_default(tmp_path):
    run_setup(tmp_path, "--components=clippy")
    rules = (tmp_path / ".config/kwinrulesrc").read_text()
    clippy = rules.split("[chicago95-clippy]")[1].split("\n[")[0]

    assert ("above=true" in clippy, "aboverule=2" in clippy) == (True, True)


def finish_session_calls(tmp_path, shell_changed):
    calls = tmp_path / "calls"
    calls.touch()
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    (stubs / "systemctl").write_text(f'#!/bin/sh\necho "systemctl $*" >> {calls}\n')
    (stubs / "gdbus").write_text("#!/bin/sh\n")
    for stub in stubs.iterdir():
        stub.chmod(0o755)
    script = (
        f"REPO={REPO}; source {REPO}/setup/steps.sh; SETUP_LOG={tmp_path}/log; "
        f"SHELL_CHANGED={shell_changed} SETUP_IN_PLASMA=1 SETUP_DRY_RUN=0 finish_session"
    )
    subprocess.run(
        ["bash", "-c", script], timeout=30, env={"PATH": f"{stubs}:/usr/bin:/bin", "HOME": str(tmp_path)}, check=False
    )
    return calls.read_text().splitlines()


def test_finishing_after_a_shell_change_restarts_plasma_with_one_queued_job_after_everything_else(tmp_path):
    """Setup may run inside plasmashell's own service (from the Control Panel, opened from the taskbar):
    stopping plasmashell would stop Setup before it starts plasmashell again, leaving no desktop. One
    restart job, queued last and not waited for, is finished by systemd whatever happens to Setup."""
    calls = finish_session_calls(tmp_path, shell_changed=1)
    plasma = [line for line in calls if "plasmashell" in line]

    assert (plasma, calls[-1]) == (["systemctl --user restart --no-block plasma-plasmashell.service"], plasma[0])


def test_finishing_without_a_shell_change_leaves_plasma_running(tmp_path):
    calls = finish_session_calls(tmp_path, shell_changed=0)

    assert [line for line in calls if "plasmashell" in line] == []


def test_detecting_without_a_display_starts_no_graphical_program_that_would_crash(tmp_path):
    """plasmashell --version and kscreen-doctor abort without a display (CI, a headless test): each abort
    is a crash report, which DrKonqi then raises in the user's session. Detection still finds Plasma."""
    calls = tmp_path / "calls"
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for program in ("plasmashell", "kscreen-doctor"):
        (stubs / program).write_text(
            f'#!/bin/sh\necho "{program} QT_QPA_PLATFORM=$QT_QPA_PLATFORM $*" >> {calls}\necho "{program} 6.8.2"\n'
        )
        (stubs / program).chmod(0o755)
    script = f'source {REPO}/setup/detect.sh; detect_plasma; detect_screen; echo "version=$SETUP_PLASMA_VERSION"'
    output = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": f"{stubs}:/usr/bin:/bin", "HOME": str(tmp_path)},
        check=False,
    ).stdout
    started = calls.read_text().splitlines() if calls.exists() else []

    assert "version=6.8.2" in output
    assert started == ["plasmashell QT_QPA_PLATFORM=offscreen --version"], started


def plymouth_stub(home, current="bgrt"):
    stubs = home / "stubs"
    stubs.mkdir(exist_ok=True)
    (stubs / "plymouth-set-default-theme").write_text(f"#!/bin/sh\necho {current}\n")
    (stubs / "plymouth-set-default-theme").chmod(0o755)


def test_dry_run_of_the_2000_boot_screen_renders_our_loading_screen_into_a_plymouth_theme_of_its_own(tmp_path):
    """The 2000 look's boot screen is not Chicago95's 95 animation: Setup draws the 2000 loading screen at the
    monitor's size, puts it under plymouth/Chicago95-2000's progress blocks and makes that the boot theme."""
    plymouth_stub(tmp_path)
    run_setup(tmp_path, "--dry-run", "--login-style=2000", "--screen=1280x1024@1", "--components=plymouth")
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()
    assert (
        f"would: env QT_QPA_PLATFORM=offscreen python3 {REPO}/bin/chicago95-splash-image --splash" in log,
        "--size 1280x1024 --scale 1 --out" in log,
        "/usr/share/plymouth/themes/Chicago95-2000" in log,
        "would: sudo plymouth-set-default-theme -R Chicago95-2000" in log,
    ) == (True, True, True, True)


@pytest.mark.parametrize(
    "assignments, style",
    [("SETUP_BOOT_STYLE=2000 SETUP_LOGIN_STYLE=classic", "2000"), ("SETUP_LOGIN_STYLE=2000", "2000"), ("", "classic")],
)
def test_the_boot_style_is_its_own_setting_and_follows_the_login_style_until_set(tmp_path, assignments, style):
    assert run_bash_with_steps(tmp_path, f"{assignments} boot_style") == [style]


def test_dry_run_of_a_2000_boot_screen_with_a_classic_login_still_builds_the_2000_plymouth_theme(tmp_path):
    plymouth_stub(tmp_path)
    run_setup(tmp_path, "--dry-run", "--login-style=classic", "--boot-style=2000", "--components=plymouth,splash")
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()
    assert (
        "would: sudo plymouth-set-default-theme -R Chicago95-2000" in log,
        "(loading screen: 2000, " in log,
    ) == (True, True)


def test_dry_run_of_a_classic_boot_screen_with_a_2000_login_keeps_chicago95s_own_plymouth_theme(tmp_path):
    plymouth_stub(tmp_path)
    (tmp_path / "src/Chicago95/Plymouth/Chicago95").mkdir(parents=True)
    run_setup(tmp_path, "--dry-run", "--login-style=2000", "--boot-style=classic", "--components=plymouth")
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()
    assert ("would: sudo plymouth-set-default-theme -R Chicago95\n" in log, "Chicago95-2000" in log) == (True, False)


def test_dry_run_of_the_classic_boot_screen_keeps_chicago95s_own_plymouth_theme(tmp_path):
    plymouth_stub(tmp_path)
    (tmp_path / "src/Chicago95/Plymouth/Chicago95").mkdir(parents=True)
    run_setup(tmp_path, "--dry-run", "--login-style=classic", "--components=plymouth")
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()
    assert ("would: sudo plymouth-set-default-theme -R Chicago95\n" in log, "Chicago95-2000" in log) == (True, False)


def test_splash_image_tool_draws_the_2000_loading_screen_at_the_size_asked(tmp_path):
    from PIL import Image

    splash = tmp_path / "splash"
    shutil.copytree(REPO / "splash/chicago95.splashscreen/contents/splash", splash)
    (splash / "settings.js").write_text(
        '.pragma library\nvar style = "2000"\nvar brandText = "Chicago 2000"\nvar brandLogo = ""\n'
        'var edition = "Professional"\nvar tagline = "Built on Linux Technology"\nvar company = "KDE"\n'
        'var companyLogo = ""\nvar loadingText = "Starting up..."\nvar footer = "Chicago95"\nvar picture = ""\n'
    )
    subprocess.run(
        [
            sys.executable,
            str(REPO / "bin/chicago95-splash-image"),
            "--splash",
            str(splash),
            "--size",
            "640x480",
            "--out",
            str(tmp_path / "screen.png"),
        ],
        check=True,
        capture_output=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        timeout=60,
    )
    image = Image.open(tmp_path / "screen.png").convert("RGB")
    assert (image.size, image.getpixel((10, 10)), image.getpixel((320, 420))) == (
        (640, 480),
        (247, 247, 247),
        (0, 37, 160),
    )


def test_the_2000_plymouth_script_places_the_originals_18_blocks_in_the_640_by_480_layout():
    script = (REPO / "plymouth/Chicago95-2000/Chicago95-2000.script").read_text()
    assert (
        "SetBootProgressFunction" in script,
        'Image("screen.png")' in script,
        "(274 + 9 * i) * unit" in script,
        "437 * unit" in script,
        "unit = screen_height / 480" in script,
        "i < 18" in script,
    ) == (True, True, True, True, True, True)


def test_saved_settings_record_the_installed_commit_for_the_update_check(tmp_path):
    head = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    ).stdout.strip()
    saved = run_bash_with_steps(
        tmp_path,
        f"SETUP_DRY_RUN=0; MANIFEST={tmp_path}/manifest; STATE_DIR={tmp_path}; save_settings; "
        f"grep ^COMMIT= {tmp_path}/.config/chicago95/setup.conf",
    )

    assert saved == [f"COMMIT={head}"]


def setup_log(home):
    return next(home.glob("chicago95-setup-*.log")).read_text()


def test_a_second_run_takes_the_previous_runs_choices_as_its_defaults(tmp_path):
    run_setup(tmp_path, "--components=sounds", "--sounds=Windows98", "--look=2000", "--start-text=Go", "--panel=32")

    run_setup(tmp_path, "--components=sounds")

    assert {key: read_saved_settings(tmp_path).get(key) for key in ("SOUND_THEME", "LOOK", "START_TEXT", "PANEL")} == {
        "SOUND_THEME": "Windows98",
        "LOOK": "2000",
        "START_TEXT": "Go",
        "PANEL": "32",
    }


def test_a_flag_still_wins_over_the_remembered_choice(tmp_path):
    run_setup(tmp_path, "--components=sounds", "--sounds=Windows98")

    run_setup(tmp_path, "--components=sounds", "--sounds=Windows2000")

    assert read_saved_settings(tmp_path)["SOUND_THEME"] == "Windows2000"


def test_the_components_of_earlier_runs_are_remembered_and_picked_again_by_default(tmp_path):
    run_setup(tmp_path, "--components=sounds,background")
    run_setup(tmp_path, "--components=lockscreen")
    for log in tmp_path.glob("chicago95-setup-*.log"):
        log.unlink()

    run_setup(tmp_path, "--dry-run")

    picked = next(line for line in setup_log(tmp_path).splitlines() if line.startswith("Components: ")).split()[1:]

    assert (read_saved_settings(tmp_path)["COMPONENTS"], picked) == (
        "sounds background lockscreen",
        ["sounds", "background", "lockscreen"],
    )


def test_the_look_greys_toolbar_icons_until_the_pointer_is_over_them_in_every_kde_program(tmp_path):
    """KIconLoader's effects, which the Plasma platform theme applies to every Qt program's themed icons."""
    log = dry_run_log(tmp_path, "--components=look")

    assert [
        f"would: kwriteconfig6 --file kdeglobals --group {group} --key {key} {value}" in log
        for group in ("MainToolbarIcons", "ToolbarIcons")
        for key, value in (("DefaultEffect", "togray"), ("DefaultValue", "1"), ("ActiveEffect", "none"))
    ] == [True] * 6


def test_the_base_theme_greys_gtk_toolbar_icons_until_the_pointer_is_over_them(tmp_path):
    log = dry_run_log(tmp_path, "--components=base")

    assert [
        f"{REPO}/config/gtk-toolbar-icons-gtk3.css" in log and f"{tmp_path}/.config/gtk-3.0/gtk.css" in log,
        f"{REPO}/config/gtk-toolbar-icons.css" in log and f"{tmp_path}/.config/gtk-4.0/gtk.css" in log,
    ] == [True, True]


def test_the_gtk_toolbar_icon_rule_is_appended_once_however_often_setup_runs(tmp_path):
    run_setup(tmp_path, "--components=base")
    run_setup(tmp_path, "--components=base")

    assert [
        (tmp_path / ".config/gtk-3.0/gtk.css").read_text().count("-gtk-icon-effect: dim"),
        (tmp_path / ".config/gtk-4.0/gtk.css").read_text().count("-gtk-icon-filter: grayscale(1)"),
    ] == [1, 1]


def test_the_tools_get_the_animations_library_and_its_table_beside_it(tmp_path):
    log = dry_run_log(tmp_path, "--components=controlpanel")

    assert (
        ".local/lib/chicago95/chicago95animations.py" in log,
        ".local/lib/chicago95/animations.conf" in log,
    ) == (True, True)


def test_reinstalling_notifications_keeps_their_motion_off_when_the_effects_tab_turned_it_off(tmp_path):
    saved = tmp_path / "setup.conf"
    saved.write_text("ANIM_NOTIFICATIONS=none\n")

    log = dry_run_log(tmp_path, f"--settings={saved}", "--components=notifications")

    assert plugin("chicago95notifications", "true") not in log


def test_the_control_panel_gets_the_screensaver_pictures_for_its_monitor(tmp_path):
    assert ".local/share/chicago95/screensaver-previews" in dry_run_log(tmp_path, "--components=controlpanel")


POINTER = "would: kwriteconfig6 --file kcminputrc --group Libinput --group 5426 --group 148 --group Razer Orochi V2"


def test_dry_run_of_the_mouse_component_sets_the_double_click_time_and_each_pointers_hand_and_speed(tmp_path):
    (tmp_path / ".config").mkdir()
    (tmp_path / ".config/kcminputrc").write_text(
        "[Libinput][5426][148][Razer Orochi V2]\nNaturalScroll=true\n\n[Mouse]\ncursorSize=48\n"
    )
    settings = tmp_path / "chosen.conf"
    settings.write_text("MOUSE_HAND=left\nDOUBLE_CLICK_MS=300\nPOINTER_SPEED=0.4\n")
    log = dry_run_log(tmp_path, "--components=mouse", f"--settings={settings}")

    assert [
        "would: kwriteconfig6 --file kdeglobals --group KDE --key DoubleClickInterval 300" in log,
        f"{POINTER} --key LeftHanded true" in log,
        f"{POINTER} --key PointerAcceleration 0.4" in log,
    ] == [True, True, True]


def test_the_session_environment_makes_firefox_take_the_window_managers_title_bar():
    environment = (REPO / "config/environment.d/chicago95.conf").read_text()

    assert "MOZ_GTK_TITLEBAR_DECORATION=system" in environment.splitlines()


def test_a_dry_run_of_any_tool_installs_the_session_environment(tmp_path):
    log = dry_run_log(tmp_path, "--components=controlpanel")

    assert "config/environment.d/chicago95.conf" in log and ".config/environment.d/chicago95.conf" in log


def test_the_look_paints_gtk_drawn_title_bars_in_its_active_and_inactive_colours(tmp_path):
    (tmp_path / ".config/gtk-3.0").mkdir(parents=True)
    (tmp_path / ".config/gtk-3.0/gtk.css").write_text("@import 'colors.css';\n")
    for _ in range(2):
        run_bash_with_steps(
            tmp_path,
            f"SETUP_DRY_RUN=0; MANIFEST={tmp_path}/manifest; STATE_DIR={tmp_path}; "
            'write_gtk_titlebar_css "#0A246A,#A6CAF0" "#808080,#C0C0C0" "rgb(212,208,200)"',
        )
    gtk3 = (tmp_path / ".config/gtk-3.0/gtk.css").read_text()
    gtk4 = (tmp_path / ".config/gtk-4.0/gtk.css").read_text()

    assert (
        gtk3.count("Chicago95 title bars BEGIN"),
        gtk3.startswith("@import 'colors.css';\n"),
        "linear-gradient(to right, #0A246A, #A6CAF0); background-color: #0A246A; color: #FFFFFF; font-weight: bold"
        in gtk3,
        "linear-gradient(to right, #808080, #C0C0C0); background-color: #808080; color: rgb(212,208,200)" in gtk3,
        "headerbar.titlebar:backdrop" in gtk4,
    ) == (1, True, True, True, True)


def test_a_dry_run_of_the_look_announces_the_gtk_title_bar_colours(tmp_path):
    log = dry_run_log(tmp_path, "--components=look", "--look=1995")

    assert "would: write the title bar colours into" in log


def test_reinstall_with_the_saved_start_logo_pointing_at_the_installed_logo_exits_0_and_keeps_the_logo(tmp_path):
    installed_logo = tmp_path / ".local/share/chicago95/start-logo.png"
    installed_logo.parent.mkdir(parents=True)
    installed_logo.write_bytes(b"saved logo")
    saved = tmp_path / "setup.conf"
    saved.write_text(f"START_LOGO={installed_logo}\n")

    result = run_setup(tmp_path, "--components=startmenu", f"--settings={saved}")

    assert (result.returncode, installed_logo.read_bytes()) == (0, b"saved logo")


def test_mouse_alone_reloads_kwin_without_clearing_plasma_caches(tmp_path):
    log = dry_run_log(tmp_path, "--components=mouse")

    assert ("org.kde.KWin.reconfigure" in log, "qmlcache" in log) == (True, False)


def test_taskbar_clears_plasma_caches_for_the_new_applets(tmp_path):
    assert "qmlcache" in dry_run_log(tmp_path, "--components=taskbar")


def install_shell_files(home):
    shared = home / ".local/share/chicago95"
    shared.mkdir(parents=True)
    shutil.copy(REPO / "data/plasmashell-menus.qss", shared / "plasmashell-menus.qss")
    shutil.copytree(REPO / "data/qml", shared / "qml")
    drop_in = home / ".config/systemd/user/plasma-plasmashell.service.d"
    drop_in.mkdir(parents=True)
    shutil.copy(
        REPO / "config/systemd/plasma-plasmashell.service.d-chicago95-menus.conf", drop_in / "chicago95-menus.conf"
    )


def test_screensaver_with_the_shell_files_already_installed_leaves_plasma_caches(tmp_path):
    install_shell_files(tmp_path)

    assert "qmlcache" not in dry_run_log(tmp_path, "--components=screensaver")


def test_screensaver_with_a_new_menu_style_sheet_clears_plasma_caches(tmp_path):
    install_shell_files(tmp_path)
    (tmp_path / ".local/share/chicago95/plasmashell-menus.qss").write_text("QMenu {}\n")

    assert "qmlcache" in dry_run_log(tmp_path, "--components=screensaver")
