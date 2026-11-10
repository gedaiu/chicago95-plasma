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


def detect_scale():
    try:
        child_env = {key: value for key, value in os.environ.items() if key != "QT_QPA_PLATFORM"}
        output = subprocess.run(["kscreen-doctor", "-o"], capture_output=True, text=True, timeout=3, env=child_env).stdout
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

from PySide6.QtCore import QRect, QRectF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QRadialGradient  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QProxyStyle, QPushButton, QStyle, QStyledItemDelegate, QWidget  # noqa: E402

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
    return {name: QColor(*(int(part) for part in settings.get(group, key, fallback=default).split(",")[:3]))
            for name, (group, key, default) in SCHEME_DEFAULTS.items()}


CHICAGO95RC = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "chicago95rc")


def look_settings(path=None):
    """The look chosen in Setup, from ~/.config/chicago95rc.

    [StartMenu] style is 1995, 1998 or 2000. [Branding] describes the "operating system" the screens
    show: osCompany (the small word above the name), osName ("Windows 2000", "Fedora 44"; its number
    is drawn thin), osEdition, tagline (the login banner's line under the edition), osLogo and
    companyLogo (image paths). Each falls back to the Start menu's
    banner text and logo, so a look without branding still has a name and a logo."""
    settings = configparser.ConfigParser(interpolation=None, strict=False)
    settings.read(path or CHICAGO95RC)
    start_menu = lambda key, default: settings.get("StartMenu", key, fallback=default)
    branding = lambda key, default: settings.get("Branding", key, fallback=default)
    logos = sorted(glob.glob(os.path.expanduser("~/.local/share/chicago95/start-logo.*")))
    banner_text = start_menu("bannerText", "Chicago95")
    return {
        "style": start_menu("style", "1995"),
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
    values = {"os": short_os_name(look["osName"]), "osname": look["osName"], "company": look["osCompany"],
              "edition": look["edition"], "user": getpass.getuser(), "computer": socket.gethostname()}
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
    """(light, shadow) for a face colour: halfway to white and two thirds of the face, as #DFDFDF and #808080 are for #C0C0C0."""
    light = QColor((face.red() + 255) // 2, (face.green() + 255) // 2, (face.blue() + 255) // 2)
    shadow = QColor(face.red() * 2 // 3, face.green() * 2 // 3, face.blue() * 2 // 3)
    return light, shadow


def bevel_colors(face, style):
    """The 3D lines around a face, as {light, shadow, dark}: the light line inside the white one, the
    shadow line inside the dark one. 1995 and 1998 derive light and shadow from the face (#DFDFDF and
    #808080 for #C0C0C0) with a black dark line; 2000 uses the face itself as light, #808080 and #404040."""
    if style == "2000":
        return {"light": QColor(face), "shadow": QColor("#808080"), "dark": QColor("#404040")}
    light, shadow = bevel_shades(face)
    return {"light": light, "shadow": shadow, "dark": QColor("#000000")}


SCHEME = read_scheme()
FACE, NAVY = SCHEME["face"], SCHEME["selection"]
LIGHT, SHADOW = bevel_shades(FACE)
TEAL = QColor("#008080")
UI_FONT_FAMILY = "MS W98 UI"
ICON_SEARCH_PATHS = [
    os.path.expanduser("~/.local/share/icons"), os.path.expanduser("~/.icons"), "/usr/share/icons", "/usr/share/pixmaps",
]


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
    bevel = bevel_colors(face, look_settings()["style"])
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
# edges) whose top-left fades into the paper, a darker frame behind it (2px lower, 2px further right), a pale blue glow to its right
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
    painter.fillRect(QRectF(57, 49, 53, 8), edge_gradient(
        (57, 0), (110, 0), ((0, "#add69c"), (0.3, "#d2e4c3"), (1, "paper")), paper))
    painter.fillRect(QRectF(18, 57, 92, 4), edge_gradient(
        (18, 0), (110, 0), ((0, "paper"), (0.04, "#8cb96f"), (0.41, "#8cb96f"), (0.48, "#add69c"), (0.61, "#d2e4c1"),
                            (0.74, "#e2efda"), (1, "paper")), paper))
    painter.fillRect(QRectF(4, 2, 53, 55), QColor(BANNER_BACK_ORANGE))
    painter.fillRect(QRectF(0, 0, 55, 55), QColor(paper))
    painter.fillRect(QRectF(0, 0, 55, 4), edge_gradient((0, 0), (55, 0), ((0.6, "paper"), (0.72, BANNER_ORANGE)), paper))
    painter.fillRect(QRectF(0, 0, 4, 55), edge_gradient((0, 0), (0, 55), ((0.67, "paper"), (0.82, BANNER_ORANGE)), paper))
    painter.fillRect(QRectF(51, 0, 4, 55), edge_gradient(
        (0, 0), (0, 55), ((0.07, BANNER_ORANGE), (0.24, "paper"), (0.36, "paper"), (0.58, BANNER_ORANGE)), paper))
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


import functools  # noqa: E402

screen_scale = functools.lru_cache(maxsize=None)(screen_scale)   # kscreen-doctor is asked once per process


def ui_font(pixel_size=11, bold=False):
    """The UI font at the originals' size: MS Sans Serif 8 points, 11px. The pixel font is drawn on an
    11px grid; at any other size its letters land on fractional pixels and space unevenly. On a whole
    scale (1x, 2x) the grid lands on screen pixels and it is drawn unsmoothed, with hard edges; on 1.5x
    it is left to fontconfig, which smooths it (config/fontconfig/60-chicago95-pixel-font.conf)."""
    family = UI_FONT_FAMILY if UI_FONT_FAMILY in QFontDatabase.families() else "Noto Sans"
    font = QFont(family)
    font.setPixelSize(pixel_size)
    font.setBold(bold)
    if family == UI_FONT_FAMILY:   # said either way: a font that leaves it open inherits the application font's choice
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


def dialog_button(caption, enabled=True):
    button = QPushButton(caption)
    button.setFixedSize(*DIALOG_BUTTON_SIZE)
    button.setEnabled(enabled)
    return button


class ClassicStyle(QProxyStyle):
    """Qt's Windows style with the originals' pressed button: a black frame on every side and a shadow frame
    inside it, instead of Qt's dark top-left and light bottom-right (tests/test_control_panel_components_reference.py)."""

    PRESSED_PANELS = (QStyle.PE_PanelButtonCommand, QStyle.PE_PanelButtonBevel)

    def drawPrimitive(self, element, option, painter, widget=None):
        if element in self.PRESSED_PANELS and option.state & QStyle.State_Sunken:
            rect = option.rect
            painter.fillRect(rect, option.palette.button())
            painter.setPen(option.palette.shadow().color())
            painter.drawRect(rect.adjusted(0, 0, -1, -1))
            painter.setPen(option.palette.dark().color())
            painter.drawRect(rect.adjusted(1, 1, -2, -2))
            return
        super().drawPrimitive(element, option, painter, widget)


_CLASSIC_STYLE = []


def classic_style():
    if not _CLASSIC_STYLE:
        _CLASSIC_STYLE.append(ClassicStyle("Windows"))
    return _CLASSIC_STYLE[0]


class PlainDisabledTextStyle(ClassicStyle):
    """Fields (combo boxes, edits, spin boxes) show disabled text plain grey; the originals engrave only captions and labels."""

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


def plain_disabled_text(widget):
    """Gives a field the originals' disabled look: grey text, no engraving, on the window colour."""
    widget.setStyle(field_style())
    return widget


LIST_ROW_HEIGHT = 13          # a list's rows (tests/references/listbox-selected.png)
DROP_DOWN_ROWS = 8            # rows an open drop-down shows before it scrolls (tests/references/combo-open.png)


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
        face, bevel = scheme["face"], bevel_colors(scheme["face"], self.style)
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
        gradient.setColorAt(0, scheme["title_active"])
        gradient.setColorAt(1, scheme["title_active_blend"])
        painter.fillRect(title, gradient)
        painter.setFont(ui_font(bold=True))
        painter.setPen(scheme["title_active_text"])
        painter.drawText(title.left() + 2, title.top() + 13, self.windowTitle())
        from PySide6.QtSvg import QSvgRenderer
        # Each element covers its button's cell, the face a row down: the close cell is 18 wide with the
        # face at its right, the help cell 16 wide.
        buttons = [("close.svg", close, 2)] + ([("help.svg", self.help_rect(), 0)] if self.help_button else [])
        for file, face, lead in buttons:
            button = QSvgRenderer(os.path.join(DECORATION, file))
            if button.isValid():
                button.render(painter, "active-center", QRectF(face.left() - lead, face.top() - 1, 16 + lead, 16))
        painter.end()

    def mousePressEvent(self, event):
        if self.close_rect().contains(event.position().toPoint()):
            self.reject()
        elif self.title_rect().contains(event.position().toPoint()) and self.windowHandle():
            self.windowHandle().startSystemMove()
