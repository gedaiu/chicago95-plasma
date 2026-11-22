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


def runs(values):
    """(start, end, value) for each run of equal neighbouring values."""
    start = 0
    for index in range(1, len(values) + 1):
        if index == len(values) or values[index] != values[start]:
            yield start, index, values[start]
            start = index


def gradient_knots(samples, tolerance=4):
    """Keep the ends and bends of a piecewise-linear colour ramp."""
    if len(samples) == 1 or all(sample == samples[0] for sample in samples):
        return [0]
    kept = [0]

    def split(start, end):
        if end > start + 1:
            first, last = samples[start], samples[end]
            worst, pivot = 0, start
            for i in range(start + 1, end):
                t = (i - start) / (end - start)
                error = max(abs(v - (a + (b - a) * t)) for a, b, v in zip(first, last, samples[i], strict=True))
                if error > worst:
                    worst, pivot = error, i
            if worst > tolerance:
                split(start, pivot)
                split(pivot, end)
                return
        kept.append(end)

    split(0, len(samples) - 1)
    return kept


def gradient_stops(values, attributes, offset=0, total=None):
    """Fit ramps through pixel centres, retaining abrupt bevels as hard stops."""
    samples = []
    for value in values:
        if isinstance(value, (float, int)):
            samples.append((value * 255,))
        else:
            colour, alpha = value
            rgb = bytes.fromhex(colour.lstrip("#"))
            samples.append(tuple(v * alpha / 255 for v in rgb) + (alpha,))
    indices = gradient_knots(samples)
    stops = []
    for k, i in enumerate(indices):
        # A large adjacent jump is a painted edge between two surfaces.
        if k and i == indices[k - 1] + 1 and max(abs(a-b) for a,b in zip(samples[i-1],samples[i],strict=True)) > 48:
            stops.extend(((i, values[i-1]), (i, values[i])))
        stops.append((i + .5, values[i]))
    length = total or len(values)
    return "".join(f'<stop offset="{number(round((offset + x) / length, 5))}" {attributes(value)}/>' for x,value in stops)


def vertical_gradient(gradient_id, column):
    """Fit the fill or border gradient along the vertical axis."""
    return (
        f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1">'
        f"{gradient_stops(column, lambda value: paint(*value))}</linearGradient>"
    )


def shade_gradient(gradient_id, shade):
    return (
        f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="1" y2="0">'
        f"{gradient_stops(shade, lambda value: f'stop-color="#000000" stop-opacity="{number(value)}"')}"
        "</linearGradient>"
    )


def face_markup(face, prefix, origin):
    """A button face at its sprite size: the centre column's gradient, the side shading, and the edge columns."""
    width, height = face["size"]
    edge = len(face["left"])
    x0, y0 = origin
    inner = width - 2 * edge
    definitions = [vertical_gradient(f"{prefix}r", face["rows"])]
    shapes = [f'<rect x="{x0 + edge}" y="{y0}" width="{inner}" height="{height}" fill="url(#{prefix}r)"/>']
    for index, band in enumerate(face["bands"]):
        top, bottom = band["rows"]
        if not any(band["shade"]):
            continue
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
    return "".join(definitions), "".join(shapes)


def face_svg(face):
    width, height = face["size"]
    definitions, shapes = face_markup(face, "f", (0, 0))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f"<defs>{definitions}</defs>{shapes}</svg>"
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


def glyph_markup(kind, colours, prefix="g", origin=(0, 0)):
    """A glyph's shapes at origin: dark outline under a white body that darkens towards its foot."""
    (_, height), layers = GLYPH_SHAPES[kind]
    x0, y0 = origin
    outline, outline_alpha = colours["outline"]
    body_id = f"{prefix}{kind}"
    gradient = (
        f'<linearGradient id="{body_id}" x1="0" y1="{y0}" x2="0" y2="{y0 + height}" gradientUnits="userSpaceOnUse">'
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
    drawn = "".join(shapes[layer](path) for layer, path in layers)
    return gradient, f'<g transform="translate({number(x0)},{number(y0)})">{drawn}</g>'


def glyph_svg(kind, colours):
    (width, height), _ = GLYPH_SHAPES[kind]
    gradient, shapes = glyph_markup(kind, colours)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f"<defs>{gradient}</defs>{shapes}</svg>"
    )


palette = load("aero_palette", HERE.parent / "palette.py")

