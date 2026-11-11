"""Windows XP Luna controls for the PySide6 tools: LunaStyle on Qt's Fusion base.

Every colour and size was sampled from the 1x originals in tests/references (x, y of the first pixel, 1x):

  push button        xpdisplayprop-1x.png, OK (default) x=158..232 y=422..444, Cancel x=239..313, Apply (disabled)
                     x=321..; halo 1px (rows 422 and 444, columns 158 and 232), border #003C74 on x=159..231
                     y=423..443, 19 face rows
                     (x=260, y=424..442) white .. #F0F0EA then #ECEBE6 #E2DFD6 #D6D0C5; default ring 2px
                     (rows #CEE7FF #BCD4F6 on top, #89ADE4 #6982EE at the bottom, sides #BAD2F5 .. #89ADE4);
                     disabled (x=340): face #F5F4EA, border #C9C7BA, text #A1A192; hover is not in the references
  check box          xpmouse.png x=33..45 y=91..103: border #1C5180, inner diagonal gradient #DCDCD7 .. #FFFFFF
  line edit, combo   xpdisplayprop-1x.png combo x=215..370 y=320..340: frame #7F9DB9, white ring, drop button x=354..368
                     (gradient #C9D8FC .. #B7C9F3, arrow #4D6185), column 17 wide with the ring
  spin box           xptimedate.png x=178..194 y=86..106: the same button, split at y=96
  tabs               xpdisplayprop-1x.png y=36..56: selected rows #E68B2C #FFC83C #FFC73C then #FCFCFE, sides #919B9C;
                     unselected from y=38: top #91A7B4, gradient white .. #F0F0EA, last row #ECEBE6, sides #919B9C;
                     page frame #919B9C, page fill #FCFCFE .. #F4F3EE
  group box          xpdisplayprop-1x.png x=24..380 y=311..372: frame #D0D0BF, title #0046D5
  menu, progress, header   not in the references: the plan's values (white menu, #ACA899 frame, 23px rows)
"""

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPalette, QPen, QPolygonF, QRegion
from PySide6.QtWidgets import QApplication, QFrame, QProxyStyle, QStyle, QStyleOptionButton, QTabBar

BUTTON_BORDER = "#003C74"
BUTTON_BORDER_DISABLED = "#C9C7BA"
BUTTON_PRESSED_GRADIENT = ["#D0CBBF", "#E2E0D8", "#DFDFD6", "#F0F0EC"]
BUTTON_FACE_DISABLED = "#F5F4EA"
BUTTON_GRADIENT = [
    "#FFFFFF", "#FEFEFE", "#FCFCFB", "#FAFAF9", "#F8F8F6", "#F6F6F3", "#F6F6F2", "#F5F5F1",
    "#F4F4F0", "#F3F3EF", "#F3F3EE", "#F2F2ED", "#F1F1ED", "#F1F1EC", "#F0F0EB", "#F0F0EA",
]  # fmt: skip
BUTTON_BOTTOM_ROWS = ["#ECEBE6", "#E2DFD6", "#D6D0C5"]
BUTTON_HALO = {"top": "#E1DDCA", "left": "#E1DDCA", "right": "#F0EEE0", "bottom": "#F8F7F0"}
DEFAULT_RING_TOP = ["#CEE7FF", "#BCD4F6"]
DEFAULT_RING_BOTTOM = ["#89ADE4", "#6982EE"]
DEFAULT_RING_SIDES = ("#BAD2F5", "#89ADE4")
HOVER_RING_LIGHT = ["#FFF0CF", "#FDD889"]
HOVER_RING_DARK = ["#F8B330", "#E59700"]
BUTTON_RADIUS = 3

FIELD_BORDER = "#7F9DB9"
FIELD_BORDER_DISABLED = "#C9C7BA"
FIELD_DISABLED_FILL = "#ECE9D8"
DROP_BUTTON_GRADIENT = ("#C9D8FC", "#B7C9F3")
DROP_BUTTON_HOVER_GRADIENT = ("#E1EAFE", "#CBDAFA")
DROP_BUTTON_HOVER_BORDER = "#FFC73C"
DROP_BUTTON_DIVIDER = "#CAD8FD"
DROP_ARROW = "#4D6185"
DROP_ARROW_DISABLED = "#ACA899"
DROP_COLUMN_WIDTH = 17
FIELD_HEIGHT = 21

INDICATOR_SIZE = 13
INDICATOR_BORDER = "#1C5180"
INDICATOR_FILL = [
    "#DCDCD7", "#DEDED9", "#E0E0DB", "#E2E2DE", "#E5E5E2", "#E8E8E5", "#ECECE9", "#EFEFEC", "#F1F1EF",
    "#F3F3F1", "#F5F5F4", "#F7F7F6", "#F9F9F8", "#FBFBFA", "#FDFDFC", "#FEFEFE", "#FFFFFF",
]  # fmt: skip
INDICATOR_FILL_PRESSED = ("#C3C1B7", "#DEDECF")
INDICATOR_FILL_DISABLED = "#FFFFFF"
INDICATOR_GLOW_LIGHT = "#FDDFA2"
INDICATOR_GLOW_DARK = "#FAC45D"
INDICATOR_BORDER_DISABLED = "#CAC8BB"
INDICATOR_MARK = "#21A121"
INDICATOR_MARK_DISABLED = "#CAC8BB"
CHECK_TICK = [
    ".....##",
    "....###",
    "#..###.",
    "##.##..",
    ".###...",
    "..##...",
    "...#...",
]

