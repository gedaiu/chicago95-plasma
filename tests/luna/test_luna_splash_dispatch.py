import shutil

from conftest import REPO
from test_loading_screen_reference import render_splash

WORDMARK_AREA = (150, 100, 500, 330)
BLACK = (0, 0, 0)


def splash_with_luna_trees(folder):
    for tree in ("qml", "splash"):
        shutil.copytree(REPO / "luna" / tree, folder / "luna" / tree)


def lit_pixels(image, area):
    return sum(1 for pixel in image.convert("RGB").crop(area).get_flattened_data() if pixel != BLACK)


def test_splash_qml_draws_the_black_xp_screen_with_its_wordmark_when_style_is_luna(qt_app, tmp_path):
    splash_with_luna_trees(tmp_path)

    image = render_splash(qt_app, tmp_path, style="luna")

    assert (image.convert("RGB").getpixel((2, 2)), lit_pixels(image, WORDMARK_AREA) > 1000) == (BLACK, True)


def test_splash_qml_keeps_the_near_white_page_when_style_is_2000(qt_app, tmp_path):
    image = render_splash(qt_app, tmp_path, style="2000")

    assert image.convert("RGB").getpixel((2, 2)) == (247, 247, 247)
