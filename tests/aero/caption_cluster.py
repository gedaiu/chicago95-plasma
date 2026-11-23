"""Compare all three caption glyphs using one translation for the entire window's button group."""

import numpy as np
from PIL import Image
from reference import screenshot


def native_cluster(scale, maximized=False):
    if scale == 1.5:
        cluster = screenshot("win7-sp1-144dpi-caption").convert("RGB")
        edges = (0, 45, 85, 160)
        if maximized:
            # The guest clips the top row against the screen edge when maximized.
            cluster.paste(screenshot("win7-sp1-144dpi-restore"), (edges[1], 1))
    else:
        # One restored window preserves Windows' inter-button spacing as captured.
        guest = screenshot("win7-sp1-aero-device-manager").convert("RGB")
        cluster, edges = guest.crop((756, 43, 861, 63)), (0, 29, 55, 105)
        if maximized:
            restore = screenshot("win7-sp1-caption-restore-motion").crop((0, 0, 27, 19))
            cluster.paste(restore, (edges[1], 1))
    return cluster, edges


def compare_cluster(shot, scale, maximized=False):
    reference, edges = native_cluster(scale, maximized)
    pixels = np.asarray(shot.convert("RGB"), dtype=int)
    red, green, blue = pixels.transpose(2, 0, 1)
    y, x = np.where((red > 145) & (red > green + 50) & (red > blue + 50))
    assert x.size and x.max() - x.min() >= round(44 * scale), "missing red Close face"

    def glyph_masks(cluster):
        masks = []
        for left, right in zip(edges[:-1], edges[1:], strict=True):
            roi = cluster[round(3 * scale) : round(17 * scale), left + round(6 * scale) : right - round(6 * scale)]
            masks.append((roi.min(axis=2) > 198) & (np.ptp(roi, axis=2) < 12))
        return masks

    targets = glyph_masks(np.asarray(reference, dtype=int))
    # The red glass becomes detectable at a different row on light and dark backdrops.
    # Register once at the Close face, preserving the spacing of all three buttons.
    best = -1
    for left in range(x.min() - edges[2] - 5, x.min() - edges[2] + 5):
        for top in range(y.min() - round(8 * scale), y.min() + 1):
            crop = pixels[top : top + reference.height, left : left + reference.width]
            if crop.shape[:2] != (reference.height, reference.width):
                continue
            scores = tuple(
                (a & b).sum() / (a | b).sum() for a, b in zip(glyph_masks(crop), targets, strict=True)
            )
            if sum(scores) > best:
                best = sum(scores)
                result = scores, Image.fromarray(crop.astype("uint8"))
    assert best >= 0, "caption clipped"
    return result
