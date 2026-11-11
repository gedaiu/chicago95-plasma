import warnings


def test_hide_emits_no_warning_when_focus_handler_was_never_connected(startmenu, qt_app):
    start_menu = startmenu.StartMenu(qt_app)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        start_menu.hide()

    assert [str(warning.message) for warning in caught] == []
