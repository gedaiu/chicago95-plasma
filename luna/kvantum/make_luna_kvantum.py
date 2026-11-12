"""Builds the Chicago95Luna Kvantum theme: the Windows XP Luna widget look for every Qt and KDE application.

    make_luna_kvantum.py [--out DIR]

Writes Chicago95Luna.svg and Chicago95Luna.kvconfig into DIR (default Chicago95Luna beside this file). Every element is
simple vector geometry: rectangles, one pixel arcs and gradients, cut into the nine pieces Kvantum expects. The colours,
gradients and sizes live in stops.py (LunaStyle's measured values), the push button body in luna/plasma-style/stops.py
and the title bar in luna/palette.py.
"""

import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LUNA_ROOT = HERE.parent
THEME_NAME = "Chicago95Luna"
EDGE_LENGTH = 8
PIECES = ("topleft", "top", "topright", "left", "right", "bottomleft", "bottom", "bottomright")
CORNER_SIDES = {
    "topleft": ("top", "left"),
    "topright": ("top", "right"),
    "bottomleft": ("bottom", "left"),
    "bottomright": ("bottom", "right"),
}
CANVAS_WIDTH = 24
GAP = 2


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


palette = load_module("luna_palette", LUNA_ROOT / "palette.py")
stops = load_module("luna_kvantum_stops", HERE / "stops.py")
plasma_stops = load_module("luna_plasma_stops", LUNA_ROOT / "plasma-style/stops.py")


def number(value):
    return f"{value:g}"


def rect(x, y, width, height, fill):
    return f'<rect x="{number(x)}" y="{number(y)}" width="{number(width)}" height="{number(height)}" fill="{fill}"/>'


def hidden_bounds(width, height):
    return f'<rect width="{number(width)}" height="{number(height)}" fill-opacity="0"/>'


def runs(values):
    kept = []
    for index, value in enumerate(values):
        previous = values[index - 1] if index else None
        following = values[index + 1] if index + 1 < len(values) else None
        if value != previous or value != following:
            kept.append((index / (len(values) - 1), value))
    return kept


def button_body_gradient():
    rows = plasma_stops.BUTTON["body"]
    first, last = rows[0][0], rows[-1][0]
    return [((row - first) / (last - first), colour) for row, colour in rows]


def gradient_table():
    return {
        **stops.GRADIENTS,
        "button-body": button_body_gradient(),
        "title-active": runs(palette.PALETTE["title_active"]),
        "title-inactive": runs(palette.PALETTE["title_inactive"]),
    }


class Sheet:
    def __init__(self):
        self.gradients = gradient_table()
        self.definitions = []
        self.defined = set()
        self.elements = []
        self.cursor = 0

    def paint(self, gradient_name):
        stop_list = self.gradients[gradient_name]
        colours = {colour for _, colour in stop_list}
        if len(colours) == 1:
            return colours.pop()
        if gradient_name not in self.defined:
            self.defined.add(gradient_name)
            rows = "".join(
                f'<stop offset="{number(round(offset, 3))}" stop-color="{colour}"/>' for offset, colour in stop_list
            )
            self.definitions.append(
                f'<linearGradient id="{gradient_name}" x1="0" y1="0" x2="0" y2="1">{rows}</linearGradient>'
            )
        return f"url(#{gradient_name})"

    def place(self, element_id, width, height, shapes, bounds=False):
        content = (hidden_bounds(width, height) if bounds else "") + shapes
        self.elements.append(f'<g id="{element_id}" transform="translate(0 {self.cursor})">{content}</g>')
        self.cursor += height + GAP

    def document(self):
        defs = f"<defs>{''.join(self.definitions)}</defs>" if self.definitions else ""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH}" height="{self.cursor}" '
            f'viewBox="0 0 {CANVAS_WIDTH} {self.cursor}">{defs}{"".join(self.elements)}</svg>\n'
        )


def mirrored_rect(x, y, width, height, size, flip_x, flip_y):
    return (size - x - width if flip_x else x), (size - y - height if flip_y else y), width, height


