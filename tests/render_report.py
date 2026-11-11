#!/usr/bin/env python3
"""The comparison report: every detail the reference tests compare, the original's beside ours.

    python3 tests/render_report.py [OUTPUT_DIR [LOOK ...]]

writes, for 1995, 1998, 2000, 2001 (XP Classic) and luna (Windows XP):
- showcase-<look>.jpg, to show people: component by component (desktop, taskbar, windows, Start menu,
  Shut Down, System Properties, and for 2000, 2001 and luna the loading and log-on screens) the original
  beside ours; showcase-controls-<look>.jpg the same for the controls;
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
sys.path[:0] = [str(TESTS), str(TESTS / "luna"), str(TESTS.parent / "lib")]

from conftest import REPO, load_script  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from reference import LOOK_2000_KDEGLOBALS, close, installed_look, qimage_to_pil, render_start_menu, screenshot  # noqa: E402

BACKGROUND, INK, DIFFERENT, GAP = (255, 255, 255), (0, 0, 0), (255, 0, 0), 12
ROW_HEIGHT, COLUMN_WIDTH, MAX_ZOOM = 168, 560, 8
DEFAULT_LOGO = REPO / "plasmoids/org.chicago95.start/contents/images/logo-flag-16.png"  # what a default install shows
# The 2000 look's default; Setup downloads it (setup/fetch-waving-flag.py), so the report uses it when present.
WAVING_FLAG = Path.home() / ".local/share/chicago95/waving-flag.png"
MENU_SETTINGS = {
    "1995": ("[StartMenu]\nbannerText=Windows95\n", ""),
    "1998": (
        "[StartMenu]\nstyle=1998\nbannerText=Windows98\nbannerTextColor=#FFFFFF\nbannerNumberColor=#FFFFFF\n"
        "bannerBackground=#00007B,#00007B@95,#0000B0@70,#0000F8@45,#0000EE@20,#0000A9@0\n",
        "",
    ),
    "2000": (
        "[StartMenu]\nstyle=2000\nbannerText=Windows 2000 Professional\nbannerTextColor=#FFFFFF\n"
        "bannerNumberColor=#FFFFFF\n"
        "bannerBackground=#000000,#000021@200,#000081@120,#0000B2@70,#0000E3@45,#0000F3@20,#0000FF@0\n",
        LOOK_2000_KDEGLOBALS,
    ),
    "2001": (
        "[StartMenu]\nstyle=2001\nbannerText=Windows XP Professional\nbannerTextColor=#FFFFFF\n"
        "bannerNumberColor=#FFFFFF\n"
        "bannerBackground=#000000@225,#000080@195,#0000FF@125,#0000FF@60,#000080@0\n",
        LOOK_2000_KDEGLOBALS,
    ),
}


MENU_ORIGINALS = {  # look: (screenshot, the menu's box in it)
    "1995": ("win95startmenu", (2, 217, 166, 456)),
    "1998": ("win98start", (2, 0, 216, 456)),
    "2000": ("w2kstartmenu", (2, 113, 206, 456)),
    "2001": ("xpclassic", (2, 233, 193, 576)),
}
MENU_EXTRA_TOP = {  # the entries an original shows above Programs
    "2000": ("New Office Document", "Open Office Document", "Windows Update"),
}
MENU_ACTIVE_ROW = {"1995": 0, "1998": 4, "2000": None, "2001": None}  # highlighted in the detail rows
SHOWCASE_ACTIVE_ROW = {"1995": 0, "1998": 4, "2000": 4, "2001": 4}  # highlighted in the showcase
LOG_OFF_LOOKS = ("1998", "2001")  # 1995's and 2000's originals have no Log Off entry
KDEGLOBALS = {  # the colours each look's Setup writes
    "1995": "",
    "1998": "[WM]\nactiveBackground=0,0,128\nactiveBlend=16,132,208\n",
    "2000": LOOK_2000_KDEGLOBALS,
    "2001": LOOK_2000_KDEGLOBALS,
}
BEVELS = {"1995": "1995", "1998": "1995", "2000": "2000", "2001": "2000"}
SCREEN_LOOKS = ("2000", "2001")  # the looks with a loading and a log-on screen of their own (2001 uses 2000's)
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
    from test_taskbar_reference import taskbar as original_taskbar

    (start_left, start_right), tasks = BUTTONS[look]
    width = original_taskbar(look).width
    boxes = {
        "left half": (0, 0, width // 2, HEIGHT),
        "right half": (width // 2, 0, width, HEIGHT),
        "Start button": (0, 2, start_right + 4, HEIGHT),
    }
    for index, x in enumerate(ETCHED_LINES.get(look, []), 1):
        boxes[f"separator {index}"] = (x - 4, 2, x + 13, HEIGHT)
    for index, x in enumerate(QUICK_LAUNCH.get(look, []), 1):
        boxes[f"Quick Launch cell {index}"] = (x - 5, 2, x + 21, HEIGHT)
    for index, (left, right, pressed) in enumerate(tasks, 1):
        boxes[f"task button {index}{' (pressed)' if pressed else ''}"] = (left - 3, 2, right + 4, HEIGHT)
        boxes[f"task button {index}: icon and label"] = (left - 2, 2, left + 56, HEIGHT)
    for index, ((_l, right, _p), (left, _r, _q)) in enumerate(zip(tasks, tasks[1:], strict=False), 1):
        boxes[f"gap between task buttons {index} and {index + 1}"] = (right - 8, 2, left + 9, HEIGHT)
    tray_left, _tray_right = TRAYS[look]
    boxes["tray box"] = (tray_left - 3, 2, width, HEIGHT)
    for index, x in enumerate(TRAY_ICONS[look], 1):
        boxes[f"tray icon {index}"] = (x - 3, 3, x + 19, HEIGHT - 1)
    boxes["clock"] = (clock_left(look) - 1, 2, width, HEIGHT)
    return boxes


def clock_left(look):
    """The clock's first column: right of the last tray icon, or just inside a tray box that holds the clock alone."""
    from test_plasma_taskbar_reference import TRAY_ICONS
    from test_taskbar_reference import TRAYS

    return TRAY_ICONS[look][-1] + 17 if TRAY_ICONS[look] else TRAYS[look][0] + 3


