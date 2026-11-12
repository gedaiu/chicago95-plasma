"""Where the Quick Launch band and the window buttons go, and what dragging its separators does (quickLaunchBand.js).

The band sits between its two separators. The one at the docked edge (the left one beside Start, the right one
before the tray) carries the whole band while dragged and docks it by the half of the taskbar it is let go in. The
one facing the window buttons sizes the band in pixels: room left over stays empty, and launchers that do not fit
go behind a chevron at the band's far end from its dock (docked right, the first launchers are the hidden ones).

Sizes come from the library's own metrics, so the QML, the library and these tests share one set of numbers.
"""

import pytest
from conftest import REPO
from js_library import call, load_js_library

TASKBAR_WIDTH, CONTENT_X = 600, -4
LAUNCHERS = 4
HALFWAY = TASKBAR_WIDTH // 2
FIT = -1  # as the band's size: as wide as all its launchers
NOT_SET = -1  # no chevron or separator here


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


def layout(band, lead, dock="left", count=LAUNCHERS, size=FIT):
    return call(band, "layout", TASKBAR_WIDTH, CONTENT_X, lead, count, size, dock)


def test_docked_left_and_fitting_its_launchers_the_band_follows_start(band, lead, metrics, separator, cells_width):
    band_x = CONTENT_X + separator(lead)
    right_separator_x = band_x + cells_width(LAUNCHERS) + metrics["gapBeforeRightSeparator"]

    assert layout(band, lead) == {
        "leftSeparatorX": CONTENT_X,
        "cellsX": band_x,
        "shown": LAUNCHERS,
        "firstShown": 0,
        "chevronX": NOT_SET,
        "rightSeparatorX": right_separator_x,
        "tasksX": right_separator_x + separator(lead),
        "tasksEnd": TASKBAR_WIDTH,
    }


def test_docked_left_a_band_wider_than_its_launchers_leaves_the_rest_empty(band, lead, metrics, separator, cells_width):
    band_x = CONTENT_X + separator(lead)
    size = cells_width(LAUNCHERS) + 40
    shape = layout(band, lead, size=size)

    assert (shape["shown"], shape["chevronX"], shape["rightSeparatorX"]) == (
        LAUNCHERS,
        NOT_SET,
        band_x + size + metrics["gapBeforeRightSeparator"],
    )


def test_docked_left_a_band_too_narrow_shows_what_fits_and_ends_with_the_chevron(
    band, lead, metrics, separator, cells_width
):
    band_x = CONTENT_X + separator(lead)
    size = metrics["chevronWidth"] + cells_width(2) + 10
    right_separator_x = band_x + size + metrics["gapBeforeRightSeparator"]

    assert layout(band, lead, size=size) == {
        "leftSeparatorX": CONTENT_X,
        "cellsX": band_x,
        "shown": 2,
        "firstShown": 0,
        "chevronX": band_x + size - metrics["chevronWidth"],
        "rightSeparatorX": right_separator_x,
        "tasksX": right_separator_x + separator(lead),
        "tasksEnd": TASKBAR_WIDTH,
    }


def test_docked_right_the_window_buttons_follow_start_and_the_band_ends_the_taskbar(
    band, lead, metrics, separator, cells_width
):
    right_separator_x = TASKBAR_WIDTH - separator(lead)
    band_x = right_separator_x - metrics["gapBeforeRightSeparator"] - cells_width(LAUNCHERS)
    left_separator_x = band_x - separator(lead)

    assert layout(band, lead, dock="right") == {
        "leftSeparatorX": left_separator_x,
        "cellsX": band_x,
        "shown": LAUNCHERS,
        "firstShown": 0,
        "chevronX": NOT_SET,
        "rightSeparatorX": right_separator_x,
        "tasksX": CONTENT_X + metrics["gapWithoutQuickLaunch"],
        "tasksEnd": left_separator_x,
    }


