"""The Windows XP tray balloon as the notification popup (the "Take a tour of Windows XP" balloon of
tests/references/xpdesktop.png, measured at 1x, x then y of the first pixel):

  balloon       x=416..740 y=487..563 (325x77), 1px #000000 border, rounded corners, #FFFFE1 fill
  info icon     16x16 at 12,6 from the balloon's corner
  title         bold Tahoma 11px from x=36, cap top y=10, black
  body          Tahoma 11px from x=12, lines 13px apart, first cap top y=30, black
  close box     16x16 at x=303,y=5: 1px #C7BEA6 border, #FFFFF5 fill, an X of two 2px strokes #AA9C87 7px wide
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import QAbstractButton, QHBoxLayout, QLabel, QWidget

BALLOON_BORDER = "#000000"
BALLOON_RADIUS = 6
CLOSE_BORDER, CLOSE_FACE, CLOSE_GLYPH = "#C7BEA6", "#FFFFF5", "#AA9C87"
CLOSE_HOVER_BORDER, CLOSE_PRESSED_FACE = "#AA9C87", "#EDE8D0"
CLOSE_SIZE = 16
CLOSE_GLYPH_REACH = 3.5
CLOSE_GLYPH_WIDTH = 2
ICON_SIZE = 16
TITLE_GAP = 8
TEXT_PIXEL_SIZE = 11
FRAME_MARGINS = (12, 6, 6, 8)
CONTENT_MARGINS = (0, 5, 0, 0)


def paint_balloon(painter, size, device_pixel_ratio, palette):
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor(BALLOON_BORDER), 1))
    painter.setBrush(palette.color(QPalette.ToolTipBase))
    painter.drawRoundedRect(QRectF(0.5, 0.5, size.width() - 1, size.height() - 1), BALLOON_RADIUS, BALLOON_RADIUS)


def close_box_colours(down, hovered):
    return (
        QColor(CLOSE_PRESSED_FACE if down else CLOSE_FACE),
        QColor(CLOSE_HOVER_BORDER if hovered or down else CLOSE_BORDER),
    )


class LunaCloseBox(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(CLOSE_SIZE, CLOSE_SIZE)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_Hover)

    def paintEvent(self, _event):
        face, border = close_box_colours(self.isDown(), self.underMouse())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(border, 1))
        painter.setBrush(face)
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 2.5, 2.5)
        centre = QPointF(self.width() / 2, self.height() / 2)
        painter.setPen(QPen(QColor(CLOSE_GLYPH), CLOSE_GLYPH_WIDTH, Qt.SolidLine, Qt.FlatCap))
        reach = CLOSE_GLYPH_REACH
        painter.drawLine(centre + QPointF(-reach, -reach), centre + QPointF(reach, reach))
        painter.drawLine(centre + QPointF(-reach, reach), centre + QPointF(reach, -reach))


class LunaTitleRow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(CLOSE_SIZE)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(ICON_SIZE, ICON_SIZE)
        self.title_label = QLabel()
        font = self.title_label.font()
        font.setBold(True)
        font.setPixelSize(TEXT_PIXEL_SIZE)
        self.title_label.setFont(font)
        self.close_button = LunaCloseBox()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(TITLE_GAP)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label, 1)
        layout.addWidget(self.close_button)

    def set_content(self, pixmap, title):
        self.icon_label.setPixmap(pixmap) if pixmap else self.icon_label.clear()
        self.title_label.setText(self.title_label.fontMetrics().elidedText(title, Qt.ElideRight, self.width() or 260))


CHROME_FIELDS = (LunaTitleRow, FRAME_MARGINS, CONTENT_MARGINS, paint_balloon, False, TEXT_PIXEL_SIZE, True)
