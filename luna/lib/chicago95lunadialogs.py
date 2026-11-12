"""Windows XP Luna "Turn off computer" and "Log Off Windows" dialogs, drawn with QPainter at 1x.

Every box was measured with PIL on tests/references/xpshutdowndialog.png and xplogoff.png (both 314x200,
x then y of the first pixel):

  outer border      1px #000000 on x=0 and 313, y=0 and 199
  top band          y=1..43, #003399; title text x=13..162 y=15..32 (white 16px Trebuchet MS, baseline 28)
  flag              x=270..307 y=7..38 (luna/images/windows-xp-flag.svg, 38x32)
  highlight         y=44..45, horizontal gradient (HIGHLIGHT_STOPS)
  middle band       y=46..155, horizontal gradient (MIDDLE_STOPS), flat down the column
  separator         y=156, #0F40A4
  bottom band       y=157..198, #003399
  icon buttons      32x32 antialiased vector artwork with continuous gradients and distinct states
  labels            white bold Tahoma 11px, baseline 130, centred under each icon
  Cancel            60x20 at (243,168), continuous gradient and rounded border, no outer halo

Fitted gradients. The screenshots are JPEG-like quantised and the same in both, so each profile was averaged over
text-free rows, smoothed with a 3-sample moving average, and reduced to the fewest linear stops that stay within 12
per channel of that average (positions are pixel columns, colours "#RRGGBB"):

  HIGHLIGHT_STOPS   xpshutdowndialog.png and xplogoff.png, rows 44..45 averaged, columns 1..312 (max deviation 6.7)
  MIDDLE_STOPS      the same images, rows 50..75 averaged (above the buttons and the labels), columns 1..312
                    (max deviation 4.8)
"""

from pathlib import Path

from chicago95luna import LunaStyle, luna_font, luna_palette
from PySide6.QtCore import QPointF, QRect, QRectF, QSizeF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton, QApplication, QDialog, QPushButton, QStyle

DIALOG_SIZE = (314, 200)
BORDER = "#000000"
BAND = "#003399"
SEPARATOR = "#0F40A4"
TOP_BAND_ROWS = (1, 43)
HIGHLIGHT_ROWS = (44, 45)
MIDDLE_ROWS = (46, 155)
SEPARATOR_ROW = 156
BOTTOM_BAND_ROWS = (157, 198)
HIGHLIGHT_STOPS = [(1, "#3960B6"), (88, "#C4D5F0"), (123, "#D8E6FA"), (226, "#C4D5F0"), (312, "#3960B6")]
MIDDLE_STOPS = [(1, "#5A7DDE"), (185, "#99B7F6"), (312, "#698BE4")]
TITLE_FAMILIES = ["Trebuchet MS", "Fira Sans", "Noto Sans"]
TITLE_PIXEL_SIZE = 16
TITLE_ORIGIN = (13, 28)
FLAG_ORIGIN = (270, 7)
ICON_SIZE = 32
ICON_TOP = 81
BUTTON_AREA = QRect(0, 78, 86, 58)
LABEL_BASELINE = 130
UNDERLINE_ROW = 131
CANCEL_RECT = QRect(243, 168, 60, 20)
WHITE = QColor("#FFFFFF")


class ButtonSpec:
    def __init__(self, command, label, mnemonic, colour, glyph, centre, underlined=True):
        self.command = command
        self.label = label
        self.mnemonic = mnemonic
        self.colour = colour
        self.glyph = glyph
        self.centre = centre
        self.underlined = underlined


BUTTON_HELP = {
    "stand_by": "Keeps your session in memory while the computer uses less power. Resume to continue working.",
    "turn_off": "Closes your programs, logs off all users, and turns off the computer.",
    "restart": "Closes your programs, logs off all users, and restarts the computer.",
    "switch_user": "Lets another user log on while keeping your programs and session open.",
    "log_off": "Closes your programs and ends your session so another user can log on.",
}


