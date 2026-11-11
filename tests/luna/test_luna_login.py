from pathlib import Path

import pytest
from PIL import Image, ImageChops
from reference import bounding_box, close, screenshot

from .luna_profile import (
    BLURRED_BUDGET,
    RAW_BUDGET,
    blurred_differing_fraction,
    differing_fraction,
    horizontal_profile,
    profile_excess,
    vertical_profile,
)
from .luna_qml import render_luna_login

PREVIEW_DIR = Path(
    "/tmp/claude-1000/-home-gedaiu-workspace-chicago95-plasma/6679116e-4ef6-4478-b441-c6cd1dc95f4a/scratchpad/luna-preview"
)
TOLERANCE = 12
PIXEL_BUDGET = 0.05
TEXT_FREE_COLUMNS = (10, 790)
TOP_BAND = (0, 0, 800, 80)
BOTTOM_BAND = (0, 500, 800, 600)
TOP_BAND_MASKS = []
BOTTOM_BAND_MASKS = [(20, 20, 215, 55), (465, 20, 755, 58), (465, 66, 620, 84)]
LOGIN_MASKS = [
    (225, 225, 395, 325),
    (90, 332, 365, 360),
    (435, 260, 490, 318),
    (496, 258, 612, 300),
    (488, 300, 700, 334),
    (20, 515, 215, 555),
    (460, 515, 760, 595),
]
ALL_COLUMNS = range(800)


def is_frame_colour(colour):
    return colour[0] > 240 and 150 < colour[1] < 250 and colour[2] < 30


def is_white(colour):
    return min(colour) > 245


FIELD_AREA = ((490, 665), (301, 340))


@pytest.fixture(scope="module")
def reference():
    return screenshot("xplogin")


@pytest.fixture(scope="module")
def ours(qt_app):
    return render_luna_login(qt_app)


def band_differing_fraction(reference, ours, area, masks):
    left, top, right, bottom = area
    first, second = reference.crop(area), ours.crop(area)
    for mask in masks:
        first.paste((255, 0, 255), mask)
        second.paste((255, 0, 255), mask)
    channels = [ImageChops.difference(a, b) for a, b in zip(first.split(), second.split(), strict=True)]
    worst = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    histogram = worst.histogram()
    return sum(histogram[TOLERANCE + 1 :]) / ((right - left) * (bottom - top))


def tolerated(reference_profile, our_profile):
    return profile_excess(reference_profile, our_profile) <= TOLERANCE


def test_screen_is_800_by_600_like_the_reference(reference, ours):
    assert ours.size == reference.size == (800, 600)


@pytest.mark.parametrize("x", TEXT_FREE_COLUMNS)
def test_text_free_column_profile_matches_the_reference_within_12(reference, ours, x):
    rows = range(600)
    assert tolerated(vertical_profile(reference, [x], rows), vertical_profile(ours, [x], rows))


@pytest.mark.parametrize(
    "rows", [[78], [79], [504], [505]], ids=["top rule 78", "top rule 79", "bottom rule 504", "bottom rule 505"]
)
def test_rule_row_profile_matches_the_reference_within_12(reference, ours, rows):
    assert tolerated(horizontal_profile(reference, ALL_COLUMNS, rows), horizontal_profile(ours, ALL_COLUMNS, rows))


def test_bottom_band_profile_between_the_texts_matches_the_reference_within_12(reference, ours):
    rows = range(562, 575)
    assert tolerated(horizontal_profile(reference, ALL_COLUMNS, rows), horizontal_profile(ours, ALL_COLUMNS, rows))


def test_divider_profile_matches_the_reference_within_12(reference, ours):
    rows = range(80, 504)
    assert tolerated(vertical_profile(reference, [398], rows), vertical_profile(ours, [398], rows))


def test_glow_profile_across_the_top_left_matches_the_reference_within_12(reference, ours):
    columns, rows = range(0, 300), range(100, 108)
    assert tolerated(horizontal_profile(reference, columns, rows), horizontal_profile(ours, columns, rows))


