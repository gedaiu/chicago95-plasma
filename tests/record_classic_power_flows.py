#!/usr/bin/env python3
"""Run intercepted 9x/2000/2001 power flows and create labelled visual review reels.

These reels hold test captures for one second, not actual OS animation timings.
No logout, suspend, reboot or shutdown command is executed.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_classic_power_flows.py", "-q"],
        cwd=REPO,
        env={**os.environ, "POWER_FLOW_OUTPUT": str(output)},
        check=True,
    )
    for style in ("1995", "1998", "2000", "2001"):
        frames = output / style / "review"
        frames.mkdir()
        manifest = []
        for action in sorted(path for path in (output / style).iterdir() if path != frames):
            for capture in sorted(action.glob("*.png")):
                image = Image.open(capture).convert("RGB")
                canvas = Image.new("RGB", (960, 720), "#202020")
                canvas.paste(image, ((960 - image.width) // 2, (720 - image.height) // 2))
                ImageDraw.Draw(canvas).text((12, 12), f"{style} / action {action.name} / {capture.stem}", fill="white")
                canvas.save(frames / f"{len(manifest):04d}.png")
                manifest.append(str(capture.relative_to(output)))
        (frames / "manifest.json").write_text(
            json.dumps(
                {
                    "frames": manifest,
                    "limits": [
                        "Backend intercepted",
                        "One-second stills, not measured timing",
                        "Widget captures do not validate compositor backdrops",
                        "2000/2001 still use the legacy safe-to-turn-off screen",
                    ],
                },
                indent=2,
            )
        )
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-framerate",
                "1",
                "-i",
                str(frames / "%04d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(output / f"power-{style}.mp4"),
            ],
            check=True,
        )
    print(output)


if __name__ == "__main__":
    main()
