"""Builds the Luna window decoration (Aurorae SVG theme) as vector shapes with the colours of luna/palette.py.

    make_luna_aurorae.py [--out DIR]

Sizes and colours are fitted to the luna.msstyles bitmaps (tests/luna/luna_sprites.py), the palette's title columns to
tests/references/xpnotepad.png, the lossless xpdisplayprop-1x.png and xpmycomputer.png (maximized title): a 4px frame,
a 26px title under 4px of rim, 21x21 caption buttons 2px apart. Gradients are the fitted stops of stops.py. Every
nine-slice piece is simple geometry with a gradient fill: a title corner is the stair-cornered fill plus one horizontal
overlay that darkens it towards the window's edge, an edge is a box, the mask is the same shapes in black. A caption
button is a rounded rectangle (the ring), the face inset by one pixel filled with a vertical gradient, radial glows, one
shade, an inner rim and a glyph of one element, each state with its own values in stops.BUTTON_ART.

Fitted geometry:
  window corner  The top corners of the window region are a hard stair (first opaque column 5, 3, 2, 1, 1, 0 on rows
                 0..5, the transparent corner of Window.Caption), drawn as a polygon so that every pixel is either
                 opaque or transparent as in the bitmap.
  caption button The eight states of CaptionButton.bmp and CloseButton.bmp: states 5 and 6 are the hover and pressed
                 faces again (and the close button's state 7 the disabled one), so they are drawn with <use>.
"""

import argparse
import itertools
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import stops  # noqa: E402
from palette import PALETTE  # noqa: E402

from luna import (  # noqa: E402
    Box,
    box_gradient,
    box_path,
    gradient,
    linear_gradient,
    linked_svg,
    number,
    plain_rect,
    radial_gradient,
    reused_gradient,
    rounded_rect,
    row_stops,
)

BORDER, TITLE_H, TOP_H = 4, 26, 30
CORNER_STAIR = [(0, 5), (1, 5), (1, 3), (2, 3), (2, 2), (3, 2), (3, 1), (5, 1), (5, 0)]
CORNER_W, EDGE_LEN, EDGE_LEN_BOTTOM = 28, 16, 4
FRAME_W, FRAME_H = 2 * CORNER_W + 16, TOP_H + EDGE_LEN + EDGE_LEN_BOTTOM
MAX_EDGE, MAX_CENTER = 4, 16
MAX_W = 2 * MAX_EDGE + MAX_CENTER
MAX_ROWS = 26
GAP = 8
BUTTON = 21
BUTTON_CELL = BUTTON + 3
INACTIVE_BORDER_BLEND = 0.5
WHITE = "#FFFFFF"
DIGITS = 2


def rescaled_to_maximized(title_stops):
    """The inactive title's stops on the 26 row maximized band, which shows rows 1..28 of the 30 row title."""
    last = TOP_H - 2
    return [(min(MAX_ROWS - 1, (row - 1) * (MAX_ROWS - 1) / last), colour) for row, colour in title_stops if row > 0]


class FrameStyle:
    def __init__(self, title, side_overlay, border_left, border_right, border_bottom):
        self.title = title
        self.side_overlay = side_overlay
        self.border_left = border_left
        self.border_right = border_right
        self.border_bottom = border_bottom


ACTIVE = FrameStyle(
    stops.TITLE["active"],
    stops.SIDE_OVERLAY,
    PALETTE["border_left"],
    PALETTE["border_bottom"],
    PALETTE["border_bottom"],
)
INACTIVE = FrameStyle(
    stops.TITLE["inactive"],
    stops.INACTIVE_SIDE_OVERLAY,
    stops.INACTIVE_BORDER_LEFT,
    stops.INACTIVE_BORDER_BOTTOM,
    stops.INACTIVE_BORDER_BOTTOM,
)


GRADIENT_TOKENS = {
    "decoration-": "a",
    "decoration-inactive-": "i",
    "decoration-maximized-": "m",
    "decoration-maximized-inactive-": "n",
}


def url(gradient_id):
    return f"url(#{gradient_id})"


def gradient_id(prefix, name):
    return GRADIENT_TOKENS[prefix] + name


