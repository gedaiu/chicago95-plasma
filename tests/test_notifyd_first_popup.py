import pytest
from conftest import load_script
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication


@pytest.fixture
def notifyd(qt_app, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return load_script("chicago95-notifyd")


@pytest.fixture
def stack(notifyd):
    popup_stack = notifyd.PopupStack()
    yield popup_stack
    popup_stack.host.close()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def a_notification(notifyd, notification_id):
    return notifyd.Notification(
        notification_id=notification_id,
        app_name="Test",
        app_icon="",
        summary="Hello",
        body="World",
        actions=[],
        hints={},
        timeout_ms=5000,
    )


def test_the_first_notification_into_an_empty_stack_shows_the_window_that_holds_the_popups(notifyd, stack):
    stack.show(a_notification(notifyd, 1))

    assert (list(stack.popups), stack.host.isVisible()) == ([1], True)
