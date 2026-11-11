#!/usr/bin/env python3
"""Renders every Windows XP flag and wordmark picture from windows-xp-logo.svg.

usage: python3 luna/images/render_logo.py
"""

import copy
import math
import os
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from PIL import Image, ImageFilter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QByteArray, QRectF  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
IMAGES = Path(__file__).resolve().parent
REPO = IMAGES.parents[1]
SOURCE_SVG = IMAGES / "windows-xp-logo.svg"
FLAG_SVG = IMAGES / "windows-xp-flag.svg"
LIGHT_SVG = IMAGES / "windows-xp-logo-light.svg"
SHADOW_FILL = "#D9DADB"
LIGHT_TEXT_FILL = "#FFFFFF"
SUPERSAMPLE = 4
MEASURE_SCALE = 8
ALPHA_THRESHOLD = 1
START_IMAGES = REPO / "luna/plasmoids/org.chicago95.start/contents/images"
FLAG_PNGS = {
    REPO / "plasmoids/org.chicago95.start/contents/images/logo-xp-16.png": ((16, 16), (16, 16)),
    START_IMAGES / "logo-flag-xp.png": ((24, 22), (21, 20)),
    START_IMAGES / "logo-flag-xp@2x.png": ((48, 44), (42, 40)),
    REPO / "luna/lib/images/windows-xp-flag-dialog.png": ((38, 32), (38, 32)),
    REPO / "luna/lib/images/windows-xp-flag-dialog@2x.png": ((76, 64), (76, 64)),
}
PLYMOUTH_WORDMARK_WIDTH = 244

ElementTree.register_namespace("", SVG_NAMESPACE)
ElementTree.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def tag_name(element):
    return element.tag.rsplit("}", 1)[-1]


def is_shadow(element):
    return element.get("fill") == SHADOW_FILL


def is_text_start(element):
    return tag_name(element) == "polyline"


def split_parts(root):
    children = list(root.find(f"{{{SVG_NAMESPACE}}}g"))
    text_start = next(index for index, child in enumerate(children) if is_text_start(child))
    defs = [child for child in children if tag_name(child) == "linearGradient"]
    drawn = [child for child in children if tag_name(child) != "linearGradient"]
    drawn_text_start = drawn.index(children[text_start])
    shadow = [child for child in drawn[:drawn_text_start] if is_shadow(child)]
    flag = [child for child in drawn[:drawn_text_start] if not is_shadow(child)]
    return defs, shadow, flag, drawn[drawn_text_start:]


def document_with(root, defs, drawn, view_box=None):
    document = copy.deepcopy(root)
    group = document.find(f"{{{SVG_NAMESPACE}}}g")
    group[:] = defs + drawn
    if view_box is not None:
        x, y, width, height = view_box
        document.set("viewBox", f"{x:g} {y:g} {width:g} {height:g}")
        document.set("width", f"{width:g}")
        document.set("height", f"{height:g}")
    return document


def whitened(text_parts):
    lit = copy.deepcopy(text_parts)
    for part in lit:
        part.attrib.setdefault("fill", LIGHT_TEXT_FILL)
    return lit


def svg_bytes(document):
    return ElementTree.tostring(document, encoding="utf-8", xml_declaration=True)


def render_to_image(svg_data, width, height, target=None):
    renderer = QSvgRenderer(QByteArray(svg_data))
    image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter, target or QRectF(0, 0, width, height))
    painter.end()
    return qimage_to_pil(image)


def qimage_to_pil(image):
    straight = image.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombytes("RGBA", (straight.width(), straight.height()), bytes(straight.constBits()))


def measured_box(root, flag_parts, defs):
    width, height = (math.ceil(float(root.get(side).replace("px", ""))) + 1 for side in ("width", "height"))
    flag_only = document_with(root, defs, flag_parts)
    alpha = render_to_image(svg_bytes(flag_only), width * MEASURE_SCALE, height * MEASURE_SCALE).getchannel("A")
    left, top, right, bottom = alpha.point(lambda value: 255 if value >= ALPHA_THRESHOLD else 0).getbbox()
    return tuple(value / MEASURE_SCALE for value in (left, top, right, bottom))


