"""The real taskbar, laid out by Plasma (tests/plasma_session.py), against the originals' taskbars.

Each original's windows, Quick Launch entries and tray icons are recreated with solid 16px squares as
icons, so every icon's place is measured exactly; frames, separators, the tray box and the labels are
compared with the original's pixels at the original's positions. Positions are in the taskbar, which
is the bottom 28 rows of the 640x480 screen.
"""
import pytest

from conftest import needs_ui_font
from plasma_session import ICON_COLOUR, ICON_SIZE, SCREEN, missing_programs
from reference import close
from test_taskbar_reference import BUTTON_HEIGHT, BUTTON_TOP, BUTTONS, HEIGHT, TASKBARS, TRAYS, taskbar

pytestmark = [needs_ui_font, pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}")]

ICON_TOP = 7                                    # every icon's top row in the originals
TASK_ICON_LEFT = 4                              # from a task button's left edge; a row lower while pressed
QUICK_LAUNCH = {"1998": [72, 95, 118, 141], "2000": [74, 97, 120]}   # the icons' left columns: 23px cells
ETCHED_LINES = {"1998": [58, 165], "2000": [60, 144]}               # the separators' etched lines
TRAY_ICONS = {"1995": [560], "1998": [543, 560], "2000": [548]}
LABEL_FROM = 20                                 # labels start right of this, from the task button's left edge


@pytest.fixture(scope="module")
def ours(desktops):
    """Our taskbar for a look: the bottom rows of its desktop."""
    return lambda look: desktops(look).crop((0, SCREEN[1] - HEIGHT, SCREEN[0], SCREEN[1]))


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


@pytest.mark.parametrize("look", TASKBARS)
def test_start_button_is_where_the_originals_is(ours, look):
    """Its bevel and the face around it; the logo and lettering are test_taskbar_reference.py's."""
    original, mine = taskbar(look), ours(look)
    (left, right), _ = BUTTONS[look]
    columns, rows = range(left - 1, right + 2), range(BUTTON_TOP - 1, BUTTON_TOP + BUTTON_HEIGHT + 1)
    edges = [(x, y) for x in columns for y in rows if x in columns[:3] or x in columns[-3:] or y in rows[:3] or y in rows[-3:]]
    assert [point for point in edges if not close(mine.getpixel(point), original.getpixel(point))] == []


@pytest.mark.parametrize("look", QUICK_LAUNCH)
def test_quick_launch_icons_sit_in_the_originals_cells(ours, look):
    first, last = QUICK_LAUNCH[look][0] - 8, QUICK_LAUNCH[look][-1] + ICON_SIZE + 8
    assert squares(ours(look), first, last) == [icon_box(left) for left in QUICK_LAUNCH[look]]


def test_1995_has_no_quick_launch(ours):
    (_, start_right), tasks = BUTTONS["1995"]
    assert squares(ours("1995"), start_right + 1, tasks[0][0]) == []


@pytest.mark.parametrize("look", ETCHED_LINES)
def test_separators_are_where_the_originals_are(ours, look):
    original, mine = taskbar(look), ours(look)
    for x in ETCHED_LINES[look]:
        assert all(close(mine.getpixel((x + dx, 12)), original.getpixel((x + dx, 12))) for dx in (-1, 0, 1, 2)), x


@pytest.mark.parametrize("look", TASKBARS)
def test_task_buttons_have_the_originals_edges_and_gaps(ours, look):
    """Every task button's outline and the 3px gaps between them, pixel for pixel."""
    original, mine = taskbar(look), ours(look)
    for left, right, _pressed in BUTTONS[look][1]:
        outline = [(x, y) for x in range(left - 1, right + 2) for y in range(BUTTON_TOP - 1, BUTTON_TOP + BUTTON_HEIGHT + 1)
                   if x in (left - 1, left, left + 1, right - 1, right, right + 1) or y in (BUTTON_TOP, BUTTON_TOP + BUTTON_HEIGHT - 1)]
        differing = [point for point in outline if not close(mine.getpixel(point), original.getpixel(point))]
        assert differing == [], f"button at {left}"


@pytest.mark.parametrize("look", TASKBARS)
def test_task_button_icons_sit_where_the_originals_do(ours, look):
    expected = [icon_box(left + TASK_ICON_LEFT, ICON_TOP + pressed) for left, _right, pressed in BUTTONS[look][1]]
    first, last = BUTTONS[look][1][0][0], BUTTONS[look][1][-1][1]
    assert squares(ours(look), first, last + 1) == expected


