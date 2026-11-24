"""Checked-in regression portraits of the controls we draw. Windows reference tests live alongside these."""

import math
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat
from reference import REFERENCES

HERE = Path(__file__).parent
SCENES = (
    "shutdown",
    "restart",
    "logoff",
    "balloon",
    "power-options",
    "start",
    "programs",
    "search",
    "system-general",
    "system-hardware",
    "system-advanced",
    "preview-list",
    "preview-cards",
)


@pytest.fixture(scope="module", params=("1", "1.5"), ids=("100-percent", "150-percent"))
def pictures(request, tmp_path_factory):
    output = tmp_path_factory.mktemp("aero-portraits")
    subprocess.run(
        [sys.executable, str(HERE / "render_aero_dialogs.py"), str(output), request.param],
        check=True,
        capture_output=True,
        text=True,
        timeout=45,
    )
    return output, HERE / "portraits" / request.param


@pytest.mark.parametrize("scene", SCENES)
def test_aero_window_matches_reviewed_portrait(pictures, scene):
    output, references = pictures
    with Image.open(output / f"{scene}.png") as actual, Image.open(references / f"{scene}.png") as expected:
        assert actual.size == expected.size
        diff = ImageChops.difference(actual.convert("RGBA"), expected.convert("RGBA"))
    # Check local tiles to catch a lost button, scroll thumb or balloon tail even on a large, flat panel.
    for y in range(0, diff.height, 32):
        for x in range(0, diff.width, 32):
            tile = diff.crop((x, y, min(x + 32, diff.width), min(y + 32, diff.height)))
            if max(ImageStat.Stat(tile).mean) > 6:
                diff.convert("RGB").save(output / f"{scene}-difference.png")
                pytest.fail(f"{scene} differs near ({x}, {y}); render and difference in {output}")


def test_background_shows_through_menu_and_preview_glass(pictures):
    output, _ = pictures
    for scene, logical_width, point, transmission in (
        ("start", 411, (393, 249), 0.27),
        ("preview-cards", 312, (156, 5), 0.42),
    ):
        with Image.open(output / f"{scene}.png") as surface:
            scale = surface.width / logical_width
            x, y = (round(value * scale) for value in point)
            assert 1 - surface.convert("RGBA").getpixel((x, y))[3] / 255 == pytest.approx(transmission, abs=0.02)


def test_shutdown_chooser_keeps_native_client_dimensions(pictures):
    output, portraits = pictures
    scale = float(portraits.name)
    with Image.open(REFERENCES / "themes/win7/shutdown.png") as native, Image.open(output / "chooser.png") as actual:
        assert actual.size == tuple(math.ceil(length * scale) for length in native.size)


def test_search_field_interior_matches_sp1_at_native_scale(pictures):
    from reference import screenshot

    output, portraits = pictures
    scale = float(portraits.name)
    with Image.open(output / "start.png") as render:
        actual = render.convert("RGB").resize((411, round(render.height / scale)), Image.Resampling.NEAREST)
    native = screenshot("win7-sp1-aero-start")

    def white_span(image, coordinates):
        indices = [i for i, point in enumerate(coordinates) if image.getpixel(point) == (255, 255, 255)]
        return min(indices), max(indices)

    # Sample clear lines inside the search field. Anchor the menu at the top of the 40px taskbar.
    def field_spans(image, top):
        horizontal = white_span(image, [(x, 688 - top) for x in range(15, 250)])
        vertical = white_span(image, [(205, y - top) for y in range(681, 715)])
        return horizontal, vertical

    for measured, expected in zip(field_spans(actual, 728 - actual.height), field_spans(native, 0), strict=True):
        assert measured == pytest.approx(expected, abs=1)
