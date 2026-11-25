"""The appliers Setup and the Control Panel's Apply share: each sets one part of the desktop from the choices and
reloads what shows it, without copying a component again. setup/steps.sh calls them through python_applier;
lib/chicago95apply.py runs them for the Control Panel. Each takes the run's Setup (lib/chicago95setup.py).

Standard library only: Setup runs on machines without PySide6.
"""

import filecmp
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

from chicago95setup import default_panel_height, extension, js_string

MENU_HEIGHT = 239  # fallback only; place_start_menu measures the real height
RUN_HEIGHT = 163  # the Run dialog with its frame and title (bin/chicago95-run)
CLIPPY_W, CLIPPY_H, CLIPPY_MARGIN = 124, 93, 24
NOTIFY_W = 340
AERO_BLUR_STRENGTH = 2
KWIN_BUILTIN_EFFECTS = Path("/usr/share/kwin/builtin-effects")
CHICAGO95_ZOOM = "chicago95zoom"


def home_path(setup, relative):
    return setup.home / relative


def panel_height(setup):
    """install.sh's PANEL_HEIGHT: the chosen taskbar height, or the taskbar style's own."""
    return int(setup.environment.get("PANEL_HEIGHT") or setup.choices["PANEL"] or default_panel_height(setup.choices))


def only_digits(text):
    return re.sub(r"[^0-9]", "", text)


# --- GTK and X settings shared by several appliers ---


def edit_xsettings(setup, key, value):
    """A key of the installed xsettingsd.conf."""
    conf = home_path(setup, ".config/xsettingsd/xsettingsd.conf")
    if not conf.exists() and not setup.dry_run:
        return
    setup.run("sed", "-i", f"s|^{key} .*|{key} {value}|", conf)
    if not setup.dry_run:
        setup.execute("pkill", "-HUP", "xsettingsd", quiet=True)


def set_gtk_interface(setup, key, value):
    """GTK programs on Wayland ignore XSETTINGS and read org.gnome.desktop.interface."""
    if not shutil.which("gsettings") and not setup.dry_run:
        return
    setup.run("gsettings", "set", "org.gnome.desktop.interface", key, value)
    setup.record(f"gsettings:{key}")


def gtk_settings(setup, version):
    return home_path(setup, f".config/gtk-{version}/settings.ini")


def gtk_theme_name(choices):
    return {"aero": "Chicago95Aero", "luna": "Chicago95Luna"}.get(choices.get("WIDGET_STYLE", "classic"), "Chicago95")


def install_aero_asset_pack(setup, kind, dest):
    with tempfile.TemporaryDirectory() as stage:
        if not setup.run("bash", setup.repo / "aero/fetch-desktop-assets.sh", kind, stage):
            return False
        setup.put_tree(stage, dest)
    return True


# --- mouse and pointer ---


def mouse(setup):
    """The double-click time, and for every pointer KWin has configured, which button is primary and its speed."""
    choices = setup.choices
    setup.kconf("kdeglobals", "KDE", "DoubleClickInterval", choices.get("DOUBLE_CLICK_MS", "500"))
    left_handed = "true" if choices.get("MOUSE_HAND", "right") == "left" else "false"
    inputs = home_path(setup, ".config/kcminputrc")
    devices = re.findall(
        r"^\[Libinput\]\[([^]]*)\]\[([^]]*)\]\[([^]]*)\]$", inputs.read_text() if inputs.exists() else "", re.M
    )
    for vendor, product, name in devices:
        groups = ("--group", "Libinput", "--group", vendor, "--group", product, "--group", name)
        setup.run("kwriteconfig6", "--file", "kcminputrc", *groups, "--key", "LeftHanded", left_handed)
        setup.run(
            "kwriteconfig6",
            "--file",
            "kcminputrc",
            *groups,
            "--key",
            "PointerAcceleration",
            choices.get("POINTER_SPEED", "0.0"),
        )
        setup.record("kconf:kcminputrc:Libinput:LeftHanded")


def pointer(setup):
    choices = setup.choices
    theme, size = "Chicago95_Animated_Hourglass_Cursors_HiDPI", choices.get("CURSOR", "32")
    aero = choices.get("WIDGET_STYLE", "classic") == "aero"
    if aero:
        theme = "Windows-7-Aero-Cursors_Default"
        pack = home_path(setup, f".local/share/icons/{theme}")
        drawn = all(
            (pack / "cursors" / name).is_file() and (pack / "cursors" / name).stat().st_size
            for name in ("left_ptr", "watch")
        )
        if not drawn and not install_aero_asset_pack(setup, "cursors", pack):
            return False
        if not setup.run(
            "python3", setup.repo / "aero/vector_art.py", "cursors", pack / "cursors", pack / "cursors_scalable"
        ):
            return False
    setup.run("plasma-apply-cursortheme", theme, "--size", size, to_log=True)
    setup.kconf("kcminputrc", "Mouse", "cursorTheme", theme)
    setup.kconf("kcminputrc", "Mouse", "cursorSize", size)
    for version in ("3.0", "4.0"):
        setup.run(
            "kwriteconfig6",
            "--file",
            gtk_settings(setup, version),
            "--group",
            "Settings",
            "--key",
            "gtk-cursor-theme-name",
            theme,
        )
    if aero:
        for version in ("3.0", "4.0"):
            setup.run(
                "kwriteconfig6",
                "--file",
                gtk_settings(setup, version),
                "--group",
                "Settings",
                "--key",
                "gtk-cursor-theme-size",
                size,
            )
        set_gtk_interface(setup, "cursor-size", size)
        edit_xsettings(setup, "Gtk/CursorThemeSize", size)
    set_gtk_interface(setup, "cursor-theme", theme)
    edit_xsettings(setup, "Gtk/CursorThemeName", f'"{theme}"')
    return True


# --- sounds, screensaver, Office Assistant ---


def sound_theme(setup):
    """The sound scheme of desktop events, in KDE, GTK, GNOME's settings and the login chime."""
    theme = setup.choices["SOUND_THEME"]
    setup.kconf("kdeglobals", "Sounds", "Theme", theme)
    for version in ("3.0", "4.0"):
        if gtk_settings(setup, version).exists():
            setup.run(
                "kwriteconfig6",
                "--file",
                gtk_settings(setup, version),
                "--group",
                "Settings",
                "--key",
                "gtk-sound-theme-name",
                theme,
            )
    if shutil.which("gsettings"):
        setup.run("gsettings", "set", "org.gnome.desktop.sound", "theme-name", theme)
    xsettings = home_path(setup, ".config/xsettingsd/xsettingsd.conf")
    if xsettings.exists():
        setup.run("sed", "-i", f's|^Net/SoundThemeName .*|Net/SoundThemeName "{theme}"|', xsettings)
        if not setup.dry_run:
            setup.execute("pkill", "-HUP", "xsettingsd", quiet=True)
    startup = home_path(setup, ".config/autostart/chicago95-startup.desktop")
    if startup.exists():
        setup.run("sed", "-i", f"s|sounds/[^/]*/stereo|sounds/{theme}/stereo|", startup)


def sounds(setup):
    """The chosen scheme, copied first when it is not installed yet."""
    name = setup.choices["SOUND_THEME"]
    theme, bundled = home_path(setup, f".local/share/sounds/{name}"), setup.repo / f"data/sound-themes/{name}"
    if not theme.is_dir():
        if bundled.is_dir():
            setup.put_tree(bundled, theme)
        if name == "Windows7":
            install_aero_asset_pack(setup, "sounds", theme)
    sound_theme(setup)


def screensaver(setup):
    """Plasma's power management watches idle time on Wayland and runs this command when it is reached."""
    choices = setup.choices
    idle = choices.get("IDLE_MIN", "5")
    command = f"{setup.home}/.local/bin/chicago95-screensaver --hack {choices.get('SAVER', 'deepstars')}"
    setup.backup(home_path(setup, ".config/powerdevilrc"))
    for profile in ("AC", "Battery", "LowBattery"):
        groups = ("--file", "powerdevilrc", "--group", profile, "--group", "RunScript")
        setup.run("kwriteconfig6", *groups, "--key", "RunScriptIdleTimeoutSec", str(int(idle) * 60))
        setup.run("kwriteconfig6", *groups, "--key", "IdleTimeoutCommand", command)
    setup.record("powerdevil:RunScript")
    setup.show_copy(f"(run {command} after {idle} min idle)", home_path(setup, ".config/powerdevilrc"))
    setup.run("systemctl", "--user", "restart", "plasma-powerdevil.service")


