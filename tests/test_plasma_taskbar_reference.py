"""The real taskbar, laid out by Plasma (tests/plasma_session.py), against the originals' taskbars.

Each original's windows, Quick Launch entries and tray icons are recreated with solid 16px squares as
icons, so every icon's place is measured exactly; frames, separators, the tray box and the labels are
compared with the original's pixels at the original's positions. Positions are in the taskbar, which
is the bottom 28 rows of the screen (640x480; 2001's is 800x600). Luna's is 30 rows: see the end.
"""

import pytest
from conftest import needs_ui_font
from PIL import Image
from plasma_session import CONTENT, ICON_COLOUR, ICON_SIZE, missing_programs
from reference import close, screenshot
from test_taskbar_reference import (
    BUTTON_HEIGHT,
    BUTTON_TOP,
    BUTTONS,
    HEIGHT,
    HELD_START_BUTTON,
    START_MENU_RIGHT_EDGE,
    TASKBARS,
    TRAYS,
    taskbar,
)

pytestmark = [
    needs_ui_font,
    pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}"),
]

SESSION_LOOKS = [look for look in TASKBARS if look in CONTENT]  # 1995, 1998, 2000, 2001
ICON_TOP = 7  # every icon's top row in the originals
TASK_ICON_LEFT = 4  # from a task button's left edge; a row lower while pressed
QUICK_LAUNCH = {"1998": [72, 95, 118, 141], "2000": [74, 97, 120]}  # the icons' left columns: 23px cells
ETCHED_LINES = {"1998": [58, 165], "2000": [60, 144]}  # the separators' etched lines
TRAY_ICONS = {"1995": [560], "1998": [543, 560], "2000": [548], "2001": []}  # XP Classic's tray holds the clock alone
TAHOMA_LOOKS = ("2000", "2001")  # their labels and clocks are Tahoma, whose capitals and digits are a row shorter
LABEL_FROM = 20  # labels start right of this, from the task button's left edge


@pytest.fixture(scope="module")
def ours(desktops):
    """Our taskbar for a look: the bottom rows of its desktop."""
    return lambda look: bottom_rows(desktops(look), HEIGHT)


def bottom_rows(screen, height):
    return screen.crop((0, screen.height - height, screen.width, screen.height))


def clock_left(look):
    """Where the clock's lettering may start: right of the last tray icon, or just inside the box."""
    return TRAY_ICONS[look][-1] + ICON_SIZE + 1 if TRAY_ICONS[look] else TRAYS[look][0] + 2


def squares(image, left, right):
    """(left, top, right, bottom) of each block of the test icons' colour between the columns, left to right."""
    columns = [x for x in range(left, right) if any(image.getpixel((x, y)) == ICON_COLOUR for y in range(HEIGHT))]
    blocks = []
    for x in columns:
        if blocks and x == blocks[-1][-1] + 1:
            blocks[-1].append(x)
        else:
            blocks.append([x])
    found = []
    for block in blocks:
        rows = [y for y in range(HEIGHT) if any(image.getpixel((x, y)) == ICON_COLOUR for x in block)]
        found.append((block[0], rows[0], block[-1], rows[-1]))
    return found


def icon_box(left, top=ICON_TOP):
    return (left, top, left + ICON_SIZE - 1, top + ICON_SIZE - 1)


def ink(image, left, right, top=BUTTON_TOP + 2, bottom=BUTTON_TOP + BUTTON_HEIGHT - 2):
    """(left, top, right, bottom) of the label's dark pixels (text, not the checkerboard or bevel)."""
    xs, ys = [], []
    for x in range(left, right):
        for y in range(top, bottom):
            if sum(image.getpixel((x, y))) < 150 and image.getpixel((x, y)) != ICON_COLOUR:
                xs.append(x)
                ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


