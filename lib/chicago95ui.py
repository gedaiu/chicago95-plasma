"""Shared Chicago95 look for the Chicago95 PySide6 tools.

Import this before any other PySide6 import: it pins the platform to XWayland,
forces the Windows style and reads the Plasma scale so dialogs render sharp.
Every tool then calls make_app() instead of QApplication() directly.
"""

import configparser
import glob
import os
import re
import signal
import subprocess
import sys
from pathlib import Path


def compositor_reachable():
    """Whether a display server is there to ask: kscreen-doctor aborts without one, and each abort is a crash report."""
    return bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))


def detect_scale():
    if not compositor_reachable():
        return "1"
    try:
        child_env = {key: value for key, value in os.environ.items() if key != "QT_QPA_PLATFORM"}
        output = subprocess.run(
            ["kscreen-doctor", "-o"], capture_output=True, text=True, timeout=3, env=child_env, check=False
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return "1"
    plain = re.sub(r"\x1b\[[0-9;]*m", "", output)
    match = re.search(r"Scale:\s*([0-9.]+)", plain)
    return match.group(1) if match else "1"


# Native Wayland by default: Qt rasterises text once at the compositor scale and it stays crisp,
# while the X11 path softened the W98 UI font at every setting. A tool that must still run on
# X11 sets CHICAGO95_PLATFORM=xcb before importing this module.
os.environ.setdefault("QT_QPA_PLATFORM", os.environ.get("CHICAGO95_PLATFORM", "wayland"))
os.environ.setdefault("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")
os.environ.setdefault("QT_STYLE_OVERRIDE", "Windows")
# On XWayland the X server advertises the real DPI (Xft.dpi 144 via ~/.Xresources) and KWin's
# "apps scale themselves" mode leaves it at that, so Qt already lands at the right scale.
# Forcing QT_SCALE_FACTOR here stacked on top of that and rendered every tool at 2.25x.
# Only the headless offscreen platform has no DPI to read, so it still needs the explicit factor.
if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    os.environ.setdefault("QT_SCALE_FACTOR", detect_scale())
os.environ.pop("QT_QPA_PLATFORMTHEME", None)

from PySide6.QtCore import QEvent, QObject, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QIcon,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QRadialGradient,
    QRegion,
)
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QDialog,
    QFrame,
    QProxyStyle,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionFrame,
    QTabBar,
    QWidget,
)

KDEGLOBALS = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "kdeglobals")

# The colour scheme (System Settings > Colors) is the single source of these colours; the values
# here are the 1995 defaults for when a key is missing.
SCHEME_DEFAULTS = {
    "face": ("Colors:Window", "BackgroundNormal", "192,192,192"),
    "selection": ("Colors:Selection", "BackgroundNormal", "0,0,128"),
    "selection_text": ("Colors:Selection", "ForegroundNormal", "255,255,255"),
    "title_active": ("WM", "activeBackground", "0,0,128"),
    "title_active_blend": ("WM", "activeBlend", "0,0,128"),
    "title_active_text": ("WM", "activeForeground", "255,255,255"),
    "title_inactive": ("WM", "inactiveBackground", "128,128,128"),
    "title_inactive_blend": ("WM", "inactiveBlend", "128,128,128"),
    "title_inactive_text": ("WM", "inactiveForeground", "192,192,192"),
}


def read_scheme(path=None):
    """The colour scheme's colours as QColors, keyed as in SCHEME_DEFAULTS."""
    settings = configparser.ConfigParser(interpolation=None, strict=False)
    settings.optionxform = str
    settings.read(path or KDEGLOBALS)
    return {
        name: QColor(*(int(part) for part in settings.get(group, key, fallback=default).split(",")[:3]))
        for name, (group, key, default) in SCHEME_DEFAULTS.items()
    }


CHICAGO95RC = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "chicago95rc")


def bevel_for_style(style):
    """The bevel palette a Start menu style implies when [Look] bevel is not set: 2000 or 1995."""
    return "2000" if style == "2000" else "1995"


def look_settings(path=None):
    """The look chosen in Setup, from ~/.config/chicago95rc.

    [StartMenu] style is 1995, 1998 or 2000. [Look] decoration, widgetStyle and bevel name the window
    frames, the controls and the bevel palette (1995 or 2000); a config without them is classic, with
    the bevel the Start menu style implies. [Branding] describes the "operating system" the screens
    show: osCompany (the small word above the name), osName ("Windows 2000", "Fedora 44"; its number
    is drawn thin), osEdition, tagline (the login banner's line under the edition), osLogo and
    companyLogo (image paths). Each falls back to the Start menu's
    banner text and logo, so a look without branding still has a name and a logo."""
    settings = configparser.ConfigParser(interpolation=None, strict=False)
    settings.read(path or CHICAGO95RC)

    def start_menu(key, default):
        return settings.get("StartMenu", key, fallback=default)

    def branding(key, default):
        return settings.get("Branding", key, fallback=default)

    logos = sorted(glob.glob(os.path.expanduser("~/.local/share/chicago95/start-logo.*")))
    banner_text = start_menu("bannerText", "Chicago95")
    style = start_menu("style", "1995")
    return {
        "style": style,
        "decoration": settings.get("Look", "decoration", fallback="classic"),
        "widgetStyle": settings.get("Look", "widgetStyle", fallback="classic"),
        "bevel": settings.get("Look", "bevel", fallback=bevel_for_style(style)),
        "bannerText": banner_text,
        "osCompany": branding("osCompany", ""),
        "osName": branding("osName", banner_text),
        "edition": branding("osEdition", start_menu("edition", "Professional")),
        "osLogo": branding("osLogo", logos[0] if logos else ""),
        "companyLogo": branding("companyLogo", ""),
        "tagline": branding("tagline", "Built on Linux Technology"),
    }


def short_os_name(name):
    """The name before its first digit ("Windows2026" -> "Windows"); the whole name when there is none."""
    return re.split(r"\d", name, maxsplit=1)[0].strip() or name


def fill_placeholders(text, look):
    """Replaces {os}, {osname}, {company}, {edition}, {user} and {computer} in a text from Setup."""
    import getpass
    import socket

    values = {
        "os": short_os_name(look["osName"]),
        "osname": look["osName"],
        "company": look["osCompany"],
        "edition": look["edition"],
        "user": getpass.getuser(),
        "computer": socket.gethostname(),
    }
    return re.sub(r"\{(os|osname|company|edition|user|computer)\}", lambda match: values[match.group(1)], text)


def icon_theme(path=None):
    """The icon set KDE uses ([Icons] Theme in kdeglobals): Chicago95, SE98 or ClassicOS-2000 per look."""
    settings = configparser.ConfigParser(interpolation=None, strict=False)
    settings.optionxform = str
    settings.read(path or KDEGLOBALS)
    return settings.get("Icons", "Theme", fallback="Chicago95")


def sound_file(theme, event, roots):
    """The sound a sound theme plays for an event: its own, else Chicago95's. Disabled sounds are skipped."""
    for theme_name in dict.fromkeys([theme, "Chicago95"]):
        for root in roots:
            sounds = glob.glob(os.path.join(glob.escape(os.path.join(root, theme_name, "stereo")), f"{event}.*"))
            enabled = sorted(path for path in sounds if not path.endswith(".disabled"))
            if enabled:
                return enabled[0]
    return None


