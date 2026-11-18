"""Fits the Start orb's glass outside its logo to win7dragedge.png and writes aero/plasma-style/orb.py.

usage: python3 tests/aero/fit_aero_orb.py

Outside the logo, from radius SHELL_FROM to the rim, the orb is drawn as rings RING_WIDTH wide cut into SECTORS
arcs, each the mean colour of the screenshot's pixels whose centres lie in it. Windows 7's orb is lit from above,
catches a bright reflection at its upper sides and glows cyan at its foot, so the colour follows the angle round the
orb. Drawn, the arcs' smoothed edges mix neighbours, so the fit then corrects each arc by its drawn mean's error,
ROUNDS times.
"""

import math
import pprint
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent), str(Path(__file__).resolve().parent)]
import conftest  # noqa: E402, F401  (an offscreen Qt for drawing)
from PIL import Image  # noqa: E402
from reference import screenshot  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
OUTPUT = REPO / "aero/plasma-style/orb.py"
CENTRE = (27, 20)
SHELL_FROM, RIM = 14, 18
SECTORS = 32
RING_WIDTH = 0.5
RINGS = round((RIM - SHELL_FROM) / RING_WIDTH)


ROUNDS = 12


def cells():
    """Each orb pixel's (ring, sector) outside the logo, by the pixel's centre."""
    cx, cy = CENTRE
    found = {}
    for x in range(58):
        for y in range(40):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            ring = math.floor((math.hypot(dx, dy) - SHELL_FROM) / RING_WIDTH)
            if 0 <= ring < RINGS:
                sector = int((math.atan2(dy, dx) % math.tau) / math.tau * SECTORS) % SECTORS
                found.setdefault((ring, sector), []).append((x, y))
    return found


def mean(image, pixels):
    return [sum(channel) / len(pixels) for channel in zip(*(image.getpixel(pixel) for pixel in pixels), strict=True)]


def hex_colour(channels):
    return "#" + "".join(f"{min(255, max(0, round(channel))):02X}" for channel in channels)


def drawn(generator, behind):
    from test_aero_buttons import rendered

    return Image.alpha_composite(behind, rendered(generator.orb_svg(), (58, 40))).convert("RGB")


def shell():
    """Each ring's sector colours, clockwise from the right (east) as SVG's angles run."""
    windows_7 = screenshot("win7dragedge")
    orb = windows_7.crop((0, 728, 58, 768))
    behind = windows_7.crop((2, 728, 3, 768)).resize((58, 40)).convert("RGBA")
    found = cells()
    target = {cell: mean(orb, pixels) for cell, pixels in found.items()}
    for ring in range(RINGS):  # a cell no pixel centre falls in takes the same sector one ring in (or out)
        for sector in range(SECTORS):
            if (ring, sector) not in target:
                neighbour = next((ring + step, sector) for step in (-1, 1, -2, 2) if (ring + step, sector) in found)
                target[ring, sector] = mean(orb, found[neighbour])
    colours = {cell: list(value) for cell, value in target.items()}
    generator = load_generator()
    for _ in range(ROUNDS):
        generator.orb.SHELL = [
            [hex_colour(colours[ring, sector]) for sector in range(SECTORS)] for ring in range(RINGS)
        ]
        ours = drawn(generator, behind)
        for cell, pixels in found.items():
            colours[cell] = [c + t - o for c, t, o in zip(colours[cell], target[cell], mean(ours, pixels), strict=True)]
    return [[hex_colour(colours[ring, sector]) for sector in range(SECTORS)] for ring in range(RINGS)]


def load_generator():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "make_aero_plasmastyle", REPO / "aero/plasma-style/make_aero_plasmastyle.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    OUTPUT.write_text(
        '"""The Start orb\'s glass outside its logo, fitted to win7dragedge.png by tests/aero/fit_aero_orb.py;\n'
        'do not edit by hand."""\n\n'
        f"CENTRE = {CENTRE}\nSHELL_FROM = {SHELL_FROM}\nRING_WIDTH = {RING_WIDTH}\nSECTORS = {SECTORS}\n"
        f"SHELL = {pprint.pformat(shell(), width=120, compact=True)}\n"
    )
    print("wrote", OUTPUT)