def clippy_autostart(setup):
    """The Office Assistant at log on, or only when started by hand."""
    entry = home_path(setup, ".config/autostart/chicago95-clippy.desktop")
    if setup.choices.get("CLIPPY_AUTOSTART", "yes")[:1] in ("y", "Y"):
        setup.put_file(setup.repo / "config/autostart/chicago95-clippy.desktop", entry)
        setup.substitute_home(entry)
    elif setup.installed_by_setup(entry):
        setup.run("rm", "-f", entry)


def clippy_restart(setup):
    """A Clippy already on screen keeps the balloon it started with: the new one takes the look."""
    clippy = home_path(setup, ".local/bin/chicago95-clippy")
    if not setup.succeeds("pgrep", "-f", f"python3 {clippy}"):
        return
    setup.run("pkill", "-f", f"python3 {clippy}")
    setup.run("setsid", "-f", clippy)


# --- the Start button, menu and the names the screens show ---

WAVING_FLAG = ".local/share/chicago95/waving-flag.png"


def start_logo_source(setup):
    """The image behind the Start logo choice: a bundled logo name, or the user's file."""
    images = setup.repo / "plasmoids/org.chicago95.start/contents/images"
    logo = setup.choices["START_LOGO"]
    bundled = {
        "flag": "logo-flag-16.png",
        "xp": "logo-xp-16.png",
        "penguin": "logo-penguin.svg",
    }  # pixel art at its size
    return str(images / bundled[logo]) if logo in bundled else logo


def start_logo_file(setup):
    """The copy keeps the source's extension, so the image loader never has to guess PNG from SVG."""
    return str(home_path(setup, f".local/share/chicago95/start-logo.{extension(start_logo_source(setup))}"))


def image_source(setup, choice):
    """The file behind a picture choice: a bundled name, or the user's own file."""
    images, sddm = setup.repo / "plasmoids/org.chicago95.start/contents/images", setup.repo / "sddm/Chicago95Plasma"
    if choice == "start":
        return start_logo_source(setup)
    bundled = {
        "flag": images / "logo-flag.png",
        "win2k-flag": sddm / "Windows2000Flag.svg",
        "aero-flag": sddm / "AeroBrandFlag.svg",
        "penguin": images / "logo-penguin.svg",
        "waving-flag": home_path(setup, WAVING_FLAG),
        "keys": sddm / "key-9x.png",
        "padlock": sddm / "padlock.svg",
        "classic": setup.repo / "splash/chicago95.splashscreen/contents/splash/images/background.png",
    }
    return str(bundled.get(choice, choice))


def login_logo(setup):
    """The login and loading screens' logo; "start" is the Start button's, from its copy once Setup made one."""
    if setup.choices["LOGIN_LOGO"] == "start" and Path(start_logo_file(setup)).is_file():
        return start_logo_file(setup)
    return image_source(setup, setup.choices["LOGIN_LOGO"])


def company_logo_file(setup):
    """The company logo lands in one known file like the Start logo; "text" shows the company's name instead."""
    logo = setup.choices["COMPANY_LOGO"]
    return "" if logo == "text" else str(home_path(setup, f".local/share/chicago95/company-logo.{extension(logo)}"))


def put_company_logo(setup):
    if company_logo_file(setup):
        setup.put_file(setup.choices["COMPANY_LOGO"], company_logo_file(setup))


def ensure_waving_flag(setup):
    """The waving flag is a trademark, so it isn't bundled: it is downloaded from Wikimedia Commons when picked,
    and the classic flag stands in when the download fails."""
    flag = home_path(setup, WAVING_FLAG)
    if setup.choices["LOGIN_LOGO"] != "waving-flag" or flag.exists():
        return
    setup.run("mkdir", "-p", flag.parent)
    if setup.run("python3", setup.repo / "setup/fetch-waving-flag.py", flag):
        setup.record(flag)
        setup.show_copy("(downloaded from Wikimedia Commons)", flag)
        return
    setup.status("Could not download the waving flag; the login and loading screens show the classic flag")
    setup.set_choice("LOGIN_LOGO", "flag")


def start_logo(setup):
    """Whatever logo was picked lands in one known file, so it can be swapped later without Setup."""
    logo_file = start_logo_file(setup)
    setup.put_file(start_logo_source(setup), logo_file)
    setup.set_choice("START_LOGO", logo_file)


def chicago95rc(setup, group, key, value):
    setup.run("kwriteconfig6", "--file", "chicago95rc", "--group", group, "--key", key, value)


def start_menu(setup):
    choices = setup.choices
    chicago95rc(setup, "StartMenu", "bannerText", choices["BANNER_TEXT"])
    chicago95rc(setup, "StartMenu", "bannerBackground", choices.get("BANNER_BG", "#808080"))
    chicago95rc(setup, "StartMenu", "bannerTextColor", choices.get("BANNER_FG", "#C0C0C0"))
    chicago95rc(setup, "StartMenu", "style", choices["START_MENU_STYLE"])
    setup.flag("START_MENU_CHANGED")


def look_rc(setup):
    """chicago95-sync-colors draws the bevels with the look's colours, and reads the look from here."""
    choices = setup.choices
    chicago95rc(setup, "Look", "decoration", choices["DECORATION"])
    chicago95rc(setup, "Look", "captionDpi", choices.get("DPI", "96"))
    chicago95rc(setup, "Look", "controlPanelStyle", choices["CONTROL_PANEL_STYLE"])
    chicago95rc(setup, "Look", "widgetStyle", choices["WIDGET_STYLE"])
    chicago95rc(setup, "Look", "bevel", choices.get("BEVEL", "1995"))
    chicago95rc(setup, "Look", "taskbarStyle", choices["TASKBAR_STYLE"])
    chicago95rc(setup, "StartMenu", "style", choices["START_MENU_STYLE"])
    setup.flag("START_MENU_CHANGED")


def branding(setup):
    """[Branding] in chicago95rc: what the 2000 banners show (Shut Down dialog, login banner)."""
    choices = setup.choices
    put_company_logo(setup)
    ensure_waving_flag(setup)
    chicago95rc(setup, "Branding", "osName", choices["BANNER_TEXT"])
    chicago95rc(setup, "Branding", "osLogo", login_logo(setup))
    chicago95rc(setup, "Branding", "osCompany", choices["COMPANY"])
    chicago95rc(setup, "Branding", "osEdition", choices["EDITION"])
    chicago95rc(setup, "Branding", "tagline", choices["TAGLINE"])
    chicago95rc(setup, "Branding", "companyLogo", company_logo_file(setup))
    setup.record(home_path(setup, ".config/chicago95rc"))


# --- windows placed above the taskbar, and the keys ---


def measured(setup, *command, fallback):
    """A height a tool measures offscreen at the screen's scale; the fallback when it cannot."""
    environment = {"QT_QPA_PLATFORM": "offscreen", "QT_SCALE_FACTOR": setup.choices.get("SCALE", "1")}
    lines = setup.output_of("python3", *command, environment=environment).strip().splitlines()
    return int(lines[-1]) if lines and lines[-1].isdigit() else fallback


def place_start_menu(setup):
    """The menu's bottom edge sits just above the taskbar (one pixel up for the classic menus: at fractional scales
    their height rounds up and would cover the taskbar's top line); its height is measured, not assumed."""
    choices = setup.choices
    height = measured(setup, setup.repo / "bin/chicago95-startmenu", "--root-height", fallback=MENU_HEIGHT)
    gap = 0 if choices["START_MENU_STYLE"] in ("luna", "aero") else 1
    top = int(choices["HEIGHT"]) - panel_height(setup) - height - gap
    setup.kwin_rule(
        "chicago95-startmenu",
        "Description=Chicago95 Start menu",
        "wmclass=chicago95-startmenu",
        "wmclassmatch=1",
        "title=chicago95-startmenu-root",
        "titlematch=1",
        f"position=0,{top}",
        "positionrule=2",
        "placement=Zero",
        "placementrule=2",
        "above=true",
        "aboverule=2",
        "skiptaskbar=true",
        "skiptaskbarrule=2",
        "skippager=true",
        "skippagerrule=2",
        "skipswitcher=true",
        "skipswitcherrule=2",
        "noborder=true",
        "noborderrule=2",
        "types=1",
    )


