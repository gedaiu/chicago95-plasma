"""Pixel-exact classic bevel frames as plain SVG rects.

QtSvg has no clipPath support, so every nine-slice piece must be drawn
from scratch instead of clipping a shared drawing.
"""

FACE, LIGHT, SHADOW, DARK, HILIGHT = "#C0C0C0", "#DFDFDF", "#808080", "#000000", "#FFFFFF"

RAISED_4 = [(LIGHT, DARK), (HILIGHT, SHADOW), (FACE, FACE), (FACE, FACE)]
RAISED_2 = [(HILIGHT, DARK), (FACE, SHADOW)]
SUNKEN_2 = [(DARK, HILIGHT), (SHADOW, LIGHT)]


def rect(x, y, w, h, fill, extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" shape-rendering="crispEdges"{extra}/>'


def svg(width, height, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n{body}\n</svg>\n'
    )


def hidden(element_id, x, y, w, h):
    return rect(x, y, w, h, "none", f' id="{element_id}"')


def ring_color(px, py, size, rings, interior):
    depth = min(px, py, size - 1 - px, size - 1 - py)
    if depth >= len(rings):
        return interior(px, py)
    top_left, bottom_right = rings[depth]
    # The light lines run along the top and left; the top-right and bottom-left corner pixels belong to
    # the dark lines, as on the originals.
    on_top = py == depth and px != size - 1 - depth
    on_left = px == depth and py != size - 1 - depth
    return top_left if (on_top or on_left) else bottom_right


def run_length_rows(x0, y0, w, h, color_at):
    """Emit the fewest rects: horizontal runs, merged across identical rows."""
    rows = []
    for row in range(h):
        runs, col = [], 0
        while col < w:
            color = color_at(col, row)
            run = 1
            while col + run < w and color_at(col + run, row) == color:
                run += 1
            runs.append((col, run, color))
            col += run
        rows.append(runs)
    out, row = [], 0
    while row < h:
        span = 1
        while row + span < h and rows[row + span] == rows[row]:
            span += 1
        out.extend(rect(x0 + col, y0 + row, run, span, color) for col, run, color in rows[row])
        row += span
    return "".join(out)


def nine_slice(prefix, x0, y0, size, border, rings, interior, margin, tile_center=False, interior_size=None):
    """Emit FrameSvg pieces for a square `size` frame with `border` px edges.

    `interior(px, py)` gives the colour inside the rings in frame coordinates.
    """
    b = border
    inner = size - 2 * b

    def color(px, py):
        return ring_color(px, py, size, rings, interior)

    def piece(name, fx, fy, w, h):
        body = run_length_rows(x0 + fx, y0 + fy, w, h, lambda cx, cy: color(fx + cx, fy + cy))
        return f'<g id="{prefix}{name}">{body}</g>'

    parts = [
        piece("topleft", 0, 0, b, b),
        piece("top", b, 0, inner, b),
        piece("topright", size - b, 0, b, b),
        piece("left", 0, b, b, inner),
        piece("right", size - b, b, b, inner),
        piece("bottomleft", 0, size - b, b, b),
        piece("bottom", b, size - b, inner, b),
        piece("bottomright", size - b, size - b, b, b),
    ]
    center_w = interior_size or inner
    parts.append(
        f'<g id="{prefix}center">'
        + run_length_rows(x0 + b, y0 + b, center_w, center_w, lambda cx, cy: interior(b + cx, b + cy))
        + "</g>"
    )
    sides = margin if isinstance(margin, tuple) else (margin, margin, margin, margin)
    for side, value in zip(("top", "bottom", "left", "right"), sides, strict=False):
        parts.append(hidden(f"{prefix}hint-{side}-margin", x0, y0 + size + 2, value, value))
    if tile_center:
        parts.append(hidden(f"{prefix}hint-tile-center", x0, y0 + size + 8, 1, 1))
    return "\n".join(parts)


CAPTION_W, CAPTION_H = 16, 14


def caption_face(x, y, colours, pressed):
    """A caption button's 16x14 face at (x, y); colours are (face, light, shadow, dark)."""
    face, light, shadow, dark = colours
    tl1, br1, tl2, br2 = (dark, HILIGHT, shadow, light) if pressed else (HILIGHT, dark, light, shadow)
    w, h = CAPTION_W, CAPTION_H
    return (
        rect(x, y, w, h, face)
        + rect(x, y, w, 1, tl1)
        + rect(x, y, 1, h, tl1)
        + rect(x, y + h - 1, w, 1, br1)
        + rect(x + w - 1, y, 1, h, br1)
        + rect(x + 1, y + 1, w - 2, 1, tl2)
        + rect(x + 1, y + 1, 1, h - 2, tl2)
        + rect(x + 1, y + h - 2, w - 2, 1, br2)
        + rect(x + w - 2, y + 1, 1, h - 2, br2)
    )


# Glyphs as (x, y, width, height) runs on the 16x14 face, measured from the originals' buttons.
GLYPHS = {
    "close": [
        (4, 3, 2, 1),
        (10, 3, 2, 1),
        (5, 4, 2, 1),
        (9, 4, 2, 1),
        (6, 5, 4, 1),
        (7, 6, 2, 1),
        (6, 7, 4, 1),
        (5, 8, 2, 1),
        (9, 8, 2, 1),
        (4, 9, 2, 1),
        (10, 9, 2, 1),
    ],
    "minimize": [(4, 9, 6, 2)],
    "maximize": [(3, 2, 9, 2), (3, 2, 1, 9), (11, 2, 1, 9), (3, 10, 9, 1)],
    "restore": [(5, 1, 6, 2), (10, 1, 1, 6), (8, 6, 3, 1), (2, 4, 6, 2), (2, 4, 1, 6), (7, 4, 1, 6), (2, 9, 6, 1)],
    "help": [(6, 2, 4, 1), (5, 3, 2, 2), (9, 3, 2, 2), (8, 5, 2, 1), (7, 6, 2, 2), (7, 9, 2, 2)],
    "alldesktops": [(7, 2, 2, 3), (4, 5, 8, 2), (5, 7, 6, 1), (7, 8, 2, 4)],
    "keepabove": [(7, 2, 2, 2), (5, 4, 6, 2), (3, 6, 10, 2), (4, 9, 8, 2)],
    "keepbelow": [(4, 2, 8, 2), (3, 5, 10, 2), (5, 7, 6, 2), (7, 9, 2, 2)],
    "shade": [(3, 3, 10, 2), (3, 6, 10, 2)],
}


def caption_glyph(kind, color, x, y):
    """The glyph's runs on a face whose corner is (x, y)."""
    return "".join(rect(x + gx, y + gy, w, h, color) for gx, gy, w, h in GLYPHS[kind])
