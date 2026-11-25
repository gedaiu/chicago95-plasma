"""Windows XP Luna "Turn off computer" and "Log Off Windows" dialogs.

Every box was measured with PIL on tests/references/xpshutdowndialog.png and xplogoff.png (both 314x200,
x then y of the first pixel):

  outer border      1px #000000 on x=0 and 313, y=0 and 199
  top band          y=1..43, #003399; title text x=13..162 y=15..32 (white 16px Trebuchet MS, baseline 28)
  flag              x=270..307 y=7..38 (luna/images/windows-xp-flag.svg, 38x32)
  highlight         y=44..45, horizontal gradient (HIGHLIGHT_STOPS)
  middle band       y=46..155, elliptical glow over a blue gradient
  separator         y=156, #0F40A4
  bottom band       y=157..198, #003399
  icon buttons      32x32 antialiased vector artwork with continuous gradients and distinct states
  labels            white bold Tahoma 11px, baseline 130, centred under each icon
  Cancel            60x20 at (243,168), continuous gradient and rounded border

The Log Off fallback's gradients use the older captures. Each profile was averaged over
text-free rows, smoothed with a 3-sample moving average, and reduced to the fewest linear stops that stay within 12
per channel of that average (positions are pixel columns, colours "#RRGGBB"):

  HIGHLIGHT_STOPS   xpshutdowndialog.png and xplogoff.png, rows 44..45 averaged, columns 1..312 (max deviation 6.7)
  MIDDLE_STOPS      the same images, rows 50..75 averaged (above the buttons and the labels), columns 1..312
                    (max deviation 4.8)

The power chooser uses the same middle-panel SVG at both DPIs. Its frame and dividers
snap to display pixels, measured from the 314×200 and 418×246 SP3 guest captures.
"""

from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

from chicago95luna import LunaStyle, luna_font, luna_palette
from PySide6.QtCore import QPointF, QRect, QRectF, QSizeF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
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
LABEL_BASELINE = 130
CANCEL_RECT = QRect(243, 168, 60, 20)
LARGE_POWER_SIZE = (334, 197)
LARGE_POWER_ICON_RECTS = (QRect(58, 79, 35, 32), QRect(149, 79, 35, 32), QRect(240, 79, 35, 32))
LARGE_POWER_CANCEL = QRect(257, 165, 66, 21)
LARGE_POWER_FLAG = QRectF(292, 9, 31, 27)
WHITE = QColor("#FFFFFF")
POWER_DIVIDER_STOPS = (
    (0, "#3c64b5"), (.02, "#3c64b5"), (.25, "#b9cdee"), (.38, "#dae7fb"),
    (.49, "#dae7fb"), (.68, "#cbdcf5"), (.77, "#aec4e7"), (.95, "#5276bf"),
    (1, "#355bb5"),
)
POWER_BUTTON_COLOURS = {
    "stand_by": (
        ("#d68e12", "#de9e28", "#e7b218", "#965a07"),
        ("#ff9f12", "#ffa921", "#ffd918", "#ac6906"),
        ("#cb7800", "#ce7900", "#dc9500", "#5a2508"),
        "#e7b26b",
    ),
    "turn_off": (
        ("#e74a19", "#e75128", "#e74612", "#9a2503"),
        ("#ff523d", "#ff6751", "#ff8765", "#c43c28"),
        ("#bb3b17", "#c13e1a", "#ce4921", "#5a2408"),
        "#de9a84",
    ),
    "restart": (
        ("#198d19", "#229921", "#08b308", "#046104"),
        ("#17aa17", "#2abf2a", "#17da17", "#087408"),
        ("#007c00", "#007f00", "#009e00", "#004500"),
        "#7bbe7b",
    ),
}


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


def paint_power_bands(painter, size, large, panel):
    scale = painter.deviceTransform().m11()
    width, height = (int(length * scale + 0.5) for length in size.toTuple())
    native_scale = 1.25 if large else 1
    unit = scale / native_scale
    border = max(1, round(unit))
    divider, separator = (round(row * unit) for row in ((54, 192) if large else (44, 156)))
    highlight_height = max(1, round(2 * unit))
    # Paint the outer stroke on the framebuffer grid. A half-device-pixel
    # widget width otherwise leaves a grey seam on the right at 120 DPI.
    painter.save()
    painter.scale(1 / scale, 1 / scale)
    painter.fillRect(QRect(0, 0, width, height), QColor(BORDER))
    inner_width = width - 2 * border
    painter.fillRect(QRect(border, border, inner_width, height - 2 * border), QColor(BAND))
    highlight = QLinearGradient(border, 0, width - border, 0)
    for offset, color in POWER_DIVIDER_STOPS:
        highlight.setColorAt(offset, QColor(color))
    painter.fillRect(QRect(border, divider, inner_width, highlight_height), highlight)
    panel_top = divider + highlight_height
    panel.render(painter, QRectF(border, panel_top, inner_width, separator - panel_top))
    painter.fillRect(QRect(border, separator, inner_width, border), QColor("#0f43a5"))
    painter.restore()


