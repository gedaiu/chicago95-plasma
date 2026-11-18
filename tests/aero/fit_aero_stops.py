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

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parent.parent)]
from aero_sprites import part, sprite_dir, straight  # noqa: E402
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


# TaskBand2's TASKITEM strip, in the order the references show: a running task, the focused one, a task calling for
# attention, and a pinned launcher, each with its pointer states.
TASK_STATES = (
    "normal",
    "hover",
    "pressed",
    "focus",
    "focus-hover",
    "focus-pressed",
    "attention",
    "launcher",
    "launcher-hover",
    "launcher-pressed",
)
BAR_GLASS = (72, 132, 181)
TASK_OUTPUT = REPO / "aero/plasma-style/stops.py"


def task_image(state):
    piece = part("TaskBand2", "TASKITEM")
    strip = straight(Image.open(sprite_dir() / piece.image_file).convert("RGBA"))
    rows = strip.height // piece.image_count
    return strip.crop((0, state * rows, strip.width, (state + 1) * rows))


SHOW_DESKTOP_STATES = ("normal", "hover", "pressed")


SHOW_DESKTOP_WIDTH = 15  # win7screenres.png's strip, x 1009..1023


def show_desktop_image(state):
    """A state of the Show desktop button as Windows draws it at the screen's edge: its 17-column sprite at
    SHOW_DESKTOP_WIDTH, the side columns its sizing margins keep and the middle ones squeezed between them."""
    piece = part("ShowDesktop::Button", "Common Properties")
    strip = straight(Image.open(sprite_dir() / piece.image_file).convert("RGBA"))
    rows = strip.height // piece.image_count
    sprite = strip.crop((0, state * rows, strip.width, (state + 1) * rows))
    left, right = piece.margins.left, piece.margins.right
    middle = sprite.crop((left, 0, sprite.width - right, rows)).resize(
        (SHOW_DESKTOP_WIDTH - left - right, rows), Image.Resampling.NEAREST
    )
    drawn = Image.new("RGBA", (SHOW_DESKTOP_WIDTH, rows))
    drawn.paste(sprite.crop((0, 0, left, rows)), (0, 0))
    drawn.paste(middle, (left, 0))
    drawn.paste(sprite.crop((sprite.width - right, 0, sprite.width, rows)), (SHOW_DESKTOP_WIDTH - right, 0))
    return drawn


# A combined button's stacked edges, laid at its right: one card for two windows (the strip's state 1), two for three
# or more (state 2), from TASKITEMGROUP and, for the focused program, TASKITEMGROUPSELECTED. State 0 is empty.
GROUP_STATES = {"group-2": ("TASKITEMGROUP", 1), "group-3": ("TASKITEMGROUP", 2)}
GROUP_STATES |= {f"group-selected-{n}": ("TASKITEMGROUPSELECTED", state) for n, state in (("2", 1), ("3", 2))}


def group_image(part_name, state):
    piece = part("TaskBand2", part_name)
    strip = straight(Image.open(sprite_dir() / piece.image_file).convert("RGBA"))
    rows = strip.height // piece.image_count
    return strip.crop((0, state * rows, strip.width, (state + 1) * rows))


