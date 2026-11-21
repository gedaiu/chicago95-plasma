"""A wrong password on the login dialog. Windows 2000 answers with a modal "Logon Message" box over a
disabled dialog (Microsoft KB 258289 quotes its text); the 9x dialog keeps its line of text on a row of its
own. Nothing on any state of the dialog lies over anything else (tests/login_theme.overlapping_pairs)."""

import pytest
from chicago95lunapreviews import copy_screen_trees
from conftest import REPO
from login_theme import login_view, overlapping_pairs, render_login
from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtTest import QTest

W2K_LOGON_MESSAGE = (
    "The system could not log you on. Make sure your User name and domain are correct, then type your "
    "password again. Letters in passwords must be typed using the correct case. Make sure that Caps Lock is "
    "not accidentally on."
)
DIALOG_STATES = {
    "classic": {"loginStyle": "classic"},
    "classic with options": {"loginStyle": "classic", "show_options": True},
    "classic after a wrong password": {"loginStyle": "classic", "failed": True},
    "2000": {"loginStyle": "2000"},
    "2000 with options": {"loginStyle": "2000", "show_options": True},
    "2000 with caps lock on": {"loginStyle": "2000", "caps_lock": True},
    "2000 after a wrong password": {"loginStyle": "2000", "failed": True},
    "2000 with options after a wrong password": {"loginStyle": "2000", "show_options": True, "failed": True},
}


def child(view, name):
    return view.rootObject().findChild(QObject, name)


@pytest.mark.parametrize("options", DIALOG_STATES.values(), ids=DIALOG_STATES.keys())
def test_no_shown_item_of_the_login_lies_over_another(qt_app, tmp_path, options):
    with login_view(qt_app, tmp_path, **options) as view:
        assert overlapping_pairs(view.rootObject()) == []


WELCOME_STATES = {
    "xp welcome": {},
    "xp welcome after a wrong password": {"failed": True},
    "xp welcome with caps lock on": {"caps_lock": True},
    "xp welcome after a wrong password with caps lock on": {"failed": True, "caps_lock": True},
}


@pytest.mark.parametrize("options", WELCOME_STATES.values(), ids=WELCOME_STATES.keys())
def test_no_shown_item_of_the_xp_welcome_login_lies_over_another(qt_app, tmp_path, options):
    copy_screen_trees(REPO / "luna", tmp_path / "theme/luna", "sddm")
    with login_view(qt_app, tmp_path, size=(800, 600), loginStyle="luna", **options) as view:
        assert overlapping_pairs(view.rootObject()) == []


def test_a_wrong_2000_password_shows_the_logon_message_box(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, loginStyle="2000", failed=True) as view:
        assert child(view, "logonMessage").isVisible()


def test_the_logon_message_box_is_titled_logon_message(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, loginStyle="2000", failed=True) as view:
        assert child(view, "logonMessage").property("title") == "Logon Message"


def test_the_logon_message_box_says_what_windows_2000_says(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, loginStyle="2000", failed=True) as view:
        assert child(view, "logonMessage").property("text") == W2K_LOGON_MESSAGE


def test_the_logon_message_box_ok_button_has_the_focus(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, loginStyle="2000", failed=True) as view:
        assert child(view, "logonMessageOk").hasActiveFocus()


def test_the_login_dialog_is_disabled_behind_the_logon_message_box(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, loginStyle="2000", failed=True) as view:
        assert child(view, "logonDialog").isEnabled() is False


def test_return_on_the_logon_message_box_closes_it(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, loginStyle="2000", failed=True) as view:
        QTest.keyClick(view, Qt.Key_Return)
        assert child(view, "logonMessage").isVisible() is False


def test_closing_the_logon_message_box_gives_the_password_field_the_focus(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, loginStyle="2000", failed=True) as view:
        QTest.keyClick(view, Qt.Key_Return)
        assert child(view, "passwordInput").hasActiveFocus()


def test_a_wrong_2000_password_draws_no_dark_red_text(qt_app, tmp_path):
    image = render_login(qt_app, tmp_path, loginStyle="2000", failed=True)
    assert (0x80, 0, 0) not in {colour for _count, colour in image.convert("RGB").getcolors(1 << 24)}