def title_font(pixel_size):
    font = QFont()
    font.setFamilies(TITLE_FAMILIES)
    font.setPixelSize(pixel_size)
    font.setStyleStrategy(QFont.PreferAntialias)
    return font


def paint_title(painter, title, large_power, power_chooser=False):
    font = title_font(18 if large_power else TITLE_PIXEL_SIZE)
    x, y = (12 if large_power else TITLE_ORIGIN[0]), TITLE_ORIGIN[1]
    if (
        power_chooser and not large_power
        and not QFontDatabase.hasFamily("Trebuchet MS") and QFontDatabase.hasFamily("Cantarell")
    ):
        # Cantarell's lowercase shapes match the guest at this size, with a slightly higher baseline.
        font.setFamilies(["Cantarell"])
        font.setPixelSize(19)
        x, y = x - 1, y - 1
    painter.setFont(font)
    painter.setPen(WHITE)
    painter.drawText(QPointF(x, y), title)


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


def paint_flag(painter, picture, slot):
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    # Preserve the picture's aspect ratio inside the original 38x32 slot, centred. Render
    # paths at the painter's actual device scale, including fractional scales.
    svg = isinstance(picture, QSvgRenderer)
    size = picture.viewBoxF().size() if svg else QSizeF(picture.size())
    scale = min(slot.width() / size.width(), slot.height() / size.height())
    width, height = size.width() * scale, size.height() * scale
    target = QRectF(0, 0, width, height)
    target.moveCenter(slot.center())
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


def paint_large_power_cancel(painter, option):
    enabled = bool(option.state & QStyle.State_Enabled)
    pressed = bool(option.state & QStyle.State_Sunken)
    hovered = enabled and not pressed and bool(option.state & QStyle.State_MouseOver)
    bounds = QRectF(option.rect)
    outline = bounds.adjusted(2.2, 1.3, -1.65, -2)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    rim = smooth_gradient("#173e91", "#bccce7", bounds.height())
    rim.setColorAt(.85, QColor("#315eaa"))
    painter.setBrush(rim)
    painter.drawRoundedRect(outline.adjusted(-.85, -.6, 1, .45), 3, 3)

    painter.setBrush(QColor("#003c74" if enabled else "#a7a69c"))
    painter.drawRoundedRect(outline, 2.8, 2.8)
    face_rect = outline.adjusted(.8, .8, -.8, -.8)
    face = QLinearGradient(0, face_rect.top(), 0, face_rect.bottom())
    stops = (
        ((0, "#d4ccc0"), (.21, "#e9e6e1"), (.79, "#e6e3dd"), (1, "#f6f2ed"))
        if pressed
        else ((0, "#ffffff"), (.13, "#ffffff"), (.25, "#f7f7f7"), (.58, "#f7f3ef"),
              (.82, "#f7f3ef"), (1, "#d3cec1"))
    )
    for position, colour in stops:
        face.setColorAt(position, QColor(colour))
    painter.setBrush(face)
    painter.drawRoundedRect(face_rect, 1.9, 1.9)
    painter.setBrush(Qt.NoBrush)
    if hovered:
        hover = QLinearGradient(0, outline.top(), 0, outline.bottom())
        hover.setColorAt(0, QColor("#fff3ce"))
        hover.setColorAt(.17, QColor("#ffdf9c"))
        hover.setColorAt(.85, QColor("#ffb631"))
        hover.setColorAt(1, QColor("#e79600"))
        painter.setPen(QPen(hover, 1.6))
        painter.drawRoundedRect(face_rect.adjusted(.6, 1, -.6, -.9), 1.3, 1.3)
    elif pressed or (option.state & QStyle.State_HasFocus and option.state & QStyle.State_KeyboardFocusChange):
        focus_rect = face_rect.adjusted(1.4, 1.4, -.6, -1.35)
        focus = QLinearGradient(0, focus_rect.top(), 0, focus_rect.bottom())
        focus.setColorAt(0, QColor("#313b10" if pressed else "#513629"))
        focus.setColorAt(.5, QColor("#313408" if pressed else "#493032"))
        focus.setColorAt(1, QColor("#050928" if pressed else "#654638"))
        pen = QPen(focus, 0)
        pen.setDashPattern((1, 1))
        pen.setDashOffset(1)
        pen.setCapStyle(Qt.FlatCap)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setPen(pen)
        painter.drawRect(focus_rect)
    painter.restore()