MENU_FRAME = "#ACA899"
MENU_ROW_HEIGHT = 21
MENU_SEPARATOR_HEIGHT = 6
MENU_SEPARATOR_MARGIN = 2
MENU_SEPARATOR_SHADOW = "#FFFFFF"
MENU_ARROW = "#000000"
MENU_ICON_COLUMN = 28
MENU_TEXT_DISABLED = "#ACA899"

GROUP_FRAME = "#D0D0BF"
GROUP_TITLE = "#0046D5"
GROUP_RADIUS = 4

TAB_BORDER = "#919B9C"
TAB_TOP_BORDER = "#91A7B4"
TAB_SELECTED_TOP = ["#E68B2C", "#FFC83C", "#FFC73C"]
TAB_SELECTED_FILL = "#FCFCFE"
TAB_GRADIENT = [
    "#FFFFFF", "#FEFEFE", "#FCFCFB", "#FAFAF9", "#F8F8F6", "#F6F6F3", "#F6F6F2", "#F5F5F1",
    "#F4F4F0", "#F3F3EF", "#F3F3EE", "#F2F2ED", "#F1F1ED", "#F1F1EC", "#F0F0EB", "#F0F0EA",
]  # fmt: skip
TAB_BOTTOM_ROW = "#ECEBE6"
TAB_HOVER_TOP = ["#FFC73C", "#FFC73C"]
TAB_HEIGHT = 21
TAB_RAISE = 2
TAB_PAGE_FILL = ("#FCFCFE", "#F4F3EE")
NORTH_TAB_SHAPES = (QTabBar.RoundedNorth, QTabBar.TriangularNorth)

PROGRESS_FRAME = "#68A3C6"
PROGRESS_CHUNK = "#39E63A"
PROGRESS_CHUNK_WIDTH = 8
PROGRESS_CHUNK_GAP = 2

HEADER_FACE = "#ECE9D8"
HEADER_FACE_PRESSED = "#D6D2C2"
HEADER_LINE = "#ACA899"
HEADER_HOVER_ROWS = ["#F8A900", "#F6C456", "#F8B31F"]

DISABLED_TEXT = "#A1A192"

ARROWS = {
    "combo": ["###...###", ".###.###.", "..#####..", "...###...", "....#...."],
    "down": ["###.###", ".#####.", "..###..", "...#..."],
    "up": ["...#...", "..###..", ".#####.", "###.###"],
}


def luna_palette():
    palette = QPalette()
    roles = {
        QPalette.Window: "#ECE9D8",
        QPalette.Button: "#ECE9D8",
        QPalette.WindowText: "#000000",
        QPalette.ButtonText: "#000000",
        QPalette.Text: "#000000",
        QPalette.BrightText: "#FFFFFF",
        QPalette.Base: "#FFFFFF",
        QPalette.AlternateBase: "#F5F4EA",
        QPalette.Highlight: "#316AC5",
        QPalette.HighlightedText: "#FFFFFF",
        QPalette.Light: "#FFFFFF",
        QPalette.Midlight: "#F1EFE2",
        QPalette.Mid: FIELD_BORDER,
        QPalette.Dark: BUTTON_BORDER,
        QPalette.Shadow: "#000000",
        QPalette.ToolTipBase: "#FFFFE1",
        QPalette.ToolTipText: "#000000",
        QPalette.Link: "#0000FF",
        QPalette.LinkVisited: "#800080",
    }
    for role, colour in roles.items():
        palette.setColor(role, QColor(colour))
    for role in (QPalette.WindowText, QPalette.ButtonText, QPalette.Text):
        palette.setColor(QPalette.Disabled, role, QColor(DISABLED_TEXT))
    palette.setColor(QPalette.Disabled, QPalette.Base, QColor(FIELD_DISABLED_FILL))
    return palette


def ui_font_family():
    return "Tahoma"


def luna_font():
    font = QFont(ui_font_family())
    font.setPixelSize(11)
    font.setStyleStrategy(QFont.PreferAntialias)
    return font


def gradient_rows(colours, count):
    last = max(count - 1, 1)
    return [colours[round(index * (len(colours) - 1) / last)] for index in range(count)]


def rows_up_from(colours, count):
    """The colours spread over count rows, counted from the bottom: the mirror of gradient_rows."""
    return gradient_rows(colours[::-1], count)[::-1]


def blend_rows(start, end, count):
    first, last = QColor(start), QColor(end)
    steps = max(count - 1, 1)
    return [
        QColor(
            *(round(a + (b - a) * index / steps) for a, b in zip(first.getRgb()[:3], last.getRgb()[:3], strict=True))
        ).name()
        for index in range(count)
    ]


def fill_rows(painter, rect, colours):
    for index, colour in enumerate(colours):
        painter.fillRect(rect.left(), rect.top() + index, rect.width(), 1, QColor(colour))


def fill_columns(painter, rect, colours):
    for index, colour in enumerate(colours):
        painter.fillRect(rect.left() + index, rect.top(), 1, rect.height(), QColor(colour))


def stroke_rect(painter, rect, colour):
    painter.fillRect(rect.left(), rect.top(), rect.width(), 1, QColor(colour))
    painter.fillRect(rect.left(), rect.bottom(), rect.width(), 1, QColor(colour))
    painter.fillRect(rect.left(), rect.top(), 1, rect.height(), QColor(colour))
    painter.fillRect(rect.right(), rect.top(), 1, rect.height(), QColor(colour))


