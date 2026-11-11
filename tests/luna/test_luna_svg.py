import importlib.util

from conftest import REPO
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

# tests/luna is itself a package called luna, so the primitives module is loaded by path.
spec = importlib.util.spec_from_file_location("luna_primitives", REPO / "luna/aurorae/luna.py")
primitives = importlib.util.module_from_spec(spec)
spec.loader.exec_module(primitives)
Box, fill_region, gradient, linear_gradient, rect, region, ring_region, rounded_rect, shape_of, svg = (
    primitives.Box,
    primitives.fill_region,
    primitives.gradient,
    primitives.linear_gradient,
    primitives.rect,
    primitives.region,
    primitives.ring_region,
    primitives.rounded_rect,
    primitives.shape_of,
    primitives.svg,
)

TOP_ROUNDED = shape_of(0, 0, 32, 50, (8, 8, 0, 0))
PILL = shape_of(0, 0, 97, 30, (0, (6, 15), (6, 15), 0))


def render(markup, width, height):
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    QSvgRenderer(markup.encode()).render(painter)
    painter.end()
    return image


def covered(image, points):
    return [image.pixelColor(x, y).alpha() > 127 for x, y in points]


def test_corner_piece_of_a_rounded_top_leaves_its_outer_corner_transparent_and_its_inside_opaque():
    image = render(svg(8, 30, fill_region(TOP_ROUNDED, Box(0, 0, 8, 30), "#0058EE")), 8, 30)
    assert covered(image, [(0, 0), (7, 7), (7, 0), (0, 20)]) == [False, True, True, True]


def test_piece_of_the_straight_top_edge_is_a_plain_rectangle():
    assert region(TOP_ROUNDED, Box(8, 0, 16, 30)) == "M8,0 L24,0 L24,30 L8,30 Z"


def test_one_pixel_column_inside_the_arc_starts_below_the_top_where_the_arc_passes():
    image = render(svg(8, 30, fill_region(TOP_ROUNDED, Box(1, 0, 1, 30), "#0058EE")), 8, 30)
    assert covered(image, [(1, 0), (1, 2), (1, 5), (1, 20)]) == [False, False, True, True]


def test_piece_outside_the_shape_is_empty():
    assert region(shape_of(0, 0, 10, 10, (0, 0, 0, 0)), Box(20, 0, 5, 5)) == ""


def test_bottom_corners_of_a_pill_end_follow_the_half_ellipse_across_the_right_pieces():
    image = render(svg(98, 30, fill_region(PILL, Box(82, 1, 16, 28), "#3A833B")), 98, 30)
    assert covered(image, [(96, 15), (95, 2), (95, 28), (90, 1), (97, 15)]) == [True, False, False, True, False]


def test_ring_is_one_pixel_wide_along_the_edge_and_transparent_inside():
    markup = ring_region(shape_of(0, 0, 10, 10, (0, 0, 0, 0)), Box(0, 0, 10, 10), 1, "#FF0000")
    assert covered(render(svg(10, 10, markup), 10, 10), [(0, 5), (5, 0), (5, 5), (9, 9)]) == [True, True, False, True]


def test_ring_follows_the_arc_of_a_rounded_corner_and_stops_at_the_cut_edges():
    shape = shape_of(0, 0, 20, 20, (6, 6, 6, 6))
    image = render(svg(20, 20, ring_region(shape, Box(0, 0, 6, 6), 1, "#FF0000")), 20, 20)
    assert covered(image, [(0, 0), (5, 0), (0, 5), (3, 3), (5, 5), (3, 5)]) == [False, True, True, False, False, False]


def test_ring_of_a_piece_on_the_straight_edge_covers_only_the_outer_side():
    shape = shape_of(0, 0, 16, 25, (3, 3, 3, 3))
    image = render(svg(16, 25, ring_region(shape, Box(0, 4, 4, 17), 1, "#FF0000")), 16, 25)
    assert covered(image, [(0, 10), (1, 10), (3, 10), (0, 3), (0, 22)]) == [True, False, False, False, False]


def test_gradient_blue_channel_follows_the_stops_within_2():
    stops = [(0, "#0000FF"), (29, "#00FF00")]
    image = render(svg(4, 30, f"<defs>{gradient('rows', stops, 0, 30)}</defs>{rect(0, 0, 4, 30, 'url(#rows)')}"), 4, 30)
    blues = [image.pixelColor(1, row).blue() for row in range(30)]
    expected = [round(255 - 255 * row / 29) for row in range(30)]
    assert all(abs(blue - want) <= 2 for blue, want in zip(blues, expected, strict=True))


def test_gradient_stop_opacity_fades_the_fill_out():
    fade = linear_gradient("fade", (0, 0), (10, 0), [(0, "#FFFFFF", 1), (1, "#FFFFFF", 0)])
    image = render(svg(10, 4, f"<defs>{fade}</defs>{rect(0, 0, 10, 4, 'url(#fade)')}"), 10, 4)
    first, last = (image.pixelColor(x, 1).alpha() for x in (0, 9))
    assert (first > 230, last < 30) == (True, True)


def test_rounded_rect_keeps_its_corner_pixel_transparent():
    image = render(svg(21, 21, rounded_rect(0, 0, 21, 21, 6, "#FF0000")), 21, 21)
    assert (image.pixelColor(0, 0).alpha(), image.pixelColor(10, 10).alpha()) == (0, 255)
