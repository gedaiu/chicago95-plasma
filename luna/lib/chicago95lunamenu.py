"""The Windows XP two-column Start menu, drawn with QPainter at 1x.

Measured from tests/references/xpdesktop.png, box (0,93)-(380,570), 380x477, coordinates below are
inside that box (xpstartmenu.png is a 282px downscale and is not used for pixels):

  header            rows 0..63, a vertical gradient (HEADER_STOPS)
  orange rule       rows 64..65, a horizontal gradient (RULE_STOPS)
  left column       white, x 2..189, rows 66..435 (370 rows)
  divider           x=190, #95BDEE, rows 66..435 (palette.py's x=198 and #B5BDCC are a text pixel, not the divider)
  right column      #D3E5FA, x 191..377, with a fade to #A6C2E6 at its right edge (RIGHT_FADE_STOPS)
  outer edges       x=0 and x=379 #1854C2; the left highlight and the right shade are gradients (LEFT_HIGHLIGHT_STOPS,
                    RIGHT_SHADE_STOPS); x=1 #91A4DA and x=378 #2B6DD1 beside the body
  footer            row 436 #1865CD, rows 437..476 a vertical gradient (FOOTER_STOPS) with side shading
                    (FOOTER_LEFT_SHADE_STOPS, FOOTER_RIGHT_SHADE_STOPS)
  corners           top corners are circular arcs of CORNER_RADIUS; bottom square
  avatar            frame 52x52 at (7,6), 2px #CCD6EB; picture 48x48 at (9,8)
  user name         bold, ink x 68..122, rows 24..36
  pinned rows       32px icon at x=10, tops 70 and 110 (pitch 40), icon 4px below the row top, text x=46,
                    title baseline 18px and subtitle baseline 31px below the row top
  separators        left rows 155 and 400, a horizontal fade white, #D3D3C8, white over x 15..185
  most used rows    32px icons, tops 159 + 40 * n (pitch 40), six slots, single-line baseline 22px below the top
  All Programs      row 402..435, text x=46, green arrow 16x24 at (129,407)
  right rows        24px icon at x=198, text x=226, pitch 32, tops 70, 102, 134, 166, 198 (bold #0A246A),
                    238, 270 (regular), 310, 342, 374 (regular); baseline 20px below the top
  right separators  rows 235 (#81B6FF fading to the column over x 219..352) and 236 (#EDEDED), and 307 and 308
  submenu arrow     4x7 triangle ending at x=368, rows 114..121 in My Recent Documents
  footer buttons    24px icons at y=444; Log Off icon x=176 and text x=204, Turn Off Computer icon x=251 and
                    text x=279, right edge 368, 12px between the buttons, text baseline 15px below the icon top

Fitted gradients, to the luna.msstyles bitmaps (tests/luna/luna_sprites.py; positions are pixels in the box, colours
"#RRGGBB" or "#AARRGGBB"), each reduced to the fewest linear stops that stay within 5 per channel:

  HEADER_STOPS            StartPanel.UserPane (StartUserPanel.bmp) centre columns, bitmap rows 1..62 as box rows 0..61
  LEFT_SHADE_STOPS, LEFT_HIGHLIGHT_STOPS, RIGHT_SHADE_STOPS
                          the bitmap's outer columns as one flat colour at a horizontal alpha profile over the header
                          gradient (a dark overlay, plus a light one on the left), fitted by random-perturbation hill
                          climbing for the fewest pixels more than 12 off
  RULE_STOPS              StartPanel.ProgList and StartPanel.PlacesList row 1 (x 2..189 and 190..), the bitmaps
                          stretched to their column
  FOOTER_STOPS            StartPanel.Logoff (StartPanelLogoffBackground.bmp) centre columns, bitmap rows 0..38 as box
                          rows 437..475
  FOOTER_LEFT_SHADE_STOPS, FOOTER_RIGHT_SHADE_STOPS
                          the bitmap's outer columns, fitted like the header's
  RIGHT_FADE_STOPS        StartPanel.PlacesList row 3, columns 372..377
CORNER_RADIUS             a circle tangent to both edges whose cut matches the reference's 3, 2, 1, 1 transparent
                          pixels on rows 0..3 of the top corners
"""