def piece(piece_id, elements, bounds=None):
    """A nine-slice piece: its only element carries the id, several are grouped, and a piece that its elements do
    not span gets an invisible rectangle of the right size."""
    if bounds is not None and not elements:
        return box_path(*bounds, "none", piece_id)
    if bounds is not None:
        elements = [box_path(*bounds, "none", f"{piece_id}-bounds"), *elements]
    if len(elements) == 1:
        return elements[0].replace(" ", f' id="{piece_id}" ', 1)
    return f'<g id="{piece_id}">{"".join(elements)}</g>'


def stretch_hint(prefix, x0):
    return box_path(x0, 0, 1, 1, "none", f"{prefix}hint-stretch-borders")


def stair_path(corner_x, right):
    """The window region's top corner piece as a polygon: the stair of CORNER_STAIR at the outer edge."""

    def mirrored(x):
        return corner_x + CORNER_W - x if right else corner_x + x

    far_x = corner_x if right else corner_x + CORNER_W
    points = [(mirrored(0), TOP_H), *((mirrored(x), y) for x, y in CORNER_STAIR), (far_x, 0), (far_x, TOP_H)]
    moves = [
        f"V{number(y)}" if x == previous_x else f"H{number(x)}"
        for (previous_x, _), (x, y) in itertools.pairwise(points)
    ]
    return f"M{number(points[0][0])},{number(points[0][1])}" + "".join(moves) + "z"


def stair_fill(corner_x, right, paint):
    fill = "" if paint is None else f' fill="{paint}"'
    return f'<path d="{stair_path(corner_x, right)}"{fill}/>'


def side_overlay_gradient(overlay_id, overlay, direction):
    fractions = [(distance / CORNER_W, colour, opacity) for distance, colour, opacity in overlay]
    return box_gradient(overlay_id, fractions, direction, DIGITS)


def frame_definitions(prefix, style):
    border_bottom = row_stops(EDGE_LEN_BOTTOM, list(enumerate(style.border_bottom)))
    return "".join(
        [
            box_gradient(gradient_id(prefix, "t"), row_stops(TOP_H, style.title), "down", DIGITS),
            side_overlay_gradient(gradient_id(prefix, "ol"), style.side_overlay["left"], "right"),
            side_overlay_gradient(gradient_id(prefix, "or"), style.side_overlay["right"], "left"),
            box_gradient(
                gradient_id(prefix, "bl"), row_stops(BORDER, list(enumerate(style.border_left))), digits=DIGITS
            ),
            box_gradient(gradient_id(prefix, "bb"), border_bottom, "down", DIGITS),
            reused_gradient(gradient_id(prefix, "br"), gradient_id(prefix, "bb")),
        ]
    )


def corner_piece(prefix, x0, right):
    side = "right" if right else "left"
    corner_x = x0 + FRAME_W - CORNER_W if right else x0
    elements = [
        stair_fill(corner_x, right, url(gradient_id(prefix, "t"))),
        stair_fill(corner_x, right, url(gradient_id(prefix, "o" + side[0]))),
    ]
    return piece(f"{prefix}top{side}", elements)


def side_piece(prefix, x0, right):
    side = "right" if right else "left"
    corner_x = x0 + FRAME_W - CORNER_W if right else x0
    border_x = corner_x + CORNER_W - BORDER if right else corner_x
    border = box_path(border_x, TOP_H, BORDER, EDGE_LEN, url(gradient_id(prefix, "b" + side[0])))
    return piece(f"{prefix}{side}", [border], bounds=(corner_x, TOP_H, CORNER_W, EDGE_LEN))


def bottom_corner_piece(prefix, x0, right):
    side = "right" if right else "left"
    corner_x = x0 + FRAME_W - CORNER_W if right else x0
    bottom_y = TOP_H + EDGE_LEN
    outer, inner = (corner_x + CORNER_W, corner_x + CORNER_W - BORDER) if right else (corner_x, corner_x + BORDER)
    mitre_path = f"M{outer},{bottom_y} H{inner} L{outer},{bottom_y + EDGE_LEN_BOTTOM} Z"
    elements = [
        box_path(corner_x, bottom_y, CORNER_W, EDGE_LEN_BOTTOM, url(gradient_id(prefix, "bb"))),
        f'<path d="{mitre_path}" fill="{url(gradient_id(prefix, "b" + side[0]))}"/>',
    ]
    return piece(f"{prefix}bottom{side}", elements)


