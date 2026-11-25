"""The Control Panel window's Windows XP chrome: Explorer's header bands, tool buttons, status bar and logo box,
the progress bar and the Appearance preview's mock windows.

  header band   the window face #ECE9D8, a 1px white line along the top, no grips
  tool button   the icon in colour, no grips; hover and pressed are LunaStyle's rounded tool button; "Back" keeps
                its label beside the icon (xpmenu.png)
  status bar    flat #ECE9D8 with the 1px #ACA899 line on top (LunaStyle's PE_PanelStatusBar), panes without frames
  logo box      the XP flag on white at the right of the menu band (xpmenu.png)
  preview       windows drawn from luna/palette.py: title rows (30), left border rows (4), bottom border rows (4),
                the close, maximize and minimize buttons of luna/aurorae/theme/*.svg
"""

import importlib.util
from pathlib import Path

from chicago95luna import FIELD_BORDER, paint_push_button
from PySide6.QtCore import QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QProgressBar,
    QStatusBar,
    QStyle,
    QStyleOptionButton,
    QToolButton,
    QWidget,
)

HERE = Path(__file__).resolve()
PALETTE_CANDIDATES = (HERE.with_name("chicago95lunapalette.py"), HERE.parents[1] / "palette.py")
FLAG_CANDIDATES = (HERE.parent / "images" / "windows-xp-flag.svg", HERE.parents[1] / "images" / "windows-xp-flag.svg")
BUTTON_THEMES = (
    Path.home() / ".local/share/aurorae/themes/Chicago95Luna",
    HERE.parents[1] / "aurorae" / "theme",
)
_palette_spec = importlib.util.spec_from_file_location(
    "luna_control_panel_palette", next(path for path in PALETTE_CANDIDATES if path.is_file())
)
PALETTE = importlib.util.module_from_spec(_palette_spec)
_palette_spec.loader.exec_module(PALETTE)
PALETTE = PALETTE.PALETTE

FACE, BAND_LINE_TOP, STATUS_LINE = "#ECE9D8", "#FFFFFF", "#ACA899"
TOOL_ICON_SIZE = 24
LOGO_BOX_FACE = "#FFFFFF"
STATUS_PANE_SEPARATOR = "#D8D2BD"
PREVIEW_TITLE_HEIGHT = 22
PREVIEW_BORDER = 3
PREVIEW_RADIUS = 6
PREVIEW_BUTTON_SIZE = 18
PREVIEW_BUTTON_FILES = (
    ("minimize.svg", "active-center"),
    ("maximize.svg", "active-center"),
    ("close.svg", "active-center"),
)


def first_existing(candidates):
    return next(path for path in candidates if path.is_file())


class LunaHeaderBand(QWidget):
    def __init__(self, content=None, content_height=22, grip=True, trailing=None):
        super().__init__()
        self.setFixedHeight(1 + content_height)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0 if trailing else 2, 0)
        layout.setSpacing(0)
        if content is not None:
            layout.addWidget(content, 1)
        if trailing is not None:
            layout.addWidget(trailing)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().window())
        painter.fillRect(0, 0, self.width(), 1, QColor(BAND_LINE_TOP))


class LunaToolbarButton(QToolButton):
    def __init__(self, action, has_menu=False):
        super().__init__()
        self.setDefaultAction(action)
        self.has_menu = has_menu
        self.setAutoRaise(True)
        self.setIconSize(QSize(TOOL_ICON_SIZE, TOOL_ICON_SIZE))
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon if action.text() == "Back" else Qt.ToolButtonIconOnly)
        self.setFixedHeight(40)
        self.setAttribute(Qt.WA_Hover)
        if has_menu and action.menu() is not None:
            self.setPopupMode(QToolButton.MenuButtonPopup)


class LunaStatusPane(QWidget):
    def __init__(self, *contents):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 1, 0)
        layout.setSpacing(4)
        for widget in contents:
            layout.addWidget(widget, 1 if widget is contents[-1] else 0)

    def paintEvent(self, _event):
        QPainter(self).fillRect(self.width() - 1, 3, 1, self.height() - 6, QColor(STATUS_PANE_SEPARATOR))


