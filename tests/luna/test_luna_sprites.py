"""Our Luna taskbar pieces against the sprites of luna.msstyles (the QuickXP extract; see luna/README.md).

The sprites are Microsoft's and are not in the repository: LUNA_MSSTYLES_DIR names the extracted folder that holds
images/BLUE_<NAME>_BMP.png (the default is the author's scratchpad copy); without it these tests skip.
"""

import os
from pathlib import Path

import pytest
from PIL import Image
from reference import close

from .test_luna_plasmastyle import generator, rendered, theme  # noqa: F401
from .test_luna_taskbar import installed, qml_root, render  # noqa: F401

DEFAULT_DIRECTORY = Path(
    "/tmp/claude-1000/-home-gedaiu-workspace-chicago95-plasma/6679116e-4ef6-4478-b441-c6cd1dc95f4a/scratchpad"
    "/refs2/gh_freitagdavid_QuickXP/QuickXP/themes/luna/luna"
)
SPRITES = Path(os.environ.get("LUNA_MSSTYLES_DIR", DEFAULT_DIRECTORY))
TOLERANCE = 12
BACKGROUND_ROWS = (15, 11)  # the taskbar background's top and bottom margins; the middle stretches
BAND_HOVER_BUDGET, GRIP_BUDGET = 0.35, 0.1
GRIP_ROWS = range(6, 12)
GLYPH_ORIGIN = (3, 6)  # where the chevron's glyph starts in a 13px cell with its top at row 4, two rows down

pytestmark = pytest.mark.skipif(not (SPRITES / "images").is_dir(), reason="LUNA_MSSTYLES_DIR has no sprites")


def sprite(name, state=None, states=1):
    image = Image.open(SPRITES / f"images/BLUE_{name}_BMP.png").convert("RGBA")
    if state is None:
        return image
    height = image.height // states
    return image.crop((0, state * height, image.width, (state + 1) * height))


def opaque(pixel):
    return pixel[3] == 255


def differing_fraction(ours, original, rows=None):
    points = [
        (x, y)
        for x in range(original.width)
        for y in (rows or range(original.height))
        if opaque(original.getpixel((x, y)))
    ]
    return sum(not close(ours.getpixel(point), original.getpixel(point)[:3], TOLERANCE) for point in points) / len(
        points
    )


def test_taskbar_background_equals_the_sprite_in_its_top_15_and_bottom_11_rows_within_12(theme):  # noqa: F811 (the fixtures imported above)
    panel = rendered(theme, "widgets/panel-background.svg", "", 50, 30)
    original = sprite("TASKBARBACKGROUND")
    top, bottom = BACKGROUND_ROWS
    pairs = [(row, row) for row in range(top)] + [(30 - bottom + index, 28 - bottom + index) for index in range(bottom)]
    ours = [
        (panel.pixelColor(20, row).red(), panel.pixelColor(20, row).green(), panel.pixelColor(20, row).blue())
        for row, _ in pairs
    ]
    assert [
        close(colour, original.getpixel((20, source))[:3], TOLERANCE)
        for colour, (_, source) in zip(ours, pairs, strict=True)
    ] == [True] * len(pairs)


def test_quick_launch_grip_dots_equal_the_sprites_rows_6_to_11_within_12(qt_app, qml_root, installed, tmp_path):  # noqa: F811 (the fixtures imported above)
    ours = render(qt_app, qml_root, installed, tmp_path, "org.chicago95.tasks", "Separator", 14, {"lead": 0})
    original = sprite("TASKBARGRIPPER")
    assert differing_fraction(ours, original, GRIP_ROWS) < GRIP_BUDGET


def mean_colour(image, box):
    pixels = [image.getpixel((x, y))[:3] for x in range(box[0], box[2]) for y in range(box[1], box[3])]
    return tuple(sum(pixel[channel] for pixel in pixels) / len(pixels) for channel in range(3))


@pytest.mark.parametrize("state", [0, 1, 2])
def test_hidden_icons_button_body_is_the_sprites_colour_in_every_state_within_36(
    qt_app,
    qml_root,  # noqa: F811 (the fixtures imported above)
    installed,  # noqa: F811 (the fixtures imported above)
    tmp_path,
    state,
):
    original = sprite("TRAYCHEVRONHORIZONTAL", state, 3).crop((0, 1, 19, 20)).resize((16, 16), Image.LANCZOS)
    ours = render(
        qt_app,
        qml_root,
        installed,
        tmp_path,
        "org.chicago95.trayframe",
        "TrayChevron",
        16,
        {"hovered": state == 1, "held": state == 2},
    ).crop((0, 0, 16, 16))
    boxes = [(2, 2, 5, 5), (11, 10, 14, 13), (2, 11, 5, 14), (11, 2, 14, 5)]
    assert [close(mean_colour(ours, box), mean_colour(original, box), 36) for box in boxes] == [True] * len(boxes)


def test_chevron_glyph_pixels_are_the_sprites_7bb6e8_double_arrow(qt_app, qml_root, installed, tmp_path):  # noqa: F811 (the fixtures imported above)
    ours = render(qt_app, qml_root, installed, tmp_path, "org.chicago95.tasks", "Chevron", 13)
    original = sprite("TASKBARCHEVRON", 0, 6)
    shifted = [
        (x + GLYPH_ORIGIN[0], y - 7 + GLYPH_ORIGIN[1])
        for x in range(original.width)
        for y in range(original.height)
        if opaque(original.getpixel((x, y)))
    ]
    glyph = [(x, y) for x in range(13) for y in range(30) if ours.getpixel((x, y)) == original.getpixel((0, 7))[:3]]
    assert sorted(glyph) == sorted(shifted)


def test_hot_band_button_resembles_the_sprites_hot_state_within_the_band_budget(qt_app, qml_root, installed, tmp_path):  # noqa: F811 (the fixtures imported above)
    original = sprite("TASKBANDBUTTONNOEDGE", 1, 6).crop((0, 3, 13, 25))
    ours = render(
        qt_app, qml_root, installed, tmp_path, "org.chicago95.tasks", "QuickLaunchButton", 13, {"hovered": True}
    ).crop((0, 4, 13, 26))
    assert differing_fraction(ours, original) < BAND_HOVER_BUDGET