def model_taskbar(look, app, scratch):
    """Ours without Plasma: the panel, Start button, separators, task buttons and tray box drawn by our
    files at the original's places (icons, labels and the clock are the programs' own, left out)."""
    import subprocess

    from aurorae_model import LOOKS
    from framesvg import render_frame
    from test_taskbar_reference import (
        BUTTON_HEIGHT,
        BUTTON_TOP,
        BUTTONS,
        SEPARATORS,
        TRAYS,
        render_on_strip,
        start_button,
    )
    from test_taskbar_reference import taskbar as original_taskbar

    colours = LOOKS[look]
    plasma_style = scratch / f"plasma-style-{look}"
    shutil.copytree(REPO / "plasma-style/theme", plasma_style)
    subprocess.run(
        [
            sys.executable,
            str(REPO / "plasma-style/make_chicago95_plasmastyle.py"),
            "--out",
            str(plasma_style),
            *[f"--{key}={colours[key]}" for key in ("face", "light", "shadow", "dark")],
        ],
        check=True,
        capture_output=True,
    )
    original = original_taskbar(look)
    ours = render_frame(
        plasma_style / "widgets/panel-background.svg", "", original.width, original.height, borders={"top"}
    )
    (_start_left, start_right), tasks = BUTTONS[look]
    strip = scratch / f"strip-{look}"
    strip.mkdir(exist_ok=True)
    button, _ = start_button(app, look, strip)
    ours.paste(button.crop((0, 2, start_right + 1, original.height)), (0, 2))
    for etched, _next in SEPARATORS.get(look, []):
        separator, width = render_on_strip(
            app, strip, "org.chicago95.tasks", "Separator", etched - 2, colours["face"], {}
        )
        ours.paste(separator.crop((etched - 2, 2, etched - 2 + width, original.height)), (etched - 2, 2))
    for left, right, pressed in tasks:
        frame = render_frame(
            plasma_style / "widgets/tasks.svg", "focus" if pressed else "normal", right - left + 1, BUTTON_HEIGHT
        )
        ours.paste(frame, (left, BUTTON_TOP))
    tray_left, tray_right = TRAYS[look]
    tray, _ = render_on_strip(
        app,
        strip,
        "org.chicago95.trayframe",
        "TrayBox",
        tray_left,
        colours["face"],
        {},
        width=tray_right - tray_left + 1,
    )
    ours.paste(tray.crop((tray_left, 2, tray_right + 1, original.height)), (tray_left, 2))
    return ours


def taskbar_masks(look):
    """The icons (the programs' own; ours are the test's squares, placed by the tests) and the clock's
    lettering (another time)."""
    from test_plasma_taskbar_reference import QUICK_LAUNCH, TRAY_ICONS
    from test_taskbar_reference import BUTTONS, TRAYS, XP_FLAG_AND_FOCUS_RECTANGLE_MASKS

    def icon(x, y=7):
        return (x, y, x + 16, y + 16)

    masks = [icon(x) for x in QUICK_LAUNCH.get(look, [])] + [icon(x) for x in TRAY_ICONS[look]]
    masks += [icon(left + 4, 7 + pressed) for left, _right, pressed in BUTTONS[look][1]]
    masks.append((clock_left(look) + 1, 6, TRAYS[look][1] - 1, 24))
    return masks + XP_FLAG_AND_FOCUS_RECTANGLE_MASKS.get(look, [])


def taskbar_details(look, desktop, app, scratch):
    from test_taskbar_reference import HEIGHT
    from test_taskbar_reference import taskbar as original_taskbar

    ours = (
        desktop.crop((0, desktop.height - HEIGHT, desktop.width, desktop.height))
        if desktop
        else model_taskbar(look, app, scratch)
    )
    return details(original_taskbar(look), ours, taskbar_boxes(look), masks=taskbar_masks(look))


# --- windows -------------------------------------------------------------------------------------


