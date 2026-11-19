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
import tempfile
from collections import namedtuple
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parent.parent
SCREEN = (640, 480)
SCREENS = {"2001": (800, 600), "luna": (800, 600)}  # the originals' sizes, where they are not 640x480
ICON_COLOUR = (0, 200, 0)  # in none of the originals: not the title bars, not the faces
ICON_SIZE = 16
TEST_ICON = "c95-test-square"
TEST_ICON_SIZES = (16, 22, 24, 32, 48)
CHICAGO95_SRC = Path(os.environ.get("CHICAGO95_SRC", Path.home() / "src/Chicago95"))

# Each original's desktop: its windows in the taskbar's order (title, toolkit, the frame's box
# (left, top, right, bottom) inclusive, or "minimized", and optionally a program ID that windows share to be
# one program), the active one, its Quick Launch entries and
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
    "2001": dict(  # XP Classic: three inactive windows (the Start menu was open), no Quick Launch, the clock alone
        windows=[
            ("My Computer", "x11", (105, 30, 562, 269)),
            ("Local Disk (C:)", "gtk4", (259, 142, 595, 429)),
            ("Program Files", "qt", (349, 235, 708, 552)),
        ],
        active="",
        launchers=0,
        tray=0,
    ),
    "luna": dict(  # xprunning.png: three task buttons, the last (Windows XP Tour) active
        windows=[
            ("Control Panel", "gtk4", "minimized"),
            ("My Computer", "x11", "minimized"),
            ("Windows XP Tour", "qt", (100, 50, 699, 453)),  # xpnotepad.png's size
        ],
        active="Windows XP Tour",
        launchers=0,
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
start_plasmashell() {{
    local command
    command=$(grep -m1 '^ExecStart=/' \\
        "$REPO/config/systemd/plasma-plasmashell.service.d-chicago95-menus.conf" | cut -d= -f2-)
    ${{command//%h/$HOME}} >"$1" 2>&1 &
}}
# Screenshots until two in a row match: Plasma settles its widgets on timers, later when the machine is busy. Each
# waits for Plasma to answer first: its answer comes from the thread that paints it, so two matching shots cannot
# be one frame held while it loads a widget (a classic Start button before the style's own one is drawn).
screenshot_settled() {{
    local shots="${{1%.png}}-shot"
    for shot in 1 2 3 4 5 6 7 8 9 10; do
        evaluate 'print("ready")' >/dev/null 2>&1
        spectacle --background --nonotify --fullscreen --output "$shots-$shot.png" >"$WORK/spectacle.log" 2>&1
        if [ "$shot" -gt 1 ] && cmp -s "$shots-$shot.png" "$shots-$((shot - 1)).png"; then break; fi
        sleep 1
    done
    cp "$shots-$shot.png" "$1"
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
    """--look={look} --screen={screen}@1{taskbar_style}{settings} >"$WORK/install.log" 2>&1 </dev/null
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
# The taskbar Setup just restarted, before anyone touches it: its settings arrive after it is up.
sleep 4
screenshot_settled "$WORK/setup-screen.png"
kill %1; wait
"""
)

DESKTOP = (
    COMMON + """
# The second session, as after logging in again: everything Setup wrote is read from the start.
kbuildsycoca6 >/dev/null 2>&1   # the windows' programs are written into the home Setup left
{windows_before_plasma}
start_plasmashell "$WORK/plasma.log"
wait_for_plasma
python3 "$WORK/tray.py" {icon} {tray} >"$WORK/tray.log" 2>&1 &
{windows_after_plasma}
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
if ({active} === "") workspace.activeWindow = null;
SCRIPT
kwin_script "$WORK/arrange.js" arrange
sleep 4
{pointer_command}
screenshot_settled "$WORK/screen.png"
gdbus call --session --dest org.kde.KWin --object-path /Effects --method org.freedesktop.DBus.Properties.Get \
    org.kde.kwin.Effects loadedEffects >"$WORK/effects.txt" 2>&1
"""
)


def right_click_at(x, y):
    return (f"move:{x},{y}", "wait:0.5", "click:right", "wait:1.5")


CLICK = (300, 120)
MENU_OPENERS = {
    "desktop": lambda look: right_click_at(CLICK[0], CLICK[1]),
    "task": lambda look: right_click_at(150, screen_of(look)[1] - 12),
    "start": lambda look: right_click_at(30, screen_of(look)[1] - 12),
}


def hover_steps(point):
    x, y = point
    return (f"move:{x - 12},{y - 6}", "wait:0.3", f"move:{x - 4},{y - 2}", "wait:0.3", f"move:{x},{y}", "wait:1")


def menu_steps(look, kind, hover=None):
    """pointer_steps that open the desktop's, a task button's or the Start button's context menu in look, and
    then move the pointer to hover (x, y) when given."""
    return (*MENU_OPENERS[kind](look), *(hover_steps(hover) if hover else ()))


ICON_SET_CLONES = ("Windows-XP", "Win98SE", "ClassicOS-2000-Icons")  # setup/steps.sh install_icon_pack


def work_folder(name, memory=Path("/dev/shm")):
    """A new folder for a session's home and logs: its path short (Wayland's socket path stops at 108 bytes), and in
    memory where the machine has such a filesystem. Setup syncs every setting it writes and copies thousands of
    files, which stalls for seconds at a time on a busy disk."""
    parent = memory if os.access(memory, os.W_OK) else Path("/tmp")
    return Path(tempfile.mkdtemp(prefix=f"c95-{name}-", dir=parent))


def screen_of(look):
    return SCREENS.get(look, SCREEN)


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
    # The icon sets Setup would otherwise clone from GitHub in every session, and nothing else of ~/src.
    (home / "src").mkdir(exist_ok=True)
    for clone in ICON_SET_CLONES:
        if (real / "src" / clone).is_dir():
            (home / "src" / clone).symlink_to(real / "src" / clone)


def enforce_screenshot(path, session):
    """A session KWin's time limit cut off, or one that crashed, must not pass as a half-built desktop."""
    if not path.exists():
        raise RuntimeError(f"{session} session took no screenshot ({path.name}); see the logs in {path.parent}")


def stub(folder, *programs):
    folder.mkdir(parents=True, exist_ok=True)
    for program in programs:
        (folder / program).write_text("#!/bin/sh\nexit 0\n")
        (folder / program).chmod(0o755)


def window_commands(work, applications, windows):
    commands = []
    for index, (title, toolkit, _place, *program_id) in enumerate(windows):
        name = program_id[0] if program_id else f"org.chicago95.test.window{index}"  # windows sharing one: one program
        if toolkit == "x11":
            desktop_file(applications, name, title, TEST_ICON, "StartupWMClass=Xmessage\n")
            program = f"xmessage -title {quote(title)} -geometry 200x100 {quote(title)}"
        else:
            desktop_file(applications, name, title, TEST_ICON)
            program = f'python3 "$WORK/{toolkit}.py" {name} {quote(title)}'
        commands.append(f'{program} >"$WORK/window-{index}.log" 2>&1 &\nsleep 1.5')
    return "\n".join(commands)


def run_session(work, script, environment, screen, xwayland=False, scale=1):
    """Run script in a nested KWin whose logical screen is screen, at scale device pixels per logical pixel."""
    (work / script.name).chmod(0o755)
    if scale != 1:
        # --scale only enlarges a virtual output; the output's own scale comes from KScreen.
        scaled = work / f"scaled-{script.name}"
        scaled.write_text(f"#!/bin/sh\nkscreen-doctor output.Virtual-0.scale.{scale} >/dev/null 2>&1\nexec {script}\n")
        scaled.chmod(0o755)
        script = scaled
    command = [
        "timeout",
        "240",
        "dbus-run-session",
        "kwin_wayland",
        "--virtual",
        "--width",
        str(screen[0] * scale),
        "--height",
        str(screen[1] * scale),
        "--no-lockscreen",
        *(["--xwayland"] if xwayland else []),
        "--exit-with-session",
        str(script),
    ]
    with open(work / f"kwin-{script.stem}.log", "w") as log:
        subprocess.run(command, env=environment, cwd=work, stdout=log, stderr=subprocess.STDOUT, check=False)


SETUP_OPTIONS = (
    "tray_applets",
    "hidden_applets",
    "tasks_config",
    "taskbar_style",
    "settings",
    "components",
    "launchers",
    "screen",
)
Installed = namedtuple("Installed", "look work screen environment")


def frozen(value):
    return tuple(frozen(item) for item in value) if isinstance(value, (list, tuple)) else value


def setup_key(look, options):
    """What Setup's session depends on, of a desktop's options: desktops that differ only in what is then shown
    (the windows, the tray's icons, the pointer) share one Setup."""
    return (look, *sorted((name, frozen(value)) for name, value in options.items() if name in SETUP_OPTIONS))


def install(
    look,
    work,
    tray_applets=(),
    hidden_applets=(),
    tasks_config=(),
    taskbar_style=None,
    settings=(),
    components=(),
    launchers=None,
    screen=None,
):
    """Runs Setup's session for a look in work (see work_folder) and keeps a copy of the home it leaves, for
    show() to start each desktop from. tray_applets are Plasma applets shown in the tray (such as
    org.kde.plasma.notifications), hidden_applets ones behind its "show hidden icons" arrow; tasks_config (key,
    value) pairs for the taskbar widget's settings; taskbar_style the taskbar Setup installs whatever the look
    (classic, luna or aero); settings (key, value) pairs Setup applies with its animations step too; components
    further Setup components to install (such as desktop); launchers replaces the number of Quick Launch entries;
    screen (width, height) replaces the look's own size, 640x480 or SCREENS'."""
    work = Path(work)
    screen_size = screen or screen_of(look)
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
    shutil.copy(REPO / "tests/eis_pointer.py", work / "eis_pointer.py")

    applications = home / ".local/share/applications"
    applications.mkdir(parents=True, exist_ok=True)
    launcher_files = [
        desktop_file(applications, f"c95-launcher-{index}", f"Launcher {index}", TEST_ICON).as_uri()
        for index in range(CONTENT[look]["launchers"] if launchers is None else launchers)
    ]
    (work / "setup.sh").write_text(
        SETUP.format(
            look=look,
            screen="x".join(map(str, screen_size)),
            taskbar_style=f" --taskbar-style={taskbar_style}" if taskbar_style else "",
            launchers=json.dumps(launcher_files),
            tray_applets=json.dumps(list(tray_applets)),
            hidden_applets=json.dumps(list(hidden_applets)),
            tasks_config=json.dumps(dict(tasks_config)),
            components="".join(f",{component}" for component in (*(["animations"] if settings else []), *components)),
            settings=f" --settings={work / 'chosen.conf'}" if settings else "",
        )
    )
    environment = {
        "SETUP_OS_RELEASE": "/dev/null",
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
    run_session(work, work / "setup.sh", environment, screen_size)
    enforce_screenshot(work / "setup-screen.png", "Setup's")
    shutil.copytree(home, work / HOME_AFTER_SETUP, symlinks=True)
    return Installed(look, work, screen_size, environment)


HOME_AFTER_SETUP = "home-after-setup"
DESKTOP_LEAVINGS = ("screen.png", "screen-shot-*.png", "effects.txt")


def show(installed, windows=None, windows_first=False, tray_icons=None, pointer_steps=()):
    """Runs the desktop's session, as after logging in again, from the home Setup left; returns the screenshot.
    windows replaces the look's own windows (an empty list: none, for the desktop behind them); windows_first
    opens them before Plasma starts, as a login that restores the last session does; tray_icons is the number of
    the test's icons in the tray, beside the original's; pointer_steps (see eis_pointer.py) drive the pointer
    before the screenshot, to open a context menu (see MENU_OPENERS) and hover one of its rows.
    The screenshot's info holds KWin's loaded effects, its log, and Setup's own session's screenshot
    ("setup_screen": the taskbar right after Setup restarted Plasma, before anyone touched it)."""
    look, work, screen_size, environment = installed
    home = work / "home"
    shutil.rmtree(home)
    shutil.copytree(work / HOME_AFTER_SETUP, home, symlinks=True)
    for leaving in DESKTOP_LEAVINGS:  # an earlier desktop's in this folder: a session that dies must show nothing
        for path in work.glob(leaving):
            path.unlink()

    content = CONTENT[look]
    if windows is not None:
        shown = [title for title, _toolkit, place, *_program in windows if place != "minimized"]
        content = {**content, "windows": list(windows), "active": shown[0] if shown else ""}  # minimized: not active
    places = {title: place for title, _toolkit, place, *_program in content["windows"]}
    window_script = window_commands(work, home / ".local/share/applications", content["windows"])
    (work / "desktop.sh").write_text(
        DESKTOP.format(
            icon=TEST_ICON,
            tray=content["tray"] if tray_icons is None else tray_icons,
            windows_before_plasma=window_script if windows_first else "",
            windows_after_plasma="" if windows_first else window_script,
            places=json.dumps(places),
            active=json.dumps(content["active"]),
            pointer_command=(
                f'python3 "$WORK/eis_pointer.py" {" ".join(quote(step) for step in pointer_steps)} '
                '>"$WORK/pointer.log" 2>&1; sleep 1'
                if pointer_steps
                else ""
            ),
        )
    )
    run_session(work, work / "desktop.sh", environment, screen_size, xwayland=True)
    enforce_screenshot(work / "screen.png", "the desktop's")
    image = Image.open(work / "screen.png").convert("RGB")
    effects, kwin_log = work / "effects.txt", work / "kwin-desktop.log"
    image.info["loaded_effects"] = effects.read_text() if effects.exists() else ""
    image.info["kwin_log"] = kwin_log.read_text(errors="replace") if kwin_log.exists() else ""
    image.info["setup_screen"] = Image.open(work / "setup-screen.png").convert("RGB")
    return image


def split_options(options):
    setup = {name: value for name, value in options.items() if name in SETUP_OPTIONS}
    return setup, {name: value for name, value in options.items() if name not in SETUP_OPTIONS}


def desktop_session(look, work, **options):
    """Runs both sessions for a look in work, with install()'s and show()'s options; returns the screenshot."""
    setup_options, desktop_options = split_options(options)
    return show(install(look, work, **setup_options), **desktop_options)


class Desktops:
    """Desktops by their options, each drawn once, with one Setup for those that share its options (setup_key)."""

    def __init__(self):
        self.screens, self.installed = {}, {}

    def __call__(self, look, **options):
        key = (look, *sorted((name, frozen(value)) for name, value in options.items()))
        if key not in self.screens:
            setup_options, desktop_options = split_options(options)
            shared = setup_key(look, options)
            if shared not in self.installed:
                self.installed[shared] = install(look, work_folder(look), **setup_options)
            self.screens[key] = show(self.installed[shared], **desktop_options)
        return self.screens[key]

    def remove_folders(self):
        for installed in self.installed.values():
            shutil.rmtree(installed.work, ignore_errors=True)


def quote(text):
    return "'" + text.replace("'", "'\\''") + "'"
