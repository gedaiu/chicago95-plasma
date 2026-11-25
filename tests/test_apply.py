import subprocess

import chicago95apply
import pytest
from conftest import REPO, load_script

CONTROL_PANEL = load_script("chicago95-control-panel")


def test_changed_cursor_needs_the_pointer_applier_only():
    assert chicago95apply.appliers_for(["CURSOR"], {}) == ["pointer"]


def test_changed_start_text_needs_the_panel_applier_only():
    assert chicago95apply.appliers_for(["START_TEXT"], {}) == ["panel"]


def test_changed_title_colour_needs_the_title_colors_applier_only():
    assert chicago95apply.appliers_for(["TITLE_ACTIVE"], {}) == ["title_colors"]


def test_changed_sound_theme_and_saver_need_sounds_then_screensaver():
    assert chicago95apply.appliers_for(["SAVER", "SOUND_THEME"], {}) == ["sounds", "screensaver"]


def test_changed_branding_source_and_unknown_keys_need_no_applier():
    assert chicago95apply.appliers_for(["BRANDING", "REPO", "UNKNOWN"], {}) == []


def test_changed_panel_height_also_moves_the_windows_placed_above_the_taskbar():
    assert chicago95apply.appliers_for(["PANEL"], {}) == ["window_rules", "panel"]


def test_changed_edition_with_the_classic_login_and_boot_asks_for_no_administrator_password():
    assert chicago95apply.appliers_for(["EDITION"], {"LOGIN_STYLE": "classic"}) == ["branding", "splash_settings"]


def test_changed_edition_with_the_luna_login_reaches_the_login_and_boot_screens_last():
    assert chicago95apply.appliers_for(["EDITION"], {"LOGIN_STYLE": "luna"}) == [
        "branding",
        "splash_settings",
        "plymouth",
        "sddm",
    ]


def test_changed_edition_with_the_2000_login_redraws_the_lock_screen_banner():
    assert chicago95apply.appliers_for(["EDITION"], {"LOGIN_STYLE": "2000", "BOOT_STYLE": "classic"}) == [
        "branding",
        "lockscreen",
        "splash_settings",
        "sddm",
    ]


def test_changed_boot_text_rebuilds_the_boot_image_only_for_a_boot_style_that_shows_it():
    assert [
        chicago95apply.appliers_for(["BOOT_TEXT"], {"BOOT_STYLE": style}) for style in ("classic", "luna", "10")
    ] == [["splash_settings"], ["splash_settings"], ["splash_settings", "plymouth"]]


def test_changed_loading_text_rebuilds_the_2000_boot_image():
    assert chicago95apply.appliers_for(["LOADING_TEXT"], {"LOGIN_STYLE": "2000"}) == ["splash_settings", "plymouth"]


def test_changed_login_style_leaves_a_boot_style_chosen_on_its_own_alone():
    assert (
        "plymouth" in chicago95apply.appliers_for(["LOGIN_STYLE"], {"LOGIN_STYLE": "luna"}),
        "plymouth" in chicago95apply.appliers_for(["LOGIN_STYLE"], {"LOGIN_STYLE": "luna", "BOOT_STYLE": "7"}),
    ) == (True, False)