def window_boxes(width, height):
    from test_window_reference import BORDER, TOP

    w, h = width, height
    boxes = {
        "whole": (0, 0, w, h),
        "title bar: icon and caption": (0, 0, min(w, 190), TOP + 4),
        "title bar: buttons": (w - 70, 0, w, TOP + 4),
    }
    for name, offset in (("close", 0), ("maximize", 18), ("minimize", 34)):
        left = w - 6 - 16 - offset
        boxes[f"{name} button"] = (left - 1, BORDER + 1, left + 17, BORDER + 17)
    boxes.update(
        {
            "top-left corner": (0, 0, 14, 14),
            "top-right corner": (w - 14, 0, w, 14),
            "bottom-left corner": (0, h - 14, 14, h),
            "bottom-right corner": (w - 14, h - 14, w, h),
            "left edge": (0, h // 2 - 8, 14, h // 2 + 8),
            "bottom edge": (w // 2 - 8, h - 14, w // 2 + 8, h),
        }
    )
    return boxes


def window_details(look, desktop, scratch):
    """Each window of the look's screenshots: ours on the real desktop (each from another toolkit) or
    drawn by our decoration at the original's size."""
    from aurorae_model import Window, build_theme
    from plasma_session import CONTENT
    from test_window_reference import SIXTEEN_COLOUR_SCREENSHOT_COLOURS, WINDOWS

    theme = build_theme(scratch / f"aurorae-{look}", look, **SIXTEEN_COLOUR_SCREENSHOT_COLOURS.get(look, {}))
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
        masks += [(box[0] - left, box[1] - top, box[2] - left + 1, box[3] - top + 1) for box in covered]
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
        rows.append(
            (
                "dialog: help button pressed",
                original.crop((14, 7, 32, 23)),
                pressed.crop((200 - 6 - 18 - 16 - 1, 5, 200 - 6 - 18 + 1, 21)),
            )
        )
        plain = Window(theme, 200, 60, True, "", right="X").render()
        rows.append(
            ("dialog: close button", original.crop((32, 7, 50, 23)), plain.crop((200 - 6 - 16 - 1, 5, 200 - 6 + 1, 21)))
        )
    if look == "1998":
        disabled = Window(theme, 200, 60, True, "", right="X", disabled="X").render()
        rows.append(
            (
                "alert: close button, disabled",
                screenshot("win98notepad").crop((502, 193, 520, 209)),
                disabled.crop((200 - 6 - 16 - 1, 5, 200 - 6 + 1, 21)),
            )
        )
    return rows


# --- Start menu ----------------------------------------------------------------------------------


def start_menu_details(startmenu, app, look, scratch):
    from test_startmenu_icons_styles_reference import ROWS
    from test_startmenu_reference import ROW_TOPS

    settings, kdeglobals = MENU_SETTINGS[look]
    name, box = MENU_ORIGINALS[look]
    (scratch / f"menu-{look}").mkdir(exist_ok=True)
    ours = render_start_menu(
        startmenu,
        app,
        scratch / f"menu-{look}",
        settings,
        kdeglobals,
        active=MENU_ACTIVE_ROW[look],
        extra_top=MENU_EXTRA_TOP.get(look, ()),
    )
    original = screenshot(name).crop(box)
    height = min(original.height, ours.height)  # 1998's original has more entries above Programs
    boxes = {
        "whole": (
            (0, original.height - height, original.width, original.height),
            (0, ours.height - height, ours.width, ours.height),
        ),
        "banner": ((0, 0, 26, original.height), (0, 0, 26, ours.height)),
        "bottom edge": (
            (0, original.height - 40, original.width, original.height),
            (0, ours.height - 40, ours.width, ours.height),
        ),
    }
    if look == "1995":
        names = ("Programs", "Documents", "Settings", "Find", "Help", "Run...", "Shut Down...")
        boxes.update(
            {
                f"row: {label}": (0, top - 2, original.width, top + 34)
                for label, top in zip(names, ROW_TOPS, strict=False)
            }
        )
    elif look in ROWS:
        rows, height, _active = ROWS[look]
        boxes.update(
            {
                f"row: {label}": (
                    (0, mine_top, original.width, mine_top + height),
                    (0, our_top, ours.width, our_top + height),
                )
                for label, (mine_top, our_top) in rows.items()
            }
        )
    return details(original, ours, boxes)


# --- Shut Down, loading and log-on screens -------------------------------------------------------

SHUT_DOWN_DIALOGS = {}  # look: our whole dialog, for the showcase
# No XP Classic shot of Shut Down or System Properties exists: 2001 is shown against 2000's originals.
SHUT_DOWN_BANNERS = {"1995": "Windows 2000", "1998": "Windows 2000", "2000": "Windows 2000", "2001": "Windows XP"}
SHUT_DOWN_REFERENCE_LOOKS = ("2000", "2001")
SYSPROPS_APPLY_LOOKS = ("2000", "2001")


def shut_down_details(shutdown, app, look, scratch):
    from test_shutdown_reference import BANNER_LINES, BANNER_MARK

    logo = WAVING_FLAG if look in SHUT_DOWN_REFERENCE_LOOKS and WAVING_FLAG.exists() else DEFAULT_LOGO
    settings = {
        "style": look,
        "bannerText": SHUT_DOWN_BANNERS[look],
        "osName": SHUT_DOWN_BANNERS[look],
        "osCompany": "Microsoft",
        "edition": "Professional",
        "osLogo": str(logo),
        "companyLogo": "",
    }  # the original's wording
    import chicago95ui
    from aurorae_model import build_theme

    chicago95ui.DECORATION = str(build_theme(scratch / f"shutdown-aurorae-{look}", look))  # the look's close button
    with installed_look(app, f"[StartMenu]\nstyle={look}\n[Look]\nbevel={BEVELS[look]}\n", KDEGLOBALS[look]):
        dialog = shutdown.ShutDownDialog(settings)
        dialog.show()
        app.processEvents()
        ours = qimage_to_pil(dialog.grab().toImage())
        dialog.close()
    SHUT_DOWN_DIALOGS[look] = ours
    if look not in SHUT_DOWN_REFERENCE_LOOKS:
        return thumbnail_shut_down_details(look, ours)
    from test_shutdown_reference import BODY_2000, CLIENT_2000, DIALOG_2000

    whole = [
        ("whole", screenshot("w2kshutdown").crop(DIALOG_2000), ours),
        (
            "title bar",
            screenshot("w2kshutdown").crop((DIALOG_2000[0], DIALOG_2000[1], DIALOG_2000[2], DIALOG_2000[1] + 22)),
            ours.crop((0, 0, ours.width, 22)),
        ),
    ]
    original = screenshot("w2kshutdown").crop(CLIENT_2000)
    ours = ours.crop((*BODY_2000, BODY_2000[0] + original.width, BODY_2000[1] + original.height))
    boxes = {
        "banner mark": BANNER_MARK,
        **{f"banner: {line}": box for line, box in BANNER_LINES.items()},
        "question and dropdown": (0, 70, original.width, 180),
        "buttons": (0, 180, original.width, original.height),
    }
    return whole + details(original, ours, boxes)


def thumbnail_shut_down_details(look, dialog):
    """1995's and 1998's originals are half-size thumbnails: the dialog cut from it at its frame, beside
    ours (which draws its own frame and title) halved the way a thumbnail is made (each pixel the average
    of four)."""
    from test_shutdown_reference import thumbnail_dialog

    original = thumbnail_dialog(look)
    halved = dialog.resize((dialog.width // 2, dialog.height // 2), Image.BOX)
    w, h = original.size
    boxes = {
        "whole, at the thumbnail's half size": ((0, 0, w, h), (0, 0, halved.width, halved.height)),
        "title bar": (0, 0, w, 14),
        "question and options": (0, 13, w, h * 2 // 3),
        "buttons": (0, h * 2 // 3, w, h),
    }
    return details(original, halved, boxes)


SYSPROPS_FACTS = dict(
    os_name="Microsoft Windows 98",
    kernel="Second Edition",
    desktop="4.10.2222 A",
    owner="Doctor",
    hostname="TARDIS",
    product_key="01902-OEM-0087094-44427",
    cpu_model="GenuineIntel",
    logical_processors="Pentium(r) II Processor",
    memory="256.0MB RAM",
    display="",
    resources_free="90% free",
    filesystem="32-bit",
    virtual_memory="32-bit",
)


def sysprops_details(look, app, scratch):
    """System Properties: the dialog, its title buttons, tab strip, General page and buttons, against
    the original's (tests/test_sysprops_reference.py), the title buttons from the look's decoration."""
    import chicago95ui
    from aurorae_model import build_theme
    from test_sysprops_reference import LOOKS, PAGE_TOP, SELECTED_TAB_TOP
    from test_sysprops_reference import original as original_dialog

    sysprops = load_script("chicago95-sysprops")
    chicago95ui.DECORATION = str(build_theme(scratch / f"sysprops-aurorae-{look}", look))
    window = sysprops.build_window(sysprops.SystemFacts(**SYSPROPS_FACTS), look)
    window.show()
    app.processEvents()
    ours = qimage_to_pil(window.grab().toImage())
    window.close()
    theirs = original_dialog(look)
    settings = LOOKS[look]
    w, h = theirs.size
    buttons_top = settings["buttons_top"]
    boxes = {
        "whole": (0, 0, w, h),
        "help and close buttons": (w - 3 - 2 - 34 - 2, 3, w - 3, 3 + 18),
        "tabs": (3, SELECTED_TAB_TOP - 3, settings["tab_boxes"][-1][1] + 8, PAGE_TOP + 6),
        "General page": (PAGE_LEFT_FOR_REPORT, PAGE_TOP, w - 9, buttons_top - 8),
        "buttons (OK is the default)": (
            min(settings["buttons"].values()) - 6,
            buttons_top - 6,
            w - 3,
            buttons_top + 23 + 6,
        ),
    }
    if look in SYSPROPS_APPLY_LOOKS:
        boxes["disabled button (Apply)"] = (
            settings["buttons"]["Apply"] - 4,
            buttons_top - 4,
            settings["buttons"]["Apply"] + 79,
            buttons_top + 27,
        )
    return details(theirs, ours, boxes, masks=[(20, PAGE_TOP + 4, 190, 220)])  # the computer picture is the icon set's


PAGE_LEFT_FOR_REPORT = 9


def loading_details(app, scratch):
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtQuick import QQuickView
    from test_loading_screen_reference import (
        COMPANY_LINE,
        CORNER,
        EDITION_LINE,
        LOADING_TEXT_BOX,
        MARK,
        NAME_LINE,
        TAGLINE_LINE,
    )

    splash = scratch / "splash"
    logo = WAVING_FLAG if WAVING_FLAG.exists() else DEFAULT_LOGO
    shutil.copytree(REPO / "splash/chicago95.splashscreen/contents/splash", splash, dirs_exist_ok=True)
    (splash / "settings.js").write_text(
        f'.pragma library\nvar style = "2000"\nvar brandText = "Windows 2000"\nvar brandLogo = "{logo}"\n'
        'var edition = "Professional"\nvar tagline = "Built on NT Technology"\nvar company = "Microsoft"\n'
        'var companyLogo = ""\nvar loadingText = "Starting up..."\n'
        'var footer = "Copyright © 1985-1999 Microsoft Corporation"\nvar picture = ""\n'
    )  # the original's wording
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
    boxes = {
        "whole": (0, 0, 640, 480),
        "mark": MARK,
        "company": COMPANY_LINE,
        "name": NAME_LINE,
        "edition": EDITION_LINE,
        "tagline": TAGLINE_LINE,
        "corner": CORNER,
        "progress": (190, 425, 460, 455),
        "loading text": LOADING_TEXT_BOX,
    }
    return details(screenshot("w2kboot"), ours, boxes)


def login_details(shutdown, app, scratch):
    from login_theme import render_login
    from test_login_reference import BANNER_LINES, DIALOG

    logo = WAVING_FLAG if WAVING_FLAG.exists() else DEFAULT_LOGO
    look = {
        "style": "2000",
        "bannerText": "Windows 2000",
        "osName": "Windows 2000",
        "osCompany": "Microsoft",
        "edition": "Professional",
        "osLogo": str(logo),
        "companyLogo": "",
        "tagline": "Built on NT Technology",
    }  # the original's wording
    shutdown.render_login_banner(look, scratch / "login-banner.png")
    with installed_look(app, "[StartMenu]\nstyle=2000\n", LOOK_2000_KDEGLOBALS):
        ours = render_login(
            app,
            scratch / "login",
            banner=scratch / "login-banner.png",
            show_options=True,
            loginStyle="2000",
            titleActive="#0A246A,#A6CAF0",
            loginTitle="Log On to Windows",
        )
    left, top, right, bottom = DIALOG
    boxes = {
        "whole": DIALOG,
        "title bar": (left, top, right, top + 22),
        "banner": (114, 96, 525, 189),
        **{f"banner: {line}": box for line, box in BANNER_LINES.items()},
        "fields": (left, 189, right, 282),
        "buttons": (left, 282, right, bottom),
    }
    return details(screenshot("w2klogon"), ours, boxes)


# --- Luna (Windows XP) ---------------------------------------------------------------------------
# Its originals are cut from several shots (tests/references/SOURCES.md); the pieces are drawn from the Luna
# modules (tests/luna/luna_render.py), the taskbar and the active window from the real desktop when there is one.

LUNA_PANEL_HEIGHT = 30
LUNA_WINDOW_FRAME = (100, 50, 700, 454)  # where plasma_session.py puts the active window: xpnotepad's size
LUNA_INACTIVE_VISIBLE = (66, 53, 312, 138)  # xpfulldesktop: the Help and Support Center's corner and title
LUNA_CORNER = 6


def luna_window_boxes(width, height, label="whole"):
    title = 30
    boxes = {
        label: (0, 0, width, height),
        "title bar: icon and caption": (0, 0, min(width, 190), title + 4),
        "title bar: buttons": (width - 80, 0, width, title + 4),
        "top-left corner": (0, 0, 14, 14),
        "left edge": (0, height // 2 - 8, 14, height // 2 + 8),
    }
    if width > 300:
        boxes.update(
            {
                "close button": (width - 28, 5, width - 5, 28),
                "maximize button": (width - 51, 5, width - 28, 28),
                "minimize button": (width - 74, 5, width - 51, 28),
                "top-right corner": (width - 14, 0, width, 14),
                "bottom-left corner": (0, height - 14, 14, height),
                "bottom-right corner": (width - 14, height - 14, width, height),
                "bottom edge": (width // 2 - 8, height - 14, width // 2 + 8, height),
            }
        )
    return boxes


def luna_window_details(desktop, scratch):
    from luna_render import luna_window

    rows = []
    original = screenshot("xpnotepad")
    width, height = original.size
    if desktop:
        ours, source = desktop.crop(LUNA_WINDOW_FRAME), "a Qt window on the real desktop"
    else:
        ours, source = luna_window(width, height, True, scratch, "Untitled - Notepad"), "our decoration"
    masks = [(0, 0, LUNA_CORNER, LUNA_CORNER), (width - LUNA_CORNER, 0, width, LUNA_CORNER)]
    masks += [(4, 30, width - 4, height - 4), (4, 4, 26, 26), (26, 3, 150, 27)]  # client area, icon, caption
    rows += details(original, ours, luna_window_boxes(width, height), f"Notepad (active; ours: {source}): ", masks)
    left, top, right, bottom = LUNA_INACTIVE_VISIBLE
    original = screenshot("xpfulldesktop").crop(LUNA_INACTIVE_VISIBLE)
    ours = luna_window(400, 402, False, scratch).crop((0, 0, right - left, bottom - top))
    masks = [(0, 0, LUNA_CORNER, LUNA_CORNER), (4, 30, right - left - 4, bottom - top), (4, 4, 26, 26), (26, 3, 225, 27)]
    boxes = luna_window_boxes(right - left, bottom - top, "whole visible part")
    rows += details(original, ours, boxes, "Help and Support Center (inactive; ours: our decoration): ", masks)
    return rows


def luna_taskbar_details(desktop, app, scratch):
    from luna_render import START_PILL, TASK_BUTTONS, TRAY_BOX, luna_taskbar

    original = screenshot("xprunning")
    ours = (
        desktop.crop((0, desktop.height - LUNA_PANEL_HEIGHT, desktop.width, desktop.height))
        if desktop
        else luna_taskbar(app, scratch)
    )
    boxes = {"whole": (0, 0, original.width, LUNA_PANEL_HEIGHT), "Start button": (0, 0, START_PILL[1] + 2, LUNA_PANEL_HEIGHT)}
    masks = [(6, 4, 78, 27), (TRAY_BOX[0] + 3, 4, original.width - 5, 26)]  # the flag and lettering, the tray's icon and clock
    for index, (left, width, _text, pressed) in enumerate(TASK_BUTTONS, 1):
        boxes[f"task button {index}{' (pressed)' if pressed else ''}"] = (left - 2, 0, left + width + 2, LUNA_PANEL_HEIGHT)
        masks += [(left + 4, 4, left + 24, 22), (left + 25, 5, left + width - 5, 22)]  # the icon, the label
    boxes["tray box"] = (TRAY_BOX[0] - 3, 0, original.width, LUNA_PANEL_HEIGHT)
    rows = details(original, ours, boxes, masks=masks)
    wide, wide_ours = screenshot("xptaskbar-1x"), luna_taskbar(app, scratch, 3000, 147)
    wide_boxes = {"Start button (3000px shot)": (0, 0, 100, LUNA_PANEL_HEIGHT), "tray box (3000px shot)": (2850, 0, 3000, LUNA_PANEL_HEIGHT)}
    return rows + details(wide, wide_ours, wide_boxes, masks=[(6, 4, 78, 27), (2858, 4, 2996, 26)])


def luna_start_menu_details():
    from luna_render import luna_menu

    original, ours = screenshot("xpdesktop").crop((0, 93, 380, 570)), luna_menu()
    boxes = {
        "whole": (0, 0, 380, 477),
        "header": (0, 0, 380, 66),
        "left column": (0, 66, 199, 436),
        "right column": (199, 66, 380, 436),
        "footer": (0, 436, 380, 477),
    }
    return details(original, ours, boxes, masks=[(6, 6, 62, 62), (66, 16, 260, 50)])  # the user's picture and name


def luna_shut_down_details():
    from luna.test_luna_dialogs import TURN_OFF_MASKS
    from luna_render import luna_turn_off

    original, ours = screenshot("xpshutdowndialog"), luna_turn_off()
    width, height = original.size
    boxes = {
        "whole": (0, 0, width, height),
        "title band": (0, 0, width, 44),
        "options": (0, 44, width, 157),
        "bottom band": (0, 157, width, height),
    }
    return details(original, ours, boxes, masks=TURN_OFF_MASKS)


def luna_loading_details(app):
    from luna_qml import render_luna_splash

    boxes = {
        "whole": (0, 0, 640, 480),
        "logo": (150, 100, 500, 330),
        "progress": (240, 340, 400, 375),
        "footer": (10, 420, 260, 470),
    }
    return details(screenshot("xpsplash"), render_luna_splash(app), boxes)


def luna_login_details(app):
    from luna_qml import render_luna_login

    boxes = {
        "whole": (0, 0, 800, 600),
        "top band": (0, 0, 800, 80),
        "bottom band": (0, 500, 800, 600),
        "fields": (490, 301, 665, 340),
    }
    return details(screenshot("xplogin"), render_luna_login(app), boxes, masks=[(20, 520, 215, 555), (465, 520, 755, 558)])


def luna_sysprops_details(app):
    """System Properties in LunaStyle and the Luna frame: no XP original of it exists, so ours alone."""
    sysprops = load_script("chicago95-sysprops")
    settings = "[StartMenu]\nstyle=luna\n[Look]\ndecoration=luna\nwidgetStyle=luna\ntaskbarStyle=luna\n"
    with installed_look(app, settings, ""):
        window = sysprops.build_window(sysprops.SystemFacts(**SYSPROPS_FACTS), "luna")
        window.show()
        app.processEvents()
        ours = qimage_to_pil(window.grab().toImage())
        window.close()
    return [("whole", None, ours)]


def luna_sections(desktop, app, scratch):
    sections = {
        "taskbar": (
            "Taskbar" + (" (real desktop; icons are the test's squares)" if desktop else " (our parts, no icons)"),
            luna_taskbar_details(desktop, app, scratch),
        ),
        "windows": ("Windows", luna_window_details(desktop, scratch)),
        "startmenu": ("Start menu", luna_start_menu_details()),
        "shutdown": ("Turn Off Computer", luna_shut_down_details()),
        "loading": ("Loading screen", luna_loading_details(app)),
        "logon": ("Log on", luna_login_details(app)),
    }
    sysprops = load_script("chicago95-sysprops")
    if "luna" in sysprops.TABS:  # no XP original of System Properties exists: ours alone
        sections["sysprops"] = ("System Properties (no original exists)", luna_sysprops_details(app))
    else:
        print("System Properties has no Luna layout yet: left out of the Luna report")
    return sections


def luna_showcase_panels(sections):
    def whole(key, index=0):
        _label, original, ours = sections[key][1][index]
        return original, ours

    inactive = next(index for index, row in enumerate(sections["windows"][1]) if "inactive" in row[0])
    panels = [
        ("Taskbar", *whole("taskbar")),
        ("Window, active", *whole("windows")),
        ("Window, inactive (the corner and title that show)", *whole("windows", inactive)),
        ("Start menu", *whole("startmenu")),
        ("Turn Off Computer", *whole("shutdown")),
    ]
    if "sysprops" in sections:
        panels.append(("System Properties (no original exists)", None, whole("sysprops")[1]))
    return panels + [("Loading screen", *whole("loading")), ("Log on", *whole("logon"))]


# --- the sheets ----------------------------------------------------------------------------------


def label_font(size=15):
    for path in (
        "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
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


def no_reference(size, note):
    placeholder = Image.new("RGB", size, SHOWCASE_BACKGROUND)
    ImageDraw.Draw(placeholder).text((6, size[1] // 2 - 7), note, fill=(110, 110, 110), font=label_font(12))
    return placeholder


def compose(title, rows, path):
    font = label_font()
    prepared = []
    summary = []
    for label, original, ours in rows:
        if original is None:  # no original exists: ours alone, nothing to count
            blank = no_reference(ours.size, "no original screenshot exists")
            images = [image.resize((image.width * 2, image.height * 2), Image.NEAREST) for image in (blank, ours)]
            prepared.append((f"{label}: no original to compare, x2", images))
            summary.append(f"{'-':>7} {'-':>5}   {title}: {label} (no original)")
            continue
        zoom = zoom_for(original, ours)
        diff = difference(original, ours)
        differing = sum(1 for pixel in diff.getdata() if pixel == DIFFERENT)
        share = 100 * differing / (diff.width * diff.height)
        images = [
            image.resize((image.width * zoom, image.height * zoom), Image.NEAREST) for image in (original, ours, diff)
        ]
        prepared.append(
            (f"{label}: {differing} pixels differ ({share:.1f}%)" + (f", x{zoom}" if zoom > 1 else ""), images)
        )
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
LOOK_NAMES = {
    "1995": "1995 look",
    "1998": "1998 look",
    "2000": "2000 look",
    "2001": "Windows XP Classic",
    "luna": "Windows XP",
}


def showcase_panels(look, desktop, sections, app, scratch, startmenu):
    """[(component, original, ours)]: the desktop, the taskbar, each window, the Start menu whole with the
    original's entries, the Shut Down dialog in our frame, and each screen whole."""
    from aurorae_model import Window, build_theme
    from plasma_session import CONTENT
    from test_taskbar_reference import HEIGHT, TASKBARS
    from test_taskbar_reference import taskbar as original_taskbar
    from test_window_reference import SIXTEEN_COLOUR_SCREENSHOT_COLOURS, WINDOWS

    panels = []
    if desktop:
        panels.append(("Desktop (ours: the test's programs and icons)", screenshot(TASKBARS[look]), desktop))
    bar = (
        desktop.crop((0, desktop.height - HEIGHT, desktop.width, desktop.height))
        if desktop
        else model_taskbar(look, app, scratch)
    )
    panels.append(("Taskbar", original_taskbar(look), bar))
    theme = build_theme(
        scratch / f"showcase-aurorae-{look}", look, **SIXTEEN_COLOUR_SCREENSHOT_COLOURS.get(look, {})
    )
    toolkits = {box: toolkit for _title, toolkit, box in CONTENT[look]["windows"]}
    for window_look, name, (left, top, right, bottom), active, caption, _covered in WINDOWS.values():
        if window_look != look:
            continue
        original = screenshot(name).crop((left, top, right + 1, bottom + 1))
        toolkit = toolkits.get((left, top, right, bottom))
        if desktop and toolkit:
            ours, note = desktop.crop((left, top, right + 1, bottom + 1)), f"ours: a {toolkit.upper()} window, empty"
        else:
            ours, note = (
                Window(theme, original.width, original.height, active, caption).render(),
                "ours: the frame alone",
            )
        panels.append((f"Window, {'active' if active else 'inactive'} ({note})", original, ours))
    settings, kdeglobals = MENU_SETTINGS[look]
    menu_box = MENU_ORIGINALS[look]
    (scratch / f"showcase-menu-{look}").mkdir(exist_ok=True)
    # Each original's own entries: 1995 had no Log Off; 2000's shows Office and Windows Update above.
    menu = render_start_menu(
        startmenu,
        app,
        scratch / f"showcase-menu-{look}",
        settings,
        kdeglobals,
        without=() if look in LOG_OFF_LOOKS else ("&Log Off...",),
        active=SHOWCASE_ACTIVE_ROW[look],
        extra_top=MENU_EXTRA_TOP.get(look, ()),
    )
    panels.append(("Start menu", screenshot(menu_box[0]).crop(menu_box[1]), menu))
    panels.append(("Shut Down", *shut_down_whole(look, sections)))
    for key, component in (("sysprops", "System Properties"), ("loading", "Loading screen"), ("logon", "Log on")):
        if key in sections:
            _label, original, ours = sections[key][1][0]  # each section's first row is the whole screen
            panels.append((component, original, ours))
    return panels


def shut_down_whole(look, sections):
    """The original dialog and ours, whole: 1995's and 1998's originals are half-size thumbnails,
    shown enlarged beside ours at full size."""
    if look in SHUT_DOWN_REFERENCE_LOOKS:
        _label, original, ours = sections["shutdown"][1][0]
        return original, ours
    _label, original, _halved = sections["shutdown"][1][0]
    return original.resize((original.width * 2, original.height * 2), Image.NEAREST), SHUT_DOWN_DIALOGS[look]


# The controls showcase: one detail row from each section, picked by its label, shown as a control.
CONTROLS = [
    ("windows", lambda label: label.endswith("title bar: buttons"), "Title bar buttons (minimize, maximize, close)"),
    ("sysprops", lambda label: label == "help and close buttons", "Dialog title buttons (help, close)"),
    ("sysprops", lambda label: label == "tabs", "Tabs (the first selected)"),
    ("sysprops", lambda label: label.startswith("buttons"), "Push buttons (OK is the default)"),
    ("sysprops", lambda label: label.startswith("disabled button"), "Disabled push button"),
    (
        "shutdown",
        lambda label: label == "question and options",
        "Radio buttons (the original is a half-size thumbnail)",
    ),
    ("shutdown", lambda label: label == "question and dropdown", "Dropdown list"),
    ("logon", lambda label: label == "fields", "Text fields, dropdown and check box"),
    ("loading", lambda label: label == "progress", "Progress bar"),
    ("startmenu", lambda label: label.lower() == "row: programs", "Menu row, highlighted"),
    ("startmenu", lambda label: label.lower() == "row: documents", "Menu row"),
    ("taskbar", lambda label: label == "Start button", "Start button"),
    (
        "taskbar",
        lambda label: label.startswith("task button") and "(pressed)" not in label and ":" not in label,
        "Task button",
    ),
    ("taskbar", lambda label: "(pressed)" in label and ":" not in label, "Task button, pressed"),
    ("taskbar", lambda label: label == "separator 1", "Toolbar separator and grip"),
    ("taskbar", lambda label: label == "tray box", "Tray box (its icons and clock are hatched)"),
]


def flat_controls(app, look):
    """Every Qt control our flat theme draws (tests/controls_gallery.py), in the look's colours."""
    import controls_gallery

    with installed_look(app, f"[StartMenu]\nstyle={look}\n", KDEGLOBALS[look]):
        return controls_gallery.controls(app, look)


def luna_controls_panels(app):
    """LunaStyle's gallery (tests/luna/luna_gallery.py) beside the Display Properties and Appearance shots."""
    from luna_render import luna_controls

    gallery = luna_controls(app)
    display, appearance = screenshot("xpdisplayprop-1x"), screenshot("xpappearance")
    return [
        ("Tabs, group box, combo, slider and buttons (the original: Display Properties)", display, gallery),
        ("Push buttons (the original: Display Properties' OK and Cancel)", display.crop((150, 415, 404, 452)), gallery.crop((6, 6, 260, 43))),
        ("Fields, check boxes, radio buttons and tabs (the original: Appearance)", appearance, gallery.crop((0, 40, 400, 215))),
    ]


def controls_panels(sections, look, app):
    """[(control, original or None, ours)]: every Qt control the look's theme draws, then our own controls
    from the sections' detail rows, in CONTROLS' order."""
    panels = luna_controls_panels(app) if look == "luna" else flat_controls(app, look)
    for section, matches, name in CONTROLS:
        rows = sections.get(section, ("", []))[1]
        for label, theirs, ours in rows:
            if matches(label):
                panels.append((name, theirs, ours))
                break
    return panels


def compose_showcase(title, panels, path):
    heading, caption = label_font(24), label_font(15)
    inner = SHOWCASE_WIDTH - 4 * GAP
    laid_out = []
    for component, original_shot, ours in panels:
        original = original_shot
        if original is None:  # no original screenshot shows this control
            original = no_reference(ours.size, "no original screenshot shows this control")
        width = max(original.width, ours.width)
        side_by_side = 2 * width + GAP <= inner
        zoom = max(1, min(3, (inner - GAP) // 2 // width)) if side_by_side else max(1, min(2, inner // width))
        zoom = max(1, min(zoom, 400 // max(original.height, ours.height)))  # tall crops (a scroll bar) stay in view
        images = [image.resize((image.width * zoom, image.height * zoom), Image.NEAREST) for image in (original, ours)]
        laid_out.append((component, side_by_side, zoom, images))
    height = 70
    for _component, side_by_side, _zoom, images in laid_out:
        body = (
            max(image.height for image in images) + 24
            if side_by_side
            else sum(image.height + 24 for image in images) + GAP
        )
        height += 40 + body + 3 * GAP
    sheet = Image.new("RGB", (SHOWCASE_WIDTH, height), SHOWCASE_BACKGROUND)
    draw = ImageDraw.Draw(sheet)
    draw.text((2 * GAP, 20), title, fill=INK, font=heading)
    y = 70
    for component, side_by_side, zoom, images in laid_out:
        body = (
            max(image.height for image in images) + 24
            if side_by_side
            else sum(image.height + 24 for image in images) + GAP
        )
        draw.rectangle((GAP, y, SHOWCASE_WIDTH - GAP, y + 40 + body + GAP), fill=CARD)
        draw.text((2 * GAP, y + 10), component + (f"  (enlarged x{zoom})" if zoom > 1 else ""), fill=INK, font=heading)
        x, top = 2 * GAP, y + 40
        for name, image in zip(("Original", "Chicago95 for Plasma"), images, strict=False):
            draw.text((x, top), name, fill=(90, 90, 90), font=caption)
            sheet.paste(image, (x, top + 20))
            if side_by_side:
                x += image.width + 2 * GAP
            else:
                top += image.height + 24 + GAP // 2
        y += 40 + body + 3 * GAP
    sheet.save(path, quality=95, subsampling=0)  # no colour subsampling: flat greys stay exact
    print("wrote", path)


def real_desktops(looks):
    """{look: screenshot} of the real desktop of each look, or {} without KWin and Plasma."""
    from plasma_session import desktop_session, missing_programs

    if missing_programs():
        print(
            "the real desktop needs",
            ", ".join(missing_programs()),
            "- the taskbar and windows are drawn from our files",
        )
        return {}
    screens = {}
    for look in looks:
        work = tempfile.mkdtemp(prefix=f"c95-{look}-", dir="/tmp")  # short: Wayland's socket path limit
        screens[look] = desktop_session(look, work)
        shutil.rmtree(work, ignore_errors=True)
    return screens


def flat_sections(look, desktop, app, scratch, startmenu, shutdown):
    against = " (against 2000's original: no XP Classic shot exists)" if look == "2001" else ""
    sections = {
        "taskbar": (
            "Taskbar" + (" (real desktop; icons are the test's squares)" if desktop else " (our parts, no icons)"),
            taskbar_details(look, desktop, app, scratch),
        ),
        "windows": ("Windows", window_details(look, desktop, scratch)),
        "startmenu": ("Start menu", start_menu_details(startmenu, app, look, scratch)),
        "shutdown": ("Shut Down" + against, shut_down_details(shutdown, app, look, scratch)),
        "sysprops": ("System Properties" + against, sysprops_details(look, app, scratch)),
    }
    if look in SCREEN_LOOKS:
        sections["loading"] = ("Loading screen", loading_details(app, scratch))
        sections["logon"] = ("Log on", login_details(shutdown, app, scratch))
    return sections


def main(output, looks):
    import chicago95ui  # noqa: F401  sets the platform before the application exists
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or chicago95ui.make_app("chicago95-report")  # as the tools make it
    startmenu, shutdown = load_script("chicago95-startmenu"), load_script("chicago95-shutdown")
    output.mkdir(parents=True, exist_ok=True)
    for look in looks:
        for stale in [*output.glob(f"report-{look}-*"), *output.glob(f"showcase-{look}.jpg"), *output.glob(f"showcase-controls-{look}.jpg")]:
            stale.unlink()
    scratch = Path(tempfile.mkdtemp(prefix="chicago95-report-"))
    desktops = real_desktops(looks)
    for look in looks:
        desktop = desktops.get(look)
        if look == "luna":
            sections = luna_sections(desktop, app, scratch)
            panels = luna_showcase_panels(sections)
        else:
            sections = flat_sections(look, desktop, app, scratch, startmenu, shutdown)
            panels = showcase_panels(look, desktop, sections, app, scratch, startmenu)
        for key, (title, rows) in sections.items():
            compose(f"{look} {title}", rows, output / f"report-{look}-{key}.png")
        compose_showcase(
            f"Chicago95 for KDE Plasma, {LOOK_NAMES[look]}: the original beside ours",
            panels,
            output / f"showcase-{look}.jpg",
        )
        compose_showcase(
            f"Chicago95 for KDE Plasma, {LOOK_NAMES[look]}: the controls, the original's beside ours",
            controls_panels(sections, look, app),
            output / f"showcase-controls-{look}.jpg",
        )


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "report"), sys.argv[2:] or list(LOOK_NAMES))
