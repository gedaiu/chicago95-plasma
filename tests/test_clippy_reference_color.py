"""Reference filtering must not alter shape or import hidden-background colors."""

import numpy as np
from clippy_reference_color import smooth_reference_color
from PIL import Image


def test_preserves_alpha_exactly():
    rng = np.random.default_rng(18)
    source = rng.integers(0, 256, size=(17, 21, 4), dtype=np.uint8)
    result = np.asarray(smooth_reference_color(Image.fromarray(source)))
    np.testing.assert_array_equal(result[:, :, 3], source[:, :, 3])


def test_hidden_rgb_cannot_contaminate_character():
    first = np.zeros((9, 9, 4), dtype=np.uint8)
    first[3:6, 3:6] = (70, 140, 210, 255)
    second = first.copy()
    second[second[:, :, 3] == 0, :3] = (255, 0, 255)
    a = np.asarray(smooth_reference_color(Image.fromarray(first)))
    b = np.asarray(smooth_reference_color(Image.fromarray(second)))
    np.testing.assert_array_equal(a, b)
    np.testing.assert_array_equal(a[4, 4], (70, 140, 210, 255))


def test_constant_color_survives_partial_alpha_edges():
    a = np.empty((9, 9, 4), dtype=np.uint8)
    a[:, :, :3] = (19, 71, 169)
    a[:, :, 3] = np.arange(9)[None, :] * 25
    b = np.asarray(smooth_reference_color(Image.fromarray(a)))
    np.testing.assert_array_equal(b[:, :, :3], a[:, :, :3])


def test_approved_reference_passes_without_erasing_raw_failure():
    from review_clippy_3d import original_frames
    from validate_clippy_fidelity import spatial

    original = original_frames("RestPose")[0][0]
    candidate = smooth_reference_color(original)
    result = spatial(original, candidate, smooth_color=True)
    assert result["pass"]
    assert result["silhouette_iou"] == 1
    assert result["regions"]["whole_foreground"]["raw_matching_pixel_fraction"] < 0.98


def test_approved_color_mode_still_rejects_shift_and_bad_timing():
    from review_clippy_3d import original_frames
    from validate_clippy_fidelity import spatial, validate_sequence

    refs = original_frames("GestureLeft")
    images = [smooth_reference_color(im) for im, _ in refs]
    durations = [d for _, d in refs]
    assert validate_sequence(refs, images, durations, smooth_color=True)["pass"]
    shifted = Image.new("RGBA", images[0].size)
    shifted.paste(images[0], (3, 0))
    assert not spatial(refs[0][0], shifted, smooth_color=True)["pass"]
    durations[2] += 10
    result = validate_sequence(refs, images, durations, smooth_color=True)
    assert all(row["pass"] for row in result["frames"])
    assert not result["timing_pass"] and not result["pass"]
