"""Optional zero-tolerance checks alongside the normal Aero regression budgets."""

import numpy as np
import pytest
from PIL import Image


def compare(original, actual, output, mask=None):
    assert original.size == actual.size
    expected = np.asarray(original.convert("RGB"), dtype=np.int16)
    observed = np.asarray(actual.convert("RGB"), dtype=np.int16)
    delta = np.abs(expected - observed)
    samples = delta if mask is None else delta[mask]
    changed = int(np.any(samples, axis=-1).sum())
    total = samples.size // 3
    assert total > 0
    if changed:
        if mask is not None:
            delta[~mask] = 0
        # Left to right: original, current render, absolute RGB error amplified 4x.
        panel = Image.new("RGB", (3 * actual.width, actual.height))
        panel.paste(original.convert("RGB"), (0, 0))
        panel.paste(actual.convert("RGB"), (actual.width, 0))
        panel.paste(Image.fromarray(np.minimum(255, 4 * delta).astype("uint8")), (2 * actual.width, 0))
        panel.save(output)
        pytest.fail(
            f"{changed}/{total} pixels differ, mean RGB error {samples.mean():.2f}/255; {output}", pytrace=False
        )
