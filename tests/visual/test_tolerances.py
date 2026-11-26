import json
from base64 import b64decode
from io import BytesIO

import numpy as np
import pytest
from original_pixels import compare
from PIL import Image
from tolerance_editor import collect
from visual_tolerances import tolerance_for, tolerance_map


def test_editor_keeps_a_review_visible_after_the_pixels_match(tmp_path):
    case = "win95/run/qt"
    directory = tmp_path / "visual" / case
    directory.mkdir(parents=True)
    captured = Image.new("RGB", (3, 1), "#c0c0c0")
    captured.save(directory / "rendered.png")
    compare(captured, captured, directory / "comparison.png", record_metrics=True)

    assert collect([tmp_path]) == {}
    result = collect([tmp_path], {case})[case]
    assert result["changed"] == 0
    with Image.open(BytesIO(b64decode(result["png"]))) as panel:
        assert panel.size == (9, 1)
        assert np.asarray(panel)[0].tolist() == [[192, 192, 192]] * 6 + [[0, 0, 0]] * 3


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