@pytest.mark.parametrize("look", SESSION_LOOKS)
def test_start_button_is_where_the_originals_is(ours, look):
    """Its bevel and the face around it; the logo and lettering are test_taskbar_reference.py's."""
    if look in HELD_START_BUTTON:
        pytest.skip("the original's Start menu is open, so its Start button is held down; ours is not")
    original, mine = taskbar(look), ours(look)
    (left, right), _ = BUTTONS[look]
    columns, rows = range(left - 1, right + 2), range(BUTTON_TOP - 1, BUTTON_TOP + BUTTON_HEIGHT + 1)
    edges = [
        (x, y)
        for x in columns
        for y in rows
        if x in columns[:3] or x in columns[-3:] or y in rows[:3] or y in rows[-3:]
    ]
    assert [point for point in edges if not close(mine.getpixel(point), original.getpixel(point))] == []


@pytest.mark.parametrize("look", QUICK_LAUNCH)
def test_quick_launch_icons_sit_in_the_originals_cells(ours, look):
    first, last = QUICK_LAUNCH[look][0] - 8, QUICK_LAUNCH[look][-1] + ICON_SIZE + 8
    assert squares(ours(look), first, last) == [icon_box(left) for left in QUICK_LAUNCH[look]]


@pytest.mark.parametrize("look", QUICK_LAUNCH)
def test_quick_launch_icons_are_in_their_cells_right_after_setup_restarts_plasma(desktops, look):
    bar = bottom_rows(desktops(look).info["setup_screen"], HEIGHT)
    first, last = QUICK_LAUNCH[look][0] - 8, QUICK_LAUNCH[look][-1] + ICON_SIZE + 8

    assert squares(bar, first, last) == [icon_box(left) for left in QUICK_LAUNCH[look]]


def test_quick_launch_icons_are_in_their_cells_when_the_windows_were_open_before_plasma_started(desktops):
    """As after a login that restores the last session: the task model has its windows before its launchers."""
    look = "2000"
    bar = bottom_rows(desktops(look, windows_first=True), HEIGHT)
    first, last = QUICK_LAUNCH[look][0] - 8, QUICK_LAUNCH[look][-1] + ICON_SIZE + 8

    assert squares(bar, first, last) == [icon_box(left) for left in QUICK_LAUNCH[look]]


def test_1995_has_no_quick_launch(ours):
    (_, start_right), tasks = BUTTONS["1995"]
    assert squares(ours("1995"), start_right + 1, tasks[0][0]) == []


@pytest.mark.parametrize("look", ETCHED_LINES)
def test_separators_are_where_the_originals_are(ours, look):
    original, mine = taskbar(look), ours(look)
    for x in ETCHED_LINES[look]:
        assert all(close(mine.getpixel((x + dx, 12)), original.getpixel((x + dx, 12))) for dx in (-1, 0, 1, 2)), x


@pytest.mark.parametrize("look", SESSION_LOOKS)
def test_task_buttons_have_the_originals_edges_and_gaps(ours, look):
    """Every task button's outline and the 3px gaps between them, pixel for pixel."""
    original, mine = taskbar(look), ours(look)
    for left, right, _pressed in BUTTONS[look][1]:
        outline = [
            (x, y)
            for x in range(left - 1, right + 2)
            for y in range(BUTTON_TOP - 1, BUTTON_TOP + BUTTON_HEIGHT + 1)
            if x in (left - 1, left, left + 1, right - 1, right, right + 1)
            or y in (BUTTON_TOP, BUTTON_TOP + BUTTON_HEIGHT - 1)
        ]
        outline = [(x, y) for x, y in outline if x > START_MENU_RIGHT_EDGE.get(look, -1) or y >= BUTTON_TOP]
        differing = [point for point in outline if not close(mine.getpixel(point), original.getpixel(point))]
        assert differing == [], f"button at {left}"


@pytest.mark.parametrize("look", SESSION_LOOKS)
def test_task_button_icons_sit_where_the_originals_do(ours, look):
    expected = [icon_box(left + TASK_ICON_LEFT, ICON_TOP + pressed) for left, _right, pressed in BUTTONS[look][1]]
    first, last = BUTTONS[look][1][0][0], BUTTONS[look][1][-1][1]
    assert squares(ours(look), first, last + 1) == expected


