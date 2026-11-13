"""Winamp (qmmp's skinned player) at the screen's scale.

    qmmp_double_size.py ~/.config/qmmp/qmmp.conf SCALE

qmmp runs unscaled under X11 (its skins are pixel art, and it moves its own windows), so on a scaled screen its
275-pixel player is smaller than everything else. A skin pixel is drawn as the screen's scale rounded to whole pixels,
crisp where a fractional scale would size the pixels unevenly: Winamp's own Double Size, the largest qmmp has, from
1.5x up. qmmp keeps the equalizer's and the playlist's positions as they were, so they move as far from the main window
as the size changes, to stay docked, as switching Double Size in the player does.
"""

import math
import re
import sys
from pathlib import Path

POINT = re.compile(r"^(eq_pos|pl_pos|mw_pos)=@Point\((-?\d+) (-?\d+)\)$")
SIZE = re.compile(r"^double_size=(true|false)$")
LARGEST_PIXEL = 2


def skin_pixel(scale):
    """The screen's scale rounded half up to whole pixels, from single to Double Size."""
    return min(LARGEST_PIXEL, max(1, math.floor(float(scale) + 0.5)))


def skinned_section(lines):
    """The [Skinned] section's line range; the shortcuts section has a double_size key of its own."""
    start = next((index for index, line in enumerate(lines) if line.strip() == "[Skinned]"), None)
    if start is None:
        return None
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("[")), len(lines))
    return start, end


def sized(text, pixel):
    double = "true" if pixel == LARGEST_PIXEL else "false"
    lines = text.splitlines()
    section = skinned_section(lines)
    if section is None:
        return text + ("\n" if text and not text.endswith("\n") else "") + f"[Skinned]\ndouble_size={double}\n"
    start, end = section
    current = next((match[1] for line in lines[start:end] if (match := SIZE.match(line))), "false")
    if current == double:
        return text
    ratio = 2 if double == "true" else 0.5
    points = {match[1]: (int(match[2]), int(match[3])) for line in lines[start:end] if (match := POINT.match(line))}
    main_x, main_y = points.get("mw_pos", (0, 0))
    for index in range(start, end):
        match = POINT.match(lines[index])
        if SIZE.match(lines[index]):
            lines[index] = f"double_size={double}"
        elif match and match[1] != "mw_pos":
            x = main_x + round(ratio * (int(match[2]) - main_x))
            y = main_y + round(ratio * (int(match[3]) - main_y))
            lines[index] = f"{match[1]}=@Point({x} {y})"
    if not any(SIZE.match(line) for line in lines[start:end]):
        lines.insert(start + 1, f"double_size={double}")
    return "\n".join(lines) + "\n"


def main():
    conf, scale = Path(sys.argv[1]), sys.argv[2]
    conf.parent.mkdir(parents=True, exist_ok=True)
    conf.write_text(sized(conf.read_text() if conf.exists() else "", skin_pixel(scale)))


if __name__ == "__main__":
    main()