def fitted_groups():
    # A strip this narrow is lines alone: every column its own vertical gradient.
    return {
        state: fit_state(image, BAR_GLASS, image.width // 2)
        for state, image in ((state, group_image(*source)) for state, source in GROUP_STATES.items())
    }


def fitted_show_desktop():
    return {state: fit_state(show_desktop_image(index), BAR_GLASS) for index, state in enumerate(SHOW_DESKTOP_STATES)}


# The states the superbar draws: a pinned program at rest shows no face, and under the pointer a running task's.
DRAWN_TASK_STATES = ("normal", "hover", "pressed", "focus", "focus-hover", "focus-pressed", "attention")
GLOSS_TOP, GLOSS_BOTTOM = 2, 3  # the face's top and bottom rows, drawn across as they are
GLOSS_EDGE = 4  # and its columns down each side: the outline, the highlight and the border's shading
GLOSS_ROUNDS = 10


def plasma_style():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "make_aero_plasmastyle", REPO / "aero/plasma-style/make_aero_plasmastyle.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def over_bar_glass(image):
    base = Image.new("RGBA", image.size, (*BAR_GLASS, 255))
    base.alpha_composite(image)
    return base.convert("RGB")


def fit_glossy_state(image, generator):
    """A superbar face: exact edge columns and top and bottom rows; each inner row's base, the faintest colour in it;
    and the gloss's curve, direction and opacities searched until the drawn face over the bar is closest to the
    sprite's."""
    from test_aero_buttons import rendered

    width, height = image.size
    inner = range(GLOSS_EDGE, width - GLOSS_EDGE)
    face = {
        "size": (width, height),
        "rows": [
            stop(min((image.getpixel((x, y)) for x in inner), key=lambda pixel: pixel[3]))
            for y in range(GLOSS_TOP, height - GLOSS_BOTTOM)
        ],
        "top": [[stop(image.getpixel((x, y))) for x in inner] for y in range(GLOSS_TOP)],
        "bottom": [[stop(image.getpixel((x, y))) for x in inner] for y in range(height - GLOSS_BOTTOM, height)],
        "left": [[stop(image.getpixel((x, y))) for y in range(height)] for x in range(GLOSS_EDGE)],
        "right": [[stop(image.getpixel((x, y))) for y in range(height)] for x in range(width - GLOSS_EDGE, width)],
    }
    target = over_bar_glass(image)

    def error(gloss):
        drawn = over_bar_glass(rendered(generator.glossy_face_svg({**face, "gloss": gloss}), (width, height)))
        return sum(
            abs(a - b)
            for x in inner
            for y in range(GLOSS_TOP, height - GLOSS_BOTTOM)
            for a, b in zip(drawn.getpixel((x, y)), target.getpixel((x, y)), strict=True)
        )

    numbers = [height * 0.6, width / 2, height * 0.3, 4, 0, 0, width * 0.8, height * 0.6, 0.6, 0.4, 0]
    steps = [3, 6, 3, 3, 6, 4, 8, 6, 0.1, 0.1, 0.1]

    def gloss_of(values):
        start, curve_x, curve_y, end, centre_x, centre_y, radius_x, radius_y, *opacities = values
        return {
            "curve": tuple(round(v, 2) for v in (start, curve_x, curve_y, end)),
            "centre": (round(centre_x, 2), round(centre_y, 2)),
            "radii": (round(max(1, radius_x), 2), round(max(1, radius_y), 2)),
            "opacity": tuple(round(min(1, max(0, opacity)), 3) for opacity in opacities),
        }

    best = error(gloss_of(numbers))
    for _ in range(GLOSS_ROUNDS):
        for index in range(len(numbers)):
            for sign in (1, -1):
                while True:
                    trial = list(numbers)
                    trial[index] += sign * steps[index]
                    score = error(gloss_of(trial))
                    if score >= best:
                        break
                    best, numbers = score, trial
        steps = [step / 2 for step in steps]
    return {**face, "gloss": gloss_of(numbers)}


def fitted_tasks():
    generator = plasma_style()
    return {state: fit_glossy_state(task_image(TASK_STATES.index(state)), generator) for state in DRAWN_TASK_STATES}


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


def seen_luminance(pixel, glass):
    """How bright a pixel looks drawn over glass."""
    alpha = pixel[3] / 255
    return sum(
        weight * (channel * alpha + behind * (1 - alpha))
        for weight, channel, behind in zip((0.299, 0.587, 0.114), pixel, glass, strict=False)
    )


def column_shade(image, x, centre_x, rows, glass):
    """How much darker column x looks than the centre across rows, as a black overlay's opacity."""
    column = sum(seen_luminance(image.getpixel((x, y)), glass) for y in rows)
    centre = sum(seen_luminance(image.getpixel((centre_x, y)), glass) for y in rows)
    return round(min(1.0, max(0.0, 1 - column / centre)), 3)


def fit_state(image, glass=GLASS, edge=EDGE):
    width, height = image.size
    centre_x = width // 2
    return {
        "size": (width, height),
        "rows": [stop(image.getpixel((centre_x, y))) for y in range(height)],
        "bands": [
            {
                "rows": (top, min(top + BAND_ROWS, height - BOTTOM_ROWS)),
                "shade": [
                    column_shade(image, x, centre_x, range(top, min(top + BAND_ROWS, height - BOTTOM_ROWS)), glass)
                    for x in range(edge, width - edge)
                ],
            }
            for top in range(TOP_ROWS, height - BOTTOM_ROWS, BAND_ROWS)
        ],
        "left": [[stop(image.getpixel((x, y))) for y in range(height)] for x in range(edge)],
        "right": [[stop(image.getpixel((x, y))) for y in range(height)] for x in range(width - edge, width)],
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
    import conftest  # noqa: F401  (an offscreen Qt for drawing the faces it fits)
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    text = (
        '"""Aero caption button faces fitted to aero.msstyles by tests/aero/fit_aero_stops.py; '
        'do not edit by hand."""\n\n'
        f"EDGE = {EDGE}\n"
        f"GLYPHS = {pprint.pformat(fitted_glyphs(), width=120, compact=True)}\n"
        f"FACES = {pprint.pformat(fitted_faces(), width=120, compact=True)}\n"
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text)
    TASK_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    TASK_OUTPUT.write_text(
        '"""Aero superbar task button faces fitted to aero.msstyles by tests/aero/fit_aero_stops.py; '
        'do not edit by hand."""\n\n'
        f"TASK_FACES = {pprint.pformat(fitted_tasks(), width=120, compact=True)}\n"
        f"SHOW_DESKTOP_FACES = {pprint.pformat(fitted_show_desktop(), width=120, compact=True)}\n"
        f"GROUP_FACES = {pprint.pformat(fitted_groups(), width=120, compact=True)}\n"
    )
    print("wrote", OUTPUT, TASK_OUTPUT)
