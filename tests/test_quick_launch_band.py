"""Where the Quick Launch band and the window buttons go, and what dragging their separators does (quickLaunchBand.js).

The Quick Launch has its own separator on its left: dragging it docks the band beside the Start button or at the
taskbar's right end, by the half of the taskbar it is let go in. The window buttons' separator, on the band's right
when it is docked left, sets how many cells it shows; launchers that do not fit go behind a chevron at its right
end. Docked right, the band's own separator is the one beside the window buttons: let go in the right half it sets
the cells, in the left half it docks the band back beside the Start button.

Sizes come from the library's own metrics, so the QML, the library and these tests share one set of numbers.
"""

import pytest
from conftest import REPO
from js_library import call, load_js_library

TASKBAR_WIDTH, CONTENT_X = 600, -4
LAUNCHERS = 4
HALFWAY = TASKBAR_WIDTH // 2
NOT_SET = -1  # no chevron or separator; as cells, every launcher shows


@pytest.fixture(scope="module")
def band(qt_app):
    return load_js_library(REPO / "plasmoids/org.chicago95.tasks/contents/ui/quickLaunchBand.js")


@pytest.fixture(scope="module")
def metrics(band):
    return call(band, "metrics")


@pytest.fixture(scope="module")
def separator(band):
    return lambda lead: call(band, "separatorWidth", lead)


@pytest.fixture(scope="module")
def cells_width(band):
    return lambda count: call(band, "cellsWidth", count)


@pytest.fixture(scope="module")
def lead(metrics):
    return metrics["separatorLead"]


def layout(band, lead, dock="left", count=LAUNCHERS, cells=NOT_SET):
    return call(band, "layout", TASKBAR_WIDTH, CONTENT_X, lead, count, cells, dock)


def test_docked_left_with_every_launcher_shown_follows_the_start_button(band, lead, metrics, separator, cells_width):
    cells_x = CONTENT_X + separator(lead)
    task_grip_x = cells_x + cells_width(LAUNCHERS) + metrics["gapBeforeTaskSeparator"]

    assert layout(band, lead) == {
        "quickLaunchGripX": CONTENT_X,
        "cellsX": cells_x,
        "shown": LAUNCHERS,
        "firstShown": 0,
        "chevronX": NOT_SET,
        "taskGripX": task_grip_x,
        "tasksX": task_grip_x + separator(lead),
        "tasksEnd": TASKBAR_WIDTH,
    }


def test_docked_left_with_2_of_4_cells_puts_the_chevron_after_them(band, lead, metrics, separator, cells_width):
    cells_x = CONTENT_X + separator(lead)
    chevron_x = cells_x + cells_width(2)
    task_grip_x = chevron_x + metrics["chevronWidth"] + metrics["gapBeforeTaskSeparator"]

    assert layout(band, lead, cells=2) == {
        "quickLaunchGripX": CONTENT_X,
        "cellsX": cells_x,
        "shown": 2,
        "firstShown": 0,
        "chevronX": chevron_x,
        "taskGripX": task_grip_x,
        "tasksX": task_grip_x + separator(lead),
        "tasksEnd": TASKBAR_WIDTH,
    }


def test_docked_right_puts_the_window_buttons_after_start_and_the_band_at_the_end(band, lead, separator, cells_width):
    cells_x = TASKBAR_WIDTH - cells_width(LAUNCHERS)
    grip_x = cells_x - separator(lead)

    assert layout(band, lead, dock="right") == {
        "quickLaunchGripX": grip_x,
        "cellsX": cells_x,
        "shown": LAUNCHERS,
        "firstShown": 0,
        "chevronX": NOT_SET,
        "taskGripX": CONTENT_X,
        "tasksX": CONTENT_X + separator(lead),
        "tasksEnd": grip_x,
    }


def test_docked_right_with_3_of_4_cells_leads_with_the_chevron_and_shows_the_last_3(
    band, lead, metrics, separator, cells_width
):
    cells_x = TASKBAR_WIDTH - cells_width(3)
    chevron_x = cells_x - metrics["chevronWidth"]
    grip_x = chevron_x - separator(lead)

    assert layout(band, lead, dock="right", cells=3) == {
        "quickLaunchGripX": grip_x,
        "cellsX": cells_x,
        "shown": 3,
        "firstShown": 1,
        "chevronX": chevron_x,
        "taskGripX": CONTENT_X,
        "tasksX": CONTENT_X + separator(lead),
        "tasksEnd": grip_x,
    }