# The originals' font leaves a blank column before most capitals but not before W; ours starts every
# glyph at its origin and the labels a pixel further in, so these titles start a pixel right of the original's.
WITHOUT_LEADING_BLANK = {("1995", 256), ("1998", 176)}  # "Windows", "WinPopup"


@pytest.mark.parametrize("look", SESSION_LOOKS)
def test_task_labels_start_and_sit_where_the_originals_do(ours, look):
    """The first stroke's column and the lettering's rows; 2000's titles are Tahoma, whose capitals are
    a row shorter than the UI font's: there only the baseline row is compared."""
    original, mine = taskbar(look), ours(look)
    for left, right, _pressed in BUTTONS[look][1]:
        theirs, our = ink(original, left + LABEL_FROM, right - 2), ink(mine, left + LABEL_FROM, right - 2)
        first = theirs[0] + ((look, left) in WITHOUT_LEADING_BLANK)
        top = theirs[1] if look not in TAHOMA_LOOKS else our and our[1]
        assert our is not None and (our[0], our[1], our[3]) == (first, top, theirs[3]), (left, our, theirs)


@pytest.mark.parametrize("look", SESSION_LOOKS)
def test_active_task_label_is_bold(ours, look):
    """Bold strokes are two pixels wide: the active label has as much ink per column as the original's."""
    original, mine = taskbar(look), ours(look)

    def ink_per_column(image, left, right):
        box = ink(image, left + LABEL_FROM, right - 2)
        dark = sum(
            1 for x in range(box[0], box[2] + 1) for y in range(box[1], box[3] + 1) if sum(image.getpixel((x, y))) < 150
        )
        return dark / (box[2] - box[0] + 1)

    for left, right, pressed in BUTTONS[look][1]:
        assert abs(ink_per_column(mine, left, right) - ink_per_column(original, left, right)) < 1.0, (left, pressed)


@pytest.mark.parametrize("look", SESSION_LOOKS)
def test_tray_box_has_the_originals_edges(ours, look):
    original, mine = taskbar(look), ours(look)
    left, right = TRAYS[look]
    edges = [
        (x, y)
        for x in range(left - 1, right + 2)
        for y in range(BUTTON_TOP - 1, BUTTON_TOP + BUTTON_HEIGHT + 1)
        if x in (left - 1, left, right, right + 1)
        or y in (BUTTON_TOP - 1, BUTTON_TOP, BUTTON_TOP + BUTTON_HEIGHT - 1, BUTTON_TOP + BUTTON_HEIGHT)
    ]
    differing = [point for point in edges if not close(mine.getpixel(point), original.getpixel(point))]
    assert differing == []


@pytest.mark.parametrize("look", SESSION_LOOKS)
def test_tray_icons_sit_where_the_originals_do(ours, look):
    left, right = TRAYS[look]
    assert squares(ours(look), left, right) == [icon_box(x) for x in TRAY_ICONS[look]]


@pytest.mark.parametrize("look", SESSION_LOOKS)
def test_clock_is_black_and_centred_on_the_originals_rows(ours, look):
    """The time differs; its lettering's rows, colour and centre do not. 2000's and 2001's clocks are Tahoma, whose
    digits are a row shorter than the UI font's: there only the baseline row is compared."""
    original, mine = taskbar(look), ours(look)
    left, right = TRAYS[look]
    start = clock_left(look)
    theirs, our = ink(original, start, right), ink(mine, start, right)
    rows = (lambda box: box[3]) if look in TAHOMA_LOOKS else (lambda box: (box[1], box[3]))
    assert our is not None and rows(our) == rows(theirs), (our, theirs)
    assert abs((our[0] + our[2]) - (theirs[0] + theirs[2])) <= 2, (our, theirs)  # centres within a pixel
    dark = {
        mine.getpixel((x, y))
        for x in range(our[0], our[2] + 1)
        for y in range(our[1], our[3] + 1)
        if sum(mine.getpixel((x, y))) < 150
    }
    assert dark == {(0, 0, 0)}


