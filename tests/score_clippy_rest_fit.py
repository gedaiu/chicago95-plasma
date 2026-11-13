"""Score an unregistered full-resolution render through the normal native validator."""

import argparse
import json

import numpy as np
from clippy_reference_color import COLOR_REFERENCE_POLICY, smooth_reference_color
from overlay_clippy_3d import downsample, metrics
from PIL import Image


def score(reference, candidate):
    original = Image.open(reference).convert("RGBA")
    source_render = Image.open(candidate)
    if original.size != (124, 93) or source_render.size != (744, 558):
        raise ValueError("Calibration scoring requires the 124×93 source and a 744×558 independent render")
    rendered = downsample(source_render)
    result = metrics(original, rendered)
    smoothed = smooth_reference_color(original)
    result["smoothed_reference_color_similarity"] = metrics(smoothed, rendered)["foreground_color_similarity"]
    result["color_reference_policy"] = COLOR_REFERENCE_POLICY
    a, b = (np.asarray(im, dtype=float) / 255 for im in (original, rendered))
    delta = np.abs(a[:, :, :3] * a[:, :, 3:] - b[:, :, :3] * b[:, :, 3:]).mean(2)
    result["eye_region_error"] = float(delta[18:44, 33:83].mean())
    smoothed_pixels = np.asarray(smoothed, dtype=float) / 255
    smoothed_delta = np.abs(smoothed_pixels[:, :, :3] * smoothed_pixels[:, :, 3:] - b[:, :, :3] * b[:, :, 3:]).mean(2)
    result["smoothed_reference_eye_region_error"] = float(smoothed_delta[18:44, 33:83].mean())
    result["loss"] = (
        1
        - result["smoothed_reference_color_similarity"]
        + 0.2 * (1 - result["silhouette_iou"])
        + 0.5 * result["smoothed_reference_eye_region_error"]
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference")
    parser.add_argument("candidate")
    args = parser.parse_args()
    print(json.dumps(score(args.reference, args.candidate)))
