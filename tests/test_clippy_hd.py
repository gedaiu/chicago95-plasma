"""HD blink artwork must not move or shimmer outside its two eye surfaces."""

import pytest
from clippy_hd import EYES, FRAME_SIZE, MASTER_SIZE, SEQUENCE, compose_eye_frame, frames, read_master
from conftest import REPO
from PIL import Image, ImageChops, ImageDraw
from PySide6.QtGui import QImage


def qimage_to_pil(image):
    rgba = image.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombytes("RGBA", (rgba.width(), rgba.height()), bytes(rgba.constBits()))


ART = REPO / "data/clippy/hd-reference"


@pytest.mark.parametrize("name", ["rest-pose-v1.png", "blink-half-source.png", "blink-closed-source.png"])
def test_hd_sources_have_real_alpha_and_matching_dimensions(name):
    image = read_master(ART / name)
    assert image.size() == MASTER_SIZE
    alpha = qimage_to_pil(image).getchannel("A")
    assert alpha.getextrema() == (0, 255)


@pytest.mark.parametrize("name", ["blink-half-source.png", "blink-closed-source.png"])
def test_blink_only_changes_eye_regions(name, tmp_path):
    base = read_master(ART / "rest-pose-v1.png")
    frame = compose_eye_frame(base, read_master(ART / name))
    original = qimage_to_pil(base)
    rendered = qimage_to_pil(frame)
    diff = ImageChops.difference(original, rendered).convert("RGB")
    diff.save(tmp_path / "difference.png")
    assert diff.getbbox() is not None
    # Rectangles include a 1px antialiasing allowance around the ellipse edges.
    for channel in ImageChops.difference(original, rendered).split():
        draw = ImageDraw.Draw(channel)
        for eye in EYES:
            draw.rectangle(
                (int(eye.left()) - 1, int(eye.top()) - 1, int(eye.right()) + 1, int(eye.bottom()) + 1), fill=0
            )
        assert channel.getbbox() is None, "Body/paper/alpha changed outside the eyes"


def test_hd_pack_is_four_times_original_resolution_and_loops_exactly():
    pack = frames(ART)
    assert len(pack) == 3
    assert all(frame.size() == FRAME_SIZE and frame.hasAlphaChannel() for frame in pack)
    assert SEQUENCE[0][0] == SEQUENCE[-1][0]
    assert all(duration > 0 and duration % 20 == 0 for _, duration in SEQUENCE)
    assert pack[0] != pack[1] and pack[1] != pack[2]


def test_mismatched_source_cannot_silently_shift_eye_alignment():
    with pytest.raises(ValueError, match="identical canvas"):
        compose_eye_frame(QImage(10, 10, QImage.Format_ARGB32), read_master(ART / "rest-pose-v1.png"))