SIDE, TOP, MIDDLE = palette.BORDER, palette.TITLE_HEIGHT, 16
FRAME_W, FRAME_H = 2 * SIDE + MIDDLE, TOP + MIDDLE + SIDE
MAX_ROWS = TOP - SIDE  # a maximized window keeps the caption without the border pushed off screen
GAP = 8
PIECES = ("topleft", "top", "topright", "left", "center", "right", "bottomleft", "bottom", "bottomright")


def piece_boxes(x0):
    """The nine-slice pieces of a frame drawn at x0, as (name, (left, top, right, bottom))."""
    columns = (x0, x0 + SIDE, x0 + SIDE + MIDDLE, x0 + FRAME_W)
    rows = (0, TOP, TOP + MIDDLE, FRAME_H)
    return [
        (PIECES[3 * row + column], (columns[column], rows[row], columns[column + 1], rows[row + 1]))
        for row in range(3)
        for column in range(3)
    ]


def rounded_path(box, radii):
    """A box with its corners (top left, top right, bottom right, bottom left) rounded by radii."""
    left, top, right, bottom = box
    top_left, top_right, bottom_right, bottom_left = radii
    return (
        f"M{left},{top + top_left}"
        + (f"A{top_left},{top_left} 0 0 1 {left + top_left},{top}" if top_left else "")
        + f"H{right - top_right}"
        + (f"A{top_right},{top_right} 0 0 1 {right},{top + top_right}" if top_right else "")
        + f"V{bottom - bottom_right}"
        + (f"A{bottom_right},{bottom_right} 0 0 1 {right - bottom_right},{bottom}" if bottom_right else "")
        + f"H{left + bottom_left}"
        + (f"A{bottom_left},{bottom_left} 0 0 1 {left},{bottom - bottom_left}" if bottom_left else "")
        + "z"
    )


def clipped(shape, piece):
    """The part of a rounded box inside a piece: their overlap, keeping a corner's rounding where the piece holds it."""
    box, radii = shape
    left, top = max(box[0], piece[0]), max(box[1], piece[1])
    right, bottom = min(box[2], piece[2]), min(box[3], piece[3])
    if right <= left or bottom <= top:
        return ""
    corners = ((left, top), (right, top), (right, bottom), (left, bottom))
    own = ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3]))
    kept = tuple(radius if corner == mine else 0 for corner, mine, radius in zip(corners, own, radii, strict=True))
    return rounded_path((left, top, right, bottom), kept)


def inset(x0, distance):
    """The window outline moved distance pixels inwards, its corner radii shrinking with it."""
    box = (x0 + distance, distance, x0 + FRAME_W - distance, FRAME_H - distance)
    top, bottom = max(palette.TOP_RADIUS - distance, 0), max(palette.BOTTOM_RADIUS - distance, 0)
    return box, (top, top, bottom, bottom)


def around_client(x0, distance):
    """The client area grown by distance pixels."""
    return (x0 + SIDE - distance, TOP - distance, x0 + SIDE + MIDDLE + distance, TOP + MIDDLE + distance), (0,) * 4


def frame_layers(x0, state):
    """(fill, opacity, outer shape, inner shape): glass, then the lines DWM draws over it, outside in."""
    lines = palette.FRAME_LINES
    glass, glass_alpha = palette.GLASS[state]
    return [
        (glass, glass_alpha, inset(x0, 0), around_client(x0, 0)),
        (*lines["outer"][state], inset(x0, 0), inset(x0, 1)),
        (*lines["highlight"][state], inset(x0, 1), inset(x0, 2)),
        (*lines["client_light"][state], around_client(x0, 2), around_client(x0, 1)),
        (*lines["client_dark"][state], around_client(x0, 1), around_client(x0, 0)),
    ]


def ring(fill, alpha, outer, inner, piece):
    path = clipped(outer, piece) + clipped(inner, piece)
    if not clipped(outer, piece):
        return ""
    return f'<path d="{path}" fill="{fill}" fill-opacity="{number(round(alpha / 255, 3))}" fill-rule="evenodd"/>'


def frame_piece(element_id, box, layers):
    left, top, right, bottom = box
    shapes = "".join(ring(*layer, box) for layer in layers)
    bounds = f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" fill="none"/>'
    return f'<g id="{element_id}">{bounds}{shapes}</g>'


