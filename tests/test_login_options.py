"""Interactive Control Panel login tests use mock accounts and never authenticate."""

import pytest
from conftest import load_script
from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtTest import QTest


@pytest.fixture
def dialog(qt_app):
    panel = load_script("chicago95-control-panel")
    window = panel.LoginTestDialog({"LOGIN_STYLE": "luna", "BANNER_TEXT": "Preview OS"})
    window.show()
    QTest.qWait(100)
    yield window
    window.close()


def tile(dialog, name):
    def find(item):
        if item.objectName() == f"userTile-{name}":
            return item
        for child in item.childItems():
            found = find(child)
            if found is not None:
                return found
        return None

    return find(dialog.preview.rootObject())


def test_multiple_users_are_centered_and_selectable(dialog, qt_app):
    first, last = tile(dialog, "Alex"), tile(dialog, "Taylor")
    assert not any(tile(dialog, user).property("selected") for user in ("Alex", "Sam", "Taylor"))
    top = first.mapToScene(QPointF(0, 0)).y()
    bottom = last.mapToScene(QPointF(0, last.height())).y()
    assert top > 80 and bottom < 504
    assert abs((top + bottom) / 2 - 287.5) < 1
    for name in ("Taylor", "Alex", "Sam"):
        target = tile(dialog, name)
        point = target.mapToScene(QPointF(30, 30)).toPoint()
        QTest.mouseClick(dialog.preview, Qt.LeftButton, pos=point)
        qt_app.processEvents()
        assert target.property("selected")
        assert sum(tile(dialog, user).property("selected") for user in ("Alex", "Sam", "Taylor")) == 1


def test_failed_login_keeps_focus_on_selected_user_and_clears_password(dialog, qt_app):
    selected = tile(dialog, "Alex")
    QTest.mouseClick(dialog.preview, Qt.LeftButton, pos=selected.mapToScene(QPointF(30, 30)).toPoint())
    field = selected.findChild(QObject, "passwordInput")
    dialog.activateWindow()
    dialog.preview.setFocus()
    QTest.mouseClick(dialog.preview, Qt.LeftButton, pos=field.mapToScene(QPointF(10, 10)).toPoint())
    QTest.keyClicks(dialog.preview, "dummy password")
    assert field.property("text") == "dummy password"
    QTest.keyClick(dialog.preview, Qt.Key_Return)
    qt_app.processEvents()
    assert field.property("text") == ""
    assert field.property("activeFocus")
    assert "incorrect password" in dialog.status.text()
    assert not tile(dialog, "Taylor").findChild(QObject, "passwordInput").property("activeFocus")


def test_test_login_simulates_success_and_power_without_real_actions(dialog):
    greeter = dialog.preview.context["sddm"]
    dialog.fail_login.setChecked(False)
    greeter.login("Sam", "dummy", 1)
    assert "successful login for Sam, session 2" in dialog.status.text()
    greeter.powerOff()
    assert dialog.status.text() == "Power off requested (simulation only)."


def test_test_window_uses_unsaved_settings_from_both_login_tabs(qt_app):
    panel = load_script("chicago95-control-panel")
    login = panel.build_tab("Passwords", "Log On", {}, panel.Actions())
    branding = panel.build_tab("Passwords", "Branding", {}, panel.Actions())
    applied = []
    page = panel.PropertiesPage("Passwords", [("Log On", login), ("Branding", branding)], applied.append)
    login.fields["LOGIN_STYLE"][1]("luna")
    branding.fields["EDITION"][1]("Unsaved edition")
    preview = login.previews[0]
    preview.open_test()
    window = preview.test_window
    assert window.preview.context["config"]["loginStyle"] == "luna"
    assert window.preview.context["config"]["edition"] == "Unsaved edition"
    assert window.preview.size().toTuple() == (800, 600)
    assert applied == []
    window.close()
    page.close()


def test_avatar_image_stays_inside_its_square_frame(dialog, tmp_path, qt_app):
    from login_preview import NAME_ROLE
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QColor, QImage

    picture = QImage(90, 30, QImage.Format_RGB32)
    picture.fill(QColor("#cc3388"))
    path = tmp_path / "wide-avatar.png"
    picture.save(str(path))
    model = dialog.preview.context["userModel"]
    model.setData(model.index(0, 0), QUrl.fromLocalFile(str(path)).toString(), NAME_ROLE + 2)
    QTest.qWait(100)
    user = tile(dialog, "Alex")
    frame = user.findChild(QObject, "avatarFrame")
    image = user.findChild(QObject, "avatarImage")
    assert (frame.width(), frame.height()) == (52, 52)
    assert (image.width(), image.height()) == (48, 48)
    point = image.mapToScene(QPointF(24, 24)).toPoint()
    screen = dialog.preview.grabFramebuffer()
    assert screen.pixelColor(point).name() == "#cc3388"
    QTest.mouseClick(dialog.preview, Qt.LeftButton, pos=user.mapToScene(QPointF(30, 30)).toPoint())
    assert (frame.width(), frame.height()) == (52, 52)


def test_logged_on_status_tracks_session_model_without_changing_selection(dialog, qt_app):
    from login_preview import LOGGED_IN_ROLE

    model = dialog.preview.context["userModel"]
    sam = tile(dialog, "Sam")
    alex = tile(dialog, "Alex")
    assert sam.property("loggedIn")
    assert sam.findChild(QObject, "userStatus").property("text") == "Logged on"
    assert not alex.property("loggedIn")
    QTest.mouseClick(dialog.preview, Qt.LeftButton, pos=sam.mapToScene(QPointF(30, 30)).toPoint())
    assert sam.property("selected")
    assert sam.findChild(QObject, "passwordInput").isVisible()
    model.setData(model.index(0, 0), True, LOGGED_IN_ROLE)
    model.setData(model.index(1, 0), False, LOGGED_IN_ROLE)
    qt_app.processEvents()
    assert alex.findChild(QObject, "userStatus").property("text") == "Logged on"
    assert sam.findChild(QObject, "userStatus").property("text") == "Type your password"
    assert sam.property("selected")


@pytest.mark.parametrize(
    "kind,session_class,state,remote,expected",
    [
        ("wayland", "user", "active", False, True),
        ("x11", "user", "online", False, True),
        ("wayland", "user-early", "online", False, True),
        ("wayland", "greeter", "active", False, False),
        ("tty", "user", "active", False, False),
        ("wayland", "user", "closing", False, False),
        ("x11", "user", "active", True, False),
    ],
)
@pytest.mark.parametrize("wrapped", [False, True])
def test_live_status_only_counts_open_local_graphical_sessions(
    qt_app, kind, session_class, state, remote, expected, wrapped
):
    import json

    from conftest import REPO
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression

    engine = QQmlEngine()
    component = QQmlComponent(engine)
    component.setData(
        b"import QtQuick\nActiveSessions { visible: false }",
        QUrl.fromLocalFile(str(REPO / "luna/sddm/session-test.qml")),
    )
    obj = component.create()
    assert obj is not None, [error.toString() for error in component.errors()]
    values = dict(Type=kind, Class=session_class, State=state, Remote=remote)
    if wrapped:
        values = {key: {"value": value} for key, value in values.items()}
    expression = QQmlExpression(engine.rootContext(), obj, "isDesktopSession(" + json.dumps(values) + ")")
    value, undefined = expression.evaluate()
    assert not expression.hasError(), expression.error().toString()
    assert not undefined and value is expected
    obj.deleteLater()