def test_glow_profile_down_the_left_matches_the_reference_within_12(reference, ours):
    columns, rows = range(40, 80), range(80, 330)
    assert tolerated(vertical_profile(reference, columns, rows), vertical_profile(ours, columns, rows))


def test_tile_fill_profile_along_its_top_matches_the_reference_within_12(reference, ours):
    columns, rows = range(430, 790), range(256, 260)
    assert tolerated(horizontal_profile(reference, columns, rows), horizontal_profile(ours, columns, rows))


def test_divider_sits_on_column_398(reference, ours):
    def divider(image):
        return [x for x in range(380, 420) if image.getpixel((x, 300))[0] > 120]

    assert divider(ours) == divider(reference) == [398]


def test_tile_frame_box_is_within_2_pixels_of_the_reference(reference, ours):
    expected, actual = (bounding_box(image, is_frame_colour, (420, 500), (240, 340)) for image in (reference, ours))
    assert all(abs(a - e) <= 2 for a, e in zip(actual, expected, strict=True)), (actual, expected)


def test_password_field_box_is_the_reference_white_box(reference, ours):
    expected, actual = (bounding_box(image, is_white, *FIELD_AREA) for image in (reference, ours))
    assert actual == expected == (496, 303, 656, 329)


def test_password_row_hides_while_no_user_is_selected(qt_app):
    image = render_luna_login(qt_app, properties={"selectedName": "nobody"})
    assert bounding_box(image, is_white, *FIELD_AREA) is None


def test_top_band_matches_the_reference_within_5_percent_of_pixels(reference, ours):
    assert band_differing_fraction(reference, ours, TOP_BAND, TOP_BAND_MASKS) <= PIXEL_BUDGET


def test_bottom_band_matches_the_reference_outside_its_text_within_5_percent_of_pixels(reference, ours):
    assert band_differing_fraction(reference, ours, BOTTOM_BAND, BOTTOM_BAND_MASKS) <= PIXEL_BUDGET


def test_shutdown_screen_bands_match_xpshuttingdown_within_5_percent(qt_app):
    expected = screenshot("xpshuttingdown")
    image = render_luna_login(qt_app, properties={"shuttingDown": True})
    top = band_differing_fraction(expected, image, TOP_BAND, [])
    bottom = band_differing_fraction(expected, image, BOTTOM_BAND, [])
    assert (top <= PIXEL_BUDGET, bottom <= PIXEL_BUDGET) == (True, True)


def test_shutdown_screen_has_no_divider_and_no_tile(qt_app):
    image = render_luna_login(qt_app, properties={"shuttingDown": True})
    assert (image.getpixel((398, 300)), bounding_box(image, is_white, (600, 665), FIELD_AREA[1])) == (
        image.getpixel((200, 300)),
        None,
    )


def test_screen_scales_with_height(qt_app):
    image = render_luna_login(qt_app, size=(1600, 1200))
    probes = {(10, 100): (0, 48, 156), (10, 155): (0, 48, 156), (10, 1100): (57, 52, 173), (1590, 1100): (0, 48, 156)}
    assert [point for point, colour in probes.items() if not close(image.getpixel(point), colour)] == []


def test_masked_login_screen_matches_the_reference_within_budget(reference, ours):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    assert differing_fraction(reference, ours, LOGIN_MASKS, PREVIEW_DIR / "login-diff.png") <= RAW_BUDGET


def test_blurred_masked_login_screen_matches_the_blurred_reference_within_budget(reference, ours):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    assert (
        blurred_differing_fraction(reference, ours, LOGIN_MASKS, PREVIEW_DIR / "login-blur-diff.png") <= BLURRED_BUDGET
    )


def test_preview_compares_the_login_screen_with_the_reference(reference, ours):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (1600, 600))
    sheet.paste(ours, (0, 0))
    sheet.paste(reference, (800, 0))
    sheet.save(PREVIEW_DIR / "login-compare.png")
    assert sheet.size == (1600, 600)