def decoration_frame_height(setup):
    """The title bar and bottom border of the decoration Setup installs."""
    rc = {
        "luna": "luna/aurorae/theme/Chicago95Lunarc",
        "aero": "aero/aurorae/theme/Chicago95Aerorc",
    }.get(setup.choices["DECORATION"], "aurorae/theme/Chicago95rc")
    parts = ("TitleHeight", "TitleEdgeTop", "TitleEdgeBottom", "BorderBottom")
    pairs = (line.split("=", 1) for line in (setup.repo / rc).read_text().splitlines() if "=" in line)
    return sum(int(float(value)) for key, value in pairs if key in parts)


def run_window_height(setup):
    """The Run window's height: the dialog's own (it draws its classic frame itself), plus under another widget style
    the title and bottom border KWin's decoration adds around it."""
    choices = setup.choices
    dialog = measured(
        setup,
        setup.repo / "bin/chicago95-run",
        "--height",
        f"--widget-style={choices['WIDGET_STYLE']}",
        f"--menu-style={choices['START_MENU_STYLE']}",
        fallback=RUN_HEIGHT,
    )
    return dialog if choices["WIDGET_STYLE"] == "classic" else dialog + decoration_frame_height(setup)


def place_run_dialog(setup):
    """Placed on the taskbar as it opens (positionrule 3), then free to be dragged; 2 would pin it for good."""
    top = int(setup.choices["HEIGHT"]) - panel_height(setup) - run_window_height(setup)
    setup.kwin_rule(
        "chicago95-run",
        "Description=Chicago95 Run dialog",
        "wmclass=chicago95-run",
        "wmclassmatch=1",
        f"position=0,{top}",
        "positionrule=3",
        "placement=Zero",
        "placementrule=2",
        "types=1",
    )


def place_notifications(setup):
    width, height = int(setup.choices["WIDTH"]), int(setup.choices["HEIGHT"])
    host_height = height * 3 // 4 + 20
    setup.kwin_rule(
        "chicago95-notifyd",
        "Description=Chicago95 notification column",
        "wmclass=chicago95-notifyd",
        "wmclassmatch=1",
        "title=chicago95-notifyd-host",
        "titlematch=1",
        f"position={width - NOTIFY_W},{height - panel_height(setup) - host_height}",
        "positionrule=2",
        "placement=Zero",
        "placementrule=2",
        "acceptfocus=false",
        "acceptfocusrule=2",
        "skiptaskbar=true",
        "skiptaskbarrule=2",
        "skippager=true",
        "skippagerrule=2",
        "skipswitcher=true",
        "skipswitcherrule=2",
        "noborder=true",
        "noborderrule=2",
        "above=true",
        "aboverule=2",
        "types=1",
    )


def place_clippy(setup):
    width, height = int(setup.choices["WIDTH"]), int(setup.choices["HEIGHT"])
    left, top = width - CLIPPY_W - CLIPPY_MARGIN, height - panel_height(setup) - CLIPPY_H - CLIPPY_MARGIN
    setup.kwin_rule(
        "chicago95-clippy",
        "Description=Chicago95 Office Assistant",
        "wmclass=chicago95-clippy",
        "wmclassmatch=1",
        f"position={left},{top}",
        "positionrule=3",
        "placement=Zero",
        "placementrule=3",
        "skiptaskbar=true",
        "skiptaskbarrule=2",
        "skippager=true",
        "skippagerrule=2",
        "noborder=true",
        "noborderrule=2",
        "above=true",
        "aboverule=2",
        "types=1",
    )


def window_rules(setup):
    """The windows that sit on the taskbar follow its height, and their own."""
    place_start_menu(setup)
    place_run_dialog(setup)
    if setup.installed_by_setup("kwinrule:chicago95-notifyd"):
        place_notifications(setup)
    if setup.installed_by_setup("kwinrule:chicago95-clippy"):
        place_clippy(setup)


def explorer_desktop_file(choices):
    return "org.kde.dolphin.desktop" if choices.get("EXPLORER", "thunar") == "dolphin" else "thunar.desktop"


def service_shortcut(setup, desktop_file, keys):
    setup.run(
        "kwriteconfig6",
        "--file",
        "kglobalshortcutsrc",
        "--group",
        "services",
        "--group",
        desktop_file,
        "--key",
        "_launch",
        keys,
    )
    setup.record(f"shortcut:{desktop_file}")


def shortcuts(setup):
    """The originals' keys: the Windows key alone and Ctrl+Esc open the Start menu, Win+R Run, Win+E Explorer, Win+D
    and Win+M show the desktop, Win+F Find. KConfig separates alternatives with a tab."""
    service_shortcut(setup, "chicago95-startmenu.desktop", "Ctrl+Esc")
    service_shortcut(setup, "chicago95-run.desktop", "Meta+R")
    service_shortcut(setup, "chicago95-showdesktop.desktop", "Meta+D\tMeta+M")
    service_shortcut(setup, "org.kde.kfind.desktop", "Meta+F")
    service_shortcut(setup, explorer_desktop_file(setup.choices), "Meta+E")
    setup.kconf(
        "kwinrc",
        "ModifierOnlyShortcuts",
        "Meta",
        "org.kde.kglobalaccel,/component/chicago95_startmenu_desktop,org.kde.kglobalaccel.Component,invokeShortcut,_launch",
    )
    setup.kwin_reconfigure()


# --- Alt+Tab ---

SWITCHER_DIR = ".local/share/kwin/tabbox/chicago95"


def preview_size(choices):
    """The width of a task button's hover preview and of Alt+Tab's previews; 0 is off."""
    size = choices.get("PREVIEW_SIZE", "off")
    return size if size in ("160", "240", "320") else "0"


def face_hex(choices):
    """The look's face as #RRGGBB (FACE is "r,g,b" for 2000, empty otherwise)."""
    red, green, blue = (int(part) for part in choices.get("FACE", "192,192,192").split(","))
    return f"#{red:02X}{green:02X}{blue:02X}"


def switcher_settings(setup):
    """settings.js of the installed switcher: its preview size and look; the switcher chosen in kwinrc."""
    choices, ui = setup.choices, home_path(setup, SWITCHER_DIR) / "contents/ui"
    setup.write_file(
        ui / "settings.js",
        ".pragma library\n"
        f"var previewSize = {preview_size(choices)};\n"
        f"var look = {js_string(choices['START_MENU_STYLE'])};\n"
        f"var face = {js_string(face_hex(choices))};\n",
    )
    setup.show_copy(
        f"(Alt+Tab: previews {preview_size(choices)}, look {choices['START_MENU_STYLE']})", ui / "settings.js"
    )
    setup.kconf("kwinrc", "TabBox", "LayoutName", "chicago95")
    setup.kconf("kwinrc", "TabBox", "ShowTabBox", "true")
    setup.kconf("kwinrc", "TabBox", "HighlightWindows", "true" if choices["START_MENU_STYLE"] == "aero" else "false")
    setup.kwin_reconfigure()


def installed(setup, path):
    """An installed component, or a dry run that lists what Apply would do to one."""
    return setup.dry_run or Path(path).exists()


def switcher(setup):
    switcher_dir = home_path(setup, SWITCHER_DIR)
    if not installed(setup, switcher_dir):
        return
    luna = switcher_dir / "contents/ui/luna"
    if setup.choices["START_MENU_STYLE"] == "luna" and not luna.is_dir():
        setup.put_tree(setup.repo / "luna/kwin-tabbox", luna)
    switcher_settings(setup)


# --- the taskbar ---


def panel_hiding(choices):
    """The panel.hiding value the saved choices ask for; nothing when none was saved."""
    if choices["TASKBAR_AUTOHIDE"] == "yes":
        return "autohide"
    if choices["TASKBAR_ON_TOP"] == "no":
        return "windowsgobelow"
    return "none" if choices["TASKBAR_AUTOHIDE"] or choices["TASKBAR_ON_TOP"] else ""


def clock_hours(choices):
    return choices["CLOCK_HOURS"] if choices["CLOCK_HOURS"] in ("locale", "12", "24") else ""


def js_list(text):
    return json.dumps([entry for entry in text.split(",") if entry])


