"""Choices shared by the Qt screens, previews and install.sh invocation."""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QImageReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import chicago95setup as backend  # noqa: E402

REF = "tests/references/"
DATA = "data/control-panel/"
DESKTOP_CAPTURES = {
    "1995": REF + "win95emptydesktop.png",
    "1998": REF + "win98emptydesktop.png",
    "2000": REF + "themes/win2k/desktop.png",
    "2001": REF + "themes/winxp-classic/desktop.png",
    "luna": REF + "xpemptydesktop.png",
    "aero": REF + "win7gadgets.png",
}
COMPONENTS = {
    "base": ("Install GTK themes, cursors, sounds and fallback icons.", "screenshot.png"),
    "look": ("Apply the selected desktop colours, frames and widgets.", REF + "win98-se-appearance.png"),
    "icons": ("Install the selected icon theme independently.", "data/desktop-icons/native/1998/computer.png"),
    "animations": ("Configure window, taskbar and menu animations.", REF + "win98effects.png"),
    "taskbar": ("Back up and replace the Plasma panels with the Chicago95 taskbar.", REF + "win98taskbarmenu.png"),
    "startmenu": ("Install the Start menu and Shut Down dialog.", REF + "win95startmenu.png"),
    "notifications": ("Install Chicago95 desktop notification popups.", REF + "win7-update-balloon.png"),
    "clippy": ("Install the Office Assistant.", REF + "clippy-letter.png"),
    "extras": ("Install System Properties, Device Manager and Dial-Up Networking.", REF + "win95sysprops.png"),
    "controlpanel": ("Install Control Panel to adjust these choices later.", REF + "win95controlpanel.png"),
    "sounds": ("Install desktop event sounds.", "installer/screenshots/sounds.png"),
    "background": ("Set the desktop wallpaper or colour.", DESKTOP_CAPTURES["1995"]),
    "desktop": (
        "Add My Computer, Network Neighborhood and Recycle Bin.",
        DESKTOP_CAPTURES["1995"],
    ),
    "switcher": ("Install the Alt+Tab window switcher.", REF + "win95alttab.png"),
    "screensaver": (
        "Install the screensaver runner and configure its idle timer.",
        REF + "win98screensaver.png",
    ),
    "winamp": ("Install the classic player skin and launcher for Qmmp.", "installer/screenshots/qmmp.png"),
    "explorer": ("Configure Explorer-style file manager navigation.", REF + "win98mycomputer.png"),
    "mouse": ("Apply pointer size and mouse preferences.", REF + "win98mouse.png"),
    "lockscreen": ("Install the Chicago95 screen locker.", REF + "themes/win2k/lock-screen/1280x1024.png"),
    "splash": ("Set the Plasma loading screen.", REF + "themes/win2k/post-login/1280x1024.png"),
    "plymouth": (
        "Install the system boot screen and rebuild the boot image (administrator access).",
        REF + "win95bootsm.png",
    ),
    "sddm": ("Install the system login screen (administrator access).", REF + "w2klogon.png"),
    "firefox": ("Apply the desktop colours to Firefox.", "installer/screenshots/firefox.png"),
}


@dataclass(frozen=True)
class Field:
    label: str
    example: str
    choices: tuple = ()
    kind: str = "text"


def menu(label, values):
    values = tuple(values.split() if isinstance(values, str) else values)
    return Field(label, values[0], values, "menu")


def picture(label, values):
    return Field(label, values[0], tuple(values), "image")


