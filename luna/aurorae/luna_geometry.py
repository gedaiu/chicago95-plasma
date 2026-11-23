"""Vector primitives for the Luna window decoration and the Luna Plasma theme, built on the flat theme's bevel helpers.

QtSvg and KSvg ignore clipPath, so a nine-slice piece is never a clipped copy of a shared drawing: every piece is
the part of the shape that falls inside its own box, written out as a path with true arcs (region), and its
outline is the even-odd difference of that region and the same region of the shape inset by the outline width (ring).

A shape is a rectangle whose four corners (top left, top right, bottom right, bottom left) are quarter ellipses.
"""

import math
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "aurorae"))
from bevel import rect, svg  # noqa: E402,F401

Shape = namedtuple("Shape", "x y w h radii")
Box = namedtuple("Box", "x y w h")
SQUARE = (0, 0)


def hidden(element_id, x, y, w, h):
    """An invisible rectangle that gives an element its bounds, or a hint KSvg reads the size of."""
    return f'<rect id="{element_id}" x="{x}" y="{y}" width="{w}" height="{h}" fill="none"/>'


def box_path(x, y, w, h, fill=None, element_id=None):
    """A rectangle written as a path, which is shorter than a rect element; no fill is the default black."""
    name = "" if element_id is None else f' id="{element_id}"'
    paint = "" if fill is None else f' fill="{fill}"'
    return f'<path{name} d="M{number(x)} {number(y)}h{number(w)}v{number(h)}h{number(-w)}z"{paint}/>'


def plain_rect(x, y, w, h, fill):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'


def reused_gradient(gradient_id, source_id, direction="right"):
    """A gradient with the stops of another one, running right or down across the bounding box."""
    attributes = {"right": ' x2="1" y2="0"', "down": ' x2="0" y2="1"'}[direction]
    return f'<linearGradient id="{gradient_id}" xlink:href="#{source_id}"{attributes}/>'


def linked_svg(width, height, body):
    """An svg whose elements may reference each other with <use>."""
    return svg(width, height, body).replace("<svg ", '<svg xmlns:xlink="http://www.w3.org/1999/xlink" ', 1)


def number(value, digits=5):
    return f"{value:.{digits}g}"


def corner_radii(radius):
    return radius if isinstance(radius, tuple) else (radius, radius)


def shape_of(x, y, w, h, radii):
    return Shape(x, y, w, h, tuple(corner_radii(radius) for radius in radii))


def inset(shape, amount):
    radii = tuple((max(0, rx - amount), max(0, ry - amount)) if rx and ry else SQUARE for rx, ry in shape.radii)
    return Shape(shape.x + amount, shape.y + amount, shape.w - 2 * amount, shape.h - 2 * amount, radii)


Arc = namedtuple("Arc", "x_from x_to centre_x centre_y radius_x radius_y")


def edge_arcs(shape, top):
    """The two quarter ellipses on the top or bottom boundary of the shape, left one first."""
    left, right = (shape.radii[0], shape.radii[1]) if top else (shape.radii[3], shape.radii[2])
    arcs = []
    for (radius_x, radius_y), at_left in ((left, True), (right, False)):
        if not radius_x:
            continue
        centre_x = shape.x + radius_x if at_left else shape.x + shape.w - radius_x
        centre_y = shape.y + radius_y if top else shape.y + shape.h - radius_y
        x_range = (shape.x, centre_x) if at_left else (centre_x, shape.x + shape.w)
        arcs.append(Arc(*x_range, centre_x, centre_y, radius_x, radius_y))
    return arcs


def arc_y(arc, top, x):
    height = arc.radius_y * math.sqrt(max(0.0, 1 - ((x - arc.centre_x) / arc.radius_x) ** 2))
    return arc.centre_y - height if top else arc.centre_y + height


def arc_at(arcs, x):
    return next((arc for arc in arcs if arc.x_from <= x <= arc.x_to), None)


def boundary_y(shape, arcs, top, clip, x):
    arc = arc_at(arcs, x)
    own = (shape.y if top else shape.y + shape.h) if arc is None else arc_y(arc, top, x)
    return max(clip, own) if top else min(clip, own)


def crossings(arcs, top, level):
    points = []
    for arc in arcs:
        offset = abs(arc.centre_y - level) / arc.radius_y
        if offset > 1:
            continue
        reach = arc.radius_x * math.sqrt(1 - offset**2)
        points += [x for x in (arc.centre_x - reach, arc.centre_x + reach) if arc.x_from <= x <= arc.x_to]
    return points


def edge_segment(shape, arcs, top, clip, a, b):
    """(arc or None, end point) of the boundary from x=a to x=b, which are consecutive breakpoints."""
    middle = (a + b) / 2
    arc = arc_at(arcs, middle)
    own_y = arc_y(arc, top, middle) if arc else None
    on_arc = arc is not None and (own_y > clip if top else own_y < clip)
    return (arc if on_arc else None), (b, boundary_y(shape, arcs, top, clip, b))


def merged_segments(start, segments):
    """Segments (arc or None, end point) with consecutive horizontal straight ones, and consecutive pieces of one
    arc, joined."""
    merged, previous = [], start
    for arc, end in segments:
        last = merged[-1] if merged else None
        horizontal = arc is None and end[1] == previous[1]
        last_horizontal = last is not None and last[0] is None and last[1][1] == last[2][1]
        if last is not None and last[0] == arc and (arc is not None or (horizontal and last_horizontal)):
            merged[-1] = (arc, last[1], end)
        else:
            merged.append((arc, previous, end))
        previous = end
    return [(arc, end) for arc, _, end in merged]


