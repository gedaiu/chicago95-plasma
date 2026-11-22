"""The Windows 7 Aero bitmaps (aero.msstyles) and their part table, as test references.

The bitmaps are Microsoft's and are never copied into the repository. AERO_MSSTYLES_DIR names a folder holding the
resources wrestool extracted into images/ and the parts.json that tests/aero/msstyles.py wrote from them; tests that
need it skip when it is absent.

A part is a class and part name from the table ("WINDOW", "CAPTION"); its bitmap is a strip of image_count states and
its sizing margins (left, right, top, bottom) cut it in nine slices that Windows stretched to the control's size.
"""

import json
import os
from collections import namedtuple
from functools import cache
from pathlib import Path

import pytest
from PIL import Image

Margins = namedtuple("Margins", "left right top bottom")
Part = namedtuple("Part", "image_file image_count margins atlas_rect properties")


def sprite_dir():
    return Path(os.environ.get("AERO_MSSTYLES_DIR", "/nonexistent"))


def sprites_available():
    return (sprite_dir() / "parts.json").is_file()


requires_sprites = pytest.mark.skipif(not sprites_available(), reason="AERO_MSSTYLES_DIR has no aero.msstyles extract")


@cache
def part_table():
    table = json.loads((sprite_dir() / "parts.json").read_text())
    return {name.upper(): parts for name, parts in table.items()}


def part(class_name, part_name, state="0"):
    """A part's own image, or, for DWM's glass parts, the class's atlas with the part's rectangle in it."""
    parts = part_table()[class_name.upper()]
    properties = parts[part_name][state]
    atlas = parts.get("Common Properties", {}).get("0", {}).get("DISKSTREAM")
    return Part(
        properties.get("IMAGEFILE", atlas if "ATLASRECT" in properties else None),
        properties.get("IMAGECOUNT", 1),
        Margins(*properties.get("SIZINGMARGINS", (0, 0, 0, 0))),
        properties.get("ATLASRECT"),
        properties,
    )


def straight(image):
    """The image with straight alpha. Some of the theme's PNG resources store premultiplied colours (no channel above
    its alpha anywhere); read as straight alpha, their white highlights would come out grey."""
    pixels = list(image.get_flattened_data())
    if any(max(pixel[:3]) > pixel[3] for pixel in pixels):
        return image
    result = image.copy()
    result.putdata(
        [
            (*(round(channel * 255 / alpha) for channel in pixel[:3]), alpha) if (alpha := pixel[3]) else (0, 0, 0, 0)
            for pixel in pixels
        ]
    )
    return result

def fixed_corner(theme_class, part_name, state):
    """Top-left unstretched corner of a control state on the standard dialog background."""
    component = part(theme_class, part_name)
    with Image.open(sprite_dir() / component.image_file) as image:
        strip = straight(image.convert("RGBA"))
    y = state * (strip.height // component.image_count)
    width, height = component.margins.left, component.margins.top
    original = Image.new("RGBA", (width, height), "#f0f0f0")
    original.alpha_composite(strip.crop((0, y, width, y + height)))
    return original.convert("RGB")