def test_docked_right_a_band_too_narrow_leads_with_the_chevron_and_shows_the_last_launchers(
    band, lead, metrics, separator, cells_width
):
    size = metrics["chevronWidth"] + cells_width(3)
    right_separator_x = TASKBAR_WIDTH - separator(lead)
    band_x = right_separator_x - metrics["gapBeforeRightSeparator"] - size
    left_separator_x = band_x - separator(lead)

    assert layout(band, lead, dock="right", size=size) == {
        "leftSeparatorX": left_separator_x,
        "cellsX": band_x + metrics["chevronWidth"],
        "shown": 3,
        "firstShown": 1,
        "chevronX": band_x,
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


@pytest.mark.parametrize(
    "grip_x, docked", [(HALFWAY - 1, "left"), (HALFWAY, "right"), (-50, "left"), (TASKBAR_WIDTH + 50, "right")]
)
def test_letting_go_of_the_docked_edges_separator_docks_the_band_by_the_half_it_is_in(band, grip_x, docked):
    assert call(band, "dockAfterDrag", grip_x, TASKBAR_WIDTH) == docked


@pytest.mark.parametrize("dock, outer", [("left", "leftSeparatorX"), ("right", "rightSeparatorX")])
def test_the_docked_edges_separator_is_the_one_that_carries_the_band(band, dock, outer):
    assert call(band, "outerSeparator", dock) == outer


def size_after_drag(band, lead, grip_x, dock):
    return call(band, "sizeAfterDrag", grip_x, TASKBAR_WIDTH, CONTENT_X, lead, dock)


def test_dragging_the_inner_separator_docked_left_sizes_the_band_to_reach_it(band, lead, metrics, separator):
    band_x = CONTENT_X + separator(lead)
    assert size_after_drag(band, lead, band_x + 150 + metrics["gapBeforeRightSeparator"], "left") == 150


def test_dragging_the_inner_separator_docked_right_sizes_the_band_from_it_to_the_end(band, lead, metrics, separator):
    band_end = TASKBAR_WIDTH - separator(lead) - metrics["gapBeforeRightSeparator"]
    assert size_after_drag(band, lead, band_end - 150 - separator(lead), "right") == 150


@pytest.mark.parametrize("grip_x, limit", [(-500, "chevron"), (TASKBAR_WIDTH * 2, "half the taskbar")])
def test_the_band_is_never_narrower_than_its_chevron_nor_wider_than_half_the_taskbar(
    band, lead, metrics, grip_x, limit
):
    expected = {"chevron": metrics["chevronWidth"], "half the taskbar": HALFWAY}[limit]
    assert size_after_drag(band, lead, grip_x, "left") == expected


def carried(band, lead, separator, grip_x, dock):
    """Where a carried band's left and right edges go, shifted from the docked layout."""
    shape = layout(band, lead, dock=dock)
    shift = call(band, "carriedShift", grip_x, shape, dock, TASKBAR_WIDTH, CONTENT_X)
    return (shape["leftSeparatorX"] + shift, shape["rightSeparatorX"] + separator(lead) + shift)


def test_a_band_carried_by_its_left_separator_follows_the_pointer(band, lead, separator):
    assert carried(band, lead, separator, 120, "left")[0] == 120


def test_a_band_carried_by_its_right_separator_follows_the_pointer(band, lead, separator, metrics):
    left, right = carried(band, lead, separator, 400, "right")
    assert right - separator(lead) == 400


@pytest.mark.parametrize("dock, grip_x", [("left", -300), ("left", TASKBAR_WIDTH + 300), ("right", -300)])
def test_a_carried_band_stays_on_the_taskbar(band, lead, separator, dock, grip_x):
    left, right = carried(band, lead, separator, grip_x, dock)
    assert (left >= CONTENT_X, right <= TASKBAR_WIDTH) == (True, True)


@pytest.mark.parametrize(
    "dock, size_cells, behind_chevron",
    [("left", None, []), ("left", 2, [2, 3]), ("left", 0, [0, 1, 2, 3]), ("right", 2, [0, 1]), ("right", 3, [0])],
)
def test_the_chevron_holds_the_launchers_on_its_side_of_the_shown_cells(
    band, metrics, cells_width, dock, size_cells, behind_chevron
):
    size = FIT if size_cells is None else metrics["chevronWidth"] + cells_width(size_cells)
    assert call(band, "chevronLaunchers", {"count": LAUNCHERS, "size": size, "dock": dock}) == behind_chevron


@pytest.mark.parametrize("unknown_size", [None, "", "wide"])
def test_a_band_size_the_widget_has_not_read_yet_fits_every_launcher(band, lead, unknown_size):
    """Right after Setup, Plasma can hand the widget a setting it has not loaded yet: the band still shows all."""
    assert layout(band, lead, size=unknown_size) == layout(band, lead)


def test_qml_gets_the_fit_every_launcher_size_from_the_library(band):
    assert call(band, "fitAll") == FIT


def test_luna_band_puts_the_grip_10px_before_the_cells_and_the_next_grip_6px_after_them(band):
    luna = call(band, "metrics", "luna")
    shape = call(band, "layout", TASKBAR_WIDTH, CONTENT_X, luna["separatorLead"], 3, FIT, "left", luna)
    first_grip, cells, second_grip, window_buttons = (
        shape["leftSeparatorX"] + luna["separatorLead"],
        shape["cellsX"],
        shape["rightSeparatorX"] + luna["separatorLead"],
        shape["tasksX"],
    )
    assert (first_grip, cells, second_grip, window_buttons) == (0, 10, 10 + 3 * 23 + 6, 10 + 3 * 23 + 6 + 10)
