"""The Windows XP "Windows is shutting down..." screen (tests/references/xpshuttingdown.png, 800x600).

Top band y=0..77 #00309C, a 1px #AFC8F6 line at y=78, the middle #5A7EDC, a 1px orange line at y=504 and the
bottom band from y=505 (#3833AC on the left to #00309C on the right); the flag and the text sit left of centre.
"""

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

BAND = "#00309C"
TOP_LINE = "#AFC8F6"
MIDDLE = "#5A7EDC"
BOTTOM_LINE = "#C1814D"
BOTTOM_LEFT = "#3833AC"
TOP_BAND_SHARE = 78 / 600
BOTTOM_BAND_SHARE = 96 / 600
TEXT = "Windows is shutting down..."
FLAG_CANDIDATES = (
    Path(__file__).resolve().parent / "images" / "windows-xp-flag.svg",
    Path(__file__).resolve().parents[1] / "images" / "windows-xp-flag.svg",
)
FLAG = next(path for path in FLAG_CANDIDATES if path.is_file())
CENTRE_SHARE = (0.545, 0.5)


def shutting_down_font(height):
    font = QFont("Tahoma")
    font.setPixelSize(round(height * 20 / 600))
    font.setStyleStrategy(QFont.PreferAntialias)
    return font


class ShuttingDownScreen(QWidget):
    def __init__(self, geometry, hold_until_input):
        super().__init__()
        self.hold_until_input = hold_until_input
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setCursor(Qt.BlankCursor)
        self.setGeometry(geometry)
        self.flag = QSvgRenderer(str(FLAG))

    def paintEvent(self, _event):
        width, height = self.width(), self.height()
        top, bottom = round(height * TOP_BAND_SHARE), round(height * (1 - BOTTOM_BAND_SHARE))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(0, 0, width, height, QColor(MIDDLE))
        painter.fillRect(0, 0, width, top, QColor(BAND))
        painter.fillRect(0, top, width, 1, QColor(TOP_LINE))
        floor = QLinearGradient(0, 0, width, 0)
        floor.setColorAt(0, QColor(BOTTOM_LEFT))
        floor.setColorAt(1, QColor(BAND))
        painter.fillRect(0, bottom, width, height - bottom, floor)
        painter.fillRect(0, bottom, width, 1, QColor(BOTTOM_LINE))
        self.paint_flag(painter, width, height)
        painter.setFont(shutting_down_font(height))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(0, height * 0.5, width * 2 * CENTRE_SHARE[0], height * 0.1), Qt.AlignCenter, TEXT)
        painter.end()

    def paint_flag(self, painter, width, height):
        flag_height = height * 0.14
        flag_width = flag_height * 296 / 261.5
        self.flag.render(
            painter, QRectF(width * CENTRE_SHARE[0] - flag_width / 2, height * 0.36, flag_width, flag_height)
        )

    def keyPressEvent(self, event):
        if self.hold_until_input:
            self.close()

    def mousePressEvent(self, event):
        if self.hold_until_input:
            self.close()
