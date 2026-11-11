"""Chicago95 as Plasma and KWin draw it, for tests that compare the desktop with the originals.

Setup (install.sh) installs the base theme, the look, the taskbar and the fonts into a throwaway home,
in a first headless session; a second one, like logging in again, runs KWin and plasmashell at the
originals' 640x480 and 1x scale with the windows, Quick Launch entries and tray icons each original
shows. The windows come from each toolkit (Qt, GTK 3, GTK 4, X11 through Xwayland) and sit where the
original's windows are, or are minimized. Every icon is a themed one whose sizes are each a solid
square of that size, so where an icon is drawn, and at which size, can be measured exactly. The result
is a full-screen screenshot.

Nothing touches the user's session: the home, the D-Bus session and the compositor are the test's own
(systemctl and pkill are stubbed). The UI font, the icon themes and the Chicago95 checkout are linked
in from the user's home and read only.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SCREEN = (640, 480)
ICON_COLOUR = (0, 200, 0)  # in none of the originals: not the title bars, not the faces
ICON_SIZE = 16
TEST_ICON = "c95-test-square"
TEST_ICON_SIZES = (16, 22, 24, 32, 48)
CHICAGO95_SRC = Path(os.environ.get("CHICAGO95_SRC", Path.home() / "src/Chicago95"))

# Each original's desktop: its windows in the taskbar's order (title, toolkit, and the frame's box
# (left, top, right, bottom) inclusive, or "minimized"), the active one, its Quick Launch entries and
# its tray icons.
CONTENT = {
    "1995": dict(
        windows=[
            ("Find: Files named", "gtk4", "minimized"),
            ("My Computer", "x11", "minimized"),
            ("Windows", "gtk3", (213, 207, 636, 444)),
            ("My Folder", "qt", (130, 94, 581, 284)),
        ],
        active="Windows",
        launchers=0,
        tray=1,
    ),
    "1998": dict(
        windows=[("WinPopup", "gtk3", "minimized"), ("Untitled - Notepad", "qt", (6, 6, 410, 364))],
        active="Untitled - Notepad",
        launchers=4,
        tray=2,
    ),
    "2000": dict(
        windows=[
            ("Administrative Tools", "x11", (280, 155, 627, 433)),
            ("Computer Management", "gtk4", (2, 2, 534, 392)),
        ],
        active="Administrative Tools",
        launchers=3,
        tray=1,
    ),
}
REQUIRED_PROGRAMS = (
    "kwin_wayland",
    "plasmashell",
    "spectacle",
    "dbus-run-session",
    "kbuildsycoca6",
    "gdbus",
    "Xwayland",
    "xmessage",
)

PROGRAMS = {
    "qt": """
import sys
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QWidget
app = QApplication(sys.argv)
QGuiApplication.setDesktopFileName(sys.argv[1])
window = QWidget()
window.setWindowTitle(sys.argv[2])
window.show()
app.exec()
""",
    "gtk3": """
import sys
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk
GLib.set_prgname(sys.argv[1])
window = Gtk.Window(title=sys.argv[2])
window.connect("destroy", Gtk.main_quit)
window.show_all()
Gtk.main()
""",
    "gtk4": """
import sys
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
app = Gtk.Application(application_id=sys.argv[1])
app.connect("activate", lambda app: Gtk.ApplicationWindow(application=app, title=sys.argv[2]).present())
app.run([])
""",
}

TRAY_PROGRAM = """
import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
app = QApplication(sys.argv)
icons = []
for index in range(int(sys.argv[2])):
    icon = QSystemTrayIcon(QIcon.fromTheme(sys.argv[1]))
    icon.setToolTip(f"tray {index}")
    icon.show()
    icons.append(icon)
app.exec()
"""

COMMON = (
    """#!/bin/bash
set -u
cd "$REPO"
evaluate() {{ gdbus call --session --dest org.kde.plasmashell --object-path /PlasmaShell """
    """--method org.kde.PlasmaShell.evaluateScript "$1"; }}
wait_for_plasma() {{ for _ in $(seq 60); do evaluate 'print("ready")' >/dev/null 2>&1 && return; sleep 0.5; done; }}
kwin_script() {{
    local id
    id=$(gdbus call --session --dest org.kde.KWin --object-path /Scripting """
    """--method org.kde.kwin.Scripting.loadScript "$1" "$2" | grep -o '[0-9]\\+')
    gdbus call --session --dest org.kde.KWin --object-path /Scripting/Script$id """
    """--method org.kde.kwin.Script.run >/dev/null
}}
"""
)

SETUP = (
    COMMON + """
# The first session: Setup, as on a desktop that runs Plasma.
kbuildsycoca6 >/dev/null 2>&1
plasmashell --no-respawn >"$WORK/plasma-setup.log" 2>&1 &
wait_for_plasma
TMPDIR="$WORK" ./install.sh --plain --yes --components=base,look,taskbar,fonts{components} """
    """--look={look} --screen=640x480@1{settings} >"$WORK/install.log" 2>&1 </dev/null