def corner_shapes(corner, size, radius, sides, fill):
    vertical_side, horizontal_side = CORNER_SIDES[corner]
    flip_y, flip_x = vertical_side == "bottom", horizontal_side == "right"
    along_edge, along_side = sides[vertical_side], sides[horizontal_side]
    levels = max(len(along_edge), len(along_side))
    colours = [along_edge[level] if level < len(along_edge) else along_side[level] for level in range(levels)]
    shapes = []
    if radius:
        sweep = 0 if flip_x != flip_y else 1
        px = (lambda x: size - x) if flip_x else (lambda x: x)
        py = (lambda y: size - y) if flip_y else (lambda y: y)
        if fill:
            shapes.append(
                f'<path d="M{px(0)} {py(size)}A{size} {size} 0 0 {sweep} {px(size)} {py(0)}L{px(size)} {py(size)}z" fill="{fill}"/>'
            )
        for level, colour in enumerate(colours):
            outer, inner = radius - level, radius - level - 1
            shapes.append(
                f'<path d="M{px(level)} {py(size)}A{outer} {outer} 0 0 {sweep} {px(size)} {py(level)}'
                f'L{px(size)} {py(level + 1)}A{inner} {inner} 0 0 {1 - sweep} {px(level + 1)} {py(size)}z" fill="{colour}"/>'
            )
        return "".join(shapes), True
    if fill:
        shapes.append(rect(0, 0, size, size, fill))
    for level in range(levels):
        horizontal_present, vertical_present = level < len(along_edge), level < len(along_side)
        if horizontal_present:
            shapes.append(rect(*mirrored_rect(level, level, size - level, 1, size, flip_x, flip_y), colours[level]))
        if vertical_present:
            top = level + 1 if horizontal_present else 0
            shapes.append(rect(*mirrored_rect(level, top, 1, size - top, size, flip_x, flip_y), colours[level]))
    return "".join(shapes), fill is None


def edge_shapes(piece, size, sides, fill_paint):
    rings = sides[piece]
    depth = len(rings)
    horizontal = piece in ("top", "bottom")
    far = piece in ("bottom", "right")
    shapes = []
    if fill_paint and depth < size:
        origin = 0 if far else depth
        shapes.append(
            rect(0, origin, EDGE_LENGTH, size - depth, fill_paint)
            if horizontal
            else rect(origin, 0, size - depth, EDGE_LENGTH, fill_paint)
        )
    for level, colour in enumerate(rings):
        position = size - 1 - level if far else level
        shapes.append(
            rect(0, position, EDGE_LENGTH, 1, colour) if horizontal else rect(position, 0, 1, EDGE_LENGTH, colour)
        )
    return "".join(shapes), fill_paint is None


def edge_fill_paint(sheet, piece, fill_name):
    if fill_name is None:
        return None
    if piece == "top":
        return sheet.gradients[fill_name][0][1]
    if piece == "bottom":
        return sheet.gradients[fill_name][-1][1]
    return sheet.paint(fill_name)


def add_frame(sheet, prefix, spec):
    size, radius = spec["size"], spec["radius"]
    for state, look in spec["states"].items():
        name = f"{prefix}-{state}"
        sides, fill_name = look["sides"], look["fill"]
        if fill_name:
            sheet.place(name, EDGE_LENGTH, EDGE_LENGTH, rect(0, 0, EDGE_LENGTH, EDGE_LENGTH, sheet.paint(fill_name)))
        for piece in PIECES:
            if piece in CORNER_SIDES:
                fill = sheet.gradients[fill_name][0 if piece.startswith("top") else -1][1] if fill_name else None
                shapes, bounds = corner_shapes(piece, size, radius, sides, fill)
                sheet.place(f"{name}-{piece}", size, size, shapes, bounds)
                continue
            shapes, bounds = edge_shapes(piece, size, sides, edge_fill_paint(sheet, piece, fill_name))
            horizontal = piece in ("top", "bottom")
            sheet.place(
                f"{name}-{piece}",
                EDGE_LENGTH if horizontal else size,
                size if horizontal else EDGE_LENGTH,
                shapes,
                bounds,
            )


def polygon(points, fill):
    return f'<polygon points="{" ".join(f"{number(x)},{number(y)}" for x, y in points)}" fill="{fill}"/>'


def arrow_shapes(direction, colour):
    triangles = {
        "up": [(1.5, 6), (7.5, 6), (4.5, 3)],
        "down": [(1.5, 3), (7.5, 3), (4.5, 6)],
        "left": [(6, 1.5), (6, 7.5), (3, 4.5)],
        "right": [(3, 1.5), (3, 7.5), (6, 4.5)],
    }
    if direction in triangles:
        return polygon(triangles[direction], colour)
    box = f'<rect x=".5" y=".5" width="8" height="8" fill="{stops.TREE_BOX_FILL}" stroke="{stops.TREE_BOX_BORDER}"/>'
    bar = rect(2, 4, 5, 1, colour)
    return box + bar + (rect(4, 2, 1, 5, colour) if direction == "plus" else "")