def command(arc, point):
    x, y = point
    if arc is None:
        return f"L{number(x)},{number(y)}"
    return f"A{number(arc.radius_x)},{number(arc.radius_y)} 0 0 1 {number(x)},{number(y)}"


def region(shape, box):
    """Path data of the part of the shape inside the box, or an empty string if they do not meet."""
    top_arcs, bottom_arcs = edge_arcs(shape, True), edge_arcs(shape, False)
    left, right = max(box.x, shape.x), min(box.x + box.w, shape.x + shape.w)
    top_clip, bottom_clip = max(box.y, shape.y), min(box.y + box.h, shape.y + shape.h)
    if right <= left or bottom_clip <= top_clip:
        return ""
    points = {left, right}
    for arcs, top, level in (
        (top_arcs, True, top_clip),
        (top_arcs, True, bottom_clip),
        (bottom_arcs, False, bottom_clip),
        (bottom_arcs, False, top_clip),
    ):
        points |= set(crossings(arcs, top, level))
    for arc in (*top_arcs, *bottom_arcs):
        points |= {arc.x_from, arc.x_to}
    ordered = sorted(x for x in points if left <= x <= right)
    spans = [
        (a, b)
        for a, b in zip(ordered, ordered[1:], strict=False)
        if b - a > 1e-9
        and boundary_y(shape, top_arcs, True, top_clip, (a + b) / 2)
        < boundary_y(shape, bottom_arcs, False, bottom_clip, (a + b) / 2)
    ]
    if not spans:
        return ""
    start, end = spans[0][0], spans[-1][1]
    origin = (start, boundary_y(shape, top_arcs, True, top_clip, start))
    segments = [edge_segment(shape, top_arcs, True, top_clip, a, b) for a, b in spans]
    segments.append((None, (end, boundary_y(shape, bottom_arcs, False, bottom_clip, end))))
    segments += [edge_segment(shape, bottom_arcs, False, bottom_clip, b, a) for a, b in reversed(spans)]
    joined = merged_segments(origin, segments)
    if joined[-1][1] == origin:
        joined = joined[:-1]
    return " ".join([f"M{number(origin[0])},{number(origin[1])}", *(command(arc, point) for arc, point in joined), "Z"])


def fill_region(shape, box, paint, extra=""):
    path = region(shape, box)
    fill = "" if paint is None else f' fill="{paint}"'
    return f'<path d="{path}"{fill}{extra}/>' if path else ""


def ring_region(shape, box, width, paint):
    """The ring of the given width along the shape's outline inside the box: an even-odd path between the shape's part
    and the part of the shape inset by the width. A fill rather than a stroke, because QtSvg grows an element's bounds
    by half the stroke width and the nine-slice pieces are sized by their bounds."""
    outer, inner = region(shape, box), region(inset(shape, width), box)
    return f'<path d="{outer} {inner}" fill="{paint}" fill-rule="evenodd"/>' if outer else ""


def stop_elements(stops, digits=5):
    """Stops are (offset, colour) or (offset, colour, opacity)."""
    out = []
    for stop in stops:
        offset, colour, opacity = (*stop, 1)[:3]
        opacity_attribute = "" if opacity == 1 else f' stop-opacity="{number(opacity, digits)}"'
        out.append(f'<stop offset="{number(offset, digits)}" stop-color="{colour}"{opacity_attribute}/>')
    return "".join(out)


def linear_gradient(gradient_id, start, end, stops, digits=5):
    """A gradient in user space between two points; stops are (offset, colour[, opacity]) with offsets in 0..1."""
    return (
        f'<linearGradient id="{gradient_id}" gradientUnits="userSpaceOnUse" '
        f'x1="{number(start[0])}" y1="{number(start[1])}" x2="{number(end[0])}" y2="{number(end[1])}">'
        f"{stop_elements(stops, digits)}</linearGradient>"
    )


def box_gradient(gradient_id, stops, direction="right", digits=5):
    """A gradient across the bounding box of whatever it paints, running right, left or down; stops are
    (offset, colour[, opacity])."""
    attributes = {"right": "", "left": ' x1="1" x2="0"', "down": ' x2="0" y2="1"'}[direction]
    return f'<linearGradient id="{gradient_id}"{attributes}>{stop_elements(stops, digits)}</linearGradient>'


def row_stops(rows, stops):
    """Stops given as (row, colour[, opacity]), row being the pixel row whose centre carries the colour, over a
    gradient of the given number of rows."""
    return [((row + 0.5) / rows, *rest) for row, *rest in stops]


def gradient(gradient_id, stops, top, rows, digits=5):
    """A vertical gradient from y=top over the given number of rows; stops are (row, colour[, opacity])."""
    return linear_gradient(gradient_id, (0, top), (0, top + rows), row_stops(rows, stops), digits)


def horizontal_gradient(gradient_id, left, columns, stops, digits=5):
    """A horizontal gradient from x=left over the given number of columns; stops are (column, colour[, opacity])."""
    return linear_gradient(gradient_id, (left, 0), (left + columns, 0), row_stops(columns, stops), digits)


def radial_gradient(gradient_id, centre, radii, stops, digits=5):
    """A radial gradient in user space, elliptical when the radii differ; stops are (offset, colour[, opacity])."""
    return (
        f'<radialGradient id="{gradient_id}" gradientUnits="userSpaceOnUse" cx="0" cy="0" r="1" '
        f'gradientTransform="translate({number(centre[0])} {number(centre[1])}) '
        f'scale({number(radii[0])} {number(radii[1])})">'
        f"{stop_elements(stops, digits)}</radialGradient>"
    )


def rounded_rect(x, y, w, h, corner_radius, fill, extra=""):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{corner_radius}" ry="{corner_radius}" '
        f'fill="{fill}"{extra}/>'
    )