# The test's launchers; the tray with the given applets only (none: the test's icons only).
evaluate 'panels().forEach(panel => {{
    panel.widgets("org.chicago95.tasks").forEach(widget => {{
        widget.currentConfigGroup = ["General"]; widget.writeConfig("launchers", {launchers});
        Object.entries({tasks_config}).forEach(([key, value]) => widget.writeConfig(key, value));
    }});
    panel.widgets("org.kde.plasma.systemtray").forEach(widget => {{
        widget.currentConfigGroup = ["General"]; widget.writeConfig("extraItems", """
    """{tray_applets}.concat({hidden_applets}));
        widget.writeConfig("shownItems", {tray_applets}); widget.writeConfig("hiddenItems", {hidden_applets});
    }});
}})' >>"$WORK/install.log" 2>&1
kill %1; wait
"""
)

DESKTOP = (
    COMMON + """
# The second session, as after logging in again: everything Setup wrote is read from the start.
plasmashell --no-respawn >"$WORK/plasma.log" 2>&1 &
wait_for_plasma
python3 "$WORK/tray.py" {icon} {tray} >"$WORK/tray.log" 2>&1 &
{windows}
sleep 2
cat >"$WORK/arrange.js" <<'SCRIPT'
const places = {places};
for (const window of workspace.windowList()) {{
    const place = places[window.caption];
    if (place === "minimized") window.minimized = true;
    else if (place) window.frameGeometry = """
    """{{x: place[0], y: place[1], width: place[2] - place[0] + 1, height: place[3] - place[1] + 1}};
}}
for (const window of workspace.windowList()) {{ if (window.caption === {active}) workspace.activeWindow = window; }}
SCRIPT
kwin_script "$WORK/arrange.js" arrange
sleep 4
# Screenshots until two in a row match: Plasma settles its widgets on timers, later when the machine is busy.
for shot in 1 2 3 4 5 6 7 8 9 10; do
    spectacle --background --nonotify --fullscreen --output "$WORK/shot-$shot.png" >"$WORK/spectacle.log" 2>&1
    if [ "$shot" -gt 1 ] && cmp -s "$WORK/shot-$shot.png" "$WORK/shot-$((shot - 1)).png"; then break; fi
    sleep 1
done
cp "$WORK/shot-$shot.png" "$WORK/screen.png"
gdbus call --session --dest org.kde.KWin --object-path /Effects --method org.freedesktop.DBus.Properties.Get \
    org.kde.kwin.Effects loadedEffects >"$WORK/effects.txt" 2>&1
"""
)


def missing_programs():
    return [program for program in REQUIRED_PROGRAMS if not shutil.which(program)]


def desktop_file(folder, name, title, icon, extra=""):
    path = folder / f"{name}.desktop"
    path.write_text(f"[Desktop Entry]\nType=Application\nName={title}\nIcon={icon}\nExec=true\n{extra}")
    return path


def link_children(source, target, copy=()):
    """target as a folder of links to source's entries (the named ones copied): Setup can write into
    target without reaching the user's files."""
    target.mkdir(parents=True, exist_ok=True)
    for entry in source.iterdir() if source.exists() else ():
        if entry.name in copy:
            shutil.copy(entry, target / entry.name)
        elif entry.is_file() or entry.name != "Chicago95":
            (target / entry.name).symlink_to(entry.resolve())


def link_user_assets(home):
    """The UI font, the icon themes and the Chicago95 checkout: the user's, linked, never written."""
    real = Path.home()
    link_children(real / ".local/share/fonts", home / ".local/share/fonts")
    link_children(real / ".local/share/icons", home / ".local/share/icons")
    link_children(real / ".icons/Chicago95", home / ".icons/Chicago95", copy=("index.theme",))
    (home / ".themes").mkdir(exist_ok=True)
    (home / ".themes/Chicago95").symlink_to(CHICAGO95_SRC / "Theme/Chicago95")


def stub(folder, *programs):
    folder.mkdir(parents=True, exist_ok=True)
    for program in programs:
        (folder / program).write_text("#!/bin/sh\nexit 0\n")
        (folder / program).chmod(0o755)


def window_commands(work, applications, windows):
    commands = []
    for index, (title, toolkit, _place) in enumerate(windows):
        name = f"org.chicago95.test.window{index}"
        if toolkit == "x11":
            desktop_file(applications, name, title, TEST_ICON, "StartupWMClass=Xmessage\n")
            program = f"xmessage -title {quote(title)} -geometry 200x100 {quote(title)}"
        else:
            desktop_file(applications, name, title, TEST_ICON)
            program = f'python3 "$WORK/{toolkit}.py" {name} {quote(title)}'
        commands.append(f'{program} >"$WORK/window-{index}.log" 2>&1 &\nsleep 1.5')
    return "\n".join(commands)