TURN_OFF_SPECS = [
    ButtonSpec("stand_by", "Stand By", "S", "yellow", "stand_by", 71),
    ButtonSpec("turn_off", "Turn Off", "U", "red", "turn_off", 157),
    ButtonSpec("restart", "Restart", "R", "green", "restart", 242),
]
LOG_OFF_SPECS = [
    ButtonSpec("switch_user", "Switch User", "S", "switch", "switch_user", 100, underlined=False),
    ButtonSpec("log_off", "Log Off", "L", "orange", "log_off", 215, underlined=False),
]


def stops_gradient(stops, left, right):
    gradient = QLinearGradient(left + 0.5, 0, right + 0.5, 0)
    for x, colour in stops:
        gradient.setColorAt((x - left) / (right - left), QColor(colour))
    return gradient


def paint_bands(painter):
    width, height = DIALOG_SIZE
    painter.fillRect(0, 0, width, height, QColor(BORDER))
    painter.fillRect(1, TOP_BAND_ROWS[0], width - 2, TOP_BAND_ROWS[1] - TOP_BAND_ROWS[0] + 1, QColor(BAND))
    painter.fillRect(1, BOTTOM_BAND_ROWS[0], width - 2, BOTTOM_BAND_ROWS[1] - BOTTOM_BAND_ROWS[0] + 1, QColor(BAND))
    painter.fillRect(1, SEPARATOR_ROW, width - 2, 1, QColor(SEPARATOR))
    highlight = stops_gradient(HIGHLIGHT_STOPS, 1, width - 2)
    painter.fillRect(QRect(1, HIGHLIGHT_ROWS[0], width - 2, 2), highlight)
    middle = stops_gradient(MIDDLE_STOPS, 1, width - 2)
    painter.fillRect(QRect(1, MIDDLE_ROWS[0], width - 2, MIDDLE_ROWS[1] - MIDDLE_ROWS[0] + 1), middle)


def title_font():
    font = QFont()
    font.setFamilies(TITLE_FAMILIES)
    font.setPixelSize(TITLE_PIXEL_SIZE)
    font.setStyleStrategy(QFont.PreferAntialias)
    return font


def paint_title(painter, title):
    painter.setFont(title_font())
    painter.setPen(WHITE)
    painter.drawText(QPointF(*TITLE_ORIGIN), title)


def flag_picture_path():
    module_folder = Path(__file__).resolve().parent
    return next(
        folder / "windows-xp-flag.svg"
        for folder in (module_folder / "images", module_folder.parent / "images")
        if (folder / "windows-xp-flag.svg").is_file()
    )


# The flags Setup bundles: with one of them the dialog keeps XP's own flag.
BUNDLED_LOGOS = ("", "waving-flag.png", "logo-flag-16.png", "logo-flag.png", "logo-xp-16.png")


def logo_picture(logo=""):
    """The picture in the flag's slot: the user's own logo (a distribution's) when the branding names one, read
    as an SVG renderer or an image; else XP's flag."""
    path = Path(logo) if logo else None
    if path is None or path.name in BUNDLED_LOGOS or not path.is_file():
        path = flag_picture_path()
    return QSvgRenderer(str(path)) if path.suffix == ".svg" else QImage(str(path))


def paint_flag(painter, picture):
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    # Preserve the picture's aspect ratio inside the original 38x32 slot, centred. Render
    # paths at the painter's actual device scale, including fractional scales.
    svg = isinstance(picture, QSvgRenderer)
    size = picture.viewBoxF().size() if svg else QSizeF(picture.size())
    scale = min(38 / size.width(), 32 / size.height())
    width, height = size.width() * scale, size.height() * scale
    target = QRectF(FLAG_ORIGIN[0] + (38 - width) / 2, FLAG_ORIGIN[1] + (32 - height) / 2, width, height)
    if svg:
        picture.render(painter, target)
    else:
        painter.drawImage(target, picture)
    painter.restore()


def smooth_gradient(top, bottom, height):
    gradient = QLinearGradient(0, 0, 0, height)
    gradient.setColorAt(0, QColor(top))
    gradient.setColorAt(1, QColor(bottom))
    return gradient


