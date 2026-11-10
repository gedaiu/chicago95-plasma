"""Our "2000" loading screen against the original 2000 start-up screen (w2kboot.png, 640x480).

The logo and the product name are other artwork on purpose and are masked; the page, the strip,
the grey bar, the progress bar and the two text lines must match.
"""
import shutil
from pathlib import Path

import pytest

from conftest import needs_ui_font

from conftest import REPO
from reference import bounding_box, close, differing_pixels, qimage_to_pil, screenshot

SPLASH = REPO / "splash/chicago95.splashscreen/contents/splash"
LOGO_AND_NAME = (100, 20, 560, 365)        # masked: the original's logo, wordmark and edition
MICROSOFT_MARK = (500, 0, 640, 50)         # masked: the original's corner wordmark
LATER_BLOCKS = (273 + 1 + 9 * 9, 436, 438, 446)  # the original shows one block more than stage 3 draws
LOADING_TEXT_BOX = (201, 437, 266, 446)
FOOTER_BOX = (196, 458, 442, 468)
# The screenshot has 256 colours: where the strip shades from bright blue to navy it is dithered.
DITHERED_STRIP = (140, 414, 262, 428)
LETTER_SHAPE_SLACK = 1                     # our pixel font against the original's Tahoma


@pytest.fixture(scope="module")
def reference():
    return screenshot("w2kboot")


@pytest.fixture(scope="module")
def ours(qt_app, tmp_path_factory):
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtQuick import QQuickView
    splash = tmp_path_factory.mktemp("splash")
    shutil.copytree(SPLASH, splash, dirs_exist_ok=True)
    (splash / "settings.js").write_text(
        '.pragma library\nvar style = "2000"\nvar brandText = "Chicago95"\nvar brandLogo = ""\n'
        'var edition = "Professional"\nvar loadingText = "Starting up..."\n'
        'var footer = "Copyright © 1985-1999 Microsoft Corporation"\nvar picture = ""\n')
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(640, 480)
    view.setSource(QUrl.fromLocalFile(str(splash / "Splash.qml")))
    assert [error.toString() for error in view.errors()] == []
    view.rootObject().setProperty("stage", 3)
    view.show()
    QTimer.singleShot(300, qt_app.quit)
    qt_app.exec()
    image = qimage_to_pil(view.grabWindow())
    view.close()
    return image


def ink_box(image, box):
    return bounding_box(image, lambda c: sum(c) < 200, (box[0] - 30, box[2] + 3), (box[1] - 4, box[3] + 4))


def lettering(reference, ours):
    """Text boxes of both renders: letter shapes differ (another font); their placement is tested separately."""
    boxes = []
    for box in (LOADING_TEXT_BOX, FOOTER_BOX):
        for image in (reference, ours):
            found = ink_box(image, box)
            boxes.append((found[0] - 1, found[1] - 1, found[2] + 2, found[3] + 2))
    return boxes


@needs_ui_font
def test_page_strip_and_bar_match_the_original_outside_logo_and_name(reference, ours, tmp_path):
    masks = [LOGO_AND_NAME, MICROSOFT_MARK, LATER_BLOCKS, DITHERED_STRIP] + lettering(reference, ours)
    count = differing_pixels(reference, ours, masks, tmp_path / "loading-diff.png", threshold=0.15)
    assert count == 0, f"{count} pixels differ; see {tmp_path}"


def test_progress_bar_is_165_by_10_at_273_436(reference, ours):
    def bar(image):
        return bounding_box(image, lambda c: close(c, (0x7d, 0x81, 0x96), 20), (260, 450), (430, 450))
    assert bar(ours)[:2] == bar(reference)[:2] == (273, 436)


@needs_ui_font
def test_loading_text_sits_where_the_original_puts_it(reference, ours):
    expected, actual = ink_box(reference, LOADING_TEXT_BOX), ink_box(ours, LOADING_TEXT_BOX)
    assert actual[1] == expected[1] and abs(actual[3] - expected[3]) <= LETTER_SHAPE_SLACK, (actual, expected)


@needs_ui_font
def test_footer_is_centred_on_the_same_line(reference, ours):
    expected, actual = ink_box(reference, FOOTER_BOX), ink_box(ours, FOOTER_BOX)
    assert (actual[1], actual[3]) == (expected[1], expected[3])
    assert abs((actual[0] + actual[2]) / 2 - (expected[0] + expected[2]) / 2) <= 2
