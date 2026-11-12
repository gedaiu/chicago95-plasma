"""Transparent sprite edges must not retain visible background haze."""

import numpy as np
from audit_clippy_hd_edges import edge_metrics
from clippy_hd_matte import clean_matte
from conftest import REPO
from PIL import Image, ImageDraw
from PySide6.QtGui import QColor, QImage


def test_edge_audit_detects_faint_residue_and_allows_contour_antialiasing(tmp_path):
    image = Image.new("RGBA", (32, 32))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 23, 23), fill=(200, 200, 200, 255))
    draw.line((7, 8, 7, 23), fill=(200, 200, 200, 64))
    path = tmp_path / "sprite.png"
    image.save(path)
    assert edge_metrics(path)["stray_pixels_above_alpha_8"] == 0
    draw.point((2, 2), fill=(255, 255, 0, 32))
    image.save(path)
    assert edge_metrics(path)["stray_pixels_above_alpha_8"] == 1


def test_shipped_hd_frames_have_no_visible_residue_outside_their_contours():
    failures = {}
    for path in sorted((REPO / "data/clippy/hd-animations").glob("*.png")):
        metrics = edge_metrics(path)
        if metrics["stray_pixels_above_alpha_8"] or metrics["transparent_pixels_with_rgb_residue"]:
            failures[path.name] = metrics
    assert not failures, failures


def test_cleanup_preserves_rgb_opaque_pixels_and_contour_antialiasing():
    image = QImage(32, 32, QImage.Format_RGBA8888)
    image.fill(QColor(120, 70, 15, 0))
    for y in range(8, 24):
        for x in range(8, 24):
            image.setPixelColor(x, y, QColor(200, 190, 180, 255))
        image.setPixelColor(7, y, QColor(200, 190, 180, 64))
    image.setPixelColor(2, 2, QColor(255, 255, 0, 32))
    cleaned = clean_matte(image)
    before = np.frombuffer(image.constBits(), dtype=np.uint8).reshape(32, 32, 4)
    after = np.frombuffer(cleaned.constBits(), dtype=np.uint8).reshape(32, 32, 4)
    visible = after[:, :, 3] > 0
    assert np.array_equal(before[:, :, :3][visible], after[:, :, :3][visible]), "Cleanup redrew visible RGB artwork"
    assert not np.any(after[~visible]), "Invisible RGB residue can leak into previews"
    assert np.array_equal(before[before[:, :, 3] >= 128], after[before[:, :, 3] >= 128])
    assert cleaned.pixelColor(7, 12).alpha() == 64, "Antialiased contour became a hard cutout"
    assert cleaned.pixelColor(2, 2).alpha() == 0
    assert clean_matte(cleaned) == cleaned, "Rebuilding must not progressively erode the sprite"
