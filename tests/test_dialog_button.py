import chicago95ui


def test_dialog_button_is_75_by_23_with_its_caption(qt_app):
    button = chicago95ui.dialog_button("OK")

    assert ((button.width(), button.height()), button.text(), button.isEnabled()) == ((75, 23), "OK", True)


def test_dialog_button_can_start_disabled(qt_app):
    assert chicago95ui.dialog_button("Apply", enabled=False).isEnabled() is False
