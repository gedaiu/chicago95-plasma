"""Our window decoration (title bars, borders, corners, caption buttons) against the originals' windows.

The decoration is the Aurorae theme that aurorae/make_chicago95_aurorae.py writes with each look's
colours, drawn by tests/aurorae_model.py the way KWin draws it, at each original window's size. The
frame, corners and buttons must match pixel for pixel outside the window icon, the caption and the
client area; the title's colours are compared column by column (the 1998 screenshot is dithered to 256
colours, the 2000 ones to 16-bit colour); the caption must start where the original's does. Dialogs
in the originals have a 3px frame where KWin gives every window the same one, so of those only the
title and buttons are compared.
"""
import pytest

from aurorae_model import Window, build_theme
from conftest import needs_ui_font
from reference import close, differing_pixels, screenshot

# id: (look, screenshot, frame box (left, top, right, bottom) inclusive, active, caption, the box of the
# window covering part of it in the screenshot)
WINDOWS = {
    "1995 active": ("1995", "win95desktop3", (213, 207, 636, 444), True, "Windows", None),
    "1995 inactive": ("1995", "win95desktop3", (130, 94, 581, 284), False, "My Folder", (213, 207, 636, 444)),
    "1998 inactive": ("1998", "win98notepad", (6, 6, 410, 364), False, "Untitled - Notepad", (123, 189, 523, 307)),
    "2000 active": ("2000", "w2kadmin", (280, 155, 627, 433), True, "Administrative Tools", None),
    "2000 inactive": ("2000", "w2kadmin", (2, 2, 534, 392), False, "Computer Management", (280, 155, 627, 433)),
    "2000 active, file browser": ("2000", "w2kfilebrowser", (85, 15, 636, 430), True, "My Computer", None),
}
BORDER, TOP = 4, 22
ICON = (6, 5, 22, 21)
CAPTION_LEFT = 24
BUTTONS_WIDTH = 6 + 16 + 16 + 18          # right inset, minimize, maximize, close
COLUMN_STEP, COLUMN_TOLERANCE = 12, 24


@pytest.fixture(scope="module")
def themes(qt_app, tmp_path_factory):
    return {look: build_theme(tmp_path_factory.mktemp(f"aurorae-{look}"), look) for look in ("1995", "1998", "2000")}


def original_and_ours(themes, window_id):
    look, name, (left, top, right, bottom), active, caption, _covered = WINDOWS[window_id]
    original = screenshot(name).crop((left, top, right + 1, bottom + 1))
    ours = Window(themes[look], original.width, original.height, active, caption).render()
    return original, ours


def title_columns(image, left, right):
    """Average colour of the title band's columns from left to right, every COLUMN_STEP pixels."""
    columns = []
    for x in range(left, right, COLUMN_STEP):
        pixels = [image.getpixel((x, y)) for y in range(BORDER, TOP)]
        columns.append(tuple(sum(pixel[channel] for pixel in pixels) / len(pixels) for channel in range(3)))
    return columns


@pytest.mark.parametrize("window_id", WINDOWS)
def test_frame_corners_and_buttons_match_the_original(themes, window_id, tmp_path):
    original, ours = original_and_ours(themes, window_id)
    w, h = original.size
    masks = [(BORDER, TOP, w - BORDER, h - BORDER),           # client area
             ICON,                                            # the application's icon
             (CAPTION_LEFT, BORDER, w - BUTTONS_WIDTH, TOP)]  # caption and the title behind it (compared by column)
    left, top, _right, _bottom = WINDOWS[window_id][2]
    covered = WINDOWS[window_id][5]
    if covered:
        masks.append((covered[0] - left, covered[1] - top, covered[2] - left + 1, covered[3] - top + 1))
    count = differing_pixels(original, ours, masks, tmp_path / "window-diff.png", threshold=0.12)
    assert count == 0, f"{count} pixels differ; see {tmp_path}"


@pytest.mark.parametrize("window_id", WINDOWS)
def test_title_colours_match_the_original_column_by_column(themes, window_id):
    original, ours = original_and_ours(themes, window_id)
    # Right of the caption, left of the buttons: plain title.
    left = {"Windows": 300, "My Folder": 200, "Untitled - Notepad": 240, "Administrative Tools": 300,
            "Computer Management": 300, "My Computer": 200}[WINDOWS[window_id][4]] - WINDOWS[window_id][2][0]
    left = max(left, 160)
    right = original.width - BUTTONS_WIDTH
    expected, actual = title_columns(original, left, right), title_columns(ours, left, right)
    assert all(close(a, e, COLUMN_TOLERANCE) for a, e in zip(actual, expected)), list(zip(actual, expected))


def test_1998_active_title_shades_from_navy_to_light_blue_like_the_original(themes):
    """The Notepad alert's title (x 126-520, its frame is a dialog's 3px), against ours at the same title width."""
    original = screenshot("win98notepad").crop((126 - BORDER, 192 - BORDER, 520 + BORDER + 1, 400))
    ours = Window(themes["1998"], original.width, original.height, True, "Notepad").render()
    left, right = 140, original.width - BUTTONS_WIDTH
    expected, actual = title_columns(original, left, right), title_columns(ours, left, right)
    assert all(close(a, e, COLUMN_TOLERANCE) for a, e in zip(actual, expected)), list(zip(actual, expected))


@pytest.mark.parametrize("look, name, origin, disabled", [("1998", "win98notepad", (503, 194), "X"), ("1995", "win95helpbutton", (33, 8), "")],
                         ids=["1998 alert close, disabled", "1995 dialog close"])
def test_dialog_close_button_matches_the_original(themes, look, name, origin, disabled):
    original = screenshot(name)
    ours = Window(themes[look], 200, 60, True, "", right="X", disabled=disabled).render()
    face = (200 - 6 - 16, 4 + 2)   # the close button's face: 6px in from the right, 2px below the title's top
    for dy in range(14):
        for dx in range(16):
            assert close(ours.getpixel((face[0] + dx, face[1] + dy)), original.getpixel((origin[0] + dx, origin[1] + dy))), (dx, dy)


def test_pressed_help_button_matches_the_original(themes):
    original = screenshot("win95helpbutton")
    ours = Window(themes["1995"], 200, 60, True, "", right="HX", pressed="H").render()
    help_left = 200 - 6 - 18 - 16
    pointer = lambda dx, dy: dy == 13 and dx >= 7   # the screenshot's mouse pointer covers the bottom row from here
    for dy in range(14):
        for dx in range(16):
            if pointer(dx, dy):
                continue
            assert close(ours.getpixel((help_left + dx, 6 + dy)), original.getpixel((15 + dx, 8 + dy))), (dx, dy)


@needs_ui_font
@pytest.mark.parametrize("window_id", ["1995 active", "1995 inactive", "1998 inactive"])
def test_caption_starts_and_sits_where_the_original_puts_it(themes, window_id):
    original, ours = original_and_ours(themes, window_id)
    text = (255, 255, 255) if WINDOWS[window_id][3] else (192, 192, 192)

    def ink(image):
        xs, ys = [], []
        for x in range(CAPTION_LEFT - 2, CAPTION_LEFT + 60):
            for y in range(BORDER, TOP):
                if close(image.getpixel((x, y)), text, 16):
                    xs.append(x)
                    ys.append(y)
        return min(xs), min(ys), max(ys)
    expected, actual = ink(original), ink(ours)
    assert all(abs(a - e) <= 1 for a, e in zip(actual, expected)), (actual, expected)
