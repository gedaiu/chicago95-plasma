"""Every Aero frame colour against the aero.msstyles pixel it was measured from."""

import importlib.util

import pytest
from aero_sprites import part, requires_sprites, sprite_dir
from conftest import REPO
from PIL import Image

spec = importlib.util.spec_from_file_location("aero_palette", REPO / "aero/palette.py")
palette = importlib.util.module_from_spec(spec)
spec.loader.exec_module(palette)


def atlas_pixel(part_name, state, x, y):
    piece = part("DWMWindow", part_name)
    left, top, right, bottom = piece.atlas_rect
    rows = (bottom - top) // piece.image_count
    return Image.open(sprite_dir() / piece.image_file).convert("RGBA").getpixel((left + x, top + state * rows + y))


@requires_sprites
@pytest.mark.parametrize("state", ["active", "inactive"])
@pytest.mark.parametrize("line", sorted(palette.FRAME_LINES))
def test_frame_line_colour_and_opacity_match_the_left_frame_sprite(line, state):
    drawn = palette.FRAME_LINES[line]
    x = drawn["sample_column"]

    colour, alpha = drawn[state]

    assert atlas_pixel("LEFTFRAME", ("active", "inactive").index(state), x, 0) == (*bytes.fromhex(colour[1:]), alpha)
