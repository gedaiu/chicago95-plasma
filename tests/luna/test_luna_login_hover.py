"""Pointer transitions in yAu91yWpSMI at 1:27 and EEuBC6NcOnA at 0:38."""

import pytest
from conftest import REPO
from PySide6.QtCore import QObject, QPoint, Qt, QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

from .luna_qml import garbage_collection_paused


@pytest.fixture
def tile_view(qt_app):
    with garbage_collection_paused():
        view = QQuickView()
        view.setSource(QUrl.fromLocalFile(str(REPO / "luna/sddm/LunaUserTile.qml")))
        view.resize(500, 200)
        assert not view.errors()
        tile = view.rootObject()
        tile.setProperty("name", "Guest")
        view.show()
        QTest.qWait(50)
        QTest.mouseMove(view, QPoint(35, 35))
        QTest.qWait(50)
        QTest.mouseMove(view, QPoint(450, 150))
        QTest.qWait(180)
        yield view, tile
        view.close()


def test_hover_brightens_account_without_selecting_or_showing_password(tile_view):
    view, tile = tile_view
    frame = tile.findChild(QObject, "avatarFrame")
    name = tile.findChild(QObject, "userName")
    initial_y = name.property("y")
    assert initial_y == 8
    assert tile.opacity() == pytest.approx(0.5)
    assert frame.property("color").name() == "#a6b6ce"

    QTest.mouseMove(view, QPoint(35, 35))
    QTest.qWait(60)
    assert 0.5 < tile.opacity() < 1
    QTest.qWait(150)
    assert tile.property("hovered")
    assert tile.opacity() == 1
    assert name.property("y") == initial_y
    assert frame.property("color").name() == "#ffb600"
    assert not tile.property("selected")
    assert not tile.property("askingPassword")
    assert tile.findChild(QObject, "selectionFill").property("opacity") == 0

    QTest.mouseMove(view, QPoint(450, 150))
    QTest.qWait(180)
    assert tile.opacity() == pytest.approx(0.5)
    assert frame.property("color").name() == "#a6b6ce"
    assert name.property("y") == initial_y


def test_selected_account_stays_bright_and_password_keeps_focus(tile_view):
    view, tile = tile_view
    tile.chosen.connect(lambda: tile.setProperty("selected", True))
    QTest.mouseClick(view, Qt.LeftButton, pos=QPoint(35, 35))
    QTest.mouseMove(view, QPoint(450, 150))
    QTest.qWait(180)
    assert tile.property("selected")
    assert tile.findChild(QObject, "userName").property("y") == 8
    assert tile.opacity() == 1
    assert tile.findChild(QObject, "selectionFill").property("opacity") == 1
    password = tile.findChild(QObject, "passwordInput")
    assert password.property("activeFocus")
    for letter in "secret":
        QTest.keyClick(view, letter)
    assert tile.property("password") == "secret"
    tile.setProperty("selected", False)
    QTest.qWait(180)
    assert tile.property("password") == ""
    assert tile.opacity() == pytest.approx(0.5)