def add_arrows(sheet):
    for direction in stops.ARROW_DIRECTIONS:
        for state, colour in stops.ARROW_STATES.items():
            sheet.place(
                f"arrow-{direction}-{state}", stops.GLYPH_SIZE, stops.GLYPH_SIZE, arrow_shapes(direction, colour), True
            )


def pixel_path(pattern, left, top, colour):
    segments = []
    for row_index, row in enumerate(pattern):
        start = 0
        while start < len(row):
            if row[start] != "#":
                start += 1
                continue
            end = start
            while end < len(row) and row[end] == "#":
                end += 1
            segments.append(f"M{left + start} {top + row_index}h{end - start}v1h-{end - start}z")
            start = end
    return f'<path d="{"".join(segments)}" fill="{colour}"/>'


def square_glow(size, light, dark):
    shapes = []
    for depth in (1, 2):
        span = size - 2 * depth
        shapes += [
            rect(depth, depth, span, 1, light),
            rect(depth, depth, 1, span, light),
            rect(depth, size - 1 - depth, span, 1, dark),
            rect(size - 1 - depth, depth, 1, span, dark),
        ]
    return "".join(shapes)


def round_glow(centre, light, dark):
    return "".join(
        f'<circle cx="{centre}" cy="{centre}" r="{centre - depth - 0.5}" fill="none" stroke="{colour}"/>'
        for depth, colour in ((1, light), (2, dark))
    )


def indicator_shapes(sheet, look, round_shape, mark_colour):
    size = stops.INDICATOR_SIZE
    paint = sheet.paint(look["fill"])
    centre = size / 2
    glow = look["glow"] or ()
    if round_shape:
        body = f'<circle cx="{centre}" cy="{centre}" r="{centre - 0.5}" fill="{paint}" stroke="{look["border"]}"/>'
        mark = f'<circle cx="{centre}" cy="{centre}" r="2.5" fill="{mark_colour}"/>' if mark_colour else ""
        return body + (round_glow(centre, *glow) if glow else "") + mark
    body = (
        f'<rect x=".5" y=".5" width="{size - 1}" height="{size - 1}" rx="1" fill="{paint}" stroke="{look["border"]}"/>'
    )
    offset = (size - len(stops.CHECK_TICK[0])) // 2
    mark = pixel_path(stops.CHECK_TICK, offset, offset, mark_colour) if mark_colour else ""
    return body + (square_glow(size, *glow) if glow else "") + mark


def add_indicators(sheet):
    for kind, variants in stops.CHECK_KINDS.items():
        for variant in variants:
            for state, look in stops.CHECK_LOOK.items():
                mark = None
                if variant:
                    mark = (
                        stops.CHECK_MARK if variant == "checked" and state != "disabled" else stops.CHECK_MARK_DISABLED
                    )
                name = "-".join(part for part in (kind, variant, state) if part)
                sheet.place(
                    name,
                    stops.INDICATOR_SIZE,
                    stops.INDICATOR_SIZE,
                    indicator_shapes(sheet, look, kind == "radio", mark),
                    True,
                )


def slider_cursor_shapes(sheet, look):
    outline = [(0.5, 0.5), (10.5, 0.5), (10.5, 14.5), (5.5, 19.5), (0.5, 14.5)]
    points = " ".join(f"{x},{y}" for x, y in outline)
    ring = (
        f'<polygon points="1.5,1.5 9.5,1.5 9.5,14 5.5,18 1.5,14" fill="none" stroke="{look["glow"][1]}"/>'
        if look["glow"]
        else ""
    )
    return f'<polygon points="{points}" fill="{sheet.paint(look["fill"])}" stroke="{look["border"]}"/>' + ring


def add_slider_cursors(sheet):
    looks = {**stops.CHECK_LOOK, "normal": {**stops.CHECK_LOOK["normal"], "fill": "slider-thumb"}}
    for state, look in looks.items():
        sheet.place(
            f"slidercursor-{state}", stops.SIZES["slider_handle_width"], 20, slider_cursor_shapes(sheet, look), True
        )


def add_solids(sheet):
    for prefix, states in stops.SOLIDS.items():
        for state in states:
            sheet.place(
                f"{prefix}-{state}",
                EDGE_LENGTH,
                EDGE_LENGTH,
                rect(0, 0, EDGE_LENGTH, EDGE_LENGTH, sheet.paint("selection")),
            )
    for name, gradient in stops.BOXES.items():
        sheet.place(name, EDGE_LENGTH, EDGE_LENGTH, rect(0, 0, EDGE_LENGTH, EDGE_LENGTH, sheet.paint(gradient)))
    for name, gradient in (("titlebar-focused", "title-active"), ("titlebar-normal", "title-inactive")):
        sheet.place(
            name,
            EDGE_LENGTH,
            len(palette.PALETTE["title_active"]),
            rect(0, 0, EDGE_LENGTH, len(palette.PALETTE["title_active"]), sheet.paint(gradient)),
        )


