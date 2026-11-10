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
        rows = [start_menu(startmenu, app, style, scratch), shut_down(shutdown, app, style)]
        if style == "2000":
            rows.append(loading_2000(app, scratch))
        compose(f"{style}: originals (left) and Chicago95 for Plasma (right)", rows, output / f"report-{style}.png")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "report"))
