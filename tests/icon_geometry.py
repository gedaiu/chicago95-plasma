"""Measure hard-edged icon geometry and diagnose overlapping SVG fills."""

import argparse
import json
import re
from copy import deepcopy
from itertools import combinations
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image

SHAPES = {"circle", "ellipse", "path", "polygon", "polyline", "rect", "line"}
SVG = "{http://www.w3.org/2000/svg}"
ET.register_namespace("", SVG[1:-1])


def overlap(svg, scale=32):
    """Rasterize each primitive independently and count fully covered intersections."""
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    tree = ET.fromstring(svg)
    if any(node.tag in {SVG + "use", SVG + "image"} for node in tree.iter()):
        raise ValueError("The overlap check expects direct vector shapes")
    definitions = {node for container in tree.iter(SVG + "defs") for node in container.iter()}
    layers = [node for node in tree.iter() if node.tag.removeprefix(SVG) in SHAPES and node not in definitions]
    masks = []
    for index, node in enumerate(layers):
        isolated = deepcopy(tree)
        nodes = dict(zip(tree.iter(), isolated.iter(), strict=True))
        for parent in tree.iter():
            for child in parent:
                if child in layers and child is not node:
                    nodes[parent].remove(nodes[child])
        renderer = QSvgRenderer(QByteArray(ET.tostring(isolated)))
        if not renderer.isValid():
            raise ValueError("Invalid SVG")
        size = renderer.defaultSize() * scale
        image = QImage(size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        pixels = np.frombuffer(image.constBits(), dtype=np.uint32).reshape(size.height(), -1)
        masks.append((node.get("id", f"{node.tag.removeprefix(SVG)} {index + 1}"), pixels >> 24 == 255))
    return [
        {"shapes": [a, b], "source_pixels_squared": round(area / scale**2, 5)}
        for (a, left), (b, right) in combinations(masks, 2)
        if (area := np.count_nonzero(left & right))
    ]


def circular_arcs(svg, element_id):
    node = next((node for node in ET.fromstring(svg).iter(SVG + "path") if node.get("id") == element_id), None)
    tokens = re.findall(r"[MAZ]|-?(?:\d*\.\d+|\d+)", node.get("d", "")) if node is not None else []
    if len(tokens) != 20 or [tokens[i] for i in (0, 3, 11, 19)] != ["M", "A", "A", "Z"]:
        raise ValueError(f"{element_id} must be drawn with two circular arcs")
    start = np.asarray(tokens[1:3], dtype=float)
    chord = np.linalg.norm(np.asarray(tokens[9:11], dtype=float) - start)
    if not np.array_equal(start, np.asarray(tokens[17:19], dtype=float)):
        raise ValueError(f"{element_id} arcs must share both endpoints")
    radii, sweeps = [], []
    for i in (4, 12):
        rx, ry, _rotation, large, sweep = map(float, tokens[i:i+5])
        if rx != ry or chord >= 2 * rx or chord == 0 or large not in (0, 1) or sweep not in (0, 1):
            raise ValueError(f"{element_id} must use valid circular arcs")
        radii.append(rx)
        sweeps.append(sweep)
    if sweeps[0] == sweeps[1]:
        raise ValueError(f"{element_id} must have a concave cutout")
    return radii


def crop(image, box):
    with Image.open(image) as source:
        source = source.convert("RGBA")
        return np.asarray(source.crop(box) if box else source)


def colour_mask(image, colours):
    target = [tuple(bytes.fromhex(colour.removeprefix("#"))) for colour in colours]
    if any(len(colour) != 3 for colour in target):
        raise ValueError("Use six-digit hexadecimal RGB colours")
    return np.any((image[..., None, :3] == target).all(axis=-1), axis=-1) & (image[..., 3] == 255)


def edge(mask, scan):
    """Fit one colour band, one contiguous run per scanline."""
    if scan == "column":
        mask = mask.T
    centers, widths = [], []
    for row, line in enumerate(mask):
        positions = np.flatnonzero(line)
        if positions.size:
            width = int(positions[-1] - positions[0] + 1)
            if width != positions.size:
                raise ValueError("Select a crop containing one contiguous edge per scanline")
            centers.append((row + .5, positions.mean() + .5))
            widths.append(width)
    if len(centers) < 2:
        raise ValueError("Select at least two scanlines through the edge")
    axis, offset = np.asarray(centers).T
    slope, intercept = np.polyfit(axis, offset, 1)
    angle = np.degrees(np.arctan2(1, slope) if scan == "row" else np.arctan(slope))
    return {
        "angle_degrees": round(angle, 3),
        "normal_width_px": round(np.median(widths) / np.hypot(1, slope), 3),
        "center_residual_px": round(np.sqrt(np.mean((offset - axis * slope - intercept)**2)), 3),
        "scanlines": len(centers),
    }


def crescent(mask):
    """Recover a broad circular crescent from the foreground pixel centres."""
    occupied = np.argwhere(mask)
    if len(occupied) < 5:
        raise ValueError("Select a crescent with at least five foreground pixels")
    (top, left), (bottom, right) = occupied.min(0), occupied.max(0)
    y, x = np.mgrid[top-2:bottom+3, left-2:right+3]
    y, x = y.ravel(), x.ravel()
    # Include a transparent margin when the selected region ends at the artwork edge.
    foreground = np.pad(mask, 2)[y+2, x+2]
    span = bottom - top + 1
    cy, cx = (top + bottom + 1) / 2, left + span / 2
    fit = np.array([[cx, cy, span / 2, right + 1., cy, span * .45]])
    rng = np.random.default_rng(58)
    for step in (1, .5, .25, .125, .06, .03, .015):
        candidates = fit[rng.integers(0, len(fit), size=8_000)] + rng.normal(size=(8_000, 6)) * step * span / 6
        candidates = np.concatenate((fit, candidates))
        ox, oy, radius, ix, iy, cutout = candidates.T[..., None]
        distance = np.hypot(ox - ix, oy - iy)[:, 0]
        signed = np.minimum(radius - np.hypot(x+.5-ox, y+.5-oy), np.hypot(x+.5-ix, y+.5-iy) - cutout)
        margins = np.where(foreground, signed, -signed)
        valid = (distance < radius[:, 0] + cutout[:, 0]) & (distance > abs(radius[:, 0] - cutout[:, 0]))
        cost = np.square(np.maximum(.12 - margins, 0)).sum(1) + 100 * ~valid
        selected = np.argsort(cost)[:20]
        fit = candidates[selected]
    return {
        "outer_circle": fit[0, :3].round(3).tolist(),
        "cutout_circle": fit[0, 3:].round(3).tolist(),
        "pixel_mismatches": int((margins[selected[0]] < 0).sum()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    svg = sub.add_parser("overlap")
    svg.add_argument("svg", type=Path)
    svg.add_argument("--scale", type=int, default=32)
    svg.add_argument("--crescent-id", help="also verify the named path uses two circular arcs")
    for name in ("edge", "crescent"):
        raster = sub.add_parser(name)
        raster.add_argument("image", type=Path)
        raster.add_argument("colours", nargs="+")
        raster.add_argument("--crop", nargs=4, type=int, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"))
        if name == "edge":
            raster.add_argument("--scan", choices=("row", "column"), default="row")
    args = parser.parse_args()
    if args.command == "overlap":
        if args.scale < 2:
            parser.error("--scale must be at least 2")
        data = args.svg.read_bytes()
        result = {"overlaps": overlap(data, args.scale)}
        if args.crescent_id:
            try:
                result["crescent_radii_px"] = circular_arcs(data, args.crescent_id)
            except ValueError as error:
                parser.error(str(error))
    else:
        mask = colour_mask(crop(args.image, args.crop), args.colours)
        result = edge(mask, args.scan) if args.command == "edge" else crescent(mask)
    print(json.dumps(result, indent=2))
    return int(args.command == "overlap" and bool(result["overlaps"]))


if __name__ == "__main__":
    raise SystemExit(main())
