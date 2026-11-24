"""Build Windows 95 and 98 boot artwork for the upstream Plymouth theme."""

import argparse
import shutil
from pathlib import Path

from PIL import Image, ImageSequence
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def svg_image(path):
    svg = QSvgRenderer(str(path))
    if not svg.isValid():
        raise ValueError(f"Invalid artwork in {path}")
    picture = QImage(svg.defaultSize(), QImage.Format_RGBA8888)
    picture.fill(0)
    painter = QPainter(picture)
    svg.render(painter)
    painter.end()
    return Image.frombytes("RGBA", (picture.width(), picture.height()), bytes(picture.constBits()))


def build(source, artwork, target, *, look="98"):
    shutil.copytree(source, target, dirs_exist_ok=True)
    script = target / "Chicago95.script"
    # The observed native palette steps are approximately 56 ms apart.
    text = script.read_text().replace("Plymouth.SetRefreshRate(10)", "Plymouth.SetRefreshRate(18)")
    script.write_text(text)
    if look == "95":
        with Image.open(artwork) as animation:
            for phase, frame in enumerate(ImageSequence.Iterator(animation)):
                frame.convert("RGB").save(target / f"win95_boot_{phase}.png")
        return

    theme = target / "Chicago95.plymouth"
    text = theme.read_text().replace("Chicago95", "Chicago95-98").replace("Windows 95", "Windows 98")
    theme.unlink()
    (target / "Chicago95-98.plymouth").write_text(text)
    script.rename(target / "Chicago95-98.script")
    image = Image.open(artwork).convert("RGB")
    # Keep the same palette fields and dithering as the Qt preview. The
    # native 640x400 rows are already corrected to the 4:3 display aspect.
    strips = svg_image(artwork.with_name("windows98-boot-strip.svg"))
    for phase in range(20):
        frame = image.copy()
        frame.paste(strips.crop((0, phase * 8, 640, (phase + 1) * 8)), (0, 472))
        frame.save(target / f"win95_boot_{phase}.png")

    # LOGOW.SYS uses the same clouds and branding. Replace the cycling strip
    # with sky and put the caption at the measured 640×480 display coordinates.
    shutdown = image.copy()
    shutdown.paste(image.crop((0, 464, 640, 472)).transpose(Image.Transpose.FLIP_TOP_BOTTOM), (0, 472))
    overlay = svg_image(Path(__file__).with_name("windows98-shutdown-caption.svg"))
    shutdown.paste(overlay, (220, 446), overlay)
    shutdown.save(target / "win95_shutdown-01.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("artwork", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--look", choices=("95", "98"), default="98")
    args = parser.parse_args()
    build(args.source, args.artwork, args.target, look=args.look)
