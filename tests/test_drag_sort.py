"""Dragging a task button or a Quick Launch cell sorts it: the button follows the pointer under a closed hand,
the others slide aside, and letting go drops it in its new place (plasmoids/org.chicago95.tasks:
dragSort.js for the arithmetic, DragSortArea.qml for the pointer handling)."""

import pytest
from conftest import REPO
from js_library import call, load_js_library
from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

UI = REPO / "plasmoids/org.chicago95.tasks/contents/ui"
ORIGIN, PITCH, COUNT = 10, 23, 4


@pytest.fixture(scope="module")
def drag_sort(qt_app):
    return load_js_library(UI / "dragSort.js")


@pytest.mark.parametrize(
    "centre_x, slot",
    [(ORIGIN + 11, 0), (ORIGIN + 22, 0), (ORIGIN + 23, 1), (ORIGIN + 23 * 2 + 11, 2), (ORIGIN + 23 * 3 + 11, 3)],
)
def test_the_slot_under_an_items_centre_changes_at_the_midpoint_between_slots(drag_sort, centre_x, slot):
    assert call(drag_sort, "slotAt", centre_x, ORIGIN, PITCH, COUNT) == slot


@pytest.mark.parametrize(
    "centre_x, count, slot", [(ORIGIN - 200, COUNT, 0), (ORIGIN + 900, COUNT, 3), (ORIGIN + 900, 1, 0)]
)
def test_the_slot_is_clamped_to_the_sections_ends(drag_sort, centre_x, count, slot):
    assert call(drag_sort, "slotAt", centre_x, ORIGIN, PITCH, count) == slot


def test_the_dragged_item_follows_the_pointer_by_where_it_was_grabbed(drag_sort):
    assert call(drag_sort, "draggedX", 100, 7, 0, 500) == 93


@pytest.mark.parametrize("pointer_x, x", [(3, 10), (400, 79)])
def test_the_dragged_item_stays_inside_its_section(drag_sort, pointer_x, x):
    assert call(drag_sort, "draggedX", pointer_x, 7, ORIGIN, call(drag_sort, "lastX", ORIGIN, PITCH, COUNT)) == x


@pytest.mark.parametrize("x, y, starts", [(9, 0, False), (4, 5, False), (10, 0, True), (5, 5, True)])
def test_a_press_becomes_a_drag_past_the_start_drag_distance(drag_sort, x, y, starts):
    assert call(drag_sort, "startsDrag", 0, 0, x, y, 10) is starts


# ---- DragSortArea.qml, driven with the mouse in a row of four 23px cells starting at x 0.

HARNESS = b"""
import QtQuick
Item {
    id: harness
    width: 200
    height: 28
    property var moves: []
    property var taps: []
    property var tapPoints: []
    ListModel {
        id: cells
        ListElement { name: "a" }
        ListElement { name: "b" }
        ListElement { name: "c" }
        ListElement { name: "d" }
    }
    Repeater {
        model: cells
        Rectangle {
            required property int index
            objectName: "cell" + index
            x: area.dragging ? area.dragX : index * 23
            width: 23
            height: 28
            color: "gray"
            DragSortArea {
                id: area
                objectName: "area" + parent.index
                anchors.fill: parent
                layoutParent: harness
                origin: 0
                pitch: 23
                count: 4
                slot: parent.index
                itemWidth: 23
                threshold: 10
                onMoved: (from, to) => { harness.moves = harness.moves.concat([[from, to]]); cells.move(from, to, 1); }
                onTapped: (button, x, y) => {
                    harness.taps = harness.taps.concat([button]);
                    harness.tapPoints = harness.tapPoints.concat([[x, y]]);
                }
            }
        }
    }
}
"""


@pytest.fixture
def harness(qt_app):
    view = QQuickView()
    component = QQmlComponent(view.engine())
    component.setData(HARNESS, QUrl.fromLocalFile(str(UI / "harness.qml")))
    assert not component.isError(), [error.toString() for error in component.errors()]
    root = component.create()
    root.setParentItem(view.contentItem())
    view.resize(200, 28)
    view.show()
    QTest.qWaitForWindowExposed(view)
    yield view, root
    view.close()