def run_session(work, script, environment, xwayland=False, screen=SCREEN):
    (work / script.name).chmod(0o755)
    command = [
        "timeout",
        "240",
        "dbus-run-session",
        "kwin_wayland",
        "--virtual",
        "--width",
        str(screen[0]),
        "--height",
        str(screen[1]),
        "--no-lockscreen",
        *(["--xwayland"] if xwayland else []),
        "--exit-with-session",
        str(script),
    ]
    with open(work / f"kwin-{script.stem}.log", "w") as log:
        subprocess.run(command, env=environment, cwd=work, stdout=log, stderr=subprocess.STDOUT, check=False)


def desktop_session(look, work, tray_applets=(), tray_icons=None, hidden_applets=(), tasks_config=(), settings=()):
    """Runs both sessions for a look in work (a short path: Wayland's socket path is limited to 108
    bytes); returns the 640x480 screenshot. tray_applets are Plasma applets shown in the tray (such
    as org.kde.plasma.notifications), hidden_applets ones behind its "show hidden icons" arrow, and
    tray_icons the number of the test's icons there, beside the original's; tasks_config (key, value) pairs
    for the taskbar widget's settings; settings (key, value) pairs Setup applies with its animations step too.
    The screenshot's info holds KWin's loaded effects and its log."""
    work = Path(work)
    home, runtime = work / "home", work / "run"
    for folder in (home / ".config", runtime):
        folder.mkdir(parents=True, exist_ok=True)
    runtime.chmod(0o700)
    stub(work / "stubs", "systemctl", "pkill")
    link_user_assets(home)
    (home / ".config/plasma-welcomerc").write_text("[General]\nShouldShow=false\nLastSeenVersion=99.0.0\n")
    for size in TEST_ICON_SIZES:
        folder = work / f"data/icons/hicolor/{size}x{size}/apps"
        folder.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (size, size), ICON_COLOUR + (255,)).save(folder / f"{TEST_ICON}.png")
    for toolkit, program in PROGRAMS.items():
        (work / f"{toolkit}.py").write_text(program)
    (work / "tray.py").write_text(TRAY_PROGRAM)

    content = CONTENT[look]
    applications = home / ".local/share/applications"
    applications.mkdir(parents=True, exist_ok=True)
    launchers = [
        desktop_file(applications, f"c95-launcher-{index}", f"Launcher {index}", TEST_ICON).as_uri()
        for index in range(content["launchers"])
    ]
    places = {title: place for title, _toolkit, place in content["windows"]}
    (work / "setup.sh").write_text(
        SETUP.format(
            look=look,
            launchers=json.dumps(launchers),
            tray_applets=json.dumps(list(tray_applets)),
            hidden_applets=json.dumps(list(hidden_applets)),
            tasks_config=json.dumps(dict(tasks_config)),
            components=",animations" if settings else "",
            settings=f" --settings={work / 'chosen.conf'}" if settings else "",
        )
    )
    (work / "desktop.sh").write_text(
        DESKTOP.format(
            icon=TEST_ICON,
            tray=content["tray"] if tray_icons is None else tray_icons,
            windows=window_commands(work, applications, content["windows"]),
            places=json.dumps(places),
            active=json.dumps(content["active"]),
        )
    )
    environment = {
        "HOME": str(home),
        "PATH": f"{work / 'stubs'}:{os.environ['PATH']}",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "XDG_RUNTIME_DIR": str(runtime),
        "XDG_DATA_DIRS": f"{work / 'data'}:/usr/local/share:/usr/share",
        "XDG_CURRENT_DESKTOP": "KDE",
        "XDG_SESSION_TYPE": "wayland",
        "CHICAGO95_SRC": str(CHICAGO95_SRC),
        "WORK": str(work),
        "REPO": str(REPO),
        "QT_QPA_PLATFORMTHEME": "kde",
        "QT_FORCE_STDERR_LOGGING": "1",
    }
    (work / "chosen.conf").write_text("".join(f"{key}={value}\n" for key, value in settings))
    run_session(work, work / "setup.sh", environment)
    run_session(work, work / "desktop.sh", environment, xwayland=True)
    screen = work / "screen.png"
    if not screen.exists():
        raise RuntimeError(f"the Plasma session took no screenshot; see the logs in {work}")
    image = Image.open(screen).convert("RGB")
    effects, kwin_log = work / "effects.txt", work / "kwin-desktop.log"
    image.info["loaded_effects"] = effects.read_text() if effects.exists() else ""
    image.info["kwin_log"] = kwin_log.read_text(errors="replace") if kwin_log.exists() else ""
    return image


def quote(text):
    return "'" + text.replace("'", "'\\''") + "'"
