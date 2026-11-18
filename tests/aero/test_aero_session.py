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


def test_empty_superbar_is_windows_7s_with_its_streaks_within_a_level_and_a_half_on_average(desktop):
    # Both screens are 1024 wide, so DWM's streaks, stretched over the screen, fall on the same columns; a band's
    # sharp edge can land a pixel or two off (tests/aero/test_aero_taskbar.py).
    ours, theirs = bar(desktop), WINDOWS_7_BAR
    columns = [
        x
        for x in range(320, 800)
        if all(
            sum(abs(a - b) for a, b in zip(theirs.getpixel((x, y)), theirs.getpixel((x, 20)), strict=True)) < 25
            for y in range(4, 37)
        )
    ]
    differences = [
        max(abs(a - b) for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True))
        for x in columns
        for y in range(40)
    ]

    assert (sum(differences) / len(differences) <= 1.5, max(differences) <= 8) == (True, True)


def test_start_orb_glass_and_the_bar_behind_it_are_windows_7s_within_six_levels_on_average(desktop):
    # The orb's glass and rim, without its logo (the logo is Setup's choice, not Windows 7's).
    ours, theirs = bar(desktop).crop((0, 0, 58, 40)), WINDOWS_7_BAR.crop((0, 0, 58, 40))
    cx, cy = 27, 20
    ring = [(x, y) for x in range(58) for y in range(40) if 14**2 <= (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= 20**2]
    differences = [
        abs(a - b) for x, y in ring for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True)
    ]

    assert sum(differences) / len(differences) <= 6


def icon_columns(image, task_area=420):
    """The (first, last) columns of each test icon (plasma_session's green square) along the bar's middle row, over
    the task area (not the tray)."""
    from plasma_session import ICON_COLOUR

    row = bar(image).crop((0, 0, task_area, 40))
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


def test_show_desktop_strip_ends_at_the_screens_edge_as_windows_7s(desktop):
    # win7screenres.png: the strip is the bar's last 15 columns, x 1009..1023, with nothing after it.
    ours, theirs = bar(desktop), WINDOWS_7_BAR
    strip = [(ours.getpixel((ours.width - 15 + x, 20)), theirs.getpixel((1009 + x, 20))) for x in range(15)]

    assert max(abs(a - b) for p, q in strip for a, b in zip(p, q, strict=True)) <= 6


@pytest.fixture(scope="module")
def two_windows_of_one_program():
    import shutil
    import tempfile

    from plasma_session import desktop_session, missing_programs

    if missing_programs():
        pytest.skip("needs KWin and Plasma")
    work = tempfile.mkdtemp(prefix="c95-group-", dir="/tmp")
    try:
        return desktop_session(
            "luna",
            work,
            settings=[("DECORATION", "aero")],
            taskbar_style="aero",
            windows=[
                ("First", "qt", "minimized", "org.chicago95.test.notes"),
                ("Second", "qt", "minimized", "org.chicago95.test.notes"),
            ],
            launchers=0,
            screen=(1024, 768),
        ).convert("RGB")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def test_two_windows_of_one_program_combine_into_one_superbar_button(two_windows_of_one_program):
    assert len(icon_columns(two_windows_of_one_program)) == 1


def test_combined_button_ends_in_one_stacked_card_over_its_last_8_columns(two_windows_of_one_program):
    # The slot is x 59..118: the face 52 wide, then the card strip (two windows) at x 111..118, drawn over the bar as
    # it shows just past the button.
    from test_aero_buttons import rendered
    from test_aero_taskbar import generator

    ours = bar(two_windows_of_one_program)
    strip = rendered(generator.group_face_svg("group-2"), (8, 40))
    differences = []
    for x in range(8):
        for y in range(40):
            *colour, alpha = strip.getpixel((x, y))
            behind = ours.getpixel((125 + x, y))
            expected = [c * alpha / 255 + b * (1 - alpha / 255) for c, b in zip(colour, behind, strict=True)]
            differences.append(max(abs(a - b) for a, b in zip(ours.getpixel((111 + x, y)), expected, strict=True)))

    assert max(differences) <= 8


def nine_programs_on_a_640_bar(pointer_steps=()):
    """Nine programs' windows on a 640-wide superbar, which holds seven: the first page, or another after the pointer
    steps (the pointer resting off the bar, so no button is lit)."""
    import shutil
    import tempfile

    from plasma_session import desktop_session, missing_programs

    if missing_programs():
        pytest.skip("needs KWin and Plasma")
    work = tempfile.mkdtemp(prefix="c95-pages-", dir="/tmp")
    try:
        return desktop_session(
            "luna",
            work,
            settings=[("DECORATION", "aero")],
            taskbar_style="aero",
            windows=[(f"Window {n}", "qt", "minimized", f"org.chicago95.test.program{n}") for n in range(9)],
            launchers=0,
            screen=(640, 480),
            pointer_steps=[*pointer_steps, "move:320,200", "wait:1"],
        ).convert("RGB")
    finally:
        shutil.rmtree(work, ignore_errors=True)


@pytest.fixture(scope="module")
def more_windows_than_fit():
    return nine_programs_on_a_640_bar()


@pytest.fixture(scope="module")
def second_page():
    return nine_programs_on_a_640_bar(["move:501,470", "click:left", "wait:1"])  # the down arrow, at x 493..509