def bevel_shades(face):
    """(light, shadow) for a face colour: halfway to white and two thirds of the face,
    as #DFDFDF and #808080 are for #C0C0C0."""
    light = QColor((face.red() + 255) // 2, (face.green() + 255) // 2, (face.blue() + 255) // 2)
    shadow = QColor(face.red() * 2 // 3, face.green() * 2 // 3, face.blue() * 2 // 3)
    return light, shadow


def bevel_colors(face, bevel):
    """The 3D lines around a face, as {light, shadow, dark}: the light line inside the white one, the
    shadow line inside the dark one. 1995 and 1998 derive light and shadow from the face (#DFDFDF and
    #808080 for #C0C0C0) with a black dark line; 2000 uses the face itself as light, #808080 and #404040."""
    if bevel == "2000":
        return {"light": QColor(face), "shadow": QColor("#808080"), "dark": QColor("#404040")}
    light, shadow = bevel_shades(face)
    return {"light": light, "shadow": shadow, "dark": QColor("#000000")}


SCHEME = read_scheme()
FACE, NAVY = SCHEME["face"], SCHEME["selection"]
LIGHT, SHADOW = bevel_shades(FACE)
TEAL = QColor("#008080")
UI_FONT_FAMILY = "MS W98 UI"
ICON_SEARCH_PATHS = [
    os.path.expanduser("~/.local/share/icons"),
    os.path.expanduser("~/.icons"),
    "/usr/share/icons",
    "/usr/share/pixmaps",
]


def instance_socket(name):
    return str(Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / f"{name}.sock")


def send_to_running(name, message, timeout_ms=500):
    """Hands the message to the tool's running instance; False when none listens."""
    from PySide6.QtNetwork import QLocalSocket

    socket = QLocalSocket()
    socket.connectToServer(instance_socket(name))
    if not socket.waitForConnected(timeout_ms):
        return False
    socket.write(message.encode())
    socket.waitForBytesWritten(timeout_ms)
    socket.disconnectFromServer()
    return True


class SingleInstance(QObject):
    """The running instance's end: on_message(text) for every message a later launch sends it."""

    def __init__(self, name, on_message, parent=None):
        from PySide6.QtNetwork import QLocalServer

        super().__init__(parent)
        self.on_message = on_message
        self.server = QLocalServer(self)
        QLocalServer.removeServer(instance_socket(name))
        self.server.listen(instance_socket(name))
        self.server.newConnection.connect(self.read_connection)

    def read_connection(self):
        connection = self.server.nextPendingConnection()
        if connection.bytesAvailable() or connection.waitForReadyRead(500):
            self.on_message(bytes(connection.readAll()).decode())
        connection.disconnectFromServer()


def quit_on_signals(app, *signal_numbers):
    """Quits the app on the given signals; keep the returned timer alive for as long as the app runs.

    Python only runs signal handlers between bytecodes, and an idle Qt event loop never returns to
    Python, so without the timer's no-op slot a SIGTERM waits forever (it hung logout once).
    """
    for number in signal_numbers or (signal.SIGTERM, signal.SIGINT):
        signal.signal(number, lambda *_: app.quit())
    wakeup = QTimer()
    wakeup.timeout.connect(lambda: None)
    wakeup.start(250)
    return wakeup


def retro_palette(scheme=None):
    """A Qt palette from the colour scheme; pass read_scheme() again to pick up a change made in System Settings."""
    scheme = scheme or SCHEME
    face, selection = scheme["face"], scheme["selection"]
    bevel = bevel_colors(face, look_settings()["bevel"])
    light, shadow, dark = bevel["light"], bevel["shadow"], bevel["dark"]
    palette = QPalette()
    for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
        palette.setColor(group, QPalette.Window, face)
        palette.setColor(group, QPalette.Button, face)
        palette.setColor(group, QPalette.Base, Qt.white)
        palette.setColor(group, QPalette.Text, Qt.black)
        palette.setColor(group, QPalette.WindowText, Qt.black)
        palette.setColor(group, QPalette.ButtonText, Qt.black)
        palette.setColor(group, QPalette.Highlight, selection)
        palette.setColor(group, QPalette.HighlightedText, scheme["selection_text"])
        palette.setColor(group, QPalette.Light, Qt.white)
        palette.setColor(group, QPalette.Midlight, light)
        palette.setColor(group, QPalette.Dark, shadow)
        palette.setColor(group, QPalette.Mid, shadow)
        palette.setColor(group, QPalette.Shadow, dark)
    # Disabled controls as the originals drew them: fields take the window colour instead of white, and
    # their text is engraved (shadow grey; the style lays a white copy a pixel down and right).
    palette.setColor(QPalette.Disabled, QPalette.Text, shadow)
    palette.setColor(QPalette.Disabled, QPalette.WindowText, shadow)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, shadow)
    palette.setColor(QPalette.Disabled, QPalette.Base, face)
    return palette


# The 2000 dialogs' small mark (Shut Down, Log On banners), in the original's pixels, measured from
# tests/references/w2kshutdown.png (tests/test_shutdown_reference.py): an orange frame (55x55, 4px
# edges) whose top-left fades into the paper, a darker frame behind it (2px lower, 2px further right),
# a pale blue glow to its right
# and a green bar under it that fade into the paper. The OS logo goes in front (BANNER_MARK_LOGO).
BANNER_MARK_SIZE = (116, 60)
BANNER_MARK_LOGO = QRectF(10, 8, 44, 36)
BANNER_ORANGE, BANNER_BACK_ORANGE = "#de5a00", "#d64200"


def edge_gradient(start, end, stops, paper):
    """A gradient from start to end through (position, colour) stops; "paper" stands for the paper colour."""
    gradient = QLinearGradient(*start, *end)
    for position, colour in stops:
        gradient.setColorAt(position, QColor(paper if colour == "paper" else colour))
    return gradient


def paint_banner_mark(painter, x, y, logo=None, paper="#ffffff"):
    """The generated frame and glows at (x, y), with the logo pixmap (if any) in front."""
    painter.save()
    painter.translate(x, y)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    clear = QColor(paper)
    clear.setAlpha(0)
    glow = QRadialGradient(0, 0, 46)
    for position, colour in ((0, QColor("#7ec2e2")), (0.3, QColor("#85c3e3")), (0.65, QColor("#c4e1f0")), (1, clear)):
        glow.setColorAt(position, colour)
    painter.save()
    painter.translate(66, 30)
    painter.scale(1, 24 / 46)
    painter.fillRect(QRectF(-46, -46, 92, 92), glow)
    painter.restore()
    painter.fillRect(
        QRectF(57, 49, 53, 8), edge_gradient((57, 0), (110, 0), ((0, "#add69c"), (0.3, "#d2e4c3"), (1, "paper")), paper)
    )
    painter.fillRect(
        QRectF(18, 57, 92, 4),
        edge_gradient(
            (18, 0),
            (110, 0),
            (
                (0, "paper"),
                (0.04, "#8cb96f"),
                (0.41, "#8cb96f"),
                (0.48, "#add69c"),
                (0.61, "#d2e4c1"),
                (0.74, "#e2efda"),
                (1, "paper"),
            ),
            paper,
        ),
    )
    painter.fillRect(QRectF(4, 2, 53, 55), QColor(BANNER_BACK_ORANGE))
    painter.fillRect(QRectF(0, 0, 55, 55), QColor(paper))
    painter.fillRect(
        QRectF(0, 0, 55, 4), edge_gradient((0, 0), (55, 0), ((0.6, "paper"), (0.72, BANNER_ORANGE)), paper)
    )
    painter.fillRect(
        QRectF(0, 0, 4, 55), edge_gradient((0, 0), (0, 55), ((0.67, "paper"), (0.82, BANNER_ORANGE)), paper)
    )
    painter.fillRect(
        QRectF(51, 0, 4, 55),
        edge_gradient(
            (0, 0), (0, 55), ((0.07, BANNER_ORANGE), (0.24, "paper"), (0.36, "paper"), (0.58, BANNER_ORANGE)), paper
        ),
    )
    painter.fillRect(QRectF(0, 51, 55, 4), QColor(BANNER_ORANGE))
    if logo is not None and not logo.isNull():
        size = logo.size().scaled(BANNER_MARK_LOGO.size().toSize(), Qt.KeepAspectRatio)
        target = QRectF(0, 0, size.width(), size.height())
        target.moveCenter(BANNER_MARK_LOGO.center())
        painter.drawPixmap(target, logo, QRectF(logo.rect()))
    painter.restore()


def draw_heavy_text(painter, x, baseline, font, text, colour, embolden, smooth=True):
    """Lettering heavier than any common bold (the 2000 name and wordmarks): the letters filled and
    outlined too, so strokes grow by embolden pixels; smooth gives them soft (feathered) edges."""
    path = QPainterPath()
    path.addText(x, baseline, font, text)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, smooth)
    painter.fillPath(path, colour)
    painter.setPen(QPen(colour, embolden))
    painter.drawPath(path)
    painter.restore()


