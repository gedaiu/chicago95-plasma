"""Source-derived Writing landmarks; paper hulls approximate occluded/curled edges."""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from review_clippy_3d import original_frames


def hull(points):
    points = sorted(set(map(tuple, points)))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    low = []
    up = []
    for p in points:
        while len(low) >= 2 and cross(low[-2], low[-1], p) <= 0:
            low.pop()
        low.append(p)
    for p in reversed(points):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return low[:-1] + up[:-1]


def paper_components(mask):
    visited = np.zeros(mask.shape, dtype=bool)
    selected = []
    for y, x in zip(*np.where(mask), strict=True):
        if visited[y, x]:
            continue
        stack = [(int(y), int(x))]
        component = []
        visited[y, x] = True
        while stack:
            cy, cx = stack.pop()
            component.append((cy, cx))
            for dy, dx in [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    stack.append((ny, nx))
        if len(component) >= 8:
            selected.extend(component)
    return np.array(selected)


def extract():
    rows = []
    for i, (im, duration) in enumerate(original_frames("Writing")):
        a = np.asarray(im).astype(float)
        r, g, b, alpha = [a[:, :, j] for j in range(4)]
        mask = (alpha > 100) & (r > 100) & (g > 100) & (b < (r + g) / 2 - 22) & (abs(r - g) < 60)
        closed = (
            np.asarray(
                Image.fromarray((mask * 255).astype("uint8"))
                .filter(ImageFilter.MaxFilter(3))
                .filter(ImageFilter.MinFilter(3))
            )
            > 0
        )
        component = paper_components(closed)
        poly = hull([(int(x), int(y)) for y, x in component])
        # The late flip is visibly concave. A convex hull fills the curled gap
        # and changes the action's silhouette; trace its actual outer edge.
        if i == 56:
            edges = {}
            for y, x in component:
                for dy, dx, start, end in [
                    (-1, 0, (x, y), (x + 1, y)),
                    (0, 1, (x + 1, y), (x + 1, y + 1)),
                    (1, 0, (x + 1, y + 1), (x, y + 1)),
                    (0, -1, (x, y + 1), (x, y)),
                ]:
                    if not (0 <= y + dy < 93 and 0 <= x + dx < 124 and closed[y + dy, x + dx]):
                        edges.setdefault(tuple(map(int, start)), []).append(tuple(map(int, end)))
            loops = []
            while edges:
                start = current = next(iter(edges))
                loop = []
                while current in edges:
                    loop.append(current)
                    following = edges[current].pop()
                    if not edges[current]:
                        del edges[current]
                    current = following
                    if current == start:
                        break
                if len(loop) > 3:
                    loops.append(loop)
            if loops:
                poly = max(
                    loops,
                    key=lambda ps: abs(
                        sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ps, ps[1:] + ps[:1], strict=True))
                    ),
                )
        red = (alpha > 100) & (r > 100) & (r > g * 1.5) & (r > b * 1.3)
        # Blue/purple metal edge pixels constrain the authored wire silhouette.
        metal_y, metal_x = np.where((alpha > 100) & (b > g + 8) & (b > 60))
        ry, rx = np.where(red)
        pencil = None
        if len(rx) > 1:
            pts = np.stack([rx, ry], axis=1)
            mean = pts.mean(0)
            axis = np.linalg.svd(pts - mean, full_matrices=False)[2][0]
            t = (pts - mean) @ axis
            pencil = [(mean + axis * t.min()).tolist(), (mean + axis * t.max()).tolist()]
        rows.append(
            {
                "source_index": i,
                "duration_ms": duration,
                "paper_polygon": poly,
                "pencil_endpoints": pencil,
                "metal_pixels": np.column_stack([metal_x, metal_y]).tolist(),
                "reference_sha256": hashlib.sha256(im.tobytes()).hexdigest(),
            }
        )
    return rows


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract source paper silhouette and pencil/eye landmarks; inspect before authoring."
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(extract(), indent=2) + "\n")