def drag(qt_app, view, start, *stops, release=True):
    QTest.mousePress(view, Qt.LeftButton, Qt.NoModifier, QPoint(*start))
    for stop in stops:
        QTest.mouseMove(view, QPoint(*stop))
        qt_app.processEvents()
    if release:
        QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, QPoint(*stops[-1]))
    qt_app.processEvents()


def items(item):
    for child in item.childItems():
        yield child
        yield from items(child)


def named(root, name):
    return next(item for item in items(root) if item.objectName() == name)


def recorded(root, name):
    return root.property(name).toVariant()


def test_the_dragged_item_moves_with_the_pointer_under_a_closed_hand(qt_app, harness):
    view, root = harness
    dragged, area = named(root, "cell0"), named(root, "area0")
    before = area.property("cursorShape")
    drag(qt_app, view, (5, 14), (15, 14), release=False)
    during = (dragged.x(), area.property("dragging"), area.property("cursorShape"))
    QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, QPoint(15, 14))
    qt_app.processEvents()

    assert (before, during, dragged.x(), area.property("cursorShape")) == (
        Qt.ArrowCursor,
        (10, True, Qt.ClosedHandCursor),
        0,
        Qt.ArrowCursor,
    )


def test_an_item_dragged_past_half_a_cell_moves_into_the_next_slot_and_keeps_being_dragged(qt_app, harness):
    view, root = harness
    dragged = named(root, "cell0")
    drag(qt_app, view, (5, 14), (15, 14), (22, 14), (25, 14), (28, 14))

    assert (recorded(root, "moves"), dragged.objectName(), dragged.x()) == ([[0, 1]], "cell1", 23)


def test_a_drag_is_not_a_click_but_a_small_movement_still_is(qt_app, harness):
    view, root = harness
    drag(qt_app, view, (5, 14), (15, 14), (25, 14))
    after_drag = recorded(root, "taps")
    drag(qt_app, view, (5, 14), (7, 14))

    assert (after_drag, recorded(root, "taps"), recorded(root, "moves")) == ([], [int(Qt.LeftButton.value)], [[0, 1]])


def test_a_click_reports_where_it_landed_inside_the_item_so_a_menu_can_open_at_the_pointer(qt_app, harness):
    view, root = harness
    QTest.mouseClick(view, Qt.RightButton, Qt.NoModifier, QPoint(23 + 7, 9))
    qt_app.processEvents()

    assert (recorded(root, "taps"), recorded(root, "tapPoints")) == ([int(Qt.RightButton.value)], [[7, 9]])


def test_the_dragged_item_cannot_leave_its_section(qt_app, harness):
    view, root = harness
    dragged = named(root, "cell0")
    drag(qt_app, view, (5, 14), (100, 14), (190, 14), release=False)
    during = dragged.x()
    # QTest remembers a held button across windows: left down, it would turn later tests' clicks into drags.
    QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, QPoint(190, 14))
    qt_app.processEvents()

    assert (during, recorded(root, "moves")) == (69, [[0, 3]])


def test_the_drag_threshold_defaults_to_the_platforms_start_drag_distance(qt_app):
    view = QQuickView()
    component = QQmlComponent(view.engine())
    component.setData(b"import QtQuick\nDragSortArea {}\n", QUrl.fromLocalFile(str(UI / "harness.qml")))
    assert not component.isError(), [error.toString() for error in component.errors()]

    assert component.create().property("threshold") == QGuiApplication.styleHints().startDragDistance()


def test_a_drag_sort_area_created_before_it_has_a_parent_raises_no_warning(qt_app):
    """A Loader creates the button before parenting it: the default layoutParent must not touch a null parent."""
    from PySide6.QtQml import QQmlEngine

    engine = QQmlEngine()
    engine.setOutputWarningsToStandardError(False)
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(error.toString() for error in errors))
    component = QQmlComponent(engine)
    component.setData(b"import QtQuick\nDragSortArea {}\n", QUrl.fromLocalFile(str(UI / "harness.qml")))
    area = component.create()
    qt_app.processEvents()

    assert (area is not None, warnings) == (True, [])
