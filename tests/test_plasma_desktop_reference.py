"""The desktop icons as Plasma's Folder View draws them (tests/plasma_session.py), against the originals'
empty desktops (tests/references/win95emptydesktop.png, win98emptydesktop.png).

The originals' icons are measured in the teal left column: 32px icons down the left edge, each label in
white a few rows under its icon. Folder View draws the same icons with the same label gap, but its cell is
taller (the label area is two of Plasma's grid units) and starts a few pixels further in; those are allowed for.
"""

import pytest
from conftest import needs_ui_font
from plasma_session import missing_programs
from reference import screenshot

pytestmark = [
    needs_ui_font,
    pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}"),
]

TEAL = (0, 128, 128)
COLUMN = 120  # the icon column's right edge in both pictures
ABOVE_TASKBAR = 450
ICON_INDENT = 18  # icons start right of this; labels, wider, start further left
ICON_LEFT = 21  # the originals' icon column
LABEL_OFFSETS = range(
    32, 39
)  # a label's top row from its icon's top: 36 to 38 in the originals; Folder View centres a short icon
FOLDER_VIEW_INSET = (3, 6)  # Folder View starts its grid this much right and down of the originals' first icon
FOLDER_VIEW_PITCH = (
    90  # Folder View's row pitch (32px icon, two grid units of label, three small spacings); the originals' is 75
)
ICON_COUNT = {"1995": 3, "1998": 4}  # My Computer, Network Neighborhood, Recycle Bin; 98 adds My Documents


def unlike_teal(colour):
    return max(abs(a - b) for a, b in zip(colour, TEAL, strict=False)) > 60


def runs(image):
    """(top, bottom, left, right) of each run of rows with pixels unlike the teal in the icon column."""
    found = []
    for y in range(ABOVE_TASKBAR):
        xs = [x for x in range(COLUMN) if unlike_teal(image.getpixel((x, y)))]
        if not xs:
            continue
        if found and y - found[-1][1] <= 1:
            top, _bottom, left, right = found[-1]
            found[-1] = (top, y, min(left, xs[0]), max(right, xs[-1]))
        else:
            found.append((y, y, xs[0], xs[-1]))
    return found


def icons(image):
    """Each icon's (top, left, label top): the tall runs at the icon indent, each followed by its label's run."""
    found = runs(image)
    return [
        (top, left, found[index + 1][0])
        for index, (top, bottom, left, _right) in enumerate(found[:-1])
        if bottom - top + 1 >= 20 and left >= ICON_INDENT
    ]


@pytest.fixture(scope="module")
def ours(desktops):
    return lambda look: desktops(look, components=["background", "desktop"], windows=[])


@pytest.mark.parametrize("look, original", [("1995", "win95emptydesktop"), ("1998", "win98emptydesktop")])
def test_icons_line_up_down_the_left_with_their_labels_under_them_like_the_originals(ours, look, original):
    theirs, mine = icons(screenshot(original)), icons(ours(look))

    assert (
        len(mine),
        {left for _top, left, _label in mine},
        [label - top in LABEL_OFFSETS for top, _left, label in theirs + mine],
        mine[0][0] - theirs[0][0],
        {later[2] - earlier[2] for earlier, later in zip(mine, mine[1:], strict=False)},
    ) == (
        ICON_COUNT[look],
        {ICON_LEFT + FOLDER_VIEW_INSET[0]},
        [True] * (len(theirs) + len(mine)),
        FOLDER_VIEW_INSET[1],
        {FOLDER_VIEW_PITCH},
    ), (theirs, mine)


BACKGROUNDS = {"2001": (0x3A, 0x6E, 0xA5), "luna": (0x00, 0x4E, 0x98)}  # XP Classic's blue, Luna's
OPEN_DESKTOP = ((400, 100), (700, 300), (300, 500))  # right of the icon column, above the taskbar

@pytest.mark.parametrize(
    "look, colour",
    [
        pytest.param("2001", BACKGROUNDS["2001"]),
        pytest.param("luna", BACKGROUNDS["luna"]),
    ],
)
def test_desktop_is_the_looks_solid_colour_wherever_no_icon_is(ours, look, colour):
    assert [ours(look).getpixel(point) for point in OPEN_DESKTOP] == [colour] * len(OPEN_DESKTOP)
