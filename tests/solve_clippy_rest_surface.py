"""Solve a bounded geometry update from full-render finite differences."""

import json
import sys
from pathlib import Path

import numpy as np
from clippy_reference_color import smooth_reference_color
from overlay_clippy_3d import downsample
from PIL import Image


def rgba(image):
    a = np.asarray(image.convert("RGBA"), dtype=float) / 255
    a[:, :, :3] *= a[:, :, 3:]
    return a


def solve(folder):
    spec = json.loads((folder / "surface-jacobian.json").read_text())
    target = rgba(smooth_reference_color(Image.open(folder / "reference.png")))
    base = rgba(downsample(Image.open(folder / spec["baseline"])))
    mask = (target[:, :, 3] > 0) | (base[:, :, 3] > 0)
    residual = (target[:, :, :3] - base[:, :, :3])[mask].ravel()
    columns = []
    for probe in spec["probes"]:
        if probe["valid"]:
            a = rgba(downsample(Image.open(folder / probe["file"])))
            columns.append(((a[:, :, :3] - base[:, :, :3])[mask] / probe["delta"]).ravel())
        else:
            columns.append(np.zeros_like(residual))
    jac = np.stack(columns, axis=1) / np.sqrt(len(residual))
    rhs = residual / np.sqrt(len(residual))
    current = np.array(spec["values"])
    edges = np.zeros((len(spec["edges"]), len(current)))
    for row, (a, b) in enumerate(spec["edges"]):
        edges[row, a] = 1
        edges[row, b] = -1
    # Gentle penalties avoid fitting image noise with a corrugated sheet.
    penalty = spec.get("regularization", 0.02)
    matrix = np.vstack([jac, penalty * np.eye(len(current)), penalty * edges])
    rhs = np.r_[rhs, -penalty * current, -penalty * edges @ current]
    step = np.linalg.lstsq(matrix, rhs, rcond=1e-6)[0]
    maximum = float(np.max(abs(step)))
    maximum_step = spec.get("maximum_step", 0.12)
    maximum_offset = spec.get("maximum_offset", 0.5)
    if maximum > maximum_step:
        step *= maximum_step / maximum
    step = np.clip(current + step, -maximum_offset, maximum_offset) - current
    return dict(
        step=step.tolist(), predicted_rms=float(np.sqrt(np.mean((jac @ step - residual / np.sqrt(len(residual))) ** 2)))
    )


if __name__ == "__main__":
    print(json.dumps(solve(Path(sys.argv[1]))))