import getpass
import importlib.util
import json
import os
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygon,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

PALETTE_CANDIDATES = (
    Path(__file__).resolve().with_name("chicago95lunapalette.py"),
    Path(__file__).resolve().parents[1] / "palette.py",
)
_palette_spec = importlib.util.spec_from_file_location(
    "luna_palette", next(path for path in PALETTE_CANDIDATES if path.is_file())
)
_palette_module = importlib.util.module_from_spec(_palette_spec)
_palette_spec.loader.exec_module(_palette_module)
START_MENU_PALETTE = _palette_module.PALETTE["start_menu"]

WIDTH = 380
HEADER_HEIGHT = 64
RULE_HEIGHT = 2
BODY_TOP = HEADER_HEIGHT + RULE_HEIGHT
FOOTER_HEIGHT = 41
LEFT_COLUMN = QRect(2, BODY_TOP, 188, 370)
DIVIDER_X = 190
RIGHT_COLUMN = QRect(191, BODY_TOP, 187, 370)
HEIGHT = BODY_TOP + LEFT_COLUMN.height() + FOOTER_HEIGHT
FOOTER_TOP = HEIGHT - FOOTER_HEIGHT

ROW_PITCH_LEFT = 40
ROW_PITCH_RIGHT = 32
MOST_USED_SLOTS = 6
PINNED_TOP = 70
MOST_USED_TOP = 159
LEFT_SEPARATOR_ROWS = (155, 400)
ALL_PROGRAMS_RECT = QRect(2, 402, 188, 34)
RIGHT_ROW_TOPS = [70, 102, 134, 166, 198, 238, 270, 310, 342, 374]
RIGHT_BOLD_ROWS = 5
RIGHT_SEPARATOR_ROWS = (235, 307)
FOOTER_ICON_TOP = 444
FOOTER_RIGHT_EDGE = 368
FOOTER_BUTTON_GAP = 8
TEXT_MARGIN = 4

OUTER_EDGE = QColor("#1854C2")
FOOTER_LINE = QColor("#1865CD")
HOVER_FILL = QColor("#316AC5")
LEFT_TEXT = QColor("#1E1E1E")
SUBTITLE_TEXT = QColor("#808080")
RIGHT_TEXT = QColor("#0A246A")
WHITE = QColor("#FFFFFF")
HEADER_STOPS = [(0, "#65A1E5"), (1, "#71A8E6"), (2, "#3A7FD7"), (3, "#1969D0"), (8, "#0E60CA"), (28, "#1A6BD1"), (62, "#4792EB")]
HEADER_BOTTOM_LINE = QColor("#1B6BD1")
RULE_STOPS = [
    (4, "#FFFFFF"),
    (43, "#FFFAF6"),
    (118, "#FF9B3C"),
    (141, "#FF8819"),
    (198, "#FB8F2B"),
    (349, "#D7D6D9"),
    (375, "#CBD3DF"),
]
FOOTER_STOPS = [(FOOTER_TOP + 1, "#438AE3"), (FOOTER_TOP + 32, "#1366D4"), (FOOTER_TOP + 39, "#0C56C0")]
RIGHT_FADE_STOPS = [(372, "#D3E5FA"), (373, "#D2E4FA"), (375, "#C5DAF4"), (377, "#A6C2E6")]
LEFT_HIGHLIGHT_STOPS = [
    (1, "#61F7CED9"),
    (2, "#54F7CED9"),
    (3, "#46F7CED9"),
    (4, "#36F7CED9"),
    (6, "#1AF7CED9"),
    (9, "#00F7CED9"),
]
LEFT_SHADE_STOPS = [
    (1, "#000029D4"),
    (3, "#4B0029D4"),
    (6, "#3A0029D4"),
    (10, "#2F0029D4"),
    (15, "#270029D4"),
    (21, "#080029D4"),
    (28, "#000029D4"),
]
RIGHT_SHADE_STOPS = [
    (350, "#00000036"),
    (358, "#07000036"),
    (364, "#14000036"),
    (368, "#19000036"),
    (372, "#1A000036"),
    (378, "#23000036"),
]
FOOTER_LEFT_SHADE_STOPS = [
    (2, "#2F1140C6"),
    (5, "#681140C6"),
    (9, "#771140C6"),
    (15, "#531140C6"),
    (22, "#381140C6"),
    (31, "#171140C6"),
    (40, "#001140C6"),
]
FOOTER_RIGHT_SHADE_STOPS = [
    (350, "#000A1943"),
    (366, "#060A1943"),
    (370, "#0B0A1943"),
    (375, "#1F0A1943"),
    (377, "#320A1943"),
]
CORNER_RADIUS = 6
BODY_LEFT_LINE = QColor("#91A4DA")
BODY_RIGHT_LINE = QColor("#2B6DD1")
FOOTER_LEFT_LINE = QColor("#3D5EBB")
FOOTER_LEFT_GLOW = QColor("#B03D5EBB")
FOOTER_RIGHT_LINE = QColor("#1D5BC0")
DIVIDER_COLOUR = QColor("#95BDEE")
LEFT_SEPARATOR_COLOUR = QColor("#D3D3C8")
RIGHT_SEPARATOR_COLOURS = (QColor("#81B6FF"), QColor("#EDEDED"))

