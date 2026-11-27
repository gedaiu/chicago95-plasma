"""Build the 120 DPI taskbar title face from the user's imported Tahoma Bold."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from font_strikes import save_font, strike_glyph
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from PIL import ImageFont


def make_task_font(source, destination, edition):
    # GDI uses Tahoma's pixel-specific advances from hdmx and its monochrome glyphs.
    family = f"Chicago95 Windows {edition} Taskbar 120 DPI"
    size, grid = 14, 64
    em = 11 * 120 * grid // 96
    raster = ImageFont.truetype(str(source), size)
    glyphs = {".notdef": TTGlyphPen(None).glyph()}
    metrics = {".notdef": (em, 0)}
    characters = {}
    with TTFont(source) as font:
        widths = font["hdmx"].hdmx.get(size) if "hdmx" in font else None
        if widths is None:
            return False
        cmap = font.getBestCmap()
        copyright_text = font["name"].getDebugName(0) or ""
        for code in (*range(32, 127), *range(160, 256), 0x2026):
            name = cmap.get(code)
            if name is None:
                continue
            characters[code] = name
            if name in glyphs:
                continue
            mask, (left, top) = raster.getmask2(chr(code), mode="1", anchor="ls")
            width, height = mask.size
            pixels = {(left + x, -top - y - 1) for y in range(height) for x in range(width) if mask[y * width + x]}
            glyphs[name], metrics[name] = strike_glyph(pixels, widths[name], grid)
    with TemporaryDirectory(dir=destination.parent) as scratch:
        path = Path(scratch) / destination.name
        save_font(path, family, True, glyphs, characters, metrics, em, size * grid, -3 * grid, grid, copyright_text)
        path.replace(destination)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("edition", choices=("2000", "XP"))
    args = parser.parse_args()
    make_task_font(args.source, args.destination, args.edition)
