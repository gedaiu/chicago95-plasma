import pytest

from conftest import REPO
from js_library import call, load_js_library

QUICK_LAUNCH_X = 10
TASKBAR_WIDTH, TASKBAR_HEIGHT = 600, 28
FOUR_LAUNCHERS = 4


@pytest.fixture(scope="module")
def launchers(qt_app):
    return load_js_library(REPO / "plasmoids/org.chicago95.tasks/contents/ui/launchers.js")


@pytest.mark.parametrize("x, count, expected", [
    (QUICK_LAUNCH_X + 0, FOUR_LAUNCHERS, 0),
    (QUICK_LAUNCH_X + 11, FOUR_LAUNCHERS, 0),
    (QUICK_LAUNCH_X + 12, FOUR_LAUNCHERS, 1),
    (QUICK_LAUNCH_X + 23 * 2, FOUR_LAUNCHERS, 2),
    (QUICK_LAUNCH_X - 40, FOUR_LAUNCHERS, 0),
    (QUICK_LAUNCH_X + 500, FOUR_LAUNCHERS, 4),
    (QUICK_LAUNCH_X + 5, 0, 0),
])
def test_insertion_index_is_the_nearest_gap_between_23px_cells(launchers, x, count, expected):
    assert call(launchers, "insertionIndexAt", x, QUICK_LAUNCH_X, count) == expected


def drag_result(launchers, from_index, x, y):
    return call(launchers, "dragResult", from_index, x, y, TASKBAR_WIDTH, TASKBAR_HEIGHT, QUICK_LAUNCH_X, FOUR_LAUNCHERS)


@pytest.mark.parametrize("y", [-30, TASKBAR_HEIGHT + 30])
def test_releasing_a_launcher_well_above_or_below_the_taskbar_removes_it(launchers, y):
    assert drag_result(launchers, 1, QUICK_LAUNCH_X + 30, y) == {"action": "remove", "to": -1}


def test_releasing_a_launcher_well_right_of_the_taskbar_removes_it(launchers):
    assert drag_result(launchers, 1, TASKBAR_WIDTH + 40, 10) == {"action": "remove", "to": -1}


def test_dropping_launcher_0_before_cell_3_moves_it_to_position_2(launchers):
    assert drag_result(launchers, 0, QUICK_LAUNCH_X + 23 * 3, 10) == {"action": "move", "to": 2}


def test_dropping_launcher_3_before_cell_0_moves_it_to_the_front(launchers):
    assert drag_result(launchers, 3, QUICK_LAUNCH_X, 10) == {"action": "move", "to": 0}


@pytest.mark.parametrize("x", [QUICK_LAUNCH_X + 23 * 2, QUICK_LAUNCH_X + 23 * 3])
def test_dropping_launcher_2_back_in_its_own_gap_changes_nothing(launchers, x):
    assert drag_result(launchers, 2, x, 10) == {"action": "none", "to": -1}


def test_dragging_a_little_outside_the_taskbar_edge_does_not_remove_the_launcher(launchers):
    assert drag_result(launchers, 0, QUICK_LAUNCH_X + 23 * 2, -5)["action"] == "move"


def test_tasks_applet_wires_dragging_and_dropping_to_the_launchers_library():
    main_qml = (REPO / "plasmoids/org.chicago95.tasks/contents/ui/main.qml").read_text()

    assert ('import "launchers.js" as Launchers' in main_qml, "Launchers.dragResult(" in main_qml, "Launchers.insertionIndexAt(" in main_qml,
            "tasksModel.move(" in main_qml) == (True, True, True, True)


def test_quick_launch_cells_show_the_programs_name_and_icon_as_a_tooltip():
    main_qml = (REPO / "plasmoids/org.chicago95.tasks/contents/ui/main.qml").read_text()
    launcher_cell = main_qml.split("id: launcherCell")[1].split("Component {")[0]

    tooltip = launcher_cell.split("PlasmaCore.ToolTipArea {")[1].split("}")[0]

    assert ("mainText: entry.model.display" in tooltip, "icon: entry.model.decoration" in tooltip) == (True, True)