class LunaStatusBar(QStatusBar):
    def __init__(self, panes):
        super().__init__()
        self.setSizeGripEnabled(True)
        self.setFixedHeight(22)
        self.panes = panes
        for pane, stretch in zip(panes, (5, 2, 3), strict=True):
            self.addWidget(pane, stretch)


class LunaLogoBox(QWidget):
    def __init__(self):
        super().__init__()
        self.flag = QSvgRenderer(str(first_existing(FLAG_CANDIDATES)))
        self.setFixedWidth(38)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(LOGO_BOX_FACE))
        height = self.height() - 6
        width = height * 296 / 261.5
        self.flag.render(painter, QRectF((self.width() - width) / 2, 3, width, height))


class LunaProgressBar(QProgressBar):
    def __init__(self):
        super().__init__()
        self.setTextVisible(False)


def title_gradient(rows, top, height):
    gradient = QLinearGradient(0, top, 0, top + height)
    for index, colour in enumerate(rows):
        gradient.setColorAt(index / (len(rows) - 1), QColor(colour))
    return gradient


class LunaAppearancePreview(QWidget):
    SIZE = QSize(358, 178)
    INACTIVE, ACTIVE, MESSAGE = QRect(10, 9, 302, 112), QRect(16, 29, 300, 126), QRect(22, 90, 212, 80)
    SHEET_SIZE = QSize(376, 188)
    SHEET_WINDOWS = QRect(8, 8, 347, 146), QRect(16, 26, 352, 144), QRect(128, 66, 120, 80)

    def __init__(self, *, property_sheet=False):
        super().__init__()
        self.property_sheet = property_sheet
        self.desktop = "#004E98"
        self.active_title = QRect()
        self.button_renderers = [
            QSvgRenderer(str(first_existing([theme / name for theme in BUTTON_THEMES])))
            for name, _element in PREVIEW_BUTTON_FILES
        ]
        self.setFixedSize(self.SHEET_SIZE if property_sheet else self.SIZE)

    def show_colors(self, active, inactive, desktop, look):
        self.desktop = desktop.split(",")[0]
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(self.desktop))
        if self.property_sheet:
            painter.setPen(QColor("#b4b3a4"))
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        inactive, active, message = self.SHEET_WINDOWS if self.property_sheet else (self.INACTIVE, self.ACTIVE, self.MESSAGE)
        self.window(painter, inactive, "Inactive Window", PALETTE["title_inactive"], 3, False)
        self.active_title = self.window(painter, active, "Active Window", PALETTE["title_active"], 3, True)
        if self.property_sheet:
            self.sheet_window_text(painter, active)
        else:
            self.menu_and_text(painter, active)
        self.window(painter, message, "Message Box", PALETTE["title_active"], 1, True)
        self.message(painter, message)

    def window(self, painter, rect, caption, title_rows, buttons, active):
        frame = QPainterPath()
        frame.addRoundedRect(QRectF(rect), PREVIEW_RADIUS, PREVIEW_RADIUS)
        painter.save()
        painter.setClipPath(frame)
        painter.fillRect(rect, QColor(PALETTE["border_left"][1]))
        painter.fillRect(rect.left(), rect.bottom() - 2, rect.width(), 3, QColor(PALETTE["border_bottom"][1]))
        title_height = 27 if self.property_sheet else PREVIEW_TITLE_HEIGHT
        title = QRect(rect.left(), rect.top(), rect.width(), title_height)
        painter.fillRect(title, title_gradient(title_rows, title.top(), title.height()))
        body = rect.adjusted(PREVIEW_BORDER, title_height, -PREVIEW_BORDER, -PREVIEW_BORDER)
        painter.fillRect(body, QColor(PALETTE["face"]))
        painter.restore()
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Trebuchet MS")
        if self.property_sheet:
            font.setFamilies(["Trebuchet MS", "Liberation Sans", "Noto Sans"])
        font.setPixelSize(11 if self.property_sheet else 13)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(title.adjusted(8, 0, 0, 0), Qt.AlignVCenter, caption)
        self.paint_buttons(painter, title, buttons, active)
        return title

    def paint_buttons(self, painter, title, count, active=True):
        size = 21 if self.property_sheet else PREVIEW_BUTTON_SIZE
        inset = 2 if self.property_sheet else 4
        top = title.top() + (4 if self.property_sheet else 2)
        for index, renderer in enumerate(self.button_renderers[-count:][::-1]):
            left = title.right() - inset - size * (index + 1) - 2 * index
            renderer.render(
                painter,
                "active-center" if active else "inactive-center",
                QRectF(left, top, size, size),
            )

    def menu_and_text(self, painter, rect):
        menu = QRect(
            rect.left() + PREVIEW_BORDER, rect.top() + PREVIEW_TITLE_HEIGHT, rect.width() - 2 * PREVIEW_BORDER, 18
        )
        painter.setFont(QFont("Tahoma", 8))
        left = menu.left() + 4
        for word, kind in (("Normal", "normal"), ("Disabled", "disabled"), ("Selected", "selected")):
            width = painter.fontMetrics().horizontalAdvance(word) + 12
            cell = QRect(left, menu.top(), width, menu.height())
            if kind == "selected":
                painter.fillRect(cell, QColor(PALETTE["selection"]))
            painter.setPen(QColor({"normal": "#000000", "disabled": "#ACA899", "selected": "#FFFFFF"}[kind]))
            painter.drawText(cell, Qt.AlignCenter, word)
            left += width
        text = QRect(menu.left() + 2, menu.bottom() + 3, menu.width() - 4, rect.bottom() - menu.bottom() - 8)
        painter.fillRect(text, QColor("#FFFFFF"))
        painter.setPen(QColor(FIELD_BORDER))
        painter.drawRect(text.adjusted(0, 0, -1, -1))
        painter.setPen(QColor("#000000"))
        painter.drawText(text.adjusted(4, 2, -20, 0), Qt.AlignTop | Qt.AlignLeft, "Window Text")

    def sheet_window_text(self, painter, rect):
        from chicago95lunascroll import paint_scroll_slider, paint_stepper, paint_trough

        body = rect.adjusted(PREVIEW_BORDER, PREVIEW_TITLE_HEIGHT + 5, -PREVIEW_BORDER, -PREVIEW_BORDER)
        painter.fillRect(body, Qt.white)
        painter.setFont(QFont("Tahoma", 8))
        painter.setPen(Qt.black)
        painter.drawText(body.adjusted(1, 0, -16, 0), Qt.AlignLeft | Qt.AlignTop, "Window Text")
        track = QRect(body.right() - 15, body.top(), 16, body.height())
        paint_trough(painter, track, False)
        for y, direction in ((track.top(), "up"), (track.bottom() - 15, "down")):
            paint_stepper(painter, QRect(track.left(), y, 16, 16), direction, "normal")
        paint_scroll_slider(painter, QRect(track.left(), track.top() + 16, 16, 17), False, "normal")

    def message(self, painter, rect):
        painter.setFont(QFont("Tahoma", 8))
        painter.setPen(QColor("#000000"))
        option = QStyleOptionButton()
        if self.property_sheet:
            option.rect = QRect(rect.left() + 29, rect.top() + 42, 62, 22)
        else:
            painter.drawText(rect.adjusted(10, PREVIEW_TITLE_HEIGHT + 6, 0, 0), Qt.AlignTop | Qt.AlignLeft, "Message Text")
            option.rect = QRect(rect.center().x() - 37, rect.bottom() - 30, 75, 23)
        option.state = QStyle.State_Enabled
        option.features = QStyleOptionButton.DefaultButton
        painter.save()
        paint_push_button(painter, option)
        painter.restore()
        painter.drawText(option.rect, Qt.AlignCenter, "OK")


CHROME_FIELDS = (
    LunaHeaderBand,
    LunaToolbarButton,
    LunaStatusBar,
    LunaStatusPane,
    LunaLogoBox,
    LunaProgressBar,
    LunaAppearancePreview,
)
