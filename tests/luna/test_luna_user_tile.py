from conftest import REPO
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

TILE = REPO / "luna/sddm/LunaUserTile.qml"


def avatar_margins(selected):
    engine = QQmlEngine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(TILE)))
    tile = component.createWithInitialProperties({"selected": selected, "name": "Guest"})
    assert tile is not None, component.errorString()
    frame = tile.findChild(QObject, "avatarFrame")
    top = frame.property("y")
    margins = top, tile.property("height") - top - frame.property("height")
    tile.deleteLater()
    return margins


def test_unselected_tile_keeps_the_selected_avatar_margins_of_10_and_8(qt_app):
    assert (avatar_margins(False), avatar_margins(True)) == ((10, 8), (10, 8))