@lru_cache(maxsize=12)
def power_icon_renderer(command, pressed, hot, enabled):
    idle, hover, down, pressed_glyph = POWER_BUTTON_COLOURS[command]
    top, middle, lit, edge = down if pressed else hover if hot else idle
    if not enabled:
        top, middle, lit, edge = "#8ea8cf", "#809cc6", "#718fb8", "#617eaa"
    artwork = Path(__file__).with_name("images") / "xp-luna-power-button.svg"
    root = ElementTree.parse(artwork).getroot()
    elements = {node.get("id"): node for node in root.iter() if "id" in node.attrib}
    rim = "#d6dff7" if pressed else "#ffffff"
    gloss = edge if pressed else "#ffffff"
    gradients = {
        "rim": (rim, "#ffffff", "#ffffff", rim),
        "bevel": (edge, top, QColor(top).lighter(113).name())
        if pressed else (QColor(top).lighter(114).name(), middle, edge),
        "face": (edge, top, top) if pressed else (top, middle, top),
        "gleam": (lit, lit, lit),
        "gloss": (gloss, gloss),
    }
    for name, colours in gradients.items():
        for stop, colour in zip(elements[name], colours, strict=True):
            stop.set("stop-color", colour)
    if pressed:
        elements["gloss"][0].set("stop-opacity", "1")
    if not enabled:
        root.remove(elements["gleam-layer"])
        root.remove(elements["gloss-layer"])
    for name in POWER_BUTTON_COLOURS.keys() - {command}:
        root.remove(elements[name])
    glyph = elements[command]
    glyph.attrib.pop("display", None)
    glyph.set("stroke", "#c3cedd" if not enabled else pressed_glyph if pressed else "#ffffff")
    return QSvgRenderer(ElementTree.tostring(root))


