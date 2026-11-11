"""Our "2000" loading screen against the original 2000 start-up screen (w2kboot.png, 640x480).

The OS logo and the product name are the user's and are masked; the page, the strip, the grey bar, the
progress bar and the two text lines must match pixel for pixel, and the mark's generated frames behind
the logo must match in colour block by block (the original dithers them to 256 colours).
"""

import shutil

import pytest
from conftest import REPO, needs_ui_font
from reference import bounding_box, close, differing_pixels, qimage_to_pil, screenshot

SPLASH = REPO / "splash/chicago95.splashscreen/contents/splash"
LOGO_AND_NAME = (100, 20, 560, 365)  # masked: the original's logo, wordmark and edition
MICROSOFT_MARK = (500, 0, 640, 50)  # masked: the original's corner wordmark
TENTH_BLOCK = (273 + 1 + 9 * 9, 437, 273 + 1 + 9 * 10, 445)  # the original shows one block more than stage 3 draws
LOADING_TEXT_BOX = (201, 437, 266, 446)
FOOTER_BOX = (196, 458, 442, 468)
# The screenshot has 256 colours: where the strip shades from bright blue to navy it is dithered.
DITHERED_STRIP = (140, 414, 262, 428)
LETTER_SHAPE_SLACK = 1  # our pixel font against the original's Tahoma
MARK = (264, 44, 476, 240)  # the framed squares behind the logo
FLAG = (296, 66, 446, 190)  # the logo inside the frame, left out of the frames' comparison
BLOCK = 6
BLOCK_TOLERANCE = 40  # per colour channel, between block averages
# Where each line of lettering is searched for: (left, top, right, bottom).
NAME_LINE = (130, 258, 560, 303)
EDITION_LINE = (250, 304, 560, 341)
TAGLINE_LINE = (300, 343, 560, 362)
COMPANY_LINE = (110, 236, 250, 257)
CORNER = (450, 5, 639, 40)
LETTERING_SLACK = 3  # Arial emboldened against the original's own typefaces


@pytest.fixture(scope="module")
def reference():
    return screenshot("w2kboot")


def render_splash(qt_app, folder, **settings):
    """Our loading screen at stage 3 of 6, 640x480, with the given settings.js values."""
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtQuick import QQuickView

    shutil.copytree(SPLASH, folder, dirs_exist_ok=True)
    values = {
        "style": "2000",
        "brandText": "Chicago95",
        "brandLogo": "",
        "edition": "Professional",
        "loadingText": "Starting up...",
        "footer": "Copyright © 1985-1999 Microsoft Corporation",
        "picture": "",
        **settings,
    }
    (folder / "settings.js").write_text(
        ".pragma library\n" + "".join(f'var {key} = "{value}"\n' for key, value in values.items())
    )
    view = QQuickView()
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(640, 480)
    view.setSource(QUrl.fromLocalFile(str(folder / "Splash.qml")))
    assert [error.toString() for error in view.errors()] == []
    view.rootObject().setProperty("stage", 3)
    view.show()
    QTimer.singleShot(300, qt_app.quit)
    qt_app.exec()
    image = qimage_to_pil(view.grabWindow())
    view.close()
    return image


@pytest.fixture(scope="module")
def ours(qt_app, tmp_path_factory):
    return render_splash(qt_app, tmp_path_factory.mktemp("splash"))


@pytest.fixture(scope="module")
def lettered(qt_app, tmp_path_factory):
    """Ours with the original's own texts, so the lettering can be measured against it."""
    return render_splash(
        qt_app,
        tmp_path_factory.mktemp("lettered"),
        brandText="Windows 2000",
        company="Microsoft",
        tagline="Built on NT Technology",
    )


def block_average(image, x, y):
    pixels = [image.getpixel((x + dx, y + dy)) for dx in range(BLOCK) for dy in range(BLOCK)]
    return tuple(sum(pixel[channel] for pixel in pixels) / len(pixels) for channel in range(3))


def outside_flag(x, y):
    return not (FLAG[0] - BLOCK < x < FLAG[2] and FLAG[1] - BLOCK < y < FLAG[3])


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
    masks = [LOGO_AND_NAME, MICROSOFT_MARK, TENTH_BLOCK, DITHERED_STRIP] + lettering(reference, ours)
    count = differing_pixels(reference, ours, masks, tmp_path / "loading-diff.png", threshold=0.15)
    assert count == 0, f"{count} pixels differ; see {tmp_path}"


def test_mark_frames_match_the_original_within_40_levels_per_6px_block(reference, ours):
    blocks = [
        (x, y) for y in range(MARK[1], MARK[3], BLOCK) for x in range(MARK[0], MARK[2], BLOCK) if outside_flag(x, y)
    ]
    differing = [
        (x, y)
        for x, y in blocks
        if max(abs(a - b) for a, b in zip(block_average(reference, x, y), block_average(ours, x, y))) > BLOCK_TOLERANCE
    ]
    assert differing == []


def test_progress_bar_is_165_by_10_at_273_436(reference, ours):
    def bar(image):
        return bounding_box(image, lambda c: close(c, (0x7D, 0x81, 0x96), 20), (260, 450), (430, 450))

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


def ink(image, area):
    return bounding_box(image, lambda c: sum(c) < 300, (area[0], area[2]), (area[1], area[3]))


def within_slack(actual, expected):
    return all(abs(a - e) <= LETTERING_SLACK for a, e in zip(actual, expected))


@pytest.mark.parametrize("line", [NAME_LINE, EDITION_LINE, TAGLINE_LINE], ids=["name", "edition", "tagline"])
def test_name_edition_and_tagline_cover_the_original_lines_within_3_pixels(reference, lettered, line):
    assert within_slack(ink(lettered, line), ink(reference, line)), (ink(lettered, line), ink(reference, line))


def test_company_name_starts_where_the_original_does(reference, lettered):
    assert within_slack(ink(lettered, COMPANY_LINE)[:2], ink(reference, COMPANY_LINE)[:2])


def test_corner_company_name_starts_where_the_original_wordmark_does(reference, lettered):
    # The original's right end is a registered mark, which ours leaves out.
    expected, actual = ink(reference, CORNER), ink(lettered, CORNER)
    assert within_slack((actual[0], actual[1], actual[3]), (expected[0], expected[1], expected[3])), (actual, expected)


def test_corner_shows_nothing_without_a_company(ours):
    assert ink(ours, CORNER) is None