def quick_launch_shown(choices):
    """The Quick Launch option: yes, no, or auto for the look's own (quickLaunch.js decides alike)."""
    option = choices.get("QUICK_LAUNCH", "auto")
    return option == "yes" or (option != "no" and choices["START_MENU_STYLE"] != "1995")


def quick_launch_defaults(setup):
    """The task list's default Quick Launch programs, from its settings file, as a JS list."""
    config = (setup.repo / "plasmoids/org.chicago95.tasks/contents/config/main.xml").read_text()
    entry = re.search(r'name="launchers".*?<default>(.*?)</default>', config, re.S)
    pins = entry.group(1).strip().split(",") if entry else [""]
    if setup.choices["TASKBAR_STYLE"] == "aero":
        pins = [pin for pin in pins if pin != "applications:chicago95-showdesktop.desktop"]
    return json.dumps(pins)


def same_file(first, second):
    return Path(first).is_file() and Path(second).is_file() and filecmp.cmp(first, second, shallow=False)


def panel_start_logo(setup):
    """The logo the Start button shows: the superbar's orb draws the bundled flags and the distribution's logo its
    own way, by name."""
    logo = setup.choices["START_LOGO"]
    if setup.choices["TASKBAR_STYLE"] != "aero" or not Path(logo).is_file():
        return logo
    images = setup.repo / "plasmoids/org.chicago95.start/contents/images"
    for kind in ("flag", "xp"):
        if same_file(logo, images / f"logo-{kind}-16.png"):
            return kind
    orb = home_path(setup, ".local/share/chicago95/icons/fedora-orb-logo.svg")
    if (
        orb.is_file()
        and orb.stat().st_size
        and same_file(logo, "/usr/share/icons/hicolor/32x32/apps/fedora-logo-icon.png")
    ):
        return str(orb)
    if same_file(logo, home_path(setup, ".local/share/icons/Windows-7/apps/distributor-logo.png")):
        return "flag"
    return logo


def taskbar_script(setup):
    """Plasma's script that puts the choices into every taskbar applet: the Start button's text and logo, the look,
    the task list's options and the clock."""
    choices = setup.choices
    look, style, bevel = (
        js_string(value)
        for value in (choices["START_MENU_STYLE"], choices["TASKBAR_STYLE"], choices.get("BEVEL", "1995"))
    )
    width = only_digits(choices["TASK_BUTTON_WIDTH"])
    width_script = (
        f"panel.widgets('org.chicago95.tasks').forEach(widget => {{ widget.currentConfigGroup = ['General']; widget.writeConfig('maxButtonWidth', {width}); }});"
        if width
        else ""
    )
    launchers_script = ""
    if "LAUNCHERS" in choices:
        launchers_script = f"panel.widgets('org.chicago95.tasks').forEach(widget => {{ widget.currentConfigGroup = ['General']; widget.writeConfig('launchers', {js_list(choices['LAUNCHERS'])}); }});"
    elif quick_launch_shown(choices):
        launchers_script = f"""// A taskbar first built under 1995 saved an empty Quick Launch; where it shows, it gets the defaults.
        panel.widgets('org.chicago95.tasks').forEach(widget => {{
            widget.currentConfigGroup = ['General'];
            if (String(widget.readConfig("launchers", '')) === '')
                widget.writeConfig('launchers', {quick_launch_defaults(setup)});
        }});"""
    height = only_digits(choices["PANEL"])
    height_script = f"if (panel.widgets('org.chicago95.tasks').length > 0) panel.height = {height};" if height else ""
    hiding = panel_hiding(choices)
    hiding_script = (
        f"if (panel.widgets('org.chicago95.tasks').length > 0) panel.hiding = \"{hiding}\";" if hiding else ""
    )
    clock_script = {
        "no": "panel.widgets('org.chicago95.clock').forEach(widget => widget.remove());",
        "yes": "if (panel.widgets('org.chicago95.tasks').length > 0 && panel.widgets('org.chicago95.clock').length === 0) "
        f"{{ const clock = panel.addWidget('org.chicago95.clock'); clock.currentConfigGroup = ['General']; clock.writeConfig('look', {look}); "
        f"clock.writeConfig('taskbarStyle', {style}); clock.writeConfig('bevel', {bevel}); }}",
    }.get(choices["CLOCK_SHOW"], "")
    if clock_hours(choices):
        clock_script += f" panel.widgets('org.chicago95.clock').forEach(widget => {{ widget.currentConfigGroup = ['General']; widget.writeConfig('hourFormat', {js_string(clock_hours(choices))}); }});"
    slide_script = ""
    if choices["ANIM_TASKBAR"] in ("none", "slide"):
        slide_script = (
            f"widget.writeConfig('animateButtons', {'true' if choices['ANIM_TASKBAR'] == 'slide' else 'false'});"
        )
    return f"""panels().forEach(panel => {{
        {height_script}
        {width_script}
        {hiding_script}
        {clock_script}
        panel.widgets('org.chicago95.tasks').forEach(widget => {{
            widget.currentConfigGroup = ['General'];
            widget.writeConfig('quickLaunch', {js_string(choices.get("QUICK_LAUNCH", "auto"))});
            widget.writeConfig('grouping', {js_string(choices.get("TASK_GROUPING", "auto"))});
            widget.writeConfig('previewSize', {preview_size(choices)});
            widget.writeConfig('referenceDpi', {choices.get("DPI", "96")});
            {slide_script}
        }});
        panel.widgets('org.chicago95.start').forEach(widget => {{
            widget.currentConfigGroup = ['General'];
            widget.writeConfig('buttonText', {js_string(choices.get("START_TEXT", "Start"))});
            widget.writeConfig('logo', {js_string(panel_start_logo(setup))});
        }});
        ['org.chicago95.start', 'org.chicago95.tasks', 'org.chicago95.trayframe', 'org.chicago95.clock'].forEach(applet =>
            panel.widgets(applet).forEach(widget => {{
                widget.currentConfigGroup = ['General'];
                widget.writeConfig('look', {look});
                widget.writeConfig('taskbarStyle', {style});
                widget.writeConfig('bevel', {bevel});
            }}));
        {launchers_script}
    }})"""


def taskbar(setup):
    """The choices into the running taskbar, once plasmashell answers (a restart may still be on its way)."""
    if setup.choices["IN_PLASMA"] != "1" or setup.dry_run:
        return
    for _ in range(20):
        if setup.succeeds(
            "gdbus",
            "call",
            "--session",
            "--dest",
            "org.kde.plasmashell",
            "--object-path",
            "/PlasmaShell",
            "--method",
            "org.kde.PlasmaShell.evaluateScript",
            'print("ready")',
        ):
            break
        time.sleep(0.5)
    setup.plasma_script(taskbar_script(setup))


def panel(setup):
    """The taskbar's options are written once the shell is back; the Start button shows Setup's copy of its logo."""
    if Path(start_logo_file(setup)).is_file():
        setup.set_choice("START_LOGO", start_logo_file(setup))
    setup.flag("TASKBAR_CHANGED")


# --- the desktop: background and icons ---


def background_color(choices):
    """The colour chosen when it is a #RRGGBB, else the classic teal."""
    color = choices["BACKGROUND_COLOR"]
    return color if re.fullmatch(r"#[0-9A-Fa-f]{6}", color) else "#008080"


def background_script(setup, image):
    choices = setup.choices
    color = background_color(choices)
    red, green, blue = (int(color[index : index + 2], 16) for index in (1, 3, 5))
    plugin, writes = "org.kde.color", f'desktop.writeConfig("Color", "{red},{green},{blue}");'
    mode = choices.get("BACKGROUND_MODE", "color")
    if mode == "image":
        fill = {"tile": "3", "stretch": "0", "cover": "2"}.get(choices["BACKGROUND_FILL"], "6")
        plugin = "org.kde.image"
        writes += f' desktop.writeConfig("Image", {js_string("file://" + (image or choices["BACKGROUND_IMAGE"]))}); desktop.writeConfig("FillMode", {fill});'
    elif mode == "pattern":
        plugin = "org.kde.image"
        writes += f' desktop.writeConfig("Image", {js_string("file://" + str(pattern_picture(setup)))}); desktop.writeConfig("FillMode", 3);'
    return (
        "desktops().forEach(desktop => {\n"
        f'    desktop.wallpaperPlugin = "{plugin}";\n'
        f'    desktop.currentConfigGroup = ["Wallpaper", "{plugin}", "General"];\n'
        f"    {writes}\n"
        "});\n"
    )


