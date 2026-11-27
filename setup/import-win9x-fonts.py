#!/usr/bin/env python3
"""Install local MS Sans Serif strikes from a Windows 95 or 98 Fonts directory."""

import argparse
import os
import shutil
import struct
from itertools import groupby
from pathlib import Path
from tempfile import TemporaryDirectory

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


def word(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def ansi_strike(path, dpi, point_size=8, face=b"MS Sans Serif"):
    """Read a CP1252 font strike from a Windows NE font library."""
    data = path.read_bytes()
    header = struct.unpack_from("<I", data, 0x3C)[0]
    if data[:2] != b"MZ" or data[header : header + 2] != b"NE":
        raise ValueError(f"{path.name} is not a Windows NE font library")
    table = header + word(data, header + 0x24)
    offset_shift = word(data, table)
    entry = table + 2
    while kind := word(data, entry):
        count = word(data, entry + 2)
        entry += 8
        if kind == 0x8008:  # RT_FONT
            for index in range(count):
                offset, length = struct.unpack_from("<HH", data, entry + index * 12)
                start = offset << offset_shift
                strike = data[start : start + (length << offset_shift)]
                face_offset = struct.unpack_from("<I", strike, 105)[0]
                if (
                    word(strike, 0) == 0x0200
                    and struct.unpack_from("<4H", strike, 66) == (0, point_size, dpi, dpi)
                    and strike[85] == 0
                    and strike[face_offset:].startswith(face + b"\0")
                ):
                    return strike
        entry += count * 12
    raise ValueError(f"{path.name} has no {point_size}-point {face.decode()} strike at {dpi} DPI")


def glyph_outline(strike, code, height, ascent, grid, bold):
    width, offset = struct.unpack_from("<HH", strike, 118 + 4 * (code - strike[95]))
    if offset + (width + 7) // 8 * height > len(strike):
        raise ValueError("Incomplete FON glyph bitmap")
    pen = TTGlyphPen(None)
    bearing = width
    for row in range(height):
        columns = {x for x in range(width) if strike[offset + x // 8 * height + row] & (0x80 >> (x % 8))}
        if bold:
            # The GDI bitmap bold face expands the ink and advance one pixel to the right.
            columns |= {x + 1 for x in columns}
        for _, run in groupby(enumerate(sorted(columns)), key=lambda pair: pair[1] - pair[0]):
            span = [x for _, x in run]
            bearing = min(bearing, span[0])
            left, right = span[0] * grid, (span[-1] + 1) * grid
            top, bottom = (ascent - row) * grid, (ascent - row - 1) * grid
            pen.moveTo((left, bottom))
            pen.lineTo((left, top))
            pen.lineTo((right, top))
            pen.lineTo((right, bottom))
            pen.closePath()
    bearing = bearing if pen.points else 0
    return pen.glyph(), ((width + int(bold)) * grid, bearing * grid)


def write_font(strike, destination, family, dpi, bold, pixel_size=11):
    # Use integer font units for that em and for each pixel of the native strike.
    grid = 64
    em = pixel_size * dpi * grid // 96
    ascent, height = word(strike, 74), word(strike, 88)
    top, bottom = ascent * grid, (ascent - height) * grid
    glyphs = {".notdef": TTGlyphPen(None).glyph()}
    metrics = {".notdef": (em, 0)}
    characters = {}
    for code in range(strike[95], strike[96] + 1):
        try:
            character = ord(bytes([code]).decode("cp1252"))
        except UnicodeDecodeError:
            continue
        name = f"uni{character:04X}"
        characters[character] = name
        glyphs[name], metrics[name] = glyph_outline(strike, code, height, ascent, grid, bold)
    builder = FontBuilder(em, isTTF=True)
    builder.font["head"].macStyle = int(bold)
    builder.setupGlyphOrder(list(glyphs))
    builder.setupCharacterMap(characters)
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=top, descent=bottom)
    style = "Bold" if bold else "Regular"
    builder.setupNameTable(
        {
            "familyName": family,
            "styleName": style,
            "uniqueFontIdentifier": f"{family} {style}",
            "fullName": f"{family} {style}",
            "psName": f"{family.replace(' ', '')}-{style}",
            "copyright": strike[6:66].split(b"\0", 1)[0].decode("cp1252"),
        }
    )
    builder.setupOS2(
        sTypoAscender=top,
        sTypoDescender=bottom,
        usWinAscent=top,
        usWinDescent=-bottom,
        usWeightClass=700 if bold else 400,
        fsSelection=32 if bold else 64,
    )
    builder.setupPost(underlinePosition=-grid, underlineThickness=grid)
    builder.save(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("edition", choices=("95", "98"))
    parser.add_argument("fonts", type=Path, help="local folder with SSERIFE.FON and SSERIFF.FON from the VM")
    args = parser.parse_args()
    try:
        sources = {file.name.lower(): file for file in args.fonts.iterdir()}
        libraries = {96: sources["sserife.fon"], 120: sources["sseriff.fon"]}
        data_home = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share"))
        destination = data_home / "fonts" / "Chicago95" / f"Windows{args.edition}"
        destination.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=destination) as scratch:
            for dpi, source in libraries.items():
                suffix = " 120 DPI" if dpi == 120 else ""
                strike = ansi_strike(source, dpi)
                family = f"Chicago95 Windows {args.edition}{suffix}"
                for bold in (False, True):
                    style = "Bold" if bold else "Regular"
                    file = Path(scratch) / f"MS-Sans-Serif-{dpi}-{style}.ttf"
                    write_font(strike, file, family, dpi, bold)
            desktop = ansi_strike(libraries[96], 96, point_size=10)
            # Keep the 96 DPI glyph grid when Qt renders at 125% scale.
            for dpi, size, suffix in ((96, 13, ""), (120, 11, " 120 DPI")):
                family = f"Chicago95 Windows {args.edition} Desktop{suffix}"
                file = Path(scratch) / f"MS-Sans-Serif-Desktop-{dpi}-Regular.ttf"
                write_font(desktop, file, family, dpi, bold=False, pixel_size=size)
            for dpi, name, suffix in ((96, "vgasys.fon", ""), (120, "8514sys.fon", " 120 DPI")):
                if name in sources:
                    system = ansi_strike(sources[name], dpi, point_size=10, face=b"System")
                    family = f"Chicago95 Windows {args.edition} System{suffix}"
                    file = Path(scratch) / f"System-{dpi}-Regular.ttf"
                    write_font(system, file, family, dpi, bold=False, pixel_size=13)
            # Windows 98's Explorer Web View uses Verdana for the HTML pane.
            if args.edition == "98":
                for name in ("verdana.ttf", "verdanab.ttf"):
                    if name in sources:
                        shutil.copyfile(sources[name], Path(scratch) / name)
            for file in Path(scratch).iterdir():
                file.replace(destination / file.name)
    except (KeyError, OSError, ValueError, struct.error) as error:
        parser.error(str(error))
    print(destination)


if __name__ == "__main__":
    main()