def widest_blank(image, box):
    """The widest run of empty columns inside the lettering's box: the space before AM or PM."""
    runs, run = [], 0
    for x in range(box[0], box[2] + 1):
        empty = all(sum(image.getpixel((x, y))) >= 150 for y in range(box[1], box[3] + 1))
        run = run + 1 if empty else 0
        runs.append(run)
    return max(runs)


@pytest.mark.parametrize("look", SESSION_LOOKS)
def test_clock_has_a_full_space_before_am_and_pm(ours, look):
    original, mine = taskbar(look), ours(look)
    left, right = TRAYS[look]
    start = clock_left(look)
    assert widest_blank(mine, ink(mine, start, right)) == widest_blank(original, ink(original, start, right))


BUSY_TRAY_APPLETS = ["org.kde.plasma.notifications", "org.kde.plasma.clipboard"]


def test_busy_tray_keeps_every_icon_16px_17px_apart_and_off_the_clock(desktops):
    """A tray with Plasma's applets (drawn by Plasma, not the test's icons) beside three programs' icons:
    every item is drawn 16px wide on the icon row, 17px apart, ending before the clock's lettering."""
    bar = bottom_rows(desktops("1998", tray_applets=BUSY_TRAY_APPLETS, tray_icons=3), HEIGHT)
    face = bar.getpixel((TRAYS["1998"][0] + 2, 6))
    clock = ink(bar, TRAY_ICONS["1998"][-1] + ICON_SIZE + 1, TRAYS["1998"][1])
    shadow_row = [x for x in range(300, bar.width) if close(bar.getpixel((x, BUTTON_TOP)), (128, 128, 128))]
    box_left = next(x for x in shadow_row if all(x + dx in shadow_row for dx in range(40)))  # the box's top line
    drawn = [
        x
        for x in range(box_left + 2, clock[0])
        if any(
            max(abs(a - b) for a, b in zip(bar.getpixel((x, y)), face, strict=False)) > 30
            for y in range(ICON_TOP, ICON_TOP + ICON_SIZE)
        )
    ]
    icons = []
    for x in drawn:
        if icons and x <= icons[-1][1] + 1:
            icons[-1][1] = x
        else:
            icons.append([x, x])
    assert len(icons) == 3 + len(BUSY_TRAY_APPLETS), icons
    assert all(right - left + 1 <= ICON_SIZE for left, right in icons), icons
    assert icons[-1][1] < clock[0] - 1, (icons, clock)


def test_hidden_icons_chevron_leads_the_tray_box_and_the_icons_keep_their_places(ours, desktops):
    """With an applet hidden, the originals draw a black chevron first in the tray box, the icons after
    it in their usual places by the clock; nothing of it reaches the clock's cell, which would take its clicks."""
    plain = ours("1998")
    clock_left = ink(plain, TRAY_ICONS["1998"][-1] + ICON_SIZE, TRAYS["1998"][1])[0]
    bar = bottom_rows(desktops("1998", hidden_applets=["org.kde.plasma.notifications"]), HEIGHT)
    shadow_row = [x for x in range(300, bar.width) if close(bar.getpixel((x, BUTTON_TOP)), (128, 128, 128))]
    box_left = next(x for x in shadow_row if all(x + dx in shadow_row for dx in range(40)))
    rows = range(ICON_TOP, ICON_TOP + ICON_SIZE)
    green = [x for x in range(box_left, clock_left) if any(bar.getpixel((x, y)) == ICON_COLOUR for y in rows)]
    black = [x for x in range(box_left + 2, green[0]) if any(sum(bar.getpixel((x, y))) < 150 for y in rows)]
    assert (green[0], green[-1]) == (TRAY_ICONS["1998"][0], TRAY_ICONS["1998"][-1] + ICON_SIZE - 1), green
    assert black, (box_left, green[0])
    chevron_rows = [y for y in range(HEIGHT) if any(sum(bar.getpixel((x, y))) < 150 for x in black)]
    above, below = chevron_rows[0] - ICON_TOP, ICON_TOP + ICON_SIZE - 1 - chevron_rows[-1]
    assert (len(chevron_rows), abs(above - below) <= 1) == (7, True), (
        chevron_rows
    )  # its own 7 rows, centred on the icons'


