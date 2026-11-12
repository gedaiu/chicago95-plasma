"""Windows XP Luna "Turn off computer" and "Log Off Windows" dialogs, drawn with QPainter at 1x.

Every box was measured with PIL on tests/references/xpshutdowndialog.png and xplogoff.png (both 314x200,
x then y of the first pixel):

  outer border      1px #000000 on x=0 and 313, y=0 and 199
  top band          y=1..43, #003399; title text x=13..162 y=15..32 (white 16px Trebuchet MS, baseline 28)
  flag              x=270..307 y=7..38 (luna/images/windows-xp-flag-dialog.png, 38x32)
  highlight         y=44..45, horizontal gradient (HIGHLIGHT_STOPS)
  middle band       y=46..155, horizontal gradient (MIDDLE_STOPS), flat down the column
  separator         y=156, #0F40A4
  bottom band       y=157..198, #003399
  icon buttons      33x33 at y=81: Stand By x=55, Turn Off x=141, Restart x=226 (centres 71, 157, 242);
                    Switch User x=84, Log Off x=199 (centres 100, 215); 1px white border, 1px rim, vertical gradient
                    (yellow #FEC363 #FEB43D #FDA926, edge #B97A08; red #EA8268 #E45939 #DB3909, edge #9D2607;
                    green #67B467 #3FA03F #0E8A0E, edge #0E620E; switch green #60C960 #2ABC2A #0FB30F;
                    log off orange #E2AE61 #DA9926 #D38902, edge #975F0F), white glyph
  labels            white bold Tahoma 11px, cap top y=122 (baseline 130), centred under the icon, mnemonic
                    underline y=131
  Cancel            halo x=243..302 y=168..187 (60x20), border #003C74 x=244..301 y=169..186; the halo is blended with
                    the blue: left and top #113C94, right #375FAF, bottom #9DB1D8
  hover             not in the references: a #FFFFFF 25% rounded halo around the button

Fitted gradients. The screenshots are JPEG-like quantised and the same in both, so each profile was averaged over
text-free rows, smoothed with a 3-sample moving average, and reduced to the fewest linear stops that stay within 12
per channel of that average (positions are pixel columns, colours "#RRGGBB"):

  HIGHLIGHT_STOPS   xpshutdowndialog.png and xplogoff.png, rows 44..45 averaged, columns 1..312 (max deviation 6.7)
  MIDDLE_STOPS      the same images, rows 50..75 averaged (above the buttons and the labels), columns 1..312
                    (max deviation 4.8)
  ICON_BODY_STOPS   each button's body, top to bottom (positions are fractions of the 31px body height): the same
                    images, the rows inside each 33x33 plate averaged over columns 3..5 and 27..29 (clear of the
                    glyph), 4 stops; the lighter left side is the white gloss radial gradient (GLOSS_*)
"""

from pathlib import Path

from chicago95luna import LunaStyle, luna_font, luna_palette
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QAbstractButton, QApplication, QDialog, QPushButton

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
ICON_SIZE = 33
ICON_TOP = 81
BUTTON_AREA = QRect(0, 78, 86, 58)
LABEL_BASELINE = 130
UNDERLINE_ROW = 131
CANCEL_RECT = QRect(243, 168, 60, 20)
CANCEL_HALO = {"left": "#113C94", "top": "#113C94", "right": "#375FAF", "bottom": "#9DB1D8"}
HOVER_HALO = QColor(255, 255, 255, 64)
HOVER_RADIUS = 5
ICON_RADIUS = 4
WHITE = QColor("#FFFFFF")