def rounded_path(rect, radius, line=1):
    path = QPainterPath()
    half = line / 2
    path.addRoundedRect(QRectF(rect).adjusted(half, half, -half, -half), radius, radius)
    return path


def stroke_rounded(painter, rect, radius, colour, line=1):
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor(colour), line))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(rounded_path(rect, radius, line))
    painter.restore()


def device_pixels(painter, rect):
    """The rect in the device's own pixels, with the painter turned to draw in them: 1 logical pixel lines
    would otherwise land on one or two device rows by turns at fractional scales."""
    scale = painter.device().devicePixelRatioF()
    painter.scale(1 / scale, 1 / scale)
    scaled = [round(value * scale) for value in (rect.left(), rect.top(), rect.width(), rect.height())]
    return QRect(*scaled), scale


def pixel_cell(painter):
    """A pixel-art cell in device pixels: 1 at 1x, 2 at 1.5x and 2x. Cells of one and two pixels by turns, which
    plain scaling gives at 1.5x, break the arrows' straight edges."""
    return max(1, round(painter.device().devicePixelRatioF()))


def paint_pixels(painter, left, top, rows, colour):
    """The pattern with its top-left cell at the logical point, drawn in whole device-pixel cells."""
    scale = painter.device().devicePixelRatioF()
    paint_cells(painter, round(left * scale), round(top * scale), rows, colour)


def paint_centred_pixels(painter, rect, rows, colour):
    scale, cell = painter.device().devicePixelRatioF(), pixel_cell(painter)
    device = QRect(*(round(value * scale) for value in (rect.left(), rect.top(), rect.width(), rect.height())))
    left = device.left() + (device.width() - len(rows[0]) * cell) // 2
    top = device.top() + (device.height() - len(rows) * cell) // 2
    paint_cells(painter, left, top, rows, colour)


def paint_cells(painter, device_left, device_top, rows, colour):
    scale, cell = painter.device().devicePixelRatioF(), pixel_cell(painter)
    painter.save()
    painter.scale(1 / scale, 1 / scale)
    for y, row in enumerate(rows):
        for x, mark in enumerate(row):
            if mark == "#":
                painter.fillRect(device_left + x * cell, device_top + y * cell, cell, cell, QColor(colour))
    painter.restore()


def button_state(option):
    features = getattr(option, "features", QStyleOptionButton.ButtonFeature.None_)
    candidates = [
        ("disabled", not option.state & QStyle.State_Enabled),
        ("pressed", bool(option.state & QStyle.State_Sunken)),
        ("hover", bool(option.state & QStyle.State_MouseOver)),
        ("default", bool(features & QStyleOptionButton.DefaultButton)),
    ]
    return next((name for name, active in candidates if active), "normal")


def paint_ring(painter, rect, colours):
    for depth, colour in enumerate(colours):
        stroke_rect(painter, rect.adjusted(depth, depth, -depth, -depth), colour)


def paint_button_gradient(painter, face, ring):
    bottom = gradient_rows(BUTTON_BOTTOM_ROWS, round(len(BUTTON_BOTTOM_ROWS) * ring / 2))
    fill_rows(painter, face, gradient_rows(BUTTON_GRADIENT, face.height() - len(bottom)) + bottom)


def paint_default_ring(painter, face, ring):
    paint_button_gradient(painter, face, ring)
    fill_rows(painter, face, gradient_rows(DEFAULT_RING_TOP, ring))
    fill_rows(
        painter,
        QRect(face.left(), face.bottom() - ring + 1, face.width(), ring),
        rows_up_from(DEFAULT_RING_BOTTOM, ring),
    )
    sides = blend_rows(*DEFAULT_RING_SIDES, face.height() - 2 * ring)
    for edge in (face.left(), face.right() - ring + 1):
        fill_rows(painter, QRect(edge, face.top() + ring, ring, len(sides)), sides)


def paint_hover_ring(painter, face, ring):
    paint_button_gradient(painter, face, ring)
    light, dark = gradient_rows(HOVER_RING_LIGHT, ring), gradient_rows(HOVER_RING_DARK[::-1], ring)
    for depth in range(ring):
        painter.fillRect(face.left() + depth, face.top(), 1, face.height(), QColor(light[depth]))
        painter.fillRect(face.right() - depth, face.top(), 1, face.height(), QColor(dark[depth]))
        painter.fillRect(face.left(), face.top() + depth, face.width(), 1, QColor(light[depth]))
        painter.fillRect(face.left(), face.bottom() - depth, face.width(), 1, QColor(dark[depth]))


BUTTON_FACES = {
    "normal": paint_button_gradient,
    "default": paint_default_ring,
    "hover": paint_hover_ring,
    "pressed": lambda painter, face, ring: fill_rows(
        painter, face, gradient_rows(BUTTON_PRESSED_GRADIENT, face.height())
    ),
    "disabled": lambda painter, face, ring: painter.fillRect(face, QColor(BUTTON_FACE_DISABLED)),
}


def paint_button_halo(painter, rect, line):
    painter.fillRect(rect.left(), rect.top(), rect.width(), line, QColor(BUTTON_HALO["top"]))
    painter.fillRect(rect.left(), rect.bottom() - line + 1, rect.width(), line, QColor(BUTTON_HALO["bottom"]))
    painter.fillRect(rect.left(), rect.top() + line, line, rect.height() - 2 * line, QColor(BUTTON_HALO["left"]))
    painter.fillRect(
        rect.right() - line + 1, rect.top() + line, line, rect.height() - 2 * line, QColor(BUTTON_HALO["right"])
    )


