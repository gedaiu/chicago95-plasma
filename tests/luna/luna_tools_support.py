from pathlib import Path

from PIL import Image
from reference import qimage_to_pil

REFERENCES = Path(__file__).resolve().parents[1] / "references"
PREVIEW_DIR = Path(
    "/tmp/claude-1000/-home-gedaiu-workspace-chicago95-plasma/6679116e-4ef6-4478-b441-c6cd1dc95f4a/scratchpad/luna-preview"
)
CLASSIC_BEVEL_COLOURS = {(0x80, 0x80, 0x80), (0x40, 0x40, 0x40), (0xDF, 0xDF, 0xDF), (0xC0, 0xC0, 0xC0)}
CLASSIC_TITLE_BAND = (0x00, 0x00, 0x80)


def hex_rgb(colour):
    return tuple(int(colour[index : index + 2], 16) for index in (1, 3, 5))


def reference(name):
    return Image.open(REFERENCES / name).convert("RGB")


def grab_picture(widget):
    return qimage_to_pil(widget.grab().toImage()).convert("RGB")


def columns_with(image, colour, row, left=0, right=None):
    wanted = hex_rgb(colour)
    return [x for x in range(left, right or image.width) if image.getpixel((x, row)) == wanted]


def border_pixels(image):
    width, height = image.size
    edge = [(x, y) for x in range(width) for y in (0, height - 1)] + [
        (x, y) for y in range(height) for x in (0, width - 1)
    ]
    return [image.getpixel(point) for point in edge]


def has_classic_bevel(image):
    return any(pixel in CLASSIC_BEVEL_COLOURS for pixel in border_pixels(image)) or any(
        pixel == CLASSIC_TITLE_BAND for pixel in border_pixels(image)
    )


def differing_fraction(first, second, masks=()):
    differing = total = 0
    for y in range(first.height):
        for x in range(first.width):
            if any(left <= x <= right and top <= y <= bottom for left, top, right, bottom in masks):
                continue
            total += 1
            differing += (
                max(abs(a - b) for a, b in zip(first.getpixel((x, y)), second.getpixel((x, y)), strict=True)) > 12
            )
    return differing / total


def save_preview(name, ours, expected=None):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    parts = [ours] + ([expected] if expected is not None else [])
    sheet = Image.new(
        "RGB", (sum(part.width for part in parts) + 8 * (len(parts) - 1), max(part.height for part in parts)), "#FFFFFF"
    )
    left = 0
    for part in parts:
        sheet.paste(part, (left, 0))
        left += part.width + 8
    sheet.save(PREVIEW_DIR / f"tools-{name}.png")
