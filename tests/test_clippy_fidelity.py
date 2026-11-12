"""Mutation tests: prove fidelity checks reject recognizable rendering failures."""

import numpy as np
from overlay_clippy_3d import metrics
from PIL import Image, ImageDraw
from review_clippy_3d import original_frames
from validate_clippy_fidelity import motion, spatial, validate_sequence


def test_all_original_sequences_pass_identity_comparison():
    for action in ("RestPose", "Idle1_1", "GestureLeft", "GestureRight"):
        refs = original_frames(action)
        if action == "Idle1_1":
            refs = refs[:5]
        assert validate_sequence(refs, [im for im, _ in refs], [duration for _, duration in refs])["pass"]


def test_bad_eye_cannot_hide_in_good_paper_score():
    original = original_frames("RestPose")[0][0]
    broken = original.copy()
    ImageDraw.Draw(broken).rectangle((42, 24, 52, 32), fill=(240, 240, 0, 255))
    assert metrics(original, broken)["foreground_color_similarity"] > 0.95
    result = spatial(original, broken)
    assert not result["regions"]["left_eye"]["pass"]
    assert not result["pass"]


def test_paper_boundary_warp_is_rejected():
    original = original_frames("RestPose")[0][0]
    broken = original.copy()
    ImageDraw.Draw(broken).rectangle((98, 40, 115, 65), fill=(0, 0, 0, 0))
    result = spatial(original, broken)
    assert not result["regions"]["paper_right_edge"]["pass"]
    assert not result["boundary_pass"]


def test_translated_frame_is_not_registered_back_into_place():
    original = original_frames("RestPose")[0][0]
    shifted = Image.new("RGBA", original.size)
    shifted.paste(original, (3, 0))
    assert not spatial(original, shifted)["pass"]


def test_small_wrong_tip_is_rejected_locally():
    original = original_frames("GestureRight")[6][0]
    broken = original.copy()
    ImageDraw.Draw(broken).rectangle((24, 41, 37, 47), fill=(0, 0, 0, 0))
    assert not spatial(original, broken)["regions"]["left_tip"]["pass"]


def test_frozen_animation_is_rejected_from_actual_pixels():
    refs = original_frames("GestureRight")
    images = [refs[0][0]] * len(refs)
    result = validate_sequence(refs, images, [d for _, d in refs])
    assert result["timing_pass"]
    assert not result["pass"]
    assert any(row["motion"] and not row["motion"]["pass"] for row in result["frames"])


def test_reverse_motion_is_rejected():
    refs = original_frames("GestureRight")
    a, b = refs[1][0], refs[2][0]
    assert not motion(a, b, b, a)["pass"]


def test_double_gesture_and_same_length_extra_excursion_are_rejected():
    refs = original_frames("GestureRight")
    images = [im for im, _ in refs]
    durations = [d for _, d in refs]
    assert not validate_sequence(refs, images * 2, durations * 2)["timing_pass"]
    # Spoof correct metadata and count: actual pixels must still reveal the extra excursion.
    broken = images.copy()
    broken[7:10] = [images[0], images[6], images[0]]
    result = validate_sequence(refs, broken, durations)
    assert result["timing_pass"] and not result["pass"]
    assert not result["frames"][7]["motion"]["pass"]


def test_wrong_duration_fails_even_when_every_pixel_matches():
    refs = original_frames("GestureLeft")
    durations = [d for _, d in refs]
    durations[5] += 10
    result = validate_sequence(refs, [im for im, _ in refs], durations)
    assert all(row["pass"] for row in result["frames"])
    assert not result["timing_pass"] and not result["pass"]


def test_color_error_and_missing_frame_are_rejected():
    refs = original_frames("RestPose")
    original = refs[0][0]
    array = np.array(original)
    array[:, :, :3] = np.clip(array[:, :, :3].astype(int) + 30, 0, 255).astype("uint8")
    assert not spatial(original, Image.fromarray(array))["pass"]
    assert not validate_sequence(refs, [], [])["pass"]


def test_hidden_rgb_is_ignored_but_alpha_loss_is_not():
    original = original_frames("RestPose")[0][0]
    array = np.array(original)
    array[array[:, :, 3] == 0, :3] = (255, 0, 255)
    assert spatial(original, Image.fromarray(array))["pass"]
    array[:, :, 3] = 255
    assert not spatial(original, Image.fromarray(array))["pass"]


def test_new_98_percent_gate_rejects_a_97_percent_color_match():
    from clippy_acceptance import MATCH_THRESHOLD

    reference = Image.new("RGBA", (124, 93), (100, 100, 100, 255))
    candidate = Image.new("RGBA", (124, 93), (108, 108, 108, 255))
    score = metrics(reference, candidate)["foreground_color_similarity"]
    assert 0.95 < score < MATCH_THRESHOLD
    assert not spatial(reference, candidate)["pass"]
    assert spatial(reference, reference)["pass"]