ICON_BODY_STOPS = {
    "yellow": [(0, "#F8B341"), (0.13, "#F9C063"), (0.87, "#F7B416"), (1, "#C47E0C")],
    "red": [(0, "#E06241"), (0.1, "#E97C63"), (0.87, "#DA4419"), (1, "#AE2E0D")],
    "green": [(0, "#3D9B3D"), (0.13, "#62B162"), (0.73, "#2B9C2B"), (1, "#0E6C0E")],
    "switch": [(0, "#40BA40"), (0.1, "#66C466"), (0.83, "#23BB23"), (1, "#0D8C0D")],
    "orange": [(0, "#D89A41"), (0.27, "#E0AF66"), (0.77, "#DA9B1F"), (1, "#9C620E")],
}
GLOSS_CENTRE = (6, 5)
GLOSS_RADIUS = 15
GLOSS_COLOURS = [(0, "#59FFFFFF"), (1, "#00FFFFFF")]


class ButtonSpec:
    def __init__(self, command, label, mnemonic, colour, glyph, centre, underlined=True):
        self.command = command
        self.label = label
        self.mnemonic = mnemonic
        self.colour = colour
        self.glyph = glyph
        self.centre = centre
        self.underlined = underlined


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


def flag_picture_path(ratio):
    suffix = "@2x" if ratio >= 2 else ""
    name = f"windows-xp-flag-dialog{suffix}.png"
    module_folder = Path(__file__).resolve().parent
    return next(
        path for path in (module_folder / "images" / name, module_folder.parents[1] / "images" / name) if path.is_file()
    )


def paint_flag(painter):
    ratio = 2 if painter.device().devicePixelRatio() >= 2 else 1
    picture = QPixmap(str(flag_picture_path(ratio)))
    picture.setDevicePixelRatio(ratio)
    painter.drawPixmap(QPoint(*FLAG_ORIGIN), picture)


def icon_body_gradient(colour_name):
    gradient = QLinearGradient(0, 0, 0, ICON_SIZE - 2)
    for position, colour in ICON_BODY_STOPS[colour_name]:
        gradient.setColorAt(position, QColor(colour))
    return gradient


def icon_gloss_gradient():
    gradient = QRadialGradient(QPointF(*GLOSS_CENTRE), GLOSS_RADIUS)
    for position, colour in GLOSS_COLOURS:
        gradient.setColorAt(position, QColor(colour))
    return gradient


def paint_icon_plate(painter, left, top, colour_name):
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.translate(left, top)
    painter.setBrush(WHITE)
    painter.drawRoundedRect(QRectF(0, 0, ICON_SIZE, ICON_SIZE), ICON_RADIUS, ICON_RADIUS)
    painter.translate(1, 1)
    body = QRectF(0, 0, ICON_SIZE - 2, ICON_SIZE - 2)
    painter.setBrush(icon_body_gradient(colour_name))
    painter.drawRoundedRect(body, ICON_RADIUS - 1, ICON_RADIUS - 1)
    painter.setBrush(icon_gloss_gradient())
    painter.drawRoundedRect(body, ICON_RADIUS - 1, ICON_RADIUS - 1)
    painter.restore()