LOOKS = "1995 1998 2000 2001 luna aero"
OS_NAMES = dict(
    zip(
        LOOKS.split(),
        ("Windows 95", "Windows 98", "Windows 2000", "Windows XP Classic", "Windows XP", "Windows 7"),
        strict=True,
    )
)
LIGHT_FIELDS = ("icons", "panel", "cursor", "start-text", "sounds")
STYLES = "classic luna aero"
SOUNDS = ["Chicago95", *(p.name for p in sorted((ROOT / "data/sound-themes").iterdir()) if p.is_dir()), "Windows7"]
SAVERS = sorted(p.stem for p in (ROOT / "data/screensaver-previews").glob("*.png"))
FIELDS = {
    "look": menu("Desktop theme", LOOKS),
    "decoration": menu("Window frames", STYLES),
    "widget-style": menu("Widget style", STYLES),
    "taskbar-style": menu("Taskbar style", STYLES),
    "start-menu-style": menu("Start menu style", LOOKS),
    "control-panel-style": menu("Control Panel style", "auto " + STYLES),
    "icons": menu("Icon theme", "chicago95 se98 classicos2000 windowsxp windows7"),
    "TITLE_ACTIVE": Field("Active title bar colours", "#000080", kind="colour"),
    "TITLE_INACTIVE": Field("Inactive title bar colours", "#808080", kind="colour"),
    "BANNER_BG": Field("Start banner colours", "#808080", kind="colour"),
    "BANNER_FG": Field("Start banner lettering", "#ffffff", kind="colour"),
    "screen": Field("Screen size and scale", "1920x1080@1", kind="screen"),
    "panel": Field("Taskbar height (px)", "28", kind="number"),
    "task-button-width": Field("Task button width (px, 0 = automatic)", "160", kind="number"),
    "quick-launch": menu("Quick Launch", "auto yes no"),
    "task-grouping": menu("Task button grouping", "auto always full never"),
    "explorer": menu("File manager", "thunar dolphin"),
    "clippy": menu("Start Office Assistant at login", "yes no"),
    "cursor": menu("Pointer size (px)", "24 32 48"),
    "wobbly": menu("Window drag effect", "no yes blurred"),
    "font": Field("Interface font family", "Sans Serif"),
    "font-scope": menu("Use interface font on", "everywhere desktop none"),
    "start-text": Field("Start button text", "Start"),
    "start-logo": picture("Start button logo", ["flag", "xp", "penguin"]),
    "banner-text": Field("Start menu banner", "Chicago95"),
    "sounds": menu("Sound scheme", SOUNDS),
    "saver": Field("Screensaver", "deepstars", tuple(SAVERS), "saver"),
    "idle": Field("Start screensaver after (minutes)", "5", kind="number"),
    "branding": menu("System branding", "distro windows"),
    "login-style": menu("Login screen style", "classic 2000 luna aero"),
    "boot-style": menu("Boot screen style", "classic 2000 luna vista 7 8 8.1 10 11"),
    "LOGIN_TITLE": Field("Login window title", "Log On to %h"),
    "LOGIN_MESSAGE": Field("Login prompt", "Welcome. Please log on."),
    "LOGIN_ICON": picture("Login picture", ["keys", "padlock"]),
    "LOGIN_LOGO": picture("Login and loading logo", ["start", "win2k-flag", "waving-flag", "flag", "xp", "penguin"]),
    "EDITION": Field("System edition", "Professional"),
    "COMPANY": Field("Company name", "KDE"),
    "COMPANY_LOGO": picture("Company logo", ["text"]),
    "TAGLINE": Field("Login tagline", "Built on Linux Technology"),
    "SPLASH_IMAGE": picture("Loading picture", ["classic"]),
    "LOADING_TEXT": Field("Loading message", "Starting up..."),
    "LOADING_FOOTER": Field("Loading footer", "Chicago95 for KDE Plasma"),
}


def validate(key, value):
    if key not in FIELDS or not value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError(f"Invalid setting: {key}")
    field = FIELDS[key]
    valid = True
    if field.kind == "menu":
        valid = value in field.choices
    elif field.kind == "image" and value not in field.choices:
        valid = Path(value).is_absolute() and Path(value).is_file() and QImageReader(value).canRead()
    elif field.kind == "number":
        valid = bool(re.fullmatch(r"[0-9]{1,5}", value)) and (int(value) > 0 or key == "task-button-width")
    elif field.kind == "screen":
        match = re.fullmatch(r"([1-9]\d{0,4})x([1-9]\d{0,4})@(\d{1,2}(?:\.\d{1,4})?)", value)
        valid = bool(match and float(match[3]) > 0)
    elif field.kind == "colour":
        valid = bool(re.fullmatch(r"#[0-9a-fA-F]{6}(,#[0-9a-fA-F]{6})?", value))
    elif field.kind == "saver":
        valid = value in field.choices
    if not valid:
        raise ValueError(f"Invalid {field.label.lower()}. Example: {field.example}")