AVATAR_FRAME = QRect(7, 6, 52, 52)
AVATAR_PICTURE = QRect(9, 8, 48, 48)
USER_NAME_ORIGIN = QPoint(67, 37)
USER_NAME_PIXELS = 17
TEXT_PIXELS = 11

BROWSER_CATEGORY = "WebBrowser"
MAIL_CATEGORY = "Email"
RIGHT_ITEMS = [
    ("My Documents", "folder-documents", "my_documents"),
    ("My Recent Documents", "document-open-recent", None),
    ("My Pictures", "folder-pictures", "my_pictures"),
    ("My Music", "folder-music", "my_music"),
    ("My Computer", "computer", "my_computer"),
    ("Control Panel", "preferences-system", "control_panel"),
    ("Printers and Faxes", "printer", "printers"),
    ("Help and Support", "help-contents", "help"),
    ("Search", "system-search", "search"),
    ("Run...", "system-run", "run"),
]
FOOTER_ITEMS = [("Log Off", "system-log-out", "log_off"), ("Turn Off Computer", "system-shutdown", "shut_down")]
COMMAND_NAMES = [name for _text, _icon, name in RIGHT_ITEMS + FOOTER_ITEMS if name]


@dataclass(frozen=True)
class RowLook:
    icon_size: QSize
    icon_offset: QPoint
    text_x: int
    baseline: int
    subtitle_baseline: int
    colour: QColor
    shadow: bool = False
    highlights: bool = True


LEFT_LOOK = RowLook(QSize(32, 32), QPoint(8, 4), 44, 22, 31, LEFT_TEXT)
PINNED_LOOK = RowLook(QSize(32, 32), QPoint(8, 4), 44, 18, 31, LEFT_TEXT)
ALL_PROGRAMS_LOOK = RowLook(QSize(16, 24), QPoint(127, 5), 44, 20, 20, LEFT_TEXT)
RIGHT_LOOK = RowLook(QSize(24, 24), QPoint(6, 4), 34, 20, 20, RIGHT_TEXT)
FOOTER_LOOK = RowLook(QSize(24, 24), QPoint(0, 0), 28, 15, 15, WHITE, shadow=True, highlights=False)


@dataclass
class Row:
    rect: QRect
    text: str
    subtitle: str
    icon: QIcon
    bold: bool
    action: object
    submenu: object
    look: RowLook


def ui_font(bold=False):
    font = QFont("Tahoma")
    font.setPixelSize(TEXT_PIXELS)
    font.setBold(bold)
    font.setStyleStrategy(QFont.PreferAntialias)
    return font


def header_name_font():
    font = QFont("Trebuchet MS")
    font.setPixelSize(USER_NAME_PIXELS)
    font.setBold(True)
    font.setStyleStrategy(QFont.PreferAntialias)
    return font


def root_menu_height(apps=None, recent=None):
    return HEIGHT


def first_with_category(apps, category):
    return next((app for app in apps if category in app["categories"]), None)


