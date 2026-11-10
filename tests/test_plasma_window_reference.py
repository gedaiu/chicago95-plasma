"""Window frames as KWin draws them around each toolkit's windows (Qt, GTK 3, GTK 4, X11 through
Xwayland), on the desktops of tests/plasma_session.py, against the originals' windows at the same places.

Where our window's state differs from the original's (1998's Notepad is inactive behind an alert; ours
is the active window), the title band is left out and the alert's active title is compared instead.
"""
import pytest

from conftest import needs_ui_font
from plasma_session import CONTENT, missing_programs
from reference import close, differing_pixels, screenshot
from test_window_reference import BORDER, BUTTONS_WIDTH, CAPTION_LEFT, COLUMN_TOLERANCE, ICON, TOP, WINDOWS, title_columns

pytestmark = [needs_ui_font, pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}")]

PLACED = [(look, title, toolkit, box) for look, content in CONTENT.items()
          for title, toolkit, box in content["windows"] if box != "minimized"]
IDS = [f"{look} {toolkit} {title}" for look, title, toolkit, _box in PLACED]


def original_window(look, box):
    """(screenshot, active, the box of the window covering it) of the original's window at box."""
    return next((name, active, covered) for window_look, name, window_box, active, _caption, covered in WINDOWS.values()
                if (window_look, window_box) == (look, box))


def crops(desktops, look, title, box):
    name, original_active, covered = original_window(look, box)
    left, top, right, bottom = box
    original = screenshot(name).crop((left, top, right + 1, bottom + 1))
    ours = desktops(look).crop((left, top, right + 1, bottom + 1))
    return original, ours, original_active, title == CONTENT[look]["active"], covered


@pytest.mark.parametrize("look, title, toolkit, box", PLACED, ids=IDS)
def test_frame_corners_and_buttons_match_the_original(desktops, look, title, toolkit, box, tmp_path):
    original, ours, original_active, active, covered = crops(desktops, look, title, box)
    w, h = original.size
    same_state = active == original_active
    title = (CAPTION_LEFT, BORDER, w - BUTTONS_WIDTH, TOP) if same_state else (BORDER, BORDER, w - BORDER, TOP)
    masks = [(BORDER, TOP, w - BORDER, h - BORDER), ICON, title]
    if covered:
        masks.append((covered[0] - box[0], covered[1] - box[1], covered[2] - box[0] + 1, covered[3] - box[1] + 1))
    count = differing_pixels(original, ours, masks, tmp_path / "window-diff.png", threshold=0.12)
    assert count == 0, f"{count} pixels differ; see {tmp_path}"
    if not same_state:   # the buttons' faces are the same in either state
        faces = [(w - 6 - 16 - offset, BORDER + 2) for offset in (0, 18, 34)]   # close, maximize, minimize
        differing = [(x + dx, y + dy) for x, y in faces for dx in range(16) for dy in range(14)
                     if not close(ours.getpixel((x + dx, y + dy)), original.getpixel((x + dx, y + dy)))]
        assert differing == []


@pytest.mark.parametrize("look, title, toolkit, box", PLACED, ids=IDS)
def test_title_colours_match_the_original_column_by_column(desktops, look, title, toolkit, box):
    original, ours, original_active, active, _covered = crops(desktops, look, title, box)
    if active != original_active:
        pytest.skip("the original's window is in the other state; see the 1998 alert's title below")
    left, right = 160, original.width - BUTTONS_WIDTH   # right of the captions
    expected, actual = title_columns(original, left, right), title_columns(ours, left, right)
    assert all(close(a, e, COLUMN_TOLERANCE) for a, e in zip(actual, expected)), list(zip(actual, expected))


def test_1998_active_title_shades_like_the_originals_alert(desktops):
    """The Notepad alert (x 126-520): our active Notepad window's title, at nearly the same width."""
    alert = screenshot("win98notepad").crop((126 - BORDER, 192 - BORDER, 520 + BORDER + 1, 230))
    left, top, right, _bottom = CONTENT["1998"]["windows"][1][2]
    ours = desktops("1998").crop((left, top, right + 1, top + 40))
    expected = title_columns(alert, 140, alert.width - BUTTONS_WIDTH)
    actual = title_columns(ours, 140, ours.width - BUTTONS_WIDTH)
    assert all(close(a, e, COLUMN_TOLERANCE) for a, e in zip(actual, expected)), list(zip(actual, expected))


@pytest.mark.parametrize("look, title, toolkit, box", [window for window in PLACED if window[0] != "2000"],
                         ids=[id_ for id_, window in zip(IDS, PLACED) if window[0] != "2000"])
def test_caption_starts_and_sits_where_the_originals_does(desktops, look, title, toolkit, box):
    """2000's captions are Tahoma; ours are the UI font, so only 1995's and 1998's are compared. The
    originals' font leaves a blank column before most capitals but not before W; ours starts every glyph
    at its origin and the caption a pixel further in, so a caption starting with W starts a pixel right."""
    original, ours, original_active, active, _covered = crops(desktops, look, title, box)

    def ink(image, colour):
        points = [(x, y) for x in range(CAPTION_LEFT - 2, CAPTION_LEFT + 60) for y in range(BORDER, TOP)
                  if close(image.getpixel((x, y)), colour, 16)]
        return min(x for x, _ in points), min(y for _, y in points), max(y for _, y in points)
    caption = lambda is_active: (255, 255, 255) if is_active else (192, 192, 192)
    expected, actual = ink(original, caption(original_active)), ink(ours, caption(active))
    assert actual == (expected[0] + title.startswith("W"), expected[1], expected[2])
