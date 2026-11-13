"""Winamp (qmmp's skinned player) at Double Size, for screens scaled 1.5x or more.

    qmmp_double_size.py ~/.config/qmmp/qmmp.conf

qmmp runs unscaled under X11 (its skins are pixel art, and it moves its own windows), so on a 1.5x screen its
275-pixel player is a third smaller than everything else. Winamp's own Double Size draws every skin pixel as a 2x2
block: crisp, where a fractional scale would size the pixels unevenly. qmmp keeps the equalizer's and the playlist's
positions as they were, so they move twice as far from the main window to stay docked, as switching Double Size in the
player does.
"""

import re
import sys
from pathlib import Path

POINT = re.compile(r"^(eq_pos|pl_pos|mw_pos)=@Point\((-?\d+) (-?\d+)\)$")


def skinned_section(lines):
    """The [Skinned] section's line range; the shortcuts section has a double_size key of its own."""
    start = next((index for index, line in enumerate(lines) if line.strip() == "[Skinned]"), None)
    if start is None:
        return None
    end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("[")), len(lines))
    return start, end


def doubled(text):
    lines = text.splitlines()
    section = skinned_section(lines)
    if section is None:
        return text + ("\n" if text and not text.endswith("\n") else "") + "[Skinned]\ndouble_size=true\n"
    start, end = section
    if "double_size=true" in lines[start:end]:
        return text
    points = {match[1]: (int(match[2]), int(match[3])) for line in lines[start:end] if (match := POINT.match(line))}
    main_x, main_y = points.get("mw_pos", (0, 0))
    for index in range(start, end):
        match = POINT.match(lines[index])
        if lines[index] == "double_size=false":
            lines[index] = "double_size=true"
        elif match and match[1] != "mw_pos":
            x, y = int(match[2]), int(match[3])
            lines[index] = f"{match[1]}=@Point({main_x + 2 * (x - main_x)} {main_y + 2 * (y - main_y)})"
    if "double_size=true" not in lines[start:end]:
        lines.insert(start + 1, "double_size=true")
    return "\n".join(lines) + "\n"


def main():
    conf = Path(sys.argv[1])
    conf.parent.mkdir(parents=True, exist_ok=True)
    conf.write_text(doubled(conf.read_text() if conf.exists() else ""))


if __name__ == "__main__":
    main()
