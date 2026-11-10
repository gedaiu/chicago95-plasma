"""Draws a nine-piece frame SVG the way KDE's FrameSvg (KSvg) does, for tests that compare our Plasma
style and window decoration with the originals.

The pieces are "<prefix>-topleft", "-top", ... "-center". The border widths are the edge pieces' sizes
(top's height, left's width, ...); corners are drawn at those sizes, edges stretched along their length,
the centre stretched or, with a "<prefix>-hint-tile-center" element, tiled from its top-left. A
disabled border is not drawn: the centre and the remaining edges extend over its place.
"""
from PySide6.QtCore import QRectF, QSizeF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

from reference import qimage_to_pil

ALL_BORDERS = frozenset({"top", "bottom", "left", "right"})


def element(prefix, name):
    return f"{prefix}-{name}" if prefix else name


def size_of(renderer, prefix, name):
    return renderer.boundsOnElement(element(prefix, name)).size() if renderer.elementExists(element(prefix, name)) else QSizeF(0, 0)


def paint_frame(painter, renderer, prefix, rect, borders=ALL_BORDERS):
    """Paints the frame filling rect (a QRectF) with the given borders enabled."""
    top = size_of(renderer, prefix, "top").height() if "top" in borders else 0
    bottom = size_of(renderer, prefix, "bottom").height() if "bottom" in borders else 0
    left = size_of(renderer, prefix, "left").width() if "left" in borders else 0
    right = size_of(renderer, prefix, "right").width() if "right" in borders else 0
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    inner_w, inner_h = w - left - right, h - top - bottom
    pieces = {
        "topleft": (x, y, left, top), "top": (x + left, y, inner_w, top), "topright": (x + w - right, y, right, top),
        "left": (x, y + top, left, inner_h), "right": (x + w - right, y + top, right, inner_h),
        "bottomleft": (x, y + h - bottom, left, bottom), "bottom": (x + left, y + h - bottom, inner_w, bottom),
        "bottomright": (x + w - right, y + h - bottom, right, bottom),
    }
    for name, (px, py, pw, ph) in pieces.items():
        if pw > 0 and ph > 0:
            renderer.render(painter, element(prefix, name), QRectF(px, py, pw, ph))
    centre = QRectF(x + left, y + top, inner_w, inner_h)
    if renderer.elementExists(element(prefix, "hint-tile-center")):
        tile = size_of(renderer, prefix, "center")
        painter.save()
        painter.setClipRect(centre)
        ty = centre.y()
        while ty < centre.bottom():
            tx = centre.x()
            while tx < centre.right():
                renderer.render(painter, element(prefix, "center"), QRectF(tx, ty, tile.width(), tile.height()))
                tx += tile.width()
            ty += tile.height()
        painter.restore()
    else:
        renderer.render(painter, element(prefix, "center"), centre)


def render_frame(svg_path, prefix, width, height, borders=ALL_BORDERS):
    """The frame alone, width x height, as a PIL image."""
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(Qt.magenta)
    painter = QPainter(image)
    paint_frame(painter, QSvgRenderer(str(svg_path)), prefix, QRectF(0, 0, width, height), borders)
    painter.end()
    return qimage_to_pil(image)
