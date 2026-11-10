#!/usr/bin/env python3
"""One comparison image per OS: each original (left) beside our render (right), with labels.

    python3 tests/render_report.py [OUTPUT_DIR]     writes report-1995.png, report-1998.png, report-2000.png

It renders with the same helpers and crops as the reference tests, so the report shows exactly what
the tests compare. Thumbnail originals (half size) are shown enlarged to full size.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="chicago95-report-config-")
TESTS = Path(__file__).resolve().parent
sys.path[:0] = [str(TESTS), str(TESTS.parent / "lib")]

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from conftest import REPO, load_script  # noqa: E402
from reference import LOOK_2000_KDEGLOBALS, installed_look, qimage_to_pil, render_start_menu, screenshot  # noqa: E402

BACKGROUND, INK, GAP = (255, 255, 255), (0, 0, 0), 16
DEFAULT_LOGO = REPO / "plasmoids/org.chicago95.start/contents/images/logo-flag.png"  # what a default install shows
# The 2000 look's default; Setup downloads it (setup/fetch-waving-flag.py), so the report uses it when present.
WAVING_FLAG = Path.home() / ".local/share/chicago95/waving-flag.png"
MENU_SETTINGS = {
    "1995": ("[StartMenu]\nbannerText=Windows95\n", ""),
    "1998": ("[StartMenu]\nstyle=1998\nbannerText=Windows98\nbannerTextColor=#FFFFFF\nbannerNumberColor=#FFFFFF\n"
             "bannerBackground=#00007B,#00007B@95,#0000B0@70,#0000F8@45,#0000EE@20,#0000A9@0\n", ""),
    "2000": ("[StartMenu]\nstyle=2000\nbannerText=Windows 2000 Professional\nbannerTextColor=#FFFFFF\nbannerNumberColor=#FFFFFF\n"
             "bannerBackground=#000000,#000021@200,#000081@120,#0000B2@70,#0000E3@45,#0000F3@20,#0000FF@0\n", LOOK_2000_KDEGLOBALS),
}


def start_menu(startmenu, app, style, scratch):
    settings, kdeglobals = MENU_SETTINGS[style]
    extra = ("New Office Document", "Open Office Document", "Windows Update") if style == "2000" else ()
    crops = {"1995": ("win95startmenu", (2, 217, 166, 456)), "1998": ("win98start", (2, 0, 216, 456)),
             "2000": ("w2kstartmenu", (2, 113, 206, 456))}
    name, box = crops[style]
    ours = render_start_menu(startmenu, app, scratch / f"menu-{style}", settings, kdeglobals,
                             active=0 if style == "1995" else None, extra_top=extra)
    return "Start menu", screenshot(name).crop(box), ours


def shut_down(shutdown, app, style):
    logo = WAVING_FLAG if style == "2000" and WAVING_FLAG.exists() else DEFAULT_LOGO
    look = {"style": style, "bannerText": "Chicago95", "osName": "Chicago95", "osCompany": "KDE",
            "edition": "Professional", "osLogo": str(logo), "companyLogo": ""}
    kdeglobals = LOOK_2000_KDEGLOBALS if style == "2000" else ""
    with installed_look(app, f"[StartMenu]\nstyle={style}\n", kdeglobals):
        dialog = shutdown.ShutDownDialog(look)
        dialog.show()
        app.processEvents()
        ours = qimage_to_pil(dialog.grab().toImage())
        dialog.close()
    if style == "2000":
        original = screenshot("w2kshutdown").crop((115, 91, 524, 337))
    else:
        name, box = {"1995": ("win95shutdownsm", (74, 60, 246, 180)), "1998": ("win98shutsm", (80, 46, 240, 152))}[style]
        original = screenshot(name).crop(box)
        original = original.resize((original.width * 2, original.height * 2), Image.NEAREST)
    return "Shut Down (thumbnail original enlarged)" if style != "2000" else "Shut Down", original, ours


def loading_2000(app, scratch):
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtQuick import QQuickView
    splash = scratch / "splash"
    logo = WAVING_FLAG if WAVING_FLAG.exists() else DEFAULT_LOGO
    shutil.copytree(REPO / "splash/chicago95.splashscreen/contents/splash", splash, dirs_exist_ok=True)
    (splash / "settings.js").write_text(
        f'.pragma library\nvar style = "2000"\nvar brandText = "Chicago95"\nvar brandLogo = "{logo}"\n'
        'var edition = "Professional"\nvar tagline = "Built on Linux Technology"\nvar company = "KDE"\n'
        'var companyLogo = ""\nvar loadingText = "Starting up..."\n'
        'var footer = "Chicago95 for KDE Plasma"\nvar picture = ""\n')
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(640, 480)
    view.setSource(QUrl.fromLocalFile(str(splash / "Splash.qml")))
    view.rootObject().setProperty("stage", 3)
    view.show()
    QTimer.singleShot(300, app.quit)
    app.exec()
    ours = qimage_to_pil(view.grabWindow())
    view.close()
    return "Loading screen", screenshot("w2kboot"), ours


def login_2000(shutdown, app, scratch):
    from login_theme import render_login
    logo = WAVING_FLAG if WAVING_FLAG.exists() else DEFAULT_LOGO
    look = {"style": "2000", "bannerText": "Chicago95", "osName": "Chicago95", "osCompany": "KDE", "edition": "Professional",
            "osLogo": str(logo), "companyLogo": "", "tagline": "Built on Linux Technology"}
    shutdown.render_login_banner(look, scratch / "login-banner.png")
    with installed_look(app, "[StartMenu]\nstyle=2000\n", LOOK_2000_KDEGLOBALS):
        ours = render_login(app, scratch / "login", banner=scratch / "login-banner.png", show_options=True, loginStyle="2000",
                            titleActive="#0A246A,#A6CAF0", host_name="CHICAGO95")
    dialog = (111, 74, 528, 330)
    return "Log on", screenshot("w2klogon").crop(dialog), ours.crop(dialog)


def windows(style, scratch):
    """Each window of the style's screenshots, its frame drawn by our decoration at the original's size."""
    from aurorae_model import Window, build_theme
    from test_window_reference import WINDOWS
    theme = build_theme(scratch / f"aurorae-{style}", style)
    rows = []
    for window_id, (look, name, (left, top, right, bottom), active, caption, _covered) in WINDOWS.items():
        if look != style or "file browser" in window_id:
            continue
        original = screenshot(name).crop((left, top, right + 1, bottom + 1))
        rows.append((f"Window, {'active' if active else 'inactive'}", original,
                     Window(theme, original.width, original.height, active, caption).render()))
    return rows


def taskbar(style, app, scratch):
    """The original's taskbar, and ours: the panel, Start button, separators, task buttons and tray box
    drawn by our files at the original's places (icons and labels are the programs' own, left out)."""
    import subprocess
    from aurorae_model import LOOKS
    from framesvg import render_frame
    from test_taskbar_reference import BUTTONS, BUTTON_HEIGHT, BUTTON_TOP, SEPARATORS, TRAYS, render_on_strip, start_button
    from test_taskbar_reference import taskbar as original_taskbar
    colours = LOOKS[style]
    plasma_style = scratch / f"plasma-style-{style}"
    subprocess.run([sys.executable, str(REPO / "plasma-style/make_chicago95_plasmastyle.py"), "--out", str(plasma_style),
                    *[f"--{key}={colours[key]}" for key in ("face", "light", "shadow", "dark")]], check=True, capture_output=True)
    original = original_taskbar(style)
    ours = render_frame(plasma_style / "widgets/panel-background.svg", "", original.width, original.height, borders={"top"})
    (start_left, start_right), tasks = BUTTONS[style]
    (scratch / f"strip-{style}").mkdir(exist_ok=True)
    button, _ = start_button(app, style, scratch / f"strip-{style}")
    ours.paste(button.crop((0, 2, start_right + 1, original.height)), (0, 2))
    for etched, _next in SEPARATORS.get(style, []):
        separator, width = render_on_strip(app, scratch / f"strip-{style}", "org.chicago95.grip", "Separator", etched - 2, colours["face"], {})
        ours.paste(separator.crop((etched - 2, 2, etched - 2 + width, original.height)), (etched - 2, 2))
    for left, right, pressed in tasks:
        frame = render_frame(plasma_style / "widgets/tasks.svg", "focus" if pressed else "normal", right - left + 1, BUTTON_HEIGHT)
        ours.paste(frame, (left, BUTTON_TOP))
    tray_left, tray_right = TRAYS[style]
    tray, _ = render_on_strip(app, scratch / f"strip-{style}", "org.chicago95.trayframe", "TrayBox", tray_left, colours["face"], {},
                              width=tray_right - tray_left + 1)
    ours.paste(tray.crop((tray_left, 2, tray_right + 1, original.height)), (tray_left, 2))
    zoom = lambda image: image.resize((image.width * 2, image.height * 2), Image.NEAREST)
    return "Taskbar (enlarged)", zoom(original.crop((0, 0, 320, original.height))), zoom(ours.crop((0, 0, 320, original.height))), \
        ("Taskbar, right half (enlarged)", zoom(original.crop((320, 0, 640, original.height))), zoom(ours.crop((320, 0, 640, original.height))))


def label_font():
    for path in ("/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, 16)
    return ImageFont.load_default()


def compose(title, rows, path):
    font = label_font()
    width = max(o.width + u.width for _, o, u in rows) + GAP * 3
    height = 40 + sum(max(o.height, u.height) + 34 + GAP for _, o, u in rows)
    sheet = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((GAP, 10), title, fill=INK, font=font)
    y = 40
    for label, original, ours in rows:
        draw.text((GAP, y), f"{label}: original", fill=INK, font=font)
        draw.text((GAP * 2 + original.width, y), "ours", fill=INK, font=font)
        sheet.paste(original, (GAP, y + 24))
        sheet.paste(ours, (GAP * 2 + original.width, y + 24))
        y += max(original.height, ours.height) + 34 + GAP
    sheet.save(path)
    print("wrote", path)


def main(output):
    from PySide6.QtWidgets import QApplication
    import chicago95ui  # noqa: F401  sets the platform before the application exists
    app = QApplication.instance() or QApplication([])
    startmenu, shutdown = load_script("chicago95-startmenu"), load_script("chicago95-shutdown")
    output.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="chicago95-report-"))
    for style in ("1995", "1998", "2000"):
        (scratch / f"menu-{style}").mkdir()
        bar = taskbar(style, app, scratch)
        rows = [start_menu(startmenu, app, style, scratch), shut_down(shutdown, app, style), *windows(style, scratch),
                bar[:3], bar[3]]
        if style == "2000":
            rows += [loading_2000(app, scratch), login_2000(shutdown, app, scratch)]
        compose(f"{style}: originals (left) and Chicago95 for Plasma (right)", rows, output / f"report-{style}.png")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "report"))