def frame_pieces(prefix, x0):
    middle, bottom_y = x0 + CORNER_W, TOP_H + EDGE_LEN
    top = box_path(middle, 0, 16, TOP_H, url(gradient_id(prefix, "t")))
    bottom = box_path(middle, bottom_y, 16, EDGE_LEN_BOTTOM, url(gradient_id(prefix, "bb")))
    return "\n".join(
        [
            corner_piece(prefix, x0, right=False),
            piece(f"{prefix}top", [top]),
            corner_piece(prefix, x0, right=True),
            side_piece(prefix, x0, right=False),
            side_piece(prefix, x0, right=True),
            bottom_corner_piece(prefix, x0, right=False),
            piece(f"{prefix}bottom", [bottom]),
            bottom_corner_piece(prefix, x0, right=True),
            piece(f"{prefix}center", [], bounds=(middle, TOP_H, 16, EDGE_LEN)),
            stretch_hint(prefix, x0),
        ]
    )


def maximized_pieces(prefix, x0):
    """KWin draws a maximized window's title from the centre piece alone, so every piece is the band itself."""
    fill = url(gradient_id(prefix, "t"))
    rows = MAX_ROWS
    layout = {
        "topleft": (0, 0, MAX_EDGE, MAX_EDGE),
        "top": (MAX_EDGE, 0, MAX_CENTER, MAX_EDGE),
        "topright": (MAX_EDGE + MAX_CENTER, 0, MAX_EDGE, MAX_EDGE),
        "left": (0, MAX_EDGE, MAX_EDGE, rows - 2 * MAX_EDGE),
        "right": (MAX_EDGE + MAX_CENTER, MAX_EDGE, MAX_EDGE, rows - 2 * MAX_EDGE),
        "bottomleft": (0, rows - MAX_EDGE, MAX_EDGE, MAX_EDGE),
        "bottom": (MAX_EDGE, rows - MAX_EDGE, MAX_CENTER, MAX_EDGE),
        "bottomright": (MAX_EDGE + MAX_CENTER, rows - MAX_EDGE, MAX_EDGE, MAX_EDGE),
        "center": (MAX_EDGE, 0, MAX_CENTER, rows),
    }
    pieces = [piece(f"{prefix}{name}", [box_path(x0 + x, y, w, h, fill)]) for name, (x, y, w, h) in layout.items()]
    return "\n".join(pieces)


def mask_pieces(x0):
    """The window's shape: opaque black where the frame is drawn, the same stairs at the top corners."""
    middle, right_x, bottom_y = x0 + CORNER_W, x0 + FRAME_W - CORNER_W, TOP_H + EDGE_LEN
    areas = {
        "mask-topleft": Box(x0, 0, CORNER_W, TOP_H),
        "mask-top": Box(middle, 0, 16, TOP_H),
        "mask-topright": Box(right_x, 0, CORNER_W, TOP_H),
        "mask-left": Box(x0, TOP_H, CORNER_W, EDGE_LEN),
        "mask-right": Box(right_x, TOP_H, CORNER_W, EDGE_LEN),
        "mask-bottomleft": Box(x0, bottom_y, CORNER_W, EDGE_LEN_BOTTOM),
        "mask-bottom": Box(middle, bottom_y, 16, EDGE_LEN_BOTTOM),
        "mask-bottomright": Box(right_x, bottom_y, CORNER_W, EDGE_LEN_BOTTOM),
        "mask-center": Box(middle, TOP_H, 16, EDGE_LEN),
    }
    stairs = {"mask-topleft": (areas["mask-topleft"].x, False), "mask-topright": (areas["mask-topright"].x, True)}
    return "\n".join(
        piece(name, [stair_fill(*stairs[name], None) if name in stairs else box_path(*area)])
        for name, area in areas.items()
    )