def paint_push_button(painter, option):
    state = button_state(option)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    rect, scale = device_pixels(painter, option.rect)
    line, ring, radius = max(1, int(scale)), round(2 * scale), BUTTON_RADIUS * scale
    body = rect.adjusted(line, line, -line, -line)
    if state != "disabled":
        painter.save()
        painter.setClipPath(rounded_path(rect, radius + line, 0), Qt.IntersectClip)
        paint_button_halo(painter, rect, line)
        painter.restore()
    painter.setClipPath(rounded_path(body, radius, line), Qt.IntersectClip)
    BUTTON_FACES[state](painter, body.adjusted(line, line, -line, -line), ring)
    painter.setClipping(False)
    border = BUTTON_BORDER_DISABLED if state == "disabled" else BUTTON_BORDER
    stroke_rounded(painter, body, radius, border, line)
    painter.restore()


def paint_field_frame(painter, rect, option):
    enabled = bool(option.state & QStyle.State_Enabled)
    stroke_rect(painter, rect, FIELD_BORDER if enabled else FIELD_BORDER_DISABLED)


def paint_line_edit_panel(painter, option):
    enabled = bool(option.state & QStyle.State_Enabled)
    painter.fillRect(option.rect, option.palette.brush(QPalette.Base if enabled else QPalette.Window))
    if getattr(option, "lineWidth", 1) > 0:
        paint_field_frame(painter, option.rect, option)


def indicator_box(rect):
    left = rect.left() + (rect.width() - INDICATOR_SIZE) // 2
    top = rect.top() + (rect.height() - INDICATOR_SIZE) // 2
    return QRect(left, top, INDICATOR_SIZE, INDICATOR_SIZE)


def indicator_colours(option):
    enabled = bool(option.state & QStyle.State_Enabled)
    return (
        INDICATOR_BORDER if enabled else INDICATOR_BORDER_DISABLED,
        INDICATOR_MARK if enabled else INDICATOR_MARK_DISABLED,
    )


def paint_indicator_gradient(painter, inner, shades):
    for y in range(inner.height()):
        for x in range(inner.width()):
            shade = shades[min(max(x + y - 2, 0), len(shades) - 1)]
            painter.fillRect(inner.left() + x, inner.top() + y, 1, 1, QColor(shade))


def paint_indicator_glow(painter, inner):
    for depth in range(2):
        ring = inner.adjusted(depth, depth, -depth, -depth)
        painter.fillRect(ring.left(), ring.top(), ring.width(), 1, QColor(INDICATOR_GLOW_LIGHT))
        painter.fillRect(ring.left(), ring.top(), 1, ring.height(), QColor(INDICATOR_GLOW_LIGHT))
        painter.fillRect(ring.left(), ring.bottom(), ring.width(), 1, QColor(INDICATOR_GLOW_DARK))
        painter.fillRect(ring.right(), ring.top(), 1, ring.height(), QColor(INDICATOR_GLOW_DARK))


def indicator_state(option):
    candidates = [
        ("disabled", not option.state & QStyle.State_Enabled),
        ("pressed", bool(option.state & QStyle.State_Sunken)),
        ("hover", bool(option.state & QStyle.State_MouseOver)),
    ]
    return next((name for name, active in candidates if active), "normal")


INDICATOR_FILLERS = {
    "disabled": lambda painter, inner: painter.fillRect(inner, QColor(INDICATOR_FILL_DISABLED)),
    "pressed": lambda painter, inner: paint_indicator_gradient(
        painter, inner, blend_rows(*INDICATOR_FILL_PRESSED, len(INDICATOR_FILL))
    ),
    "hover": lambda painter, inner: (
        paint_indicator_gradient(painter, inner, INDICATOR_FILL),
        paint_indicator_glow(painter, inner),
    ),
    "normal": lambda painter, inner: paint_indicator_gradient(painter, inner, INDICATOR_FILL),
}


def paint_indicator_fill(painter, box, option):
    INDICATOR_FILLERS[indicator_state(option)](painter, box.adjusted(1, 1, -1, -1))


def paint_check_box(painter, option):
    box = indicator_box(option.rect)
    border, mark = indicator_colours(option)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    paint_indicator_fill(painter, box, option)
    stroke_rect(painter, box, border)
    if option.state & QStyle.State_On:
        paint_pixels(painter, box.left() + 3, box.top() + 3, CHECK_TICK, mark)
    painter.restore()


def paint_radio_button(painter, option):
    box = indicator_box(option.rect)
    border, mark = indicator_colours(option)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    painter.setClipPath(rounded_path(box, INDICATOR_SIZE / 2), Qt.IntersectClip)
    paint_indicator_fill(painter, box, option)
    painter.setClipping(False)
    painter.setRenderHint(QPainter.Antialiasing)
    stroke_rounded(painter, box, INDICATOR_SIZE / 2, border)
    if option.state & QStyle.State_On:
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(mark))
        painter.drawEllipse(QRectF(box.adjusted(4, 4, -4, -4)))
    painter.restore()


def paint_menu_panel(painter, option):
    painter.fillRect(option.rect, option.palette.brush(QPalette.Base))
    stroke_rect(painter, option.rect, MENU_FRAME)


def paint_menu_frame(painter, option):
    stroke_rect(painter, option.rect, MENU_FRAME)


