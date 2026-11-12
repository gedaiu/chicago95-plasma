"""Exercise actual video selection, zero-duration frames, and decoded transparency."""

import json
import shutil

import numpy as np
import pytest
from export_clippy_video import export
from PIL import Image


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg required")
def test_selected_clip_retains_exact_alpha_and_zero_duration(tmp_path):
    # Non-binary alpha catches conversion errors hidden by opaque-only test images.
    rgba = np.zeros((16, 16, 4), dtype=np.uint8)
    rgba[:, :, :3] = [140, 170, 210]
    rgba[:, :, 3] = np.arange(256, dtype=np.uint8).reshape(16, 16)
    Image.fromarray(rgba).save(tmp_path / "frame.png")
    manifest = {
        "pixel_size": [16, 16],
        "status": "test",
        "sequences": {
            "Omitted": [{"file": "does-not-exist.png", "duration_ms": 500}],
            "Selected": [{"file": "frame.png", "duration_ms": d} for d in [20, 0, 50]],
        },
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    output = tmp_path / "video"
    export(tmp_path, output, ["Selected"])
    result = json.loads((output / "verification.json").read_text())
    assert result["actions"] == ["Selected"]
    assert result["frames"] == result["webm_decoded_frames"] == 7
    assert result["fps"] == 100
    assert result["duration_seconds"] == 0.07
    assert result["max_alpha_error"] == 0
    assert result["mp4_fully_decoded"]


def test_library_audit_rejects_clipped_artwork_and_changed_source(tmp_path, monkeypatch):
    import review_clippy_library as review

    source = {"RestPose": {"frames": [{"duration": 100, "images": []}]}}
    monkeypatch.setattr(review, "catalog", lambda: source)
    reference = Image.new("RGBA", (124, 93))
    monkeypatch.setattr(review, "original_frames", lambda name: [(reference, 100)])
    frame = Image.new("RGBA", (124, 93))
    frame.putpixel((0, 45), (255, 255, 255, 255))
    frame.save(tmp_path / "frame.png")
    item = {"source_index": 0, "duration_ms": 100, "source": source["RestPose"]["frames"][0], "file": "frame.png"}
    manifest = {"pixel_size": [124, 93], "sequences": {"RestPose": [item]}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "bake-verification.json").write_text(json.dumps({"poses": 1, "failures": []}))
    with pytest.raises(ValueError, match="clips the render border"):
        review.audit(tmp_path)
    item["source"] = {"duration": 100, "images": [], "exitBranch": 1}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="branch metadata changed"):
        review.audit(tmp_path)


def test_sixty_fps_rounds_cumulative_boundaries_without_drift():
    from export_clippy_video import frame_schedule

    repeats, errors = frame_schedule([10, 0, 10] * 1000, 60)
    assert sum(repeats) == 1200
    assert all(repeats[i] == 0 for i in range(1, len(repeats), 3))
    assert max(map(abs, errors)) <= 1000 / 120


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg required")
def test_sixty_fps_export_verifies_alpha_and_frame_rate(tmp_path):
    Image.new("RGBA", (16, 16), (120, 180, 200, 127)).save(tmp_path / "frame.png")
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "pixel_size": [16, 16],
                "status": "test",
                "sequences": {"Clip": [{"file": "frame.png", "duration_ms": d} for d in [10, 0, 20, 40]]},
            }
        )
    )
    export(tmp_path, tmp_path / "video", fps=60)
    r = json.loads((tmp_path / "video/verification.json").read_text())
    assert r["fps"] == 60
    assert r["frames"] == r["webm_decoded_frames"] == 4
    assert r["max_alpha_error"] == 0
    assert r["max_boundary_error_ms"] <= 1000 / 120
    assert r["source_frame_repeats"][1] == 0


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg required")
def test_dense_motion_exports_every_unique_pose_once(tmp_path):
    frames = []
    for index, duration in enumerate([17, 16, 17, 17, 16, 17]):
        filename = f"{index}.png"
        # Distinct alpha per pose catches dropped, reordered, or repeated images
        # in the exporter's independent decoded-alpha comparison.
        Image.new("RGBA", (16, 16), (100, 150, 200, 30 + index * 35)).save(tmp_path / filename)
        frames.append({"file": filename, "duration_ms": duration})
    sampling = "One independently rendered pose per 60-fps frame."
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "pixel_size": [16, 16],
                "status": "test",
                "sampling": sampling,
                "sequences": {"Motion": frames},
            }
        )
    )
    export(tmp_path, tmp_path / "video", fps=60)
    report = json.loads((tmp_path / "video/verification.json").read_text())
    assert report["source_frame_repeats"] == [1] * 6
    assert report["frames"] == report["webm_decoded_frames"] == 6
    assert report["max_alpha_error"] == 0
    assert report["sampling"] == sampling