def decoration_svg():
    step = FRAME_W + GAP
    max_step = MAX_W + GAP
    max_x = 2 * step
    maximized_inactive_title = rescaled_to_maximized(stops.TITLE["inactive"])
    definitions = "".join(
        [
            frame_definitions("decoration-", ACTIVE),
            frame_definitions("decoration-inactive-", INACTIVE),
            gradient(gradient_id("decoration-maximized-", "t"), stops.TITLE["maximized"], 0, MAX_ROWS, DIGITS),
            gradient(gradient_id("decoration-maximized-inactive-", "t"), maximized_inactive_title, 0, MAX_ROWS, DIGITS),
        ]
    )
    body = "\n".join(
        [
            f"<defs>{definitions}</defs>",
            frame_pieces("decoration-", 0),
            frame_pieces("decoration-inactive-", step),
            maximized_pieces("decoration-maximized-", max_x),
            maximized_pieces("decoration-maximized-inactive-", max_x + max_step),
            mask_pieces(max_x + 2 * max_step),
        ]
    )
    return linked_svg(max_x + 2 * max_step + FRAME_W, FRAME_H, body)


def close_glyph(ink):
    start, end, width = stops.BUTTON_CLOSE_STROKE
    mirrored_start, mirrored_end = round(BUTTON - start, 2), round(BUTTON - end, 2)
    strokes = f"M{start},{start} L{end},{end} M{mirrored_start},{start} L{mirrored_end},{end}"
    return f'<path d="{strokes}" fill="none" stroke="{ink}" stroke-width="{width}"/>'


def glyph_markup(kind, ink):
    return {
        "minimize": plain_rect(5, 13, 7, 3, ink),
        "maximize": f'<path d="M5,5 H16 V16 H5 Z M6,8 V15 H15 V8 Z" fill="{ink}" fill-rule="evenodd"/>',
        "restore": (
            f'<path d="M8,5 H15 V12 H13 V11 H14 V7 H8 Z M5,8 H12 V15 H5 Z M6,10 V14 H11 V10 Z" '
            f'fill="{ink}" fill-rule="evenodd"/>'
        ),
        "close": close_glyph(ink),
        "help": (
            f'<path d="M7,7.5 Q7,4.5 10.5,4.5 Q14,4.5 14,7.5 Q14,9.5 10.5,10.5 V12.5" fill="none" '
            f'stroke="{ink}" stroke-width="2.2"/>{plain_rect(9.5, 14.5, 2, 2, ink)}'
        ),
        "alldesktops": (
            f'<circle cx="10.5" cy="8" r="3.5" fill="{ink}"/>'
            f"{plain_rect(5, 11, 11, 2, ink)}{plain_rect(9.75, 12, 1.5, 5, ink)}"
        ),
        "keepabove": f'<path d="M5,10 L10.5,4.5 L16,10 Z M5,13 H16 V15 H5 Z" fill="{ink}"/>',
        "keepbelow": f'<path d="M5,11 L10.5,16.5 L16,11 Z M5,6 H16 V8 H5 Z" fill="{ink}"/>',
        "shade": f"{plain_rect(5, 5, 11, 4, ink)}{plain_rect(5, 11, 11, 2, ink)}",
    }[kind]


STATE_NAMES = [
    "active",
    "hover",
    "pressed",
    "deactivated",
    "inactive",
    "hover-inactive",
    "pressed-inactive",
    "deactivated-inactive",
]
REUSED_STATES = {5: 1, 6: 2}
FACE_FIT_STATE = {"blue": {7: 7}, "red": {7: 3}}


def own_art_state(color, index):
    return FACE_FIT_STATE[color].get(index, index)


def face_use(paint):
    return f'<use xlink:href="#r" fill="{paint}"/>'


def face_definitions(prefix, art):
    glows = art["glows"]
    shade = art["shade"]
    face_stops = [(y / BUTTON, colour) for y, colour in art["face"]]
    definitions = [linear_gradient(f"{prefix}f", (0, 0), (0, BUTTON), face_stops, 3)]
    definitions += [
        radial_gradient(
            f"{prefix}g{index}",
            glow["centre"],
            glow["radii"],
            [(offset, glow["colour"], opacity) for offset, opacity in glow["stops"]],
            3,
        )
        for index, glow in enumerate(glows)
    ]
    definitions.append(
        linear_gradient(
            f"{prefix}s",
            shade["from"],
            shade["to"],
            [(offset, shade["colour"], opacity) for offset, opacity in shade["stops"]],
            3,
        )
    )
    return "".join(definitions)