def most_used(apps, usage, excluded):
    candidates = [app for app in apps if app not in excluded]
    counted = sorted((app for app in candidates if usage.get(app["path"], 0) > 0), key=lambda app: -usage[app["path"]])
    unused = [app for app in candidates if app not in counted]
    return (counted + unused)[:MOST_USED_SLOTS]


def read_usage(path):
    if path is None or not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text())


def write_usage(path, usage):
    if path is None:
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(usage))


def left_rows(apps, usage, icon, launch_app):
    pinned = [
        ("Internet", first_with_category(apps, BROWSER_CATEGORY)),
        ("E-mail", first_with_category(apps, MAIL_CATEGORY)),
    ]
    pinned = [(title, app) for title, app in pinned if app is not None]
    rows = [
        Row(
            QRect(LEFT_COLUMN.left(), PINNED_TOP + ROW_PITCH_LEFT * index, LEFT_COLUMN.width(), ROW_PITCH_LEFT),
            title, app["name"], icon(app), True, lambda app=app: launch_app(app), None, PINNED_LOOK,
        )
        for index, (title, app) in enumerate(pinned)
    ]  # fmt: skip
    frequent = most_used(apps, usage, [app for _title, app in pinned])
    rows += [
        Row(
            QRect(LEFT_COLUMN.left(), MOST_USED_TOP + ROW_PITCH_LEFT * index, LEFT_COLUMN.width(), ROW_PITCH_LEFT),
            app["name"], "", icon(app), False, lambda app=app: launch_app(app), None, LEFT_LOOK,
        )
        for index, app in enumerate(frequent)
    ]  # fmt: skip
    return rows


def all_programs_row(fill_menu):
    return Row(ALL_PROGRAMS_RECT, "All Programs", "", green_arrow_icon(), True, None, fill_menu, ALL_PROGRAMS_LOOK)


def right_rows(icon, run_command, fill_recent_menu):
    rows = []
    for index, (text, icon_name, command_name) in enumerate(RIGHT_ITEMS):
        rect = QRect(RIGHT_COLUMN.left() + 1, RIGHT_ROW_TOPS[index], 181, ROW_PITCH_RIGHT)
        action = (lambda name=command_name: run_command(name)) if command_name else None
        submenu = None if command_name else fill_recent_menu
        rows.append(Row(rect, text, "", icon(icon_name), index < RIGHT_BOLD_ROWS, action, submenu, RIGHT_LOOK))
    return rows


def footer_rows(icon, run_command, metrics):
    widths = [FOOTER_LOOK.text_x + metrics.horizontalAdvance(text) + TEXT_MARGIN for text, _icon, _name in FOOTER_ITEMS]
    rows = []
    right = FOOTER_RIGHT_EDGE + 1 + TEXT_MARGIN
    for (text, icon_name, command_name), width in reversed(list(zip(FOOTER_ITEMS, widths, strict=True))):
        rect = QRect(right - width, FOOTER_ICON_TOP, width, FOOTER_LOOK.icon_size.height())
        rows.append(
            Row(rect, text, "", icon(icon_name), False, lambda name=command_name: run_command(name), None, FOOTER_LOOK)
        )
        right -= width + FOOTER_BUTTON_GAP
    return rows[::-1]


