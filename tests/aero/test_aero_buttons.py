"""The vector caption button faces against the aero.msstyles states they were fitted to."""

import importlib.util

import pytest
from aero_sprites import requires_sprites
from conftest import REPO
from fit_aero_stops import FACES, STATES, state_image
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
def test_vector_face_matches_its_sprite_over_glass_within_six_levels(qt_app, face, window, state):
    sprite = state_image(FACES[face][window == "inactive"], state)
    fitted = generator.stops.FACES[face][window][STATES[state]]
    ours = over_glass(rendered(generator.face_svg(fitted), sprite.size))
    theirs = over_glass(sprite)
    differences = [
        abs(a - b)
        for p, q in zip(ours.get_flattened_data(), theirs.get_flattened_data(), strict=True)
        for a, b in zip(p, q, strict=True)
    ]

    assert sum(differences) / len(differences) < 6