def test_a_wrong_classic_password_shows_no_logon_message_box(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, loginStyle="classic", failed=True) as view:
        assert child(view, "logonMessage").isVisible() is False


def test_a_wrong_classic_password_shows_the_line_under_the_fields(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, loginStyle="classic", failed=True) as view:
        assert child(view, "failureLine").property("text") == "The password is incorrect. Try again."


def test_aero_login_rejects_a_password_and_leaves_the_field_ready_for_retry(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, loginStyle="aero", failed=True) as view:
        field = child(view, "aeroPassword")
        assert (child(view, "logonDialog").isVisible(), field.hasActiveFocus(), field.property("text")) == (
            False,
            True,
            "",
        )


def test_aero_centres_the_225_pixel_password_box_below_the_account_portrait(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, size=(1024, 768), loginStyle="aero") as view:
        field = child(view, "aeroPassword")
        assert field.width() == 225
        assert abs(field.mapToScene(QPointF(0, 0)).x() + field.width() / 2 - view.width() / 2) <= 0.5


def test_aero_power_arrow_opens_the_menu_without_requesting_shutdown(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, size=(1024, 768), loginStyle="aero") as view:
        shutdown = child(view, "aeroShutdown")
        arrow = child(view, "aeroPowerOptions")
        menu = child(view, "aeroPowerMenu")
        requests = []
        view.rootContext().contextProperty("sddm").powerRequested.connect(requests.append)
        for control, x, width in [(shutdown, 932, 38), (arrow, 970, 20)]:
            assert control.mapToScene(QPointF(0, 0)) == QPointF(x, 706)
            assert control.width() == width and control.height() == 28
        QTest.mouseClick(view, Qt.LeftButton, pos=arrow.mapToScene(QPointF(10, 14)).toPoint())
        assert menu.property("visible") and not requests
        QTest.keyClick(view, Qt.Key_Down)
        QTest.keyClick(view, Qt.Key_Return)
        QTest.qWait(200)
        assert requests == ["Restart"]
        QTest.mouseClick(view, Qt.LeftButton, pos=shutdown.mapToScene(QPointF(19, 14)).toPoint())
        assert requests == ["Restart", "Power off"]


def test_aero_ease_of_access_enlarges_the_credentials_without_submitting(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, size=(1024, 768), loginStyle="aero") as view:
        password = child(view, "aeroPassword")
        from PySide6.QtGui import QFontDatabase

        expected = "Segoe UI" if "Segoe UI" in QFontDatabase.families() else "Selawik"
        assert password.property("font").family() == expected
        switch = child(view, "aeroSwitchUser")
        before = password.height()
        normal_switch = view.grabWindow().copy(switch.mapRectToScene(switch.boundingRect()).toRect())
        options = child(view, "aeroAccessibility")
        QTest.mouseClick(view, Qt.LeftButton, pos=options.mapToScene(QPointF(10, 10)).toPoint())
        QTest.keyClick(view, Qt.Key_Down)
        QTest.keyClick(view, Qt.Key_Return)
        QTest.qWait(100)
        assert password.height() > before
        large_switch = view.grabWindow().copy(switch.mapRectToScene(switch.boundingRect()).toRect())
        assert large_switch.height() > normal_switch.height()
        assert large_switch.scaled(normal_switch.size()) != normal_switch


def test_aero_switch_user_keeps_long_account_names_inside_their_tiles(qt_app, tmp_path):
    name = "A very long account display name for a shared computer"
    with login_view(qt_app, tmp_path, size=(640, 480), loginStyle="aero", user=name, users=(name, "Guest")) as view:
        switch = child(view, "aeroSwitchUser")
        QTest.mouseClick(view, Qt.LeftButton, pos=switch.mapToScene(QPointF(12, 12)).toPoint())
        QTest.qWait(60)

        def visible_items(item):
            if item.isVisible():
                yield item
                for inner in item.childItems():
                    yield from visible_items(inner)

        label = next(item for item in visible_items(view.rootObject()) if item.property("text") == name)
        assert label.property("truncated") is True
        # Render the actual account chooser at its small-screen size.
        assert not view.grabWindow().isNull()
