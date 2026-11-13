"""Fit paper control-point projections to native source alpha; no image registration.

This is a geometry-only calibration experiment. Colors, eyes, wire and acceptance
thresholds are untouched. A fresh Blender render must verify the proxy fit.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from review_clippy_3d import original_frames


def crossings(poly):
    def cross(a, b, c):
        u = b - a
        v = c - a
        return u[0] * v[1] - u[1] * v[0]

    count = len(poly)
    for i in range(count):
        for j in range(i + 2, count):
            if i == 0 and j == count - 1:
                continue
            a, b, c, d = poly[i], poly[(i + 1) % count], poly[j], poly[(j + 1) % count]
            if cross(a, b, c) * cross(a, b, d) < 0 and cross(c, d, a) * cross(c, d, b) < 0:
                return True
    return False


def fit(folder):
    reference = original_frames("RestPose")[0][0]
    reference.save(folder / "reference.png")
    target = np.array(reference.getchannel("A"), dtype=float) / 255
    body = Image.open(folder / "body.png").getchannel("A").resize((124, 93), Image.Resampling.LANCZOS)
    body = np.array(body, dtype=float) / 255
    spec = json.loads((folder / "outline.json").read_text())
    initial = np.array(spec["points"])
    points = initial.copy()
    order = spec["boundary"]
    source_mask = target >= 0.5

    def loss(points):
        poly = points[order]
        if crossings(poly):
            return 1e3
        im = Image.new("L", (744, 558))
        ImageDraw.Draw(im).polygon([tuple(p * 6) for p in poly], fill=255)
        paper = np.array(im.resize((124, 93), Image.Resampling.LANCZOS), dtype=float) / 255
        combined = 1 - (1 - paper) * (1 - body)
        mask = combined >= 0.5
        union = source_mask | mask
        iou = (source_mask & mask).sum() / union.sum()
        return 1 - iou + 0.2 * np.abs(combined - target)[union].mean()

    before = best = loss(points)
    steps = []
    evaluations = 1
    for step in [1.0, 0.5, 0.25, 0.125]:
        for iteration in range(3):
            changed = 0
            for vertex in order:
                for axis in range(2):
                    old = points[vertex, axis]
                    choice = old
                    for direction in [-1, 1]:
                        proposal = old + direction * step
                        if abs(proposal - initial[vertex, axis]) > 3:
                            continue
                        points[vertex, axis] = proposal
                        value = loss(points)
                        evaluations += 1
                        if value < best - 1e-8:
                            best = value
                            choice = proposal
                    points[vertex, axis] = choice
                    changed += int(choice != old)
            steps.append(dict(step=step, iteration=iteration, loss=best, changed=changed))
            print(steps[-1], flush=True)
            if not changed:
                break
    result = dict(
        points=points.tolist(),
        boundary=order,
        proxy_loss_before=before,
        proxy_loss_after=best,
        maximum_control_shift_px=float(np.linalg.norm(points - initial, axis=1).max()),
        evaluations=evaluations,
        steps=steps,
        scope="Paper projection only. Must be checked with an independent full Blender render.",
    )
    (folder / "fitted-outline.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    fit(p.parse_args().folder)