def add_progress(sheet):
    tile = stops.PROGRESS_CHUNK_WIDTH + stops.PROGRESS_CHUNK_GAP
    height = stops.PROGRESS_CHUNK_HEIGHT
    for state, paint in (("normal", sheet.paint("progress-chunk")), ("disabled", sheet.paint("face-pressed"))):
        sheet.place(
            f"progress-pattern-{state}", tile, height, rect(0, 0, stops.PROGRESS_CHUNK_WIDTH, height, paint), True
        )


def add_default_indicator(sheet):
    ring = f'<rect x="1" y="1" width="22" height="{stops.SIZES["button_height"] - 2}" rx="2" fill="none" stroke="{sheet.paint("default-ring")}" stroke-width="2"/>'
    sheet.place("button-default-indicator", 24, stops.SIZES["button_height"], ring, True)


def add_decorations(sheet):
    grip_lines = "".join(rect(x, 1, 1, 7, "#6F8DDB") + rect(x + 1, 1, 1, 7, "#FFFFFF") for x in (1, 3, 5, 7))
    for state in ("normal", "focused", "pressed"):
        sheet.place(f"grip-{state}", 9, 9, grip_lines, True)
    sheet.place("header-separator", 2, 16, rect(0, 0, 1, 16, stops.MENU_BORDER) + rect(1, 0, 1, 16, "#FFFFFF"))
    handle_dots = "".join(
        rect(x, y, 2, 2, "#FFFFFF") + rect(x - 1, y - 1, 2, 2, "#A0A096") for x in (2, 5) for y in (2, 5, 8, 11)
    )
    sheet.place("toolbar-handle", 7, 14, handle_dots, True)
    grip_dots = "".join(
        rect(x + 1, y + 1, 2, 2, "#FFFFFF") + rect(x, y, 2, 2, stops.MENU_BORDER)
        for row in range(4)
        for x, y in [(10 - 3 * column, 1 + 3 * row) for column in range(4 - row)]
    )
    sheet.place("sizegrip-normal", 14, 14, grip_dots, True)
    for side, (width, height) in {"top": (20, 1), "bottom": (20, 1), "left": (1, 20), "right": (1, 20)}.items():
        dashes = (
            f'<path d="M0 .5H{width}" stroke-dasharray="1 1"'
            if width > height
            else f'<path d="M.5 0V{height}" stroke-dasharray="1 1"'
        )
        sheet.place(f"focus-{side}", width, height, f'{dashes} stroke="{stops.FOCUS_DOTS}" fill="none"/>', True)


def build_svg():
    sheet = Sheet()
    for prefix, spec in stops.FRAMES.items():
        add_frame(sheet, prefix, spec)
    add_arrows(sheet)
    add_indicators(sheet)
    add_slider_cursors(sheet)
    add_solids(sheet)
    add_progress(sheet)
    add_default_indicator(sheet)
    add_decorations(sheet)
    return sheet.document()


def resolve_colour(value):
    return {"face": palette.PALETTE["face"], "selection": palette.PALETTE["selection"]}.get(value, value)


def section_lines(name, entries):
    return [f"[{name}]", *(f"{key}={value}" for key, value in entries.items()), ""]


def build_kvconfig():
    general = {**stops.KVCONFIG_GENERAL}
    sizes = stops.SIZES
    general.update(
        scroll_width=sizes["scrollbar"],
        slider_width=sizes["slider_groove"],
        slider_handle_width=sizes["slider_handle_width"],
        slider_handle_length=sizes["slider_handle_length"],
        spin_button_width=sizes["spin_button_width"],
        splitter_width=sizes["splitter"],
    )
    colours = {key: resolve_colour(value) for key, value in stops.KVCONFIG_COLORS.items()}
    lines = section_lines("%General", general) + section_lines("GeneralColors", colours)
    for name, entries in stops.SECTIONS.items():
        lines += section_lines(name, entries)
    return "\n".join(lines)


def write_theme(out):
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{THEME_NAME}.svg").write_text(build_svg())
    (out / f"{THEME_NAME}.kvconfig").write_text(build_kvconfig())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=HERE / THEME_NAME)
    options = parser.parse_args()
    write_theme(options.out)
    print("wrote", options.out)