def arrow_match(image, state):
    """The smallest average difference between the drawn arrow, composited over the bar just past its right edge
    (buttons lie to its left), and the bar at any place along it, with that place."""
    from test_aero_buttons import rendered
    from test_aero_taskbar import ARROW_SIZE, generator

    arrow = rendered(generator.scroll_arrow_svg(state, ARROW_SIZE), ARROW_SIZE)
    top = 0 if state.startswith("up") else ARROW_SIZE[1]
    best = None
    for left in range(60, image.width - ARROW_SIZE[0] - 2):
        total = 0
        for x in range(ARROW_SIZE[0]):
            for y in range(ARROW_SIZE[1]):
                *colour, alpha = arrow.getpixel((x, y))
                behind = image.getpixel((left + ARROW_SIZE[0] + 2, top + y))
                expected = [c * alpha / 255 + b * (1 - alpha / 255) for c, b in zip(colour, behind, strict=True)]
                total += max(abs(a - b) for a, b in zip(image.getpixel((left + x, top + y)), expected, strict=True))
        best = min(best or (total, left), (total, left))
    return best[0] / (ARROW_SIZE[0] * ARROW_SIZE[1]), best[1]


def test_more_windows_than_fit_show_a_page_of_them_with_the_paging_arrows_after_it(more_windows_than_fit):
    ours = bar(more_windows_than_fit)
    up_difference, up_x = arrow_match(ours, "up-disabled")
    down_difference, down_x = arrow_match(ours, "down-normal")
    icons = icon_columns(more_windows_than_fit, task_area=up_x)

    assert (len(icons) == 7, up_difference <= 8, down_difference <= 8, down_x == up_x, icons[-1][1] < up_x) == (
        True,
        True,
        True,
        True,
        True,
    )


def test_down_arrow_shows_the_last_two_windows_from_the_first_slot_with_only_the_up_arrow_enabled(second_page):
    ours = bar(second_page)
    up_difference, up_x = arrow_match(ours, "up-normal")
    down_difference, down_x = arrow_match(ours, "down-disabled")

    assert (icon_columns(second_page, task_area=up_x), up_difference <= 8, down_difference <= 8, up_x) == (
        [(73, 104), (135, 166)],
        True,
        True,
        493,
    )


@pytest.fixture(scope="module")
def hidden_tray_icons():
    from render_report import aero_desktop

    image = aero_desktop(hidden_applets=["org.kde.plasma.notifications"], tray_icons=3)  # as win7peek.png's three
    if image is None:
        pytest.skip("needs KWin and Plasma")
    return image.convert("RGB")


def test_show_hidden_icons_button_is_win7peeks_before_the_flag_within_six_levels_on_average(hidden_tray_icons):
    # win7peek.png: the triangle's tip at (850, 747), the 21 by 20 button at x 840 and y 739.
    box = (840, 739, 861, 759)
    ours, theirs = hidden_tray_icons.crop(box), screenshot("win7peek").convert("RGB").crop(box)
    differences = [
        max(abs(a - b) for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True))
        for x in range(21)
        for y in range(20)
    ]

    assert sum(differences) / len(differences) <= 6


def test_bar_before_the_show_hidden_icons_button_darkens_as_win7peeks_within_two_levels_on_average(hidden_tray_icons):
    # Windows 7's darkening at the notification area starts the button's 21 pixels further left while it shows.
    box = (770, 731, 838, 766)
    ours, theirs = hidden_tray_icons.crop(box), screenshot("win7peek").convert("RGB").crop(box)
    differences = [
        abs(a - b)
        for x in range(ours.width)
        for y in range(ours.height)
        for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True)
    ]

    assert sum(differences) / len(differences) <= 2


def test_tray_icons_start_at_win7peeks_866_890_and_914(hidden_tray_icons):
    from plasma_session import ICON_COLOUR

    row = [x for x in range(800, 1024) if hidden_tray_icons.getpixel((x, 748)) == ICON_COLOUR]

    assert [x for x in row if x - 1 not in row] == [866, 890, 914]


@pytest.fixture(scope="module")
def hidden_icons_open():
    from render_report import aero_desktop

    image = aero_desktop(
        hidden_applets=["org.kde.plasma.notifications"],
        tray_icons=3,
        pointer_steps=["move:850,749", "click:left", "wait:1", "move:500,300", "wait:1"],
    )
    if image is None:
        pytest.skip("needs KWin and Plasma")
    return image.convert("RGB")


def test_show_hidden_icons_button_points_down_while_its_popup_is_open(hidden_icons_open):
    # The open button's triangle: seven pixels wide on its top row (y 747), one at its foot (y 750).
    top_row = [sum(hidden_icons_open.getpixel((x, 747))) > 600 for x in range(846, 855)]

    assert top_row == [False, True, True, True, True, True, True, True, False]


@pytest.fixture(scope="module")
def unlocked():
    from render_report import aero_desktop

    image = aero_desktop(tasks_config=[("locked", "false")])
    if image is None:
        pytest.skip("needs KWin and Plasma")
    return image.convert("RGB")


def test_unlocked_taskbar_shows_the_grip_where_its_band_began_and_moves_the_pinned_programs_12_right(unlocked, desktop):
    from test_aero_buttons import rendered
    from test_aero_taskbar import generator

    grip = rendered(generator.grip_svg(), (12, 40))
    locked_bar, unlocked_bar = bar(desktop), bar(unlocked)
    band = 58  # the first pinned cell, its button one pixel in at x 59
    differences = []
    for x in range(12):
        for y in range(40):
            *colour, alpha = grip.getpixel((x, y))
            behind = locked_bar.getpixel((band + x, y))  # bar there when locked: the pinned icon starts at x 73
            expected = [c * alpha / 255 + b * (1 - alpha / 255) for c, b in zip(colour, behind, strict=True)]
            seen = unlocked_bar.getpixel((band + x, y))
            differences.append(max(abs(a - b) for a, b in zip(seen, expected, strict=True)))

    assert (max(differences) <= 6, [a + 12 for a, _ in icon_columns(desktop)]) == (
        True,
        [a for a, _ in icon_columns(unlocked)],
    )
