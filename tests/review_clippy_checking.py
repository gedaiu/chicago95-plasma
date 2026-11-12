"""Check all dense CheckingSomething renders and create a local video review."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from export_clippy_video import export
from PIL import Image, ImageDraw


def review(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    collision = json.loads((folder / "checking-collisions.json").read_text())
    items = manifest["sequences"]["CheckingSomething"]
    assert collision["baked_samples_checked"] == len(items)
    assert collision["start_end_rest_projection_matches"]
    assert collision["blend_sha256"] == hashlib.sha256((folder / "all-animations.blend").read_bytes()).hexdigest()
    images, hashes = [], set()
    for item in items:
        im = Image.open(folder / item["file"]).convert("RGBA")
        assert im.size == tuple(manifest["pixel_size"])
        alpha = np.asarray(im)[:, :, 3]
        assert alpha.any(), ("Empty frame", item["file"])
        assert not any(edge.any() for edge in [alpha[0], alpha[-1], alpha[:, 0], alpha[:, -1]]), (
            "Clipped",
            item["file"],
        )
        hashes.add(hashlib.sha256(im.tobytes()).hexdigest())
        images.append(im)
    first, last = np.asarray(images[0]).astype(int), np.asarray(images[-1]).astype(int)
    # Equal geometry can differ by one 8-bit level from denoising roundoff.
    endpoint_error = int(abs(first - last).max())
    assert endpoint_error <= 1, ("Endpoint pixels differ", endpoint_error)
    assert len(hashes) > len(images) * 0.9, "Dense motion unexpectedly repeats too many rendered poses"
    transitions = [list(range(0, 37, 3)), list(range(len(items) - 37, len(items), 3))]
    sheet = Image.new("RGB", (13 * 124, 2 * 116), "#008080")
    draw = ImageDraw.Draw(sheet)
    for row, ticks in enumerate(transitions):
        for col, tick in enumerate(ticks):
            im = images[tick].resize((124, 93), Image.Resampling.LANCZOS)
            x, y = col * 124, row * 116
            draw.text((x + 2, y + 2), f"{tick / 60:.2f}s", fill="white")
            sheet.paste(im, (x, y + 20), im)
    sheet.save(folder / "transitions.png")
    low = [np.asarray(im.resize((124, 93), Image.Resampling.LANCZOS).convert("RGBa"), dtype=float) for im in images]
    deltas = [float(np.abs(b - a).mean()) for a, b in zip(low, low[1:], strict=False)]
    report = {
        "frames_checked": len(items),
        "distinct_rgba_frames": len(hashes),
        "first_last_rgba_identical": bool(np.array_equal(first, last)),
        "first_last_max_channel_error": endpoint_error,
        "clipped_frames": 0,
        "adjacent_mean_premultiplied_change": deltas,
        "scope": "Pixel checks and transition filmstrip. No 98% original fidelity claim.",
    }
    (folder / "visual-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    video = folder / "videos/CheckingSomething"
    if not video.exists():
        export(folder, video, fps=60)
    checked = json.loads((video / "verification.json").read_text())
    assert checked["source_frame_repeats"] == [1] * len(items)
    assert checked["max_alpha_error"] == 0 and checked["mp4_fully_decoded"]
    (folder / "index.html").write_text("""<!doctype html><meta charset="utf-8"><title>CheckingSomething repair</title>
<style>body{font:16px system-ui;margin:24px;max-width:1200px}video,img{max-width:100%}video{background:#008080}</style>
<h1>CheckingSomething — transition and collision repair</h1>
<p>398 individually rendered poses at 60 fps. Starts and ends at the same rest pose
(rendered endpoint channels differ by at most one 8-bit level).
The wire contracts and returns continuously; glasses appear and withdraw continuously.
This is reconstructed motion, not a certified match to the original animation.</p>
<video src="videos/CheckingSomething/clippy-transparent.webm" controls loop playsinline></video>
<p><button onclick="document.querySelector('video').playbackRate=1">1×</button>
<button onclick="document.querySelector('video').playbackRate=.25">¼×</button></p>
<p><a href="videos/CheckingSomething/clippy-preview.mp4">MP4</a> ·
<a href="checking-collisions.json">All output-frame collision checks</a> ·
<a href="visual-verification.json">Pixel checks</a> ·
<a href="videos/CheckingSomething/verification.json">Video and alpha checks</a> ·
<a href="all-animations.blend">Editable single-animation Blender candidate</a></p>
<p>Internal pupil/socket and glasses bridge/frame joins are retained. Other intersections are rejected.
The main library and older combined video are unchanged.</p>
<h2>Entrance and return, every 50 ms</h2>
<a href="transitions.png"><img src="transitions.png" alt="Entrance and return to rest"></a>""")
    print(json.dumps({k: v for k, v in report.items() if not isinstance(v, list)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    review(parser.parse_args().folder)
