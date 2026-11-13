"""Bounded wire-shape calibration using component masks, checked by a real render."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def fit(folder):
    reference = np.array(Image.open(folder / "reference.png").getchannel("A")) / 255
    source = reference >= 0.5

    def alpha(name):
        return (
            np.array(Image.open(folder / f"{name}.png").getchannel("A").resize((124, 93), Image.Resampling.LANCZOS))
            / 255
        )

    face, paper = alpha("face"), alpha("paper")
    base = Image.open(folder / "wire.png").getchannel("A")
    best = None
    for dilation in range(4):
        wire = base if dilation == 0 else base.filter(ImageFilter.MaxFilter(2 * dilation + 1))
        x = np.array([0.0, 0.0, 1.0, 1.0, 0.0])
        limits = [(-2, 2), (-2, 2), (0.94, 1.06), (0.94, 1.06), (-0.06, 0.06)]

        def loss(v, wire=wire):
            dx, dy, sx, sy, shear = v
            mat = np.array([[sx, shear, 0], [0, sy, 0], [0, 0, 1.0]])
            pivot = np.array([60 * 6, 48 * 6])
            mat[:2, 2] = pivot + np.array([dx, dy]) * 6 - mat[:2, :2] @ pivot
            inverse = np.linalg.inv(mat)
            im = wire.transform(wire.size, Image.Transform.AFFINE, tuple(inverse[:2].ravel()), Image.Resampling.BICUBIC)
            a = np.array(im.resize((124, 93), Image.Resampling.LANCZOS)) / 255
            a = 1 - (1 - a) * (1 - face) * (1 - paper)
            mask = a >= 0.5
            union = mask | source
            return 1 - (mask & source).sum() / union.sum() + 0.2 * abs(a - reference)[union].mean()

        score = loss(x)
        for multiplier in [1.0, 0.5, 0.25, 0.125]:
            for _ in range(3):
                changed = False
                for i, step in enumerate([0.5, 0.5, 0.02, 0.02, 0.02]):
                    old = x[i]
                    choice = old
                    for direction in [-1, 1]:
                        value = old + step * multiplier * direction
                        if not limits[i][0] <= value <= limits[i][1]:
                            continue
                        x[i] = value
                        candidate = loss(x)
                        if candidate < score - 1e-8:
                            score = candidate
                            choice = value
                    x[i] = choice
                    changed |= choice != old
                if not changed:
                    break
        result = dict(parameters=x.tolist(), dilation_hd_pixels=dilation, proxy_loss=float(score))
        print(result, flush=True)
        if best is None or score < best["proxy_loss"]:
            best = result
    radius = json.loads((folder / "wire-radius.json").read_text())["radius_px"]
    best["skin_radius_scale"] = 1 + best["dilation_hd_pixels"] / 6 / radius
    (folder / "fitted-wire.json").write_text(json.dumps(best, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    fit(p.parse_args().folder)
