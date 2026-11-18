"""Setup's full-screen preview of the login screen closes with Escape; the real login screen never does."""

import pytest
from login_theme import login_view
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest


def quits_on_escape(app, folder, **settings):
    with login_view(app, folder, **settings) as view:
        asked = []
        view.engine().quit.connect(lambda: asked.append(True))
        QTest.keyClick(view, Qt.Key_Escape)
        return bool(asked)


@pytest.mark.parametrize(("settings", "quits"), [({"closeOnEscape": "true"}, True), ({}, False)])
def test_escape_closes_the_login_screen_only_when_setups_preview_asks_for_it(qt_app, tmp_path, settings, quits):
    assert quits_on_escape(qt_app, tmp_path, **settings) is quits
