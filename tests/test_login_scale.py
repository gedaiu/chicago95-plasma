"""The login dialog's size: a classic pixel is `scale` screen pixels (Setup writes the session's scale rounded),
whatever device pixel ratio the greeter itself runs at, so it matches the lock screen and the desktop."""

import pytest
from login_theme import login_view
from PySide6.QtCore import QObject


def screen_pixels_per_classic_pixel(view, greeter_ratio):
    view.rootObject().setProperty("screenScale", greeter_ratio)
    return view.rootObject().findChild(QObject, "logonDialog").property("scale") * greeter_ratio


@pytest.mark.parametrize(("scale", "greeter_ratio", "pixels"), [("2", 1, 2), ("2", 2, 2), ("3", 2, 3), ("1", 1.5, 1)])
def test_dialog_draws_a_classic_pixel_as_the_set_scale_in_screen_pixels(qt_app, tmp_path, scale, greeter_ratio, pixels):
    with login_view(qt_app, tmp_path, scale=scale) as view:
        assert screen_pixels_per_classic_pixel(view, greeter_ratio) == pytest.approx(pixels)


def test_dialog_without_a_set_scale_on_a_4k_screen_at_ratio_2_draws_3_screen_pixels(qt_app, tmp_path):
    with login_view(qt_app, tmp_path, size=(1920, 1080), scale="0") as view:
        assert screen_pixels_per_classic_pixel(view, 2) == pytest.approx(3)
