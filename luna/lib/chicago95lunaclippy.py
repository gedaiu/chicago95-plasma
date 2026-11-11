"""The Office XP assistant balloon: a #FFFFE1 rounded balloon with a 1px black border, a soft grey shadow to the
bottom right, a tail toward the character, antialiased Tahoma text and a Luna OK button."""

from chicago95lunanotify import paint_balloon
from PySide6.QtCore import QPoint, QPointF, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QPushButton, QWidget

BALLOON_WIDTH = 200
TEXT_MARGIN = QPoint(10, 8)
BUTTON_SIZE = QSize(75, 23)
BUTTON_GAP = 8
SHADOW_OFFSET = 2
SHADOW_COLOUR = QColor(0, 0, 0, 56)
SHADOW_RADIUS = 6
TAIL_LEFT = 35
TAIL_WIDTH = 14
TAIL_ROWS = 14
TAIL_TIP_SHIFT = -6
ASSISTANT_UNDER_BALLOON = QPoint(7, 6)
TIMEOUT_MS = 20_000
CLOSE_KEYS = (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter)


def tail_outline(body_height):
    seam = body_height - 1
    return [
        QPointF(TAIL_LEFT + 0.5, seam),
        QPointF(TAIL_LEFT + TAIL_WIDTH / 2 + TAIL_TIP_SHIFT + 0.5, seam + TAIL_ROWS),
        QPointF(TAIL_LEFT + TAIL_WIDTH + 0.5, seam),
    ]


def paint_tail(painter, body_height, face):
    outline = QPainterPath()
    outline.moveTo(tail_outline(body_height)[0])
    for corner in tail_outline(body_height)[1:]:
        outline.lineTo(corner)
    painter.setBrush(face)
    painter.setPen(QPen(QColor("#000000"), 1))
    painter.drawPath(outline)
    painter.setPen(QPen(face, 1))
    painter.drawLine(QPointF(TAIL_LEFT + 1, body_height - 1), QPointF(TAIL_LEFT + TAIL_WIDTH, body_height - 1))


def paint_luna_balloon(painter, size, palette):
    body = QSize(size.width() - SHADOW_OFFSET, size.height() - TAIL_ROWS - SHADOW_OFFSET)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(SHADOW_COLOUR)
    painter.drawRoundedRect(
        QRect(SHADOW_OFFSET, SHADOW_OFFSET, body.width(), body.height()), SHADOW_RADIUS, SHADOW_RADIUS
    )
    paint_balloon(painter, body, 1, palette)
    paint_tail(painter, body.height(), palette.color(QPalette.ToolTipBase))


class LunaBalloon(QWidget):
    def __init__(self, font, owner=None):
        super().__init__(owner, Qt.ToolTip | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.owner = owner
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFont(font)
        self.text = ""
        self.text_rect = QRect()
        self.ok_button = QPushButton("OK", self)
        self.ok_button.setFont(font)
        self.ok_button.setFixedSize(BUTTON_SIZE)
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.hide)
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.hide)

    def show_tip(self, text, assistant_at):
        self.text = text
        text_width = BALLOON_WIDTH - SHADOW_OFFSET - 2 * TEXT_MARGIN.x()
        self.text_rect = self.fontMetrics().boundingRect(
            QRect(TEXT_MARGIN.x(), TEXT_MARGIN.y(), text_width, 1000), Qt.TextWordWrap | Qt.AlignLeft, text
        )
        body_height = self.text_rect.bottom() + 1 + 2 * BUTTON_GAP + BUTTON_SIZE.height()
        self.resize(BALLOON_WIDTH, body_height + TAIL_ROWS + SHADOW_OFFSET)
        self.ok_button.move(
            BALLOON_WIDTH - SHADOW_OFFSET - BUTTON_GAP - BUTTON_SIZE.width(),
            body_height - BUTTON_GAP - BUTTON_SIZE.height(),
        )
        self.move(assistant_at - ASSISTANT_UNDER_BALLOON - QPoint(0, body_height - 1))
        if self.owner is not None and self.owner.windowHandle() is not None:
            self.winId()
            self.windowHandle().setTransientParent(self.owner.windowHandle())
        self.show()
        self.raise_()
        self.close_timer.start(TIMEOUT_MS)

    def paintEvent(self, _event):
        painter = QPainter(self)
        paint_luna_balloon(painter, self.size(), self.palette())
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.setPen(self.palette().color(QPalette.ToolTipText))
        painter.setFont(self.font())
        painter.drawText(self.text_rect, Qt.TextWordWrap | Qt.AlignLeft, self.text)

    def keyPressEvent(self, event):
        self.hide() if event.key() in CLOSE_KEYS else super().keyPressEvent(event)

    def mousePressEvent(self, _event):
        self.hide()
