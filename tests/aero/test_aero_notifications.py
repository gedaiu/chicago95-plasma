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
