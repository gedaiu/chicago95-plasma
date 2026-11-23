"""Shared artwork checks for every shipped Windows theme, including inherited SVGs."""

import re
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from PIL import Image, ImageChops, ImageFilter, ImageStat
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]
ASSETS = sorted(
    path.relative_to(ROOT)
    for directory in ROOT.iterdir()
    if directory.is_dir() and not directory.name.startswith(".") and directory.name != "build"
    for path in directory.rglob("*.svg")
    if not path.is_symlink()
)


@pytest.mark.parametrize("asset", ASSETS, ids=str)
def test_svg_scales_as_vector_art(qt_app, asset):
    path = ROOT / asset
    for node in ET.parse(path).iter():
        assert node.tag.rsplit("}", 1)[-1] not in {"image", "feImage"}, asset
        # A repeated dot field belongs in a tile or reusable symbol. Likewise,
        # long stacks of single-row boxes conceal edges that should be paths.
        dots = [
            child for child in node if child.tag.endswith("}rect") and child.get("width") == child.get("height") == "1"
        ]
        assert len(dots) < 32, (asset, "individual dots")
        strips = re.findall(r"M[\d .,\-]+h\d+v1h-\d+z", node.get("d", ""), re.IGNORECASE)
        assert len(strips) < 32, (asset, "one-row subpaths")
    renderer = QSvgRenderer(str(path))
    assert renderer.isValid()
    width, height = renderer.defaultSize().toTuple()
    assert min(width, height) > 0
    size = width, height

    def sample(scale):
        target = QImage(*(round(n * scale) for n in size), QImage.Format_RGBA8888)
        target.fill(Qt.transparent)
        painter = QPainter(target)
        renderer.render(painter)
        painter.end()
        rgba = Image.frombytes("RGBA", (target.width(), target.height()), bytes(target.constBits()))
        # Compare premultiplied colours and coverage, including translucent bevels.
        premultiplied = rgba.convert("RGBa").resize(size, Image.Resampling.LANCZOS)
        return Image.frombytes("RGBA", size, premultiplied.tobytes())

    native = sample(1)
    for scale in (1.5, 2):
        larger = sample(scale)
        # A one-pixel low-pass tolerates sampling phase at thin, high-contrast edges.
        delta = ImageChops.difference(native.filter(ImageFilter.BoxBlur(1)), larger.filter(ImageFilter.BoxBlur(1)))
        assert max(ImageStat.Stat(delta).mean) < 12, (asset, scale)


def radio_artwork():
    for path in ASSETS:
        if path.stem.startswith(("radio", "dot-")) and path.stem != "radiobutton":
            yield path, ""
        elif path.name == "radiobutton.svg":
            for element in ("normal", "hover", "symbol"):
                yield path, element
        elif path.name == "Chicago95Luna.svg" and "kvantum" in path.parts:
            for node in ET.parse(ROOT / path).iter():
                if node.get("id", "").startswith("radio-"):
                    yield path, node.get("id")


@pytest.mark.parametrize(("asset", "element"), list(radio_artwork()))
def test_radio_art_composites_its_rim_and_centre_on_the_backdrop(qt_app, asset, element):
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor

    renderer = QSvgRenderer(str(ROOT / asset))
    if element:
        assert renderer.elementExists(element)
    for side in (13, 26):
        for matte in ("#35254e", "#e4f5c1"):
            image = QImage(side, side, QImage.Format_RGB32)
            image.fill(QColor(matte))
            painter = QPainter(image)
            if element:
                renderer.render(painter, element, QRectF(0, 0, side, side))
            else:
                renderer.render(painter)
            painter.end()
            assert all(image.pixelColor(x, y).name() == matte for x in (0, side - 1) for y in (0, side - 1))
            hollow = asset.stem.startswith("radio-face-disabled") or element == "radio-disabled"
            assert (image.pixelColor(side // 2, side // 2).name() == matte) == hollow
            if hollow:
                assert image.pixelColor(side // 2, 0).name() != matte