def paint_cancel(painter, option):
    """A continuous face and a single border, with no outer highlight/shadow."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    enabled = bool(option.state & QStyle.State_Enabled)
    pressed = bool(option.state & QStyle.State_Sunken)
    hot = bool(option.state & QStyle.State_MouseOver)
    rect = QRectF(option.rect).adjusted(1.5, 1.5, -1.5, -1.5)
    top, bottom = ("#DDD9CF", "#F0EFE8") if pressed else ("#FFFFFF", "#ECE9DF")
    painter.setBrush(smooth_gradient(top, bottom, option.rect.height()))
    painter.setPen(QPen(QColor("#003C74" if enabled else "#A7A69C"), 1))
    painter.drawRoundedRect(rect, 2.5, 2.5)
    if enabled and hot and not pressed:
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#F3BB51"), 1.5))
        painter.drawRoundedRect(rect.adjusted(1.25, 1.25, -1.25, -1.25), 1.5, 1.5)
    painter.restore()


def paint_icon(painter, spec, pressed=False, hot=False, enabled=True):
    """Render at the display resolution instead of enlarging a 32px bitmap."""
    colours = {
        "stand_by": ("#FBC66A", "#E69B0C"),
        "turn_off": ("#ED876E", "#CF3712"),
        "restart": ("#70B970", "#138513"),
        "switch_user": ("#75CC70", "#159F0A"),
        "log_off": ("#E8BB75", "#CD880D"),
    }
    top, bottom = map(QColor, colours[spec.command])
    if not enabled:
        top, bottom = QColor("#8EA8CF"), QColor("#718FB8")
    elif pressed:
        top, bottom = top.darker(145), bottom.darker(145)
    elif hot:
        top, bottom = top.lighter(120), bottom.lighter(120)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor("#FFFFFF" if not pressed else "#C4C9D5"), 1))
    painter.setBrush(smooth_gradient(top, bottom, 31))
    painter.drawRoundedRect(QRectF(0.5, 0.5, 31, 31), 3.5, 3.5)
    gloss = QRadialGradient(QPointF(7, 5), 24)
    gloss.setColorAt(0, QColor(255, 255, 255, 65 if not pressed else 15))
    gloss.setColorAt(1, QColor(255, 255, 255, 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(gloss)
    painter.drawRoundedRect(QRectF(1.5, 1.5, 29, 29), 2.5, 2.5)
    pen = QPen(QColor("#FFFFFF" if enabled and not pressed else "#C3CEDD"), 2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    if spec.command in ("stand_by", "turn_off"):
        if spec.command == "stand_by":
            painter.drawArc(QRectF(8, 8, 16, 17), 125 * 16, 290 * 16)
            painter.drawLine(QPointF(16, 6), QPointF(16, 15))
        else:
            painter.drawEllipse(QRectF(7.5, 7, 17, 18))
            painter.drawLine(QPointF(16, 11), QPointF(16, 21))
    elif spec.command == "restart":
        for angle in range(0, 360, 45):
            painter.save()
            painter.translate(16, 16)
            painter.rotate(angle)
            painter.drawLine(QPointF(0, -11), QPointF(0, -5))
            painter.restore()
    elif spec.command == "switch_user":
        for points in (((24, 9), (8, 9), (13, 4)), ((8, 23), (24, 23), (19, 28))):
            path = QPainterPath(QPointF(*points[0]))
            path.lineTo(QPointF(*points[1]))
            path.lineTo(QPointF(*points[2]))
            painter.drawPath(path)
        painter.drawLine(QPointF(8, 9), QPointF(13, 14))
        painter.drawLine(QPointF(24, 23), QPointF(19, 18))
    else:
        painter.drawEllipse(QRectF(17, 5, 9, 9))
        path = QPainterPath(QPointF(19, 13))
        for point in ((8, 24), (5, 24), (5, 20), (8, 20), (8, 17), (11, 17), (17, 11)):
            path.lineTo(QPointF(*point))
        painter.drawPath(path)
    painter.restore()


def label_font():
    font = luna_font()
    font.setBold(True)
    return font


def paint_label(painter, spec, enabled=True):
    font = label_font()
    metrics = QFontMetrics(font)
    left = (BUTTON_AREA.width() - metrics.horizontalAdvance(spec.label)) // 2
    painter.setFont(font)
    colour = WHITE if enabled else QColor(160, 160, 160)
    painter.setPen(colour)
    baseline = LABEL_BASELINE - BUTTON_AREA.top()
    painter.drawText(left, baseline, spec.label)
    if not spec.underlined:
        return
    index = spec.label.upper().index(spec.mnemonic)
    start = left + metrics.horizontalAdvance(spec.label[:index])
    painter.fillRect(start, UNDERLINE_ROW - BUTTON_AREA.top(), metrics.horizontalAdvance(spec.mnemonic), 1, colour)


class IconButton(QAbstractButton):
    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.setAttribute(Qt.WA_Hover)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setGeometry(spec.centre - ICON_SIZE // 2, ICON_TOP, ICON_SIZE, ICON_SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.setText(spec.label)
        self.setToolTip(
            f'<qt><table width="240"><tr><td><b>{spec.label}</b><br>{BUTTON_HELP[spec.command]}</td></tr></table></qt>'
        )
        self.setAccessibleDescription(BUTTON_HELP[spec.command])

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.click()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_icon(painter, self.spec, self.isDown(), self.underMouse() or self.hasFocus(), self.isEnabled())


class LunaDialog(QDialog):
    TITLE = ""
    SPECS = []

    def __init__(self, commands, parent=None, logo="", name="Windows"):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.commands = commands
        self.title = self.TITLE.format(name=name)
        self.flag = logo_picture(logo)
        self.luna_style = LunaStyle()
        # Smooth dialog-specific faces, with no shadow beneath Cancel.
        button_painter = paint_cancel
        self.luna_style.primitive_painters[QStyle.PE_PanelButtonCommand] = button_painter
        self.luna_style.control_painters[QStyle.CE_PushButtonBevel] = button_painter
        self.setWindowTitle(self.title)
        self.setFixedSize(*DIALOG_SIZE)
        self.setPalette(luna_palette())
        self.setFont(luna_font())
        self.buttons = {spec.command: self.add_icon_button(spec) for spec in self.SPECS}
        self.cancel_button = self.add_cancel_button()
        self.buttons[self.SPECS[0].command].setFocus()

    def add_icon_button(self, spec):
        button = IconButton(spec, self)
        button.clicked.connect(lambda: self.run(spec.command))
        return button

    def add_cancel_button(self):
        button = QPushButton("Cancel", self)
        button.setStyle(self.luna_style)
        button.setAutoDefault(False)
        button.setToolTip("Closes this dialog without changing your session.")
        button.setGeometry(CANCEL_RECT)
        button.clicked.connect(self.reject)
        return button

    def run(self, command):
        self.commands[command]()
        self.accept()

    def reject(self):
        self.commands["cancel"]()
        super().reject()

    def keyPressEvent(self, event):
        shortcut = {spec.mnemonic: spec.command for spec in self.SPECS}.get(event.text().upper())
        if shortcut is None:
            super().keyPressEvent(event)
            return
        if self.buttons[shortcut].isEnabled():
            self.run(shortcut)

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_bands(painter)
        paint_title(painter, self.title)
        paint_flag(painter, self.flag)
        for spec in self.SPECS:
            painter.save()
            painter.translate(spec.centre - BUTTON_AREA.width() // 2, BUTTON_AREA.top())
            paint_label(painter, spec, self.buttons[spec.command].isEnabled())
            painter.restore()


class TurnOffDialog(LunaDialog):
    TITLE = "Turn off computer"
    SPECS = TURN_OFF_SPECS

    def __init__(self, commands, parent=None, **branding):
        resolved = dict(commands)
        resolved["stand_by"] = commands.get("stand_by") or commands["hibernate"]
        super().__init__(resolved, parent, **branding)


class LogOffDialog(LunaDialog):
    TITLE = "Log Off {name}"
    SPECS = LOG_OFF_SPECS


def grab_image(dialog):
    image = QImage(*DIALOG_SIZE, QImage.Format_RGB32)
    dialog.render(image)
    return image


def silent_commands(*names):
    return {name: (lambda: None) for name in (*names, "cancel")}


def drawn_turn_off_dialog():
    QApplication.instance() or QApplication([])
    return grab_image(TurnOffDialog(silent_commands("stand_by", "turn_off", "restart")))


def drawn_log_off_dialog():
    QApplication.instance() or QApplication([])
    return grab_image(LogOffDialog(silent_commands("log_off", "switch_user")))
