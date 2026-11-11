#!/usr/bin/env python3
"""Draws one 8x8 tile of a desktop pattern: set bits black, the rest in the background colour.

python3 setup/background_pattern.py diagonal "#008080" pattern.png
"""

import sys

from PySide6.QtGui import QColor, QImage

TILE_SIZE = 8
PATTERNS = {
    "checks": [0xF0, 0xF0, 0xF0, 0xF0, 0x0F, 0x0F, 0x0F, 0x0F],
    "diagonal": [0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01],
    "grid": [0xFF, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80],
    "dots": [0xAA, 0x00, 0xAA, 0x00, 0xAA, 0x00, 0xAA, 0x00],
}


def pattern_png(rows, colour, path):
    tile = QImage(TILE_SIZE, TILE_SIZE, QImage.Format_RGB32)
    tile.fill(QColor(colour))
    for y, row in enumerate(rows):
        for x in range(TILE_SIZE):
            if row & (0x80 >> x):
                tile.setPixelColor(x, y, QColor("black"))
    if not tile.save(str(path)):
        raise SystemExit(f"cannot write {path}")


if __name__ == "__main__":
    pattern_png(PATTERNS[sys.argv[1]], sys.argv[2], sys.argv[3])
