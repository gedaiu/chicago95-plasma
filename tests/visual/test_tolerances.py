import json

import numpy as np
import pytest
from original_pixels import compare
from PIL import Image
from visual_tolerances import tolerance_for, tolerance_map


def test_reviewed_region_allows_only_its_channel_limit(tmp_path, monkeypatch):
    directory = tmp_path / "visual/win7/caption/kwin/mattes/blue/buttons"
    directory.mkdir(parents=True)
    output = directory / "comparison.png"
    reference = Image.new("RGB", (3, 1))
    rendered = reference.copy()
    rendered.putpixel((0, 0), (8, 1, 2))
    case = directory.relative_to(tmp_path / "visual").as_posix()
    policy = tmp_path / "review.json"
    policy.write_text(json.dumps({"version": 1, "cases": {case: {
        "size": [3, 1],
        "review": {"status": "approved", "comment": "The image looks right."},
        "regions": [{"x": 0, "y": 0, "width": 1, "height": 1, "max_channel_delta": 8}],
    }}}))

    with pytest.raises(pytest.fail.Exception, match="1/3 pixels differ"):
        compare(reference, rendered, output)

    monkeypatch.setenv("CHICAGO95_VISUAL_TOLERANCES", str(policy))
    tolerance = tolerance_for(directory, reference.size)
    compare(reference, rendered, output, record_metrics=True, tolerance=tolerance)
    metrics = json.loads(output.with_suffix(".metrics.json").read_text())
    assert metrics["changed_pixels"] == 1
    assert metrics["pixels_over_tolerance"] == 0

    rendered.putpixel((0, 0), (8, 9, 2))
    rendered.putpixel((1, 0), (1, 0, 0))
    with pytest.raises(pytest.fail.Exception, match="2/3 pixels exceed tolerance"):
        compare(reference, rendered, output, tolerance=tolerance)


def test_overlapping_exact_region_and_existing_comparison_mask(tmp_path):
    reference = Image.new("RGB", (3, 1))
    rendered = Image.new("RGB", (3, 1), (10, 10, 10))
    regions = [
        {"x": 0, "y": 0, "width": 2, "height": 1, "max_channel_delta": 255},
        {"x": 1, "y": 0, "width": 1, "height": 1, "max_channel_delta": 0},
    ]
    tolerance = tolerance_map(reference.size, regions)
    output = tmp_path / "comparison.png"
    with pytest.raises(pytest.fail.Exception, match="2/3 pixels exceed tolerance"):
        compare(reference, rendered, output, tolerance=tolerance)
    compare(reference, rendered, output, np.array([[True, False, False]]), tolerance=tolerance)

    with pytest.raises(pytest.fail.Exception, match="Reference size"):
        compare(reference, rendered.crop((0, 0, 1, 1)), output, tolerance=tolerance)
