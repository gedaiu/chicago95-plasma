import pytest
from conftest import REPO
from js_library import call, load_js_library

QUICK_LAUNCH_X = 10
TASKBAR_WIDTH, TASKBAR_HEIGHT = 600, 28
FOUR_LAUNCHERS = 4


@pytest.fixture(scope="module")
def launchers(qt_app):
    return load_js_library(REPO / "plasmoids/org.chicago95.tasks/contents/ui/launchers.js")


@pytest.mark.parametrize(
    "x, count, expected",
    [
        (QUICK_LAUNCH_X + 0, FOUR_LAUNCHERS, 0),
        (QUICK_LAUNCH_X + 11, FOUR_LAUNCHERS, 0),
        (QUICK_LAUNCH_X + 12, FOUR_LAUNCHERS, 1),
        (QUICK_LAUNCH_X + 23 * 2, FOUR_LAUNCHERS, 2),
        (QUICK_LAUNCH_X - 40, FOUR_LAUNCHERS, 0),
        (QUICK_LAUNCH_X + 500, FOUR_LAUNCHERS, 4),
        (QUICK_LAUNCH_X + 5, 0, 0),
    ],
)
def test_insertion_index_is_the_nearest_gap_between_23px_cells(launchers, x, count, expected):
    assert call(launchers, "insertionIndexAt", x, QUICK_LAUNCH_X, count) == expected


@pytest.mark.parametrize(
    "x, y", [(QUICK_LAUNCH_X + 30, -30), (QUICK_LAUNCH_X + 30, TASKBAR_HEIGHT + 30), (TASKBAR_WIDTH + 40, 10)]
)
def test_releasing_a_launcher_well_outside_the_taskbar_removes_it(launchers, x, y):
    assert call(launchers, "releasedOffTaskbar", x, y, TASKBAR_WIDTH, TASKBAR_HEIGHT) is True


@pytest.mark.parametrize("x, y", [(QUICK_LAUNCH_X + 23 * 2, -5), (TASKBAR_WIDTH + 12, 10), (QUICK_LAUNCH_X, 10)])
def test_releasing_a_launcher_on_or_a_little_outside_the_taskbar_keeps_it(launchers, x, y):
    assert call(launchers, "releasedOffTaskbar", x, y, TASKBAR_WIDTH, TASKBAR_HEIGHT) is False


def test_tasks_applet_wires_dropping_and_sorting_to_the_libraries():
    main_qml = (REPO / "plasmoids/org.chicago95.tasks/contents/ui/main.qml").read_text()

    assert (
        'import "launchers.js" as Launchers' in main_qml,
        "Launchers.releasedOffTaskbar(" in main_qml,
        "Launchers.insertionIndexAt(" in main_qml,
        "tasksModel.move(" in main_qml,
        "Launchers.dragResult(" in main_qml,
    ) == (True, True, True, True, False)


def qml_block(text, opening):
    start = text.index(opening)
    depth = 0
    for position in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[position], 0)
        if depth == 0 and text[position] == "}":
            return text[start : position + 1]


def test_quick_launch_cells_show_the_programs_name_and_icon_as_a_tooltip():
    main_qml = (REPO / "plasmoids/org.chicago95.tasks/contents/ui/main.qml").read_text()
    launcher_cell = qml_block(main_qml, "id: launcherCell")

    tooltip = qml_block(launcher_cell, "PlasmaCore.ToolTipArea {")

    assert ("mainText: entry.model.display" in tooltip, "icon: entry.model.decoration" in tooltip) == (True, True)


def test_quick_launch_cells_hover_reaches_the_tooltip_through_the_click_area_inside_it():
    main_qml = (REPO / "plasmoids/org.chicago95.tasks/contents/ui/main.qml").read_text()
    tooltip = qml_block(qml_block(main_qml, "id: launcherCell"), "PlasmaCore.ToolTipArea {")

    assert "id: launcherArea" in tooltip


def main_qml():
    return (REPO / "plasmoids/org.chicago95.tasks/contents/ui/main.qml").read_text()


def test_quick_launch_cells_sort_by_dragging_inside_their_tooltip_area():
    tooltip = qml_block(qml_block(main_qml(), "id: launcherCell"), "PlasmaCore.ToolTipArea {")

    assert (
        "DragSortArea {" in tooltip,
        "id: launcherArea" in tooltip,
        "slot: entry.index - root.firstShown" in tooltip,
        "count: root.shownLaunchers" in tooltip,
        "tasksModel.move(root.firstShown + from, root.firstShown + to)" in tooltip,
        "Launchers.releasedOffTaskbar(" in tooltip,
        "requestRemoveLauncher(" in tooltip,
        "tasksModel.syncLaunchers()" in tooltip,
    ) == (True,) * 8


def test_window_buttons_sort_by_dragging_inside_their_own_section():
    button = qml_block(main_qml(), "id: windowButton")

    assert (
        "DragSortArea {" in button,
        "origin: root.tasksX" in button,
        "pitch: root.buttonWidth + root.gap" in button,
        "count: root.windowCount" in button,
        "slot: entry.index - root.launcherCount" in button,
        "tasksModel.move(root.launcherCount + from, root.launcherCount + to)" in button,
    ) == (True,) * 6


def test_a_dragged_button_follows_the_pointer_and_the_others_slide_aside_in_120_ms():
    entry = qml_block(main_qml(), "Loader {\n            id: entry")

    assert (
        "x: entry.dragging ? entry.dragX : entry.laidOutX" in entry,
        "z: entry.dragging ? 1 : 0" in entry,
        "Behavior on x {" in entry,
        "enabled: entry.slides" in entry,
        "duration: 120" in entry,
    ) == (True,) * 5


def test_the_old_drag_overlay_is_gone():
    text = main_qml()

    assert ("draggedIndex" in text, "dragInsideTaskbar" in text, "draggedIcon" in text) == (False, False, False)


def test_tap_handlers_name_the_mouse_button_so_the_task_button_id_stays_the_menus_parent():
    """`onTapped: button =>` would shadow the TaskButton's id, and the window menu would be given a number."""
    window_button = qml_block(main_qml(), "id: windowButton")

    assert (
        "onTapped: button =>" in window_button,
        "onTapped: (mouseButton, clickX, clickY) =>" in window_button,
        "windowMenu.visualParent = button" in window_button,
    ) == (
        False,
        True,
        True,
    )
