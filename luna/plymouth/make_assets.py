"""Render the stock XP SP3 wordmark and progress artwork at 1x and 2x."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "images"))

import render_logo  # noqa: E402

FOLDER = Path(__file__).parent / "Chicago95-XP"
WORDMARK_WIDTH = 244
TROUGH_UNITS = (126, 15)
BLOCK_UNITS = (22, 9)
SPLASH = Path(__file__).resolve().parents[1] / "splash"
logo_viewbox = render_logo.view_box_size(render_logo.LIGHT_SVG)
SIZES = {
    "logo": (WORDMARK_WIDTH, round(WORDMARK_WIDTH * logo_viewbox[1] / logo_viewbox[0])),
    "trough": TROUGH_UNITS,
    "block": BLOCK_UNITS,
}
MULTIPLIERS = {"": 1, "@2x": 2}


def draw_logo(multiplier):
    return render_logo.render_fitted(render_logo.LIGHT_SVG, size_at("logo", multiplier))


def size_at(name, multiplier):
    return tuple(side * multiplier for side in SIZES[name])


def draw_trough(multiplier):
    return render_logo.render_to_image((SPLASH / "boot-trough.svg").read_bytes(), *size_at("trough", multiplier))


def draw_block(multiplier):
    return render_logo.render_to_image((SPLASH / "boot-blocks.svg").read_bytes(), *size_at("block", multiplier))


DRAWERS = {"logo": draw_logo, "trough": draw_trough, "block": draw_block}


def write_all():
    FOLDER.mkdir(parents=True, exist_ok=True)
    for name, drawer in DRAWERS.items():
        for suffix, multiplier in MULTIPLIERS.items():
            drawer(multiplier).save(FOLDER / f"{name}{suffix}.png")


if __name__ == "__main__":
    write_all()
