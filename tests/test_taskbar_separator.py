"""The taskbar separator (plasmoids/org.chicago95.tasks/contents/ui/Separator.qml) under a real mouse, offscreen.

Dragged, it reports where its left edge would be under the pointer, in its parent's coordinates, on every move and
when let go; the Quick Launch band follows those reports. Hovered, it shows the left-right resize cursor.
"""

import pytest
from conftest import REPO
from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtQuick import QQuickItem, QQuickView
from PySide6.QtTest import QTest

UI = REPO / "plasmoids/org.chicago95.tasks/contents/ui"
SEPARATOR_X, GRAB_AT = 100, 5


@pytest.fixture
def separator_view(qt_app, tmp_path):
    scene = tmp_path / "scene.qml"
    scene.write_text(
        f"""import QtQuick
import "{UI.as_uri()}"
Item {{
    width: 400
    height: 28
    property var moves: []
    property var releases: []
    Separator {{
        objectName: "separator"
        x: {SEPARATOR_X}
        height: parent.height
        draggable: true
        onDragged: gripX => parent.moves = parent.moves.concat([gripX])
        onReleased: gripX => parent.releases = parent.releases.concat([gripX])
    }}
}}
"""
    )
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(str(scene)))
    assert view.status() == QQuickView.Ready, [error.toString() for error in view.errors()]
    view.show()
    qt_app.processEvents()
    yield view
    view.close()


def test_dragging_a_separator_reports_its_left_edge_under_the_pointer_on_each_move_and_on_release(separator_view):
    start = QPoint(SEPARATOR_X + GRAB_AT, 14)
    QTest.mousePress(separator_view, Qt.LeftButton, Qt.NoModifier, start)
    for step in (10, 40, -30):
        QTest.mouseMove(separator_view, start + QPoint(step, 0))
    QTest.mouseRelease(separator_view, Qt.LeftButton, Qt.NoModifier, start + QPoint(-30, 0))
    root = separator_view.rootObject()

    assert (root.property("moves").toVariant(), root.property("releases").toVariant()) == (
        [SEPARATOR_X + 10, SEPARATOR_X + 40, SEPARATOR_X - 30],
        [SEPARATOR_X - 30],
    )


def test_a_draggable_separator_shows_the_left_right_resize_cursor(separator_view):
    separator = separator_view.rootObject().findChild(QQuickItem, "separator")
    mouse_area = next(
        child for child in separator.childItems() if child.metaObject().className().startswith("QQuickMouseArea")
    )

    assert mouse_area.cursor().shape() == Qt.SizeHorCursor
