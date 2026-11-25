#!/usr/bin/env python3
"""What a changed choice of setup.conf needs, and the Control Panel's Apply that sets it: the appliers that set each
choice, in the order Setup runs them. An applier sets values and reloads what shows them; it never copies a
component again. Most are lib/chicago95appliers.py's; the rest (BASH_APPLIERS) are setup/steps.sh's applier_<name>,
run through install.sh --apply.

    chicago95apply.py --settings=FILE --changed=KEY,KEY [--dry-run]       the Control Panel's Apply
    chicago95apply.py --environment --appliers=NAME,NAME [--report=FILE]  setup/steps.sh's python_applier

Standard library only: Setup runs it on machines without PySide6.
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chicago95appliers import APPLIERS, finish, start_menu_restart, taskbar  # noqa: E402
from chicago95setup import REPO, Choices, Setup, read_key_values, resolve_choices  # noqa: E402

# The administrator's password is asked last: refusing it loses nothing else.
APPLY_ORDER = (
    "look",
    "widgets",
    "colors",
    "decoration",
    "plasma_style",
    "icons",
    "title_colors",
    "gtk_title_bars",
    "fonts",
    "look_rc",
    "live_blur",
    "animations",
    "aero_blur",
    "pointer",
    "mouse",
    "start_logo",
    "start_menu",
    "branding",
    "window_rules",
    "shortcuts",
    "switcher",
    "explorer",
    "explorer_style",
    "sounds",
    "screensaver",
    "clippy_autostart",
    "background",
    "desktop_icons",
    "lockscreen",
    "lockscreen_settings",
    "splash",
    "splash_settings",
    "panel",
    "plymouth_look",
    "plymouth",
    "sddm_look",
    "sddm",
)

ANIMATION_KEYS = (
    "ANIM_WINDOWS",
    "ANIM_MINIMIZE",
    "ANIM_MAXIMIZE",
    "ANIM_DIALOGS",
    "ANIM_WOBBLY",
    "ANIM_SHOW_DESKTOP",
    "ANIM_DESKTOPS",
    "ANIM_SESSION",
    "ANIM_MENUS",
    "ANIM_NOTIFICATIONS",
    "ANIM_TASKBAR",
    "ANIM_SPEED",
)
# The names and logos the login, loading, boot and Shut Down screens show.
BRAND_KEYS = ("BANNER_TEXT", "START_LOGO", "LOGIN_LOGO", "EDITION", "COMPANY", "TAGLINE", "COMPANY_LOGO")
# The loading screen's own picture and texts: the 2000 and later boot screens are pictures of it.
LOADING_KEYS = ("SPLASH_IMAGE", "LOADING_TEXT", "LOADING_FOOTER")
POST_XP_KEYS = (
    "BOOT_LOGO",
    "BOOT_NAME",
    "BOOT_TEXT",
    "BOOT_FOOTER",
    "BOOT_BACKGROUND",
    "BOOT_FOREGROUND",
    "BOOT_ACCENT",
    "BOOT_FONT",
    "BOOT_BACKGROUND_IMAGE",
    "BOOT_ANIMATION",
    "BOOT_FRAMES",
    "BOOT_LOOP_START",
    "BOOT_FPS",
    "BOOT_LOGO_SIZE",
)
POST_XP_BOOT_STYLES = ("vista", "7", "8", "8.1", "10", "11")

# setup/steps.sh's applier_<name>: the look's files and themes, icon packs, fonts, the file manager, and the screens
# that are installed whole or need the administrator's password.
BASH_APPLIERS = (
    "look",
    "widgets",
    "decoration",
    "plasma_style",
    "icons",
    "gtk_title_bars",
    "fonts",
    "live_blur",
    "aero_blur",
    "explorer",
    "explorer_style",
    "lockscreen",
    "splash",
    "plymouth_look",
    "plymouth",
    "sddm_look",
    "sddm",
)
# The appliers that stand on the look's files: where the look was never installed, "look" installs it whole first.
LOOK_APPLIERS = ("widgets", "colors", "decoration", "plasma_style", "title_colors", "gtk_title_bars")

APPLIERS_BY_KEY = {
    "LOOK": ("colors", "title_colors", "animations", "switcher", "plymouth_look", "sddm_look"),
    "FACE": ("colors", "title_colors", "gtk_title_bars", "switcher"),
    "SELECTION": ("colors",),
    "DECORATION": ("decoration", "title_colors", "gtk_title_bars", "fonts", "look_rc", "window_rules"),
    "WIDGET_STYLE": ("widgets", "colors", "title_colors", "fonts", "look_rc", "window_rules", "explorer_style"),
    "CONTROL_PANEL_STYLE": ("look_rc",),
    "BEVEL": ("icons", "title_colors", "gtk_title_bars", "look_rc", "panel"),
    "TASKBAR_STYLE": ("plasma_style", "fonts", "look_rc", "window_rules", "panel"),
    "START_MENU_STYLE": ("look_rc", "start_menu", "window_rules", "switcher", "desktop_icons", "panel"),
    "TITLE_ACTIVE": ("title_colors", "gtk_title_bars"),
    "TITLE_INACTIVE": ("title_colors", "gtk_title_bars"),
    "ICONS": ("icons",),
    "FONT": ("fonts",),
    "FONT_SCOPE": ("fonts",),
    **{key: ("animations",) for key in ANIMATION_KEYS},
    "ANIM_WOBBLY": ("live_blur", "animations", "aero_blur"),
    "ANIM_MENUS": ("animations", "start_menu"),
    "ANIM_TASKBAR": ("animations", "panel"),
    "BANNER_BG": ("start_menu",),
    "BANNER_FG": ("start_menu",),
    "CURSOR": ("pointer",),
    "MOUSE_HAND": ("mouse",),
    "DOUBLE_CLICK_MS": ("mouse",),
    "POINTER_SPEED": ("mouse",),
    "PANEL": ("window_rules", "panel"),
    "TASK_BUTTON_WIDTH": ("panel",),
    "QUICK_LAUNCH": ("panel",),
    "TASK_GROUPING": ("panel",),
    "LAUNCHERS": ("panel",),
    "TASKBAR_AUTOHIDE": ("panel",),
    "TASKBAR_ON_TOP": ("panel",),
    "CLOCK_SHOW": ("panel",),
    "CLOCK_HOURS": ("panel",),
    "START_TEXT": ("panel",),
    "PREVIEW_SIZE": ("switcher", "panel"),
    "SAVER": ("screensaver",),
    "IDLE_MIN": ("screensaver",),
    "LOGIN_STYLE": ("branding", "lockscreen", "splash", "sddm"),
    "LOGIN_TITLE": ("sddm",),
    "LOGIN_MESSAGE": ("sddm",),
    "LOGIN_ICON": ("sddm",),
    **{key: ("branding", "splash_settings") for key in BRAND_KEYS},
    "BANNER_TEXT": ("start_menu", "branding", "splash_settings"),
    "START_LOGO": ("start_logo", "branding", "splash_settings", "panel"),
    "BRANDING": (),  # only which names the texts and logos came from: they apply themselves
    "BOOT_STYLE": ("splash", "plymouth"),
    **{key: ("splash_settings",) for key in LOADING_KEYS + POST_XP_KEYS},
    "SOUND_THEME": ("sounds",),
    "CLIPPY_AUTOSTART": ("clippy_autostart",),
    "EXPLORER": ("shortcuts", "explorer", "desktop_icons"),
    "BACKGROUND_MODE": ("background",),
    "BACKGROUND_COLOR": ("background", "lockscreen_settings", "splash_settings"),
    "BACKGROUND_PATTERN": ("background",),
    "BACKGROUND_IMAGE": ("background",),
    "BACKGROUND_FILL": ("background",),
    "DESKTOP_ICONS": ("desktop_icons",),
}


def read_settings(path):
    return read_key_values(path) if Path(path).exists() else {}


def screen_appliers(key, settings):
    """The appliers of the login, lock and boot screens a key reaches only under the styles that show it."""
    login_style = settings.get("LOGIN_STYLE") or "classic"
    boot_style = settings.get("BOOT_STYLE") or login_style
    if key == "LOGIN_STYLE" and not settings.get("BOOT_STYLE"):
        return ("plymouth",)
    if key in BRAND_KEYS:
        return (
            *(("lockscreen",) if login_style in ("2000", "aero") else ()),
            *(("sddm",) if login_style != "classic" else ()),
            *(("plymouth",) if boot_style != "classic" else ()),
        )
    if key in LOADING_KEYS and boot_style in ("2000", *POST_XP_BOOT_STYLES):
        return ("plymouth",)
    if key in POST_XP_KEYS and boot_style in POST_XP_BOOT_STYLES:
        return ("plymouth",)
    return ()


def appliers_for(changed_keys, settings):
    needed = {
        applier for key in changed_keys for applier in (*APPLIERS_BY_KEY.get(key, ()), *screen_appliers(key, settings))
    }
    # A screen copied whole writes its settings too.
    needed -= {f"{screen}_settings" for screen in ("lockscreen", "splash") if screen in needed}
    if needed & set(LOOK_APPLIERS):
        needed.add("look")
    return [applier for applier in APPLY_ORDER if applier in needed]


def setup_command(repo, settings_path, appliers):
    return [f"{repo}/install.sh", "--plain", "--yes", f"--settings={settings_path}", f"--apply={','.join(appliers)}"]


def runs_of_one_language(appliers):
    """The appliers in order, as runs of Python ones and of setup/steps.sh's ones."""
    runs = []
    for applier in appliers:
        in_bash = applier in BASH_APPLIERS
        if runs and runs[-1][0] == in_bash:
            runs[-1][1].append(applier)
        else:
            runs.append((in_bash, [applier]))
    return runs


