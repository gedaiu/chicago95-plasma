"""Where the Quick Launch band and the window buttons go, and what dragging its separators does (quickLaunchBand.js).

The band always sits between its two separators. Dragging the left one docks the band beside the Start button or at
the taskbar's right end, by the half of the taskbar it is let go in. Dragging the right one sets how many cells the
band shows; launchers that do not fit go behind a chevron at the band's far end from where it is docked: last
docked left, first docked right (where the first launchers are the hidden ones).

Sizes come from the library's own metrics, so the QML, the library and these tests share one set of numbers.
"""

import pytest
from conftest import REPO
from js_library import call, load_js_library

TASKBAR_WIDTH, CONTENT_X = 600, -4
LAUNCHERS = 4
HALFWAY = TASKBAR_WIDTH // 2
NOT_SET = -1  # no chevron or separator; as cells, every launcher shows
SHOWN_BEFORE_DRAG = 2


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
    right_separator_x = cells_x + cells_width(LAUNCHERS) + metrics["gapBeforeRightSeparator"]

    assert layout(band, lead) == {
        "leftSeparatorX": CONTENT_X,
        "cellsX": cells_x,
        "shown": LAUNCHERS,
        "firstShown": 0,
        "chevronX": NOT_SET,
        "rightSeparatorX": right_separator_x,
        "tasksX": right_separator_x + separator(lead),
        "tasksEnd": TASKBAR_WIDTH,
    }


def test_docked_left_with_2_of_4_cells_puts_the_chevron_after_them(band, lead, metrics, separator, cells_width):
    cells_x = CONTENT_X + separator(lead)
    chevron_x = cells_x + cells_width(2)
    right_separator_x = chevron_x + metrics["chevronWidth"] + metrics["gapBeforeRightSeparator"]

    assert layout(band, lead, cells=2) == {
        "leftSeparatorX": CONTENT_X,
        "cellsX": cells_x,
        "shown": 2,
        "firstShown": 0,
        "chevronX": chevron_x,
        "rightSeparatorX": right_separator_x,
        "tasksX": right_separator_x + separator(lead),
        "tasksEnd": TASKBAR_WIDTH,
    }


def test_docked_right_the_window_buttons_follow_start_and_the_band_ends_the_taskbar(
    band, lead, metrics, separator, cells_width
):
    right_separator_x = TASKBAR_WIDTH - separator(lead)
    cells_x = right_separator_x - metrics["gapBeforeRightSeparator"] - cells_width(LAUNCHERS)
    left_separator_x = cells_x - separator(lead)

    assert layout(band, lead, dock="right") == {
        "leftSeparatorX": left_separator_x,
        "cellsX": cells_x,
        "shown": LAUNCHERS,
        "firstShown": 0,
        "chevronX": NOT_SET,
        "rightSeparatorX": right_separator_x,
        "tasksX": CONTENT_X + metrics["gapWithoutQuickLaunch"],
        "tasksEnd": left_separator_x,
    }


def test_docked_right_with_3_of_4_cells_leads_with_the_chevron_and_shows_the_last_3(
    band, lead, metrics, separator, cells_width
):
    right_separator_x = TASKBAR_WIDTH - separator(lead)
    cells_x = right_separator_x - metrics["gapBeforeRightSeparator"] - cells_width(3)
    chevron_x = cells_x - metrics["chevronWidth"]
    left_separator_x = chevron_x - separator(lead)

    assert layout(band, lead, dock="right", cells=3) == {
        "leftSeparatorX": left_separator_x,
        "cellsX": cells_x,
        "shown": 3,
        "firstShown": 1,
        "chevronX": chevron_x,
        "rightSeparatorX": right_separator_x,
        "tasksX": CONTENT_X + metrics["gapWithoutQuickLaunch"],
        "tasksEnd": left_separator_x,
    }


def test_without_launchers_the_window_buttons_start_after_the_start_button(band, lead, metrics):
    assert layout(band, lead, count=0) == {
        "leftSeparatorX": NOT_SET,
        "cellsX": NOT_SET,
        "shown": 0,
        "firstShown": 0,
        "chevronX": NOT_SET,
        "rightSeparatorX": NOT_SET,
        "tasksX": CONTENT_X + metrics["gapWithoutQuickLaunch"],
        "tasksEnd": TASKBAR_WIDTH,
    }


@pytest.mark.parametrize("cells, shown", [(0, 0), (9, LAUNCHERS), (NOT_SET, LAUNCHERS)])
def test_cells_beyond_the_launchers_show_them_all_and_zero_shows_only_the_chevron(band, lead, cells, shown):
    assert layout(band, lead, cells=cells)["shown"] == shown


def released(band, lead, which, grip_x, dock):
    return call(
        band, f"{which}SeparatorReleased", grip_x, TASKBAR_WIDTH, CONTENT_X, lead, LAUNCHERS, SHOWN_BEFORE_DRAG, dock
    )


@pytest.mark.parametrize(
    "dock, grip_x, docked",
    [
        ("left", HALFWAY + 1, "right"),
        ("left", HALFWAY - 1, "left"),
        ("left", -50, "left"),
        ("right", HALFWAY - 1, "left"),
        ("right", HALFWAY + 1, "right"),
    ],
)
def test_letting_go_of_the_left_separator_docks_the_band_by_the_half_it_is_in(band, lead, dock, grip_x, docked):
    assert released(band, lead, "left", grip_x, dock) == {"dock": docked, "cells": SHOWN_BEFORE_DRAG}


@pytest.mark.parametrize("fitting, expected_cells", [(1, 1), (3, 3), (LAUNCHERS, NOT_SET), (9, NOT_SET), (0, 0)])
def test_letting_go_of_the_right_separator_docked_left_sets_the_cells(
    band, lead, metrics, separator, cells_width, fitting, expected_cells
):
    chevron = metrics["chevronWidth"] if 0 < fitting < LAUNCHERS else 0
    grip_x = CONTENT_X + separator(lead) + cells_width(fitting) + chevron + metrics["gapBeforeRightSeparator"]

    assert released(band, lead, "right", grip_x, "left") == {"dock": "left", "cells": expected_cells}


@pytest.mark.parametrize(
    "cells_moved, expected_cells", [(-1, SHOWN_BEFORE_DRAG - 1), (0, SHOWN_BEFORE_DRAG), (2, NOT_SET), (-9, 0)]
)
def test_dragging_the_right_separator_docked_right_grows_or_shrinks_the_band_by_as_much(
    band, lead, separator, cells_width, cells_moved, expected_cells
):
    grip_x = TASKBAR_WIDTH - separator(lead) + cells_width(cells_moved)

    assert released(band, lead, "right", grip_x, "right") == {"dock": "right", "cells": expected_cells}


@pytest.mark.parametrize(
    "dock, cells, behind_chevron",
    [("left", NOT_SET, []), ("left", 2, [2, 3]), ("left", 0, [0, 1, 2, 3]), ("right", 2, [0, 1]), ("right", 3, [0])],
)
def test_the_chevron_holds_the_launchers_on_its_side_of_the_shown_cells(band, dock, cells, behind_chevron):
    assert call(band, "chevronLaunchers", LAUNCHERS, cells, dock) == behind_chevron