def pattern_picture(setup):
    return home_path(setup, ".local/share/chicago95/pattern.png")


def run_plasma_script(setup, script):
    """setup/steps.sh's `run plasma_script`: listed in a dry run, sent to Plasma otherwise."""
    if setup.dry_run:
        setup.log(f"  would: plasma_script {script}")
        return
    setup.plasma_script(script)


def background(setup):
    """The desktop picture: a colour, one tile of a pattern, or an image, written into every desktop's wallpaper."""
    choices = setup.choices
    mode = choices.get("BACKGROUND_MODE", "color")
    if mode == "pattern":
        pattern = (
            choices["BACKGROUND_PATTERN"]
            if choices["BACKGROUND_PATTERN"] in ("checks", "diagonal", "grid", "dots")
            else "checks"
        )
        setup.run("mkdir", "-p", pattern_picture(setup).parent)
        setup.run(
            "python3",
            setup.repo / "setup/background_pattern.py",
            pattern,
            background_color(choices),
            pattern_picture(setup),
        )
        setup.record(pattern_picture(setup))
    if not setup.dry_run and choices["IN_PLASMA"] != "1":
        setup.status("Plasma is not running; the desktop background is unchanged")
        return
    image = ""
    if mode == "image":
        image = choices["BACKGROUND_IMAGE"]
        if image.startswith(f"{setup.repo}/data/wallpapers/") and Path(image).is_file():
            target = home_path(setup, f".local/share/chicago95/wallpapers/{Path(image).name}")
            setup.put_file(image, target)
            image = str(target)
    run_plasma_script(setup, background_script(setup, image))


def desktop_icon_defaults(choices):
    return {
        "aero": "recycle",
        "luna": "recycle",
        "1995": "computer,network,recycle",
        "2001": "documents,computer,network,recycle",
    }.get(choices["START_MENU_STYLE"], "computer,documents,network,recycle")


def desktop_icons_chosen(choices):
    """DESKTOP_ICONS lists them (computer, documents, network, recycle); unset or auto takes the look's own, empty none."""
    chosen = choices.unset_or("DESKTOP_ICONS", "auto")
    chosen = desktop_icon_defaults(choices) if chosen == "auto" else chosen
    return [icon for icon in chosen.split(",") if icon in ("computer", "documents", "network", "recycle")]


def desktop_icon_source(setup, icon):
    """The link file in the repository; 2000 calls the network My Network Places."""
    desktop, style = setup.repo / "config/desktop", setup.choices["START_MENU_STYLE"]
    if style == "aero" and icon != "recycle":
        return desktop / f"aero/{icon}.desktop"
    network = "my-network-places" if style in ("2000", "2001") else "network-neighborhood"
    names = {"computer": "my-computer", "documents": "my-documents", "network": network, "recycle": "trash"}
    return desktop / f"{names[icon]}.desktop"


def desktop_link_name(source):
    return re.search(r"^Name=(.*)$", Path(source).read_text(), re.M).group(1)


DESKTOP_SCRIPT = """desktops().forEach(desktop => {
    if (desktop.type !== "org.kde.plasma.folder") { print("desktop " + desktop.id + " is " + desktop.type + ", not a Folder View: no desktop icons"); return; }
    desktop.currentConfigGroup = ["General"];
    desktop.writeConfig("iconSize", 1);
    desktop.writeConfig("labelWidth", 0);
    desktop.writeConfig("textLines", 2);
    desktop.writeConfig("arrangement", 1);
    desktop.writeConfig("alignment", 0);
    desktop.reloadConfig();
});
"""


def desktop_icons(setup):
    """Links in ~/Desktop, shown by Folder View at the originals' 32px with two label lines."""
    choices, style = setup.choices, setup.choices["START_MENU_STYLE"]
    if style == "aero" or (style == "luna" and choices.unset_or("DESKTOP_ICONS", "auto") == "auto"):
        for name in ("my-computer", "my-documents", "my-network-places", "network-neighborhood"):
            old = setup.repo / f"config/desktop/{name}.desktop"
            target = home_path(setup, f"Desktop/{desktop_link_name(old)}.desktop")
            as_installed = old.read_text().replace("@HOME@", str(setup.home))
            if setup.installed_by_setup(target) and target.is_file() and target.read_text() == as_installed:
                setup.backup(target)
                setup.run("rm", "-f", target)
    for icon in desktop_icons_chosen(choices):
        source = desktop_icon_source(setup, icon)
        target = home_path(setup, f"Desktop/{desktop_link_name(source)}.desktop")
        setup.put_file(source, target)
        setup.substitute_home(target)
        if icon == "computer" and style == "aero":
            if choices.get("EXPLORER", "thunar") == "dolphin" or choices.get("HAS_THUNAR", "0") != "1":
                setup.run("sed", "-i", "s|^Exec=.*|Exec=dolphin computer:/|", target)
            setup.run("chmod", "+x", target)
    if not setup.dry_run and choices["IN_PLASMA"] != "1":
        setup.status("Plasma is not running; the desktop's icon layout is unchanged")
        return
    run_plasma_script(setup, DESKTOP_SCRIPT)


# --- the lock and loading screens' settings ---

LOCKSCREEN_DIR = ".local/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen"
SPLASH_DIR = ".local/share/plasma/look-and-feel/chicago95.splashscreen/contents/splash"
POST_XP_OPTIONS = (
    ("BOOT_LOGO", "logo"),
    ("BOOT_NAME", "name"),
    ("BOOT_TEXT", "text"),
    ("BOOT_FOOTER", "footer"),
    ("BOOT_BACKGROUND", "background"),
    ("BOOT_FOREGROUND", "foreground"),
    ("BOOT_ACCENT", "accent"),
    ("BOOT_FONT", "font"),
    ("BOOT_BACKGROUND_IMAGE", "backgroundImage"),
    ("BOOT_ANIMATION", "animation"),
    ("BOOT_FRAMES", "frames"),
    ("BOOT_LOOP_START", "loopStart"),
    ("BOOT_FPS", "fps"),
    ("BOOT_LOGO_SIZE", "logoSize"),
)


def lockscreen_settings(setup):
    """settings.js of the installed lock screen: the look it is drawn in, on the desktop colour."""
    choices = setup.choices
    directory = Path(setup.environment.get("APPLY_INTO") or home_path(setup, LOCKSCREEN_DIR))
    if not installed(setup, directory):
        return
    text = f".pragma library\nvar look = {js_string(choices['LOGIN_STYLE'])};\nvar desktopColor = {js_string(background_color(choices))};\n"
    xp_classic = choices["LOGIN_STYLE"] == "2000" and choices["START_MENU_STYLE"] == "2001"
    text += f"var xpClassic = {'true' if xp_classic else 'false'};\n"
    text += f"var hostName = {js_string(os.uname().nodename if xp_classic else '')};\n"
    if choices["LOGIN_STYLE"] == "aero":
        logo = f"classic/brand-logo.{extension(login_logo(setup))}"
        text += f"var brandText = {js_string(choices['BANNER_TEXT'])};\nvar brandEdition = {js_string(choices['EDITION'])};\nvar brandLogo = {js_string(logo)};\n"
    setup.write_file(directory / "settings.js", text)
    setup.show_copy(f"(lock screen look {choices['LOGIN_STYLE']})", directory / "settings.js")


def boot_style(choices):
    """The boot and loading screens' style, chosen on its own; until then, the login's."""
    return choices.get("BOOT_STYLE") or choices.get("LOGIN_STYLE") or "classic"


def user_picture(setup):
    """The user's picture, as the Start menu finds it (lib/chicago95ui.py user_picture_path)."""
    user = setup.environment.get("USER") or setup.output_of("id", "-un").strip()
    accounts = setup.environment.get("ACCOUNTS_ICONS", "/var/lib/AccountsService/icons")
    for picture in (setup.home / ".face", setup.home / ".face.icon", Path(accounts) / user):
        if picture.is_file():
            return str(picture)
    return ""


