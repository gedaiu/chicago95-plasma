from pathlib import Path

import pytest
from PIL import Image
from reference import bounding_box, screenshot

from .luna_profile import (
    BLURRED_BUDGET,
    RAW_BUDGET,
    blurred_differing_fraction,
    differing_fraction,
    profile_excess,
    vertical_profile,
)
from .luna_qml import render_luna_splash

PREVIEW_DIR = Path(
    "/tmp/claude-1000/-home-gedaiu-workspace-chicago95-plasma/6679116e-4ef6-4478-b441-c6cd1dc95f4a/scratchpad/luna-preview"
)
TOLERANCE = 12
BLOCK_COLUMNS = [range(308, 313), range(316, 321), range(324, 329)]
SPLASH_MASKS = [(200, 115, 460, 305), (15, 425, 170, 465), (540, 435, 640, 465)]

LOGO_AREA = ((150, 500), (100, 330))
TROUGH_AREA = ((240, 400), (340, 375))
BLOCK_AREA = ((250, 400), (340, 375))
FOOTER_AREA = ((10, 260), (420, 470))
BLOCK_ROWS = range(354, 363)
TROUGH_ROWS = range(349, 369)


def is_lit(colour):
    return max(colour) > 60


def is_trough_edge(colour):
    return max(colour) > 50


def is_block_blue(colour):
    return colour[2] > 150 and colour[0] < 150


def is_footer_ink(colour):
    return max(colour) > 100


def centre(box):
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


@pytest.fixture(scope="module")
def reference():
    return screenshot("xpsplash")


@pytest.fixture(scope="module")
def ours(qt_app):
    return render_luna_splash(qt_app)


def test_screen_is_640_by_480_black_at_the_corners(reference, ours):
    assert (ours.size, ours.getpixel((2, 2)), ours.getpixel((637, 2))) == (reference.size, (0, 0, 0), (0, 0, 0))


def test_logo_centre_is_within_2_pixels_of_the_reference(reference, ours):
    expected, actual = (centre(bounding_box(image, is_lit, *LOGO_AREA)) for image in (reference, ours))
    assert (abs(actual[0] - expected[0]) <= 2, abs(actual[1] - expected[1]) <= 2) == (True, True), (actual, expected)


def test_trough_box_equals_the_reference_box(reference, ours):
    expected, actual = (bounding_box(image, is_trough_edge, *TROUGH_AREA) for image in (reference, ours))
    assert actual == expected == (255, 351, 380, 365)


def test_blocks_cover_the_reference_box_when_the_sweep_is_half_way(reference, ours):
    expected, actual = (bounding_box(image, is_block_blue, *BLOCK_AREA) for image in (reference, ours))
    assert actual == expected == (307, 354, 328, 362)


@pytest.mark.parametrize("columns", BLOCK_COLUMNS, ids=["first block", "second block", "third block"])
def test_block_profile_matches_the_reference_within_12(reference, ours, columns):
    rows = range(353, 364)
    assert (
        profile_excess(vertical_profile(reference, columns, rows), vertical_profile(ours, columns, rows)) <= TOLERANCE
    )


def test_trough_profile_down_its_left_part_matches_the_reference_within_12(reference, ours):
    columns = range(260, 300)
    assert (
        profile_excess(vertical_profile(reference, columns, TROUGH_ROWS), vertical_profile(ours, columns, TROUGH_ROWS))
        <= TOLERANCE
    )


@pytest.mark.parametrize("step", range(18))
def test_each_step_matches_the_english_sp3_vm_capture(qt_app, step):
    frame = render_luna_splash(qt_app, properties={"phase": (step + 0.5) / 18})
    with Image.open(Path(__file__).parents[1] / "references/xp-sp3-boot-bar.png") as strip:
        expected = strip.crop((0, step * 15, 126, (step + 1) * 15)).convert("RGB")
    assert frame.crop((255, 351, 381, 366)).tobytes() == expected.tobytes()


def test_blocks_are_clipped_inside_the_trough_at_the_start_of_the_sweep(qt_app):
    image = render_luna_splash(qt_app, properties={"phase": 0})
    assert bounding_box(image, is_block_blue, *BLOCK_AREA) is None


def test_footer_starts_at_the_reference_column_and_stays_grey(reference, ours):
    expected, actual = (bounding_box(image, is_footer_ink, *FOOTER_AREA) for image in (reference, ours))
    assert abs(actual[0] - expected[0]) <= 2 and abs(actual[1] - expected[1]) <= 3, (actual, expected)


def test_footer_text_is_not_pure_white(ours):
    box = bounding_box(ours, is_footer_ink, *FOOTER_AREA)
    assert max(ours.getpixel((x, y))[0] for x in range(box[0], box[2]) for y in range(box[1], box[3])) == 239


def test_layout_centres_on_a_wider_screen(qt_app, reference):
    image = render_luna_splash(qt_app, size=(1280, 480))
    box = bounding_box(image, is_trough_edge, (500, 780), (340, 375))
    assert box == (255 + 320, 351, 380 + 320, 365)


def test_masked_splash_matches_the_reference_within_budget(reference, ours):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    assert differing_fraction(reference, ours, SPLASH_MASKS, PREVIEW_DIR / "splash-diff.png") <= RAW_BUDGET


def test_blurred_masked_splash_matches_the_blurred_reference_within_budget(reference, ours):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    assert (
        blurred_differing_fraction(reference, ours, SPLASH_MASKS, PREVIEW_DIR / "splash-blur-diff.png")
        <= BLURRED_BUDGET
    )


def test_preview_compares_the_splash_with_the_reference(reference, ours):
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (1280, 480))
    sheet.paste(ours, (0, 0))
    sheet.paste(reference, (640, 0))
    sheet.save(PREVIEW_DIR / "splash-compare.png")
    assert sheet.size == (1280, 480)


def test_live_sweep_visits_the_native_frames_at_the_sp3_rate(qt_app):
    from time import monotonic

    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtQuick import QQuickView
    from reference import qimage_to_pil

    with Image.open(Path(__file__).parents[1] / "references/xp-sp3-boot-bar.png") as strip:
        frames = {strip.crop((0, i * 15, 126, (i + 1) * 15)).convert("RGB").tobytes(): i for i in range(18)}
    view = QQuickView()
    view.setSource(QUrl.fromLocalFile(str(Path(__file__).parent / "harness/LunaSplashHarness.qml")))
    view.show()
    seen = []

    def sample():
        bar = qimage_to_pil(view.grabWindow()).crop((255, 351, 381, 366))
        state = frames.get(bar.tobytes())
        if not seen or state != seen[-1][0]:
            seen.append((state, monotonic()))

    timer = QTimer()
    timer.timeout.connect(sample)
    try:
        view.rootObject().setProperty("animated", True)
        timer.start(20)
        QTimer.singleShot(3700, qt_app.quit)
        qt_app.exec()
    finally:
        timer.stop()
        view.close()

    starts = [i for i, (state, _) in enumerate(seen) if state == 0]
    begin, end = starts[-2:]
    assert [state for state, _ in seen[begin:end]] == list(range(18))
    # The VM repeated the same state after 1.67–1.70 s. Allow two capture intervals.
    assert seen[end][1] - seen[begin][1] == pytest.approx(1.688, abs=0.05)
