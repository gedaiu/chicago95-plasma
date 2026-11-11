import pytest
from PIL import Image
from PySide6.QtWidgets import QStyle
from reference import qimage_to_pil

from . import luna_states
from .luna_tools_support import reference, save_preview

TRACK_COLUMNS = range(577, 593)
TRACK_ROWS = range(80, 350, 30)
STEPPER_ARROW_ROWS = range(54, 68)
TOLERANCE = 8


@pytest.fixture(scope="module")
def xp_notepad():
    return reference("xpnotepad.png")


@pytest.fixture(scope="module")
def our_scroll_bar(qt_app):
    import chicago95luna

    image = luna_states.scroll_bar(chicago95luna.LunaStyle(), chicago95luna.luna_palette(), "disabled", QStyle.SC_None)
    return qimage_to_pil(image).convert("RGB")


def channel_distance(first, second):
    return max(abs(a - b) for a, b in zip(first, second, strict=True))


def test_disabled_scroll_bar_trough_columns_match_the_xp_notepad_trough(xp_notepad, our_scroll_bar):
    save_preview(
        "scrollbar",
        our_scroll_bar.resize((17 * 3, 120 * 3), Image.NEAREST),
        xp_notepad.crop((570, 40, 600, 160)).resize((90, 360), Image.NEAREST),
    )
    distances = [
        channel_distance(
            our_scroll_bar.getpixel((column - TRACK_COLUMNS.start, 60)), xp_notepad.getpixel((column, row))
        )
        for column in TRACK_COLUMNS
        for row in TRACK_ROWS
    ]
    assert max(distances) <= TOLERANCE


def test_disabled_stepper_arrow_is_the_xp_notepad_disabled_arrow_grey(xp_notepad, our_scroll_bar):
    reference_arrow = {xp_notepad.getpixel((x, y)) for x in range(577, 593) for y in STEPPER_ARROW_ROWS}
    ours = {our_scroll_bar.getpixel((x, y)) for x in range(17) for y in range(17)}
    assert (0xC9, 0xC9, 0xC2) in reference_arrow and (0xC9, 0xC9, 0xC2) in ours


def test_disabled_stepper_face_is_within_the_notepad_stepper_gradient(xp_notepad, our_scroll_bar):
    reference_face = xp_notepad.getpixel((583, 56))
    assert channel_distance(our_scroll_bar.getpixel((8, 3)), reference_face) <= 12
