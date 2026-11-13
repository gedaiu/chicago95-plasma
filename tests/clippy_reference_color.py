"""Fixed, user-approved color reference for smooth HD Clippy artwork.

Only reference RGB is smoothed. Alpha, source timing, registration and geometry
remain unchanged. Candidate images are never blurred to make their score pass.
"""

import numpy as np
from PIL import Image

REFERENCE_COLOR_SIGMA = 0.5
REFERENCE_COLOR_RADIUS = 3
COLOR_REFERENCE_POLICY = "alpha-normalized-gaussian-sigma-0.5-native-pixels-v1"


def smooth_reference_color(original):
    source = np.asarray(original.convert("RGBA"), dtype=float)
    alpha = source[:, :, 3] / 255
    x = np.arange(-REFERENCE_COLOR_RADIUS, REFERENCE_COLOR_RADIUS + 1, dtype=float)
    kernel = np.exp(-(x * x) / (2 * REFERENCE_COLOR_SIGMA**2))
    kernel /= kernel.sum()

    def blur(values):
        for axis in (0, 1):
            values = np.apply_along_axis(
                lambda row: np.convolve(np.pad(row, REFERENCE_COLOR_RADIUS), kernel, "valid"), axis, values
            )
        return values

    weights = blur(alpha)
    result = source.copy()
    for channel in range(3):
        result[:, :, channel] = np.divide(
            blur(source[:, :, channel] * alpha),
            weights,
            out=np.zeros_like(alpha),
            where=weights > 1e-12,
        )
    return Image.fromarray(np.clip(np.rint(result), 0, 255).astype(np.uint8))
