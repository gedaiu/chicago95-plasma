"""The Quick Launch docked at the taskbar's right end, two of its four launchers shown, in a real Plasma session
(tests/plasma_session.py), measured against the layout quickLaunchBand.js gives and the docked-left originals.

Docked right, the window buttons follow the Start button with no separator between them, and the band ends the
taskbar between its two separators: the left one, the chevron, the shown launchers' cells, then the right one.
"""

import pytest
from conftest import REPO, needs_ui_font
from js_library import call, load_js_library
from PIL import Image
from plasma_session import ICON_SIZE, SCREEN, missing_programs
from test_plasma_taskbar_reference import ETCHED_LINES, ICON_TOP, TASK_ICON_LEFT, icon_box, squares
from test_taskbar_reference import HEIGHT, TRAYS

pytestmark = [
    needs_ui_font,
    pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}"),
]

LOOK = "1998"
SHOWN = 2
ETCHED_ROW = 12  # a taskbar row the separators' etched lines cross, clear of their grips' ends
CHEVRON_ART = REPO / "data/icons/tray-chevron.png"


@pytest.fixture(scope="module")
def band(qt_app):
    return load_js_library(REPO / "plasmoids/org.chicago95.tasks/contents/ui/quickLaunchBand.js")


@pytest.fixture(scope="module")
def metrics(band):
    return call(band, "metrics")


@pytest.fixture(scope="module")
def taskbar(desktops):
    screen = desktops(LOOK, tasks_config=(("quickLaunchDock", "right"), ("quickLaunchCells", SHOWN)))
    return screen.crop((0, SCREEN[1] - HEIGHT, SCREEN[0], SCREEN[1]))


def etched_lines(image):
    """Columns where a separator's etched line (shadow, then white) runs down the taskbar's middle row."""
    return [
        x
        for x in range(image.width - 1)
        if image.getpixel((x, ETCHED_ROW)) == (128, 128, 128) and image.getpixel((x + 1, ETCHED_ROW)) == (255, 255, 255)
    ]


def chevron_columns():
    """The chevron art's dark columns: docked right it points left, as the art does."""
    art = Image.open(CHEVRON_ART).convert("RGBA")
    return sorted({x for x in range(art.width) for y in range(art.height) if art.getpixel((x, y))[3] > 128})


def separator_left(line, metrics):
    """A separator's left edge from its etched line."""
    return line - metrics["separatorLead"]


def test_no_separator_sits_beside_start_and_the_window_buttons_follow_it(taskbar, band, metrics):
    content_x = ETCHED_LINES[LOOK][0] - metrics["separatorLead"]  # where the docked-left band's separator starts
    tasks_x = content_x + metrics["gapWithoutQuickLaunch"]
    first_task_icon = squares(taskbar, tasks_x, tasks_x + 2 * TASK_ICON_LEFT + ICON_SIZE)[0]

    assert (len(etched_lines(taskbar)), first_task_icon[0]) == (2, tasks_x + TASK_ICON_LEFT)


def test_the_chevron_leads_the_band_right_after_its_left_separator_pointing_left(taskbar, band, metrics):
    left_line = etched_lines(taskbar)[0]
    chevron_x = separator_left(left_line, metrics) + call(band, "separatorWidth", metrics["separatorLead"])
    dark = {
        x
        for x in range(chevron_x, chevron_x + metrics["chevronWidth"])
        for y in range(HEIGHT)
        if taskbar.getpixel((x, y)) == (0, 0, 0)
    }

    assert sorted(dark) == [chevron_x + column for column in chevron_columns()]


def test_only_the_shown_launchers_sit_between_the_chevron_and_the_right_separator(taskbar, band, metrics):
    left_line, right_line = etched_lines(taskbar)
    separator = call(band, "separatorWidth", metrics["separatorLead"])
    cells_x = separator_left(left_line, metrics) + separator + metrics["chevronWidth"]
    cells_end = cells_x + call(band, "cellsWidth", SHOWN)

    assert (
        squares(taskbar, cells_x, cells_end),
        separator_left(right_line, metrics) - cells_end,
        separator_left(right_line, metrics) + separator <= TRAYS[LOOK][0],
    ) == (
        [
            icon_box(cells_x + metrics["iconInset"] + call(band, "cellsWidth", index), ICON_TOP)
            for index in range(SHOWN)
        ],
        metrics["gapBeforeRightSeparator"],
        True,
    )
