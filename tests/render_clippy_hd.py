#!/usr/bin/env python3
"""Build the experimental HD blink pack and a review video; no live desktop changes."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from clippy_hd import FRAME_SIZE, SEQUENCE, frames  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter  # noqa: E402


def render(output):
    output.mkdir(parents=True, exist_ok=False)
    images = frames(ROOT / "data/clippy/hd-reference")
    for index, image in enumerate(images):
        if not image.save(str(output / f"blink-{index}.png")):
            raise RuntimeError("Could not save HD frame")
    manifest = {
        "status": "experimental blink pack, not the complete assistant atlas",
        "logical_size": [124, 93],
        "pixel_size": [FRAME_SIZE.width(), FRAME_SIZE.height()],
        "scale": 4,
        "sequence": [{"file": f"blink-{index}.png", "duration_ms": duration} for index, duration in SEQUENCE],
        "invariants": ["Body, paper and eyebrows fixed to rest master", "First and last frame identical"],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # MP4 has no alpha; display the actual transparent frames on desktop teal.
    # A second row at native logical size reveals flicker that a large still can hide.
    video = output / "video-frames"
    video.mkdir()
    count = 0
    for _ in range(2):
        for index, duration in SEQUENCE:
            canvas = QImage(640, 540, QImage.Format_RGB32)
            canvas.fill(QColor("#008080"))
            painter = QPainter(canvas)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.drawImage(72, 12, images[index])
            painter.drawImage(258, 420, images[index].scaled(124, 93, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            painter.end()
            for _ in range(duration // 20):
                canvas.save(str(video / f"{count:05d}.png"))
                count += 1
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-framerate",
            "50",
            "-i",
            str(video / "%05d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output / "clippy-hd-blink.mp4"),
        ],
        check=True,
    )
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.output)
    print(args.output / "clippy-hd-blink.mp4")
