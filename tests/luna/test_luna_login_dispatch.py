import shutil

from conftest import REPO
from login_theme import render_login
from PIL import ImageChops

from .luna_qml import render_luna_login

SCREEN = (800, 600)
CLASSIC_TEAL = (0, 128, 128)


def theme_with_luna_trees(folder):
    for tree in ("qml", "sddm"):
        shutil.copytree(REPO / "luna" / tree, folder / "theme/luna" / tree)


def differing_pixels(first, second):
    difference = ImageChops.difference(first.convert("RGB"), second.convert("RGB")).convert("L")
    return difference.point(lambda value: 255 if value > 12 else 0).histogram()[255] / (first.width * first.height)


def test_sddm_main_qml_draws_the_luna_screen_when_login_style_is_luna(qt_app, tmp_path):
    theme_with_luna_trees(tmp_path)

    themed = render_login(
        qt_app, tmp_path, size=SCREEN, user="Administrator", users=("Administrator",), loginStyle="luna"
    )

    assert differing_pixels(themed, render_luna_login(qt_app)) < 0.02


def test_sddm_main_qml_keeps_the_classic_teal_desktop_when_login_style_is_classic(qt_app, tmp_path):
    themed = render_login(qt_app, tmp_path, size=SCREEN, loginStyle="classic")

    assert themed.convert("RGB").getpixel((2, 2)) == CLASSIC_TEAL


def test_luna_screen_differs_from_the_classic_dialog(qt_app, tmp_path):
    classic = render_login(qt_app, tmp_path, size=SCREEN, user="Administrator", users=("Administrator",))

    assert differing_pixels(classic, render_luna_login(qt_app)) > 0.5
