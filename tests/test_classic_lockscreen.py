from contextlib import contextmanager

import pytest
from conftest import REPO, run_bash_with_steps
from login_theme import overlapping_pairs
from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtQuick import QQuickItem, QQuickView
from PySide6.QtTest import QTest
from reference import qimage_to_pil
from test_install import dry_run_log

THEME = REPO / "sddm/Chicago95Plasma"
LOCK_SCREEN_UI = REPO / "lockscreen/lockscreen/LockScreenUi.qml"
HARNESS = """import QtQuick 2.15
import "%s"

ClassicLockScreen {
    width: 800
    height: 600
    userName: "Nathan"
    modern: %s
    desktopColor: "#112233"
    authenticator: lockAuthenticator
    onPasswordEntered: password => lockAuthenticator.respond(password)
}
"""


class Authenticator(QObject):
    failed = Signal(int)

    def __init__(self):
        super().__init__()
        self.responses = []

    @Slot(str)
    def respond(self, password):
        self.responses.append(password)


def wait(app, milliseconds):
    QTimer.singleShot(milliseconds, app.quit)
    app.exec()


@contextmanager
def lock_screen(app, tmp_path, modern=False):
    harness = tmp_path / "harness.qml"
    harness.write_text(HARNESS % (THEME.as_uri(), str(modern).lower()))
    authenticator = Authenticator()
    view = QQuickView()
    view.rootContext().setContextProperty("lockAuthenticator", authenticator)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(800, 600)
    view.setSource(QUrl.fromLocalFile(str(harness)))
    assert [error.toString() for error in view.errors()] == []
    view.show()
    wait(app, 300)
    try:
        yield view, authenticator
    finally:
        view.close()


def named(view, name):
    return view.rootObject().findChild(QQuickItem, name)


def type_password(app, view, keys):
    for key in keys:
        QTest.keyClick(view, Qt.Key_Return if key == "\r" else key)
    wait(app, 100)


def has_the_keyboard(view):
    return view.activeFocusItem().parentItem().objectName() == "lockPassword"


def sits_inside(child, window):
    return (
        child.x() >= 0
        and child.y() >= 0
        and child.x() + child.width() <= window.width()
        and (child.y() + child.height() <= window.height())
    )


def shown_texts(item):
    texts = [item.property("text")] if item.metaObject().className().startswith("ClassicText") else []
    return texts + [text for child in item.childItems() if child.isVisible() for text in shown_texts(child)]


@pytest.mark.parametrize(("modern", "title"), [(False, "Windows Screen Saver"), (True, "Unlock Computer")])
def test_lock_dialog_is_titled_like_the_windows_of_its_look(qt_app, tmp_path, modern, title):
    with lock_screen(qt_app, tmp_path, modern) as (view, _):
        assert shown_texts(named(view, "lockDialog"))[0] == title


@pytest.mark.parametrize("modern", [False, True], ids=["9x", "2000"])
def test_password_box_has_the_keyboard_before_anything_is_typed(qt_app, tmp_path, modern):
    with lock_screen(qt_app, tmp_path, modern) as (view, _):
        assert has_the_keyboard(view)


def test_2000_dialog_names_the_user_who_can_unlock_it(qt_app, tmp_path):
    with lock_screen(qt_app, tmp_path, modern=True) as (view, _):
        assert "Only Nathan or an administrator can unlock this computer." in shown_texts(named(view, "lockDialog"))[1]


def test_screen_around_the_dialog_is_the_desktop_colour(qt_app, tmp_path):
    with lock_screen(qt_app, tmp_path) as (view, _):
        image = qimage_to_pil(view.grabWindow()).convert("RGB")
        assert {image.getpixel(point) for point in [(10, 10), (790, 10), (10, 590), (790, 590)]} == {(0x11, 0x22, 0x33)}