def test_without_launchers_the_window_buttons_start_after_the_start_button(band, lead, metrics):
    assert layout(band, lead, count=0) == {
        "quickLaunchGripX": NOT_SET,
        "cellsX": NOT_SET,
        "shown": 0,
        "firstShown": 0,
        "chevronX": NOT_SET,
        "taskGripX": NOT_SET,
        "tasksX": CONTENT_X + metrics["gapWithoutQuickLaunch"],
        "tasksEnd": TASKBAR_WIDTH,
    }


@pytest.mark.parametrize("cells, shown", [(0, 0), (9, LAUNCHERS), (NOT_SET, LAUNCHERS)])
def test_cells_beyond_the_launchers_show_them_all_and_zero_shows_only_the_chevron(band, lead, cells, shown):
    assert layout(band, lead, cells=cells)["shown"] == shown


def quick_launch_grip_released(band, lead, grip_x, dock, cells=2):
    return call(band, "quickLaunchGripReleased", grip_x, TASKBAR_WIDTH, CONTENT_X, lead, LAUNCHERS, cells, dock)


@pytest.mark.parametrize(
    "dock, grip_x, docked",
    [
        ("left", HALFWAY + 1, "right"),
        ("left", HALFWAY - 1, "left"),
        ("left", -50, "left"),
        ("right", HALFWAY - 1, "left"),
    ],
)
def test_letting_go_of_the_quick_launch_separator_docks_the_band_by_the_half_it_is_in(band, lead, dock, grip_x, docked):
    assert quick_launch_grip_released(band, lead, grip_x, dock) == {"dock": docked, "cells": 2}


@pytest.mark.parametrize("fitting, expected_cells", [(3, 3), (LAUNCHERS, NOT_SET)])
def test_letting_go_of_the_quick_launch_separator_docked_right_sizes_the_band(
    band, lead, metrics, separator, cells_width, fitting, expected_cells
):
    chevron = metrics["chevronWidth"] if fitting < LAUNCHERS else 0
    grip_x = TASKBAR_WIDTH - chevron - cells_width(fitting) - separator(lead)

    assert quick_launch_grip_released(band, lead, grip_x, "right") == {"dock": "right", "cells": expected_cells}


def test_the_quick_launch_separator_let_go_beyond_the_right_end_leaves_only_the_chevron(band, lead):
    assert quick_launch_grip_released(band, lead, TASKBAR_WIDTH + 50, "right") == {"dock": "right", "cells": 0}


def task_grip_released(band, lead, grip_x, dock="left"):
    return call(band, "taskGripReleased", grip_x, TASKBAR_WIDTH, CONTENT_X, lead, LAUNCHERS, 2, dock)


@pytest.mark.parametrize("fitting, expected_cells", [(1, 1), (3, 3), (LAUNCHERS, NOT_SET), (9, NOT_SET), (0, 0)])
def test_letting_go_of_the_window_buttons_separator_docked_left_sets_the_cells(
    band, lead, metrics, separator, cells_width, fitting, expected_cells
):
    chevron = metrics["chevronWidth"] if 0 < fitting < LAUNCHERS else 0
    grip_x = CONTENT_X + separator(lead) + cells_width(fitting) + chevron + metrics["gapBeforeTaskSeparator"]

    assert task_grip_released(band, lead, grip_x) == {"dock": "left", "cells": expected_cells}


def test_the_window_buttons_separator_docked_right_changes_nothing(band, lead):
    assert task_grip_released(band, lead, HALFWAY, dock="right") == {"dock": "right", "cells": 2}


@pytest.mark.parametrize(
    "dock, cells, hidden",
    [("left", NOT_SET, []), ("left", 2, [2, 3]), ("left", 0, [0, 1, 2, 3]), ("right", 2, [0, 1]), ("right", 3, [0])],
)
def test_the_chevron_holds_the_launchers_on_its_side_of_the_shown_cells(band, dock, cells, hidden):
    assert call(band, "hiddenLaunchers", LAUNCHERS, cells, dock) == hidden
