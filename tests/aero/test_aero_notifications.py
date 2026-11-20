from conftest import load_script
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy, QTest


def test_aero_balloon_uses_the_summary_and_its_close_button_dismisses(qt_app, monkeypatch):
    daemon = load_script("chicago95-notifyd")
    monkeypatch.setattr(daemon.chicago95ui, "look_settings", lambda: {"widgetStyle": "aero"})
    popup = daemon.NotificationPopup(daemon.Notification(1, "Mail", "", "New message", "Hello", [], {}, 0))
    try:
        popup.show()
        assert popup.title_bar.title_label.text() == "New message"
        assert not popup.summary_label.isVisible()
        assert popup.testAttribute(Qt.WA_TranslucentBackground)
        dismissed = QSignalSpy(popup.dismissed)
        QTest.mouseClick(popup.title_bar.close_button, Qt.LeftButton)
        assert dismissed.at(0) == [daemon.CLOSED_DISMISSED]
    finally:
        popup.close()


def test_repeat_keeps_one_balloon_in_place_until_the_renewed_timeout(qt_app, monkeypatch):
    from types import SimpleNamespace

    daemon = load_script("chicago95-notifyd")
    monkeypatch.setattr(daemon.chicago95ui, "look_settings", lambda: {"widgetStyle": "aero"})
    monkeypatch.setattr(daemon, "motion_for", lambda ms: ("none", 0))
    stack = daemon.PopupStack()
    service = SimpleNamespace(stack=stack, last_id=0)
    closed = QSignalSpy(stack.closed)

    def send(app="Mail", body="Hello", timeout=600):
        return daemon.NotificationService.Notify(service, app, 0, "", "New message", body, [], {}, timeout)

    try:
        first = send()
        popup = stack.popups[first]
        QTest.qWait(35)
        before = stack.host.grab().toImage()
        # Approach the old deadline without relying on the host's timer precision.
        popup.expiry_timer.start(30)
        assert send() == first
        QTest.qWait(60)
        assert list(stack.popups.values()) == [popup]
        assert stack.host.grab().toImage() == before
        assert 0 < popup.expiry_timer.remainingTime() <= 650
        assert not closed.count()
        assert closed.wait(1200)
        assert closed.at(0) == [first, daemon.CLOSED_EXPIRED]
        assert send() != first
        assert len({send(), send(app="Chat"), send(body="Other message")}) == 3
    finally:
        stack.host.close()