def apply_in_bash(setup, settings_path, appliers):
    """setup/steps.sh's appliers, through install.sh --apply; what they leave for the session comes back."""
    with tempfile.NamedTemporaryFile("r", prefix="chicago95-apply-", suffix=".report") as report:
        command = setup_command(setup.repo, settings_path, appliers) + (["--dry-run"] if setup.dry_run else [])
        environment = {**os.environ, **setup.flags, "SETUP_LOG": setup.log_path, "APPLY_REPORT": report.name}
        exit_code = subprocess.run(command, env=environment, check=False).returncode
        if exit_code:
            raise SystemExit(exit_code)
        for key, value in read_key_values(report.name).items():
            if key.startswith("SETUP_"):
                setup.choices[key.removeprefix("SETUP_")] = value
            elif key not in ("COPIED", "STATUS"):
                setup.flag(key, value)


def apply_changes(settings_path, changed_keys, dry_run):
    """The Control Panel's Apply: the appliers the changed choices need, then what the session needs reloaded."""
    appliers = appliers_for(changed_keys, read_settings(settings_path))
    if not appliers:
        return
    home = Path(os.environ.get("HOME", Path.home()))
    log = Path(os.environ.get("TMPDIR", "/tmp")) / time.strftime("chicago95-setup-%Y%m%d-%H%M%S.log")
    environment = {**os.environ, "SETUP_LOG": str(log), "SETUP_DRY_RUN": "1" if dry_run else "0", "UI_PLAIN": "1"}
    log.write_text(f"Apply: {','.join(changed_keys)} -> {','.join(appliers)}\n")
    setup = Setup(
        resolve_choices(settings_path, REPO, home, environment), repo=REPO, home=home, environment=environment
    )
    for in_bash, run in runs_of_one_language(appliers):
        if in_bash:
            apply_in_bash(setup, settings_path, run)
            continue
        for applier in run:
            if APPLIERS[applier](setup) is False:
                raise SystemExit(f"Could not apply {applier}; the Setup log has the details: {log}")
    finish(setup)
    # After the shell is back: the applets take their options from the one that is running.
    if setup.flags.get("TASKBAR_CHANGED") == "1":
        taskbar(setup)
    if setup.flags.get("START_MENU_CHANGED") == "1":
        start_menu_restart(setup)


def apply_for_setup(appliers, report):
    """setup/steps.sh's python_applier: the appliers with the run's SETUP_* values; flags back through the report."""
    environment = dict(os.environ)
    choices = Choices(
        {key.removeprefix("SETUP_"): value for key, value in environment.items() if key.startswith("SETUP_")}
    )
    setup = Setup(choices, repo=REPO, home=Path(environment["HOME"]), environment=environment, report=report)
    failed = [applier for applier in appliers if APPLIERS[applier](setup) is False]
    setup.write_report()
    return 1 if failed else 0


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--settings")
    parser.add_argument("--changed")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--environment", action="store_true")
    parser.add_argument("--appliers", default="")
    parser.add_argument("--report")
    options = parser.parse_args(arguments)
    if options.environment:
        return apply_for_setup([name for name in options.appliers.split(",") if name], options.report)
    if not (options.settings and options.changed):
        parser.error("--settings and --changed are needed")
    apply_changes(options.settings, options.changed.split(","), options.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
