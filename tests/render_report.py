#!/usr/bin/env python3
"""The comparison report: every detail the reference tests compare, the original's beside ours.

    python3 tests/render_report.py [OUTPUT_DIR]

writes, for 1995, 1998 and 2000:
- showcase-<look>.jpg, to show people: component by component (desktop, taskbar, windows, Start menu,
  Shut Down, and for 2000 the loading and log-on screens) the original beside ours;
- report-<look>-<section>.png (and .txt, the counts): every detail the tests compare, one per row: the
  original, ours and their difference (red where a pixel differs, the original faded elsewhere),
  enlarged together. What is not ours to compare (the programs' content in the windows, icons, the
  clock's time) is hatched alike in both. Our banners carry the original's wording, as in the tests.

The taskbar and the windows come from the real desktop (tests/plasma_session.py: Setup, KWin and
plasmashell in a headless session, the test's icons solid squares) when KWin and Plasma are installed;
otherwise from the decoration and the taskbar parts drawn the way KWin and Plasma draw them.
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
from reference import LOOK_2000_KDEGLOBALS, close, installed_look, qimage_to_pil, render_start_menu, screenshot  # noqa: E402

BACKGROUND, INK, DIFFERENT, GAP = (255, 255, 255), (0, 0, 0), (255, 0, 0), 12
ROW_HEIGHT, COLUMN_WIDTH, MAX_ZOOM = 168, 560, 8
DEFAULT_LOGO = REPO / "plasmoids/org.chicago95.start/contents/images/logo-flag-16.png"  # what a default install shows
# The 2000 look's default; Setup downloads it (setup/fetch-waving-flag.py), so the report uses it when present.
WAVING_FLAG = Path.home() / ".local/share/chicago95/waving-flag.png"
MENU_SETTINGS = {
    "1995": ("[StartMenu]\nbannerText=Windows95\n", ""),
    "1998": ("[StartMenu]\nstyle=1998\nbannerText=Windows98\nbannerTextColor=#FFFFFF\nbannerNumberColor=#FFFFFF\n"
             "bannerBackground=#00007B,#00007B@95,#0000B0@70,#0000F8@45,#0000EE@20,#0000A9@0\n", ""),
    "2000": ("[StartMenu]\nstyle=2000\nbannerText=Windows 2000 Professional\nbannerTextColor=#FFFFFF\nbannerNumberColor=#FFFFFF\n"
             "bannerBackground=#000000,#000021@200,#000081@120,#0000B2@70,#0000E3@45,#0000F3@20,#0000FF@0\n", LOOK_2000_KDEGLOBALS),
}


HATCH, HATCH_BACKGROUND = (200, 200, 200), (240, 240, 240)


def hatched(image, masks):
    """A copy with the boxes hatched: what is not ours to compare (the programs' content, icons, the time)."""
    image = image.copy()
    draw = ImageDraw.Draw(image)
    for left, top, right, bottom in masks:
        draw.rectangle((left, top, right - 1, bottom - 1), fill=HATCH_BACKGROUND)
        for start in range(left - (bottom - top), right, 4):
            draw.line((start, bottom - 1, start + (bottom - top), top), fill=HATCH)
        draw.rectangle((left, top, right - 1, bottom - 1), outline=HATCH)
    return image


def details(original, ours, boxes, prefix="", masks=()):
    """[(label, the original's crop, our crop)] for boxes {label: box, or (the original's box, ours)}; the
    masks (boxes in both images) are hatched alike, so they show as equal."""
    original, ours = hatched(original, masks), hatched(ours, masks)
    rows = []
    for label, box in boxes.items():
        original_box, our_box = box if isinstance(box[0], tuple) else (box, box)
        rows.append((prefix + label, original.crop(original_box), ours.crop(our_box)))
    return rows


# --- taskbar -------------------------------------------------------------------------------------

def taskbar_boxes(look):
    from test_plasma_taskbar_reference import ETCHED_LINES, QUICK_LAUNCH, TRAY_ICONS
    from test_taskbar_reference import BUTTONS, HEIGHT, TRAYS
    (start_left, start_right), tasks = BUTTONS[look]
    boxes = {"left half": (0, 0, 320, HEIGHT), "right half": (320, 0, 640, HEIGHT), "Start button": (0, 2, start_right + 4, HEIGHT)}
    for index, x in enumerate(ETCHED_LINES.get(look, []), 1):
        boxes[f"separator {index}"] = (x - 4, 2, x + 13, HEIGHT)
    for index, x in enumerate(QUICK_LAUNCH.get(look, []), 1):
        boxes[f"Quick Launch cell {index}"] = (x - 5, 2, x + 21, HEIGHT)
    for index, (left, right, pressed) in enumerate(tasks, 1):
        boxes[f"task button {index}{' (pressed)' if pressed else ''}"] = (left - 3, 2, right + 4, HEIGHT)
        boxes[f"task button {index}: icon and label"] = (left - 2, 2, left + 56, HEIGHT)
    for index, ((_l, right, _p), (left, _r, _q)) in enumerate(zip(tasks, tasks[1:]), 1):
        boxes[f"gap between task buttons {index} and {index + 1}"] = (right - 8, 2, left + 9, HEIGHT)
    tray_left, _tray_right = TRAYS[look]
    boxes["tray box"] = (tray_left - 3, 2, 640, HEIGHT)
    for index, x in enumerate(TRAY_ICONS[look], 1):
        boxes[f"tray icon {index}"] = (x - 3, 3, x + 19, HEIGHT - 1)
    boxes["clock"] = (TRAY_ICONS[look][-1] + 16, 2, 640, HEIGHT)
    return boxes


def model_taskbar(look, app, scratch):
    """Ours without Plasma: the panel, Start button, separators, task buttons and tray box drawn by our
    files at the original's places (icons, labels and the clock are the programs' own, left out)."""
    import subprocess
    from aurorae_model import LOOKS
    from framesvg import render_frame
    from test_taskbar_reference import BUTTONS, BUTTON_HEIGHT, BUTTON_TOP, SEPARATORS, TRAYS, render_on_strip, start_button
    from test_taskbar_reference import taskbar as original_taskbar
    colours = LOOKS[look]
    plasma_style = scratch / f"plasma-style-{look}"
    shutil.copytree(REPO / "plasma-style/theme", plasma_style)
    subprocess.run([sys.executable, str(REPO / "plasma-style/make_chicago95_plasmastyle.py"), "--out", str(plasma_style),
                    *[f"--{key}={colours[key]}" for key in ("face", "light", "shadow", "dark")]], check=True, capture_output=True)
    original = original_taskbar(look)
    ours = render_frame(plasma_style / "widgets/panel-background.svg", "", original.width, original.height, borders={"top"})
    (_start_left, start_right), tasks = BUTTONS[look]
    strip = scratch / f"strip-{look}"
    strip.mkdir(exist_ok=True)
    button, _ = start_button(app, look, strip)
    ours.paste(button.crop((0, 2, start_right + 1, original.height)), (0, 2))
    for etched, _next in SEPARATORS.get(look, []):
        separator, width = render_on_strip(app, strip, "org.chicago95.tasks", "Separator", etched - 2, colours["face"], {})
        ours.paste(separator.crop((etched - 2, 2, etched - 2 + width, original.height)), (etched - 2, 2))
    for left, right, pressed in tasks:
        frame = render_frame(plasma_style / "widgets/tasks.svg", "focus" if pressed else "normal", right - left + 1, BUTTON_HEIGHT)
        ours.paste(frame, (left, BUTTON_TOP))
    tray_left, tray_right = TRAYS[look]
    tray, _ = render_on_strip(app, strip, "org.chicago95.trayframe", "TrayBox", tray_left, colours["face"], {},
                              width=tray_right - tray_left + 1)
    ours.paste(tray.crop((tray_left, 2, tray_right + 1, original.height)), (tray_left, 2))
    return ours


def taskbar_masks(look):
    """The icons (the programs' own; ours are the test's squares, placed by the tests) and the clock's
    lettering (another time)."""
    from test_plasma_taskbar_reference import QUICK_LAUNCH, TRAY_ICONS
    from test_taskbar_reference import BUTTONS
    icon = lambda x, y=7: (x, y, x + 16, y + 16)
    masks = [icon(x) for x in QUICK_LAUNCH.get(look, [])] + [icon(x) for x in TRAY_ICONS[look]]
    masks += [icon(left + 4, 7 + pressed) for left, _right, pressed in BUTTONS[look][1]]
    masks.append((TRAY_ICONS[look][-1] + 18, 6, 636, 24))
    return masks


def taskbar_details(look, desktop, app, scratch):
    from test_taskbar_reference import HEIGHT
    from test_taskbar_reference import taskbar as original_taskbar
    ours = desktop.crop((0, desktop.height - HEIGHT, desktop.width, desktop.height)) if desktop else model_taskbar(look, app, scratch)
    return details(original_taskbar(look), ours, taskbar_boxes(look), masks=taskbar_masks(look))


# --- windows -------------------------------------------------------------------------------------

def window_boxes(width, height):
    from test_window_reference import BORDER, TOP
    w, h = width, height
    boxes = {"whole": (0, 0, w, h), "title bar: icon and caption": (0, 0, min(w, 190), TOP + 4),
             "title bar: buttons": (w - 70, 0, w, TOP + 4)}
    for name, offset in (("close", 0), ("maximize", 18), ("minimize", 34)):
        left = w - 6 - 16 - offset
        boxes[f"{name} button"] = (left - 1, BORDER + 1, left + 17, BORDER + 17)
    boxes.update({"top-left corner": (0, 0, 14, 14), "top-right corner": (w - 14, 0, w, 14),
                  "bottom-left corner": (0, h - 14, 14, h), "bottom-right corner": (w - 14, h - 14, w, h),
                  "left edge": (0, h // 2 - 8, 14, h // 2 + 8), "bottom edge": (w // 2 - 8, h - 14, w // 2 + 8, h)})
    return boxes


def window_details(look, desktop, scratch):
    """Each window of the look's screenshots: ours on the real desktop (each from another toolkit) or
    drawn by our decoration at the original's size."""
    from aurorae_model import Window, build_theme
    from plasma_session import CONTENT
    from test_window_reference import WINDOWS
    theme = build_theme(scratch / f"aurorae-{look}", look)
    toolkits = {box: toolkit for _title, toolkit, box in CONTENT[look]["windows"]}
    rows = []
    from test_window_reference import BORDER, ICON, TOP
    for window_look, name, (left, top, right, bottom), active, caption, covered in WINDOWS.values():
        if window_look != look:
            continue
        original = screenshot(name).crop((left, top, right + 1, bottom + 1))
        toolkit = toolkits.get((left, top, right, bottom))
        if desktop and toolkit:
            ours, source = desktop.crop((left, top, right + 1, bottom + 1)), f"{toolkit} window on the desktop"
        else:
            ours, source = Window(theme, original.width, original.height, active, caption).render(), "our decoration"
        state = "active" if active else "inactive"
        w, h = original.size
        masks = [(BORDER, TOP, w - BORDER, h - BORDER), ICON]
        if covered:
            masks.append((covered[0] - left, covered[1] - top, covered[2] - left + 1, covered[3] - top + 1))
        rows += details(original, ours, window_boxes(w, h), f"{caption} ({state}; ours: {source}): ", masks)
    rows += dialog_button_details(look, theme)
    return rows


def dialog_button_details(look, theme):
    """The dialogs' caption buttons the window tests compare: 1995's help button pressed and its close
    button, 1998's disabled close button."""
    from aurorae_model import Window
    rows = []
    if look == "1995":
        original = screenshot("win95helpbutton")
        pressed = Window(theme, 200, 60, True, "", right="HX", pressed="H").render()
        rows.append(("dialog: help button pressed", original.crop((14, 7, 32, 23)), pressed.crop((200 - 6 - 18 - 16 - 1, 5, 200 - 6 - 18 + 1, 21))))
        plain = Window(theme, 200, 60, True, "", right="X").render()
        rows.append(("dialog: close button", original.crop((32, 7, 50, 23)), plain.crop((200 - 6 - 16 - 1, 5, 200 - 6 + 1, 21))))
    if look == "1998":
        disabled = Window(theme, 200, 60, True, "", right="X", disabled="X").render()
        rows.append(("alert: close button, disabled", screenshot("win98notepad").crop((502, 193, 520, 209)),
                     disabled.crop((200 - 6 - 16 - 1, 5, 200 - 6 + 1, 21))))
    return rows


# --- Start menu ----------------------------------------------------------------------------------

def start_menu_details(startmenu, app, look, scratch):
    from test_startmenu_icons_styles_reference import ROWS
    from test_startmenu_reference import ROW_TOPS
    settings, kdeglobals = MENU_SETTINGS[look]
    extra = ("New Office Document", "Open Office Document", "Windows Update") if look == "2000" else ()
    name, box = {"1995": ("win95startmenu", (2, 217, 166, 456)), "1998": ("win98start", (2, 0, 216, 456)),
                 "2000": ("w2kstartmenu", (2, 113, 206, 456))}[look]
    (scratch / f"menu-{look}").mkdir(exist_ok=True)
    ours = render_start_menu(startmenu, app, scratch / f"menu-{look}", settings, kdeglobals,
                             active={"1995": 0, "1998": 4, "2000": None}[look], extra_top=extra)
    original = screenshot(name).crop(box)
    height = min(original.height, ours.height)   # 1998's original has more entries above Programs
    boxes = {"whole": ((0, original.height - height, original.width, original.height), (0, ours.height - height, ours.width, ours.height)),
             "banner": ((0, 0, 26, original.height), (0, 0, 26, ours.height)),
             "bottom edge": ((0, original.height - 40, original.width, original.height), (0, ours.height - 40, ours.width, ours.height))}
    if look == "1995":
        names = ("Programs", "Documents", "Settings", "Find", "Help", "Run...", "Shut Down...")
        boxes.update({f"row: {label}": (0, top - 2, original.width, top + 34) for label, top in zip(names, ROW_TOPS)})
    else:
        rows, height, _active = ROWS[look]
        boxes.update({f"row: {label}": ((0, mine_top, original.width, mine_top + height), (0, our_top, ours.width, our_top + height))
                      for label, (mine_top, our_top) in rows.items()})
    return details(original, ours, boxes)


# --- Shut Down, loading and log-on screens -------------------------------------------------------

SHUT_DOWN_DIALOGS = {}   # look: our whole dialog, for the showcase


def shut_down_details(shutdown, app, look, scratch):
    from test_shutdown_reference import BANNER_LINES, BANNER_MARK
    logo = WAVING_FLAG if look == "2000" and WAVING_FLAG.exists() else DEFAULT_LOGO
    settings = {"style": look, "bannerText": "Windows 2000", "osName": "Windows 2000", "osCompany": "Microsoft",
                "edition": "Professional", "osLogo": str(logo), "companyLogo": ""}   # the original's wording
    import chicago95ui
    from aurorae_model import build_theme
    chicago95ui.DECORATION = str(build_theme(scratch / f"shutdown-aurorae-{look}", look))   # the look's close button
    kdeglobals = {"1995": "", "1998": "[WM]\nactiveBackground=0,0,128\nactiveBlend=16,132,208\n", "2000": LOOK_2000_KDEGLOBALS}[look]
    with installed_look(app, f"[StartMenu]\nstyle={look}\n", kdeglobals):
        dialog = shutdown.ShutDownDialog(settings)
        dialog.show()
        app.processEvents()
        ours = qimage_to_pil(dialog.grab().toImage())
        dialog.close()
    SHUT_DOWN_DIALOGS[look] = ours
    if look != "2000":
        return thumbnail_shut_down_details(look, ours)
    from test_shutdown_reference import BODY_2000, CLIENT_2000, DIALOG_2000
    whole = [("whole", screenshot("w2kshutdown").crop(DIALOG_2000), ours),
             ("title bar", screenshot("w2kshutdown").crop((DIALOG_2000[0], DIALOG_2000[1], DIALOG_2000[2], DIALOG_2000[1] + 22)), ours.crop((0, 0, ours.width, 22)))]
    original = screenshot("w2kshutdown").crop(CLIENT_2000)
    ours = ours.crop((*BODY_2000, BODY_2000[0] + original.width, BODY_2000[1] + original.height))
    boxes = {"banner mark": BANNER_MARK,
             **{f"banner: {line}": box for line, box in BANNER_LINES.items()},
             "question and dropdown": (0, 70, original.width, 180), "buttons": (0, 180, original.width, original.height)}
    return whole + details(original, ours, boxes)


def thumbnail_shut_down_details(look, dialog):
    """1995's and 1998's originals are half-size thumbnails: the dialog cut from it at its frame, beside
    ours (which draws its own frame and title) halved the way a thumbnail is made (each pixel the average
    of four)."""
    from test_shutdown_reference import thumbnail_dialog
    original = thumbnail_dialog(look)
    halved = dialog.resize((dialog.width // 2, dialog.height // 2), Image.BOX)
    w, h = original.size
    boxes = {"whole, at the thumbnail's half size": ((0, 0, w, h), (0, 0, halved.width, halved.height)),
             "title bar": (0, 0, w, 14), "question and options": (0, 13, w, h * 2 // 3), "buttons": (0, h * 2 // 3, w, h)}
    return details(original, halved, boxes)


def loading_details(app, scratch):
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtQuick import QQuickView
    from test_loading_screen_reference import COMPANY_LINE, CORNER, EDITION_LINE, LOADING_TEXT_BOX, MARK, NAME_LINE, TAGLINE_LINE
    splash = scratch / "splash"
    logo = WAVING_FLAG if WAVING_FLAG.exists() else DEFAULT_LOGO
    shutil.copytree(REPO / "splash/chicago95.splashscreen/contents/splash", splash, dirs_exist_ok=True)
    (splash / "settings.js").write_text(
        f'.pragma library\nvar style = "2000"\nvar brandText = "Windows 2000"\nvar brandLogo = "{logo}"\n'
        'var edition = "Professional"\nvar tagline = "Built on NT Technology"\nvar company = "Microsoft"\n'
        'var companyLogo = ""\nvar loadingText = "Starting up..."\n'
        'var footer = "Copyright © 1985-1999 Microsoft Corporation"\nvar picture = ""\n')   # the original's wording
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
    boxes = {"whole": (0, 0, 640, 480), "mark": MARK, "company": COMPANY_LINE, "name": NAME_LINE, "edition": EDITION_LINE,
             "tagline": TAGLINE_LINE, "corner": CORNER, "progress": (190, 425, 460, 455), "loading text": LOADING_TEXT_BOX}
    return details(screenshot("w2kboot"), ours, boxes)


def login_details(shutdown, app, scratch):
    from login_theme import render_login
    from test_login_reference import BANNER_LINES, DIALOG
    logo = WAVING_FLAG if WAVING_FLAG.exists() else DEFAULT_LOGO
    look = {"style": "2000", "bannerText": "Windows 2000", "osName": "Windows 2000", "osCompany": "Microsoft", "edition": "Professional",
            "osLogo": str(logo), "companyLogo": "", "tagline": "Built on NT Technology"}   # the original's wording
    shutdown.render_login_banner(look, scratch / "login-banner.png")
    with installed_look(app, "[StartMenu]\nstyle=2000\n", LOOK_2000_KDEGLOBALS):
        ours = render_login(app, scratch / "login", banner=scratch / "login-banner.png", show_options=True, loginStyle="2000",
                            titleActive="#0A246A,#A6CAF0", loginTitle="Log On to Windows")
    left, top, right, bottom = DIALOG
    boxes = {"whole": DIALOG, "title bar": (left, top, right, top + 22), "banner": (114, 96, 525, 189),
             **{f"banner: {line}": box for line, box in BANNER_LINES.items()},
             "fields": (left, 189, right, 282), "buttons": (left, 282, right, bottom)}
    return details(screenshot("w2klogon"), ours, boxes)


# --- the sheets ----------------------------------------------------------------------------------

def label_font(size=15):
    for path in ("/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def difference(original, ours):
    """Red where the pixels differ (beyond the screenshots' palette rounding), the original faded elsewhere."""
    width, height = max(original.width, ours.width), max(original.height, ours.height)
    padded = [Image.new("RGB", (width, height), BACKGROUND) for _ in range(2)]
    padded[0].paste(original)
    padded[1].paste(ours)
    result = Image.new("RGB", (width, height))
    for x in range(width):
        for y in range(height):
            a, b = padded[0].getpixel((x, y)), padded[1].getpixel((x, y))
            result.putpixel((x, y), (a[0] // 4 + 191, a[1] // 4 + 191, a[2] // 4 + 191) if close(a, b) else DIFFERENT)
    return result


def zoom_for(original, ours):
    width, height = max(original.width, ours.width), max(original.height, ours.height)
    return max(1, min(MAX_ZOOM, ROW_HEIGHT // height, COLUMN_WIDTH // width))


def compose(title, rows, path):
    font = label_font()
    prepared = []
    summary = []
    for label, original, ours in rows:
        zoom = zoom_for(original, ours)
        diff = difference(original, ours)
        differing = sum(1 for pixel in diff.getdata() if pixel == DIFFERENT)
        share = 100 * differing / (diff.width * diff.height)
        images = [image.resize((image.width * zoom, image.height * zoom), Image.NEAREST) for image in (original, ours, diff)]
        prepared.append((f"{label}: {differing} pixels differ ({share:.1f}%)" + (f", x{zoom}" if zoom > 1 else ""), images))
        summary.append(f"{differing:7d} {share:5.1f}%  {title}: {label}")
    width = max(sum(image.width for image in images) for _, images in prepared) + GAP * 4
    height = 44 + sum(max(image.height for image in images) + 30 + GAP for _, images in prepared)
    sheet = Image.new("RGB", (max(width, 900), height), BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((GAP, 12), f"{title}: original, ours, difference (red)", fill=INK, font=font)
    y = 44
    for label, images in prepared:
        draw.text((GAP, y), label, fill=INK, font=font)
        x = GAP
        for image in images:
            sheet.paste(image, (x, y + 22))
            x += image.width + GAP
        y += max(image.height for image in images) + 30 + GAP
    sheet.save(path)
    Path(path).with_suffix(".txt").write_text("\n".join(summary) + "\n")
    print("wrote", path)


# --- the showcase: one picture per OS, component by component --------------------------------------

SHOWCASE_WIDTH, SHOWCASE_BACKGROUND, CARD = 1400, (236, 236, 236), (255, 255, 255)
LOOK_NAMES = {"1995": "1995 look", "1998": "1998 look", "2000": "2000 look"}


def showcase_panels(look, desktop, sections, app, scratch, startmenu):
    """[(component, original, ours)]: the desktop, the taskbar, each window, the Start menu whole with the
    original's entries, the Shut Down dialog in our frame, and each screen whole."""
    from aurorae_model import Window, build_theme
    from plasma_session import CONTENT
    from test_taskbar_reference import HEIGHT, TASKBARS
    from test_taskbar_reference import taskbar as original_taskbar
    from test_window_reference import WINDOWS
    panels = []
    if desktop:
        panels.append(("Desktop (ours: the test's programs and icons)", screenshot(TASKBARS[look]), desktop))
    bar = desktop.crop((0, desktop.height - HEIGHT, desktop.width, desktop.height)) if desktop else model_taskbar(look, app, scratch)
    panels.append(("Taskbar", original_taskbar(look), bar))
    theme = build_theme(scratch / f"showcase-aurorae-{look}", look)
    toolkits = {box: toolkit for _title, toolkit, box in CONTENT[look]["windows"]}
    for window_look, name, (left, top, right, bottom), active, caption, _covered in WINDOWS.values():
        if window_look != look:
            continue
        original = screenshot(name).crop((left, top, right + 1, bottom + 1))
        toolkit = toolkits.get((left, top, right, bottom))
        if desktop and toolkit:
            ours, note = desktop.crop((left, top, right + 1, bottom + 1)), f"ours: a {toolkit.upper()} window, empty"
        else:
            ours, note = Window(theme, original.width, original.height, active, caption).render(), "ours: the frame alone"
        panels.append((f"Window, {'active' if active else 'inactive'} ({note})", original, ours))
    settings, kdeglobals = MENU_SETTINGS[look]
    menu_box = {"1995": ("win95startmenu", (2, 217, 166, 456)), "1998": ("win98start", (2, 0, 216, 456)),
                "2000": ("w2kstartmenu", (2, 113, 206, 456))}[look]
    (scratch / f"showcase-menu-{look}").mkdir(exist_ok=True)
    # Each original's own entries: 1995 had no Log Off; 2000's shows Office and Windows Update above.
    menu = render_start_menu(startmenu, app, scratch / f"showcase-menu-{look}", settings, kdeglobals,
                             without=() if look == "1998" else ("&Log Off...",), active={"1995": 0, "1998": 4, "2000": 4}[look],
                             extra_top=("New Office Document", "Open Office Document", "Windows Update") if look == "2000" else ())
    panels.append(("Start menu", screenshot(menu_box[0]).crop(menu_box[1]), menu))
    panels.append(("Shut Down", *shut_down_whole(look, sections)))
    for key, component in (("loading", "Loading screen"), ("logon", "Log on")):
        if key in sections:
            _label, original, ours = sections[key][1][0]   # each section's first row is the whole screen
            panels.append((component, original, ours))
    return panels


def shut_down_whole(look, sections):
    """The original dialog and ours, whole: 1995's and 1998's originals are half-size thumbnails,
    shown enlarged beside ours at full size."""
    if look == "2000":
        _label, original, ours = sections["shutdown"][1][0]
        return original, ours
    _label, original, _halved = sections["shutdown"][1][0]
    return original.resize((original.width * 2, original.height * 2), Image.NEAREST), SHUT_DOWN_DIALOGS[look]


def compose_showcase(title, panels, path):
    heading, caption = label_font(24), label_font(15)
    inner = SHOWCASE_WIDTH - 4 * GAP
    laid_out = []
    for component, original, ours in panels:
        width = max(original.width, ours.width)
        side_by_side = 2 * width + GAP <= inner
        zoom = max(1, min(3, (inner - GAP) // 2 // width)) if side_by_side else max(1, min(2, inner // width))
        images = [image.resize((image.width * zoom, image.height * zoom), Image.NEAREST) for image in (original, ours)]
        laid_out.append((component, side_by_side, zoom, images))
    height = 70
    for _component, side_by_side, _zoom, images in laid_out:
        body = max(image.height for image in images) + 24 if side_by_side else sum(image.height + 24 for image in images) + GAP
        height += 40 + body + 3 * GAP
    sheet = Image.new("RGB", (SHOWCASE_WIDTH, height), SHOWCASE_BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((2 * GAP, 20), title, fill=INK, font=heading)
    y = 70
    for component, side_by_side, zoom, images in laid_out:
        body = max(image.height for image in images) + 24 if side_by_side else sum(image.height + 24 for image in images) + GAP
        draw.rectangle((GAP, y, SHOWCASE_WIDTH - GAP, y + 40 + body + GAP), fill=CARD)
        draw.text((2 * GAP, y + 10), component + (f"  (enlarged x{zoom})" if zoom > 1 else ""), fill=INK, font=heading)
        x, top = 2 * GAP, y + 40
        for name, image in zip(("Original", "Chicago95 for Plasma"), images):
            draw.text((x, top), name, fill=(90, 90, 90), font=caption)
            sheet.paste(image, (x, top + 20))
            if side_by_side:
                x += image.width + 2 * GAP
            else:
                top += image.height + 24 + GAP // 2
        y += 40 + body + 3 * GAP
    sheet.save(path, quality=95, subsampling=0)   # no colour subsampling: flat greys stay exact
    print("wrote", path)


def real_desktops():
    """{look: screenshot} of the real desktop, or {} without KWin and Plasma."""
    from plasma_session import desktop_session, missing_programs
    if missing_programs():
        print("the real desktop needs", ", ".join(missing_programs()), "- the taskbar and windows are drawn from our files")
        return {}
    screens = {}
    for look in ("1995", "1998", "2000"):
        work = tempfile.mkdtemp(prefix=f"c95-{look}-", dir="/tmp")   # short: Wayland's socket path limit
        screens[look] = desktop_session(look, work)
        shutil.rmtree(work, ignore_errors=True)
    return screens


def main(output):
    from PySide6.QtWidgets import QApplication
    import chicago95ui  # noqa: F401  sets the platform before the application exists
    app = QApplication.instance() or chicago95ui.make_app("chicago95-report")   # as the tools make it
    startmenu, shutdown = load_script("chicago95-startmenu"), load_script("chicago95-shutdown")
    output.mkdir(parents=True, exist_ok=True)
    for stale in [*output.glob("report-*"), *output.glob("showcase-*")]:
        stale.unlink()
    scratch = Path(tempfile.mkdtemp(prefix="chicago95-report-"))
    desktops = real_desktops()
    for look in ("1995", "1998", "2000"):
        desktop = desktops.get(look)
        sections = {"taskbar": ("Taskbar" + (" (real desktop; icons are the test's squares)" if desktop else " (our parts, no icons)"),
                                taskbar_details(look, desktop, app, scratch)),
                    "windows": ("Windows", window_details(look, desktop, scratch)),
                    "startmenu": ("Start menu", start_menu_details(startmenu, app, look, scratch)),
                    "shutdown": ("Shut Down", shut_down_details(shutdown, app, look, scratch))}
        if look == "2000":
            sections["loading"] = ("Loading screen", loading_details(app, scratch))
            sections["logon"] = ("Log on", login_details(shutdown, app, scratch))
        for key, (title, rows) in sections.items():
            compose(f"{look} {title}", rows, output / f"report-{look}-{key}.png")
        compose_showcase(f"Chicago95 for KDE Plasma, {LOOK_NAMES[look]}: the original beside ours",
                         showcase_panels(look, desktop, sections, app, scratch, startmenu), output / f"showcase-{look}.jpg")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "report"))
