"""Progress geometry, readable labels and fill clipping on real Qt widgets."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QProgressBar
from reference import qimage_to_pil


@pytest.fixture
def progress(qt_app):
    import chicago95luna

    bar = QProgressBar()
    style = chicago95luna.LunaStyle()
    bar.setStyle(style)
    bar.setPalette(chicago95luna.luna_palette())
    bar.setFont(chicago95luna.luna_font())
    yield bar
    bar.close()


@pytest.mark.parametrize("orientation", (Qt.Horizontal, Qt.Vertical))
@pytest.mark.parametrize("value", (0, 1, 55, 100))
@pytest.mark.parametrize("enabled", (True, False))
def test_progress_has_white_inset_and_black_text(progress, orientation, value, enabled):
    bar = progress
    bar.setOrientation(orientation)
    bar.setEnabled(enabled)
    bar.setValue(value)
    bar.resize(260, 17) if orientation == Qt.Horizontal else bar.resize(17, 160)
    bar.setTextVisible(False)
    plain = qimage_to_pil(bar.grab().toImage())
    bar.setTextVisible(True)
    labelled = qimage_to_pil(bar.grab().toImage())
    assert any(max(pixel) < 50 for pixel in labelled.get_flattened_data())
    assert plain.tobytes() != labelled.tobytes()
    # The full white ring must survive even at 100%, including disabled/vertical bars.
    for x in range(2, plain.width - 2):
        assert plain.getpixel((x, 1)) == plain.getpixel((x, plain.height - 2)) == (255, 255, 255)
    for y in range(2, plain.height - 2):
        assert plain.getpixel((1, y)) == plain.getpixel((plain.width - 2, y)) == (255, 255, 255)
    greens = [
        (x, y) for y in range(plain.height) for x in range(plain.width) if plain.getpixel((x, y)) == (57, 230, 58)
    ]
    assert bool(greens) == (value > 0)
    assert all(2 <= x < plain.width - 2 and 2 <= y < plain.height - 2 for x, y in greens)


@pytest.mark.parametrize("orientation", (Qt.Horizontal, Qt.Vertical))
@pytest.mark.parametrize("text_visible", (True, False))
def test_progress_default_thickness_is_seventeen_pixels(progress, orientation, text_visible):
    progress.setOrientation(orientation)
    progress.setTextVisible(text_visible)
    hint = progress.sizeHint()
    assert (hint.height() if orientation == Qt.Horizontal else hint.width()) == 17
