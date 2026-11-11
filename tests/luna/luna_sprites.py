"""The Windows XP Luna bitmaps (luna.msstyles, Blue colour scheme) as test references.

The bitmaps are Microsoft's and are never copied into the repository. They are extracted from luna.msstyles with the
QuickXP project's script (github.com/freitagdavid/QuickXP, themes/luna) into a folder holding images/BLUE_<NAME>_BMP.png
and settings/NORMALBLUE.ini; LUNA_MSSTYLES_DIR names that folder. Tests that need it skip when it is absent.

A part is an INI section of NORMALBLUE.ini ("button.pushbutton", "Window.CloseButton"); its bitmap is a vertical strip
of imageCount states, and its SizingMargins (left, right, top, bottom) cut it in nine slices that Windows stretched to
the size of the control.
"""

import configparser
import os
from collections import namedtuple
from pathlib import Path

import pytest
from PIL import Image, ImageChops

DEFAULT_DIR = Path(
    "/tmp/claude-1000/-home-gedaiu-workspace-chicago95-plasma/6679116e-4ef6-4478-b441-c6cd1dc95f4a/scratchpad/refs2/"
    "gh_freitagdavid_QuickXP/QuickXP/themes/luna/luna"
)
Margins = namedtuple("Margins", "left right top bottom")
Part = namedtuple("Part", "image_file image_count margins")


def sprite_dir():
    return Path(os.environ.get("LUNA_MSSTYLES_DIR", DEFAULT_DIR))


def sprites_available():
    return (sprite_dir() / "settings/NORMALBLUE.ini").exists()


requires_sprites = pytest.mark.skipif(not sprites_available(), reason="LUNA_MSSTYLES_DIR has no luna.msstyles bitmaps")


def theme_ini():
    parser = configparser.ConfigParser(strict=False, inline_comment_prefixes=(";",), interpolation=None)
    parser.read(sprite_dir() / "settings/NORMALBLUE.ini", encoding="latin-1")
    return parser


def numbers(text):
    return [int(value) for value in text.replace(" ", "").split(",")]


def part_of(section, image_file=None):
    values = theme_ini()[section]
    file_name = image_file or values["imagefile"]
    margins = Margins(*numbers(values.get("sizingmargins", "0,0,0,0")))
    return Part(file_name, int(values.get("imagecount", "1")), margins)


def strip_path(image_file):
    stem = image_file.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0].upper()
    return sprite_dir() / "images" / f"BLUE_{stem}_BMP.png"


def sprite(section, state, image_file=None):
    part = part_of(section, image_file)
    strip = Image.open(strip_path(part.image_file)).convert("RGBA")
    height = strip.height // part.image_count
    return strip.crop((0, state * height, strip.width, (state + 1) * height))


def stretched(section, state, width, height, image_file=None):
    """The part at the given size: corners as they are, the four edges and the middle stretched."""
    source = sprite(section, state, image_file)
    left, right, top, bottom = part_of(section, image_file).margins
    columns = [(0, left, 0), (left, source.width - right, left), (source.width - right, source.width, width - right)]
    rows = [(0, top, 0), (top, source.height - bottom, top), (source.height - bottom, source.height, height - bottom)]
    widths = [left, width - left - right, right]
    heights = [top, height - top - bottom, bottom]
    out = Image.new("RGBA", (width, height))
    for (x0, x1, x_to), piece_width in zip(columns, widths, strict=True):
        for (y0, y1, y_to), piece_height in zip(rows, heights, strict=True):
            if piece_width <= 0 or piece_height <= 0 or x1 <= x0 or y1 <= y0:
                continue
            piece = source.crop((x0, y0, x1, y1)).resize((piece_width, piece_height), Image.NEAREST)
            out.paste(piece, (x_to, y_to))
    return out


def flattened(image, background="#FFFFFF"):
    base = Image.new("RGBA", image.size, background)
    base.alpha_composite(image.convert("RGBA"))
    return base.convert("RGB")


def differing_fraction(ours, expected, tolerance=12, background="#FFFFFF", ignored=()):
    """The share of pixels, outside the ignored boxes (left, top, right, bottom), where a channel of ours differs from
    the expected image by more than the tolerance; both are laid over the background first."""
    difference = ImageChops.difference(flattened(ours, background), flattened(expected, background))
    red, green, blue = (band.point(lambda value: 255 if value > tolerance else 0) for band in difference.split())
    wrong = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    counted = Image.new("L", ours.size, 255)
    for box in ignored:
        counted.paste(0, box)
    wrong_total = sum(1 for flag, keep in zip(wrong.getdata(), counted.getdata(), strict=True) if flag and keep)
    return wrong_total / max(1, sum(1 for keep in counted.getdata() if keep))
