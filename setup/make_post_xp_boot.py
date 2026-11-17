#!/usr/bin/env python3
"""Import original boot artwork without installing fonts or fetching files.

python setup/make_post_xp_boot.py --vista /path/to/PlymouthVista --font /path/to/segoe_slboot.ttf
Windows 7: 105 original 200×200 frames, 15 fps, repeat frames 60–104.
Windows 8–11 (the dotted spinner in the reference): U+E052–U+E0C6, 30 fps.
"""

import argparse
import json
import subprocess
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
ASSETS = REPO / "splash/chicago95.splashscreen/contents/splash/postxp"


def generate(vista, font, video=None):
    ASSETS.mkdir(parents=True, exist_ok=True)
    # 15×7 keeps both dimensions below 4096, unlike a 21,000px vertical strip.
    sheet = Image.new("RGBA", (3000, 1400))
    for index in range(105):
        image = Image.open(vista / "images" / f"flag{index}.png").convert("RGBA")
        # Unmatte the original black canvas. Compositing back onto black recovers
        # the original RGB (within rounding), while custom backgrounds remain visible.
        pixels = []
        for red, green, blue, _alpha in image.get_flattened_data():
            alpha = max(red, green, blue)
            pixels.append(
                (round(red * 255 / alpha), round(green * 255 / alpha), round(blue * 255 / alpha), alpha)
                if alpha
                else (0, 0, 0, 0)
            )
        image.putdata(pixels)
        sheet.paste(image, ((index % 15) * 200, (index // 15) * 200))
    sheet.save(ASSETS / "seven.png", optimize=True)
    Image.open(vista / "images/progress.png").save(ASSETS / "vista-progress.png")
    source = TTFont(font)
    glyphs, mapping = source.getGlyphSet(), source.getBestCmap()
    paths = []
    # Bounds over every spinner frame: (32, -478)–(2690, 2182).
    # A common transform preserves the original acceleration, spacing and dot sizes.
    scale = 64 / 2660
    for codepoint in range(0xE052, 0xE0C7):
        pen = SVGPathPen(glyphs)
        transform = TransformPen(pen, (scale, 0, 0, -scale, -32 * scale, 2182 * scale))
        glyphs[mapping[codepoint]].draw(transform)
        paths.append(pen.getCommands())
    (ASSETS / "SpinnerPaths.qml").write_text(
        "import QtQml 2.15\n\nQtObject {\n    readonly property var paths: "
        + json.dumps(paths, indent=4).replace("\n", "\n    ")
        + "\n}\n"
    )

    if video is not None:
        for name, timestamp, box in (
            ("seven-text", 338.5, "320:80:800:720"),
            ("seven-footer", 338.5, "320:48:800:1000"),
            ("vista-footer", 296, "320:48:800:864"),
        ):
            subprocess.run(
                [
                    "ffmpeg",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    str(timestamp),
                    "-i",
                    str(video),
                    "-vf",
                    "crop=" + box,
                    "-frames:v",
                    "1",
                    str(ASSETS / (name + ".png")),
                ],
                check=True,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vista", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--video", type=Path, help="1920×1080 Z1ZHVuCi14E.mp4, for default lettering")
    args = parser.parse_args()
    generate(args.vista, args.font, args.video)
