"""What KSplash shows after an XP Welcome log on: the Welcome screen stays, with only the chosen user's
tile and "Loading your personal settings..." where the password box was, under the hourglass pointer,
until Plasma is up and KWin fades it into the desktop."""

import pytest
from chicago95lunapreviews import copy_screen_trees
from conftest import REPO
from login_theme import overlapping_pairs, shown_texts
from PySide6.QtCore import QObject, Qt
from test_loading_screen_reference import splash_view

LOADING = "Loading your personal settings..."
WELCOME = {"style": "luna", "logonStyle": "luna", "userName": "Ada", "userPicture": "", "desktopColor": "#004E98"}


@pytest.fixture
def welcome(qt_app, tmp_path):
    copy_screen_trees(REPO / "luna", tmp_path / "luna", "splash", "sddm")
    with splash_view(qt_app, tmp_path, booting=False, **WELCOME) as view:
        yield view


def test_after_an_xp_welcome_log_on_the_tile_says_it_is_loading_the_personal_settings(welcome):
    assert LOADING in shown_texts(welcome.rootObject())


def test_after_an_xp_welcome_log_on_the_tile_shows_the_user_who_logged_on(welcome):
    assert "Ada" in shown_texts(welcome.rootObject())


def test_after_an_xp_welcome_log_on_the_caption_and_turn_off_button_are_gone(welcome):
    texts = shown_texts(welcome.rootObject())
    assert [text for text in ("To begin, click your user name", "Turn off computer") if text in texts] == []


def test_after_an_xp_welcome_log_on_no_password_box_is_shown(welcome):
    assert "Type your password" not in shown_texts(welcome.rootObject())


def test_after_an_xp_welcome_log_on_the_pointer_is_the_hourglass(welcome):
    pointer = welcome.rootObject().findChild(QObject, "waitPointer")
    assert pointer.property("cursorShape") == Qt.CursorShape.WaitCursor


def test_after_an_xp_welcome_log_on_no_shown_item_lies_over_another(welcome):
    assert overlapping_pairs(welcome.rootObject()) == []
