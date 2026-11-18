"""Fits the notification area's "show hidden icons" button to aero.msstyles and writes aero/plasma-style/traybutton.py.

usage: AERO_MSSTYLES_DIR=~/src/aero-msstyles python3 tests/aero/fit_aero_tray_button.py

The hot and pressed faces are fitted as the task faces are (fit_aero_stops.fit_state), from the sprite with its glyph
covered by its glyph-free column 3. The glyph's colours are its middle column's, row by row. The shadow is layers of
the triangle grown and moved down, in black: each layer's move, growth and opacity found by coordinate descent,
drawing every state over the bar and comparing it with its sprite.
"""

import importlib.util
import pprint
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parent.parent)]
from fit_aero_stops import BAR_GLASS, TRAY_BUTTON_PARTS, TRAY_BUTTON_STATES, fit_state, stop, tray_button_image  # noqa: E402
from PIL import Image  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "aero/plasma-style/traybutton.py"
CLEAR_COLUMN = 3  # the face's first column clear of the glyph and its shadow; the face is level from here to 17
SHADOW_START = [(0.5, 0.75, 0.25), (1.5, 1.0, 0.1)]
STEPS = (0.25, 0.25, 0.02)


def glyphless(image):
    covered = image.copy()
    for x in range(CLEAR_COLUMN + 1, image.width - CLEAR_COLUMN):
        for y in range(image.height):
            covered.putpixel((x, y), image.getpixel((CLEAR_COLUMN, y)))
    return covered


def fitted_face(image):
    """The face, without the side shading bands a face level across leaves empty."""
    face = fit_state(glyphless(image), BAR_GLASS, CLEAR_COLUMN)
    return {**face, "bands": [band for band in face["bands"] if any(band["shade"])]}


def fitted_faces():
    return {
        f"{kind}{state}": fitted_face(tray_button_image(kind, state))
        for kind in TRAY_BUTTON_PARTS
        for state in TRAY_BUTTON_STATES[1:]
    }


def glyph_rows(kind):
    image = tray_button_image(kind, "normal")
    middle = image.width // 2
    return [
        (y, stop(image.getpixel((middle, y)))[0]) for y in range(image.height) if image.getpixel((middle, y))[3] == 255
    ]


def error(generator, shadow):
    from test_aero_buttons import rendered

    total = 0
    for kind in TRAY_BUTTON_PARTS:
        for state in TRAY_BUTTON_STATES:
            sprite = tray_button_image(kind, state)
            ours = rendered(generator.tray_button_svg(f"{kind}{state}", shadow), sprite.size)
            for image in (ours, sprite):
                base = Image.new("RGBA", sprite.size, (*BAR_GLASS, 255))
                base.alpha_composite(image)
                image.info["seen"] = base.convert("RGB")
            total += sum(
                max(
                    abs(a - b)
                    for a, b in zip(ours.info["seen"].getpixel(xy), sprite.info["seen"].getpixel(xy), strict=True)
                )
                for xy in ((x, y) for x in range(sprite.width) for y in range(sprite.height))
            )
    return total


def fitted_shadow(generator):
    shadow = [list(layer) for layer in SHADOW_START]
    best = error(generator, shadow)
    improved = True
    while improved:
        improved = False
        for layer in shadow:
            for index, step in enumerate(STEPS):
                for sign in (1, -1):
                    while True:
                        layer[index] += sign * step
                        candidate = error(generator, shadow)
                        if candidate < best and layer[2] > 0:
                            best, improved = candidate, True
                            continue
                        layer[index] -= sign * step
                        break
    return [tuple(round(value, 2) for value in layer) for layer in shadow]


def write(faces, rows, shadow):
    OUTPUT.write_text(
        '"""The notification area\'s "show hidden icons" button fitted to aero.msstyles by\n'
        'tests/aero/fit_aero_tray_button.py; do not edit by hand."""\n\n'
        f"FACES = {pprint.pformat(faces, width=120, compact=True)}\n"
        f"GLYPH_ROWS = {pprint.pformat(rows, width=120, compact=True)}\n"
        f"SHADOW = {shadow}\n"
    )


if __name__ == "__main__":
    import conftest  # noqa: F401  (an offscreen Qt for drawing the button it fits)
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    faces, rows = fitted_faces(), {kind: glyph_rows(kind) for kind in TRAY_BUTTON_PARTS}
    write(faces, rows, SHADOW_START)
    spec = importlib.util.spec_from_file_location(
        "make_aero_plasmastyle", REPO / "aero/plasma-style/make_aero_plasmastyle.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    shadow = fitted_shadow(generator)
    write(faces, rows, shadow)
    print("wrote", OUTPUT, "error", error(generator, shadow))
