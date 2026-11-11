import shutil

import pytest
from conftest import REPO
from PySide6.QtCore import QPoint, Qt, QTimer, QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

TASKS = REPO / "plasmoids/org.chicago95.tasks/contents/ui"
LUNA_TASKS = REPO / "luna/plasmoids/org.chicago95.tasks/contents/ui/luna"
SEAM_X, SEAM_HEIGHT, GRABBED_AT, DRAGGED_BY = 100, 30, 8, 30
HARNESS = """import QtQuick
Item {
    width: 400; height: 30
    property int draggedTo: -1
    property int releasedAt: -1
    SeparatorSeam {
        x: %(x)d; height: %(height)d; luna: %(luna)s; lead: 4
        onDragged: gripX => draggedTo = gripX
        onReleased: gripX => releasedAt = gripX
    }
}
"""


@pytest.fixture(scope="module")
def ui(tmp_path_factory):
    folder = tmp_path_factory.mktemp("tasks-ui")
    shutil.copytree(TASKS, folder, dirs_exist_ok=True)
    shutil.copytree(LUNA_TASKS, folder / "luna", dirs_exist_ok=True)
    return folder


def drag_separator(qt_app, ui, luna):
    (ui / "harness.qml").write_text(HARNESS % {"x": SEAM_X, "height": SEAM_HEIGHT, "luna": luna})
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(str(ui / "harness.qml")))
    assert [error.toString() for error in view.errors()] == []
    view.show()
    QTimer.singleShot(200, qt_app.quit)
    qt_app.exec()
    press = QPoint(SEAM_X + GRABBED_AT, 15)
    QTest.mousePress(view, Qt.LeftButton, Qt.NoModifier, press)
    QTest.mouseMove(view, press + QPoint(DRAGGED_BY // 2, 0))
    QTest.mouseMove(view, press + QPoint(DRAGGED_BY, 0))
    QTest.mouseRelease(view, Qt.LeftButton, Qt.NoModifier, press + QPoint(DRAGGED_BY, 0))
    root = view.rootObject()
    reported = (root.property("draggedTo"), root.property("releasedAt"))
    view.close()
    return reported


@pytest.mark.parametrize("luna", ["false", "true"])
def test_dragging_a_separator_30px_right_reports_its_left_edge_30px_right_in_the_taskbars_coordinates(qt_app, ui, luna):
    assert drag_separator(qt_app, ui, luna) == (SEAM_X + DRAGGED_BY, SEAM_X + DRAGGED_BY)
