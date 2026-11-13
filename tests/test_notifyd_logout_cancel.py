"""Cancel on Setup's "Logging off..." notification stops the logout: Plasma has no call for that, but KWin asks
through a notification of its own (x-kde-eventId cancellogout) when a program will not close, and its action "1" is
Cancel Logout. The daemon answers that prompt for the user, at once when it is up, or the moment it comes."""

import pytest
from conftest import load_script
from PySide6.QtTest import QTest

SESSION_END = {"x-chicago95-session-end": True}
KWIN_PROMPT = {"x-kde-eventId": "cancellogout"}
KWIN_ACTIONS = [("1", "Cancel Logout"), ("2", "Log Out Anyway")]


@pytest.fixture
def notifyd(qt_app, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return load_script("chicago95-notifyd")


@pytest.fixture
def stack(notifyd):
    stack = notifyd.PopupStack()
    stack.answers = []
    stack.action_invoked.connect(lambda notification_id, key: stack.answers.append((notification_id, key)))
    yield stack
    stack.host.close()


def show(notifyd, stack, notification_id, hints, actions):
    stack.show(notifyd.Notification(notification_id, "app", "", "summary", "", actions, hints, 0))


def press_cancel_on_logging_off(notifyd, stack):
    show(notifyd, stack, 1, SESSION_END, [("cancel", "Cancel")])
    stack.invoke(1, "cancel", False)


def test_cancel_with_kwins_prompt_up_answers_it_with_cancel_logout(notifyd, stack):
    show(notifyd, stack, 2, KWIN_PROMPT, KWIN_ACTIONS)
    press_cancel_on_logging_off(notifyd, stack)
    assert (2, "1") in stack.answers


def test_kwins_prompt_after_cancel_is_answered_with_cancel_logout_at_once(notifyd, stack):
    press_cancel_on_logging_off(notifyd, stack)
    show(notifyd, stack, 2, KWIN_PROMPT, KWIN_ACTIONS)
    QTest.qWait(10)
    assert ((2, "1") in stack.answers, 2 in stack.popups) == (True, False)


def test_kwins_prompt_is_answered_only_after_notify_has_handed_kwin_its_id(notifyd, stack):
    press_cancel_on_logging_off(notifyd, stack)
    show(notifyd, stack, 2, KWIN_PROMPT, KWIN_ACTIONS)
    assert (2, "1") not in stack.answers


def test_kwins_prompt_without_a_cancel_shows_its_buttons(notifyd, stack):
    show(notifyd, stack, 2, KWIN_PROMPT, KWIN_ACTIONS)
    assert (2 in stack.popups, stack.answers) == (True, [])


def test_a_cancel_older_than_a_minute_leaves_the_next_logout_alone(notifyd, stack, monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(notifyd.time, "monotonic", lambda: clock[0])
    press_cancel_on_logging_off(notifyd, stack)
    clock[0] += 61
    show(notifyd, stack, 2, KWIN_PROMPT, KWIN_ACTIONS)
    assert 2 in stack.popups


def test_cancel_on_another_apps_notification_cancels_no_logout(notifyd, stack):
    show(notifyd, stack, 1, {}, [("cancel", "Cancel")])
    stack.invoke(1, "cancel", False)
    show(notifyd, stack, 2, KWIN_PROMPT, KWIN_ACTIONS)
    assert 2 in stack.popups


def test_cancel_logout_on_kwins_prompt_closes_the_logging_off_notification(notifyd, stack):
    show(notifyd, stack, 1, SESSION_END, [("cancel", "Cancel")])
    show(notifyd, stack, 2, KWIN_PROMPT, KWIN_ACTIONS)
    stack.invoke(2, "1", False)
    assert stack.popups == {}