def green_arrow_icon():
    pixmap = QPixmap(16, 24)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    gradient = QRadialGradient(QPointF(5, 9), 15)
    gradient.setColorAt(0, QColor("#B4E8B4"))
    gradient.setColorAt(0.45, QColor("#3DBE3D"))
    gradient.setColorAt(1, QColor("#16901B"))
    path = QPainterPath()
    path.moveTo(1.5, 1.5)
    path.lineTo(14.5, 12)
    path.lineTo(1.5, 22.5)
    path.closeSubpath()
    painter.setBrush(gradient)
    painter.setPen(QPen(QColor("#1C7C1C"), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


def rounded_top_outline():
    radius = CORNER_RADIUS
    outline = QPainterPath()
    outline.moveTo(0, HEIGHT)
    outline.lineTo(0, radius)
    outline.arcTo(0, 0, 2 * radius, 2 * radius, 180, -90)
    outline.lineTo(WIDTH - radius, 0)
    outline.arcTo(WIDTH - 2 * radius, 0, 2 * radius, 2 * radius, 90, -90)
    outline.lineTo(WIDTH, HEIGHT)
    outline.closeSubpath()
    return outline


def corner_cutouts():
    window = QPainterPath()
    window.addRect(0, 0, WIDTH, HEIGHT)
    return window.subtracted(rounded_top_outline())


def stops_gradient(start, end, stops, vertical=False):
    first, last = start + 0.5, end + 0.5
    gradient = QLinearGradient(0, first, 0, last) if vertical else QLinearGradient(first, 0, last, 0)
    for position, colour in stops:
        gradient.setColorAt((position - start) / (end - start), QColor(colour))
    return gradient


def fade_gradient(left, right, colour, background):
    gradient = QLinearGradient(left, 0, right, 0)
    gradient.setColorAt(0, background)
    gradient.setColorAt(0.15, colour)
    gradient.setColorAt(0.85, colour)
    gradient.setColorAt(1, background)
    return gradient


def paint_side_lines(painter, top, bottom, left_colour, right_colour):
    painter.fillRect(0, top, 1, bottom - top, OUTER_EDGE)
    painter.fillRect(WIDTH - 1, top, 1, bottom - top, OUTER_EDGE)
    painter.fillRect(1, top, 1, bottom - top, left_colour)
    painter.fillRect(WIDTH - 2, top, 1, bottom - top, right_colour)


def paint_header(painter):
    painter.fillRect(0, 0, WIDTH, HEADER_HEIGHT, stops_gradient(0, HEADER_HEIGHT - 2, HEADER_STOPS, vertical=True))
    painter.fillRect(0, HEADER_HEIGHT - 1, WIDTH, 1, HEADER_BOTTOM_LINE)
    painter.fillRect(1, 0, 27, HEADER_HEIGHT - 1, stops_gradient(1, 28, LEFT_SHADE_STOPS))
    painter.fillRect(1, 0, 8, HEADER_HEIGHT - 1, stops_gradient(1, 9, LEFT_HIGHLIGHT_STOPS))
    painter.fillRect(350, 0, 28, HEADER_HEIGHT - 1, stops_gradient(350, 378, RIGHT_SHADE_STOPS))
    painter.fillRect(0, 0, 1, HEADER_HEIGHT, OUTER_EDGE)
    painter.fillRect(WIDTH - 1, 0, 1, HEADER_HEIGHT, OUTER_EDGE)
    painter.fillRect(0, HEADER_HEIGHT, WIDTH, RULE_HEIGHT, stops_gradient(4, 375, RULE_STOPS))


def paint_body(painter):
    painter.fillRect(LEFT_COLUMN, QColor(START_MENU_PALETTE["left_column"]))
    painter.fillRect(DIVIDER_X, BODY_TOP, 1, LEFT_COLUMN.height(), DIVIDER_COLOUR)
    painter.fillRect(RIGHT_COLUMN, QColor(START_MENU_PALETTE["right_column"]))
    painter.fillRect(372, BODY_TOP, 6, LEFT_COLUMN.height(), stops_gradient(372, 378, RIGHT_FADE_STOPS))
    paint_side_lines(painter, BODY_TOP, FOOTER_TOP, BODY_LEFT_LINE, BODY_RIGHT_LINE)


def paint_footer(painter):
    painter.fillRect(0, FOOTER_TOP, WIDTH, 1, FOOTER_LINE)
    footer = QRect(0, FOOTER_TOP + 1, WIDTH, HEIGHT - FOOTER_TOP - 1)
    painter.fillRect(footer, stops_gradient(FOOTER_TOP + 1, HEIGHT - 1, FOOTER_STOPS, vertical=True))
    painter.fillRect(2, footer.top(), 38, footer.height(), stops_gradient(2, 40, FOOTER_LEFT_SHADE_STOPS))
    painter.fillRect(350, footer.top(), 28, footer.height(), stops_gradient(350, 378, FOOTER_RIGHT_SHADE_STOPS))
    painter.fillRect(2, footer.top(), 1, footer.height(), FOOTER_LEFT_GLOW)
    paint_side_lines(painter, FOOTER_TOP, HEIGHT, FOOTER_LEFT_LINE, FOOTER_RIGHT_LINE)


def paint_separators(painter):
    column = QColor(START_MENU_PALETTE["right_column"])
    for row in LEFT_SEPARATOR_ROWS:
        gradient = QLinearGradient(15, 0, 185, 0)
        gradient.setColorAt(0, WHITE)
        gradient.setColorAt(0.5, LEFT_SEPARATOR_COLOUR)
        gradient.setColorAt(1, WHITE)
        painter.fillRect(15, row, 170, 1, gradient)
    for row in RIGHT_SEPARATOR_ROWS:
        for offset, colour in enumerate(RIGHT_SEPARATOR_COLOURS):
            painter.fillRect(219, row + offset, 134, 1, fade_gradient(219, 353, colour, column))


def paint_avatar(painter, picture):
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor("#CCD6EB"), 2))
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(AVATAR_FRAME.adjusted(1, 1, -1, -1), 3, 3)
    painter.drawPixmap(AVATAR_PICTURE, picture)
    painter.setRenderHint(QPainter.Antialiasing, False)