def paint_menu_separator(painter, option):
    painter.fillRect(option.rect, option.palette.brush(QPalette.Base))
    left = option.rect.left() + MENU_ICON_COLUMN
    width = option.rect.width() - MENU_ICON_COLUMN - MENU_SEPARATOR_MARGIN
    line_top = option.rect.top() + MENU_SEPARATOR_MARGIN
    painter.fillRect(left, line_top, width, 1, QColor(MENU_FRAME))
    painter.fillRect(left, line_top + 1, width, 1, QColor(MENU_SEPARATOR_SHADOW))


def menu_text_colour(option):
    enabled = bool(option.state & QStyle.State_Enabled)
    selected = bool(option.state & QStyle.State_Selected) and enabled
    colours = {
        (True, True): option.palette.color(QPalette.HighlightedText),
        (True, False): option.palette.color(QPalette.Text),
        (False, True): QColor(MENU_TEXT_DISABLED),
        (False, False): QColor(MENU_TEXT_DISABLED),
    }
    return colours[(enabled, selected)]


def paint_menu_arrow(painter, rect, colour):
    middle = rect.center().y()
    right = rect.right() - 8
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    painter.setPen(Qt.NoPen)
    painter.setBrush(colour)
    painter.drawPolygon(
        QPolygonF([QPointF(right - 4, middle - 3), QPointF(right, middle + 0.5), QPointF(right - 4, middle + 4)])
    )
    painter.restore()