def paint_icon(painter, spec, pressed=False, hot=False, enabled=True):
    """Render at the display resolution instead of enlarging a 32px bitmap."""
    if spec.command in POWER_BUTTON_COLOURS:
        power_icon_renderer(spec.command, pressed, hot, enabled).render(painter, QRectF(0, 0, ICON_SIZE, ICON_SIZE))
        return
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    other_colours = {
        "switch_user": ("#75CC70", "#159F0A"),
        "log_off": ("#E8BB75", "#CD880D"),
    }
    top, bottom = map(QColor, other_colours[spec.command])
    if not enabled:
        top, bottom = QColor("#8EA8CF"), QColor("#718FB8")
    elif pressed:
        top, bottom = top.darker(145), bottom.darker(145)
    elif hot:
        top, bottom = top.lighter(120), bottom.lighter(120)
    painter.setPen(QPen(QColor("#FFFFFF" if not pressed else "#C4C9D5"), 1))
    painter.setBrush(smooth_gradient(top, bottom, 31))
    painter.drawRoundedRect(QRectF(.5, .5, 31, 31), 3.5, 3.5)
    gloss = QRadialGradient(QPointF(7, 5), 24)
    gloss.setColorAt(0, QColor(255, 255, 255, 15 if pressed else 65))
    gloss.setColorAt(1, QColor(255, 255, 255, 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(gloss)
    painter.drawRoundedRect(QRectF(1.5, 1.5, 29, 29), 2.5, 2.5)
    glyph = QColor("#FFFFFF" if enabled and not pressed else "#C3CEDD")
    pen = QPen(glyph, 2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    if spec.command == "switch_user":
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


def power_font():
    font = luna_font()
    font.setFamilies(["Tahoma", "Liberation Sans", "Noto Sans"])
    return font


def label_font(power):
    font = power_font() if power else luna_font()
    font.setBold(True)
    return font


def paint_label(painter, spec, centre, baseline, enabled=True):
    font = label_font(spec.command in POWER_BUTTON_COLOURS)
    metrics = QFontMetrics(font)
    left = (2 * centre - metrics.horizontalAdvance(spec.label)) // 2
    painter.setFont(font)
    colour = WHITE if enabled else QColor(160, 160, 160)
    painter.setPen(colour)
    painter.drawText(left, baseline, spec.label)
    if not spec.underlined:
        return
    index = spec.label.upper().index(spec.mnemonic)
    start = left + metrics.horizontalAdvance(spec.label[:index])
    painter.fillRect(start, baseline + 1, metrics.horizontalAdvance(spec.mnemonic), 1, colour)


class IconButton(QAbstractButton):
    def __init__(self, spec, rect, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.setAttribute(Qt.WA_Hover)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setGeometry(rect)
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
        painter.scale(self.width() / ICON_SIZE, self.height() / ICON_SIZE)
        hot = self.hasFocus() or (self.underMouse() and self.spec.command != "stand_by")
        paint_icon(painter, self.spec, self.isDown(), hot, self.isEnabled())


class LunaDialog(QDialog):
    TITLE = ""
    SPECS = []
    IS_POWER_CHOOSER = False

    def __init__(self, commands, parent=None, logo="", name="Windows"):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.commands = commands
        self.title = self.TITLE.format(name=name)
        self.flag = logo_picture(logo)
        self.large_power = self.IS_POWER_CHOOSER and self.devicePixelRatioF() >= 1.125
        self.power_panel = None
        if self.IS_POWER_CHOOSER:
            artwork = Path(__file__).with_name("images") / "xp-luna-power-panel.svg"
            self.power_panel = QSvgRenderer(str(artwork))
        self.luna_style = LunaStyle()
        button_painter = paint_large_power_cancel if self.large_power else paint_cancel
        self.luna_style.primitive_painters[QStyle.PE_PanelButtonCommand] = button_painter
        self.luna_style.control_painters[QStyle.CE_PushButtonBevel] = button_painter
        self.setWindowTitle(self.title)
        self.setFixedSize(*(LARGE_POWER_SIZE if self.large_power else DIALOG_SIZE))
        self.setPalette(luna_palette())
        self.setFont(luna_font())
        icon_extent = ICON_SIZE + 1 if self.IS_POWER_CHOOSER else ICON_SIZE
        rects = LARGE_POWER_ICON_RECTS if self.large_power else (
            QRect(spec.centre - ICON_SIZE // 2, ICON_TOP, icon_extent, icon_extent) for spec in self.SPECS
        )
        self.buttons = {
            spec.command: self.add_icon_button(spec, rect) for spec, rect in zip(self.SPECS, rects, strict=True)
        }
        self.cancel_button = self.add_cancel_button()
        self.buttons[self.SPECS[0].command].setFocus()

    def add_icon_button(self, spec, rect):
        button = IconButton(spec, rect, self)
        button.clicked.connect(lambda: self.run(spec.command))
        return button

    def add_cancel_button(self):
        button = QPushButton("Cancel", self)
        button.setStyle(self.luna_style)
        if self.IS_POWER_CHOOSER:
            font = power_font()
            if self.large_power:
                font.setStyleStrategy(QFont.NoAntialias)
            button.setFont(font)
        button.setAutoDefault(self.IS_POWER_CHOOSER)
        button.setToolTip("Closes this dialog without changing your session.")
        button.setGeometry(LARGE_POWER_CANCEL if self.large_power else CANCEL_RECT)
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
        if self.power_panel is not None:
            paint_power_bands(painter, self.size(), self.large_power, self.power_panel)
        else:
            paint_bands(painter)
        paint_title(painter, self.title, self.large_power, self.IS_POWER_CHOOSER)
        slot = LARGE_POWER_FLAG if self.large_power else QRectF(*FLAG_ORIGIN, 38, 32)
        paint_flag(painter, self.flag, slot)
        for spec in self.SPECS:
            button = self.buttons[spec.command]
            centre = button.x() + button.width() // 2
            paint_label(painter, spec, centre, 128 if self.large_power else LABEL_BASELINE, button.isEnabled())


class TurnOffDialog(LunaDialog):
    TITLE = "Turn off computer"
    SPECS = TURN_OFF_SPECS
    IS_POWER_CHOOSER = True

    def __init__(self, commands, parent=None, **branding):
        resolved = dict(commands)
        resolved["stand_by"] = commands.get("stand_by") or commands["hibernate"]
        super().__init__(resolved, parent, **branding)


class LogOffDialog(LunaDialog):
    TITLE = "Log Off {name}"
    SPECS = LOG_OFF_SPECS


def grab_image(dialog):
    image = QImage(dialog.size(), QImage.Format_RGB32)
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