def paint_user_name(painter, name):
    painter.setFont(header_name_font())
    painter.setPen(QColor(0, 0, 0, 110))
    painter.drawText(USER_NAME_ORIGIN + QPoint(1, 1), name)
    painter.setPen(WHITE)
    painter.drawText(USER_NAME_ORIGIN, name)


def paint_submenu_arrow(painter, row, colour):
    right = row.rect.right() - 4
    painter.setPen(Qt.NoPen)
    painter.setBrush(colour)
    middle = row.rect.top() + 16
    painter.drawPolygon(QPolygon([QPoint(right - 3, middle - 4), QPoint(right, middle), QPoint(right - 3, middle + 3)]))


def paint_row(painter, row, hovered):
    look = row.look
    selected = hovered and look.highlights
    if selected:
        painter.fillRect(row.rect, HOVER_FILL)
    colour = WHITE if selected else look.colour
    icon_rect = QRect(row.rect.topLeft() + look.icon_offset, look.icon_size)
    row.icon.paint(painter, icon_rect)
    font = ui_font(row.bold)
    painter.setFont(font)
    text_x = row.rect.left() + look.text_x
    room = row.rect.right() + 1 - text_x - (14 if row.submenu is not None else TEXT_MARGIN)
    metrics = QFontMetrics(font)
    baseline = row.rect.top() + look.baseline
    title = metrics.elidedText(row.text, Qt.ElideRight, room)
    if look.shadow:
        painter.setPen(QColor(0, 0, 0, 120))
        painter.drawText(QPoint(text_x + 1, baseline + 1), title)
    painter.setPen(colour)
    painter.drawText(QPoint(text_x, baseline), title)
    if row.subtitle:
        painter.setFont(ui_font(False))
        painter.setPen(WHITE if selected else SUBTITLE_TEXT)
        subtitle = QFontMetrics(ui_font(False)).elidedText(row.subtitle, Qt.ElideRight, room)
        painter.drawText(QPoint(text_x, row.rect.top() + look.subtitle_baseline), subtitle)
    if row.submenu is not None and look is RIGHT_LOOK:
        paint_submenu_arrow(painter, row, colour)


def default_user_picture(icon):
    return icon("user-identity").pixmap(AVATAR_PICTURE.size())


def load_user_picture(path, icon):
    pixmap = QPixmap(str(path)) if path is not None and Path(path).exists() else QPixmap()
    if pixmap.isNull():
        return default_user_picture(icon)
    return pixmap.scaled(AVATAR_PICTURE.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)