def paint_menu_icon(painter, option, colour):
    column = QRect(option.rect.left(), option.rect.top(), MENU_ICON_COLUMN, option.rect.height())
    if not option.icon.isNull():
        mode = QIcon.Normal if option.state & QStyle.State_Enabled else QIcon.Disabled
        pixmap = option.icon.pixmap(QSize(16, 16), mode)
        painter.drawPixmap(column.left() + 4, column.top() + (column.height() - pixmap.height()) // 2, pixmap)
        return
    if option.checked:
        paint_centred_pixels(painter, column, CHECK_TICK, colour.name())


def paint_menu_texts(painter, option, colour):
    label, _, shortcut = option.text.partition("\t")
    flags = Qt.AlignVCenter | Qt.TextSingleLine | Qt.TextShowMnemonic | Qt.TextDontClip
    painter.setFont(option.font)
    painter.setPen(colour)
    text_rect = option.rect.adjusted(MENU_ICON_COLUMN + 2, 0, -18, 0)
    painter.drawText(text_rect, flags | Qt.AlignLeft, label)
    painter.drawText(text_rect, flags | Qt.AlignRight, shortcut)


def paint_menu_row(painter, option):
    selected = bool(option.state & QStyle.State_Selected) and bool(option.state & QStyle.State_Enabled)
    painter.fillRect(option.rect, option.palette.brush(QPalette.Highlight if selected else QPalette.Base))
    colour = menu_text_colour(option)
    paint_menu_icon(painter, option, colour)
    paint_menu_texts(painter, option, colour)
    if option.menuItemType == option.MenuItemType.SubMenu:
        selected_arrow = {True: colour, False: QColor(MENU_ARROW)}
        paint_menu_arrow(
            painter, option.rect, selected_arrow[colour == option.palette.color(QPalette.HighlightedText) and selected]
        )


def paint_menu_item(painter, option):
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    painter_for = {True: paint_menu_separator, False: paint_menu_row}
    painter_for[option.menuItemType == option.MenuItemType.Separator](painter, option)
    painter.restore()


def paint_group_frame(painter, rect):
    stroke_rounded(painter, rect, GROUP_RADIUS, GROUP_FRAME)


def paint_group_label(painter, option, label_rect):
    enabled = bool(option.state & QStyle.State_Enabled)
    painter.setPen(QColor(GROUP_TITLE if enabled else DISABLED_TEXT))
    painter.drawText(label_rect, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextShowMnemonic | Qt.TextSingleLine, option.text)


def tab_edges(option):
    position = option.position
    open_left = position in (option.TabPosition.Beginning, option.TabPosition.OnlyOneTab)
    open_right = position in (option.TabPosition.End, option.TabPosition.OnlyOneTab)
    return (0 if open_left else 2, 0 if open_right else 2)


def tab_body_rows(rect, selected):
    first_row = rect.top() if selected else rect.top() + TAB_RAISE
    return first_row, rect.bottom() - (0 if selected else 1)


def paint_selected_tab(painter, rect):
    top, bottom = rect.top(), rect.bottom()
    painter.fillRect(rect.left(), top, rect.width(), bottom - top + 1, QColor(TAB_SELECTED_FILL))
    fill_rows(painter, rect, TAB_SELECTED_TOP)
    painter.fillRect(rect.left(), top, 1, bottom - top + 1, QColor(TAB_BORDER))
    painter.fillRect(rect.right(), top, 1, bottom - top + 1, QColor(TAB_BORDER))
    painter.fillRect(rect.left(), top, 1, 1, QColor(TAB_SELECTED_TOP[0]))
    painter.fillRect(rect.right(), top, 1, 1, QColor(TAB_SELECTED_TOP[0]))


def paint_unselected_tab(painter, rect, hovered=False):
    top, bottom = tab_body_rows(rect, False)
    body = QRect(rect.left(), top + 1, rect.width(), bottom - top)
    fill_rows(painter, body, gradient_rows(TAB_GRADIENT, body.height() - 1) + [TAB_BOTTOM_ROW])
    painter.fillRect(rect.left(), top, rect.width(), 1, QColor(TAB_TOP_BORDER))
    if hovered:
        fill_rows(painter, QRect(rect.left() + 1, top, rect.width() - 2, 2), TAB_HOVER_TOP)
    painter.fillRect(rect.left(), top, 1, bottom - top + 1, QColor(TAB_BORDER))
    painter.fillRect(rect.right(), top, 1, bottom - top + 1, QColor(TAB_BORDER))


def paint_tab_shape(painter, option):
    selected = bool(option.state & QStyle.State_Selected)
    left_spread, right_spread = tab_edges(option) if selected else (0, 0)
    rect = option.rect.adjusted(-left_spread, 0, right_spread, 0)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    if selected:
        paint_selected_tab(painter, rect)
    else:
        paint_unselected_tab(painter, rect, bool(option.state & QStyle.State_MouseOver))
    painter.restore()


def paint_tab_page(painter, option):
    rect = option.rect
    inner = rect.adjusted(1, 1, -1, -1)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    fill_rows(painter, inner, blend_rows(*TAB_PAGE_FILL, inner.height()))
    stroke_rect(painter, rect, TAB_BORDER)
    painter.restore()


def paint_tab_base(painter, option):
    painter.fillRect(option.rect.left(), option.rect.bottom(), option.rect.width(), 1, QColor(TAB_BORDER))


def blue_button_rows(height, pressed):
    colours = blend_rows(*DROP_BUTTON_GRADIENT, height)
    return colours[::-1] if pressed else colours


def paint_blue_button(painter, rect, pressed=False, hovered=False):
    rows = (
        blend_rows(*DROP_BUTTON_HOVER_GRADIENT, rect.height()) if hovered else blue_button_rows(rect.height(), pressed)
    )
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setClipPath(rounded_path(rect, 2.5), Qt.IntersectClip)
    painter.setRenderHint(QPainter.Antialiasing, False)
    fill_rows(painter, rect, rows)
    painter.restore()
    if hovered:
        stroke_rounded(painter, rect, 2.5, DROP_BUTTON_HOVER_BORDER)


def paint_disabled_blue_button(painter, rect):
    painter.fillRect(rect, QColor(BUTTON_FACE_DISABLED))
    stroke_rounded(painter, rect, 2.5, BUTTON_BORDER_DISABLED)


def drop_button_painter(option, sub_control):
    state = option.state
    if not state & QStyle.State_Enabled:
        return paint_disabled_blue_button
    active = bool(option.activeSubControls & sub_control)
    pressed = active and bool(state & QStyle.State_Sunken)
    hovered = active and bool(state & QStyle.State_MouseOver) and not pressed
    return lambda painter, rect: paint_blue_button(painter, rect, pressed, hovered)


def arrow_colour(option):
    return DROP_ARROW if option.state & QStyle.State_Enabled else DROP_ARROW_DISABLED


def drop_column(rect):
    return QRect(rect.right() - DROP_COLUMN_WIDTH, rect.top() + 1, DROP_COLUMN_WIDTH, rect.height() - 2)


def paint_field_background(painter, option):
    enabled = bool(option.state & QStyle.State_Enabled)
    painter.fillRect(option.rect, option.palette.brush(QPalette.Base if enabled else QPalette.Window))
    paint_field_frame(painter, option.rect, option)


def paint_combo_box(painter, option):
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    paint_field_background(painter, option)
    button = drop_column(option.rect).adjusted(1, 1, -1, -1)
    drop_button_painter(option, QStyle.SC_ComboBoxArrow)(painter, button)
    paint_centred_pixels(painter, button, ARROWS["combo"], arrow_colour(option))
    painter.restore()


def spin_halves(button):
    upper_height = button.height() // 2
    return (
        QRect(button.left(), button.top(), button.width(), upper_height),
        QRect(button.left(), button.top() + upper_height + 1, button.width(), button.height() - upper_height - 1),
    )


def paint_spin_box(painter, option):
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    paint_field_background(painter, option)
    button = drop_column(option.rect).adjusted(1, 1, -1, -1)
    upper, lower = spin_halves(button)
    drop_button_painter(option, QStyle.SC_SpinBoxUp)(painter, upper)
    drop_button_painter(option, QStyle.SC_SpinBoxDown)(painter, lower)
    painter.fillRect(button.left(), upper.bottom() + 1, button.width(), 1, QColor(DROP_BUTTON_DIVIDER))
    paint_centred_pixels(painter, upper, ARROWS["up"], arrow_colour(option))
    paint_centred_pixels(painter, lower, ARROWS["down"], arrow_colour(option))
    painter.restore()


def paint_progress_groove(painter, option):
    painter.fillRect(option.rect, option.palette.brush(QPalette.Base))
    stroke_rect(painter, option.rect, PROGRESS_FRAME)


def progress_chunk_count(option, width):
    span = max(option.maximum - option.minimum, 1)
    filled = width * (option.progress - option.minimum) / span
    return round(filled / (PROGRESS_CHUNK_WIDTH + PROGRESS_CHUNK_GAP))


def paint_progress_chunks(painter, option):
    inner = option.rect.adjusted(1, 1, -1, -1)
    for index in range(progress_chunk_count(option, inner.width())):
        left = inner.left() + index * (PROGRESS_CHUNK_WIDTH + PROGRESS_CHUNK_GAP)
        painter.fillRect(left, inner.top(), PROGRESS_CHUNK_WIDTH, inner.height(), QColor(PROGRESS_CHUNK))


def paint_header_section(painter, option):
    pressed = bool(option.state & QStyle.State_Sunken)
    rect = option.rect
    painter.fillRect(rect, QColor(HEADER_FACE_PRESSED if pressed else HEADER_FACE))
    painter.fillRect(rect.right(), rect.top(), 1, rect.height(), QColor(HEADER_LINE))
    painter.fillRect(rect.left(), rect.bottom(), rect.width(), 1, QColor(HEADER_LINE))
    if option.state & QStyle.State_MouseOver and not pressed:
        fill_rows(painter, QRect(rect.left(), rect.bottom() - 2, rect.width() - 1, 3), HEADER_HOVER_ROWS)


def group_label_rect_clip(frame_rect, label_rect):
    return QRegion(frame_rect.adjusted(-1, -1, 1, 1)).subtracted(QRegion(label_rect.adjusted(-2, 0, 2, 0)))


PIXEL_METRICS = {
    QStyle.PM_ButtonMargin: 6,
    QStyle.PM_DefaultFrameWidth: 1,
    QStyle.PM_IndicatorWidth: INDICATOR_SIZE,
    QStyle.PM_IndicatorHeight: INDICATOR_SIZE,
    QStyle.PM_ExclusiveIndicatorWidth: INDICATOR_SIZE,
    QStyle.PM_ExclusiveIndicatorHeight: INDICATOR_SIZE,
    QStyle.PM_TabBarTabHSpace: 12,
    QStyle.PM_TabBarTabVSpace: 8,
    QStyle.PM_TabBarBaseOverlap: 1,
    QStyle.PM_TabBarTabShiftHorizontal: 0,
    QStyle.PM_TabBarTabShiftVertical: 0,
    QStyle.PM_MenuHMargin: 1,
    QStyle.PM_MenuVMargin: 1,
    QStyle.PM_MenuPanelWidth: 1,
    QStyle.PM_ButtonShiftHorizontal: 0,
    QStyle.PM_ButtonShiftVertical: 0,
    QStyle.PM_ScrollBarExtent: 17,
    QStyle.PM_ScrollBarSliderMin: 17,
    QStyle.PM_SliderThickness: 21,
    QStyle.PM_SliderLength: 11,
    QStyle.PM_SliderControlThickness: 21,
}


class LunaStyle(QProxyStyle):
    def __init__(self):
        super().__init__("Fusion")
        self.primitive_painters = {
            QStyle.PE_PanelButtonCommand: paint_push_button,
            QStyle.PE_FrameLineEdit: lambda painter, option: paint_field_frame(painter, option.rect, option),
            QStyle.PE_PanelLineEdit: paint_line_edit_panel,
            QStyle.PE_IndicatorCheckBox: paint_check_box,
            QStyle.PE_IndicatorRadioButton: paint_radio_button,
            QStyle.PE_PanelMenu: paint_menu_panel,
            QStyle.PE_FrameMenu: paint_menu_frame,
            QStyle.PE_FrameGroupBox: lambda painter, option: paint_group_frame(painter, option.rect),
            QStyle.PE_FrameTabWidget: paint_tab_page,
        }
        self.control_painters = {
            QStyle.CE_PushButtonBevel: paint_push_button,
            QStyle.CE_MenuItem: paint_menu_item,
            QStyle.CE_ProgressBarGroove: paint_progress_groove,
            QStyle.CE_ProgressBarContents: paint_progress_chunks,
            QStyle.CE_HeaderSection: paint_header_section,
        }
        self.complex_painters = {
            QStyle.CC_ComboBox: paint_combo_box,
            QStyle.CC_SpinBox: paint_spin_box,
        }
        self.styled_painters = {
            QStyle.CC_ScrollBar: "paint_scroll_bar",
            QStyle.CC_Slider: "paint_slider",
        }
        import chicago95lunascroll
        import chicago95lunawidgets

        self.scroll_module = chicago95lunascroll
        self.primitive_painters.update(chicago95lunawidgets.PRIMITIVE_PAINTERS)
        self.control_painters.update(chicago95lunawidgets.CONTROL_PAINTERS)

    def standardPalette(self):
        return luna_palette()

    def polish(self, subject):
        if not isinstance(subject, QApplication):
            return super().polish(subject)
        subject.setPalette(luna_palette())
        subject.setFont(luna_font())

    def pixelMetric(self, metric, option=None, widget=None):
        if metric in PIXEL_METRICS:
            return PIXEL_METRICS[metric]
        return super().pixelMetric(metric, option, widget)

    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PE_FrameTabBarBase and option.shape in NORTH_TAB_SHAPES:
            return paint_tab_base(painter, option)
        painter_for = self.primitive_painters.get(element)
        if painter_for is None:
            return super().drawPrimitive(element, option, painter, widget)
        painter_for(painter, option)

    def drawControl(self, element, option, painter, widget=None):
        handlers = {
            QStyle.CE_TabBarTabShape: self.draw_tab_shape,
            QStyle.CE_TabBarTabLabel: self.draw_tab_label,
            QStyle.CE_ShapedFrame: self.draw_shaped_frame,
        }
        handler = handlers.get(element)
        painter_for = self.control_painters.get(element)
        if handler is not None:
            return handler(element, option, painter, widget)
        if painter_for is None or not self.handles_orientation(element, option):
            return super().drawControl(element, option, painter, widget)
        painter_for(painter, option)

    def handles_orientation(self, element, option):
        progress_elements = (QStyle.CE_ProgressBarGroove, QStyle.CE_ProgressBarContents)
        return element not in progress_elements or bool(option.state & QStyle.State_Horizontal)

    def draw_tab_shape(self, element, option, painter, widget):
        if option.shape not in NORTH_TAB_SHAPES:
            return super().drawControl(element, option, painter, widget)
        paint_tab_shape(painter, option)

    def draw_shaped_frame(self, element, option, painter, widget):
        if option.frameShape != QFrame.StyledPanel:
            return super().drawControl(element, option, painter, widget)
        self.drawPrimitive(QStyle.PE_Frame, option, painter, widget)

    def draw_tab_label(self, element, option, painter, widget):
        label_option = type(option)(option)
        selected = bool(option.state & QStyle.State_Selected)
        label_option.rect = option.rect.adjusted(0, 0 if selected else TAB_RAISE, 0, 0)
        super().drawControl(element, label_option, painter, widget)

    def drawComplexControl(self, control, option, painter, widget=None):
        if control == QStyle.CC_GroupBox:
            return self.draw_group_box(option, painter, widget)
        if control in self.styled_painters:
            return getattr(self.scroll_module, self.styled_painters[control])(painter, option, self, widget)
        painter_for = self.complex_painters.get(control)
        if painter_for is None:
            return super().drawComplexControl(control, option, painter, widget)
        painter_for(painter, option)

    def draw_group_box(self, option, painter, widget):
        frame = self.subControlRect(QStyle.CC_GroupBox, option, QStyle.SC_GroupBoxFrame, widget)
        label = self.subControlRect(QStyle.CC_GroupBox, option, QStyle.SC_GroupBoxLabel, widget)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setClipRegion(group_label_rect_clip(frame, label))
        paint_group_frame(painter, frame)
        painter.setClipping(False)
        paint_group_label(painter, option, label)
        painter.restore()
        if option.subControls & QStyle.SC_GroupBoxCheckBox:
            self.draw_group_check_box(option, painter, widget)

    def draw_group_check_box(self, option, painter, widget):
        indicator = QStyleOptionButton()
        indicator.state = option.state | (QStyle.State_On if option.state & QStyle.State_On else QStyle.State_Off)
        indicator.palette = option.palette
        indicator.rect = self.subControlRect(QStyle.CC_GroupBox, option, QStyle.SC_GroupBoxCheckBox, widget)
        self.drawPrimitive(QStyle.PE_IndicatorCheckBox, indicator, painter, widget)

    def subControlRect(self, control, option, sub_control, widget=None):
        if control == QStyle.CC_ComboBox:
            return self.combo_rect(option, sub_control, widget)
        if control == QStyle.CC_SpinBox:
            return self.spin_rect(option, sub_control, widget)
        return super().subControlRect(control, option, sub_control, widget)

    def combo_rect(self, option, sub_control, widget):
        column = drop_column(option.rect)
        rects = {
            QStyle.SC_ComboBoxArrow: column,
            QStyle.SC_ComboBoxEditField: QRect(
                option.rect.left() + 2,
                option.rect.top() + 2,
                column.left() - option.rect.left() - 2,
                option.rect.height() - 4,
            ),
            QStyle.SC_ComboBoxFrame: option.rect,
            QStyle.SC_ComboBoxListBoxPopup: option.rect,
        }
        return rects.get(sub_control) or super().subControlRect(QStyle.CC_ComboBox, option, sub_control, widget)

    def spin_rect(self, option, sub_control, widget):
        column = drop_column(option.rect)
        upper, lower = spin_halves(column)
        rects = {
            QStyle.SC_SpinBoxUp: upper.adjusted(0, -1, 0, 0),
            QStyle.SC_SpinBoxDown: lower.adjusted(0, 0, 0, 1),
            QStyle.SC_SpinBoxEditField: QRect(
                option.rect.left() + 1,
                option.rect.top() + 1,
                column.left() - option.rect.left() - 1,
                option.rect.height() - 2,
            ),
            QStyle.SC_SpinBoxFrame: option.rect,
        }
        return rects.get(sub_control) or super().subControlRect(QStyle.CC_SpinBox, option, sub_control, widget)

    def sizeFromContents(self, contents_type, option, size, widget=None):
        base = super().sizeFromContents(contents_type, option, size, widget)
        adjusters = {
            QStyle.CT_MenuItem: lambda: menu_item_size(option, base),
            QStyle.CT_TabBarTab: lambda: QSize(base.width(), max(base.height(), TAB_HEIGHT)),
            QStyle.CT_ComboBox: lambda: QSize(base.width(), max(base.height(), FIELD_HEIGHT)),
            QStyle.CT_SpinBox: lambda: QSize(base.width(), max(base.height(), FIELD_HEIGHT)),
            QStyle.CT_PushButton: lambda: push_button_size(option, base),
        }
        return adjusters.get(contents_type, lambda: base)()


def menu_item_size(option, base):
    is_separator = option.menuItemType == option.MenuItemType.Separator
    return QSize(base.width(), {True: MENU_SEPARATOR_HEIGHT, False: MENU_ROW_HEIGHT}[is_separator])


def push_button_size(option, base):
    has_caption = bool(getattr(option, "text", ""))
    return QSize(max(base.width(), 75 if has_caption else 0), max(base.height(), 23))
