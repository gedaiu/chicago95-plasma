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


def nine_slice(
    prefix, x0, y0, size, border, rings, interior, margin, tile_center=False, interior_size=None, center_fill=None
):
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
    if center_fill is not None:
        centre = rect(x0 + b, y0 + b, center_w, center_w, center_fill)
    else:
        centre = run_length_rows(x0 + b, y0 + b, center_w, center_w, lambda cx, cy: interior(b + cx, b + cy))
    parts.append(f'<g id="{prefix}center">{centre}</g>')
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

    def rim(inset, top_left, bottom_right):
        # The darker side owns both shared corner pixels.
        left, top = x + inset, y + inset
        width, height = w - 2 * inset, h - 2 * inset
        end, foot = left + width, top + height
        light_edge = f"M{left} {top}H{end - 1}v1H{left + 1}V{foot - 1}h-1z"
        dark_edge = f"M{end - 1} {top}h1V{foot}H{left}v-1H{end - 1}z"
        return f'<path d="{light_edge}" fill="{top_left}"/><path d="{dark_edge}" fill="{bottom_right}"/>'

    return rect(x, y, w, h, face) + rim(0, tl1, br1) + rim(1, tl2, br2)


# Closed outlines retain the deliberately stepped pixels of the classic 16×14 masters.
GLYPHS = {
    "close": (
        "M4 4h1v1h1v1h1v1h-1v1h-1v1h-1v1h2v-1h1v-1h2v1h1v1h2v-1h-1v-1h-1v-1"
        "h-1v-1h1v-1h1v-1h1v-1h-2v1h-1v1h-2v-1h-1v-1h-2z"
    ),
    "minimize": "M10 9h-6v2h6z",
    "maximize": "M3 11h9v-9h-9zM4 4h7v6h-7z",
    "restore": "M2 10h6v-3h3v-6h-6v2h5v3h-2v-2h-6zM3 9v-3h4v3z",
    "help": "M6 2v1h-1v2h2v-2h2v2h-1v1h-1v2h2v-2h1v-1h1v-2h-1v-1zM7 11h2v-2h-2z",
    "alldesktops": "M7 5h-3v2h1v1h2v4h2v-4h2v-1h1v-2h-3v-3h-2z",
    "keepabove": "M7 4h-2v2h-2v2h10v-2h-2v-2h-2v-2h-2zM4 11h8v-2h-8z",
    "keepbelow": "M4 4h8v-2h-8zM3 7h2v2h2v2h2v-2h2v-2h2v-2h-10z",
    "shade": "M3 3v2h10v-2zM3 6v2h10v-2z",
}


def caption_glyph(kind, color, x, y):
    return f'<path transform="translate({x} {y})" d="{GLYPHS[kind]}" fill="{color}" fill-rule="evenodd"/>'
