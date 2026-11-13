"""Log off, shut down and restart announce themselves in a notification at the screen's corner, with Cancel, in every
look: the session takes a while to end when programs are slow to close, and Plasma itself says nothing until then."""

import os
import select
import signal
import subprocess
import time

import dbus
import dbus.service
import pytest
from conftest import load_script
from dbus.mainloop.glib import DBusGMainLoop
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

LOOK = {"style": "2000", "osName": "Fedora Linux 44", "osCompany": "Fedora"}


@pytest.fixture
def notifyd(qt_app, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return load_script("chicago95-notifyd")


@pytest.fixture
def bus_address():
    daemon = subprocess.Popen(
        ["dbus-daemon", "--session", "--nofork", "--print-address"],
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    ready, _, _ = select.select([daemon.stdout], [], [], 5)
    assert ready
    yield daemon.stdout.readline().strip()
    os.killpg(daemon.pid, signal.SIGKILL)
    daemon.wait(timeout=5)


@pytest.fixture
def stack(notifyd, bus_address):
    connection = dbus.bus.BusConnection(bus_address, mainloop=DBusGMainLoop())
    name = dbus.service.BusName(notifyd.INTERFACE, connection)
    stack = notifyd.PopupStack()
    service = notifyd.NotificationService(connection, stack)
    yield stack
    del service, name
    stack.host.close()
    connection.close()


@pytest.fixture
def announce(shutdown, bus_address, stack):
    """Starts announcing a choice; returns the notice and the list its action appends to when it runs."""
    notices = []

    def start(choice, delay_ms=0):
        ran = []
        connection = dbus.bus.BusConnection(bus_address, mainloop=DBusGMainLoop())
        notice = shutdown.SessionEndNotice(connection, choice, LOOK, lambda: ran.append(choice), delay_ms)
        notice.start()
        notices.append((notice, connection))
        return notice, ran

    yield start
    for _notice, connection in notices:
        connection.close()


def wait_until(condition, seconds=2):
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        QApplication.processEvents()
        QTest.qWait(10)
    return condition()


def shown_popup(stack):
    assert wait_until(lambda: len(stack.popups) == 1)
    return next(iter(stack.popups.values()))


@pytest.mark.parametrize(
    ("choice_name", "summary"),
    [
        ("LOG_OFF", "Logging off..."),
        ("SHUT_DOWN", "Fedora Linux is shutting down..."),
        ("RESTART", "Fedora Linux is restarting..."),
    ],
)
def test_notice_names_the_action_and_the_system(shutdown, choice_name, summary):
    assert shutdown.session_end_text(getattr(shutdown, choice_name), LOOK)[0] == summary


def test_notice_says_it_waits_for_programs_to_close(shutdown):
    assert shutdown.session_end_text(shutdown.LOG_OFF, LOOK)[1] == "Waiting for your programs to close."


def test_log_off_shows_a_notice_with_a_cancel_button(shutdown, stack, announce):
    announce(shutdown.LOG_OFF)
    assert [button.text() for button in shown_popup(stack).action_buttons] == ["Cancel"]


def test_notice_carries_the_hint_that_lets_its_cancel_stop_the_logout(shutdown, stack, announce):
    announce(shutdown.LOG_OFF)
    shown_popup(stack)
    assert len(stack.session_end_ids) == 1


def test_action_runs_once_its_delay_has_passed(shutdown, stack, announce):
    _notice, ran = announce(shutdown.SHUT_DOWN, delay_ms=50)
    assert wait_until(lambda: ran == [shutdown.SHUT_DOWN])


def test_cancel_before_the_delay_has_passed_never_runs_the_action(shutdown, stack, announce):
    _notice, ran = announce(shutdown.RESTART, delay_ms=500)
    shown_popup(stack).action_buttons[0].click()
    QTest.qWait(700)
    assert ran == []


def test_notice_finishes_when_its_notification_is_closed(shutdown, stack, announce):
    notice, _ran = announce(shutdown.LOG_OFF)
    finished = []
    notice.finished.connect(lambda: finished.append(True))
    stack.close(shown_popup(stack).notification_id, 3)
    assert wait_until(lambda: finished == [True])


def end_session_on(shutdown, qt_app, bus_address):
    ran = []
    connection = dbus.bus.BusConnection(bus_address, mainloop=DBusGMainLoop())
    QTimer.singleShot(3000, qt_app.quit)
    result = shutdown.end_session(qt_app, connection, shutdown.LOG_OFF, LOOK, lambda: ran.append("logout"), 0)
    connection.close()
    return result, ran


def test_ending_the_session_runs_the_action_and_returns(shutdown, qt_app, bus_address, stack):
    assert end_session_on(shutdown, qt_app, bus_address) == (0, ["logout"])


def test_ending_the_session_without_a_notification_server_still_runs_the_action(shutdown, qt_app, bus_address):
    assert end_session_on(shutdown, qt_app, bus_address) == (0, ["logout"])