LUNA_PANEL_HEIGHT = 30
LUNA_GAP_COLUMN = 650  # between the task buttons and the tray: the panel's own rows
LUNA_TASKS = (350, 520)  # inside the second task button (normal) and the third (pressed), in the 800px panel
TEAL = (0, 128, 128)
LUNA_TASK_BUTTONS = [(106, 160), (266, 160), (426, 160)]
LUNA_TRAY_LEFT = 707
LUNA_ELEMENT_BUDGETS = {
    "whole": 0.021,
    "start button": 0.07,
    "first task button": 0.03,
    "second task button": 0.026,
    "third task button, pressed": 0.023,
    "tray box": 0.013,
}


def is_green(colour):
    return colour[1] > colour[0] + 40 and colour[1] > colour[2] + 40


def luna_masks():
    masks = [(6, 4, 78, 27), (LUNA_TRAY_LEFT + 3, 4, 795, 26)]
    for left, width in LUNA_TASK_BUTTONS:
        masks += [(left + 4, 4, left + 24, 22), (left + 25, 5, left + width - 5, 22)]
    return masks


def luna_element_boxes():
    boxes = {"whole": (0, 0, 800, LUNA_PANEL_HEIGHT), "start button": (0, 0, 100, LUNA_PANEL_HEIGHT)}
    names = ["first task button", "second task button", "third task button, pressed"]
    for name, (left, width) in zip(names, LUNA_TASK_BUTTONS, strict=True):
        boxes[name] = (left - 2, 0, left + width + 2, LUNA_PANEL_HEIGHT)
    boxes["tray box"] = (LUNA_TRAY_LEFT - 3, 0, 800, LUNA_PANEL_HEIGHT)
    return boxes


def differing_fraction_outside_masks(ours, original, box, masks):
    left, top, right, bottom = box
    points = [
        (x, y)
        for x in range(left, right)
        for y in range(top, bottom)
        if not any(m_left <= x < m_right and m_top <= y < m_bottom for m_left, m_top, m_right, m_bottom in masks)
    ]
    return sum(not close(ours.getpixel(point), original.getpixel(point)) for point in points) / len(points)


@pytest.fixture(scope="module")
def luna_bar(desktops):
    return bottom_rows(desktops("luna"), LUNA_PANEL_HEIGHT)


def test_luna_panel_gap_column_has_all_30_rows_of_the_xp_gradient(luna_bar):
    original = screenshot("xprunning")
    differing = [
        y
        for y in range(LUNA_PANEL_HEIGHT)
        if not close(luna_bar.getpixel((LUNA_GAP_COLUMN, y)), original.getpixel((LUNA_GAP_COLUMN, y)))
    ]
    assert differing == []


@pytest.mark.parametrize("element", list(LUNA_ELEMENT_BUDGETS))
def test_luna_element_differs_from_the_xp_taskbar_in_less_than_its_budget_of_pixels_outside_icons_and_text(
    luna_bar, element
):
    original = screenshot("xprunning")
    differing = differing_fraction_outside_masks(luna_bar, original, luna_element_boxes()[element], luna_masks())
    assert differing < LUNA_ELEMENT_BUDGETS[element]


def test_luna_start_pill_is_green_to_the_right_of_its_lettering(luna_bar):
    assert close(luna_bar.getpixel((90, 15)), screenshot("xprunning").getpixel((90, 15)), 24)


def test_luna_pressed_task_button_is_darker_than_the_normal_one_above_the_icons(luna_bar):
    normal, pressed = (sum(luna_bar.getpixel((x, 5))) for x in LUNA_TASKS)
    assert pressed < normal