def screen_scale():
    """The screen's scale as the compositor sets it: 1.5 on a 1.5x screen. Qt's own device pixel ratio
    rounds that up to 2 on Wayland, which would pass for a whole scale."""
    return float(detect_scale())


import functools

screen_scale = functools.lru_cache(maxsize=None)(screen_scale)  # kscreen-doctor is asked once per process


def ui_font(pixel_size=11, bold=False):
    """The UI font at the originals' size: MS Sans Serif 8 points, 11px. The pixel font is drawn on an
    11px grid; at any other size its letters land on fractional pixels and space unevenly. On a whole
    scale (1x, 2x) the grid lands on screen pixels and it is drawn unsmoothed, with hard edges; on 1.5x
    it is left to fontconfig, which smooths it (config/fontconfig/60-chicago95-pixel-font.conf)."""
    family = UI_FONT_FAMILY if UI_FONT_FAMILY in QFontDatabase.families() else "Noto Sans"
    font = QFont(family)
    font.setPixelSize(pixel_size)
    font.setBold(bold)
    if family == UI_FONT_FAMILY:  # said either way: a font that leaves it open inherits the application font's choice
        font.setStyleStrategy(QFont.NoAntialias if float(screen_scale()).is_integer() else QFont.PreferAntialias)
    return font


def make_app(app_name):
    # Pass the fractional compositor scale through instead of rounding 1.5 up to 2.
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setDesktopFileName(app_name)
    app.setApplicationName(app_name)
    app.setStyle(classic_style())
    app.setPalette(retro_palette())
    app.setFont(ui_font())
    QIcon.setThemeSearchPaths(ICON_SEARCH_PATHS + QIcon.themeSearchPaths())
    QIcon.setThemeName(icon_theme())
    return app


DIALOG_BUTTON_SIZE = (75, 23)


TASK_BUTTON_HEIGHT, TASK_ICON_LEFT, TASK_ICON_TOP, TASK_LABEL_TOP = 22, 4, 3, 6
TASK_LABEL_LEFT = {"2000": 22}  # else 23: Tahoma has no blank column before its capitals


def paint_task_button(painter, rect, caption, icon, pressed, look, face=None):
    """One taskbar button as the originals draw it and as the taskbar plasmoid does (TaskButton.qml,
    tests/test_plasma_taskbar_reference.py): a 2px bevel, raised, or sunken over a white row and a white
    and face checkerboard when pressed; the icon 16px at 4,3 and the title from 23px, a pixel lower while
    pressed, bold for the active window."""
    face = face or SCHEME["face"]
    bevel_key = bevel_for_style(look)
    bevel = bevel_colors(face, bevel_key)
    white = QColor("#ffffff")
    rings = (
        [(bevel["dark"], white), (bevel["shadow"], bevel["light"])]
        if pressed
        else [(white, bevel["dark"]), (bevel["light"], bevel["shadow"])]
    )
    painter.fillRect(rect, face)
    for depth, (top_left, bottom_right) in enumerate(rings):
        edge = rect.adjusted(depth, depth, -depth, -depth)
        painter.fillRect(edge.left(), edge.top(), edge.width(), 1, top_left)
        painter.fillRect(edge.left(), edge.top(), 1, edge.height(), top_left)
        painter.fillRect(edge.left(), edge.bottom(), edge.width(), 1, bottom_right)
        painter.fillRect(edge.right(), edge.top(), 1, edge.height(), bottom_right)
    if pressed:
        inside = rect.adjusted(2, 2, -2, -2)
        painter.fillRect(inside.left(), inside.top(), inside.width(), 1, white)
        for y in range(inside.top() + 1, inside.bottom() + 1):
            for x in range(inside.left() + (y - inside.top() - 1) % 2, inside.right() + 1, 2):
                painter.fillRect(x, y, 1, 1, white)
    shift = 1 if pressed else 0
    if icon is not None:
        icon.paint(painter, rect.left() + TASK_ICON_LEFT, rect.top() + TASK_ICON_TOP + shift, 16, 16)
    painter.setFont(ui_font(11, bold=pressed))
    painter.setPen(QColor("#000000"))
    label_left = rect.left() + TASK_LABEL_LEFT.get(bevel_key, 23)
    label = QRect(label_left, rect.top() + TASK_LABEL_TOP + shift, max(0, rect.right() - 3 - label_left), 14)
    painter.drawText(
        label,
        Qt.AlignLeft | Qt.AlignTop,
        QFontMetrics(painter.font()).elidedText(caption, Qt.ElideRight, label.width()),
    )


_GREY_PIXMAPS = {}


def grey_pixmap(pixmap):
    """The pixmap in greys, its transparency kept: Internet Explorer 4's toolbar icons until the pointer is
    over them."""
    key = (pixmap.cacheKey(), pixmap.devicePixelRatio())
    if key not in _GREY_PIXMAPS:
        image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        for y in range(image.height()):
            for x in range(image.width()):
                colour = image.pixelColor(x, y)
                grey = (colour.red() * 299 + colour.green() * 587 + colour.blue() * 114) // 1000
                image.setPixelColor(x, y, QColor(grey, grey, grey, colour.alpha()))
        _GREY_PIXMAPS[key] = QPixmap.fromImage(image)
        _GREY_PIXMAPS[key].setDevicePixelRatio(pixmap.devicePixelRatio())
    return _GREY_PIXMAPS[key]


def dialog_button(caption, enabled=True):
    button = QPushButton(caption)
    button.setFixedSize(*DIALOG_BUTTON_SIZE)
    button.setEnabled(enabled)
    return button


# The check box and radio button indicators, pixel for pixel from the 1998 original
# (tests/test_qt_controls_reference.py): s shadow, K black, l light, W white, . the window colour.
CHECK_BOX = ["ssssssssssssW", "sKKKKKKKKKKlW"] + ["sKiiiiiiiiilW"] * 9 + ["slllllllllllW", "WWWWWWWWWWWWW"]
CHECK_MARK = [
    "WWWWWWWWW",
    "WWWWWWWKW",
    "WWWWWWKKW",
    "WKWWWKKKW",
    "WKKWKKKWW",
    "WKKKKKWWW",
    "WWKKKWWWW",
    "WWWKWWWWW",
    "WWWWWWWWW",
]
RADIO_BUTTON = [
    "....ssss....",
    "..ssKKKKss..",
    ".sKKiiiiKKW.",
    ".sKiiiiiilW.",
    "sKiiiiiiiilW",
    "sKiiiiiiiilW",
    "sKiiiiiiiilW",
    "sKiiiiiiiilW",
    ".sKiiiiiilW.",
    ".slliiiillW.",
    "..WWllllWW..",
    "....WWWW....",
]
DROP_DOWN_ARROW = ["KKKKKKK", ".KKKKK.", "..KKK..", "...K..."]
RADIO_DOT = [(5, 4), (6, 4), (4, 5), (5, 5), (6, 5), (7, 5), (4, 6), (5, 6), (6, 6), (7, 6), (5, 7), (6, 7)]


