#!/usr/bin/env python3
"""What a changed choice of setup.conf needs: the appliers of setup/steps.sh (applier_<name>) that set it, in the
order Setup runs them. An applier sets values and reloads what shows them; it never copies a component again.

    chicago95apply.py --settings=FILE --changed=KEY,KEY [--dry-run]

Standard library only: Setup runs it on machines without PySide6.
"""

import argparse
import os
import sys
from pathlib import Path

# The administrator's password is asked last: refusing it loses nothing else.
APPLY_ORDER = (
    "widgets",
    "colors",
    "decoration",
    "plasma_style",
    "icons",
    "title_colors",
    "fonts",
    "look_rc",
    "animations",
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

APPLIERS_BY_KEY = {
    "LOOK": ("colors", "title_colors", "animations", "switcher", "plymouth_look", "sddm_look"),
    "FACE": ("colors", "title_colors", "switcher"),
    "SELECTION": ("colors",),
    "DECORATION": ("decoration", "title_colors", "fonts", "look_rc", "window_rules"),
    "WIDGET_STYLE": ("widgets", "colors", "title_colors", "fonts", "look_rc", "window_rules", "explorer_style"),
    "CONTROL_PANEL_STYLE": ("look_rc",),
    "BEVEL": ("icons", "title_colors", "look_rc", "panel"),
    "TASKBAR_STYLE": ("plasma_style", "fonts", "look_rc", "window_rules", "panel"),
    "START_MENU_STYLE": ("look_rc", "start_menu", "window_rules", "switcher", "desktop_icons", "panel"),
    "TITLE_ACTIVE": ("title_colors",),
    "TITLE_INACTIVE": ("title_colors",),
    "ICONS": ("icons",),
    "FONT": ("fonts",),
    "FONT_SCOPE": ("fonts",),
    **{key: ("animations",) for key in ANIMATION_KEYS},
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
    if not Path(path).exists():
        return {}
    lines = [line for line in Path(path).read_text().splitlines() if "=" in line and not line.startswith("#")]
    return dict(line.split("=", 1) for line in lines)


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
    return [applier for applier in APPLY_ORDER if applier in needed]


def setup_command(repo, settings_path, appliers):
    return [f"{repo}/install.sh", "--plain", "--yes", f"--settings={settings_path}", f"--apply={','.join(appliers)}"]


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--settings", required=True)
    parser.add_argument("--changed", required=True)
    parser.add_argument("--dry-run", action="store_true")
    options = parser.parse_args(arguments)
    appliers = appliers_for(options.changed.split(","), read_settings(options.settings))
    if not appliers:
        return
    repo = Path(__file__).resolve().parent.parent
    command = setup_command(repo, options.settings, appliers) + (["--dry-run"] if options.dry_run else [])
    os.execv(command[0], command)


if __name__ == "__main__":
    main(sys.argv[1:])