def splash_file(setup):
    """settings.js of a loading screen (the installed one, or the boot screen being drawn): its style, texts and
    pictures. The directory is the run's --into."""
    choices = setup.choices
    directory = Path(setup.environment.get("APPLY_INTO") or home_path(setup, SPLASH_DIR))
    style, brand, edition, footer = (
        boot_style(choices),
        choices["BANNER_TEXT"],
        choices["EDITION"],
        choices["LOADING_FOOTER"],
    )
    if style == "luna" and not choices.unset_or("BANNER_TEXT", "Chicago95"):
        brand, edition = "", choices.unset_or("EDITION", "")
        footer = choices.unset_or("LOADING_FOOTER", "Copyright © Microsoft Corporation")
    ensure_waving_flag(setup)
    put_company_logo(setup)
    post_xp = "".join(
        f"{js_string(name)}:{js_string(choices[key])}," for key, name in POST_XP_OPTIONS if key in choices
    )
    user = setup.environment.get("USER") or setup.output_of("id", "-un").strip()
    values = [
        ("style", style),
        ("brandText", brand),
        ("brandLogo", login_logo(setup)),
        ("edition", edition),
        ("tagline", choices["TAGLINE"]),
        ("company", choices["COMPANY"]),
        ("companyLogo", company_logo_file(setup)),
        ("loadingText", choices["LOADING_TEXT"]),
        ("footer", footer.replace("%h", os.uname().nodename)),
        ("picture", image_source(setup, choices["SPLASH_IMAGE"])),
        ("logonStyle", choices["LOGIN_STYLE"]),
        ("desktopColor", background_color(choices)),
        ("userName", user),
        ("userPicture", user_picture(setup)),
    ]
    lines = [".pragma library", f"var style = {js_string(style)}", f"var postXp = {{{post_xp}}}"]
    lines += [f"var {name} = {js_string(value)}" for name, value in values[1:]]
    setup.write_file(directory / "settings.js", "".join(f"{line}\n" for line in lines))
    setup.show_copy(f"(loading screen: {style}, {choices['BANNER_TEXT']})", directory / "settings.js")


def splash_settings(setup):
    """The installed loading screen's settings; the 2000 login's status banner is drawn with them."""
    directory = home_path(setup, SPLASH_DIR)
    if not installed(setup, directory):
        return
    splash_file(setup)
    if setup.choices["LOGIN_STYLE"] == "2000":
        branding(setup)
        setup.run(
            "env",
            "QT_QPA_PLATFORM=offscreen",
            "python3",
            setup.repo / "bin/chicago95-shutdown",
            "--status-banner",
            directory / "brand-banner.png",
        )


# --- the look's colours, in every toolkit that draws them ---


def color_scheme(setup):
    setup.run("plasma-apply-colorscheme", gtk_theme_name(setup.choices), to_log=True)


def face_colors(setup):
    """The 2000 look: warm grey face and its selection colour."""
    choices = setup.choices
    if not choices["FACE"]:
        return
    for group in ("Colors:Window", "Colors:Button", "Colors:Header", "Colors:Complementary"):
        setup.kconf("kdeglobals", group, "BackgroundNormal", choices["FACE"])
    setup.kconf("kdeglobals", "Colors:Selection", "BackgroundNormal", choices["SELECTION"])
    if choices["WIDGET_STYLE"] != "aero":  # 2000's inactive title text is the face colour
        setup.kconf("kdeglobals", "WM", "inactiveForeground", choices["FACE"])


def gtk_palette(setup):
    if setup.choices["WIDGET_STYLE"] == "classic" and home_path(setup, ".themes/Chicago95").is_dir():
        setup.run("python3", setup.repo / "lib/gtk_palette.py")


def rendered_menus_qss(setup, source):
    """The menus stylesheet with this home's paths, the look's face and selection, and the measured row heights."""
    choices = setup.choices
    scale, style = choices.get("SCALE", "1"), choices.get("WIDGET_STYLE", "classic")
    lines = Path(source).read_text().replace("@HOME@", str(setup.home)).splitlines(keepends=True)
    if style == "luna" and re.fullmatch(r"1\.250*", scale):
        lines = [line.replace("height: 21px;", "height: 17px;", 1) for line in lines]
    if style != "classic":
        return "".join(lines)
    rgb = r"([0-9]{1,3},){2}[0-9]{1,3}"
    if re.fullmatch(rgb, choices["FACE"]):
        lines = [line.replace("#C0C0C0", f"rgb({choices['FACE']})") for line in lines]
    if re.fullmatch(rgb, choices["SELECTION"]):
        lines = [line.replace("#000080", f"rgb({choices['SELECTION']})") for line in lines]
    row_height = ""
    if re.fullmatch(r"1\.250*", scale):
        row_height = "17" if choices["LOOK"] in ("2000", "2001") else "16"
    elif choices["LOOK"] == "1995" and re.fullmatch(r"1(\.0+)?", scale):
        row_height = "17"
    if row_height:  # the measured Windows menus use a shorter row than Qt's Windows style
        lines += [f"QMenu::item {{ height: {row_height}px; padding: 0 12px 0 3px; }}\n", "QMenu::icon { left: 2px; }\n"]
    return "".join(lines)


def shell_menu(setup):
    """plasmashell's menus in the widgets' style; it restarts only when they changed."""
    if setup.flags.get("SHELL_MENU_DONE") == "1":
        return
    setup.flag("SHELL_MENU_DONE")
    drop_in = home_path(setup, ".config/systemd/user/plasma-plasmashell.service.d/chicago95-menus.conf")
    installed_qss = home_path(setup, ".local/share/chicago95/plasmashell-menus.qss")
    menus_qss = setup.repo / "data/plasmashell-menus.qss"
    style = setup.choices.get("WIDGET_STYLE", "classic")
    if style == "aero":
        menus_qss = setup.repo / "aero/plasma-style/menus.qss"
        for art in ("menu-selection", "menu-gutter", "menu-arrow"):
            installed_art = home_path(setup, f".local/share/chicago95/images/aero-{art}.svg")
            if setup.differs(setup.repo / f"aero/plasma-style/{art}.svg", installed_art):
                setup.flag("SHELL_CHANGED")
            setup.put_file(setup.repo / f"aero/plasma-style/{art}.svg", installed_art)
    elif style == "luna":
        menus_qss = setup.repo / "data/plasmashell-menus-luna.qss"
    rendered = rendered_menus_qss(setup, menus_qss)
    menus_differ = not installed_qss.is_file() or installed_qss.read_text() != rendered
    if menus_differ or setup.differs(
        setup.repo / "config/systemd/plasma-plasmashell.service.d-chicago95-menus.conf", drop_in
    ):
        setup.flag("SHELL_CHANGED")
    setup.put_file(menus_qss, installed_qss)
    if setup.dry_run:
        setup.log(f"  would: render_menus_qss -i {installed_qss}")
    else:
        installed_qss.write_text(rendered)
    setup.put_file(
        setup.repo / "luna/images/menu-arrow.svg", home_path(setup, ".local/share/chicago95/images/menu-arrow.svg")
    )
    setup.put_file(
        setup.repo / "luna/images/menu-arrow-selected.svg",
        home_path(setup, ".local/share/chicago95/images/menu-arrow-selected.svg"),
    )
    setup.put_file(setup.repo / "config/systemd/plasma-plasmashell.service.d-chicago95-menus.conf", drop_in)


def wine_prefixes(setup):
    """Every prefix of the installed Wine in the home (~/.wine, ~/.wine-*, ~/Games/*): a folder with a registry next to
    its C: drive. A prefix made by another Wine would be "updated" on its first run here; Wine tells by the prefix's
    .update-timestamp, its wine.inf's time ("disable" turns updates off). Steam's Proton prefixes lie deeper."""
    wine = shutil.which("wine")
    if not wine:
        return []
    inf = Path(os.path.realpath(wine)).parent / "../share/wine/wine.inf"
    inf_time = str(int(inf.stat().st_mtime)) if inf.exists() else ""
    found = setup.output_of("find", setup.home, "-maxdepth", "4", "-name", "system.reg", "-not", "-path", "*/.cache/*")
    prefixes = []
    for registry in sorted(found.splitlines()):
        prefix = Path(registry).parent
        stamp_file = prefix / ".update-timestamp"
        stamp = (
            stamp_file.read_text().splitlines()[0].replace("\r", "")
            if stamp_file.is_file() and stamp_file.read_text()
            else ""
        )
        if (prefix / "drive_c").is_dir() and stamp in ("disable", inf_time):
            prefixes.append(prefix)
    return prefixes


