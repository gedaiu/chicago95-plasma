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
