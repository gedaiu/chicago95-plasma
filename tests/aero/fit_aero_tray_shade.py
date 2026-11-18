"""Fits Windows 7's darkening of the bar at its notification area to win7screenres.png and writes
aero/plasma-style/trayshade.py.

usage: python3 tests/aero/fit_aero_tray_shade.py

Explorer, not the theme, darkens the bar from before the notification area to the screen's edge, as it does behind
the orb. Measured over the bar's last WIDTH columns, in bands of BAND rows: each STEP columns, black's opacity over the
streak-free bar (tests/aero/aero_model.plain_bar) from the median of the cell's pixels, leaving out icons and the
clock's lettering (pixels more than 30 levels from the cell's median); a cell less than half bar, mostly
icon (darker than DARKEST) or mostly lettering (lighter than the bar) takes its left
neighbour's value, or the one above. Behind the Show desktop strip,
its last STRIP columns, the bar is lighter instead: solved through the strip's sprite (with AERO_MSSTYLES_DIR), as
white's opacity per band, LIGHT.
"""

import pprint
import statistics
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parent.parent)]
from aero_model import plain_bar  # noqa: E402
from reference import screenshot  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "aero/plasma-style/trayshade.py"
WIDTH, STRIP = 216, 15
TOP, BAND, STEP = 2, 2, 8
DARKEST = 0.35  # the darkening reaches 0.28 at most in every reference


def opacity(image, glass, x0, y0):
    left = 1024 - WIDTH
    cell = [(x, y) for x in range(x0, min(x0 + STEP, WIDTH - STRIP)) for y in range(y0, min(y0 + BAND, 40))]
    pixels = [image.getpixel((left + x, 728 + y)) for x, y in cell]
    middle = [statistics.median(channel) for channel in zip(*pixels, strict=True)]
    kept = [
        (pixel, y)
        for pixel, (_, y) in zip(pixels, cell, strict=True)
        if max(abs(a - b) for a, b in zip(pixel, middle, strict=True)) <= 30
    ]
    if 2 * len(kept) < len(cell):  # mostly icon or lettering, with their smoothed edges
        return None
    darkening = statistics.median(1 - sum(pixel) / sum(glass[y]) for pixel, y in kept)
    # Lighter than the bar is the clock's lettering, and darker than DARKEST an icon: neither is the darkening.
    return round(darkening * 255) if 0 <= darkening <= DARKEST else None


def bands():
    image, glass = screenshot("win7screenres"), plain_bar("win7screenres")
    rows = []
    for y0 in range(TOP, 40, BAND):
        row = [opacity(image, glass, x0, y0) for x0 in range(0, WIDTH - STRIP, STEP)]
        for index, value in enumerate(row):
            if value is None:
                row[index] = row[index - 1] if index else rows[-1][index]
        rows.append(row)
    return rows


def lightening():
    """White's opacity behind the Show desktop strip per band: the bar there, solved through the strip's normal
    sprite as Windows draws it, against the streak-free bar, over its middle columns where the sprite lets it show."""
    from fit_aero_stops import show_desktop_image

    sprite, image, glass = show_desktop_image(0), screenshot("win7screenres"), plain_bar("win7screenres")
    bands_light = []
    for y0 in range(TOP, 40, BAND):
        values = []
        for x in range(3, STRIP - 3):
            for y in range(y0, min(y0 + BAND, 40)):
                *colour, alpha = sprite.getpixel((x, y))
                if alpha > 242:
                    continue
                opacity = alpha / 255
                seen = image.getpixel((1024 - STRIP + x, 728 + y))
                behind = sum((s - c * opacity) / (1 - opacity) for s, c in zip(seen, colour, strict=True))
                values.append((behind - sum(glass[y])) / (765 - sum(glass[y])))
        bands_light.append(max(0, round(statistics.median(values) * 255)) if values else 0)
    return bands_light


if __name__ == "__main__":
    OUTPUT.write_text(
        '"""Windows 7\'s darkening of the bar at its notification area, fitted to win7screenres.png by\n'
        'tests/aero/fit_aero_tray_shade.py; do not edit by hand."""\n\n'
        f"WIDTH = {WIDTH}\nSTRIP = {STRIP}\nBAND = {BAND}\nSTEP = {STEP}\n"
        f"OPACITY = {pprint.pformat(bands(), width=120, compact=True)}\n"
        f"LIGHT = {lightening()}\n"
    )
    print("wrote", OUTPUT)
