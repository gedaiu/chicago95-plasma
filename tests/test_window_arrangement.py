"""The taskbar menu's Cascade, Tile and Minimize All (kwin-scripts/chicago95windows), against the originals'
arrangements: in tests/references/win98cascade.png four 486px-wide windows step 22 right and 21 down from (4, 4) on
a 623x445 work area; win98tilev.png and win98tileh.png split that area into three equal columns and rows."""

import pytest
from conftest import REPO
from PySide6.QtQml import QJSEngine

SCRIPT = REPO / "kwin-scripts/chicago95windows/contents/code/main.js"
WORK_AREA = {
    "x": 4,
    "y": 4,
    "width": 619,
    "height": 441,
}  # tests/references/win98cascade.png, right of the 4px desktop edge
STUBS = """
var KWin = { WorkArea: 3 };
var windows = [];
var workspace = {
    currentDesktop: "one",
    activeOutput: "screen",
    windowList: function () { return windows; },
    clientArea: function () { return %s; },
};
function fakeWindow(stacking, extra) {
    var window = { normalWindow: true, skipTaskbar: false, onAllDesktops: true, desktops: [], minimized: false,
        minimizable: true, moveable: true, resizeable: true, stackingOrder: stacking,
        frameGeometry: { x: 100 + stacking, y: 50, width: 300, height: 200 } };
    Object.keys(extra || {}).forEach(function (key) { window[key] = extra[key]; });
    return window;
}
"""


@pytest.fixture
def engine(qt_app):
    import json

    engine = QJSEngine()
    assert not engine.evaluate(STUBS % json.dumps(WORK_AREA)).isError()
    loaded = engine.evaluate(SCRIPT.read_text(), str(SCRIPT))
    assert not loaded.isError(), loaded.toString()
    return engine


def run(engine, code):
    result = engine.evaluate(code)
    assert not result.isError(), result.toString()
    return result.toVariant()


def test_cascaded_windows_step_22_right_and_21_down_at_seven_eighths_of_what_the_stagger_leaves(engine):
    assert run(engine, f"[0, 1, 2, 3].map(index => cascadeGeometry({WORK_AREA}, {{count: 4, index}}))") == [
        {"x": 4, "y": 4, "width": 484, "height": 331},
        {"x": 26, "y": 25, "width": 484, "height": 331},
        {"x": 48, "y": 46, "width": 484, "height": 331},
        {"x": 70, "y": 67, "width": 484, "height": 331},
    ]


def test_three_windows_tiled_vertically_are_three_equal_columns_of_the_work_area(engine):
    assert run(engine, f"[0, 1, 2].map(index => tileGeometry({WORK_AREA}, {{count: 3, index}}, COLUMNS))") == [
        {"x": 4, "y": 4, "width": 206, "height": 441},
        {"x": 210, "y": 4, "width": 207, "height": 441},
        {"x": 417, "y": 4, "width": 206, "height": 441},
    ]


def test_three_windows_tiled_horizontally_are_three_equal_rows_of_the_work_area(engine):
    assert run(engine, f"[0, 1, 2].map(index => tileGeometry({WORK_AREA}, {{count: 3, index}}, ROWS))") == [
        {"x": 4, "y": 4, "width": 619, "height": 147},
        {"x": 4, "y": 151, "width": 619, "height": 147},
        {"x": 4, "y": 298, "width": 619, "height": 147},
    ]


def test_five_windows_tile_as_a_grid_of_three_columns_with_the_last_row_stretched_over_two(engine):
    area = {"x": 0, "y": 0, "width": 600, "height": 400}

    assert run(engine, f"[0, 1, 2, 3, 4].map(index => tileGeometry({area}, {{count: 5, index}}, COLUMNS))") == [
        {"x": 0, "y": 0, "width": 200, "height": 200},
        {"x": 200, "y": 0, "width": 200, "height": 200},
        {"x": 400, "y": 0, "width": 200, "height": 200},
        {"x": 0, "y": 200, "width": 300, "height": 200},
        {"x": 300, "y": 200, "width": 300, "height": 200},
    ]


def test_cascade_arranges_the_taskbars_windows_bottom_to_top_and_leaves_minimized_and_other_windows_alone(engine):
    run(
        engine,
        "windows = [fakeWindow(3), fakeWindow(1), fakeWindow(2, {minimized: true}), fakeWindow(4, {skipTaskbar: true}),"
        " fakeWindow(5, {normalWindow: false})]; cascadeWindows();",
    )

    assert run(
        engine, "windows.map(window => [window.stackingOrder, window.frameGeometry.x, window.frameGeometry.y])"
    ) == [
        [3, 26, 25],
        [1, 4, 4],
        [2, 102, 50],
        [4, 104, 50],
        [5, 105, 50],
    ]


def test_minimize_all_minimizes_the_taskbars_windows_and_undo_restores_them_and_their_places(engine):
    run(engine, "windows = [fakeWindow(1), fakeWindow(2)]; tileWindowsVertically(); minimizeAllWindows();")
    minimized = run(engine, "windows.map(window => window.minimized)")
    run(engine, "undoArrangement();")
    after_undo = run(engine, "windows.map(window => [window.minimized, window.frameGeometry.width])")
    run(engine, "undoArrangement();")  # a second Undo has nothing left to do

    assert (minimized, after_undo, run(engine, "undo")) == ([True, True], [[False, 310], [False, 309]], None)


def test_undo_skips_windows_that_closed_in_the_meantime(engine):
    run(
        engine, "windows = [fakeWindow(1), fakeWindow(2)]; cascadeWindows(); windows = [windows[1]]; undoArrangement();"
    )

    assert run(engine, "windows.map(window => window.frameGeometry.x)") == [102]


def test_the_script_registers_its_five_shortcuts_under_the_names_the_taskbar_invokes(qt_app):
    engine = QJSEngine()
    engine.evaluate(
        "var registered = []; function registerShortcut(name, text, keys, callback) { registered.push(name); }"
    )
    engine.evaluate(SCRIPT.read_text(), str(SCRIPT))

    assert engine.evaluate("registered").toVariant() == [
        "Chicago95CascadeWindows",
        "Chicago95TileWindowsHorizontally",
        "Chicago95TileWindowsVertically",
        "Chicago95MinimizeAllWindows",
        "Chicago95UndoArrangement",
    ]