def enclosing_view_box(box):
    left, top, right, bottom = box
    x, y = math.floor(left * 2) / 2, math.floor(top * 2) / 2
    return (x, y, math.ceil(right * 2) / 2 - x, math.ceil(bottom * 2) / 2 - y)


def write_svgs():
    root = ElementTree.parse(SOURCE_SVG).getroot()
    defs, _, flag_parts, text_parts = split_parts(root)
    flag_box = measured_box(root, flag_parts, defs)
    view_box = enclosing_view_box(flag_box)
    FLAG_SVG.write_bytes(svg_bytes(document_with(root, defs, flag_parts, view_box)))
    LIGHT_SVG.write_bytes(svg_bytes(document_with(root, defs, flag_parts + whitened(text_parts))))
    return flag_box, view_box


def fitted_rectangle(source_size, canvas_size):
    scale = min(canvas_size[0] / source_size[0], canvas_size[1] / source_size[1])
    width, height = source_size[0] * scale, source_size[1] * scale
    return QRectF((canvas_size[0] - width) / 2, (canvas_size[1] - height) / 2, width, height)


def view_box_size(svg_path):
    renderer = QSvgRenderer(str(svg_path))
    return renderer.viewBoxF().width(), renderer.viewBoxF().height()


def render_fitted(svg_path, canvas_size, content_size=None):
    content_size = content_size or canvas_size
    big_size = tuple(side * SUPERSAMPLE for side in canvas_size)
    content = fitted_rectangle(view_box_size(svg_path), tuple(side * SUPERSAMPLE for side in content_size))
    margin = tuple((canvas - used) * SUPERSAMPLE / 2 for canvas, used in zip(canvas_size, content_size, strict=True))
    target = content.translated(*margin)
    big = render_to_image(svg_path.read_bytes(), *big_size, target)
    return big.resize(canvas_size, Image.LANCZOS)


def render_flag(canvas_size, content_size=None):
    return render_fitted(FLAG_SVG, canvas_size, content_size)


def render_wordmark(width):
    source_width, source_height = view_box_size(LIGHT_SVG)
    return render_fitted(LIGHT_SVG, (width, round(width * source_height / source_width)))


# The Start button's flag shadow: the flag's outline, moved a quarter pixel right and 2 down, blurred and
# darkened, on a canvas
# FLAG_SHADOW_PADDING larger on every side than the 20x18 flag, drawn at FLAG_SHADOW_SCALE for the 2x screens.
FLAG_SHADOW_PNG = START_IMAGES / "logo-flag-xp-shadow.png"
FLAG_SHADOW_SIZE = (20, 18)
FLAG_SHADOW_PADDING = 4
FLAG_SHADOW_OFFSET = (0.25, 2)
FLAG_SHADOW_BLUR = 0.5
FLAG_SHADOW_COLOUR = (11, 58, 11)
FLAG_SHADOW_OPACITY = 1.0
FLAG_SHADOW_SCALE = 4


def render_flag_shadow():
    scale, padding = FLAG_SHADOW_SCALE, FLAG_SHADOW_PADDING
    width, height = (side * scale for side in FLAG_SHADOW_SIZE)
    canvas = (width + 2 * padding * scale, height + 2 * padding * scale)
    left, top = (round((padding + offset) * scale) for offset in FLAG_SHADOW_OFFSET)
    alpha = render_fitted(FLAG_SVG, (width, height)).getchannel("A")
    placed = Image.new("L", canvas, 0)
    placed.paste(alpha, (left, top))
    blurred = placed.filter(ImageFilter.GaussianBlur(FLAG_SHADOW_BLUR * scale))
    shadow = Image.new("RGBA", canvas, FLAG_SHADOW_COLOUR + (0,))
    shadow.putalpha(blurred.point(lambda value: round(value * FLAG_SHADOW_OPACITY)))
    return shadow


def write_flag_pngs():
    for path, (canvas_size, content_size) in FLAG_PNGS.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        render_flag(canvas_size, content_size).save(path)
    render_flag_shadow().save(FLAG_SHADOW_PNG)


def main():
    QGuiApplication.instance() or QGuiApplication([])
    flag_box, view_box = write_svgs()
    write_flag_pngs()
    print(f"flag box {flag_box}, view box {view_box}")


if __name__ == "__main__":
    main()
