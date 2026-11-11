"""Notification popups (bin/chicago95-notifyd) move as the Effects tab's "Notifications" choice says
(chicago95rc [Animations]): sliding in and out, or appearing and leaving at once."""

import pytest
from conftest import load_script
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget

TARGET = QPoint(10, 40)


@pytest.fixture
def popup(qt_app, tmp_path, monkeypatch):
    notifyd = load_script("chicago95-notifyd")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    host = QWidget()
    host.resize(400, 400)
    notification = notifyd.Notification(1, "Test", "", "Hello", "World", [], {}, 5000)
    yield lambda choice: (
        (tmp_path / "chicago95rc").write_text(f"[Animations]\nANIM_NOTIFICATIONS={choice}\n"),
        notifyd.NotificationPopup(notification, host),
    )[1]
    host.close()


def test_without_notification_animations_a_popup_appears_in_place_at_once(popup):
    shown = popup("none")
    shown.slide_in(TARGET)

    assert (shown.pos(), shown.windowOpacity(), shown.move_animation) == (TARGET, 1.0, None)


def test_with_sliding_notifications_a_popup_slides_in_toward_its_place(popup):
    shown = popup("slide")
    shown.slide_in(TARGET)

    assert (shown.pos() != TARGET, shown.move_animation.endValue()) == (True, TARGET)


def test_without_notification_animations_a_closed_popup_goes_at_once(popup):
    shown = popup("none")
    shown.slide_in(TARGET)
    shown.slide_out()

    assert (shown.isVisible(), shown.move_animation) == (False, None)
