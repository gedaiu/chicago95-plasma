"""Clippy against Office's own balloon (tests/references/clippy-letter.png, "It looks like you're writing a letter").

The original is exact pixels: K black, F the balloon's #FFFFCC, a space for transparent. Its balloon is drawn
without smoothing, with 8 pixel stepped corners and a 15 row tail on the left that drops onto Clippy, whose
frame sits 7 pixels in from the balloon's left and 6 rows under its bottom edge.
"""

import io

import pytest
from conftest import REPO, load_script, needs_ui_font
from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice, QPoint, QSize
from PySide6.QtGui import QPixmap

LETTER_TEXT = "It looks like you're writing a letter.\n\nWould you like help?"
ORIGINAL_WIDTH, ORIGINAL_BODY_HEIGHT = 130, 212
ORIGINAL_ASSISTANT_AT = (7, 217)


def mark(colour):
    if colour[3] < 128:
        return " "
    return {(0, 0, 0): "K", (255, 255, 204): "F"}.get(colour[:3], "?")


def rgba(widget):
    """The widget as drawn, its untouched pixels left transparent."""
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    widget.grab().toImage().save(buffer, "PNG")
    return Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGBA")


def marks(image, left, top, width, height):
    return ["".join(mark(image.getpixel((x, y))) for x in range(left, left + width)) for y in range(top, top + height)]


@pytest.fixture(scope="session")
def original():
    return Image.open(REPO / "tests/references/clippy-letter.png").convert("RGBA")


@pytest.fixture(scope="session")
def clippy():
    return load_script("chicago95-clippy")


@pytest.fixture
def balloon(clippy, qt_app):
    import chicago95ui

    balloon = clippy.Balloon(chicago95ui.ui_font())
    balloon.show_tip(LETTER_TEXT, QPoint(300, 400))
    yield balloon
    balloon.hide()


def body_height(balloon, clippy):
    return balloon.height() - clippy.BALLOON_TAIL_ROWS


def test_our_balloon_is_as_wide_as_the_original(balloon):
    assert balloon.width() == ORIGINAL_WIDTH


def test_our_balloon_corners_match_the_originals_pixel_for_pixel(original, balloon, clippy):
    ours, height = rgba(balloon), body_height(balloon, clippy)
    corners = [(0, 0), (ORIGINAL_WIDTH - 8, 0), (0, -8), (ORIGINAL_WIDTH - 8, -8)]
    assert [marks(ours, x, y if y >= 0 else height + y, 8, 8) for x, y in corners] == [
        marks(original, x, y if y >= 0 else ORIGINAL_BODY_HEIGHT + y, 8, 8) for x, y in corners
    ]


def test_our_balloon_edges_are_one_black_pixel_round_a_yellow_body(balloon, clippy):
    ours, height = rgba(balloon), body_height(balloon, clippy)
    edges = {
        "top": marks(ours, 8, 0, ORIGINAL_WIDTH - 16, 2),
        "left": ["".join(row) for row in zip(*marks(ours, 0, 8, 2, height - 16), strict=False)],
        "right": ["".join(row) for row in zip(*marks(ours, ORIGINAL_WIDTH - 2, 8, 2, height - 16), strict=False)],
    }
    assert edges == {
        "top": ["K" * (ORIGINAL_WIDTH - 16), "F" * (ORIGINAL_WIDTH - 16)],
        "left": ["K" * (height - 16), "F" * (height - 16)],
        "right": ["F" * (height - 16), "K" * (height - 16)],
    }


def test_our_balloon_tail_matches_the_originals_pixel_for_pixel(original, balloon, clippy):
    ours, height = rgba(balloon), body_height(balloon, clippy)
    assert marks(ours, 30, height - 1, 20, 16) == marks(original, 30, ORIGINAL_BODY_HEIGHT - 1, 20, 16)


@needs_ui_font
def test_our_balloon_text_ink_starts_where_the_originals_does(original, balloon):
    def first_ink(image):
        def inside_corners(x, y):
            return y < 8 and (x < 8 or x >= ORIGINAL_WIDTH - 8)

        ink = [
            (x, y)
            for y in range(1, 30)
            for x in range(1, ORIGINAL_WIDTH - 1)
            if mark(image.getpixel((x, y))) == "K" and not inside_corners(x, y)
        ]
        return (min(x for x, _ in ink), min(y for _, y in ink))

    assert first_ink(rgba(balloon)) == first_ink(original)


def test_balloon_opens_with_clippy_7_pixels_in_and_6_rows_under_its_body(balloon, clippy):
    balloon.show_tip(LETTER_TEXT, QPoint(500, 400))
    bottom_row = balloon.y() + body_height(balloon, clippy) - 1
    assert (500 - balloon.x(), 400 - bottom_row) == (
        ORIGINAL_ASSISTANT_AT[0],
        ORIGINAL_ASSISTANT_AT[1] - (ORIGINAL_BODY_HEIGHT - 1),
    )


def test_clippy_draws_the_originals_idle_frame_pixel_for_pixel(original, clippy, qt_app):
    animations = clippy.parse_agent_js((REPO / "data/clippy/agent.js").read_text())
    sprites = clippy.SpriteSheet(QPixmap(str(REPO / "data/clippy/map.png")), QSize(124, 93))
    window = clippy.ClippyWindow(animations, sprites, clippy.SoundPlayer({}, True), qt_app.font())
    window.current_frame = animations["Idle1_1"].frames[1]
    ours = rgba(window)
    left, top = ORIGINAL_ASSISTANT_AT
    differing = [
        (x, y)
        for y in range(min(93, original.height - top))
        for x in range(min(124, original.width - left))
        if ours.getpixel((x, y))[3] >= 128
        and ours.getpixel((x, y))[:3] != original.getpixel((left + x, top + y))[:3]
        or ours.getpixel((x, y))[3] < 128
        and mark(original.getpixel((left + x, top + y))) == "?"
    ]
    assert differing == []


def test_right_click_menu_offers_hide_options_choose_assistant_and_animate_like_office(clippy, qt_app):
    animations = clippy.parse_agent_js((REPO / "data/clippy/agent.js").read_text())
    sprites = clippy.SpriteSheet(QPixmap(str(REPO / "data/clippy/map.png")), QSize(124, 93))
    window = clippy.ClippyWindow(animations, sprites, clippy.SoundPlayer({}, True), qt_app.font())
    menu = window.assistant_menu()
    assert [(action.text(), action.isEnabled()) for action in menu.actions()] == [
        ("Hide", True),
        ("Options...", False),
        ("Choose Assistant...", False),
        ("Animate!", True),
        ("", True),
        ("Exit", True),
    ]


@pytest.mark.parametrize(
    "roll, stop_requested, expected",
    [(50, False, 1), (94, False, 1), (95, False, 2), (50, True, 2)],
)
def test_idle_frame_with_95_percent_branch_to_itself_at_roll_returns_frame(clippy, roll, stop_requested, expected):
    animations = clippy.parse_agent_js((REPO / "data/clippy/agent.js").read_text())
    animation = animations["Idle1_1"]
    assert clippy.next_frame_index(animation, 1, stop_requested, roll) == expected
