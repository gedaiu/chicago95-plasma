"""Deterministic matte cleanup for opaque HD sprites; never redraw RGB artwork."""

from PIL import Image, ImageChops, ImageFilter
from PySide6.QtGui import QImage


def clean_matte(image: QImage) -> QImage:
    rgba = image.convertToFormat(QImage.Format_RGBA8888)
    pil = Image.frombytes("RGBA", (rgba.width(), rgba.height()), bytes(rgba.constBits()))
    alpha = pil.getchannel("A")
    # The paper/metal are solid objects. Keep their existing contour antialiasing
    # within one physical pixel of the opaque silhouette, but remove the distant
    # low-opacity clouds left by generated background removal. No global alpha
    # threshold: that would turn the smooth edge into a jagged binary cutout.
    core = alpha.point(lambda value: 255 if value >= 128 else 0)
    support = core.filter(ImageFilter.MaxFilter(3))
    cleaned_alpha = ImageChops.multiply(alpha, support)
    pil.putalpha(cleaned_alpha)
    # Discard hidden RGB as well. Some thumbnailers ignore alpha; straight-alpha
    # resamplers can also leak these yellow/gray colors back into the contour.
    pil.paste((0, 0, 0, 0), mask=cleaned_alpha.point(lambda value: 255 if value == 0 else 0))
    data = pil.tobytes()
    return QImage(data, pil.width, pil.height, pil.width * 4, QImage.Format_RGBA8888).copy()
