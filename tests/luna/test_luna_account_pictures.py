from conftest import REPO
from login_preview import login_context
from PySide6.QtCore import QDeadlineTimer, QThread, QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QApplication

from .luna_qml import HARNESS, SDDM_THEME

STOCK = REPO / "luna/images/account-pictures"
OWN = REPO / "tests/references/clippy-letter.png"
SDDM_DEFAULT = "/usr/share/sddm/faces/.face.icon"
USERS = (
    {"name": "alice", "icon": str(OWN)},
    {"name": "bob", "icon": SDDM_DEFAULT},
    {"name": "carol"},
    {"name": "dave"},
)


def descendants(item):
    for child in item.childItems():
        yield child
        yield from descendants(child)


def shown_pictures(qt_app):
    context = login_context(SDDM_THEME, user="alice", users=USERS)
    view = QQuickView()
    for name, value in context.items():
        view.rootContext().setContextProperty(name, value)
    view.setSource(QUrl.fromLocalFile(str(HARNESS / "LunaLoginHarness.qml")))
    items = {item.objectName(): item for item in descendants(view.rootObject())}
    tiles = [items[f"userTile-{user['name']}"] for user in USERS]
    deadline = QDeadlineTimer(2000)
    while any(tile.property("picture").isEmpty() for tile in tiles[1:]) and not deadline.hasExpired():
        QApplication.processEvents()
        QThread.msleep(5)
    pictures = [tile.property("picture").path() for tile in tiles]
    view.close()
    return pictures


def test_own_picture_is_kept_and_the_others_get_three_different_stock_pictures(qt_app):
    own, *others = shown_pictures(qt_app)
    stock = {str(path) for path in STOCK.glob("*.png")}

    assert (own, len(set(others)), set(others) <= stock) == (str(OWN), 3, True)