def paint_bitmap(painter, left, top, rows, colours):
    for y, row in enumerate(rows):
        for x, key in enumerate(row):
            if colours.get(key) is not None:
                painter.fillRect(left + x, top + y, 1, 1, colours[key])


def slider_handle_inside(width, height, horizontal, pointed_start, pointed_end):
    """The pixels inside a slider handle's 2px bevel, in handle coordinates: Qt's Windows-style handle is a
    rectangle, drawn to a point on the side its tick marks are on (the point is half the handle's width high)."""
    across, along = (width, height) if horizontal else (height, width)
    point = across // 2 if pointed_start != pointed_end else 0
    body_from = point if pointed_start else 2
    body_to = along - 1 - (point if pointed_end else 2)
    cells = [(a, b) for b in range(body_from, body_to + 1) for a in range(2, across - 2)]
    for step in range(point):
        inset = 3 + step
        for a in range(inset, across - inset):
            if pointed_end:
                cells.append((a, body_to + 1 + step))
            if pointed_start:
                cells.append((a, body_from - 1 - step))
    return [(a, b) if horizontal else (b, a) for a, b in cells]


def is_drop_down_list(widget):
    return widget is not None and widget.window().inherits("QComboBoxPrivateContainer")


# A horizontal track bar as the originals drew it, 1:1 from tests/references/win98mouse.png: an 11x21 thumb pointing at
# its tick marks, over a 4-row groove; ticks are 2 rows tall, a row below the point. ' ' is outside the thumb.
SLIDER_THUMB = (
    "WWWWWWWWWWK",
    *["W........SK"] * 15,
    " W......SK ",
    "  W....SK  ",
    "   W..SK   ",
    "    WSK    ",
    "     K     ",
)
SLIDER_GROOVE_TOP, SLIDER_TICK_GAP, SLIDER_TICK_ROWS = 7, 1, 2
# A group box's title, from three originals: its ink starts 10 pixels in, a row lower than Qt puts it;
# the top line stops
# 3 pixels before the ink and starts again 2 after the text (tests/test_control_panel_components_reference.py).
GROUP_TITLE_INK, GROUP_TITLE_DROP, GROUP_LINE_BEFORE, GROUP_LINE_AFTER = 10, 1, 3, 2
RADIO_CAPTION_SHIFT, RADIO_CAPTION_DROP, RADIO_FOCUS_INSETS, RADIO_CAPTION_GAP = 1, 1, (0, -2, 1, 1), 16
# A spin box as Windows 98 built it, 1:1 from tests/references/win98datetime01.png: a 21-row sunken edit field with a
# separate up-down control beside it, outside its border: two 16x10 buttons, each with a 1-3 pixel arrow.
SPIN_HEIGHT, SPIN_BUTTON = 21, (16, 10)
SPIN_BUTTON_FACE = (  # L is the 3D light: face in the 16-colour capture, DFDFDF in true colour
    "LLLLLLLLLLLLLLLK",
    "LWWWWWWWWWWWWWSK",
    *["LW............SK"] * 6,
    "LSSSSSSSSSSSSSSK",
    "KKKKKKKKKKKKKKKK",
)
SPIN_BUTTON_PUSHED = (
    "SSSSSSSSSSSSSSSS",
    *["S..............S"] * 8,
    "SSSSSSSSSSSSSSSS",
)
SPIN_ARROW_UP, SPIN_ARROW_DOWN, SPIN_ARROW_AT = (".K.", "KKK"), ("KKK", ".K."), (6, 4)
# The originals' size grip (tests/test_status_bar_reference.py): a face square in the last pane's corner.
SIZE_GRIP = (
    "...........W.",
    "..........WS.",
    ".........WSS.",
    "........WSS..",
    ".......WSS.W.",
    "......WSS.WS.",
    ".....WSS.WSS.",
    "....WSS.WSS..",
    "...WSS.WSS.W.",
    "..WSS.WSS.WS.",
    ".WSS.WSS.WSS.",
    "WSS.WSS.WSS..",
    ".............",
)


@functools.lru_cache(maxsize=512)
def caption_ink_width(text, font_key):
    """How wide a caption's ink is, drawn once: the UI font keeps its glyphs' spacing on their right, so its advance
    widths overstate the ink and centring on them pulls captions left of where the originals put them."""
    font = QFont()
    font.fromString(font_key)
    metrics = QFontMetrics(font)
    image = QImage(metrics.horizontalAdvance(text) + 4, metrics.height() + 4, QImage.Format_RGB32)
    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    painter.setFont(font)
    painter.setPen(QColor("#000000"))
    painter.drawText(image.rect(), Qt.AlignLeft | Qt.AlignTop | Qt.TextHideMnemonic, text)
    painter.end()
    inked = [x for x in range(image.width()) if any(image.pixelColor(x, y).red() < 128 for y in range(image.height()))]
    return inked[-1] - inked[0] + 1 if inked else 0


def slider_tick_values(minimum, maximum, interval, single_step, page_step, span):
    """The values a slider marks with ticks, as Qt's common style picks them."""
    step = interval if interval > 0 else single_step
    if maximum > minimum and step * span / (maximum - minimum) < 3:
        step = page_step
    step = max(step, 1)
    return list(range(minimum, maximum + 1, step))


# The classic tab control (tests/test_tab_control.py, measured in tests/references/win98mouse.png): a tab is its caption
# plus 6 pixels each side and at least 42 wide, 18 rows tall; the selected one rises 2 rows, spreads 2 pixels each side
# and covers 2 rows of the page frame; the first tab starts 2 pixels inside the page frame.
TAB_ROW_HEIGHT, TAB_RISE, TAB_SEAM, TAB_CAPTION_TOP = 18, 2, 2, 5
TAB_PADDING, TAB_MIN_WIDTH, TAB_INSET, TAB_SPREAD = 6, 42, 2, 2
TAB_HEIGHT = TAB_ROW_HEIGHT + TAB_RISE + TAB_SEAM


def tab_width(metrics, caption):
    return max(metrics.horizontalAdvance(caption) + TAB_PADDING * 2, TAB_MIN_WIDTH)


