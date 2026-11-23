import pytest
from conftest import REPO
from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QSignalSpy, QTest
from screencast_stubs import write_stubs


@pytest.fixture
def view(qt_app, tmp_path):
    window = QQuickView()
    window.engine().addImportPath(str(write_stubs(tmp_path / "qml-stubs")))
    return window


def test_clicking_the_second_window_in_a_group_selects_that_window(view):
    view.setSource(
        QUrl.fromLocalFile(str(REPO / "aero/plasmoids/org.chicago95.tasks/contents/ui/aero/TaskToolTip.qml"))
    )
    assert not view.errors()
    tip = view.rootObject()
    tip.setProperty("title", "Notes")
    tip.setProperty("ids", ["first", "second"])
    view.resize(148, 62)
    view.show()
    QTest.qWait(100)
    selected = QSignalSpy(tip.chooseWindow)
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, QPoint(60, 44))
    assert selected.count() == 1 and selected.at(0) == [1]
    view.close()


def test_preview_close_targets_the_hovered_window_without_activating_it(view):
    view.setSource(
        QUrl.fromLocalFile(str(REPO / "aero/plasmoids/org.chicago95.tasks/contents/ui/aero/TaskToolTip.qml"))
    )
    tip = view.rootObject()
    tip.setProperty("ids", ["first", "second"])
    view.resize(148, 62)
    view.show()
    closed, selected = QSignalSpy(tip.closeWindow), QSignalSpy(tip.chooseWindow)
    point = QPoint(131, 40)
    QTest.mouseMove(view, point)
    QTest.qWait(50)
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, point)
    assert closed.count() == 1 and closed.at(0) == [1] and selected.count() == 0
    view.close()


def test_thumbnail_hover_selects_then_releases_the_window_for_peek(view):
    view.setSource(
        QUrl.fromLocalFile(str(REPO / "aero/plasmoids/org.chicago95.tasks/contents/ui/aero/TaskToolTip.qml"))
    )
    tip = view.rootObject()
    tip.setProperty("ids", ["first", "second"])
    view.resize(148, 62)
    view.show()
    try:
        assert QTest.qWaitForWindowExposed(view)
        QTest.mouseMove(view, QPoint(1, 1))
        QTest.mouseMove(view, QPoint(60, 43))
        QTest.qWait(550)
        assert tip.property("highlightedId") == "second"
        QTest.mouseMove(view, QPoint(1, 1))
        QTest.qWait(50)
        assert tip.property("highlightedId") == ""
    finally:
        view.close()