def test_luna_tray_box_has_the_xp_gradient_right_of_the_clock(luna_bar):
    original = screenshot("xprunning")
    rows = [*range(0, 6), *range(24, LUNA_PANEL_HEIGHT - 2)]
    assert [y for y in rows if not close(luna_bar.getpixel((795, y)), original.getpixel((795, y)))] == []


def test_1995_look_with_the_luna_taskbar_has_a_30_row_panel_a_green_pill_and_the_teal_desktop(desktops):
    screen = desktops("1995", taskbar_style="luna", components=["background"], windows=[])
    height = screen.height
    assert (
        close(screen.getpixel((400, height - LUNA_PANEL_HEIGHT)), screenshot("xprunning").getpixel((400, 0)), 16),
        screen.getpixel((400, height - LUNA_PANEL_HEIGHT - 1)),
        is_green(screen.getpixel((90, height - 15))),
        screen.getpixel((300, 200)),
    ) == (True, TEAL, True, TEAL)


LUNA_START = (0, 0, 98, LUNA_PANEL_HEIGHT)
LUNA_START_WHOLE_BUDGET = 0.28
LUNA_NOTCH = (10, 46, 82)  # the tray box's dark left column, xprunning.png x=707
LUNA_NOTCH_X = 707
LUNA_TRAY_ICON = (718, 7, 733, 22)  # xprunning.png: 16px icon, 11px after the notch, rows 7..22
LUNA_CLOCK_INK_ROWS = (11, 18)  # xprunning.png: the clock's digits and capitals
LUNA_TASK_RING = (48, 104, 222)  # a normal task button's left outline
LUNA_PRESSED_TASK_RING = (8, 42, 112)  # the active one's
LUNA_QUICK_LAUNCH_ICONS = [119, 142, 165]  # xpquicklaunch.png (2x, halved): 23px cells, 7px after the grip
LUNA_GRIPS = [(106, 106), (191, 168)]  # ours, the reference's: the grip's first column
LUNA_GRIP_WIDTH = 6
LUNA_GRIP_BUDGET = 0.03
LUNA_FIRST_TASK = 201  # the second grip's first column and 10px: its 6px and the 4px after it
LUNA_TASK_WIDTH = 160
LUNA_CHEVRON_RIM = (
    (61, 88, 154),
    (134, 173, 212),
    (49, 74, 140),
    (136, 158, 208),
)  # left, right, top, bottom of the sphere's ring
LUNA_PANEL_BLUE = (36, 92, 215)
LUNA_CHEVRON_WHITE = 240
LUNA_HIDDEN_APPLET = "org.kde.plasma.notifications"
LUNA_WINDOWS = [("Control Panel", "gtk4", "minimized"), ("My Computer", "x11", "minimized")]


def box_of(image, keep, columns):
    points = [(x, y) for x in columns for y in range(image.height) if keep(image.getpixel((x, y)))]
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return (min(xs), min(ys), max(xs), max(ys))


def lettering_box(image):
    return box_of(image, lambda colour: min(colour) > 235, range(34, 80))


def flag_box(image):
    points = []
    for y in range(4, 27):
        pill = image.getpixel((33, y))
        points += [
            (x, y)
            for x in range(4, 33)
            if sum(abs(a - b) for a, b in zip(image.getpixel((x, y)), pill, strict=False)) > 110
        ]
    xs, ys = [x for x, _ in points], [y for _, y in points]
    return (min(xs), min(ys), max(xs), max(ys))


def differing_fraction(ours, original):
    points = [(x, y) for x in range(original.width) for y in range(original.height)]
    return sum(not close(ours.getpixel(point), original.getpixel(point)) for point in points) / len(points)


@pytest.fixture(scope="module")
def luna_start_reference():
    return screenshot("xptaskbar-1x").crop(LUNA_START)


@pytest.fixture(scope="module")
def luna_quick_launch_bar(desktops):
    screen = desktops("luna", launchers=3, windows=LUNA_WINDOWS, hidden_applets=[LUNA_HIDDEN_APPLET])
    return bottom_rows(screen, LUNA_PANEL_HEIGHT)


