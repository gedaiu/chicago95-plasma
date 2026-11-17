"""Fits the Aero caption button faces to aero.msstyles and writes them to aero/aurorae/stops.py.

usage: AERO_MSSTYLES_DIR=... python3 tests/aero/fit_aero_stops.py

Each face is a strip of four states (normal, hot, pressed, disabled) in DWM's atlas. A state is drawn from: its centre
column as a vertical gradient, a black overlay whose opacity per column is how much darker that column is than the
centre (the face's horizontal shading), and EDGE columns on each side as lines with their own vertical gradients (the
border, inner highlight and outline, whose alpha also rounds the corners). Only these numbers are committed; the
bitmaps stay outside the repository.
"""

import pprint
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aero_sprites import part, sprite_dir  # noqa: E402
from PIL import Image  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "aero/aurorae/stops.py"
EDGE = 3
FACES = {
    "caption-end": ("BUTTONACTIVECAPTIONEND", "BUTTONINACTIVECAPTIONEND"),
    "caption": ("BUTTONACTIVECAPTION", "BUTTONINACTIVECAPTION"),
    "close": ("BUTTONACTIVECLOSE", "BUTTONINACTIVECLOSE"),
}
STATES = ("normal", "hot", "pressed", "disabled")
GLYPH_PARTS = {"close": "CLOSE", "minimize": "MIN", "maximize": "MAX", "restore": "RESTORE"}


def state_image(part_name, state):
    piece = part("DWMWindow", part_name)
    left, top, right, bottom = piece.atlas_rect
    rows = (bottom - top) // piece.image_count
    atlas = Image.open(sprite_dir() / piece.image_file).convert("RGBA")
    return atlas.crop((left, top + state * rows, right, top + (state + 1) * rows))


def glyph_image(glyph, state, dpi=96):
    piece = part("DWMWindow", f"BUTTON{GLYPH_PARTS[glyph]}GLYPH{dpi}")
    left, top, right, bottom = piece.atlas_rect
    rows = (bottom - top) // piece.image_count
    atlas = Image.open(sprite_dir() / piece.image_file).convert("RGBA")
    return atlas.crop((left, top + state * rows, right, top + (state + 1) * rows))


def glyph_colours(image):
    """The outline (the darkest of the most opaque pixels) and the body's top and bottom (its lightest rows)."""
    pixels = [[image.getpixel((x, y)) for x in range(image.width)] for y in range(image.height)]
    solid = max(pixel[3] for row in pixels for pixel in row)
    outline = min((pixel for row in pixels for pixel in row if pixel[3] == solid), key=lambda pixel: sum(pixel[:3]))
    lightest = [
        max((pixel for pixel in row if pixel[3] == solid), key=sum) for row in pixels if solid in [p[3] for p in row]
    ]
    body = [pixel for pixel in lightest if sum(pixel[:3]) > sum(outline[:3]) + 60]
    return {"outline": stop(outline), "top": stop(body[0]), "bottom": stop(body[-1])}


def stop(pixel):
    red, green, blue, alpha = pixel
    return (f"#{red:02X}{green:02X}{blue:02X}", alpha)


GLASS = (82, 139, 185)
TOP_ROWS, BOTTOM_ROWS = 2, 3
BAND_ROWS = 2


def seen_luminance(pixel):
    """How bright a pixel looks drawn over the frame glass."""
    alpha = pixel[3] / 255
    return sum(
        weight * (channel * alpha + glass * (1 - alpha))
        for weight, channel, glass in zip((0.299, 0.587, 0.114), pixel, GLASS, strict=False)
    )


def column_shade(image, x, centre_x, rows):
    """How much darker column x looks than the centre across rows, as a black overlay's opacity."""
    column = sum(seen_luminance(image.getpixel((x, y))) for y in rows)
    centre = sum(seen_luminance(image.getpixel((centre_x, y))) for y in rows)
    return round(min(1.0, max(0.0, 1 - column / centre)), 3)


def fit_state(image):
    width, height = image.size
    centre_x = width // 2
    return {
        "size": (width, height),
        "rows": [stop(image.getpixel((centre_x, y))) for y in range(height)],
        "bands": [
            {
                "rows": (top, min(top + BAND_ROWS, height - BOTTOM_ROWS)),
                "shade": [
                    column_shade(image, x, centre_x, range(top, min(top + BAND_ROWS, height - BOTTOM_ROWS)))
                    for x in range(EDGE, width - EDGE)
                ],
            }
            for top in range(TOP_ROWS, height - BOTTOM_ROWS, BAND_ROWS)
        ],
        "left": [[stop(image.getpixel((x, y))) for y in range(height)] for x in range(EDGE)],
        "right": [[stop(image.getpixel((x, y))) for y in range(height)] for x in range(width - EDGE, width)],
    }


def fitted_faces():
    return {
        face: {
            window: {state: fit_state(state_image(parts[index], number)) for number, state in enumerate(STATES)}
            for index, window in enumerate(("active", "inactive"))
        }
        for face, parts in FACES.items()
    }


def fitted_glyphs():
    return {
        glyph: {state: glyph_colours(glyph_image(glyph, number)) for number, state in enumerate(STATES)}
        for glyph in GLYPH_PARTS
    }


if __name__ == "__main__":
    text = (
        '"""Aero caption button faces fitted to aero.msstyles by tests/aero/fit_aero_stops.py; '
        'do not edit by hand."""\n\n'
        f"EDGE = {EDGE}\n"
        f"GLYPHS = {pprint.pformat(fitted_glyphs(), width=120, compact=True)}\n"
        f"FACES = {pprint.pformat(fitted_faces(), width=120, compact=True)}\n"
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text)
    print("wrote", OUTPUT)
