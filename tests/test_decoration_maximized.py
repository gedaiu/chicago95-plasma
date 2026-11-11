"""A maximized window's title bar: KWin draws it from the decoration's centre piece alone (no borders), so the
decoration needs "decoration-maximized" and "decoration-maximized-inactive" pieces whose centre is the title band
itself, in the active and the inactive colours; without them every maximized title came out face grey."""

import pytest
from aurorae_model import build_theme
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


@pytest.fixture(scope="module")
def decoration(tmp_path_factory, qt_app):
    return build_theme(tmp_path_factory.mktemp("aurorae"), "1998") / "decoration.svg"


def rendered_row(svg_path, element, width=300, height=18, row=9):
    renderer = QSvgRenderer(str(svg_path))
    image = QImage(width, height, QImage.Format_RGB32)
    image.fill(0xFF00FF00)
    painter = QPainter(image)
    renderer.render(painter, element, QRectF(0, 0, width, height))
    painter.end()
    return [image.pixelColor(x, row).name() for x in range(width)]


def test_the_maximized_pieces_exist_for_both_states(decoration):
    renderer = QSvgRenderer(str(decoration))

    assert [
        renderer.elementExists(f"decoration-maximized{suffix}-{part}")
        for suffix in ("", "-inactive")
        for part in ("center", "top", "topleft", "bottomright")
    ] == [True] * 8


def test_a_maximized_active_title_is_the_same_band_as_the_active_top_edge(decoration):
    centre = rendered_row(decoration, "decoration-maximized-center")

    assert (centre == rendered_row(decoration, "decoration-top", row=12), centre[0], centre[-1]) == (
        True,
        "#000080",
        "#1084d0",
    )


def test_a_maximized_inactive_title_is_the_same_band_as_the_inactive_top_edge(decoration):
    centre = rendered_row(decoration, "decoration-maximized-inactive-center")

    assert (centre == rendered_row(decoration, "decoration-inactive-top", row=12), centre[0], centre[-1]) == (
        True,
        "#808080",
        "#c0c0c0",
    )
