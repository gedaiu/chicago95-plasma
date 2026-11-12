"""Calibrate diagnostic measurements with known native-pixel displacements."""

import hashlib
import json
from pathlib import Path

import pytest
from clippy_geometry_audit import PUPIL_WINDOWS, audit_frame, contour_error, detect_pupil
from PIL import Image, ImageDraw
from review_clippy_3d import original_frames


def pupil_image(dx=0, dy=0):
    image = Image.new("RGBA", (124, 93))
    draw = ImageDraw.Draw(image)
    draw.ellipse((39 + dx, 23 + dy, 53 + dx, 37 + dy), fill="white")
    draw.rectangle((44 + dx, 28 + dy, 48 + dx, 32 + dy), fill="black")
    return image


def test_known_pupil_displacement_is_measured_in_pixels():
    a = detect_pupil(pupil_image(), PUPIL_WINDOWS["left_pupil"])
    b = detect_pupil(pupil_image(3, 2), PUPIL_WINDOWS["left_pupil"])
    assert a["status"] == b["status"] == "detected"
    assert b["point"][0] - a["point"][0] == pytest.approx(3)
    assert b["point"][1] - a["point"][1] == pytest.approx(2)


def test_missing_or_ambiguous_pupils_are_not_matches():
    assert detect_pupil(Image.new("RGBA", (124, 93)), PUPIL_WINDOWS["left_pupil"])["status"] == "missing"
    image = Image.new("RGBA", (124, 93), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((38, 28, 41, 31), fill="black")
    draw.rectangle((49, 28, 52, 31), fill="black")
    assert detect_pupil(image, PUPIL_WINDOWS["left_pupil"])["status"] == "ambiguous"


def test_paper_direction_and_distance_are_exact():
    original = [[90, y] for y in range(60, 80)]
    displaced = [[93, y] for y in range(60, 80)]
    result = contour_error(original, displaced)
    assert result["mean_offset_xy"] == [3, 0]
    assert result["max_error_px"] == result["p95_error_px"] == 3
    assert not result["pass"]
    assert contour_error(original, original)["pass"]
    assert not contour_error(original, [None] * len(original))["pass"]


def test_frozen_reference_annotations_pass_original_images():
    path = Path(__file__).parent / "fixtures/clippy/reference-landmarks.json"
    fixture = json.loads(path.read_text())
    for key, annotation in fixture["frames"].items():
        action, index = key.split("/")
        image = original_frames("Idle1_1" if action == "Blink" else action)[int(index)][0]
        assert hashlib.sha256(image.tobytes()).hexdigest() == annotation["rgba_sha256"]
        closed = all(item["point"] is None for item in annotation["landmarks"].values())
        result, _, _ = audit_frame(image, image, closed, annotation)
        assert result["pass"], (key, result["landmarks"])


def test_reference_prior_does_not_realign_bad_pupil():
    original = pupil_image()
    changed = pupil_image(3, 0)
    annotation = {"landmarks": {"left_pupil": {"point": [46, 30]}, "right_pupil": {"point": [65, 30]}}}
    result, _, _ = audit_frame(original, changed, False, annotation)
    assert result["landmarks"]["left_pupil"]["error_px"] == pytest.approx(3)
    assert not result["landmarks"]["left_pupil"]["pass"]


def test_real_image_paper_edge_displacement_is_measured():
    import numpy as np
    from clippy_geometry_audit import contours

    original = original_frames("RestPose")[0][0]
    broken = original.copy()
    alpha = np.array(original.getchannel("A"))
    for y in range(58, 87):
        right = int(np.flatnonzero(alpha[y] >= 128).max())
        for x in range(right + 1, right + 4):
            broken.putpixel((x, y), (204, 204, 153, 255))
    result = contour_error(contours(original)["paper_right"], contours(broken)["paper_right"])
    assert result["mean_offset_xy"] == [3, 0]
    assert result["max_error_px"] == 3
    assert not result["pass"]


def test_changed_reference_cannot_silently_redefine_target():
    from clippy_geometry_audit import measure_reference

    original = original_frames("RestPose")[0][0]
    changed = original.copy()
    changed.putpixel((0, 0), (255, 0, 0, 255))
    with pytest.raises(ValueError, match="Reference frame changed"):
        measure_reference("RestPose", 0, changed, original)
