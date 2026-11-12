"""HD Clippy artwork assembly: local eye layers keep the rest of each frame fixed.

This experimental blink pack does not replace the original 43-animation atlas.
"""

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QImage, QPainter, QPainterPath

MASTER_SIZE = QSize(1448, 1086)
FRAME_SIZE = QSize(496, 372)  # four physical pixels per original logical pixel
# Measured on the approved HD rest-pose master. Only these eye surfaces may move.
EYES = (QRectF(418, 238, 184, 184), QRectF(635, 276, 184, 182))
SEQUENCE = ((0, 2200), (1, 60), (2, 100), (1, 60), (0, 700))


def read_master(path: Path):
    image = QImage(str(path)).convertToFormat(QImage.Format_ARGB32)
    if image.isNull() or image.size() != MASTER_SIZE:
        raise ValueError(f"HD source must be {MASTER_SIZE.width()}×{MASTER_SIZE.height()}: {path}")
    return image


def compose_eye_frame(base: QImage, eyes: QImage):
    """Treat generated eye poses as layers, not independent redraws of the body."""
    if base.size() != MASTER_SIZE or eyes.size() != MASTER_SIZE:
        raise ValueError("HD eye layers and master must have identical canvas dimensions")
    result = base.copy()
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    for rect in EYES:
        clip.addEllipse(rect)
    painter.setClipPath(clip)
    painter.drawImage(0, 0, eyes)
    painter.end()
    return result


def frames(folder: Path):
    base = read_master(folder / "rest-pose-v1.png")
    layers = (
        base,
        compose_eye_frame(base, read_master(folder / "blink-half-source.png")),
        compose_eye_frame(base, read_master(folder / "blink-closed-source.png")),
    )
    return [image.scaled(FRAME_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation) for image in layers]
