"""Show layout stays anchored to the actual original atlas, not a guessed zoom."""

import json

import pytest
from clippy_show import SHOW_BOUNDS, bounds_error, layout
from PIL import Image
from review_clippy_3d import original_frames


def test_show_layout_uses_the_original_frames_and_keeps_the_blank_start():
    frames = original_frames("Show")
    bounds = tuple(
        image.getchannel("A").point(lambda alpha: 255 if alpha >= 128 else 0).getbbox() for image, _ in frames
    )
    assert SHOW_BOUNDS == bounds
    assert layout(0) is None
    assert [duration for _, duration in frames] == [10] * 5
    assert layout(4) == (1, 64, 48)


@pytest.mark.parametrize("index", [1, 2, 3, 4])
def test_uniform_zoom_preserves_source_centres_and_bounds_within_one_native_pixel(index):
    scale, x, y = layout(index)
    full = SHOW_BOUNDS[-1]
    width, height = (full[2] - full[0]) * scale, (full[3] - full[1]) * scale
    projected = (x - width / 2, y - height / 2, x + width / 2, y + height / 2)
    assert max(abs(a - b) for a, b in zip(projected, SHOW_BOUNDS[index], strict=True)) <= 1


def test_visual_gate_rejects_the_old_small_bottom_anchored_show_frame():
    reference = original_frames("Show")[1][0]
    broken = Image.new("RGBA", reference.size)
    broken.paste((200, 200, 150, 255), (53, 68, 69, 82))
    assert bounds_error(reference, broken) == 30
    assert bounds_error(reference, reference) == 0
    assert bounds_error(reference, Image.new("RGBA", reference.size)) == float("inf")


def test_visual_gate_requires_a_blank_first_show_frame():
    blank = original_frames("Show")[0][0]
    visible = blank.copy()
    visible.putpixel((60, 48), (255, 255, 255, 255))
    assert bounds_error(blank, blank) == 0
    assert bounds_error(blank, visible) == float("inf")


def test_hide_is_the_exact_source_reverse_of_show_including_transparency_and_timing():
    show = original_frames("Show")
    hide = original_frames("Hide")
    assert len(show) == len(hide) == 5
    for (a, duration_a), (b, duration_b) in zip(show, reversed(hide), strict=True):
        assert a.tobytes() == b.tobytes()
        assert duration_a == duration_b == 10
    assert hide[-1][0].getchannel("A").getbbox() is None


@pytest.mark.parametrize("action", ["Show", "Hide"])
def test_library_review_rejects_the_old_transition_layout(tmp_path, monkeypatch, action):
    import review_clippy_library as review
    from clippy_all_catalog import catalog

    source = {action: catalog()[action]}
    monkeypatch.setattr(review, "catalog", lambda: source)
    items = []
    broken_index = 1 if action == "Show" else 4
    for index, (reference, duration) in enumerate(original_frames(action)):
        image = reference
        if index == broken_index:
            image = Image.new("RGBA", image.size)
            image.paste((200, 200, 150, 255), (53, 68, 69, 82))
        filename = f"{index}.png"
        image.save(tmp_path / filename)
        items.append(
            {
                "file": filename,
                "source_index": index,
                "duration_ms": duration,
                "source": source[action]["frames"][index],
            }
        )
    (tmp_path / "manifest.json").write_text(json.dumps({"pixel_size": [124, 93], "sequences": {action: items}}))
    (tmp_path / "bake-verification.json").write_text(json.dumps({"poses": 5, "failures": []}))
    with pytest.raises(ValueError, match=f"{action}/{broken_index}: size or position"):
        review.audit(tmp_path)