# The originals' font leaves a blank column before most capitals but not before W; ours starts every
# glyph at its origin and the labels a pixel further in, so these titles start a pixel right of the original's.
WITHOUT_LEADING_BLANK = {("1995", 256), ("1998", 176)}   # "Windows", "WinPopup"


@pytest.mark.parametrize("look", TASKBARS)
def test_task_labels_start_and_sit_where_the_originals_do(ours, look):
    """The first stroke's column and the lettering's rows; 2000's titles are Tahoma, whose capitals are
    a row shorter than the UI font's: there only the baseline row is compared."""
    original, mine = taskbar(look), ours(look)
    for left, right, _pressed in BUTTONS[look][1]:
        theirs, our = ink(original, left + LABEL_FROM, right - 2), ink(mine, left + LABEL_FROM, right - 2)
        first = theirs[0] + ((look, left) in WITHOUT_LEADING_BLANK)
        top = theirs[1] if look != "2000" else our and our[1]
        assert our is not None and (our[0], our[1], our[3]) == (first, top, theirs[3]), (left, our, theirs)


@pytest.mark.parametrize("look", TASKBARS)
def test_active_task_label_is_bold(ours, look):
    """Bold strokes are two pixels wide: the active label has as much ink per column as the original's."""
    original, mine = taskbar(look), ours(look)

    def ink_per_column(image, left, right):
        box = ink(image, left + LABEL_FROM, right - 2)
        dark = sum(1 for x in range(box[0], box[2] + 1) for y in range(box[1], box[3] + 1) if sum(image.getpixel((x, y))) < 150)
        return dark / (box[2] - box[0] + 1)
    for left, right, pressed in BUTTONS[look][1]:
        assert abs(ink_per_column(mine, left, right) - ink_per_column(original, left, right)) < 1.0, (left, pressed)


@pytest.mark.parametrize("look", TASKBARS)
def test_tray_box_has_the_originals_edges(ours, look):
    original, mine = taskbar(look), ours(look)
    left, right = TRAYS[look]
    edges = [(x, y) for x in range(left - 1, right + 2) for y in range(BUTTON_TOP - 1, BUTTON_TOP + BUTTON_HEIGHT + 1)
             if x in (left - 1, left, right, right + 1) or y in (BUTTON_TOP - 1, BUTTON_TOP, BUTTON_TOP + BUTTON_HEIGHT - 1, BUTTON_TOP + BUTTON_HEIGHT)]
    differing = [point for point in edges if not close(mine.getpixel(point), original.getpixel(point))]
    assert differing == []


@pytest.mark.parametrize("look", TASKBARS)
def test_tray_icons_sit_where_the_originals_do(ours, look):
    left, right = TRAYS[look]
    assert squares(ours(look), left, right) == [icon_box(x) for x in TRAY_ICONS[look]]


@pytest.mark.parametrize("look", TASKBARS)
def test_clock_is_black_and_centred_on_the_originals_rows(ours, look):
    """The time differs; its lettering's rows, colour and centre do not. 2000's clock is Tahoma, whose
    digits are a row shorter than the UI font's: there only the baseline row is compared."""
    original, mine = taskbar(look), ours(look)
    left, right = TRAYS[look]
    start = TRAY_ICONS[look][-1] + ICON_SIZE + 1
    theirs, our = ink(original, start, right), ink(mine, start, right)
    rows = (lambda box: box[3]) if look == "2000" else (lambda box: (box[1], box[3]))
    assert our is not None and rows(our) == rows(theirs), (our, theirs)
    assert abs((our[0] + our[2]) - (theirs[0] + theirs[2])) <= 2, (our, theirs)   # centres within a pixel
    dark = {mine.getpixel((x, y)) for x in range(our[0], our[2] + 1) for y in range(our[1], our[3] + 1) if sum(mine.getpixel((x, y))) < 150}
    assert dark == {(0, 0, 0)}


def widest_blank(image, box):
    """The widest run of empty columns inside the lettering's box: the space before AM or PM."""
    runs, run = [], 0
    for x in range(box[0], box[2] + 1):
        empty = all(sum(image.getpixel((x, y))) >= 150 for y in range(box[1], box[3] + 1))
        run = run + 1 if empty else 0
        runs.append(run)
    return max(runs)


@pytest.mark.parametrize("look", TASKBARS)
def test_clock_has_a_full_space_before_am_and_pm(ours, look):
    original, mine = taskbar(look), ours(look)
    left, right = TRAYS[look]
    start = TRAY_ICONS[look][-1] + ICON_SIZE + 1
    assert widest_blank(mine, ink(mine, start, right)) == widest_blank(original, ink(original, start, right))
