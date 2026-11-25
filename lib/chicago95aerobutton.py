"""Aero push-button artwork and hover transitions shared by the Qt dialogs."""

from math import ceil, floor
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, QRectF, QSignalBlocker, QStandardPaths, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen, QTextLayout
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton, QStyle, QStyleOptionButton, QStylePainter


def aero_button_artwork():
    path = Path(__file__).resolve().parents[1] / "aero/shutdown-button.svg"
    if not path.is_file():
        path = QStandardPaths.locate(QStandardPaths.GenericDataLocation, "chicago95/aero-shutdown-button.svg")
    return QSvgRenderer(str(path))


def mnemonic_caption(text):
    prefix, marker, suffix = text.partition("&")
    if marker and suffix and "&" not in suffix:
        return prefix + suffix, len(prefix.encode("utf-16-le")) // 2
    return None


def paint_mnemonic_underline(painter, caption, contents, color):
    text, position = caption
    layout = QTextLayout(text, painter.font(), painter.device())
    layout.beginLayout()
    line = layout.createLine()
    layout.endLayout()
    start = line.cursorToX(position)[0]
    end = line.cursorToX(layout.nextCursorPosition(position))[0]
    x = contents.x() + (contents.width() - line.naturalTextWidth()) / 2
    baseline = contents.y() + (contents.height() - line.height()) / 2 + line.ascent()
    transform = painter.deviceTransform()
    left = round(transform.map(QPointF(x + min(start, end), baseline)).x())
    right = floor(transform.map(QPointF(x + max(start, end), baseline)).x())
    row = floor(transform.map(QPointF(x, baseline)).y()) + 1
    inverse, invertible = transform.inverted()
    if invertible:
        underline = QRectF(left, row, max(1, right - left), 1)
        painter.fillRect(inverse.mapRect(underline), color)


class AeroDialogButton(QPushButton):
    # Milliseconds, from the Windows 7 Basic guest's Cancel-button capture.
    HOVER_DELAY, FADE_IN, FADE_OUT = 120, 400, 1500

    def __init__(self, label, artwork, parent, *, default_face="default", normal_face="normal"):
        super().__init__(label, parent)
        self.artwork = artwork
        self.default_face = default_face
        self.normal_face = normal_face
        self.face_rect = None
        self.aligned_geometry = None
        self.glow = 0.0
        self.hover_target = 0.0
        self.hover_delay = QTimer(self)
        self.hover_delay.setSingleShot(True)
        self.hover_delay.timeout.connect(self.fade_hover)
        self.hover_animation = QVariantAnimation(self)
        self.hover_animation.valueChanged.connect(self.update_glow)

    def update_glow(self, value):
        self.glow = value
        self.update()

    def fade_hover(self):
        duration = self.FADE_IN if self.hover_target else self.FADE_OUT
        start = self.glow
        with QSignalBlocker(self.hover_animation):
            self.hover_animation.setStartValue(start)
            self.hover_animation.setEndValue(self.hover_target)
            self.hover_animation.setDuration(round(duration * abs(self.hover_target - start)))
        self.hover_animation.start()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.set_hover_target(1.0)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.set_hover_target(0.0)

    def set_hover_target(self, target):
        self.hover_target = target
        self.hover_animation.stop()
        self.hover_delay.start(self.HOVER_DELAY)

    def set_aligned_geometry(self, x, y, width, height):
        """Fit the floating-point SVG canvas inside the integer QWidget bounds."""
        self.aligned_geometry = (x, y, width, height)
        scale = self.devicePixelRatioF()
        left, top = (floor(value * scale) / scale for value in (x, y))
        width, height = (round(value * scale) / scale for value in (width, height))
        outer_x, outer_y = floor(left), floor(top)
        self.face_rect = QRectF(left - outer_x, top - outer_y, width, height)
        self.setGeometry(outer_x, outer_y, ceil(self.face_rect.right()), ceil(self.face_rect.bottom()))

    def event(self, event):
        result = super().event(event)
        if event.type() == QEvent.DevicePixelRatioChange and self.aligned_geometry is not None:
            self.set_aligned_geometry(*self.aligned_geometry)
        return result

    def paint_caption(self, painter, option):
        # Qt's scaled underline becomes two device pixels tall. Aero's is one
        # pixel, with the same label advances whether the underline is shown or hidden.
        caption = mnemonic_caption(option.text)
        if caption is None or not option.icon.isNull():
            painter.drawControl(QStyle.CE_PushButtonLabel, option)
            return
        option.text = caption[0]
        painter.drawControl(QStyle.CE_PushButtonLabel, option)
        style = self.style()
        if not style.styleHint(QStyle.SH_UnderlineShortcut, option, self):
            return
        content = style.subElementRect(QStyle.SE_PushButtonContents, option, self)
        if option.state & (QStyle.State_Sunken | QStyle.State_On):
            content.translate(
                style.pixelMetric(QStyle.PM_ButtonShiftHorizontal, option, self),
                style.pixelMetric(QStyle.PM_ButtonShiftVertical, option, self),
            )
        paint_mnemonic_underline(painter, caption, content, option.palette.buttonText())

    def paintEvent(self, event):
        if not self.artwork.isValid() or not self.isEnabled():
            super().paintEvent(event)
            return
        painter = QStylePainter(self)
        rect = self.face_rect if self.face_rect is not None else QRectF(self.rect())
        if self.isDown():
            self.artwork.render(painter, "pressed", rect)
        elif self.glow >= 1:
            self.artwork.render(painter, "hover", rect)
        else:
            self.artwork.render(painter, self.default_face if self.isDefault() else self.normal_face, rect)
            if self.glow > 0:
                painter.setOpacity(self.glow)
                self.artwork.render(painter, "hover", rect)
                painter.setOpacity(1)
        if self.hasFocus() or self.isDown():
            painter.save()
            painter.setCompositionMode(QPainter.CompositionMode_Difference)
            pen = QPen(QColor(Qt.white), 1)
            pen.setCosmetic(True)
            pen.setCapStyle(Qt.FlatCap)
            pen.setDashPattern([1, 1])
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self.rect().adjusted(2, 2, -3, -3))
            painter.restore()
        option = QStyleOptionButton()
        self.initStyleOption(option)
        self.paint_caption(painter, option)
