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


def test_empty_superbar_glass_is_windows_7s_without_its_streaks_row_by_row_within_three_levels(desktop):
    from aero_model import plain_bar

    ours = bar(desktop)
    column = [ours.getpixel((ours.width - 200, y)) for y in range(40)]
    windows_7 = plain_bar("win7screenres")

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


def icon_columns(image):
    """The (first, last) columns of each test icon (plasma_session's green square) along the bar's middle row."""
    from plasma_session import ICON_COLOUR

    row = bar(image).crop((0, 0, 420, 40))  # the task area, not the tray
    runs, start = [], None
    for x in range(row.width + 1):
        green = x < row.width and row.getpixel((x, 20)) == ICON_COLOUR
        if green and start is None:
            start = x
        if not green and start is not None:
            runs.append((start, x - 1))
            start = None
    return runs


def icon_rows(image, x):
    from plasma_session import ICON_COLOUR

    rows = [y for y in range(40) if bar(image).getpixel((x, y)) == ICON_COLOUR]
    return rows[0], rows[-1]


def test_pinned_programs_and_the_task_button_sit_on_windows_7s_62_pixel_pitch(desktop):
    # win7screenres.png: slots from x 59 every 62 pixels, each button 60 wide; Explorer's 32-pixel icon spans
    # 135..166, centred in its slot, and the focused Control Panel button spans 245..304.
    assert (icon_columns(desktop), icon_rows(desktop, 150)) == (
        [(73, 104), (135, 166), (197, 228), (259, 290)],
        (4, 35),
    )


def test_focused_task_button_spans_windows_7s_columns(desktop):
    ours, theirs = bar(desktop), WINDOWS_7_BAR
    edges = [ours.getpixel((x, 20)) for x in (244, 245, 304, 305)]
    windows_7 = [theirs.getpixel((x, 20)) for x in (244, 245, 304, 305)]

    assert max(abs(a - b) for p, q in zip(edges, windows_7, strict=True) for a, b in zip(p, q, strict=True)) <= 6


def test_pinned_programs_at_rest_show_only_their_icons_on_windows_7s_bar(desktop):
    # Between and around the 32-pixel icons (x 59..243, win7screenres.png's pinned slots) there is no separator,
    # grip or button face: the bar's glass, darkened behind the orb as Windows 7's is. DWM lays screen-anchored
    # streaks over its glass, whole columns a few levels lighter or darker, which a stretched Plasma panel cannot
    # draw: the bound is how far Windows 7's own bar strays from its plain row there, plus two.
    icons = [(73, 104), (135, 166), (197, 228)]
    outside = [
        (x, y)
        for x in range(59, 244)
        for y in range(40)
        if not any(left - 4 <= x <= right + 4 for left, right in icons)
    ]
    ours, theirs = bar(desktop), WINDOWS_7_BAR
    differences = [
        max(abs(a - b) for a, b in zip(ours.getpixel(pixel), theirs.getpixel(pixel), strict=True)) for pixel in outside
    ]

    streaks = max(
        abs(a - b)
        for x in range(110, 244)
        for y in (12, 20)
        if not any(left - 4 <= x <= right + 4 for left, right in icons)
        for a, b in zip(theirs.getpixel((x, y)), theirs.getpixel((600, y)), strict=True)
    )

    assert max(differences) <= streaks + 2


def test_running_task_button_outside_its_icon_is_windows_7s_within_six_levels(desktop):
    # win7screenres.png's Control Panel button (x 245..304) is running but not focused: its context menu has the focus.
    ours, theirs = bar(desktop), WINDOWS_7_BAR
    face = [(x, y) for x in range(245, 305) for y in range(40) if not (255 <= x <= 294 and 0 <= y <= 39)]
    differences = [
        max(abs(a - b) for a, b in zip(ours.getpixel(pixel), theirs.getpixel(pixel), strict=True)) for pixel in face
    ]

    assert sum(differences) / len(differences) <= 6