def wine(setup):
    """Wine's classic controls in the look's colours, its own visual theme off (lib/wine_look.py)."""
    prefixes = wine_prefixes(setup)
    if not prefixes:
        return
    registry = home_path(setup, ".local/share/chicago95/wine-look.reg")
    setup.run("mkdir", "-p", registry.parent)
    setup.run("python3", setup.repo / "lib/wine_look.py", registry)
    setup.record(registry)
    for prefix in prefixes:
        if not setup.run("env", f"WINEPREFIX={prefix}", "WINEDEBUG=-all", "wine", "regedit", registry, to_log=True):
            setup.log(f"  Wine failed in {prefix}; it keeps its own settings")
        setup.show_copy("(Wine controls in the look's colours)", prefix / "user.reg")


def firefox(setup):
    """Firefox's controls in the look: its userChrome.css imports chicago95-controls.css."""
    profile = setup.choices["FIREFOX_PROFILE"]
    if not profile:
        return
    chrome, style = Path(profile) / "chrome", setup.choices["WIDGET_STYLE"]
    user_chrome, controls = chrome / "userChrome.css", chrome / "chicago95-controls.css"
    importing = '@import url("chicago95-controls.css");'
    setup.backup(user_chrome)
    if setup.dry_run:
        setup.log(f"  would: draw Firefox's controls in the look from {user_chrome}")
        return
    chrome.mkdir(parents=True, exist_ok=True)
    kept = [
        line for line in (user_chrome.read_text().splitlines() if user_chrome.exists() else []) if line != importing
    ]
    user_chrome.write_text("".join(f"{line}\n" for line in ([] if style == "luna" else [importing]) + kept))
    if style == "aero":
        setup.put_file(setup.repo / "aero/firefox-controls.css", controls)
    elif style != "classic":
        controls.unlink(missing_ok=True)
    else:
        setup.execute("python3", setup.repo / "lib/firefox_chrome.py", controls)
        setup.record(controls)
    setup.record(user_chrome)
    setup.show_copy("(Firefox's controls in the look)", user_chrome)


def colors(setup):
    """The look's face and selection, in every toolkit that draws them."""
    if setup.flags.get("LOOK_STEP_DONE") == "1":
        return
    color_scheme(setup)
    face_colors(setup)
    gtk_palette(setup)
    shell_menu(setup)
    if setup.choices["WIDGET_STYLE"] == "classic":
        wine(setup)
    firefox(setup)
    clippy_restart(setup)
    setup.flag("START_MENU_CHANGED")


# --- title bars ---


def rgb(color):
    return ",".join(str(int(color[index : index + 2], 16)) for index in (1, 3, 5))


def title_values(setup):
    """The colour scheme holds the title colours; System Settings > Colors can change them later, and
    chicago95-colors.path redraws the decoration whenever it does."""
    active, inactive = setup.choices.get("TITLE_ACTIVE", "#000080"), setup.choices.get("TITLE_INACTIVE", "#808080")
    setup.kconf("kdeglobals", "WM", "activeBackground", rgb(active.split(",")[0]))
    setup.kconf("kdeglobals", "WM", "activeBlend", rgb(active.split(",")[-1]))
    setup.kconf("kdeglobals", "WM", "inactiveBackground", rgb(inactive.split(",")[0]))
    setup.kconf("kdeglobals", "WM", "inactiveBlend", rgb(inactive.split(",")[-1]))


def title_bars_redraw(setup):
    setup.run("python3", home_path(setup, ".local/bin/chicago95-sync-colors"), "--force", to_log=True)
    choices = setup.choices
    setup.show_copy(
        f"(title bars: active {choices.get('TITLE_ACTIVE', '#000080')}, inactive {choices.get('TITLE_INACTIVE', '#808080')})",
        home_path(setup, ".local/share/aurorae/themes/Chicago95/decoration.svg"),
    )


ZOOM_CAPTIONS = {  # the travelling caption's speed in device pixels per millisecond, and how it ends
    "1995:classic": {"ClassicStripSpeed": "4.4", "palette": "start"},
    "1998:classic": {
        "ClassicStripSpeed": "3",
        "ClassicStripMaxMs": "300",
        "palette": "start",
        "InstantMaximize": "true",
    },
    "2000:classic": {"ClassicStripSpeed": "3.1", "palette": "gradient"},
    "2001:classic": {"ClassicStripSpeed": "3.3", "palette": "gradient", "InstantMaximize": "true"},
}


def zoom_titlebar(setup):
    """The title bar zoom effect draws the look's caption: Luna's strip, or the classic gradient at the original's speed."""
    choices, effect = setup.choices, f"Effect-{CHICAGO95_ZOOM}"
    luna = choices["DECORATION"] == "luna"
    setup.kconf("kwinrc", effect, "TitleBarHeight", "30" if luna else "--delete")
    setup.kconf("kwinrc", effect, "LunaTitleStrip", "true" if luna else "--delete")
    active = choices.get("TITLE_ACTIVE", "#000080")
    caption = ZOOM_CAPTIONS.get(f"{choices['LOOK']}:{choices['DECORATION']}", {})
    palette = {"start": active.split(",")[0], "gradient": f"{active.split(',')[0]},{active.split(',')[-1]}"}
    setup.kconf("kwinrc", effect, "ClassicStripSpeed", caption.get("ClassicStripSpeed", "--delete"))
    setup.kconf("kwinrc", effect, "ClassicStripMaxMs", caption.get("ClassicStripMaxMs", "--delete"))
    setup.kconf("kwinrc", effect, "ClassicStripPalette", palette.get(caption.get("palette"), "--delete"))
    # The native clients stay in place during the caption motion.
    setup.kconf("kwinrc", effect, "InstantMaximize", "true" if luna else caption.get("InstantMaximize", "--delete"))


def plasma_style_drawing(setup):
    """The Plasma styles' artwork as plasmashell would load it: it keeps what it has loaded until it restarts."""
    styles = home_path(setup, ".local/share/plasma/desktoptheme")
    return (
        sorted((str(path), path.read_bytes()) for path in styles.glob("Chicago95*/**/*.svg")) if styles.is_dir() else []
    )


def title_colors(setup):
    if setup.flags.get("LOOK_STEP_DONE") == "1":
        return
    title_values(setup)
    zoom_titlebar(setup)
    if not installed(setup, home_path(setup, ".local/bin/chicago95-sync-colors")):
        return
    drawn = plasma_style_drawing(setup)
    title_bars_redraw(setup)
    if drawn != plasma_style_drawing(setup):
        setup.flag("SHELL_CHANGED")


# --- animations: setup/animations.conf lists each event, its choices and the KWin effects they turn on ---


def animations_table(setup):
    rows = [line.split("|") for line in (setup.repo / "setup/animations.conf").read_text().splitlines()]
    return [row for row in rows if row and row[0] in ("EVENT", "CHOICE")]


def effects_in_category(setup, category):
    """Installed KWin effects of an exclusive category, by id."""
    if not category:
        return []
    found = []
    for folder in (home_path(setup, ".local/share/kwin/effects"), Path("/usr/share/kwin/effects")):
        for metadata in sorted(folder.glob("*/metadata.json")):
            if re.search(rf'"X-KWin-Exclusive-Category": *"{re.escape(category)}"', metadata.read_text()):
                found.append(metadata.parent.name)
    for metadata in sorted(KWIN_BUILTIN_EFFECTS.glob("*.json")):
        if re.search(rf'"exclusiveGroup": *"{re.escape(category)}"', metadata.read_text()):
            found.append(metadata.stem)
    return found


def choice_effects(table, event, value):
    """The effects a choice turns on; any other value is an effect's id."""
    listed = [row[4] for row in table if row[0] == "CHOICE" and row[1] == event and row[2] == value]
    return listed[0].split() if listed else [value]


def event_effects(setup, table, event):
    """Every effect the event's choices name, and the installed ones of its category."""
    named = [token for row in table if row[0] == "CHOICE" and row[1] == event for token in row[4].split()]
    category = next((row[3] for row in table if row[0] == "EVENT" and row[1] == event and row[3] != "-"), "")
    return named + effects_in_category(setup, category)


