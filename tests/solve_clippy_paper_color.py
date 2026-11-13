"""Fit a smooth low-dimensional vertex-color field from rendered RGB responses."""

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
    spec = json.loads((folder / "paper-color-jacobian.json").read_text())
    target = rgba(smooth_reference_color(Image.open(folder / "reference.png")))
    base = rgba(downsample(Image.open(folder / "paper-color-baseline.png")))
    mask = (target[:, :, 3] > 0) | (base[:, :, 3] > 0)
    samples = [rgba(downsample(Image.open(folder / name))) for name in spec["probes"]]
    current = np.array(spec["values"])
    n = len(current)
    edges = np.zeros((len(spec["edges"]), n))
    for row, (a, b) in enumerate(spec["edges"]):
        edges[row, a] = 1
        edges[row, b] = -1
    steps = []
    for channel in range(3):
        residual = (target[:, :, channel] - base[:, :, channel])[mask]
        jac = np.stack([(a[:, :, channel] - base[:, :, channel])[mask] / spec["delta"] for a in samples], axis=1)
        normalization = np.sqrt(len(residual))
        penalty = 0.01
        matrix = np.vstack([jac / normalization, penalty * np.eye(n), penalty * edges])
        rhs = np.r_[
            residual / normalization, -penalty * (current[:, channel] - 1), -penalty * edges @ current[:, channel]
        ]
        steps.append(np.linalg.lstsq(matrix, rhs, rcond=1e-6)[0])
    step = np.stack(steps, axis=1)
    maximum = float(np.max(abs(step)))
    if maximum > 0.2:
        step *= 0.2 / maximum
    step = np.clip(current + step, 0.5, 1.5) - current
    return dict(step=step.tolist())


if __name__ == "__main__":
    print(json.dumps(solve(Path(sys.argv[1]))))
