"""Windows 7 notification-area balloon. The lower-right tail points towards the tray."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QWidget


def paint_balloon(painter, size, _dpr, _palette, anchor=None):
    w, bottom = size.width() - 3, size.height() - 17
    shape = QPainterPath()
    shape.addRoundedRect(QRectF(0.5, 0.5, w, bottom), 4, 4)
    tail = QPainterPath()
    tip = w - 17 if anchor is None else max(6, min(w - 6, anchor))
    base = tip - 18 if tip > w / 2 else tip + 18
    tail.moveTo(base, bottom - 1)
    tail.lineTo(tip, bottom + 15)
    tail.lineTo(tip, bottom - 1)
    tail.closeSubpath()
    shape = shape.united(tail)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.fillPath(shape.translated(2, 2), QColor(0, 0, 0, 55))
    fill = QLinearGradient(0, 0, 0, bottom)
    fill.setColorAt(0, QColor("#ffffff"))
    fill.setColorAt(1, QColor("#e4e8f0"))
    painter.setPen(QPen(QColor("#767676"), 1))
    painter.setBrush(fill)
    painter.drawPath(shape)


class BalloonTitle(QWidget):
    def __init__(self):
        super().__init__()
        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setTextFormat(Qt.PlainText)
        self.title_label.setStyleSheet('color: #003399; font: 15px "Segoe UI", "Noto Sans";')
        self.close_button = QToolButton()
        self.close_button.setAccessibleName("Close")
        self.close_button.setText("×")
        self.close_button.setFocusPolicy(Qt.NoFocus)
        self.close_button.setFixedSize(16, 16)
        self.close_button.setStyleSheet("""
            QToolButton { border: none; color: #737373; background: transparent; font: bold 15px sans-serif; }
            QToolButton:hover { color: #333; background: #d7dee8; }
            QToolButton:pressed { background: #bdcad9; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.title_label, 1)
        layout.addWidget(self.close_button, 0, Qt.AlignTop)

    def set_content(self, _pixmap, title):
        self.title_label.setText(title)


CHROME_FIELDS = (BalloonTitle, (10, 8, 10, 26), (0, 0, 0, 0), paint_balloon, True, 12, True, True)
