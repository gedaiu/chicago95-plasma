"""Fits DWM's glass streaks (aero.msstyles' DWMWindow REFLECTIONMAP) and writes aero/reflection.py.

usage: AERO_MSSTYLES_DIR=... python3 tests/aero/fit_aero_reflection.py

DWM lays the map over all glass, stretched to the screen: on win7screenres.png's bar, the map at 75% (the theme's
OPACITY for the taskbar) predicts the streaks with a correlation of 0.998. The map is straight bands, so it is one
profile across them at ANGLE: each 1-pixel step across, the mean of its pixels' light (colour times alpha) and alpha,
as a colour and opacity. Runs whose colour and opacity change less than TOLERANCE are merged, so the gradient keeps
only the stops that shape it. Only those numbers are committed; the bitmap stays outside the repository.
"""

import math
import pprint
import sys
from pathlib import Path

import numpy

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parent.parent)]
from aero_sprites import part, sprite_dir, straight  # noqa: E402
from PIL import Image  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "aero/reflection.py"
ANGLES = [15 + step / 4 for step in range(121)]  # degrees from vertical the bands lean right
TOLERANCE = 0.25  # levels of light and alpha, out of 255
OPACITY = 75  # DWMWindow REFLECTIONMAP's OPACITY for the taskbar's state, which the bar's streaks match


def reflection_map():
    piece = part("DWMWindow", "REFLECTIONMAP")
    return straight(Image.open(sprite_dir() / piece.image_file).convert("RGBA")).crop(piece.atlas_rect)


def profile(light, alpha, angle):
    """(position across the bands, light, alpha) per 1-pixel step, and the profile's mean squared error over the map;
    light is grey times alpha, both 0..255."""
    height, width = alpha.shape
    rows, columns = numpy.mgrid[0:height, 0:width]
    lean = math.radians(angle)
    across = columns * math.cos(lean) - rows * math.sin(lean)
    start = across.min()
    steps = numpy.round(across - start).astype(int)
    counts = numpy.bincount(steps.ravel())
    mean_light = numpy.bincount(steps.ravel(), light.ravel()) / numpy.maximum(counts, 1)
    mean_alpha = numpy.bincount(steps.ravel(), alpha.ravel()) / numpy.maximum(counts, 1)
    error = float(((light - mean_light[steps]) ** 2).mean())
    return [
        (index + start, mean_light[index], mean_alpha[index]) for index in range(len(counts)) if counts[index]
    ], error


def merged(points):
    """Fewer stops: a point is dropped while the straight line between its kept neighbours stays within TOLERANCE
    levels of its light and alpha."""
    kept = [points[0]]
    for index in range(1, len(points) - 1):
        previous, following = kept[-1], points[index + 1]
        share = (points[index][0] - previous[0]) / (following[0] - previous[0])
        if any(abs(previous[k] + (following[k] - previous[k]) * share - points[index][k]) > TOLERANCE for k in (1, 2)):
            kept.append(points[index])
    return [*kept, points[-1]]


def fit():
    image = numpy.asarray(reflection_map(), dtype=float)
    alpha = image[..., 3]
    light = image[..., :3].mean(axis=2) * alpha / 255
    coarse = min(ANGLES[::8], key=lambda angle: profile(light, alpha, angle)[1])
    angle = min((a for a in ANGLES if abs(a - coarse) <= 2), key=lambda candidate: profile(light, alpha, candidate)[1])
    points, _ = profile(light, alpha, angle)
    stops = [
        (
            round(float(position), 2),
            round(float(grey_light / opacity * 255)) if opacity else 0,
            round(float(opacity), 2),
        )
        for position, grey_light, opacity in merged(points)
    ]
    return (image.shape[1], image.shape[0]), angle, stops


if __name__ == "__main__":
    size, angle, stops = fit()
    OUTPUT.write_text(
        '"""DWM\'s glass streaks, fitted to aero.msstyles\' DWMWindow REFLECTIONMAP by\n'
        "tests/aero/fit_aero_reflection.py; do not edit by hand. The map, MAP_SIZE, is stretched over the screen;\n"
        "its bands lean ANGLE degrees from vertical, and STOPS run across them: (position, grey level, alpha out of\n"
        '255), at OPACITY percent."""\n\n'
        f"MAP_SIZE = {size}\nANGLE = {angle}\nOPACITY = {OPACITY}\n"
        f"STOPS = {pprint.pformat(stops, width=120, compact=True)}\n"
    )
    print("wrote", OUTPUT, len(stops), "stops at", angle)
