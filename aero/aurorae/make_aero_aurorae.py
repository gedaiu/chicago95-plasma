#!/usr/bin/env python3
"""Builds the Chicago95Aero window decoration: the Windows 7 Aero glass frame for KWin's Aurorae engine.

usage: python3 aero/aurorae/make_aero_aurorae.py [--out DIR]

The frame is translucent glass that KWin's blur effect blurs behind (the mask-* elements mark the region), edged with
the lines DWM's atlas draws (aero/palette.py). The caption buttons are vector faces fitted to the atlas
(aero/aurorae/stops.py, written by tests/aero/fit_aero_stops.py).
"""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stops = load("aero_aurorae_stops", HERE / "stops.py")


def number(value):
    return f"{value:g}"


def paint(colour, alpha):
    return f'stop-color="{colour}" stop-opacity="{number(round(alpha / 255, 3))}"'


def vertical_gradient(gradient_id, column):
    """One stop per pixel row, held across the row: the sprite column as a gradient that scales smoothly."""
    rows = len(column)
    stops_markup = "".join(
        f'<stop offset="{number(round(edge / rows, 4))}" {paint(*column[row])}/>'
        for row in range(rows)
        for edge in (row, row + 1)
    )
    return f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1">{stops_markup}</linearGradient>'


def shade_gradient(gradient_id, shade):
    columns = len(shade)
    stops_markup = "".join(
        f'<stop offset="{number(round(edge / columns, 4))}" stop-color="#000000" '
        f'stop-opacity="{number(shade[column])}"/>'
        for column in range(columns)
        for edge in (column, column + 1)
    )
    return f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="1" y2="0">{stops_markup}</linearGradient>'


def face_svg(face, prefix="f", origin=(0, 0)):
    """A button face at its sprite size: the centre column's gradient, the side shading, and the edge columns."""
    width, height = face["size"]
    edge = len(face["left"])
    x0, y0 = origin
    inner = width - 2 * edge
    definitions = [vertical_gradient(f"{prefix}r", face["rows"])]
    shapes = [f'<rect x="{x0 + edge}" y="{y0}" width="{inner}" height="{height}" fill="url(#{prefix}r)"/>']
    for index, band in enumerate(face["bands"]):
        top, bottom = band["rows"]
        definitions.append(shade_gradient(f"{prefix}s{index}", band["shade"]))
        shapes.append(
            f'<rect x="{x0 + edge}" y="{y0 + top}" width="{inner}" height="{bottom - top}" '
            f'fill="url(#{prefix}s{index})"/>'
        )
    for side, offset in (("left", 0), ("right", width - edge)):
        for index, column in enumerate(face[side]):
            gradient_id = f"{prefix}{side[0]}{index}"
            definitions.append(vertical_gradient(gradient_id, column))
            shapes.append(
                f'<rect x="{x0 + offset + index}" y="{y0}" width="1" height="{height}" fill="url(#{gradient_id})"/>'
            )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f"<defs>{''.join(definitions)}</defs>{''.join(shapes)}</svg>"
    )


def rect(x, y, width, height):
    return f"M{x},{y}h{width}v{height}h{-width}z"


# Glyph shapes in their 96 DPI sprite's pixel coordinates (BUTTON<KIND>GLYPH96): (box, layers drawn in order), each
# layer an "outline" or "body" path, filled even-odd so a ring is an outer and an inner rectangle.
CLOSE_ARMS = ("M2.1,3H4.9L10.9,11H8.1z", "M8.1,3H10.9L4.9,11H2.1z")
GLYPH_SHAPES = {
    "close": ((13, 14), [("stroke", arm) for arm in CLOSE_ARMS] + [("body", arm) for arm in CLOSE_ARMS]),
    "minimize": ((14, 14), [("outline", rect(0, 7, 14, 5)), ("body", rect(2, 8, 10, 3))]),
    "maximize": (
        (16, 14),
        [("outline", rect(3, 2, 13, 10) + rect(7, 6, 4, 2)), ("body", rect(4, 3, 10, 8) + rect(6, 5, 6, 4))],
    ),
    "restore": (
        (14, 14),
        [
            ("outline", rect(3, 0, 11, 11)),
            ("body", rect(4, 2, 8, 8)),
            ("outline", rect(0, 3, 11, 11) + rect(5, 7, 2, 2)),
            ("body", rect(2, 4, 8, 8) + rect(4, 6, 4, 4)),
        ],
    ),
}
CLOSE_OUTLINE_WIDTH = 2


def glyph_markup(kind, colours, prefix="g"):
    """A glyph's shapes: dark outline under a white body that darkens towards its foot."""
    (width, height), layers = GLYPH_SHAPES[kind]
    outline, outline_alpha = colours["outline"]
    body_id = f"{prefix}{kind}"
    gradient = (
        f'<linearGradient id="{body_id}" x1="0" y1="0" x2="0" y2="{height}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" {paint(*colours["top"])}/><stop offset="1" {paint(*colours["bottom"])}/></linearGradient>'
    )
    opacity = number(round(outline_alpha / 255, 3))
    shapes = {
        "outline": lambda path: f'<path d="{path}" fill="{outline}" fill-opacity="{opacity}" fill-rule="evenodd"/>',
        "stroke": lambda path: (
            f'<path d="{path}" fill="none" stroke="{outline}" stroke-opacity="{opacity}" '
            f'stroke-width="{CLOSE_OUTLINE_WIDTH}" stroke-linejoin="round"/>'
        ),
        "body": lambda path: f'<path d="{path}" fill="url(#{body_id})" fill-rule="evenodd"/>',
    }
    return gradient, "".join(shapes[layer](path) for layer, path in layers)


def glyph_svg(kind, colours):
    (width, height), _ = GLYPH_SHAPES[kind]
    gradient, shapes = glyph_markup(kind, colours)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f"<defs>{gradient}</defs>{shapes}</svg>"
    )