def test_typing_a_password_and_enter_hands_it_to_the_authenticator(qt_app, tmp_path):
    with lock_screen(qt_app, tmp_path) as (view, authenticator):
        type_password(qt_app, view, "secret\r")
        assert authenticator.responses == ["secret"]


def test_wrong_password_brings_up_the_message_box(qt_app, tmp_path):
    with lock_screen(qt_app, tmp_path) as (view, authenticator):
        type_password(qt_app, view, "wrong\r")
        authenticator.failed.emit(0)
        wait(qt_app, 50)
        assert named(view, "lockMessage").isVisible()


def test_a_fingerprint_failure_brings_up_no_message_box(qt_app, tmp_path):
    with lock_screen(qt_app, tmp_path) as (view, authenticator):
        authenticator.failed.emit(1)
        wait(qt_app, 50)
        assert not named(view, "lockMessage").isVisible()


def test_ok_on_the_message_box_closes_it_and_gives_the_empty_password_box_the_keyboard(qt_app, tmp_path):
    with lock_screen(qt_app, tmp_path) as (view, authenticator):
        type_password(qt_app, view, "wrong\r")
        authenticator.failed.emit(0)
        wait(qt_app, 50)
        type_password(qt_app, view, " ")
        field = named(view, "lockPassword")
        assert (
            named(view, "lockMessage").isVisible(),
            field.property("text"),
            has_the_keyboard(view),
        ) == (
            False,
            "",
            True,
        )


def test_cancel_empties_the_password_box(qt_app, tmp_path):
    with lock_screen(qt_app, tmp_path) as (view, _):
        type_password(qt_app, view, "half")
        named(view, "lockCancel").clicked.emit()
        wait(qt_app, 50)
        assert named(view, "lockPassword").property("text") == ""


@pytest.mark.parametrize("modern", [False, True], ids=["9x", "2000"])
@pytest.mark.parametrize("failed", [False, True], ids=["prompt", "message"])
def test_no_text_or_control_of_the_lock_screen_overlaps_another(qt_app, tmp_path, modern, failed):
    with lock_screen(qt_app, tmp_path, modern) as (view, authenticator):
        if failed:
            authenticator.failed.emit(0)
            wait(qt_app, 50)
        assert overlapping_pairs(view.rootObject()) == []


@pytest.mark.parametrize("modern", [False, True], ids=["9x", "2000"])
def test_every_text_and_control_sits_inside_its_window(qt_app, tmp_path, modern):
    with lock_screen(qt_app, tmp_path, modern) as (view, authenticator):
        authenticator.failed.emit(0)
        wait(qt_app, 50)
        windows = [named(view, "lockDialog"), named(view, "lockMessage")]
        assert [
            (window.objectName(), child.property("text") or child.property("label") or child.objectName())
            for window in windows
            for child in window.childItems()
            if child.isVisible() and not sits_inside(child, window)
        ] == []


def test_lock_screen_ui_hides_breezes_own_prompt_and_footer():
    text = LOCK_SCREEN_UI.read_text()
    assert (
        "the loaded screen draws the lock screen.\n            visible: false\n" in text,
        "id: footer\n            visible: false\n" in text,
    ) == (True, True)


def test_setup_installs_the_classic_screen_inside_the_lockscreen_package(tmp_path):
    log = dry_run_log(tmp_path, "--components=lockscreen", "--look=1998").replace(str(tmp_path), "~")
    assert "lockscreen/classic/ClassicLockScreen.qml" in log


def test_setup_writes_the_look_and_desktop_colour_into_the_lock_screen_settings(tmp_path):
    run_bash_with_steps(
        tmp_path,
        "SETUP_DRY_RUN=0 SETUP_START_MENU_STYLE=2000 SETUP_BACKGROUND_COLOR=#3A6EA5; "
        f"write_lockscreen_settings {tmp_path}",
    )
    assert (
        tmp_path / "settings.js"
    ).read_text() == '.pragma library\nvar look = "2000";\nvar desktopColor = "#3A6EA5";\n'
