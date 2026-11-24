#!/usr/bin/env python3
"""Builds the Chicago95Aero window decoration: the Windows 7 Aero glass frame for KWin's Aurorae engine.

usage: python3 aero/aurorae/make_aero_aurorae.py [--out DIR]

The frame is translucent glass that KWin's blur effect blurs behind (the mask-* elements mark the region), edged with
the lines DWM's atlas draws (aero/palette.py). The caption buttons are vector faces fitted to the atlas
(aero/aurorae/stops.py, written by tests/aero/fit_aero_stops.py).
"""

import importlib.util
import re
from pathlib import Path
from xml.etree import ElementTree as ET

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


def gradient_knots(samples, tolerance=4, positions=None):
    """Keep the ends and bends of a piecewise-linear colour ramp."""
    if len(samples) == 1 or all(sample == samples[0] for sample in samples):
        return [0]
    positions = range(len(samples)) if positions is None else positions
    kept = [0]

    def split(start, end):
        if end > start + 1:
            first, last = samples[start], samples[end]
            worst, pivot = 0, start
            for i in range(start + 1, end):
                t = (positions[i] - positions[start]) / (positions[end] - positions[start])
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


def gradient_stops(values, attributes, offset=0, total=None, positions=None):
    """Fit ramps through pixel centres, retaining abrupt bevels as hard stops."""
    samples = []
    for value in values:
        if isinstance(value, (float, int)):
            samples.append((value * 255,))
        else:
            colour, alpha = value
            rgb = bytes.fromhex(colour.lstrip("#"))
            samples.append(tuple(v * alpha / 255 for v in rgb) + (alpha,))
    positions = range(len(values)) if positions is None else positions
    indices = gradient_knots(samples, positions=positions)
    stops = []
    for k, i in enumerate(indices):
        # A large adjacent jump is a painted edge between two surfaces.
        if (
            k
            and positions[i] == positions[indices[k - 1]] + 1
            and max(abs(a - b) for a, b in zip(samples[i - 1], samples[i], strict=True)) > 48
        ):
            stops.extend(((positions[i], values[i - 1]), (positions[i], values[i])))
        stops.append((positions[i] + 0.5, values[i]))
    length = total or positions[-1] + 1
    return "".join(
        f'<stop offset="{number(round((offset + x) / length, 5))}" {attributes(value)}/>' for x, value in stops
    )


def sprite_sheet(width, height, definitions, groups):
    """Share identical paint servers across states while keeping every public element ID."""
    paints, aliases, unique = {}, {}, []
    for paint in ET.fromstring("<defs>" + "".join(definitions) + "</defs>"):
        name = paint.attrib.pop("id")
        shape = ET.tostring(paint, encoding="unicode")
        if shape in paints:
            aliases[name] = paints[shape]
        else:
            paints[shape] = name
            paint.set("id", name)
            unique.append(ET.tostring(paint, encoding="unicode"))
    art = re.sub(r"url\(#([^)]+)\)", lambda match: f"url(#{aliases.get(match[1], match[1])})", "\n".join(groups))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f"<defs>{''.join(unique)}</defs>\n{art}\n</svg>\n"
    )


def vertical_gradient(gradient_id, column, positions=None, *, height=None):
    """Fit the fill or border gradient along the vertical axis."""
    units = ' gradientUnits="userSpaceOnUse"' if height is not None else ""
    return (
        f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="{height or 1}"{units}>'
        f"{gradient_stops(column, lambda value: paint(*value), positions=positions)}</linearGradient>"
    )


def shade_gradient(gradient_id, shade):
    stops = gradient_stops(shade, lambda value: f'stop-color="#000000" stop-opacity="{number(value)}"')
    return f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="1" y2="0">{stops}</linearGradient>'


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
CLOSE_CROSS = "M1.4 3H4.67L6.5 5.33 8.33 3h3.27L7.67 7l3.93 4H8.33L6.5 8.67 4.67 11H1.4l3.93-4z"
GLYPH_SHAPES = {
    "close": ((13, 14), [("stroke", CLOSE_CROSS), ("body", CLOSE_CROSS)]),
    "minimize": ((14, 14), [("outline", rect(0, 7, 14, 5)), ("body", rect(2, 8, 10, 3))]),
    "maximize": (
        (16, 14),
        [("outline", rect(3, 2, 13, 10) + rect(7, 6, 4, 2)), ("body", rect(4, 3, 10, 8) + rect(6, 5, 6, 4))],
    ),
    "restore": (
        (14, 14),
        [
            ("outline", "M3 0h11v11h-3v3H0V3h3z" + rect(5, 7, 2, 2)),
            ("body", "M4 2h8v8h-1V3H4z"),
            ("body", rect(2, 4, 8, 8) + rect(4, 6, 4, 4)),
        ],
    ),
}
CLOSE_OUTLINE_WIDTH = 2