@pytest.fixture(scope="module")
def quick_launch_reference():
    band = screenshot("xpquicklaunch").crop((0, 181, 492, 241))
    return band.resize((band.width // 2, band.height // 2), Image.NEAREST)


def test_luna_start_pill_with_flag_and_lettering_differs_from_xptaskbar_in_less_than_its_budget(
    luna_bar, luna_start_reference
):
    assert differing_fraction(luna_bar.crop(LUNA_START), luna_start_reference) < LUNA_START_WHOLE_BUDGET


def test_luna_start_lettering_lands_within_a_pixel_of_the_xp_lettering(luna_bar, luna_start_reference):
    ours, original = lettering_box(luna_bar), lettering_box(luna_start_reference)
    assert all(abs(a - b) <= 1 for a, b in zip(ours, original, strict=True)), (ours, original)


def test_luna_start_flag_lands_within_a_pixel_of_the_xp_flag(luna_bar, luna_start_reference):
    ours, original = flag_box(luna_bar), flag_box(luna_start_reference)
    assert all(abs(a - b) <= 1 for a, b in zip(ours, original, strict=True)), (ours, original)


@pytest.mark.parametrize("ours_x, original_x", LUNA_GRIPS)
def test_luna_quick_launch_grip_matches_the_xp_grip_in_less_than_its_budget(
    luna_quick_launch_bar, quick_launch_reference, ours_x, original_x
):
    box = (0, 0, LUNA_GRIP_WIDTH, LUNA_PANEL_HEIGHT)
    ours = luna_quick_launch_bar.crop((ours_x, 0, ours_x + LUNA_GRIP_WIDTH, LUNA_PANEL_HEIGHT))
    original = quick_launch_reference.crop((original_x, 0, original_x + LUNA_GRIP_WIDTH, LUNA_PANEL_HEIGHT))
    assert differing_fraction(ours, original) < LUNA_GRIP_BUDGET, box


def test_luna_quick_launch_icons_sit_23px_apart_from_x_119_on_rows_7_to_22(luna_quick_launch_bar):
    found = squares(luna_quick_launch_bar, 100, 190)
    assert [(left, top, right - left + 1, bottom - top + 1) for left, top, right, bottom in found] == [
        (left, ICON_TOP, ICON_SIZE, ICON_SIZE) for left in LUNA_QUICK_LAUNCH_ICONS
    ]


def test_luna_task_buttons_follow_the_second_grip_and_touch_at_a_pitch_of_160(luna_quick_launch_bar):
    outlines = [
        x
        for x in range(190, 700)
        if close(luna_quick_launch_bar.getpixel((x, 15)), LUNA_TASK_RING, 4)
        or close(luna_quick_launch_bar.getpixel((x, 15)), LUNA_PRESSED_TASK_RING, 4)
    ]
    assert outlines[:2] == [LUNA_FIRST_TASK, LUNA_FIRST_TASK + LUNA_TASK_WIDTH]


def notch_column(bar):
    return next(x for x in range(600, 790) if close(bar.getpixel((x, 3)), LUNA_NOTCH, 14))


def test_luna_hidden_icons_button_is_a_circle_on_the_notch_spanning_rows_7_to_22(luna_quick_launch_bar):
    notch = notch_column(luna_quick_launch_bar)
    bar = luna_quick_launch_bar
    rim = [
        bar.getpixel((notch - 8, 15)),
        bar.getpixel((notch + 7, 15)),
        bar.getpixel((notch - 1, ICON_TOP)),
        bar.getpixel((notch - 1, ICON_TOP + ICON_SIZE - 1)),
    ]
    beyond = [
        bar.getpixel((notch - 9, 15)),
        bar.getpixel((notch - 1, ICON_TOP - 1)),
        bar.getpixel((notch - 1, ICON_TOP + ICON_SIZE)),
    ]
    assert (
        [close(colour, expected, 30) for colour, expected in zip(rim, LUNA_CHEVRON_RIM, strict=True)],
        [close(colour, LUNA_PANEL_BLUE, 16) for colour in beyond],
    ) == ([True] * 4, [True] * 3)


def test_luna_hidden_icons_button_has_a_white_arrow_and_the_icons_keep_their_places(luna_quick_launch_bar):
    notch = notch_column(luna_quick_launch_bar)
    arrow = box_of(luna_quick_launch_bar, lambda colour: min(colour) > LUNA_CHEVRON_WHITE, range(notch - 7, notch + 7))
    icon = squares(luna_quick_launch_bar, notch, 790)[0]
    assert (arrow[0] > notch - 7, arrow[2] < notch + 7, icon) == (True, True, (notch + 11, ICON_TOP, notch + 26, 22))


def test_luna_tray_icon_sits_11px_after_the_notch_on_rows_7_to_22(luna_bar):
    assert squares(luna_bar, LUNA_NOTCH_X, 790) == [LUNA_TRAY_ICON]


def test_luna_clock_digits_use_the_xp_rows_and_start_right_of_the_icon(luna_bar):
    ink = box_of(luna_bar, lambda colour: min(colour) > 215, range(LUNA_TRAY_ICON[2] + 2, 790))
    assert (ink[1], ink[3], ink[0] > LUNA_TRAY_ICON[2] + 5) == (*LUNA_CLOCK_INK_ROWS, True)


LUNA_NARROW_BAND = 60  # holds two launchers beside the chevron: the width a separator drag saves
CLASSIC_BEVEL_COLOURS = ((192, 192, 192), (128, 128, 128), (223, 223, 223))
LUNA_CHEVRON_GLYPH = (123, 182, 232)


@pytest.fixture(scope="module")
def luna_resized_band_bar(desktops):
    screen = desktops(
        "luna",
        launchers=3,
        windows=LUNA_WINDOWS,
        tasks_config=[("quickLaunchWidth", LUNA_NARROW_BAND)],
    )
    return bottom_rows(screen, LUNA_PANEL_HEIGHT)


def test_luna_band_resized_by_a_separator_drag_keeps_the_luna_grips_cells_chevron_and_buttons(luna_resized_band_bar):
    bar = luna_resized_band_bar
    classic = [(x, y) for x in range(100, 700) for y in range(3, 27) if bar.getpixel((x, y)) in CLASSIC_BEVEL_COLOURS]
    glyph = [x for x in range(100, 260) for y in range(3, 27) if bar.getpixel((x, y)) == LUNA_CHEVRON_GLYPH]
    icons = squares(bar, 100, 190)
    assert (classic, len(glyph) > 0, [left for left, *_ in icons]) == ([], True, LUNA_QUICK_LAUNCH_ICONS[:2])


# Opening Plasma's hidden-items popup must not repaint the notification area as a
# pressed task. The original's tray retains its cyan gradient (xprunning.png).
LUNA_OPEN_TRAY_STEPS = ("move:700,580", "wait:0.3", "move:706,585", "wait:0.5", "click:left", "wait:2")


@pytest.fixture(scope="module")
def luna_open_tray_bar(desktops):
    screen = desktops("luna", hidden_applets=[LUNA_HIDDEN_APPLET], pointer_steps=LUNA_OPEN_TRAY_STEPS)
    return bottom_rows(screen, LUNA_PANEL_HEIGHT)


def test_luna_tray_under_its_open_popup_keeps_the_original_cyan_gradient(
    luna_open_tray_bar,
):
    bar, notch = luna_open_tray_bar, LUNA_NOTCH_X
    columns, rows = range(notch + 9, notch + 17), [*range(1, 6), *range(24, 29)]
    pixels = [bar.getpixel((x, y)) for x in columns for y in rows]
    assert (
        [colour for colour in pixels if min(colour) > 200],
        all(colour[2] > colour[1] + 20 and colour[2] > colour[0] + 60 for colour in pixels),
        close(bar.getpixel((notch + 12, 4)), screenshot("xprunning").getpixel((notch + 12, 4)), 12),
    ) == ([], True, True), bar.getpixel((notch + 12, 4))
