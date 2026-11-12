"""Adapt the upstream Plymouth theme's prompt handling to the Windows 98 boot artwork."""

import argparse
import shutil
from pathlib import Path

from PIL import Image, ImageChops


def build(source, artwork, target):
    shutil.copytree(source, target, dirs_exist_ok=True)
    theme = target / "Chicago95.plymouth"
    text = theme.read_text().replace("Chicago95", "Chicago95-98").replace("Windows 95", "Windows 98")
    theme.unlink()
    (target / "Chicago95-98.plymouth").write_text(text)
    (target / "Chicago95.script").rename(target / "Chicago95-98.script")
    image = Image.open(artwork).convert("RGB")
    # The captured DOS screen is 640x400 with non-square pixels; the shipped
    # artwork is already corrected to 640x480. Only its bottom colour strip moves.
    strip = image.crop((0, 472, image.width, 480))
    for phase in range(20):
        frame = image.copy()
        frame.paste(ImageChops.offset(strip, phase * image.width // 20, 0), (0, 472))
        frame.save(target / f"win95_boot_{phase}.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("artwork", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    build(args.source, args.artwork, args.target)
