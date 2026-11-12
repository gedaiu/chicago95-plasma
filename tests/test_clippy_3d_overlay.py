"""Regression tests for the low-resolution visual comparison, not artwork approval."""

import numpy as np
from overlay_clippy_3d import downsample, metrics, panels, timeline_index
from PIL import Image


def test_alpha_filter_ignores_hidden_color():
    clean = Image.new("RGBA", (744, 558))
    dirty = Image.new("RGBA", clean.size, (255, 0, 255, 0))
    for image in (clean, dirty):
        image.paste((32, 64, 96, 255), (100, 100, 300, 300))
    assert downsample(clean).tobytes() == downsample(dirty).tobytes()


def test_fixed_canvas_does_not_register_shifted_artwork():
    a = Image.new("RGBA", (744, 558))
    b = Image.new("RGBA", (744, 558))
    a.paste((255, 255, 255, 255), (60, 60, 180, 180))
    b.paste((255, 255, 255, 255), (120, 60, 240, 180))
    original, shifted = downsample(a), downsample(b)
    assert original.size == shifted.size == (124, 93)
    assert original.getbbox()[0] + 10 == shifted.getbbox()[0]
    assert metrics(original, shifted)["silhouette_iou"] < 0.5


def test_exact_match_and_difference():
    a = Image.new("RGBA", (124, 93), (10, 20, 30, 255))
    assert metrics(a, a)["exact_match"]
    assert metrics(a, a)["premultiplied_rgb_mae"] == 0
    assert not np.asarray(panels(a, a)[3]).any()
    b = a.copy()
    b.putpixel((20, 30), (20, 40, 60, 255))
    views = panels(a, b)
    assert views[2].getpixel((20, 30)) == (15, 30, 45)
    assert views[3].getpixel((20, 30)) == (40, 80, 120)
    assert not metrics(a, b)["exact_match"]


def test_original_timeline_boundaries_and_final_hold():
    durations = [100, 550, 100]
    assert [timeline_index(durations, t) for t in [0, 99, 100, 649, 650, 749, 750, 900]] == [0, 0, 1, 1, 2, 2, 2, 2]


def test_source_timeline_has_one_pointing_excursion_and_exact_durations():
    from clippy_3d_timeline import source_timeline
    from review_clippy_3d import original_frames

    for action, frames in source_timeline().items():
        refs = original_frames("Idle1_1" if action == "Blink" else action)
        if action == "Blink":
            refs = refs[:5]
        assert [f["duration_ms"] for f in frames] == [duration for _, duration in refs]
        assert [f["original_index"] for f in frames] == list(range(len(refs)))
        if action.startswith("Gesture"):
            values = [f["progress"] for f in frames]
            peak = values.index(max(values))
            assert values[0] == values[-1] == 0
            assert all(a <= b for a, b in zip(values[:peak], values[1 : peak + 1], strict=True))
            assert all(a >= b for a, b in zip(values[peak:-1], values[peak + 1 :], strict=True))


def test_foreground_similarity_does_not_reward_empty_canvas():
    a = Image.new("RGBA", (124, 93))
    b = a.copy()
    a.putpixel((10, 10), (255, 255, 255, 255))
    b.putpixel((10, 10), (0, 0, 0, 255))
    assert metrics(a, b)["foreground_color_similarity"] == 0


def test_empty_source_and_candidate_have_full_silhouette_overlap():
    blank = Image.new("RGBA", (124, 93))
    assert metrics(blank, blank)["silhouette_iou"] == 1
