"""The vector caption button faces against the aero.msstyles states they were fitted to."""

import importlib.util

import pytest
from aero_sprites import requires_sprites
from conftest import REPO
from fit_aero_stops import FACES, STATES, glyph_image, state_image
from PIL import Image

spec = importlib.util.spec_from_file_location("make_aero_aurorae", REPO / "aero/aurorae/make_aero_aurorae.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
GLASS = (82, 139, 185, 255)


def rendered(svg, size):
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    image = QImage(*size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    rgba = image.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombuffer("RGBA", size, bytes(rgba.constBits()), "raw", "RGBA", rgba.bytesPerLine(), 1)


def over_glass(image):
    base = Image.new("RGBA", image.size, GLASS)
    base.alpha_composite(image)
    return base.convert("RGB")


@requires_sprites
@pytest.mark.parametrize("state", range(len(STATES)))
@pytest.mark.parametrize("window", ["active", "inactive"])
@pytest.mark.parametrize("face", sorted(FACES))
def test_vector_face_matches_its_sprite_over_glass_within_six_levels(qt_app, face, window, state, exact_original):
    sprite = state_image(FACES[face][window == "inactive"], state)
    fitted = generator.stops.FACES[face][window][STATES[state]]
    ours = over_glass(rendered(generator.face_svg(fitted), sprite.size))
    theirs = over_glass(sprite)
    exact_original(theirs, ours)
    differences = [
        abs(a - b)
        for p, q in zip(ours.get_flattened_data(), theirs.get_flattened_data(), strict=True)
        for a, b in zip(p, q, strict=True)
    ]

    assert sum(differences) / len(differences) < 6


@requires_sprites
@pytest.mark.parametrize("state", range(len(STATES)))
@pytest.mark.parametrize("glyph", ["close", "minimize", "maximize", "restore"])
def test_vector_glyph_matches_its_96_dpi_sprite_over_glass_within_twelve_levels(qt_app, glyph, state, exact_original):
    sprite = glyph_image(glyph, state)
    ours = over_glass(rendered(generator.glyph_svg(glyph, generator.stops.GLYPHS[glyph][STATES[state]]), sprite.size))
    theirs = over_glass(sprite)
    exact_original(theirs, ours)
    differences = [
        abs(a - b)
        for p, q in zip(ours.get_flattened_data(), theirs.get_flattened_data(), strict=True)
        for a, b in zip(p, q, strict=True)
    ]

    assert sum(differences) / len(differences) < 12


@pytest.mark.parametrize(
    ("kind", "left", "width"), [("minimize", 0, 45), ("maximize", 45, 40), ("close", 85, 75), ("restore", 0, 40)]
)
def test_large_caption_glyph_matches_144_dpi_guest(qt_app, kind, left, width):
    import numpy as np

    native = Image.open(REPO / "tests/references/win7-sp1-144dpi-caption.png").convert("RGB")
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from reference import qimage_to_pil

    asset = REPO / f"aero/aurorae/theme/{kind}-large.svg"
    renderer = QSvgRenderer(str(asset))
    assert renderer.elementExists("active-center")
    pixels = QImage(width, 30, QImage.Format_RGB32)
    pixels.fill(Qt.black)
    painter = QPainter(pixels)
    renderer.render(painter, "active-center", QRectF(0, 0, width, 30))
    painter.end()
    actual = qimage_to_pil(pixels)
    expected = native.crop((left, 0, left + width, 30))

    if kind == "restore":
        expected = Image.open(REPO / "tests/references/win7-sp1-144dpi-restore.png").convert("RGB")
        # The maximized caption clips the topmost row at the screen edge.
        actual = actual.crop((0, 1, width, 30))

    # Isolate the bright glyph body from the bevel and translucent glass.
    def body(im):
        return np.asarray(im)[4:25, 6:-6].min(axis=2) > 198

    a, b = body(actual), body(expected)
    assert (a & b).sum() / (a | b).sum() > 0.82
