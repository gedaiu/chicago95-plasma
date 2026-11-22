"""Build Windows 98 boot and shutdown artwork for the upstream Plymouth theme."""

import argparse
import shutil
from pathlib import Path

from PIL import Image, ImageChops
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


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

    # LOGOW.SYS uses the same clouds and branding. Replace the cycling strip
    # with sky and put the caption at the measured 640×480 display coordinates.
    shutdown = image.copy()
    shutdown.paste(image.crop((0, 464, 640, 472)).transpose(Image.Transpose.FLIP_TOP_BOTTOM), (0, 472))
    svg = QSvgRenderer(str(Path(__file__).with_name("windows98-shutdown-caption.svg")))
    if not svg.isValid():
        raise ValueError("Invalid Windows 98 shutdown caption")
    caption = QImage(svg.defaultSize(), QImage.Format_RGBA8888)
    caption.fill(0)
    painter = QPainter(caption)
    svg.render(painter)
    painter.end()
    overlay = Image.frombytes("RGBA", (caption.width(), caption.height()), bytes(caption.constBits()))
    shutdown.paste(overlay, (220, 446), overlay)
    shutdown.save(target / "win95_shutdown-01.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("artwork", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    build(args.source, args.artwork, args.target)