# At 96 DPI the native outlines chamfer the corners at the ends of the
# straight strokes. The white ink and its adjoining steps share one grid.
CAPTION_OUTLINES_96 = {
    "minimize": "M2 7H12V8H13V11H12V12H2V11H1V8H2Z",
    "maximize": "M4 2H14V3H15V11H14V12H4V11H3V3H4Z" + rect(7, 6, 4, 2),
    "restore": "M4 1H12V2H13V10H12V11H11V12H10V13H2V12H1V4H2V3H3V2H4Z" + rect(5, 7, 2, 2),
}
CAPTION_INK_96 = {
    "minimize": (8, (255, 238, 228)),
    "maximize": (3, (255, 255, 255, 240, 232, 227, 222, 218)),
    "restore": (2, (255, 255, 255, 255, 243, 234, 229, 225, 221, 217)),
}


def glyph_markup(kind, colours, prefix="g", origin=(0, 0), *, optical=False):
    """A glyph's shapes at origin: dark outline under a white body that darkens towards its foot."""
    (_, height), layers = GLYPH_SHAPES[kind]
    x0, y0 = origin
    outline, outline_alpha = colours["outline"]
    body_id = f"{prefix}{kind}"
    if optical:
        first, shades = CAPTION_INK_96[kind]
        knots = "".join(
            f'<stop offset="{(row + .5) / height:g}" stop-color="#{shade:02x}{shade:02x}{shade:02x}"/>'
            for row, shade in enumerate(shades, first)
        )
        start = 0
        if kind in CAPTION_OUTLINES_96:
            layers = [("outline", CAPTION_OUTLINES_96[kind]), *layers[1:]]
    else:
        start = y0
        knots = f'<stop offset="0" {paint(*colours["top"])}/><stop offset="1" {paint(*colours["bottom"])}/>'
    gradient = (
        f'<linearGradient id="{body_id}" x1="0" y1="{start}" x2="0" y2="{start + height}" '
        f'gradientUnits="userSpaceOnUse">{knots}</linearGradient>'
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


def frame_layers(x0, state, glass):
    """(fill, opacity, outer shape, inner shape): glass, then the lines DWM draws over it, outside in."""
    lines = palette.FRAME_LINES
    color, opacity = glass
    tint = [(color, opacity, inset(x0, 0), around_client(x0, 0))] if opacity else []
    return tint + [
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


def frame(prefix, x0, state, *, glass=None):
    layers = frame_layers(x0, state, palette.GLASS[state] if glass is None else glass)
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


def decoration_svg(*, native_glass=False):
    step = FRAME_W + GAP
    active_glass = inactive_glass = None
    definitions = ""
    if native_glass:
        active_glass = ("none", 0)
        side, opacity = palette.GLASS["inactive"]
        inactive_glass = ("url(#inactive-tint)", opacity)
        # The restored inactive caption is cooler and darker than its frame.
        # Keep a continuous tint across the joins to the side borders.
        definitions = (
            '<defs><linearGradient id="inactive-tint" gradientUnits="userSpaceOnUse" '
            f'x1="0" y1="0" x2="0" y2="{TOP}">'
            '<stop offset=".8" stop-color="#58A5E1"/>'
            f'<stop offset="1" stop-color="{side}"/></linearGradient></defs>'
        )
    body = "\n".join(
        [
            frame("decoration-", 0, "active", glass=active_glass),
            frame("decoration-inactive-", step, "inactive", glass=inactive_glass),
            maximized("decoration-maximized-", 2 * step, "active"),
            maximized("decoration-maximized-inactive-", 3 * step, "inactive"),
            mask(4 * step),
        ]
    )
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{5 * step}" height="{FRAME_H}">\n{definitions}{body}\n</svg>\n'


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
    "close": "M28.5 7h5l3.5 3.5 3.5-3.5h5l-7 7 7 7h-5L37 17.5 33.5 21h-5l7-7z",
    "restore": ("M14,6h15v13h-2V8H14z " + rect(11, 9, 15, 13) + rect(15, 13, 7, 5)),
}


DOUBLE_DENSITY_STRAIGHT_GLYPHS = {
    "minimize": rect(20, 23, 21, 5),
    "maximize": rect(15, 9, 24, 19) + rect(20, 13, 13, 11),
}
# GTK rasterizes this glyph on a 2× grid before the compositor scales it.
GTK_RESTORE_PATH = "M14,6h15v14h-2V8H14z " + rect(11, 9, 15, 13) + rect(15, 13, 7, 5)


def large_caption_glyph(kind, colours, prefix, x0, pixel_density=None):
    body = f"g{prefix}LargeGlyph"
    native_restore = kind == "restore" and pixel_density is None
    if colours["top"] == colours["bottom"]:
        stops_markup = f"<stop {paint(*colours['top'])}/>"
    else:
        # The SP1 glyph stays white across the top bevel, then shades to grey.
        if kind == "minimize":
            samples = ((0.125, 255), (0.375, 244), (0.625, 232), (0.875, 225))
        elif native_restore:
            samples = (
                (5.5 / 16, 255),
                (6.5 / 16, 245),
                (7.5 / 16, 239),
                (8.5 / 16, 234),
                (13.5 / 16, 220),
                (15.5 / 16, 216),
            )
        else:
            samples = (
                (4.5 / 14, 255),
                (5.5 / 14, 242),
                (6.5 / 14, 236),
                (7.5 / 14, 232),
                (10.5 / 14, 223),
                (13.5 / 14, 216),
            )
        stops_markup = "".join(
            f'<stop offset="{at}" stop-color="#{shade:02x}{shade:02x}{shade:02x}"/>' for at, shade in samples
        )
    gradient = f'<linearGradient id="{body}" x2="0" y2="1">{stops_markup}</linearGradient>'
    # A GTK HiDPI icon is rasterized at twice the logical size before it is
    # displayed. Keep axis-aligned glyph edges on that source pixel grid.
    double_density = pixel_density == 2 and kind in DOUBLE_DENSITY_STRAIGHT_GLYPHS
    path = DOUBLE_DENSITY_STRAIGHT_GLYPHS[kind] if double_density else LARGE_CAPTION_PATHS[kind]
    if kind == "restore" and not native_restore:
        path = GTK_RESTORE_PATH
    scale = ".5" if double_density else "0.66666667"
    # The 40-pixel caption cell is narrower than a simple 1.5× scale of
    # the 27-unit SVG canvas. Keep its square-shouldered glyphs on the device grid.
    transform = f"scale({scale})"
    if kind in ("maximize", "restore") and pixel_density is None:
        transform = f"scale({palette.BUTTON_WIDTHS['maximize'] / 40:g} {scale})"
    outline, alpha = colours["outline"]
    shape = (
        f'<g transform="translate({x0:g} 0) {transform}">'
        f'<path d="{path}" stroke="{outline}" stroke-opacity="{number(alpha / 255)}" '
        'stroke-width="2" '
        f'stroke-linejoin="{"round" if kind == "close" else "miter"}" fill="none"/>'
        f'<path d="{path}" fill="url(#{body})" fill-rule="evenodd"/></g>'
    )
    return gradient, shape


def caption_rim(left, top, right, bottom, left_radius, right_radius, *, left_edge=True, right_edge=True):
    """The lower corners and two sides of a caption cell."""
    edge = f"M{left:g} {top:g}V{bottom - left_radius:g}" if left_edge else f"M{left + left_radius:g} {bottom:g}"
    if left_radius and left_edge:
        edge += f"a{left_radius} {left_radius} 0 0 0 {left_radius} {left_radius}"
    edge += f"H{right - right_radius:g}"
    if right_radius:
        edge += f"a{right_radius} {right_radius} 0 0 0 {right_radius} -{right_radius}"
    return edge + (f"V{top:g}" if right_edge else "")


# Gradient anchors for the active, resting 144-DPI buttons. Estimate the
# face paint over the adjacent glass in the dark, light and blue VM captures.
# Row indices refer to the 30-pixel native face before scaling.
LARGE_ACTIVE_FACE = {
    "minimize": (
        (0, "#FCFCFC", 255), (1, "#F5F5F5", 158), (3, "#F5F5F5", 158),
        (7, "#DEDFDE", 130), (12, "#D1D2D2", 122), (15, "#30302F", 56),
        (19, "#161619", 51), (21, "#1C1C23", 53), (26, "#9098AE", 80),
        (27, "#EAEBF1", 150), (28, "#010101", 154), (29, "#FDFDFD", 170),
    ),
    "maximize": (
        (0, "#FCFCFC", 255), (1, "#F6F6F6", 174), (3, "#F5F5F5", 174),
        (7, "#E2E2E2", 153), (12, "#DADADA", 145), (15, "#7E7E7E", 89),
        (21, "#6C6D70", 79), (26, "#A8ADBF", 99), (27, "#EDEEF2", 160),
        (28, "#262627", 183), (29, "#FDFDFD", 177),
    ),
    "close": (
        (0, "#FCFCFC", 255), (1, "#FDAEA1", 221), (7, "#EF8572", 221),
        (12, "#EC7E6B", 221), (15, "#D43418", 221), (21, "#D3351A", 221),
        (26, "#E17B5B", 220), (27, "#F3B7A5", 220), (28, "#582B23", 249),
        (29, "#FEFEFE", 196),
    ),
}

# The straight shared seam uses a dark trailing edge on Minimize and a
# translucent leading highlight on Maximize. Each occupies one 144-DPI pixel.
LARGE_ACTIVE_JOINED_EDGES = {
    "minimize": {
        "right": (
            (0, "#828282", 215), (1, "#808080", 210), (12, "#616161", 186),
            (15, "#262625", 151), (21, "#1C1E1E", 146), (27, "#45454A", 157),
            (28, "#232325", 181), (29, "#FDFDFD", 175),
        ),
    },
    "maximize": {
        "left": (
            (0, "#FCFCFC", 255), (1, "#FDFDFD", 215), (12, "#F2F2F2", 200),
            (15, "#DFDEDF", 172), (21, "#DDDDDF", 169), (27, "#F8F8FA", 208),
            (28, "#232325", 181), (29, "#FEFEFE", 175),
        ),
        "right": (
            (0, "#FCFCFC", 255), (1, "#FAFBFA", 204), (12, "#ECECEC", 190),
            (15, "#CECECF", 159), (21, "#CCCBCD", 155), (27, "#EEEFF4", 177),
            (28, "#343434", 196), (29, "#FEFEFE", 190),
        ),
    },
}

# The red bevel inside the outer grey rim turns into the dark lower lip.
LARGE_CLOSE_INNER_BEVEL = (
    (0, "#5B4743", 255), (1, "#58433E", 253), (12, "#492D27", 251),
    (15, "#380D04", 249), (21, "#370E05", 249), (25, "#491904", 247),
    (28, "#582B23", 249), (29, "#582B23", 249),
)

LARGE_CLOSE_INNER_HIGHLIGHTS = (
    (
        (0, "#FCFCFC", 255), (1, "#F3D8D3", 221), (6, "#EAC4BF", 221),
        (12, "#E7BFB9", 220), (15, "#D59A92", 220), (21, "#D79992", 219),
        (26, "#E1B9B2", 218), (29, "#FDFDFD", 192),
    ),
    (
        (0, "#FCFCFC", 255), (1, "#F1CFC9", 223), (6, "#E4B7B0", 224),
        (12, "#E0B0A9", 222), (15, "#CC8279", 222), (21, "#CD8378", 223),
        (26, "#A78E8D", 219), (29, "#FFFFFF", 132),
    ),
)

# Active disabled Close at 144 DPI, measured with the caption buttons
# shown and hidden over three solid backgrounds. Each entry is a gradient
# anchor at a physical row, with the glass colour and its opacity separated.
LARGE_DISABLED_CLOSE_FACE = (
    (0, "#FAFBFB", 166), (1, "#FBA89A", 121), (6, "#EC7E6B", 121),
    (12, "#E87360", 121), (15, "#CC2305", 121), (19, "#CC2102", 121),
    (21, "#CC2507", 121), (26, "#DA714F", 121), (27, "#F1B29F", 121),
    (28, "#55271F", 222), (29, "#FEFEFE", 169),
)
LARGE_DISABLED_CLOSE_DIVIDER = (
    (0, "#946A61", 224), (6, "#8A4E41", 223), (12, "#874637", 221),
    (16, "#751101", 217), (21, "#761303", 217), (27, "#853426", 219), (28, "#5D2014", 222),
)
LARGE_DISABLED_CLOSE_BEVEL = (
    (0, "#57423F", 225), (6, "#4C2F2B", 225), (12, "#472B25", 225),
    (16, "#330900", 222), (22, "#340C04", 222), (25, "#481D17", 219),
    (28, "#55271F", 222),
)
LARGE_DISABLED_CLOSE_HIGHLIGHTS = (
    (
        (0, "#FBFBFA", 164), (1, "#F4D5D1", 120), (6, "#EBC1B9", 120),
        (12, "#E5B9B1", 121), (16, "#D39289", 121), (21, "#D39289", 121),
        (26, "#DEB3AD", 122), (27, "#F0D7D3", 121),
    ),
    (
        (0, "#FAFBFB", 166), (1, "#F1CAC4", 121), (6, "#E4B1A9", 121),
        (12, "#E0A8A0", 120), (16, "#C3766C", 121), (21, "#C8786E", 121),
        (25, "#CB9E97", 121),
    ),
)


def large_disabled_close_glyph(x):
    # The grey outline and translucent white ink are adjacent fills. The
    # disabled X would darken if the two translucent shapes overlapped.
    ink = LARGE_CAPTION_PATHS["close"]
    outline = "M29 6h5l3 3 3-3h5q1 0 1 1l-7 7 7 7q0 1-1 1h-5l-3-3-3 3h-5q-1 0-1-1l7-7-7-7q0-1 1-1z"
    return (
        f'<g transform="translate({x:g} 0) scale(0.66666667)" fill-opacity="0.4">'
        f'<path d="{outline} {ink}" fill="#7f7f7f" fill-rule="evenodd"/>'
        f'<path d="{ink}" fill="white"/></g>'
    )


def caption_gradient(gradient_id, profile, height):
    anchors, colours, alphas = zip(*profile, strict=True)
    return vertical_gradient(gradient_id, list(zip(colours, alphas, strict=True)), anchors, height=height)


# The outer highlight, dark lip and inner highlight on Minimize follow
# nested quarter circles. The measured fills are separate paints over glass.
LARGE_MINIMIZE_BEVEL = (
    ((0, "#FDFDFD", 173), (3, "#FDFDFD", 175), (24, "#FDFDFD", 170), (29, "#FDFDFD", 175)),
    (
        (0, "#0E0E0E", 162), (6, "#090909", 159), (12, "#050505", 156),
        (21, "#020202", 155), (28, "#010101", 154), (29, "#010101", 154),
    ),
    (
        (0, "#FCFCFC", 255), (1, "#FAFAFA", 198), (3, "#FAFAFA", 198),
        (6, "#F2F2F2", 184), (12, "#EBEBEB", 176), (15, "#CBCBCB", 136),
        (21, "#C5C5C8", 132), (26, "#DADEE3", 146), (27, "#EBEDF2", 157),
        (28, "#0B0B0A", 159), (29, "#FDFDFD", 175),
    ),
)


def large_minimize_surface(width, prefix):
    height = palette.BUTTON_HEIGHT
    pixel = height / 30
    body_right = width - 2 * pixel
    borders = [
        caption_rim(
            inset * pixel, 0, body_right if inset == 3 else width - pixel,
            height - inset * pixel, (4.35 - inset) * pixel, 0,
        ) + "Z"
        for inset in range(4)
    ]
    paths = [outer + inner for outer, inner in zip(borders[:-1], borders[1:], strict=True)] + borders[-1:]
    profiles = (*LARGE_MINIMIZE_BEVEL, LARGE_ACTIVE_FACE["minimize"])
    definitions, shapes = [], []
    for index, (path, profile) in enumerate(zip(paths, profiles, strict=True)):
        gradient = f"{prefix}Bevel{index}"
        definitions.append(caption_gradient(gradient, profile, height))
        shapes.append(f'<path d="{path}" fill="url(#{gradient})" fill-rule="evenodd"/>')
    # The body brightens towards the shared seam, modulating the opacity as well
    # as the colour. The horizontal highlight sits inside the inner bevel.
    sheen = f"{prefix}Sheen"
    definitions.append(
        f'<linearGradient id="{sheen}" x2="1" y2="0">'
        '<stop offset=".04" stop-color="white" stop-opacity="0"/>'
        '<stop offset="1" stop-color="white" stop-opacity=".105"/></linearGradient>'
    )
    shapes.append(f'<path d="{borders[-1]}" fill="url(#{sheen})"/>')
    edge = f"{prefix}Right"
    definitions.append(caption_gradient(edge, LARGE_ACTIVE_JOINED_EDGES["minimize"]["right"], height))
    shapes.append(f'<path d="{rect(width - pixel, 0, pixel, height)}" fill="url(#{edge})"/>')
    return "".join(definitions), "".join(shapes)


def caption_surface(kind, face, width, prefix, large, *, optical_face=(), resting=False, disabled_close=False):
    """Paint the glass face and bevels with independently translucent gradients."""
    if kind == "minimize" and optical_face:
        return large_minimize_surface(width, prefix)
    height = palette.BUTTON_HEIGHT
    large_close = kind == "close" and bool(optical_face)
    left_radius = 2 if kind in ("minimize", "close") else 0
    right_radius = 2 if large_close else 3 if kind == "close" else 0
    stroke = 2 / 3 if large else 1
    half = stroke / 2
    bottom, right = height - half, width - half
    joined = LARGE_ACTIVE_JOINED_EDGES.get(kind, {}) if optical_face else {}
    if resting and not large and kind == "maximize":
        # The neighbouring Minimize button owns the dark seam. Maximize
        # starts with one translucent light pixel at both densities.
        joined = {"left": LARGE_ACTIVE_JOINED_EDGES["maximize"]["left"]}
    edge = caption_rim(
        half, half, right, bottom, left_radius, right_radius,
        left_edge="left" not in joined and not disabled_close, right_edge="right" not in joined,
    )
    # Keep the body inside the stroke. The two translucent paints should not
    # stack on straight edges and make the lower highlight opaque.
    surface = (
        caption_rim(stroke, 0, width - stroke, height - stroke, max(0, left_radius - half), max(0, right_radius - half))
        + "Z"
    )
    body = f"{prefix}Gloss"
    shade = f"{prefix}Sides"
    rows = face["rows"]
    # At 144 DPI the bevel and dark lip each occupy one physical row. The
    # central colour bands absorb the additional height of the optical master.
    positions = (0, 1, 2, 3, 4, 5, 6, 7, 12, 15, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29) if large else None
    if optical_face:
        definitions = caption_gradient(body, optical_face, height)
    else:
        definitions = vertical_gradient(body, rows, positions, height=height)
    side_samples = [band["shade"][2] for band in face["bands"] if len(band["shade"]) > 2]
    if disabled_close:
        strength, shade_colour, inner_stop, outer_stop = 0.105, ' stop-color="#53595b"', ".19", ".81"
    else:
        strength = sum(side_samples) / len(side_samples) if side_samples else 0
        shade_colour, inner_stop, outer_stop = "", ".4", ".6"
    definitions += (
        f'<linearGradient id="{shade}" x2="1" y2="0">'
        f'<stop{shade_colour} stop-opacity="{strength:.3f}"/>'
        f'<stop offset="{inner_stop}"{shade_colour} stop-opacity="0"/>'
        f'<stop offset="{outer_stop}"{shade_colour} stop-opacity="0"/>'
        f'<stop offset="1"{shade_colour} stop-opacity="{strength:.3f}"/></linearGradient>'
    )
    # The atlas repeats the outside highlights for nine-slice stretching.
    # Follow the circular rim with a single stroke and keep the shaded seam
    # on the inside. The next cell supplies the divider on joined edges.
    light, alpha = rows[-1]
    if disabled_close:
        _, light, alpha = LARGE_DISABLED_CLOSE_FACE[-1]
    rim_paint = f'stroke="{light}" stroke-opacity="{alpha / 255:.3f}"'
    if large_close and not disabled_close:
        # The lower reflection is brighter than the two sides. Keep the
        # tint neutral all the way around the same continuous curved stroke.
        rim = f"{prefix}Rim"
        definitions += caption_gradient(rim, ((0, light, alpha), (28, light, alpha), optical_face[-1]), height)
        rim_paint = f'stroke="url(#{rim})"'
    left_column = face["left"][-1 if kind == "minimize" else 0]
    left_seam = f"{prefix}Left"
    bevels = []
    if disabled_close:
        definitions += caption_gradient(left_seam, LARGE_DISABLED_CLOSE_DIVIDER, height)
        divider = f"M0 0h{stroke:g}v{height - 2 * stroke:g}q0 {stroke:g} -{stroke:g} {stroke:g}Z"
        bevels.append(f'<path d="{divider}" fill="url(#{left_seam})"/>')
    elif "left" not in joined:
        definitions += vertical_gradient(left_seam, left_column, positions, height=height)
        bevels.append(
            f'<rect x="0" y="{stroke:g}" width="{stroke:g}" height="{bottom - left_radius - stroke:g}" '
            f'fill="url(#{left_seam})"/>'
        )
    for side, profile in joined.items():
        gradient = f"{prefix}{side.title()}"
        definitions += caption_gradient(gradient, profile, height)
        x = 0 if side == "left" else width - stroke
        bevels.append(
            f'<rect x="{x:g}" y="0" width="{stroke:g}" height="{height - stroke:g}" fill="url(#{gradient})"/>'
        )
    if large_close:
        inner = f"{prefix}InnerBevel"
        profile = LARGE_DISABLED_CLOSE_BEVEL if disabled_close else LARGE_CLOSE_INNER_BEVEL
        definitions += caption_gradient(inner, profile, height)
        radius = right_radius - stroke
        x, y = right - stroke, bottom - stroke
        inner_edge = f"M{x:g} {half:g}V{y - radius:g}a{radius:g} {radius:g} 0 0 1 -{radius:g} {radius:g}"
        bevels.append(
            f'<path d="{inner_edge}" stroke-width="{stroke:g}" stroke="url(#{inner})" '
            'stroke-linecap="square" fill="none"/>'
        )
        # Paint each highlight in a cutout in the glass face so its alpha
        # stays independent of the main fill.
        highlights = LARGE_DISABLED_CLOSE_HIGHLIGHTS if disabled_close else LARGE_CLOSE_INNER_HIGHLIGHTS
        for index, (x, profile) in enumerate(zip((stroke, width - 3 * stroke), highlights, strict=True)):
            highlight = f"{prefix}InnerHighlight{index}"
            definitions += caption_gradient(highlight, profile, height)
            path = rect(x, 0, stroke, height - 4 * stroke)
            surface += path
            bevels.append(f'<path d="{path}" fill="url(#{highlight})"/>')
    fill_rule = ' fill-rule="evenodd"' if large_close else ""
    return definitions, (
        f'<path d="{surface}" fill="url(#{body})"{fill_rule}/>'
        f'<path d="{surface}" fill="url(#{shade})"{fill_rule}/>'
        f'<path d="{edge}" {rim_paint} stroke-width="{stroke:g}" '
        'stroke-linecap="square" fill="none"/>'
        + "".join(bevels)
    )


def button_state(kind, window, look, prefix, x0=0, large=False, *, cell_width=None, pixel_density=None):
    face_name = BUTTON_FACES[kind]
    original_width = palette.BUTTON_WIDTHS["maximize" if kind == "restore" else kind]
    width = original_width if cell_width is None else cell_width
    height = palette.BUTTON_HEIGHT
    glyph_width, glyph_height = GLYPH_SHAPES[kind][0]
    left, right, top, bottom = palette.BUTTON_CONTENT[face_name]
    glyph_x = round((width - glyph_width + left - right) / 2)
    glyph_y = round((height - glyph_height + top - bottom) / 2)
    face = button_face(stops.FACES[face_name][window][look])
    resting = (window, look) == ("active", "normal")
    disabled_close = large and kind == "close" and (window, look) == ("active", "disabled")
    optical_face = LARGE_ACTIVE_FACE.get(kind, ()) if large and resting else ()
    if disabled_close:
        optical_face = LARGE_DISABLED_CLOSE_FACE
    face_definitions, face_shapes = caption_surface(
        kind, face, width, f"f{prefix}", large, optical_face=optical_face, resting=resting, disabled_close=disabled_close
    )
    face_shapes = f'<g transform="translate({x0} 0)">{face_shapes}</g>'
    if disabled_close:
        return face_definitions, face_shapes + large_disabled_close_glyph(x0 + (width - original_width) / 2)
    if large:
        glyph_gradient, glyph_shapes = large_caption_glyph(
            kind, stops.GLYPHS[kind][look], prefix, x0 + (width - original_width) / 2, pixel_density
        )
    else:
        glyph_gradient, glyph_shapes = glyph_markup(
            kind, stops.GLYPHS[kind][look], f"g{prefix}", (x0 + glyph_x, glyph_y),
            optical=kind in CAPTION_INK_96 and look != "disabled",
        )
    return face_definitions + glyph_gradient, face_shapes + glyph_shapes


# Optional KWin decoration commands share the Windows caption face. Their
# symbols also remain visible when a custom button group uses stock Aurorae.
EXTRA_CAPTION_GLYPHS = {
    "help": (
        "M9 6q0-4 4.5-4t4.5 3.5q0 2-2.4 3.5-1.6 1-1.6 2.6h-2.5q0-2.7 2.1-4.1"
        "Q15.7 6 15.7 5q0-1.1-2.1-1.1T11.5 6z M11.5 13h2.6v2.6h-2.6z"
    ),
    "keepabove": "M7 11l6.5-6 6.5 6-2 2-4.5-4.3L9 13z",
    "keepbelow": "M7 8l2-2 4.5 4.3L18 6l2 2-6.5 6z",
    "shade": "M7 6h13v3H7z",
    "alldesktops": "M10 3h7v2h-1v4l2 2v1h-4v4l-1 1v-5H9v-1l2-2V5h-1z",
}


def extra_caption_svg(kind):
    width = palette.BUTTON_WIDTHS["maximize"]
    definitions, groups = [], []
    for i, (state, (window, look)) in enumerate(AURORAE_STATES.items()):
        face = button_face(stops.FACES["caption"][window][look])
        defs, background = caption_surface("extra", face, width, f"f{i}", False)
        definitions.append(defs)
        colours = stops.GLYPHS["maximize"][look]
        colour, alpha = colours["top"]
        outline, _ = colours["outline"]
        glyph = (
            f'<path d="{EXTRA_CAPTION_GLYPHS[kind]}" fill="{colour}" stroke="{outline}" '
            f'stroke-width="1" stroke-linejoin="round" opacity="{number(alpha / 255)}"/>'
        )
        groups.append(f'<g id="{state}-center" transform="translate({i * (width + GAP)} 0)">{background}{glyph}</g>')
    return sprite_sheet(len(groups) * (width + GAP), palette.BUTTON_HEIGHT, definitions, groups)


def button_svg(kind, large=False):
    width = palette.BUTTON_WIDTHS["maximize" if kind == "restore" else kind]
    height = palette.BUTTON_HEIGHT
    definitions, groups = [], []
    for index, (state, (window, look)) in enumerate(AURORAE_STATES.items()):
        defs, shapes = button_state(kind, window, look, index, index * (width + GAP), large)
        definitions.append(defs)
        groups.append(f'<g id="{state}-center">{shapes}</g>')
    total = len(AURORAE_STATES) * (width + GAP)
    return sprite_sheet(total, height, definitions, groups)


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
    (out / "decoration-native.svg").write_text(decoration_svg(native_glass=True))
    for kind in BUTTON_FACES:
        (out / f"{kind}.svg").write_text(button_svg(kind))
        (out / f"{kind}-large.svg").write_text(button_svg(kind, large=True))
    for kind in EXTRA_CAPTION_GLYPHS:
        (out / f"{kind}.svg").write_text(extra_caption_svg(kind))
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
