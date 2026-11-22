"""The Aero frame, laid out as Aurorae lays it out over the references' plain desktop, against Windows 7.

win7screenres.png's window is inactive (the desktop menu has the focus) at x 152..942, y 100..639; Notepad in
win7dragedge.png is active with its right edge at x 522 and its top at y 219. The left border and bottom-left corner of
the inactive window are covered by the desktop menu and are not compared. Windows 7 also paints screen-anchored glass
streaks over the caption, which a decoration cannot follow; the limits allow for them and catch any regression.
"""

import pytest
from aero_model import REFERENCE_DESKTOP, AeroWindow
from reference import screenshot

INACTIVE_BOX = (152, 100, 943, 640)
ACTIVE_WIDTH, ACTIVE_RIGHT, ACTIVE_TOP = 600, 522, 219


def mean_difference(ours, theirs):
    differences = [
        abs(a - b)
        for p, q in zip(ours.get_flattened_data(), theirs.get_flattened_data(), strict=True)
        for a, b in zip(p, q, strict=True)
    ]
    return sum(differences) / len(differences)


@pytest.fixture(scope="module")
def inactive(qt_app):
    from PySide6.QtGui import QColor

    left, top, right, bottom = INACTIVE_BOX
    window = AeroWindow(right - left, bottom - top, active=False).render(background=QColor(REFERENCE_DESKTOP))
    return window, screenshot("win7screenres").crop(INACTIVE_BOX)


@pytest.fixture(scope="module")
def active(qt_app):
    from PySide6.QtGui import QColor

    window = AeroWindow(ACTIVE_WIDTH, 360, active=True).render(background=QColor(REFERENCE_DESKTOP))
    left = ACTIVE_RIGHT - ACTIVE_WIDTH + 1
    return window, screenshot("win7dragedge").crop((left, ACTIVE_TOP, ACTIVE_RIGHT + 1, ACTIVE_TOP + 360))


@pytest.mark.parametrize(
    ("region", "box", "limit"),
    [
        ("right border", (783, 30, 791, 530), 6),
        ("bottom border", (8, 532, 783, 540), 8),
        ("caption buttons", (678, 0, 785, 19), 16),
        ("top right corner", (770, 0, 791, 30), 18),
    ],
)
def test_inactive_frame_region_is_within_its_limit_of_windows_7(inactive, region, box, limit, exact_original):
    ours, theirs = inactive
    exact_original(theirs.crop(box), ours.crop(box))

    assert mean_difference(ours.crop(box), theirs.crop(box)) < limit


@pytest.mark.parametrize(
    ("region", "box", "limit"),
    [
        ("right border", (ACTIVE_WIDTH - 8, 30, ACTIVE_WIDTH, 350), 12),
        ("caption buttons", (ACTIVE_WIDTH - 111, 0, ACTIVE_WIDTH - 6, 19), 20),
        ("top right corner", (ACTIVE_WIDTH - 21, 0, ACTIVE_WIDTH, 30), 29),
    ],
)
def test_active_frame_region_is_within_its_limit_of_windows_7(active, region, box, limit, exact_original):
    ours, theirs = active
    exact_original(theirs.crop(box), ours.crop(box))

    assert mean_difference(ours.crop(box), theirs.crop(box)) < limit


def test_outer_line_over_inactive_glass_is_the_screenshots_line_colour(inactive):
    ours, theirs = inactive

    assert max(abs(a - b) for a, b in zip(ours.getpixel((790, 300)), theirs.getpixel((790, 300)), strict=True)) <= 4


@pytest.mark.parametrize("window", ["active", "inactive"])
def test_caption_lower_rim_matches_windows_7(window, request):
    ours, theirs = request.getfixturevalue(window)
    # Interior columns of minimize, maximize and close, clear of the glyphs.
    for offset in (105, 70, 39):
        x = ours.width - offset
        strip = (x, 17, x + 1, 22)
        for image in (theirs, ours):
            samples = list(image.crop(strip).convert("L").get_flattened_data())
            assert samples.index(min(samples)) == 2  # dark outline at y=19
            assert samples.index(max(samples)) == 3  # highlight at y=20
        assert mean_difference(ours.crop(strip), theirs.crop(strip)) < 22
