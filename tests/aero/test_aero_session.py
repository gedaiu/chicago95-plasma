"""The Aero superbar in a real nested KWin and Plasma session, over Windows 7's plain desktop, against
win7screenres.png pixel for pixel."""

import pytest
from reference import screenshot


@pytest.fixture(scope="module")
def desktop():
    from render_report import aero_desktop

    image = aero_desktop()
    if image is None:
        pytest.skip("needs KWin and Plasma")
    return image.convert("RGB")


def bar(image):
    return image.crop((0, image.height - 40, image.width, image.height))


WINDOWS_7_BAR = screenshot("win7screenres").crop((0, 728, 1024, 768))


def test_empty_superbar_glass_is_windows_7s_row_by_row_within_three_levels(desktop):
    ours, theirs = bar(desktop), WINDOWS_7_BAR
    column = [ours.getpixel((ours.width - 200, y)) for y in range(40)]
    windows_7 = [theirs.getpixel((600, y)) for y in range(40)]

    assert max(abs(a - b) for p, q in zip(column, windows_7, strict=True) for a, b in zip(p, q, strict=True)) <= 3


def test_start_orb_glass_and_the_bar_behind_it_are_windows_7s_within_six_levels_on_average(desktop):
    # The orb's glass and rim, without its logo (the logo is Setup's choice, not Windows 7's).
    ours, theirs = bar(desktop).crop((0, 0, 58, 40)), WINDOWS_7_BAR.crop((0, 0, 58, 40))
    cx, cy = 27, 20
    ring = [(x, y) for x in range(58) for y in range(40) if 14**2 <= (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= 20**2]
    differences = [
        abs(a - b) for x, y in ring for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True)
    ]

    assert sum(differences) / len(differences) <= 6