def animations(setup):
    """The saved animation choices into KWin, KDE's speed and our own tools; unset events stay as they are."""
    choices, table = setup.choices, animations_table(setup)
    if "look" not in setup.environment.get("COMPONENTS", "").split():
        zoom_titlebar(setup)
    managed, chosen = [], set()
    for event in (row[1] for row in table if row[0] == "EVENT"):
        value = choices[event]
        if not value and choices["LOOK"] == "aero" and event in ("ANIM_MINIMIZE", "ANIM_MAXIMIZE"):
            value = "aero"
        if not value:
            continue
        if event == "ANIM_SPEED":
            setup.kconf("kdeglobals", "KDE", "AnimationDurationFactor", value)
            continue
        if event in ("ANIM_MENUS", "ANIM_NOTIFICATIONS", "ANIM_TASKBAR"):
            setup.kconf("chicago95rc", "Animations", event, value)
        managed += [token for token in event_effects(setup, table, event) if token not in managed]
        chosen |= set(choice_effects(table, event, value))
    if "better_wobblywindows" in chosen:
        setup.kconf("kwinrc", "Effect-better_wobblywindows", "EmbeddedDXBlur", "true")
        setup.kconf("kwinrc", "Effect-better_wobblywindows", "EmbeddedDXBlurApiOnly", "false")
    switched = {}
    for token in managed:
        effect = token.split("/")[0]
        if effect in switched:
            continue
        switched[effect] = "true" if any(key.split("/")[0] == effect for key in chosen) else "false"
        setup.kconf("kwinrc", "Plugins", f"{effect}Enabled", switched[effect])
    for token in (token for token in managed if "/" in token):
        effect, option = token.split("/", 1)
        setup.kconf("kwinrc", f"Effect-{effect}", option, "true" if token in chosen else "false")
    zoom_enabled = (
        switched.get(CHICAGO95_ZOOM)
        or setup.output_of(
            "kreadconfig6",
            "--file",
            "kwinrc",
            "--group",
            "Plugins",
            "--key",
            f"{CHICAGO95_ZOOM}Enabled",
            "--default",
            "false",
        ).strip()
    )
    if zoom_enabled == "true":  # a running scripted effect keeps the schema and code it was loaded with
        setup.kwin_reconfigure()
        for method in ("unloadEffect", "loadEffect"):
            setup.run(
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.kde.KWin",
                "--object-path",
                "/Effects",
                "--method",
                f"org.kde.kwin.Effects.{method}",
                CHICAGO95_ZOOM,
                quiet=True,
            )


# --- what the session needs once the appliers are done ---


def current_aero_decoration(setup):
    theme = setup.output_of(
        "kreadconfig6", "--file", "kwinrc", "--group", "org.kde.kdecoration2", "--key", "theme"
    ).strip()
    return theme if theme in ("__aurorae__svg__Chicago95Aero", "org.chicago95.aero") else ""


def frame_glass(setup):
    """The Aero frame drawn for KWin's glass (NATIVE_GLASS=true) or for its plain blur."""
    svg = "decoration-native.svg" if setup.choices["NATIVE_GLASS"] == "true" else "decoration.svg"
    source = setup.repo / f"aero/aurorae/theme/{svg}"
    frame = home_path(setup, ".local/share/aurorae/themes/Chicago95Aero/decoration.svg")
    if not same_file(source, frame):
        setup.put_file(source, frame)
        setup.flag("AERO_FRAME_CHANGED")


def effects_call(setup, method, effect):
    return setup.output_of(
        "gdbus",
        "call",
        "--session",
        "--dest",
        "org.kde.KWin",
        "--object-path",
        "/Effects",
        "--method",
        f"org.kde.kwin.Effects.{method}",
        effect,
    ).strip()


def refresh_glass_effect(setup):
    """KWin loads the glass the settings chose and drops the other; the plain frame returns when it cannot."""
    native = setup.succeeds(
        "kreadconfig6",
        "--file",
        "kwinrc",
        "--group",
        "Plugins",
        "--key",
        "aeroglassblurEnabled",
        "--type",
        "bool",
        "--default",
        "false",
    )
    target, previous = ("aeroglassblur", "blur") if native else ("blur", "aeroglassblur")
    effects_call(setup, "unloadEffect", previous)
    if effects_call(setup, "isEffectLoaded", target) == "(true,)":
        return
    if effects_call(setup, "loadEffect", target) != "(true,)":
        effects_call(setup, "loadEffect", previous)
        setup.status(f"KWin could not activate {target} in this session. Check the effect after signing in again.")
        if target == "aeroglassblur" and current_aero_decoration(setup):
            setup.choices["NATIVE_GLASS"] = "false"
            frame_glass(setup)


def reload_caption_decoration(setup, theme):
    """KWin can retain Aurorae's QML and rasterized SVGs while the same plugin stays loaded: the decoration is
    recreated by switching to Breeze and back, without restarting the compositor."""
    if setup.dry_run or not setup.environment.get("DBUS_SESSION_BUS_ADDRESS"):
        return
    plugins = setup.output_of("qtpaths6", "--plugin-dir").strip()
    if not plugins or not Path(plugins, "org.kde.kdecoration3/org.kde.breeze.so").is_file():
        return
    group = ("--file", "kwinrc", "--group", "org.kde.kdecoration2")
    try:
        setup.execute("kwriteconfig6", *group, "--key", "library", "org.kde.breeze")
        setup.execute("kwriteconfig6", *group, "--key", "theme", "Breeze")
        setup.kwin_reconfigure()
    finally:
        setup.execute("kwriteconfig6", *group, "--key", "library", "org.kde.kwin.aurorae")
        setup.execute("kwriteconfig6", *group, "--key", "theme", theme)
        setup.kwin_reconfigure()


def finish(setup):
    """KWin always rereads its settings; plasmashell restarts only when something it loads changed."""
    flags = setup.flags
    if flags.get("SHELL_CHANGED") == "1":
        caches = (".cache/plasmashell/qmlcache", ".cache/ksvg-elements", ".cache/plasma_theme_Chicago95.kcache")
        setup.run("rm", "-rf", *(home_path(setup, cache) for cache in caches))
    setup.run("systemctl", "--user", "daemon-reload")
    setup.kwin_reconfigure()
    if setup.dry_run or setup.choices["IN_PLASMA"] != "1":
        return
    if flags.get("GLASS_EFFECT_CHANGED") == "1":
        refresh_glass_effect(setup)
    theme = flags.get("CAPTION_RELOAD") or (flags.get("AERO_FRAME_CHANGED") == "1" and current_aero_decoration(setup))
    if theme:
        reload_caption_decoration(setup, theme)
    if setup.succeeds("systemctl", "--user", "is-enabled", "chicago95-notifyd.service"):
        setup.execute("systemctl", "--user", "restart", "chicago95-notifyd.service", quiet=True)
    if flags.get("SHELL_CHANGED") == "1":
        # Last, and one queued job: Setup may run inside plasmashell's service (started from the Control Panel,
        # opened from the taskbar), and stopping it stops Setup too; systemd finishes the job anyway.
        setup.execute("systemctl", "--user", "restart", "--no-block", "plasma-plasmashell.service", quiet=True)


def start_menu_restart(setup):
    """The menu stays resident; a new look must replace the running copy."""
    if setup.dry_run:
        return
    pid_file = Path(setup.environment.get("XDG_RUNTIME_DIR", "/tmp")) / "chicago95-startmenu.pid"
    if pid_file.is_file():
        setup.execute("kill", "-TERM", pid_file.read_text().strip(), quiet=True)
    setup.execute("systemctl", "--user", "start", "app-chicago95\\x2dstartmenu@autostart.service", quiet=True)


APPLIERS = {
    function.__name__: function
    for function in (
        mouse,
        pointer,
        sound_theme,
        sounds,
        screensaver,
        clippy_autostart,
        clippy_restart,
        start_logo,
        start_menu,
        look_rc,
        branding,
        place_start_menu,
        place_run_dialog,
        place_notifications,
        place_clippy,
        window_rules,
        shortcuts,
        switcher_settings,
        switcher,
        taskbar,
        panel,
        background,
        desktop_icons,
        lockscreen_settings,
        splash_file,
        splash_settings,
        color_scheme,
        face_colors,
        gtk_palette,
        shell_menu,
        wine,
        firefox,
        colors,
        title_values,
        title_bars_redraw,
        zoom_titlebar,
        title_colors,
        animations,
        frame_glass,
        finish,
        start_menu_restart,
    )
}