def glyph_pen(width=2.6):
    pen = QPen(WHITE, width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def glyph_stand_by(painter, cx, cy):
    painter.drawArc(QRectF(cx - 8, cy - 7, 16, 16), 120 * 16, 300 * 16)
    painter.drawLine(QPointF(cx, cy - 10), QPointF(cx, cy))


def glyph_turn_off(painter, cx, cy):
    painter.drawEllipse(QPointF(cx, cy), 9, 9)
    painter.drawLine(QPointF(cx, cy - 6), QPointF(cx, cy + 4))


def glyph_restart(painter, cx, cy):
    for step in range(8):
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(step * 45)
        painter.drawLine(QPointF(0, -10), QPointF(0, -5.5))
        painter.restore()


def glyph_arrow(painter, tail, head, wing):
    painter.drawLine(tail, head)
    painter.drawLine(head, QPointF(head.x() - wing, head.y() - 4))
    painter.drawLine(head, QPointF(head.x() - wing, head.y() + 4))


def glyph_switch_user(painter, cx, cy):
    glyph_arrow(painter, QPointF(cx + 9, cy - 6), QPointF(cx - 9, cy - 6), -6)
    glyph_arrow(painter, QPointF(cx - 9, cy + 7), QPointF(cx + 9, cy + 7), 6)


def glyph_log_off(painter, cx, cy):
    painter.drawEllipse(QPointF(cx + 4, cy - 4), 4.5, 4.5)
    painter.drawLine(QPointF(cx + 1, cy - 1), QPointF(cx - 9, cy + 9))
    painter.drawLine(QPointF(cx - 6, cy + 6), QPointF(cx - 3, cy + 9))
    painter.drawLine(QPointF(cx - 9, cy + 9), QPointF(cx - 6, cy + 12))


GLYPHS = {
    "stand_by": glyph_stand_by,
    "turn_off": glyph_turn_off,
    "restart": glyph_restart,
    "switch_user": glyph_switch_user,
    "log_off": glyph_log_off,
}


def paint_icon(painter, left, top, spec):
    paint_icon_plate(painter, left, top, spec.colour)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(glyph_pen())
    painter.setBrush(Qt.NoBrush)
    GLYPHS[spec.glyph](painter, left + ICON_SIZE / 2, top + ICON_SIZE / 2 - 1)
    painter.restore()


def label_font():
    font = luna_font()
    font.setBold(True)
    return font


def paint_label(painter, spec):
    font = label_font()
    metrics = QFontMetrics(font)
    left = (BUTTON_AREA.width() - metrics.horizontalAdvance(spec.label)) // 2
    painter.setFont(font)
    painter.setPen(WHITE)
    baseline = LABEL_BASELINE - BUTTON_AREA.top()
    painter.drawText(left, baseline, spec.label)
    if not spec.underlined:
        return
    index = spec.label.upper().index(spec.mnemonic)
    start = left + metrics.horizontalAdvance(spec.label[:index])
    painter.fillRect(start, UNDERLINE_ROW - BUTTON_AREA.top(), metrics.horizontalAdvance(spec.mnemonic), 1, WHITE)


class IconButton(QAbstractButton):
    def __init__(self, spec, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.setAttribute(Qt.WA_Hover)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setGeometry(BUTTON_AREA.translated(spec.centre - BUTTON_AREA.width() // 2, 0))
        self.setText(spec.label)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.click()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.underMouse() or self.hasFocus():
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(HOVER_HALO)
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(2, 0, -2, 0), HOVER_RADIUS, HOVER_RADIUS)
        paint_icon(painter, (self.width() - ICON_SIZE + 1) // 2, ICON_TOP - BUTTON_AREA.top(), self.spec)
        paint_label(painter, self.spec)


class CancelButton(QPushButton):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        right, bottom = self.width() - 1, self.height() - 1
        painter.fillRect(1, 0, self.width() - 2, 1, QColor(CANCEL_HALO["top"]))
        painter.fillRect(1, bottom, self.width() - 2, 1, QColor(CANCEL_HALO["bottom"]))
        painter.fillRect(0, 1, 1, self.height() - 2, QColor(CANCEL_HALO["left"]))
        painter.fillRect(right, 1, 1, self.height() - 2, QColor(CANCEL_HALO["right"]))


class LunaDialog(QDialog):
    TITLE = ""
    SPECS = []

    def __init__(self, commands, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.commands = commands
        self.luna_style = LunaStyle()
        self.setWindowTitle(self.TITLE)
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
        button = CancelButton("Cancel", self)
        button.setStyle(self.luna_style)
        button.setAutoDefault(False)
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
        self.run(shortcut)

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_bands(painter)
        paint_title(painter, self.TITLE)
        paint_flag(painter)


class TurnOffDialog(LunaDialog):
    TITLE = "Turn off computer"
    SPECS = TURN_OFF_SPECS

    def __init__(self, commands, parent=None):
        resolved = dict(commands)
        resolved["stand_by"] = commands.get("stand_by") or commands["hibernate"]
        super().__init__(resolved, parent)


class LogOffDialog(LunaDialog):
    TITLE = "Log Off Windows"
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
