"""Nine-slice frames for the Luna Plasma theme, drawn as one vector shape.

A frame is one rounded rectangle (FrameSpec): a vertical gradient fill, one pixel rings, optionally a glow and a shade
over the fill and a halo outside the right end. Each of the nine pieces is that shape written out for its own box
(luna.region), which puts the piece boundaries where the shape is straight and gives each corner piece a true arc.
The fill gradient is defined once in user space over the whole shape, so every piece shares one continuous fill:

  top, bottom, center  the fill path, the rings being hard bands of the gradient
  left, right          the fill path and one even-odd ring path painted with a horizontal gradient of hard bands
  corners              one path painted with a radial gradient of hard bands (ring colours, then the body)

A ring is a fill rather than a stroke: QtSvg grows an element's bounds by half the stroke width, and the pieces are
sized by their bounds. A ring side is None (transparent), a colour or, for a side that fades, a list of (row, colour).
"""

import importlib.util
import re
import sys
from dataclasses import dataclass
from pathlib import Path


def load_primitives():
    if "luna_primitives" not in sys.modules:
        path = Path(__file__).resolve().parent.parent / "aurorae" / "luna.py"
        spec = importlib.util.spec_from_file_location("luna_primitives", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["luna_primitives"] = module
        spec.loader.exec_module(module)
    return sys.modules["luna_primitives"]


primitives = load_primitives()
Box, fill_region, inset, region, ring_region, shape_of = (
    primitives.Box,
    primitives.fill_region,
    primitives.inset,
    primitives.region,
    primitives.ring_region,
    primitives.shape_of,
)

SIDES = ("left", "right", "top", "bottom")
HINT_ROOM = 12
CORNER_SIDES = {
    "topleft": ("left", "top"),
    "topright": ("right", "top"),
    "bottomleft": ("left", "bottom"),
    "bottomright": ("right", "bottom"),
}
CORNER_RADIUS_INDEX = {"topleft": 0, "topright": 1, "bottomright": 2, "bottomleft": 3}


@dataclass(frozen=True)
class FrameSpec:
    width: int
    height: int
    edges: tuple
    margins: tuple
    radii: tuple = (0, 0, 0, 0)
    body: object = None
    rings: tuple = ()
    halo: object = None
    glow: object = None
    shade: tuple = ()


def boxes_of(spec, x0):
    left, right, top, bottom = spec.edges
    columns = {
        "left": (x0, left),
        "": (x0 + left, spec.width - left - right),
        "right": (x0 + spec.width - right, right),
    }
    rows = {"top": (0, top), "": (top, spec.height - top - bottom), "bottom": (spec.height - bottom, bottom)}
    return {
        (row_name + column_name) or "center": Box(x, y, w, h)
        for row_name, (y, h) in rows.items()
        for column_name, (x, w) in columns.items()
    }


def pill_shape(spec, x0):
    grow = spec.halo["width"] if spec.halo else 0
    return shape_of(x0, 0, spec.width - grow, spec.height, spec.radii)


def halo_shape(spec, x0):
    grow = spec.halo["width"]
    top_left, top_right, bottom_right, bottom_left = spec.radii
    radii = (top_left, (top_right[0] + grow, top_right[1]), (bottom_right[0] + grow, bottom_right[1]), bottom_left)
    return shape_of(x0, 0, spec.width, spec.height, radii)


TRANSPARENT = ("#000000", 0)


def short(value):
    text = f"{value:.4g}"
    return text[1:] if text.startswith("0.") else "-" + text[2:] if text.startswith("-0.") else text


def stop_markup(offset, colour, opacity=1):
    colour_attribute = "" if opacity == 0 else f' stop-color="{colour}"'
    opacity_attribute = "" if opacity == 1 else f' stop-opacity="{short(opacity)}"'
    return f'<stop offset="{short(offset)}"{colour_attribute}{opacity_attribute}/>'


def gradient_markup(kind, gradient_id, attributes, stops):
    stop_list = "".join(stop_markup(*stop) for stop in stops)
    return f'<{kind} id="{gradient_id}" {attributes}>{stop_list}</{kind}>'


def linear_gradient(gradient_id, start, end, stops):
    attributes = (
        f'gradientUnits="userSpaceOnUse" x1="{short(start[0])}" y1="{short(start[1])}" '
        f'x2="{short(end[0])}" y2="{short(end[1])}"'
    )
    return gradient_markup("linearGradient", gradient_id, attributes, stops)


def radial_gradient(gradient_id, centre, radii, stops):
    if radii[0] == radii[1]:
        attributes = f'gradientUnits="userSpaceOnUse" cx="{short(centre[0])}" cy="{short(centre[1])}" r="{short(radii[0])}"'
    else:
        attributes = (
            f'gradientUnits="userSpaceOnUse" cx="0" cy="0" r="1" gradientTransform="translate({short(centre[0])} {short(centre[1])}) '
            f'scale({short(radii[0])} {short(radii[1])})"'
        )
    return gradient_markup("radialGradient", gradient_id, attributes, stops)


def lerp_colour(a, b, amount):
    mixed = (
        int(a[index : index + 2], 16) * (1 - amount) + int(b[index : index + 2], 16) * amount for index in (1, 3, 5)
    )
    return "#" + "".join(f"{round(value):02X}" for value in mixed)


def colour_at(stops, offset):
    """The colour of (offset, colour) stops at the offset, clamped at both ends."""
    if offset <= stops[0][0]:
        return stops[0][1]
    for (start, first), (end, second) in zip(stops, stops[1:], strict=False):
        if start <= offset <= end:
            return lerp_colour(first, second, (offset - start) / (end - start) if end > start else 0)
    return stops[-1][1]


def band_stops(colours, first_row, height):
    """Hard one pixel bands for the ring colours (outermost first), None being transparent."""
    stops = []
    for index, colour in enumerate(colours):
        paint = (colour, 1) if colour else TRANSPARENT
        stops += [((first_row + index) / height, *paint), ((first_row + index + 1) / height, *paint)]
    return stops


def banded_stops(spec):
    """The fill gradient's stops: the top rings as bands, the body between them, the bottom rings as bands."""
    height, depth = spec.height, len(spec.rings)
    first, last = depth / height, 1 - depth / height
    if spec.body is None:
        inner = [(first, "#000000", 0), (last, "#000000", 0)]
    else:
        interior = [((row + 0.5) / height, colour) for row, colour in body_stops(spec)]
        middle = [stop for stop in interior if first < stop[0] < last]
        inner = [
            (offset, colour, 1)
            for offset, colour in [(first, colour_at(interior, first)), *middle, (last, colour_at(interior, last))]
        ]
    top = band_stops([ring.get("top") for ring in spec.rings], 0, height)
    bottom = band_stops([ring.get("bottom") for ring in reversed(spec.rings)], height - depth, height)
    return top + inner + bottom


def body_stops(spec):
    return [(0, spec.body), (spec.height - 1, spec.body)] if isinstance(spec.body, str) else spec.body


def body_colour_at(spec, y):
    """The body colour at pixel row y (fractional), or None when the frame has no body."""
    if spec.body is None:
        return None
    return colour_at([((row + 0.5) / spec.height, colour) for row, colour in body_stops(spec)], y / spec.height)


def fill_paint(prefix, spec, box):
    """The paint of a piece's fill: a plain colour where the piece lies between the rings' rows, else the gradient."""
    depth = len(spec.rings)
    between_rings = depth <= box.y and box.y + box.h <= spec.height - depth
    if between_rings and (spec.body is None or isinstance(spec.body, str)):
        return spec.body
    return f"url(#{prefix}fill)"


def fill_definition(prefix, spec):
    return linear_gradient(f"{prefix}fill", (0, 0), (0, spec.height), banded_stops(spec))


def pill_right_edge(spec, x0):
    return x0 + spec.width - (spec.halo["width"] if spec.halo else 0)


def glows_of(spec):
    return [spec.glow] if isinstance(spec.glow, dict) else list(spec.glow or [])


def glow_definition(prefix, index, glow, x0):
    colour = glow.get("colour", "#FFFFFF")
    stops = [(0, colour, glow["opacity"]), (1, colour, 0)]
    return radial_gradient(f"{prefix}glow{index}", (x0 + glow["centre"][0], glow["centre"][1]), glow["radii"], stops)


def shade_definition(prefix, spec, x0):
    """A black gradient across the frame; shade is (column from the left edge, opacity) in ascending columns."""
    first, last = spec.shade[0][0], spec.shade[-1][0]
    stops = [((column - first) / (last - first), "#000000", opacity) for column, opacity in spec.shade]
    return linear_gradient(f"{prefix}shade", (x0 + first, 0), (x0 + last, 0), stops)


def shaded_columns(spec, x0):
    """The (left, right) column ranges where the shade is not transparent."""
    ranges = [
        (x0 + start, x0 + end)
        for (start, opacity), (end, following) in zip(spec.shade, spec.shade[1:], strict=False)
        if opacity or following
    ]
    return ranges


def washes_markup(prefix, name, box, spec, x0, shape):
    parts = []
    for index, glow in enumerate(glows_of(spec)):
        if name in glow.get("pieces", STRIPS):
            parts.append(fill_region(shape, box, f"url(#{prefix}glow{index})"))
    if any(box.x < end and start < box.x + box.w for start, end in shaded_columns(spec, x0)):
        parts.append(fill_region(shape, box, f"url(#{prefix}shade)"))
    return "".join(parts)


def halo_markup(spec, box, x0):
    reach = max(primitives.corner_radii(spec.radii[1])[0], primitives.corner_radii(spec.radii[2])[0])
    if box.x + box.w <= pill_right_edge(spec, x0) - reach:
        return ""
    outer, inner = region(halo_shape(spec, x0), box), region(pill_shape(spec, x0), box)
    if not outer:
        return ""
    halo = spec.halo
    return f'<path d="{outer} {inner}" fill="{halo["colour"]}" fill-opacity="{halo["opacity"]}" fill-rule="evenodd"/>'


STRIPS = ("top", "bottom", "center")


def lies_in_one_pixel_ring(spec, name, box):
    """A piece of a square frame with a one pixel ring that lies wholly inside the ring."""
    square = not any(any(primitives.corner_radii(radius)) for radius in spec.radii)
    thin = {"left": box.w <= 1, "right": box.w <= 1, "top": box.h <= 1, "bottom": box.h <= 1}
    fits = thin.get(name, box.w <= 1 and box.h <= 1) if name != "center" else False
    return square and len(spec.rings) == 1 and fits


def band_markup(spec, name, box):
    ring = spec.rings[0]
    sides = CORNER_SIDES.get(name, (name,))
    colour = next((ring.get(side) for side in sides if ring.get(side)), None)
    return fill_region(shape_of(box.x, box.y, box.w, box.h, (0, 0, 0, 0)), box, colour) if colour else ""


def ring_definition(prefix, spec, x0):
    """One horizontal gradient across the shape that paints the left and right rings: each side's colours as hard one
    pixel bands, outermost ring first."""
    depth, width = len(spec.rings), pill_shape(spec, x0).w
    left = [ring.get("left") for ring in spec.rings]
    right = [ring.get("right") for ring in reversed(spec.rings)]
    bands = band_stops(left, 0, width) + band_stops(right, width - depth, width)
    return linear_gradient(f"{prefix}ring", (x0, 0), (x0 + width, 0), bands)


def fades(spec, name):
    return any(isinstance(ring.get(name), list) for ring in spec.rings)


def fading_ring_definition(prefix, name, spec):
    stops = [((row + 0.5) / spec.height, colour) for row, colour in spec.rings[0][name]]
    return linear_gradient(f"{prefix}ring-{name}", (0, 0), (0, spec.height), stops)


def ring_paint(prefix, name, spec):
    """([definitions], paint) of a side's rings: a vertical gradient for a side that fades, the colour of a single ring,
    else the shared horizontal bands."""
    if fades(spec, name):
        return [fading_ring_definition(prefix, name, spec)], f"url(#{prefix}ring-{name})"
    if len(spec.rings) == 1:
        return [], spec.rings[0][name]
    return [], f"url(#{prefix}ring)"


def follows_arc(shape, name, depth):
    """Whether the side's corner arcs are wide enough that its rings must follow the outline."""
    corners = (0, 3) if name == "left" else (1, 2)
    return max(shape.radii[corner][0] for corner in corners) > 2 * depth


def side_markup(prefix, name, box, spec, shape, fill):
    depth = len(spec.rings)
    unpainted = next((index for index, ring in enumerate(spec.rings) if ring.get(name)), depth)
    body_box = Box(box.x + (unpainted if name == "left" else 0), box.y, box.w - unpainted, box.h)
    parts = [fill_region(shape, body_box, fill)] if fill else []
    if not any(ring.get(name) for ring in spec.rings):
        return [], parts
    definitions, paint = ring_paint(prefix, name, spec)
    if follows_arc(shape, name, depth):
        return definitions, [*parts, ring_region(shape, box, depth, paint)]
    stripe = Box(box.x if name == "left" else box.x + box.w - depth, box.y, depth, box.h)
    return definitions, [*parts, fill_region(shape, stripe, paint)]


def corner_stops(spec, name, centre_y, radius):
    """The radial stops of a corner, from the centre out: the body, then a hard band for each ring, the last band
    being the padding."""
    top = name.startswith("top")
    depth = len(spec.rings)
    body = body_colour_at(spec, centre_y + (-1 if top else 1) * (radius - depth) / 2)
    stops = [((radius - depth) / radius, *((body, 1) if body else TRANSPARENT))]
    for index in reversed(range(depth)):
        colour = next((spec.rings[index].get(side) for side in CORNER_SIDES[name] if spec.rings[index].get(side)), None)
        paint = (colour, 1) if colour else TRANSPARENT
        stops += [((radius - index - 1) / radius, *paint), ((radius - index) / radius, *paint)]
    return stops[:-1]


def corner_markup(prefix, name, box, spec, shape):
    """The corner as one path under a radial gradient: the body inside, then a hard band for each ring. The corners
    on one side of the frame take their stops from one shared gradient."""
    radius, _ = shape.radii[CORNER_RADIUS_INDEX[name]]
    left, top = name.endswith("left"), name.startswith("top")
    centre_x = shape.x + radius if left else shape.x + shape.w - radius
    centre_y = shape.y + radius if top else shape.y + shape.h - radius
    stops_id, gradient_id = f"{prefix}{'top' if top else 'bottom'}-corners", f"{prefix}{name}-fill"
    stops = gradient_markup("radialGradient", stops_id, "", corner_stops(spec, name, centre_y, radius))
    attributes = (
        f'gradientUnits="userSpaceOnUse" cx="{short(centre_x)}" cy="{short(centre_y)}" r="{short(radius)}" '
        f'xlink:href="#{stops_id}"'
    )
    definitions = [stops, gradient_markup("radialGradient", gradient_id, attributes, [])]
    return definitions, [fill_region(shape, box, f"url(#{gradient_id})")]


def piece_markup(prefix, name, box, spec, x0):
    shape = pill_shape(spec, x0)
    if lies_in_one_pixel_ring(spec, name, box):
        return [], band_markup(spec, name, box)
    fill = fill_paint(prefix, spec, box)
    rounded = name in CORNER_SIDES and any(primitives.corner_radii(spec.radii[CORNER_RADIUS_INDEX[name]]))
    if rounded:
        definitions, parts = corner_markup(prefix, name, box, spec, shape)
    elif name in STRIPS or name in CORNER_SIDES:
        definitions, parts = [], [fill_region(shape, box, fill)] if fill else []
    else:
        definitions, parts = side_markup(prefix, name, box, spec, shape, fill)
    parts.insert(1 if parts else 0, washes_markup(prefix, name, box, spec, x0, shape))
    if spec.halo:
        parts.append(halo_markup(spec, box, x0))
    return definitions, "".join(parts)


def path_extent(markup):
    """Bounding box of the end points of every path in the markup, or None if there is none."""
    points = [
        (float(x), float(y))
        for data in re.findall(r' d="([^"]+)"', markup)
        for x, y in re.findall(r"(-?[\d.]+),(-?[\d.]+)", re.sub(r"A[\d.]+,[\d.]+ 0 0 1", "", data))
    ]
    if not points:
        return None
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def bounds_markup(prefix, name, box, markup):
    covered = path_extent(markup) == (box.x, box.y, box.x + box.w, box.y + box.h)
    return "" if covered else f'<rect x="{box.x}" y="{box.y}" width="{box.w}" height="{box.h}" fill="none"/>'


def hint(element_id, size):
    return f'<rect id="{element_id}" width="{size}" height="{size}" fill="none"/>'


def hint_markup(prefix, spec):
    hints = [hint(f"{prefix}hint-stretch-borders", 1)]
    for side, value in zip(("top", "bottom", "left", "right"), spec.margins, strict=True):
        hints.append(hint(f"{prefix}hint-{side}-margin", value))
    return hints


def shared_definitions(prefix, spec, x0):
    shared = {f"{prefix}fill": fill_definition(prefix, spec)}
    if len(spec.rings) > 1:
        shared[f"{prefix}ring"] = ring_definition(prefix, spec, x0)
    for index, glow in enumerate(glows_of(spec)):
        shared[f"{prefix}glow{index}"] = glow_definition(prefix, index, glow, x0)
    if spec.shade:
        shared[f"{prefix}shade"] = shade_definition(prefix, spec, x0)
    return shared


def piece_element(element_id, markup):
    """The elements of a piece with its id: on the element itself when there is one, else on a group."""
    if len(re.findall(r"<(?:path|rect|use)\b", markup)) == 1:
        return re.sub(r"^<(\w+) ", rf'<\1 id="{element_id}" ', markup)
    return f'<g id="{element_id}">{markup}</g>'


def definition_id(markup):
    return re.match(r'<\w+ id="([^"]+)"', markup).group(1)


def frame_markup(prefix, x0, spec):
    definitions, pieces = [], []
    for name, box in boxes_of(spec, x0).items():
        if box.w <= 0 or box.h <= 0:
            continue
        piece_definitions, markup = piece_markup(prefix, name, box, spec, x0)
        definitions += piece_definitions
        pieces.append(piece_element(f"{prefix}{name}", bounds_markup(prefix, name, box, markup) + markup))
    used = "".join(pieces)
    definitions += [
        definition for gradient_id, definition in shared_definitions(prefix, spec, x0).items() if f"#{gradient_id})" in used
    ]
    unique = {definition_id(definition): definition for definition in definitions}
    markup = [f"<defs>{''.join(unique.values())}</defs>", *pieces] if unique else pieces
    return "\n".join([*markup, *hint_markup(prefix, spec)])


def alias_markup(prefix, source_prefix, x0, spec, wash=None, source_x0=0):
    """The frame of another prefix, referenced piece by piece, so the two prefixes draw the same shape; wash is an
    optional (colour, opacity) laid over every piece."""
    shape = pill_shape(spec, x0)
    pieces = []
    for name, box in boxes_of(spec, x0).items():
        if box.w <= 0 or box.h <= 0:
            continue
        covering = fill_region(shape, box, wash[0], f' fill-opacity="{wash[1]}"') if wash else ""
        moved = f' x="{x0 - source_x0}"' if x0 != source_x0 else ""
        pieces.append(piece_element(f"{prefix}{name}", f'<use xlink:href="#{source_prefix}{name}"{moved}/>{covering}'))
    return "\n".join([*pieces, *hint_markup(prefix, spec)])


GAP = 16


def frames_svg(specs, extra="", aliases=None, extra_height=0):
    """The frames side by side; aliases maps a prefix to (the prefix whose drawing it reuses, an optional wash)."""
    aliases = aliases or {}
    parts, x0, origins = [], 0, {}
    for prefix, spec in specs:
        source, wash = aliases.get(prefix, (None, None))
        origins[prefix] = x0
        parts.append(
            alias_markup(prefix, source, x0, spec, wash, origins.get(source, 0))
            if source
            else frame_markup(prefix, x0, spec)
        )
        x0 += spec.width + GAP
    return primitives.linked_svg(x0 - GAP, strip_height(specs) + extra_height, "\n".join(parts) + extra)


def strip_height(specs):
    """Where the elements below a strip of frames may start."""
    return max(spec.height for _, spec in specs) + HINT_ROOM
