"""Optional zero-tolerance checks alongside the normal Windows reference regression budgets."""

import json

import numpy as np
import pytest
from PIL import Image


def compare(original, actual, output, mask=None, *, record_metrics=False):
    reference_size, rendered_size = original.size, actual.size
    metrics_path = output.with_suffix(".metrics.json")
    geometry = ""
    if original.size != actual.size:
        geometry = f"Reference size {original.size} differs from rendered size {actual.size}. "
        original.save(output.with_name(output.stem + "-reference.png"))
        actual.save(output.with_name(output.stem + "-rendered.png"))
        width, height = min(original.width, actual.width), min(original.height, actual.height)
        original = original.crop((0, 0, width, height))
        actual = actual.crop((0, 0, width, height))
        if mask is not None:
            mask = mask[:height, :width]
        output = output.with_name(output.stem + "-overlap.png")
    expected = np.asarray(original.convert("RGB"), dtype=np.int16)
    observed = np.asarray(actual.convert("RGB"), dtype=np.int16)
    delta = np.abs(expected - observed)
    samples = delta if mask is None else delta[mask]
    changed = int(np.any(samples, axis=-1).sum())
    total = samples.size // 3
    assert total > 0
    mean_error = float(samples.mean())
    if record_metrics:
        metrics_path.write_text(json.dumps({
            "reference_size": reference_size,
            "rendered_size": rendered_size,
            "changed_pixels": changed,
            "compared_pixels": total,
            "mean_rgb_error": mean_error,
        }) + "\n")
    if changed or geometry:
        if mask is not None:
            delta[~mask] = 0
        # Left to right: original, current render, absolute RGB error amplified 4x.
        panel = Image.new("RGB", (3 * actual.width, actual.height))
        panel.paste(original.convert("RGB"), (0, 0))
        panel.paste(actual.convert("RGB"), (actual.width, 0))
        panel.paste(Image.fromarray(np.minimum(255, 4 * delta).astype("uint8")), (2 * actual.width, 0))
        panel.save(output)
        region = " in the top-left overlap" if geometry else ""
        pytest.fail(
            f"{geometry}{changed}/{total} pixels differ{region}, mean RGB error {mean_error:.2f}/255; {output}",
            pytrace=False,
        )
