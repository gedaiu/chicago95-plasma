import pytest
from conftest import REPO
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

TILE = REPO / "luna/sddm/LunaUserTile.qml"


PICTURE = REPO / "tests/references/clippy-letter.png"


@pytest.fixture(scope="module")
def engine(qt_app):
    return QQmlEngine()


def created_tile(engine, **properties):
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(TILE)))
    tile = component.createWithInitialProperties({"name": "Guest", **properties})
    assert tile is not None, component.errorString()
    return tile, component


def avatar_margins(engine, selected):
    tile, _component = created_tile(engine, selected=selected)
    frame = tile.findChild(QObject, "avatarFrame")
    top = frame.property("y")
    margins = top, tile.property("height") - top - frame.property("height")
    tile.deleteLater()
    return margins


def test_unselected_tile_keeps_the_selected_avatar_margins_of_10_and_8(engine):
    assert (avatar_margins(engine, False), avatar_margins(engine, True)) == ((10, 8), (10, 8))


def default_picture_shown(engine, **properties):
    tile, _component = created_tile(engine, **properties)
    shown = tile.findChild(QObject, "defaultPicture").property("visible")
    tile.deleteLater()
    return shown


def test_default_picture_is_hidden_on_an_idle_tile_with_a_user_picture_and_shown_without_one(engine):
    picture = QUrl.fromLocalFile(str(PICTURE))
    with_picture = default_picture_shown(engine, selected=False, picture=picture)

    assert (with_picture, default_picture_shown(engine, selected=False)) == (False, True)