def test_every_saved_key_is_known_to_the_appliers_map_and_every_applier_is_a_function_of_setup():
    setup_keys = subprocess.run(
        ["bash", "-c", f"REPO={REPO}; source {REPO}/setup/steps.sh; echo $SETTINGS_KEYS; declare -F"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    functions = {line.split()[-1] for line in setup_keys[1:]}
    named = {applier for appliers in chicago95apply.APPLIERS_BY_KEY.values() for applier in appliers}

    assert (
        sorted(chicago95apply.APPLIERS_BY_KEY),
        named - set(chicago95apply.APPLY_ORDER),
        {applier for applier in chicago95apply.APPLY_ORDER if f"applier_{applier}" not in functions},
    ) == (sorted(setup_keys[0].split()), set(), set())


def test_setup_command_runs_install_sh_plain_yes_with_the_settings_and_the_appliers():
    assert chicago95apply.setup_command("/repo", "/home/setup.conf", ["pointer", "panel"]) == [
        "/repo/install.sh",
        "--plain",
        "--yes",
        "--settings=/home/setup.conf",
        "--apply=pointer,panel",
    ]


def test_apply_command_runs_the_repository_s_apply_module_with_the_changed_keys_in_its_own_scope(tmp_path):
    assert CONTROL_PANEL.apply_command("/repo", tmp_path / "setup.conf", ["CURSOR", "PANEL"]) == [
        *CONTROL_PANEL.OWN_SCOPE,
        "python3",
        "/repo/lib/chicago95apply.py",
        f"--settings={tmp_path / 'setup.conf'}",
        "--changed=CURSOR,PANEL",
    ]


def apply(home, changes, *arguments):
    settings_path = home / "setup.conf"
    settings_path.write_text("".join(f"{key}={value}\n" for key, value in {"REPO": REPO, **changes}.items()))
    result = subprocess.run(
        [
            "python3",
            str(REPO / "lib/chicago95apply.py"),
            f"--settings={settings_path}",
            f"--changed={','.join(changes)}",
            *arguments,
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        timeout=120,
        env={"PATH": "/usr/bin:/bin", "SETUP_OS_RELEASE": "/dev/null", "HOME": str(home), "TMPDIR": str(home)},
        check=False,
    )
    logs = sorted(home.glob("chicago95-setup-*.log"))
    return result, logs[-1].read_text() if logs else ""


def would_lines(log):
    return [line.strip() for line in log.splitlines() if line.startswith("  would:")]


def test_applying_double_click_400_in_a_dry_run_writes_the_interval_and_copies_nothing(tmp_path):
    result, log = apply(tmp_path, {"DOUBLE_CLICK_MS": "400"}, "--dry-run")

    assert (result.returncode, [line for line in log.splitlines() if "copy" in line], would_lines(log)[0]) == (
        0,
        [],
        "would: kwriteconfig6 --file kdeglobals --group KDE --key DoubleClickInterval 400",
    )


def test_applying_only_the_branding_source_runs_nothing_and_exits_0(tmp_path):
    result, log = apply(tmp_path, {"BRANDING": "distro"}, "--dry-run")

    assert (result.returncode, log) == (0, "")


STUBBED = (
    "systemctl",
    "gdbus",
    "kwriteconfig6",
    "plasma-apply-colorscheme",
    "plasma-apply-desktoptheme",
    "plasma-apply-cursortheme",
    "pkill",
    "pgrep",
    "gsettings",
    "sudo",
    "xrdb",
)


def apply_for_real(home, changes, saved=None, boot_theme=""):
    """Apply as the Control Panel runs it, in a home of its own: what would reach the session is recorded instead."""
    stubs = home / "stubs"
    stubs.mkdir(exist_ok=True)
    calls = home / "calls"
    calls.write_text("")
    (stubs / "plymouth-set-default-theme").write_text(f"#!/bin/sh\necho {boot_theme}\n")
    (stubs / "plymouth-set-default-theme").chmod(0o755)
    for command in STUBBED:
        (stubs / command).write_text(f"#!/bin/sh\nprintf '%s\\n' \"{command} $*\" >> {calls}\n")
        (stubs / command).chmod(0o755)
    (stubs / "plasmashell").write_text("#!/bin/sh\necho plasmashell 6.8.2\n")
    (stubs / "plasmashell").chmod(0o755)
    with (stubs / "pgrep").open("a") as nothing_runs:
        nothing_runs.write("exit 1\n")
    with (stubs / "sudo").open("a") as takes_what_is_piped_to_tee:
        takes_what_is_piped_to_tee.write('[ "$1" != tee ] || cat >/dev/null\n')
    settings_path = home / ".config/chicago95/setup.conf"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings = {**CONTROL_PANEL.read_settings(settings_path), "REPO": str(REPO), **(saved or {}), **changes}
    CONTROL_PANEL.write_settings(settings_path, settings)
    result = subprocess.run(
        [
            "python3",
            str(REPO / "lib/chicago95apply.py"),
            f"--settings={settings_path}",
            f"--changed={','.join(changes)}",
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        timeout=120,
        env={
            "PATH": f"{stubs}:/usr/bin:/bin",
            "SETUP_OS_RELEASE": "/dev/null",
            "HOME": str(home),
            "TMPDIR": str(home),
            "XDG_CURRENT_DESKTOP": "KDE",
        },
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return calls.read_text(), sorted(home.glob("chicago95-setup-*.log"))[-1].read_text()


def copied(log):
    return [line for line in log.splitlines() if line.startswith("copied:") and "(" not in line]


def test_applying_start_text_go_writes_it_to_the_running_taskbar_without_restarting_plasmashell_or_copying(tmp_path):
    calls, log = apply_for_real(tmp_path, {"START_TEXT": "Go"})

    assert (
        "widget.writeConfig('buttonText', \"Go\");" in calls,
        "plasma-plasmashell" in calls,
        copied(log),
    ) == (True, False, [])


def test_applying_cursor_48_sets_the_pointer_size_and_copies_nothing(tmp_path):
    calls, log = apply_for_real(tmp_path, {"CURSOR": "48"})

    assert (
        "plasma-apply-cursortheme Chicago95_Animated_Hourglass_Cursors_HiDPI --size 48" in calls,
        "plasma-plasmashell" in calls,
        copied(log),
    ) == (True, False, [])


def with_the_look_installed(home):
    (home / ".local/share/aurorae/themes/Chicago95").mkdir(parents=True)
    return home


def test_applying_title_colour_writes_the_window_colours_without_restarting_plasmashell(tmp_path):
    with_the_look_installed(tmp_path)
    calls, log = apply_for_real(tmp_path, {"TITLE_ACTIVE": "#0A246A,#A6CAF0"})

    assert (
        "kwriteconfig6 --file kdeglobals --group WM --key activeBackground 10,36,106" in calls,
        "kwriteconfig6 --file kdeglobals --group WM --key activeBlend 166,202,240" in calls,
        "plasma-plasmashell" in calls,
    ) == (True, True, False)


def test_applying_sound_theme_windows98_copies_that_theme_alone_and_a_second_time_nothing(tmp_path):
    calls, first = apply_for_real(tmp_path, {"SOUND_THEME": "Windows98"})
    installed = sorted(path.name for path in (tmp_path / ".local/share/sounds").iterdir())
    _, second = apply_for_real(tmp_path, {"SOUND_THEME": "Windows98"})

    assert (
        installed,
        "kwriteconfig6 --file kdeglobals --group Sounds --key Theme Windows98" in calls,
        copied(second),
    ) == (["Windows98"], True, [])


def test_applying_clippy_autostart_no_removes_the_entry_an_earlier_yes_installed(tmp_path):
    entry = tmp_path / ".config/autostart/chicago95-clippy.desktop"
    apply_for_real(tmp_path, {"CLIPPY_AUTOSTART": "yes"})
    installed = entry.exists()
    apply_for_real(tmp_path, {"CLIPPY_AUTOSTART": "no"})

    assert (installed, entry.exists()) == (True, False)


def run_dialog_top(home):
    rules = (home / ".config/kwinrulesrc").read_text()
    return int(rules.split("[chicago95-run]")[1].split("position=0,")[1].splitlines()[0])


def test_applying_panel_height_40_moves_the_run_dialog_12_pixels_up_from_a_28_pixel_taskbar(tmp_path):
    apply_for_real(tmp_path, {"PANEL": "28"})
    above_28 = run_dialog_top(tmp_path)
    apply_for_real(tmp_path, {"PANEL": "40"})

    assert above_28 - run_dialog_top(tmp_path) == 12


def test_applying_leaves_the_saved_settings_as_the_control_panel_wrote_them(tmp_path):
    settings_path = tmp_path / ".config/chicago95/setup.conf"
    apply_for_real(tmp_path, {"DOUBLE_CLICK_MS": "400"}, saved={"LOOK": "custom", "SAVER": "maze"})

    assert settings_path.read_text() == f"REPO={REPO}\nLOOK=custom\nSAVER=maze\nDOUBLE_CLICK_MS=400\n"


def test_install_sh_refuses_an_applier_it_does_not_know(tmp_path):
    result = subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--apply=nonsense"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=120,
        env={"PATH": "/usr/bin:/bin", "SETUP_OS_RELEASE": "/dev/null", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )

    assert (result.returncode, 'Apply does not know "nonsense".' in result.stdout) == (1, True)


@pytest.mark.parametrize(
    "boot_theme, remembered",
    [("bgrt", ["plymouth:bgrt"]), ("Chicago95-2000", [])],
)
def test_changing_the_boot_style_remembers_only_a_boot_theme_that_is_not_setup_s_own_for_uninstall(
    tmp_path, boot_theme, remembered
):
    apply_for_real(tmp_path, {"BOOT_STYLE": "luna"}, boot_theme=boot_theme)
    manifest = (tmp_path / ".local/share/chicago95/installed-files.txt").read_text().splitlines()

    assert [entry for entry in manifest if entry.startswith("plymouth:")] == remembered


@pytest.mark.parametrize("redrawn, restarts", [("new bevel", True), ("same bevel", False)])
def test_applying_a_title_colour_restarts_plasmashell_only_when_the_plasma_style_was_drawn_differently(
    tmp_path, redrawn, restarts
):
    panel = tmp_path / ".local/share/plasma/desktoptheme/Chicago95/widgets/panel-background.svg"
    panel.parent.mkdir(parents=True)
    panel.write_text("same bevel")
    sync_colors = tmp_path / ".local/bin/chicago95-sync-colors"
    sync_colors.parent.mkdir(parents=True)
    sync_colors.write_text(f"from pathlib import Path\nPath({str(panel)!r}).write_text({redrawn!r})\n")

    calls, _ = apply_for_real(with_the_look_installed(tmp_path), {"TITLE_ACTIVE": "#000080"})

    assert ("systemctl --user restart --no-block plasma-plasmashell.service" in calls) == restarts


def test_applying_start_text_keeps_the_start_button_on_setup_s_copy_of_an_own_logo(tmp_path):
    own_logo = tmp_path / "Pictures/own.png"
    own_logo.parent.mkdir()
    own_logo.write_bytes(b"png")
    apply_for_real(tmp_path, {"START_LOGO": str(own_logo)})
    calls, _ = apply_for_real(tmp_path, {"START_TEXT": "Go"})

    assert f"widget.writeConfig('logo', \"{tmp_path}/.local/share/chicago95/start-logo.png\");" in calls


def test_applying_classic_frames_where_the_look_was_never_installed_installs_the_look_once(tmp_path):
    _, log = apply_for_real(tmp_path, {"DECORATION": "classic", "TITLE_ACTIVE": "#000080"})
    decoration = tmp_path / ".local/share/aurorae/themes/Chicago95/decoration.svg"

    assert (decoration.exists(), log.count(f"copied: {REPO}/aurorae/theme/decoration.svg -> {decoration}\n")) == (
        True,
        1,
    )


def test_applying_the_classic_boot_style_of_1998_without_the_chicago95_checkout_skips_the_boot_screen(tmp_path):
    calls, _ = apply_for_real(tmp_path, {"BOOT_STYLE": "classic"}, saved={"LOOK": "1998"}, boot_theme="bgrt")

    assert "sudo plymouth-set-default-theme" not in calls