def rim_stroke(rim):
    colour, opacity = rim
    return (
        f'<rect x="1.5" y="1.5" width="{BUTTON - 3}" height="{BUTTON - 3}" rx="{stops.BUTTON_RING_RADIUS - 1.5}" '
        f'fill="none" stroke="{colour}" stroke-opacity="{opacity}"/>'
    )


def face_art(prefix, art, kind):
    ring = rounded_rect(0, 0, BUTTON, BUTTON, stops.BUTTON_RING_RADIUS, art["ring"])
    paints = [f"{prefix}f", *(f"{prefix}g{index}" for index in range(len(art["glows"]))), f"{prefix}s"]
    rim = [rim_stroke(art["rim"])] if "rim" in art else []
    return ring + "".join(face_use(url(paint)) for paint in paints) + "".join(rim) + glyph_markup(kind, art["glyph"])


def button_svg(kind):
    color = "red" if kind == "close" else "blue"
    arts = stops.BUTTON_ART[color]
    definitions = [
        f'<rect id="r" x="1" y="1" width="{BUTTON - 2}" height="{BUTTON - 2}" rx="{stops.BUTTON_RING_RADIUS - 1}"/>'
    ]
    groups = []
    for index, name in enumerate(STATE_NAMES):
        element_id = f"{name}-center"
        offset = index * BUTTON_CELL
        placement = "" if index == 0 else f' transform="translate({offset},0)"'
        if index in REUSED_STATES:
            source = REUSED_STATES[index]
            shift = -source * BUTTON_CELL
            groups.append(
                f'<g id="{element_id}"{placement}><use xlink:href="#{STATE_NAMES[source]}-center" '
                f'transform="translate({shift},0)"/></g>'
            )
            continue
        art = arts[own_art_state(color, index)]
        prefix = f"s{index}"
        definitions.append(face_definitions(prefix, art))
        groups.append(f'<g id="{element_id}"{placement}>{face_art(prefix, art, kind)}</g>')
    body = "\n".join([f"<defs>{''.join(definitions)}</defs>", *groups])
    return linked_svg(len(STATE_NAMES) * BUTTON_CELL, BUTTON, body)


RC = """[General]
ActiveTextColor=255,255,255,255
InactiveTextColor=216,228,248,255
TitleAlignment=Left
TitleVerticalAlignment=Center
Animation=0
Shadow=false
UseTextShadow=true
ActiveTextShadowColor=10,24,131,255
InactiveTextShadowColor=0,0,0,0
TextShadowOffsetX=1
TextShadowOffsetY=1
HaloActive=false
HaloInactive=false

[Layout]
TitleHeight={title_h}
TitleEdgeTop={border}
TitleEdgeBottom=0
TitleEdgeLeft=5
TitleEdgeRight=6
TitleEdgeTopMaximized=0
TitleEdgeBottomMaximized=0
TitleEdgeLeftMaximized=3
TitleEdgeRightMaximized=3
TitleBorderLeft={border}
TitleBorderRight={border}
ButtonHeight={button}
ButtonWidth={button}
ButtonWidthMenu=16
ButtonWidthClose={button}
ButtonSpacing=2
ButtonMarginTop=2
ExplicitButtonSpacer=4
BorderLeft={border}
BorderRight={border}
BorderBottom={border}
PaddingTop=0
PaddingBottom=0
PaddingLeft=0
PaddingRight=0
"""

METADATA = """{
  "KPlugin": {
    "Authors": [{ "Name": "Bending Unit 22" }],
    "Id": "Chicago95Luna",
    "License": "GPL-3.0",
    "Name": "Chicago95 Luna",
    "Description": "Chicago95 Windows XP Luna window decoration",
    "Version": "1.0"
  }
}
"""


def write_theme(out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "decoration.svg").write_text(decoration_svg())
    for kind in ("minimize", "maximize", "restore", "close", "help", "alldesktops", "keepabove", "keepbelow", "shade"):
        (out / f"{kind}.svg").write_text(button_svg(kind))
    (out / "Chicago95Lunarc").write_text(RC.format(title_h=TITLE_H, border=BORDER, button=BUTTON))
    (out / "metadata.json").write_text(METADATA)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=HERE / "theme")
    destination = parser.parse_args().out
    write_theme(destination)
    print("wrote", sorted(path.name for path in destination.iterdir()))
