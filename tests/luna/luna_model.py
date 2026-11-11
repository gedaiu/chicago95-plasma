"""Draws a Luna window the way tests/aurorae_model.py draws a flat one, but from a theme directory and with alpha.

aurorae_model.Window reads Chicago95rc and renders opaque RGB; the Luna frame has transparent rounded corners and
its own rc name, so this subclass reuses its button layout and button painting and replaces the rest.
"""

import configparser
import sys
from pathlib import Path

from aurorae_model import Window
from conftest import REPO
from framesvg import paint_frame
from PIL import Image, ImageFilter
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from reference import differing_pixels

LUNA_THEME = REPO / "luna/aurorae/theme"
GENERATOR = REPO / "luna/aurorae/make_luna_aurorae.py"
MAXIMIZED_KEYS = ("TitleEdgeTop", "TitleEdgeLeft", "TitleEdgeRight")


def title_font():
    font = QFont("Trebuchet MS")
    font.setPixelSize(13)
    font.setBold(True)
    return font


def qimage_to_rgba(image):
    rgba = image.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombuffer("RGBA", (rgba.width(), rgba.height()), bytes(rgba.constBits()), "raw", "RGBA", 0, 1)


class LunaWindow(Window):
    def __init__(
        self,
        width,
        height,
        theme=LUNA_THEME,
        active=True,
        maximized=False,
        caption="",
        left="M",
        right="IAX",
        pressed=(),
    ):
        self.theme = Path(theme)
        self.width, self.height, self.active, self.caption = width, height, active, caption
        self.left, self.right, self.pressed, self.disabled = left, right, set(pressed), set()
        rc = configparser.ConfigParser()
        rc.optionxform = str
        rc.read(self.theme / "Chicago95Lunarc")
        self.layout = {key: int(value) for key, value in rc["Layout"].items()}
        self.general = rc["General"]
        self.maximized = maximized
        if maximized:
            self.layout.update({key: self.layout[key + "Maximized"] for key in MAXIMIZED_KEYS})

    def paint_frame(self, painter):
        renderer = QSvgRenderer(str(self.theme / "decoration.svg"))
        inactive = "" if self.active else "-inactive"
        if self.maximized:
            band = QRectF(0, 0, self.width, self.layout["TitleHeight"])
            paint_frame(painter, renderer, f"decoration-maximized{inactive}", band, borders=frozenset())
            return
        paint_frame(painter, renderer, f"decoration{inactive}", QRectF(0, 0, self.width, self.height))

    def paint_caption(self, painter):
        colour = self.general["ActiveTextColor" if self.active else "InactiveTextColor"].split(",")
        area = self.caption_rect()
        painter.setFont(title_font())
        if self.active:
            shadow = [int(part) for part in self.general["ActiveTextShadowColor"].split(",")]
            painter.setPen(QColor(*shadow[:3]))
            painter.drawText(area.translated(1, 1), Qt.AlignLeft | Qt.AlignVCenter, self.caption)
        painter.setPen(QColor(*(int(part) for part in colour[:3])))
        painter.drawText(area, Qt.AlignLeft | Qt.AlignVCenter, self.caption)

    def render_rgba(self):
        image = QImage(self.width, self.height, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        self.paint_frame(painter)
        self.paint_buttons(painter)
        self.paint_caption(painter)
        painter.end()
        return qimage_to_rgba(image)


def build_luna_theme(out):
    import subprocess

    subprocess.run([sys.executable, str(GENERATOR), "--out", str(out)], check=True, capture_output=True)
    return Path(out)


PIXELMATCH_THRESHOLD = 0.05


def unmasked_pixel_count(size, masks):
    kept = Image.new("1", size, 1)
    for box in masks:
        kept.paste(0, box)
    return kept.convert("L").histogram()[255]


def differing_fraction(reference, ours, masks, diff_path, blur=False):
    """The share of the unmasked pixels where ours differs from the reference by more than about 12 per channel
    (pixelmatch at threshold .05); blur compares both images after a 3x3 box blur, which averages away the
    references' dithering and our anti-aliasing. The diff images are written next to diff_path for review."""
    if blur:
        reference, ours = (image.filter(ImageFilter.BoxBlur(1)) for image in (reference, ours))
    count = differing_pixels(reference, ours, masks, diff_path, threshold=PIXELMATCH_THRESHOLD)
    return count / unmasked_pixel_count(reference.size, masks)
