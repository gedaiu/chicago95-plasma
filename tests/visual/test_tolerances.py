import json
from base64 import b64decode, b64encode
from io import BytesIO

import numpy as np
import pytest
from original_pixels import compare
from PIL import Image
from tolerance_editor import collect, valid_entry
from visual_tolerances import approval_for, tolerance_for, tolerance_map


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
    assert result["passed"]
    with Image.open(BytesIO(b64decode(result["png"]))) as panel:
        assert panel.size == (9, 1)
        assert np.asarray(panel)[0].tolist() == [[192, 192, 192]] * 6 + [[0, 0, 0]] * 3


def test_editor_uses_latest_measured_result_even_when_a_passing_capture_differs(tmp_path):
    case = "win95/run/qt"
    reference = Image.new("RGB", (2, 1))
    rendered = reference.copy()
    rendered.putpixel((0, 0), (1, 0, 0))
    failed_run, passing_run = tmp_path / "failed", tmp_path / "passing"
    for run in (failed_run, passing_run):
        (run / "visual" / case).mkdir(parents=True)
    with pytest.raises(pytest.fail.Exception, match="1/2 pixels differ"):
        compare(reference, rendered, failed_run / "visual" / case / "comparison.png", record_metrics=True)
    compare(
        reference, rendered, passing_run / "visual" / case / "comparison.png",
        tolerance=np.ones((1, 2), dtype=np.uint8), record_metrics=True,
    )

    passed = collect([failed_run, passing_run])[case]
    assert passed["changed"] == 1 and passed["passed"]
    assert not collect([passing_run, failed_run])[case]["passed"]


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


def test_approval_matches_reviewed_pixels_and_keeps_windows_colors_valid(tmp_path, monkeypatch):
    directory = tmp_path / "visual/win7/caption/gtk4/hover/close"
    directory.mkdir(parents=True)
    output = directory / "comparison.png"
    reference = Image.new("RGB", (3, 1), (20, 20, 20))
    rendered = reference.copy()
    rendered.putpixel((1, 0), (30, 23, 20))
    captured = Image.new("RGB", (6, 1))
    captured.paste(reference)
    captured.paste(rendered, (3, 0))
    stream = BytesIO()
    captured.save(stream, format="PNG")
    entry = {
        "size": [3, 1], "regions": [],
        "review": {"status": "approved", "comment": "Accept the current caption."},
        "approved_pixels": b64encode(stream.getvalue()).decode(),
    }
    assert valid_entry(entry, [3, 1])
    assert not valid_entry({**entry, "approved_pixels": "bad"}, [3, 1])
    assert not valid_entry({**entry, "review": {"status": "rejected", "comment": ""}}, [3, 1])
    policy = tmp_path / "policy.json"
    case = directory.relative_to(tmp_path / "visual").as_posix()
    policy.write_text(json.dumps({"version": 1, "cases": {case: entry}}))
    monkeypatch.setattr("visual_tolerances.DEFAULT_POLICY", policy)
    monkeypatch.delenv("CHICAGO95_VISUAL_TOLERANCES", raising=False)

    approval = approval_for(directory, reference)
    assert tolerance_for(directory, reference.size) is None
    compare(reference, rendered, output, approval=approval, record_metrics=True)
    assert json.loads(output.with_suffix(".metrics.json").read_text())["pixels_over_tolerance"] == 0
    compare(reference, reference, output, approval=approval)

    rendered.putpixel((0, 0), (21, 20, 20))
    rendered.putpixel((1, 0), (23, 30, 20))
    with pytest.raises(pytest.fail.Exception, match="2/3 pixels exceed tolerance"):
        compare(reference, rendered, output, approval=approval)
    with pytest.raises(pytest.fail.Exception, match="Reference size"):
        compare(reference, rendered.crop((0, 0, 2, 1)), output, approval=approval)
    assert approval_for(directory.parent, reference) is None
    assert approval_for(directory, rendered) is None
    monkeypatch.setenv("CHICAGO95_VISUAL_TOLERANCES", "")
    assert approval_for(directory, reference) is None