def paint_tab(painter, rect, palette, selected):
    """A tab as the originals draw it: a white left edge and top with a two-step corner, a grey-and-black right
    edge; the selected tab also hides the page frame under it and runs its edges down to meet the frame."""
    face, light, shadow, dark = (
        palette.window().color(),
        palette.light().color(),
        palette.dark().color(),
        palette.shadow().color(),
    )
    left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
    seam = TAB_SEAM if selected else 0
    painter.fillRect(rect.adjusted(0, 0, 0, seam), face)
    painter.fillRect(left + 2, top, rect.width() - 4, 1, light)
    painter.fillRect(left + 1, top + 1, 1, 1, light)
    painter.fillRect(left, top + 2, 1, bottom - top - 1 + seam, light)
    painter.fillRect(right - 1, top + 1, 1, 1, dark)
    painter.fillRect(right - 1, top + 2, 1, bottom - top - 1 + seam // 2, shadow)
    painter.fillRect(right, top + 2, 1, bottom - top - 1 + seam // 2, dark)


def paint_tab_caption(painter, rect, palette, caption, enabled=True):
    """The caption centred in the tab's padding, one column right of it (the originals' bitmap font's side bearing)."""
    metrics = painter.fontMetrics()
    left = rect.left() + TAB_PADDING + 1 + (rect.width() - TAB_PADDING * 2 - metrics.horizontalAdvance(caption)) // 2
    painter.setPen((palette.windowText() if enabled else palette.mid()).color())
    painter.drawText(left, rect.top() + TAB_CAPTION_TOP + metrics.ascent(), caption)


def tab_rects(option):
    """(shape rect, caption rect) for Qt's tab: the first and last tab carry the inset to the page frame, an
    unselected tab starts 2 rows down and ends above the page frame, the selected one spreads over its neighbours."""
    first = option.position in (option.TabPosition.Beginning, option.TabPosition.OnlyOneTab)
    last = option.position in (option.TabPosition.End, option.TabPosition.OnlyOneTab)
    base = option.rect.adjusted(TAB_INSET if first else 0, 0, -TAB_INSET if last else 0, -TAB_SEAM)
    if option.state & QStyle.State_Selected:
        return base.adjusted(-TAB_SPREAD, 0, TAB_SPREAD, 0), base
    return base.adjusted(0, TAB_RISE, 0, 0), base.adjusted(0, TAB_RISE, 0, 0)


class ClassicStyle(QProxyStyle):
    """Qt's Windows style with the originals' details: a pressed button has a black frame on every side
    and a shadow frame inside it (tests/test_control_panel_components_reference.py); check boxes and radio
    buttons are the 1998 original's bitmaps; a tab's caption keeps its top row; a closed drop-down's field
    is white to its frame (tests/test_qt_controls_reference.py)."""

    PRESSED_PANELS = (QStyle.PE_PanelButtonCommand, QStyle.PE_PanelButtonBevel)

    def indicator_colours(self, option):
        palette = option.palette
        enabled = bool(option.state & QStyle.State_Enabled)
        return {
            "s": palette.dark().color(),
            "K": palette.shadow().color(),
            "l": palette.midlight().color(),
            "W": palette.light().color(),
            "i": palette.base().color() if enabled else palette.window().color(),
            ".": None,
            "mark": palette.text().color() if enabled else palette.dark().color(),
        }

    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PE_FrameFocusRect and is_drop_down_list(widget):
            return
        if element == QStyle.PE_IndicatorCheckBox:
            colours = self.indicator_colours(option)
            left, top = (
                option.rect.left() + (option.rect.width() - 13) // 2,
                option.rect.top() + (option.rect.height() - 13) // 2,
            )
            paint_bitmap(painter, left, top, CHECK_BOX, colours)
            if option.state & QStyle.State_On:
                paint_bitmap(painter, left + 2, top + 2, CHECK_MARK, {"K": colours["mark"]})
            return
        if element == QStyle.PE_IndicatorRadioButton:
            colours = self.indicator_colours(option)
            left, top = (
                option.rect.left() + (option.rect.width() - 12) // 2,
                option.rect.top() + (option.rect.height() - 12) // 2,
            )
            paint_bitmap(painter, left, top, RADIO_BUTTON, colours)
            if option.state & QStyle.State_On:
                for x, y in RADIO_DOT:
                    painter.fillRect(left + x, top + y, 1, 1, colours["mark"])
            return
        if element == QStyle.PE_FrameLineEdit:
            # A field's sunken frame: shadow and black outside and inside at the top left, light grey and
            # white at the bottom right (Qt puts the button colour where the light grey goes).
            palette, rect = option.palette, option.rect
            for depth, (top_left, bottom_right) in enumerate(
                (
                    (palette.dark().color(), palette.light().color()),
                    (palette.shadow().color(), palette.midlight().color()),
                )
            ):
                inner = rect.adjusted(depth, depth, -depth, -depth)
                painter.fillRect(inner.left(), inner.top(), inner.width() - 1, 1, top_left)
                painter.fillRect(inner.left(), inner.top(), 1, inner.height() - 1, top_left)
                painter.fillRect(inner.left(), inner.bottom(), inner.width(), 1, bottom_right)
                painter.fillRect(inner.right(), inner.top(), 1, inner.height(), bottom_right)
            return
        if element in self.PRESSED_PANELS and option.state & QStyle.State_Sunken:
            rect = option.rect
            painter.fillRect(rect, option.palette.button())
            painter.setPen(option.palette.shadow().color())
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            painter.setPen(option.palette.dark().color())
            painter.drawRect(rect.adjusted(1, 1, -2, -2))
            return
        super().drawPrimitive(element, option, painter, widget)

    def drawControl(self, element, option, painter, widget=None):
        if element == QStyle.CE_RadioButton:
            self.draw_classic_radio_button(option, painter, widget)
            return
        if element == QStyle.CE_SizeGrip:
            palette = option.palette
            paint_bitmap(
                painter,
                option.rect.right() + 1 - len(SIZE_GRIP[0]),
                option.rect.bottom() + 1 - len(SIZE_GRIP),
                SIZE_GRIP,
                {"W": palette.light().color(), ".": palette.button().color(), "S": palette.dark().color()},
            )
            return
        if element == QStyle.CE_PushButtonLabel and option.text and option.icon.isNull():
            # Centred on the caption's ink, as the originals' captions are
            # (tests/test_control_panel_components_reference.py).
            font = widget.font() if widget else painter.font()
            ink = caption_ink_width(
                option.text.replace("&&", "\0").replace("&", "").replace("\0", "&"), font.toString()
            )
            left = option.rect.left() + (option.rect.width() - ink + 1) // 2
            label = QRect(left, option.rect.top(), option.rect.right() - left + 1, option.rect.height())
            if option.state & (QStyle.State_Sunken | QStyle.State_On):
                label.translate(
                    self.pixelMetric(QStyle.PM_ButtonShiftHorizontal, option, widget),
                    self.pixelMetric(QStyle.PM_ButtonShiftVertical, option, widget),
                )
            self.drawItemText(
                painter,
                label,
                Qt.AlignLeft | Qt.AlignVCenter | Qt.TextShowMnemonic,
                option.palette,
                bool(option.state & QStyle.State_Enabled),
                option.text,
                QPalette.ButtonText,
            )
            return
        if element in (QStyle.CE_TabBarTabShape, QStyle.CE_TabBarTabLabel) and option.shape == QTabBar.RoundedNorth:
            shape, caption = tab_rects(option)
            if element == QStyle.CE_TabBarTabShape:
                paint_tab(painter, shape, option.palette, bool(option.state & QStyle.State_Selected))
            else:
                paint_tab_caption(
                    painter, caption, option.palette, option.text, bool(option.state & QStyle.State_Enabled)
                )
            return
        # A checked item of an exclusive group carries a round bullet, as the originals' menus do, not a tick.
        if element == QStyle.CE_MenuItem and option.checkType == option.CheckType.Exclusive and option.checked:
            plain = type(option)(option)
            plain.checked = False
            super().drawControl(element, plain, painter, widget)
            selected = option.state & QStyle.State_Selected
            colour = (option.palette.highlightedText() if selected else option.palette.text()).color()
            left = option.rect.left() + 6
            top = option.rect.top() + (option.rect.height() - 4) // 2
            for row, (inset, width) in enumerate(((1, 2), (0, 4), (0, 4), (1, 2))):
                painter.fillRect(left + inset, top + row, width, 1, colour)
            return
        super().drawControl(element, option, painter, widget)

    def classic_slider(self, option):
        from PySide6.QtWidgets import QSlider

        return option.orientation == Qt.Horizontal and option.tickPosition in (QSlider.NoTicks, QSlider.TicksBelow)

    def slider_handle_left(self, option):
        return QStyle.sliderPositionFromValue(
            option.minimum,
            option.maximum,
            option.sliderPosition,
            option.rect.width() - len(SLIDER_THUMB[0]),
            option.upsideDown,
        )

    def draw_classic_slider(self, option, painter):
        from PySide6.QtWidgets import QSlider

        left, top, width = option.rect.left(), option.rect.top(), option.rect.width()
        white, shadow, black, face = (
            QColor("#FFFFFF"),
            option.palette.dark().color(),
            QColor("#000000"),
            option.palette.window().color(),
        )
        groove = top + SLIDER_GROOVE_TOP
        right = left + width - 1
        painter.fillRect(left, groove, right - left, 1, shadow)
        painter.fillRect(right, groove, 1, 3, white)
        painter.fillRect(left, groove + 1, 1, 2, shadow)
        painter.fillRect(left + 1, groove + 1, right - left - 2, 1, black)
        painter.fillRect(left, groove + 3, right - left + 1, 1, white)
        span = width - len(SLIDER_THUMB[0])
        if option.tickPosition == QSlider.TicksBelow:
            tick_top = top + len(SLIDER_THUMB) + SLIDER_TICK_GAP
            for value in slider_tick_values(
                option.minimum, option.maximum, option.tickInterval, option.singleStep, option.pageStep, span
            ):
                x = (
                    left
                    + QStyle.sliderPositionFromValue(option.minimum, option.maximum, value, span, option.upsideDown)
                    + len(SLIDER_THUMB[0]) // 2
                )
                painter.fillRect(x, tick_top, 1, SLIDER_TICK_ROWS, black)
        paint_bitmap(
            painter,
            left + self.slider_handle_left(option),
            top,
            SLIDER_THUMB,
            {"W": white, ".": face, "S": shadow, "K": black},
        )

    def draw_classic_group_box(self, option, painter, widget):
        frame_rect = self.subControlRect(QStyle.CC_GroupBox, option, QStyle.SC_GroupBoxFrame, widget)
        label = self.subControlRect(QStyle.CC_GroupBox, option, QStyle.SC_GroupBoxLabel, widget)
        text_width = QFontMetrics(widget.font() if widget else painter.font()).horizontalAdvance(
            option.text.replace("&", "")
        )
        ink_left = frame_rect.left() + GROUP_TITLE_INK
        # A row above and below the frame's two rows as well: at a fractional screen scale the rows round
        # onto other device pixels than a two-row gap would, and a line would show under the title.
        gap = QRect(
            ink_left - GROUP_LINE_BEFORE,
            frame_rect.top() - 1,
            label.left() + text_width + GROUP_LINE_AFTER - (ink_left - GROUP_LINE_BEFORE),
            4,
        )
        frame = QStyleOptionFrame()
        frame.rect = frame_rect
        frame.palette = option.palette
        frame.state = option.state | QStyle.State_Sunken
        frame.lineWidth, frame.midLineWidth = option.lineWidth, option.midLineWidth
        frame.features = option.features
        painter.save()
        painter.setClipRegion(QRegion(option.rect).subtracted(QRegion(gap)))
        self.drawPrimitive(QStyle.PE_FrameGroupBox, frame, painter, widget)
        painter.restore()
        enabled = bool(option.state & QStyle.State_Enabled)
        self.drawItemText(
            painter,
            label,
            Qt.TextShowMnemonic | Qt.AlignLeft | Qt.AlignTop,
            option.palette,
            enabled,
            option.text,
            QPalette.WindowText,
        )

    def draw_classic_spin_box(self, option, painter, widget):
        white, shadow, black = QColor("#FFFFFF"), option.palette.dark().color(), QColor("#000000")
        face, light = option.palette.window().color(), option.palette.midlight().color()
        enabled = bool(option.state & QStyle.State_Enabled)
        field = self.subControlRect(QStyle.CC_SpinBox, option, QStyle.SC_SpinBoxFrame, widget)
        painter.fillRect(option.rect, face)
        painter.fillRect(field.adjusted(2, 2, -2, -2), option.palette.base() if enabled else option.palette.window())
        painter.fillRect(field.left(), field.top(), field.width() - 1, 1, shadow)
        painter.fillRect(field.left(), field.top(), 1, field.height() - 1, shadow)
        painter.fillRect(field.left() + 1, field.top() + 1, field.width() - 3, 1, black)
        painter.fillRect(field.left() + 1, field.top() + 1, 1, field.height() - 3, black)
        painter.fillRect(field.right() - 1, field.top() + 1, 1, field.height() - 2, light)
        painter.fillRect(field.left() + 1, field.bottom() - 1, field.width() - 2, 1, light)
        painter.fillRect(field.right(), field.top(), 1, field.height(), white)
        painter.fillRect(field.left(), field.bottom(), field.width(), 1, white)
        for sub_control, arrow, step_enabled in (
            (QStyle.SC_SpinBoxUp, SPIN_ARROW_UP, QAbstractSpinBox.StepUpEnabled),
            (QStyle.SC_SpinBoxDown, SPIN_ARROW_DOWN, QAbstractSpinBox.StepDownEnabled),
        ):
            button = self.subControlRect(QStyle.CC_SpinBox, option, sub_control, widget)
            pushed = bool(option.activeSubControls & sub_control and option.state & QStyle.State_Sunken)
            paint_bitmap(
                painter,
                button.left(),
                button.top(),
                SPIN_BUTTON_PUSHED if pushed else SPIN_BUTTON_FACE,
                {"W": white, "S": shadow, "K": black, ".": face, "L": light},
            )
            left, top = button.left() + SPIN_ARROW_AT[0] + pushed, button.top() + SPIN_ARROW_AT[1] + pushed
            if enabled and option.stepEnabled & step_enabled:
                paint_bitmap(painter, left, top, arrow, {"K": black})
            else:
                paint_bitmap(painter, left + 1, top + 1, arrow, {"K": white})
                paint_bitmap(painter, left, top, arrow, {"K": shadow})

    def drawComplexControl(self, control, option, painter, widget=None):
        if control == QStyle.CC_SpinBox:
            self.draw_classic_spin_box(option, painter, widget)
            return
        if control == QStyle.CC_GroupBox and option.text and not option.subControls & QStyle.SC_GroupBoxCheckBox:
            self.draw_classic_group_box(option, painter, widget)
            return
        if control == QStyle.CC_Slider and self.classic_slider(option):
            self.draw_classic_slider(option, painter)
            if not option.state & QStyle.State_Enabled:
                self.dither_disabled_slider_handle(option, painter, widget)
            return
        super().drawComplexControl(control, option, painter, widget)
        # A drop-down's field is white up to its 2px frame, and the window colour when disabled; Qt leaves the
        # button colour there, and a ring of it around the field (around the line edit of an editable one).
        if control == QStyle.CC_ComboBox:
            arrow = self.subControlRect(QStyle.CC_ComboBox, option, QStyle.SC_ComboBoxArrow, widget)
            inside = option.rect.adjusted(2, 2, -2, -2)
            inside.setRight(arrow.left() - 1)
            painter.fillRect(
                inside, option.palette.base() if option.state & QStyle.State_Enabled else option.palette.window()
            )
            if option.state & QStyle.State_HasFocus and not option.editable:
                self.paint_drop_down_focus(option, painter, inside.adjusted(1, 1, -1, -1))
            self.paint_drop_down_arrow(option, painter, arrow)
            self.paint_drop_down_light_edges(option, painter, arrow)
        if (
            control == QStyle.CC_Slider
            and not option.state & QStyle.State_Enabled
            and option.subControls & QStyle.SC_SliderHandle
        ):
            self.dither_disabled_slider_handle(option, painter, widget)

    def dither_disabled_slider_handle(self, option, painter, widget):
        """The classic track bar greys its thumb with the 50% dither (tests/test_qt_controls_reference.py)."""
        from PySide6.QtWidgets import QSlider

        handle = self.subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, widget)
        ticks = option.tickPosition
        above, below = (
            ticks in (QSlider.TicksAbove, QSlider.TicksBothSides),
            ticks in (QSlider.TicksBelow, QSlider.TicksBothSides),
        )
        horizontal = option.orientation == Qt.Horizontal
        for x, y in slider_handle_inside(handle.width(), handle.height(), horizontal, above, below):
            if (x + y) % 2 == 0:
                painter.fillRect(handle.left() + x, handle.top() + y, 1, 1, option.palette.light())

    def paint_drop_down_light_edges(self, option, painter, button):
        """The sunken field's inner bottom and right edges and the arrow button's outer top and left edges are the 3D
        light, as Windows drew them (tests/test_control_panel_components_reference.py); Qt leaves the face there."""
        light, rect = option.palette.midlight().color(), option.rect
        painter.fillRect(rect.left() + 1, rect.bottom() - 1, rect.width() - 2, 1, light)
        painter.fillRect(rect.right() - 1, rect.top() + 1, 1, rect.height() - 2, light)
        if option.state & QStyle.State_Sunken:
            return
        painter.fillRect(button.left(), button.top(), button.width() - 1, 1, light)
        painter.fillRect(button.left(), button.top(), 1, button.height() - 1, light)

    def paint_drop_down_focus(self, option, painter, focus):
        """The focused drop-down's field, as the originals drew it (tests/references/win98datetime04.png): the highlight
        a pixel inside the white, and on its edge the dotted focus rectangle, every other dot inverted, the rest
        black."""
        highlight = option.palette.highlight().color()
        painter.fillRect(focus, highlight)
        inverted = QColor(255 - highlight.red(), 255 - highlight.green(), 255 - highlight.blue())
        origin = option.rect.topLeft()
        edge = [(x, y) for x in range(focus.left(), focus.right() + 1) for y in (focus.top(), focus.bottom())]
        edge += [(x, y) for y in range(focus.top() + 1, focus.bottom()) for x in (focus.left(), focus.right())]
        for x, y in edge:
            painter.fillRect(x, y, 1, 1, inverted if (x - origin.x() + y - origin.y()) % 2 == 0 else QColor("#000000"))

    def paint_drop_down_arrow(self, option, painter, button):
        """The originals' 7-5-3-1 arrow in the middle of the button; disabled, engraved."""
        painter.fillRect(button.adjusted(2, 2, -2, -2), option.palette.button())
        pushed = 1 if option.state & QStyle.State_Sunken else 0
        left = button.left() + (button.width() - 7) // 2 + pushed
        top = button.top() + (button.height() - 5) // 2 + pushed
        if option.state & QStyle.State_Enabled:
            paint_bitmap(painter, left, top, DROP_DOWN_ARROW, {"K": option.palette.buttonText().color()})
            return
        paint_bitmap(painter, left + 1, top + 1, DROP_DOWN_ARROW, {"K": option.palette.light().color()})
        paint_bitmap(painter, left, top, DROP_DOWN_ARROW, {"K": option.palette.dark().color()})

    def subControlRect(self, control, option, sub_control, widget=None):
        if control == QStyle.CC_SpinBox:
            rect = option.rect
            button_width, button_height = SPIN_BUTTON
            field = QRect(rect.left(), rect.top(), rect.width() - button_width, rect.height())
            spin_rects = {
                QStyle.SC_SpinBoxFrame: field,
                QStyle.SC_SpinBoxEditField: field.adjusted(2, 2, -2, -2),
                QStyle.SC_SpinBoxUp: QRect(field.right() + 1, rect.top(), button_width, button_height),
                QStyle.SC_SpinBoxDown: QRect(
                    field.right() + 1, rect.top() + button_height, button_width, button_height
                ),
            }
            if sub_control in spin_rects:
                return spin_rects[sub_control]
        if control == QStyle.CC_GroupBox and sub_control == QStyle.SC_GroupBoxLabel and option.text:
            label = super().subControlRect(control, option, sub_control, widget)
            frame = super().subControlRect(control, option, QStyle.SC_GroupBoxFrame, widget)
            return label.translated(frame.left() + GROUP_TITLE_INK - label.left(), GROUP_TITLE_DROP)
        if control == QStyle.CC_Slider and self.classic_slider(option):
            if sub_control == QStyle.SC_SliderHandle:
                return QRect(
                    option.rect.left() + self.slider_handle_left(option),
                    option.rect.top(),
                    len(SLIDER_THUMB[0]),
                    len(SLIDER_THUMB),
                )
            if sub_control == QStyle.SC_SliderGroove:
                return QRect(option.rect.left(), option.rect.top() + SLIDER_GROOVE_TOP, option.rect.width(), 4)
        return super().subControlRect(control, option, sub_control, widget)

    def sizeFromContents(self, contents, option, size, widget=None):
        if contents == QStyle.CT_TabBarTab and option.shape == QTabBar.RoundedNorth:
            insets = (option.position in (option.TabPosition.Beginning, option.TabPosition.OnlyOneTab)) + (
                option.position in (option.TabPosition.End, option.TabPosition.OnlyOneTab)
            )
            return QSize(tab_width(option.fontMetrics, option.text) + insets * TAB_INSET, TAB_HEIGHT)
        if contents == QStyle.CT_SpinBox:
            return QSize(size.width() + SPIN_BUTTON[0] + 4, SPIN_HEIGHT)
        if contents == QStyle.CT_Slider and self.classic_slider(option):
            from PySide6.QtWidgets import QSlider

            ticks = SLIDER_TICK_GAP + SLIDER_TICK_ROWS if option.tickPosition == QSlider.TicksBelow else 0
            return QSize(size.width(), len(SLIDER_THUMB) + ticks)
        grown = super().sizeFromContents(contents, option, size, widget)
        if contents == QStyle.CT_ComboBox:
            grown.setHeight(grown.height() + 1)  # the originals' lists are a row taller than Qt's
        return grown

    def draw_classic_radio_button(self, option, painter, widget):
        """The circle where Qt puts it; the caption a pixel lower and closer to it than Qt's, and the focus
        rectangle hugging the caption's ink (tests/test_mouse_page.py, from Mouse Properties)."""
        from PySide6.QtWidgets import QStyleOptionButton, QStyleOptionFocusRect

        indicator = QStyleOptionButton(option)
        indicator.rect = self.subElementRect(QStyle.SE_RadioButtonIndicator, option, widget)
        self.drawPrimitive(QStyle.PE_IndicatorRadioButton, indicator, painter, widget)
        # A widget's "captionGap" property asks for the caption further from the circle than the usual
        # RADIO_CAPTION_GAP, as some originals space theirs.
        wider = (widget.property("captionGap") or RADIO_CAPTION_GAP) - RADIO_CAPTION_GAP if widget else 0
        label = QStyleOptionButton(option)
        label.rect = self.subElementRect(QStyle.SE_RadioButtonContents, option, widget).translated(
            wider - RADIO_CAPTION_SHIFT, RADIO_CAPTION_DROP
        )
        self.drawControl(QStyle.CE_RadioButtonLabel, label, painter, widget)
        if option.state & QStyle.State_HasFocus and option.text:
            focus = QStyleOptionFocusRect()
            focus.palette, focus.state = option.palette, option.state
            metrics = QFontMetrics(widget.font() if widget else painter.font())
            ink = metrics.boundingRect(label.rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextShowMnemonic, option.text)
            focus.rect = ink.adjusted(*RADIO_FOCUS_INSETS)
            self.drawPrimitive(QStyle.PE_FrameFocusRect, focus, painter, widget)

    def pixelMetric(self, metric, option=None, widget=None):
        if metric == QStyle.PM_TabBarBaseOverlap:
            return TAB_SEAM
        if metric in (QStyle.PM_TabBarTabOverlap, QStyle.PM_TabBarTabShiftHorizontal, QStyle.PM_TabBarTabShiftVertical):
            return 0
        if metric in (QStyle.PM_IndicatorWidth, QStyle.PM_IndicatorHeight):
            return 13
        if metric in (QStyle.PM_ExclusiveIndicatorWidth, QStyle.PM_ExclusiveIndicatorHeight):
            return 12
        if metric == QStyle.PM_SliderLength:
            return len(SLIDER_THUMB[0])
        if metric in (QStyle.PM_SliderThickness, QStyle.PM_SliderControlThickness):
            return len(SLIDER_THUMB)
        return super().pixelMetric(metric, option, widget)


_CLASSIC_STYLE = []


def classic_style():
    """One shared style; made again when the application has replaced and deleted the previous one."""
    import shiboken6

    if not _CLASSIC_STYLE or not shiboken6.isValid(_CLASSIC_STYLE[0]):
        _CLASSIC_STYLE[:] = [ClassicStyle("Windows")]
    return _CLASSIC_STYLE[0]


class PlainDisabledTextStyle(ClassicStyle):
    """Fields (combo boxes, edits, spin boxes) show disabled text plain grey;
    the originals engrave only captions and labels."""

    def styleHint(self, hint, option=None, widget=None, return_data=None):
        if hint == QStyle.SH_EtchDisabledText:
            return 0
        if hint == QStyle.SH_ComboBox_PopupFrameStyle:
            return int(QFrame.Box | QFrame.Plain)
        return super().styleHint(hint, option, widget, return_data)


_FIELD_STYLE = []


def field_style():
    if not _FIELD_STYLE:
        _FIELD_STYLE.append(PlainDisabledTextStyle("Windows"))
    return _FIELD_STYLE[0]


def read_only_field(edit):
    """A field that only shows text (a wizard's result): read only, on the window colour instead of white,
    its selection still navy with white letters (tests/test_qt_controls_reference.py)."""
    edit.setReadOnly(True)
    palette = edit.palette()
    palette.setColor(QPalette.Base, palette.color(QPalette.Window))
    edit.setPalette(palette)
    return edit


def plain_disabled_text(widget):
    """Gives a field the originals' disabled look: grey text, no engraving, on the window colour."""
    widget.setStyle(field_style())
    return widget


LIST_ROW_HEIGHT = 13  # a list's rows (tests/references/listbox-selected.png)
DROP_DOWN_ROWS = 8  # rows an open drop-down shows before it scrolls (tests/references/combo-open.png)


class ListRowDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        hint.setHeight(LIST_ROW_HEIGHT)
        return hint


def classic_combo(combo):
    """A drop-down as the originals had it: plain grey when disabled, and a list with a 1px black border,
    13px rows and eight rows before it scrolls."""
    plain_disabled_text(combo)
    combo.setMaxVisibleItems(DROP_DOWN_ROWS)
    combo.view().setItemDelegate(ListRowDelegate(combo.view()))
    return combo


def sunken_panel():
    panel = QFrame()
    panel.setFrameStyle(QFrame.Panel | QFrame.Sunken)
    panel.setLineWidth(2)
    return panel


def etched_line():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line


# The window decoration Setup installs: its close button is the dialogs' too.
DECORATION = os.path.expanduser("~/.local/share/aurorae/themes/Chicago95")
DIALOG_FRAME, DIALOG_TITLE = 3, 18
CLOSE_FACE = (16, 14)


class ClassicDialog(QDialog):
    """A dialog that draws its own frame and title bar, as the originals' dialogs look and the window
    decoration can't: a 3px raised frame (light and dark, white and shadow, face), an 18px title with
    no icon, the caption 2px into it, the title's gradient ending 2px before the close button and
    holding its end colour behind it, and the close button 2px in from the title's corner. The
    contents go in body; dragging the title moves the dialog (tests/test_shutdown_reference.py)."""

    def __init__(self, title, style, body_size, body_inset=DIALOG_FRAME, help_button=False):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.style = style
        self.help_button = help_button
        self.held = False  # the close button, pressed and the mouse still on it
        width, height = body_size
        self.setFixedSize(width + 2 * body_inset, height + DIALOG_FRAME * 2 + DIALOG_TITLE)
        self.body = QWidget(self)
        self.body.setGeometry(body_inset, DIALOG_FRAME + DIALOG_TITLE, width, height)

    def title_rect(self):
        return QRect(DIALOG_FRAME, DIALOG_FRAME, self.width() - 2 * DIALOG_FRAME, DIALOG_TITLE)

    def close_rect(self):
        """The close button's face: 16x14, 2px below and left of the title's top-right corner."""
        title = self.title_rect()
        return QRect(title.right() + 1 - 2 - CLOSE_FACE[0], title.top() + 2, *CLOSE_FACE)

    def help_rect(self):
        """The help button's face, 2px left of the close button's."""
        return self.close_rect().translated(-18, 0)

    def paintEvent(self, _event):
        scheme = read_scheme()
        face, bevel = scheme["face"], bevel_colors(scheme["face"], bevel_for_style(self.style))
        painter = QPainter(self)
        painter.fillRect(self.rect(), face)
        rings = [(bevel["light"], bevel["dark"]), (QColor("#ffffff"), bevel["shadow"]), (face, face)]
        w, h = self.width(), self.height()
        for depth, (top_left, bottom_right) in enumerate(rings):
            painter.fillRect(depth, depth, w - 2 * depth - 1, 1, top_left)
            painter.fillRect(depth, depth, 1, h - 2 * depth - 1, top_left)
            painter.fillRect(depth, h - 1 - depth, w - 2 * depth, 1, bottom_right)
            painter.fillRect(w - 1 - depth, depth, 1, h - 2 * depth, bottom_right)
        title, close = self.title_rect(), self.close_rect()
        gradient = QLinearGradient(title.left(), 0, close.left() - 2, 0)
        state = (
            "active" if self.isActiveWindow() else "inactive"
        )  # only the active window's title is in the active colours
        gradient.setColorAt(0, scheme[f"title_{state}"])
        gradient.setColorAt(1, scheme[f"title_{state}_blend"])
        painter.fillRect(title, gradient)
        painter.setFont(ui_font(bold=True))
        painter.setPen(scheme[f"title_{state}_text"])
        painter.drawText(title.left() + 2, title.top() + 13, self.windowTitle())
        from PySide6.QtSvg import QSvgRenderer

        # Each element covers its button's cell, the face a row down: the close cell is 18 wide with the
        # face at its right, the help cell 16 wide.
        buttons = [("close.svg", close, 2, "pressed" if self.held else state)] + (
            [("help.svg", self.help_rect(), 0, state)] if self.help_button else []
        )
        for file, face, lead, button_state in buttons:
            button = QSvgRenderer(os.path.join(DECORATION, file))
            element = {"active": "active-center", "inactive": "inactive-center", "pressed": "pressed-center"}[
                button_state
            ]
            if button.isValid():
                button.render(
                    painter,
                    element if button.elementExists(element) else "active-center",
                    QRectF(face.left() - lead, face.top() - 1, 16 + lead, 16),
                )
        painter.end()

    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange:
            self.update()
        super().changeEvent(event)

    def mousePressEvent(self, event):
        """The close button sinks while held and closes on release over it, as the decoration's do."""
        if self.close_rect().contains(event.position().toPoint()):
            self.held = True
            self.update()
        elif self.title_rect().contains(event.position().toPoint()) and self.windowHandle():
            self.windowHandle().startSystemMove()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.held != self.close_rect().contains(event.position().toPoint()):
            self.held = not self.held
            self.update()

    def mouseReleaseEvent(self, event):
        if self.held:
            self.held = False
            self.update()
            if self.close_rect().contains(event.position().toPoint()):
                self.reject()