def frame(prefix, x0, state):
    layers = frame_layers(x0, state)
    pieces = [frame_piece(f"{prefix}{name}", box, layers) for name, box in piece_boxes(x0)]
    return "\n".join(
        [*pieces, f'<rect id="{prefix}hint-stretch-borders" x="{x0}" y="0" width="1" height="1" fill="none"/>']
    )


def maximized(prefix, x0, state):
    """A maximized window's caption: glass with the client lines along its foot, the same band in every piece."""
    glass, glass_alpha = palette.GLASS[state]
    light, light_alpha = palette.FRAME_LINES["client_light"][state]
    dark, dark_alpha = palette.FRAME_LINES["client_dark"][state]
    band = (
        f'<rect x="{x0}" y="0" width="{FRAME_W}" height="{MAX_ROWS}" fill="{glass}" '
        f'fill-opacity="{number(round(glass_alpha / 255, 3))}"/>'
        f'<rect x="{x0}" y="{MAX_ROWS - 2}" width="{FRAME_W}" height="1" fill="{light}" '
        f'fill-opacity="{number(round(light_alpha / 255, 3))}"/>'
        f'<rect x="{x0}" y="{MAX_ROWS - 1}" width="{FRAME_W}" height="1" fill="{dark}" '
        f'fill-opacity="{number(round(dark_alpha / 255, 3))}"/>'
    )
    return "\n".join(f'<g id="{prefix}{name}">{band}</g>' for name in PIECES)


def mask(x0):
    """The window's shape, where KWin blurs behind the glass: the frame's outline with the client inside it."""
    outline = inset(x0, 0)
    return "\n".join(
        f'<path id="mask-{name}" d="{clipped(outline, box)}"/>'
        for name, box in piece_boxes(x0)
        if clipped(outline, box)
    )


def decoration_svg():
    step = FRAME_W + GAP
    body = "\n".join(
        [
            frame("decoration-", 0, "active"),
            frame("decoration-inactive-", step, "inactive"),
            maximized("decoration-maximized-", 2 * step, "active"),
            maximized("decoration-maximized-inactive-", 3 * step, "inactive"),
            mask(4 * step),
        ]
    )
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{5 * step}" height="{FRAME_H}">\n{body}\n</svg>\n'


# Aurorae's button states, each a (window, Windows 7 state) of the atlas.
AURORAE_STATES = {
    "active": ("active", "normal"),
    "hover": ("active", "hot"),
    "pressed": ("active", "pressed"),
    "deactivated": ("active", "disabled"),
    "inactive": ("inactive", "normal"),
    "hover-inactive": ("inactive", "hot"),
    "pressed-inactive": ("inactive", "pressed"),
    "deactivated-inactive": ("inactive", "disabled"),
}
BUTTON_FACES = {"minimize": "caption-end", "maximize": "caption", "restore": "caption", "close": "close"}


def button_face(face):
    # The atlas duplicates its top and bottom highlights for stretching. At
    # 96 DPI DWM paints each highlight once, preserving the dark lower edge.
    return {
        **face,
        "size": (face["size"][0], face["size"][1] - 2),
        "rows": face["rows"][1:-1],
        "left": [column[1:-1] for column in face["left"]],
        "right": [column[1:-1] for column in face["right"]],
        "bands": [{**band, "rows": (band["rows"][0] - 1, band["rows"][1] - 1)} for band in face["bands"]],
    }


# Optical masters in the guest's 144-DPI button coordinates. The high-DPI
# maximize ring and X have heavier strokes than a scaled 96-DPI glyph.
LARGE_CAPTION_PATHS = {
    "minimize": rect(15, 17, 16, 4),
    "maximize": rect(11, 7, 18, 14) + rect(15, 10, 10, 8),
    "close": "M29,7h5l3,4 3,-4h5l-6,7 6,7h-5l-3,-4 -3,4h-5l6,-7z",
    "restore": ("M14,6h15v14h-2V8H14z " + rect(11, 9, 15, 13) + rect(15, 13, 7, 5)),
}


def large_caption_glyph(kind, colours, prefix, x0):
    body = f"g{prefix}LargeGlyph"
    gradient = (
        f'<linearGradient id="{body}" x2="0" y2="1"><stop offset="0" {paint(*colours["top"])}/>'
        f'<stop offset="1" {paint(*colours["bottom"])}/></linearGradient>'
    )
    path = LARGE_CAPTION_PATHS[kind]
    outline, alpha = colours["outline"]
    shape = (
        f'<g transform="translate({x0} 0) scale(0.66666667)">'
        f'<path d="{path}" stroke="{outline}" stroke-opacity="{number(alpha / 255)}" '
        f'stroke-width="3" stroke-linejoin="round" fill="none"/>'
        f'<path d="{path}" fill="url(#{body})" fill-rule="evenodd"/></g>'
    )
    return gradient, shape


