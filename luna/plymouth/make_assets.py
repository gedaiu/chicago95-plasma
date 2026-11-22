"""Draws the XP boot screen's pictures: the wordmark (rendered from luna/images/windows-xp-logo.svg) with the
edition name below it, the SVG progress trough and moving group of three blocks, at 1x and 2x (a 640x480 layout)."""

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "images"))

import render_logo  # noqa: E402

FOLDER = Path(__file__).parent / "Chicago95-XP"
SUPERSAMPLE = 4
WORDMARK_SCALE = 1.85
WORDMARK_UNITS = (132, 95)
TROUGH_UNITS = (126, 15)
BLOCK_UNITS = (22, 9)
SPLASH = Path(__file__).resolve().parents[1] / "splash"
EDITION_NAME = "Professional"
EDITION_LEFT_UNITS = 8
EDITION_BASELINE_UNITS = 93.6
EDITION_WIDTH_UNITS = 90
EDITION_SIZE_UNITS = 18
WHITE = (239, 239, 239, 255)
SIZES = {
    "logo": tuple(round(unit * WORDMARK_SCALE) for unit in WORDMARK_UNITS),
    "trough": TROUGH_UNITS,
    "block": BLOCK_UNITS,
}
MULTIPLIERS = {"": 1, "@2x": 2}


def bold_font_path():
    matched = subprocess.run(
        ["fc-match", "-f", "%{file}", "Trebuchet MS:bold"], capture_output=True, text=True, check=True
    ).stdout
    return matched


def fitted_font(text, width, start_size):
    size = start_size
    while size > 4:
        font = ImageFont.truetype(bold_font_path(), size)
        if font.getlength(text) <= width:
            return font
        size -= 1
    return ImageFont.truetype(bold_font_path(), 4)


def draw_edition(canvas, scale):
    font = fitted_font(EDITION_NAME, EDITION_WIDTH_UNITS * scale, EDITION_SIZE_UNITS * scale)
    ImageDraw.Draw(canvas).text(
        (EDITION_LEFT_UNITS * scale, EDITION_BASELINE_UNITS * scale), EDITION_NAME, font=font, fill=WHITE, anchor="ls"
    )


def draw_logo(multiplier):
    scale = WORDMARK_SCALE * multiplier * SUPERSAMPLE
    size = tuple(round(unit * scale) for unit in WORDMARK_UNITS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_edition(canvas, scale)
    canvas = canvas.resize(size_at("logo", multiplier), Image.LANCZOS)
    canvas.alpha_composite(render_logo.render_wordmark(size_at("logo", multiplier)[0]))
    return canvas


def size_at(name, multiplier):
    return tuple(side * multiplier for side in SIZES[name])


def draw_trough(multiplier):
    return render_logo.render_to_image((SPLASH / "boot-trough.svg").read_bytes(), *size_at("trough", multiplier))


def draw_block(multiplier):
    return render_logo.render_to_image((SPLASH / "boot-blocks.svg").read_bytes(), *size_at("block", multiplier))


DRAWERS = {"logo": draw_logo, "trough": draw_trough, "block": draw_block}


def write_all():
    FOLDER.mkdir(parents=True, exist_ok=True)
    for name, drawer in DRAWERS.items():
        for suffix, multiplier in MULTIPLIERS.items():
            drawer(multiplier).save(FOLDER / f"{name}{suffix}.png")


if __name__ == "__main__":
    write_all()