class LunaMenu(QWidget):
    """Rows are Row values; apps rows call launch(app), command rows call launch(command_list) or the callable."""

    def __init__(
        self,
        apps,
        recent,
        launch,
        icon,
        retro_menu_factory,
        click_shield_factory,
        user_name=None,
        user_picture=None,
        commands=None,
        parent=None,
        recent_path=None,
    ):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedSize(WIDTH, root_menu_height(apps, recent))
        self.apps, self.recent, self.launch, self.icon = apps, recent, launch, icon
        self.retro_menu_factory, self.click_shield_factory = retro_menu_factory, click_shield_factory
        self.recent_path = recent_path
        self.commands = commands or {}
        self.user_name = user_name or getpass.getuser()
        self.user_picture = load_user_picture(user_picture or Path.home() / ".face", icon)
        self.shield = None
        self.submenu = None
        self.hovered = None
        self.rows = self.build_rows()

    def build_rows(self):
        usage = read_usage(self.recent_path)
        rows = left_rows(self.apps, usage, self.icon, self.launch_app)
        rows.append(all_programs_row(self.fill_programs_menu))
        rows += right_rows(self.icon, self.run_command, self.fill_recent_menu)
        rows += footer_rows(self.icon, self.run_command, QFontMetrics(ui_font()))
        return rows

    def sizeHint(self):
        return QSize(WIDTH, root_menu_height(self.apps, self.recent))

    def launch_app(self, app):
        usage = read_usage(self.recent_path)
        usage[app["path"]] = usage.get(app["path"], 0) + 1
        write_usage(self.recent_path, usage)
        self.launch(app)
        self.close()

    def run_command(self, name):
        command = self.commands.get(name)
        self.close()
        if callable(command):
            command()
        elif command:
            self.launch(command)

    def fill_programs_menu(self, menu):
        for app in sorted(self.apps, key=lambda app: app["name"].lower()):
            action = menu.addAction(self.icon(app), app["name"])
            action.triggered.connect(lambda _checked=False, app=app: self.launch_app(app))

    def fill_recent_menu(self, menu):
        for location in self.recent:
            action = menu.addAction(self.icon("text-x-generic"), os.path.basename(location))
            action.triggered.connect(lambda _checked=False, loc=location: self.launch(["xdg-open", loc]))

    def open_submenu(self, row):
        menu = self.submenu = self.retro_menu_factory()
        row.submenu(menu)
        menu.popup(self.mapToGlobal(QPoint(row.rect.right() + 1, row.rect.top())))

    def activate(self, row):
        if row.submenu is not None:
            self.open_submenu(row)
            return
        row.action()

    def row_at(self, point):
        return next((row for row in self.rows if row.rect.contains(point)), None)

    def highlightable_rows(self):
        return [row for row in self.rows if row.look.highlights]

    def paintEvent(self, _event):
        painter = QPainter(self)
        paint_header(painter)
        paint_body(painter)
        paint_footer(painter)
        paint_separators(painter)
        paint_avatar(painter, self.user_picture)
        paint_user_name(painter, self.user_name)
        for row in self.rows:
            paint_row(painter, row, row is self.hovered)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.fillPath(corner_cutouts(), Qt.transparent)
        painter.end()

    def mouseMoveEvent(self, event):
        hovered = self.row_at(event.position().toPoint())
        if hovered is not self.hovered:
            self.hovered = hovered
            self.update()

    def leaveEvent(self, _event):
        self.hovered = None
        self.update()

    def mouseReleaseEvent(self, event):
        row = self.row_at(event.position().toPoint())
        if event.button() == Qt.LeftButton and row is not None:
            self.activate(row)

    def keyPressEvent(self, event):
        steps = {Qt.Key_Down: 1, Qt.Key_Up: -1}
        rows = self.highlightable_rows()
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() in steps:
            current = rows.index(self.hovered) if self.hovered in rows else (-1 if event.key() == Qt.Key_Down else 0)
            self.hovered = rows[(current + steps[event.key()]) % len(rows)]
            self.update()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter) and self.hovered is not None:
            self.activate(self.hovered)

    def showEvent(self, event):
        super().showEvent(event)
        if self.click_shield_factory is None or os.environ.get("QT_QPA_PLATFORM") == "wayland":
            return
        self.shield = self.click_shield_factory(self.close)
        self.shield.setGeometry(self.screen().geometry())
        self.shield.show()
        self.raise_()

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.shield is None:
            return
        self.shield.hide()
        self.shield.deleteLater()
        self.shield = None


def drawn_root_menu(apps, recent, icon, **options):
    menu = LunaMenu(apps, recent, lambda _item: None, icon, None, None, **options)
    menu.adjustSize()
    return menu.grab().toImage()