def linux_preferences(config):
    """Read supported Plasma preferences without changing the session."""

    def entry(filename, group, key):
        try:
            lines = (config / filename).read_text().splitlines()
        except (OSError, UnicodeError):
            return ""
        section = ""
        for line in lines:
            if line.startswith("["):
                section = line.strip()
            elif section == f"[{group}]" and line.startswith(key + "="):
                return line.partition("=")[2].strip()
        return ""

    choices = {"branding": "distro"}
    font = entry("kdeglobals", "General", "font").partition(",")[0]
    if font and font.isprintable():
        choices["font"] = font
    cursor = entry("kcminputrc", "Mouse", "cursorSize")
    if cursor in FIELDS["cursor"].choices:
        choices["cursor"] = cursor
    managers = {"org.kde.dolphin.desktop": "dolphin", "thunar.desktop": "thunar"}
    for filename in ("kde-mimeapps.list", "mimeapps.list"):
        manager = entry(filename, "Default Applications", "inode/directory").partition(";")[0].lower()
        if manager:
            if manager in managers:
                choices["explorer"] = managers[manager]
            break
    return choices


def plan(components, overrides):
    if not components or any(k not in COMPONENTS for k in components):
        raise ValueError("Select at least one known component.")
    args = ["--plain", "--yes", "--components=" + ",".join(components)]
    settings = {}
    for key, value in overrides.items():
        validate(key, value)
        if key == "icons" and not {"look", "icons"}.intersection(components):
            raise ValueError("Select Desktop look or Icons to apply an icon theme.")
        if key == "wobbly" and "animations" not in components:
            raise ValueError("Select Animations to apply a window drag effect.")
        if key.isupper():
            settings[key] = value
        else:
            args.append(f"--{key}={value}")
    return args, settings


def defaults(saved, overrides, machine=None):
    """Resolve inherited preview values in the same order as install.sh."""

    previous = backend.read_key_values(saved) if saved.is_file() else {}
    preset = previous.get("LOOK", "1995")
    values = backend.read_key_values(ROOT / "looks/1995.conf")
    if preset in LOOKS.split():
        values.update(backend.read_key_values(ROOT / f"looks/{preset}.conf"))
    values.update(previous)
    if overrides.get("look") in LOOKS.split():
        values.update(backend.read_key_values(ROOT / f"looks/{overrides['look']}.conf"))
    names = {"sounds": "SOUND_THEME", "idle": "IDLE_MIN", "clippy": "CLIPPY_AUTOSTART", "wobbly": "ANIM_WOBBLY"}
    base = {
        key: values.get(names.get(key, key.upper().replace("-", "_")), field.example) for key, field in FIELDS.items()
    }
    base.update({"look": preset, "wobbly": values.get("ANIM_WOBBLY", "no"), "saver": values.get("SAVER", "deepstars")})
    if machine:
        for key, value in machine.items():
            if key.upper() not in values:
                base[key] = value
    style = overrides.get("taskbar-style", base["taskbar-style"])
    screen = overrides.get("screen", base["screen"])
    if overrides.get("look") == "luna":
        base["task-button-width"] = "0"
    if "look" in overrides:
        base["branding"] = "windows"
    if "look" in overrides or not values.get("PANEL"):
        base["panel"] = backend.default_panel_height(
            backend.Choices({"TASKBAR_STYLE": style, "SCALE": screen.partition("@")[2]})
        )
    if "/" in base["SPLASH_IMAGE"]:
        base["SPLASH_IMAGE"] = str(ROOT / base["SPLASH_IMAGE"])
    return base | overrides