def button_state(kind, window, look, prefix, x0=0, large=False):
    face_name = BUTTON_FACES[kind]
    width = palette.BUTTON_WIDTHS["maximize" if kind == "restore" else kind]
    height = palette.BUTTON_HEIGHT
    glyph_width, glyph_height = GLYPH_SHAPES[kind][0]
    left, right, top, bottom = palette.BUTTON_CONTENT[face_name]
    glyph_x = round((width - glyph_width + left - right) / 2)
    glyph_y = round((height - glyph_height + top - bottom) / 2)
    face = button_face(stops.FACES[face_name][window][look])
    face_definitions, face_shapes = face_markup(face, f"f{prefix}", (0, 0))
    face_shapes = f'<g transform="translate({x0} 0) scale({width / face["size"][0]} 1)">{face_shapes}</g>'
    glyph_gradient, glyph_shapes = glyph_markup(kind, stops.GLYPHS[kind][look], f"g{prefix}", (x0 + glyph_x, glyph_y))
    if large:
        glyph_gradient, glyph_shapes = large_caption_glyph(kind, stops.GLYPHS[kind][look], prefix, x0)
    return face_definitions + glyph_gradient, face_shapes + glyph_shapes


def button_svg(kind, large=False):
    width = palette.BUTTON_WIDTHS["maximize" if kind == "restore" else kind]
    height = palette.BUTTON_HEIGHT
    definitions, groups = [], []
    for index, (state, (window, look)) in enumerate(AURORAE_STATES.items()):
        defs, shapes = button_state(kind, window, look, index, index * (width + GAP), large)
        definitions.append(defs)
        groups.append(f'<g id="{state}-center">{shapes}</g>')
    total = len(AURORAE_STATES) * (width + GAP)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{height}">'
        f"<defs>{''.join(definitions)}</defs>\n" + "\n".join(groups) + "\n</svg>\n"
    )


RC = """[General]
ActiveTextColor=0,0,0,255
InactiveTextColor=0,0,0,255
TitleAlignment=Left
TitleVerticalAlignment=Center
Animation=0
Shadow=false

[Layout]
TitleHeight={title}
TitleEdgeTop=1
TitleEdgeBottom=0
TitleEdgeLeft={side}
TitleEdgeRight={right_inset}
TitleEdgeTopMaximized=0
TitleEdgeBottomMaximized=0
TitleEdgeLeftMaximized=2
TitleEdgeRightMaximized=2
TitleBorderLeft=4
TitleBorderRight=4
ButtonHeight={button_height}
ButtonWidth={maximize}
ButtonWidthMenu=16
ButtonWidthMinimize={minimize}
ButtonWidthMaximizeRestore={maximize}
ButtonWidthClose={close}
ButtonSpacing=-1
ButtonMarginTop=0
ExplicitButtonSpacer=4
BorderLeft={side}
BorderRight={side}
BorderBottom={side}
PaddingTop=0
PaddingBottom=0
PaddingLeft=0
PaddingRight=0
"""
METADATA = """{
  "KPlugin": {
    "Authors": [{ "Name": "Bending Unit 22" }],
    "Id": "Chicago95Aero",
    "License": "GPL-3.0",
    "Name": "Chicago95 Aero",
    "Description": "Chicago95 Windows 7 Aero glass window decoration",
    "Version": "1.0"
  }
}
"""


def write_theme(out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "decoration.svg").write_text(decoration_svg())
    for kind in BUTTON_FACES:
        (out / f"{kind}.svg").write_text(button_svg(kind))
        (out / f"{kind}-large.svg").write_text(button_svg(kind, large=True))
    (out / "Chicago95Aerorc").write_text(
        RC.format(
            title=palette.TITLE_HEIGHT - 1,
            side=palette.BORDER,
            right_inset=palette.BUTTON_RIGHT_INSET,
            button_height=palette.BUTTON_HEIGHT,
            **palette.BUTTON_WIDTHS,
        )
    )
    (out / "metadata.json").write_text(METADATA)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=HERE / "theme")
    destination = parser.parse_args().out
    write_theme(destination)
    print("wrote", destination)
