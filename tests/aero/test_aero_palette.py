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


@pytest.mark.parametrize(
    ("state", "measured"),
    [("active", "#528BB9"), ("inactive", "#5DABE8")],
)
def test_glass_over_the_reference_desktop_matches_the_median_frame_glass_within_three_levels(state, measured):
    colour, alpha = palette.GLASS[state]
    desktop = bytes.fromhex(palette.REFERENCE_DESKTOP[1:])
    blended = [round(d + (c - d) * alpha / 255) for c, d in zip(bytes.fromhex(colour[1:]), desktop, strict=True)]

    assert max(abs(b - m) for b, m in zip(blended, bytes.fromhex(measured[1:]), strict=True)) <= 3


@requires_sprites
@pytest.mark.parametrize(
    ("face", "part_name"),
    [("caption-end", "BUTTONACTIVECAPTIONEND"), ("caption", "BUTTONACTIVECAPTION"), ("close", "BUTTONACTIVECLOSE")],
)
def test_button_content_margins_are_the_sprites_content_margins(face, part_name):
    assert palette.BUTTON_CONTENT[face] == tuple(part("DWMWindow", part_name).properties["CONTENTMARGINS"])
