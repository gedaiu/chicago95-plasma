#!/usr/bin/env python3
"""Gives a font's no-break space (U+00A0) the same glyph and width as its space.

MS W98 UI Regular ships a no-break space a third as wide as its space. Editors built on
Monaco (VS Code's commit box, settings fields) draw every space as U+00A0, so words ran
together there while ordinary text looked fine.

    fix-font-spaces.py FONT...   rewrites each font in place; prints what it changed
"""
import sys

from fontTools.ttLib import TTFont

NO_BREAK_SPACE = 0xA0


def fix_no_break_space(path):
    font = TTFont(path)
    cmap = font.getBestCmap()
    space, no_break = cmap.get(0x20), cmap.get(NO_BREAK_SPACE)
    if space is None or no_break is None or space == no_break:
        return None
    hmtx = font["hmtx"]
    space_width, no_break_width = hmtx[space][0], hmtx[no_break][0]
    if space_width == no_break_width:
        return None
    hmtx[no_break] = hmtx[space]
    if "CFF " in font:
        charstrings = font["CFF "].cff.topDictIndex[0].CharStrings
        charstrings[space].decompile()
        no_break_glyph = charstrings[no_break]
        no_break_glyph.program = list(charstrings[space].program)
        no_break_glyph.bytecode = None  # otherwise fontTools writes the old compiled glyph back unchanged
    font.save(path)
    return no_break_width, space_width


def main(paths):
    for path in paths:
        change = fix_no_break_space(path)
        if change:
            print(f"{path}: no-break space {change[0]} -> {change[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
