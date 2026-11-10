"""Pixel tests: our Start menu against the 1995 original (tests/references/win95startmenu.png).

The root menu is cropped out of the screenshot. Our menu is rendered at 1x with the same items (no
"Log Off...") and "Programs" highlighted, as in the screenshot. Icons and the menu's text are drawn
with other artwork and fonts on purpose, so those areas are measured, not compared pixel by pixel.
"""
import pytest

from conftest import needs_ui_font

from reference import bounding_box, close, differing_pixels, render_start_menu, screenshot

ROOT_MENU = (2, 217, 166, 456)            # left, top, right, bottom of the root menu in the screenshot
ICON_COLUMN = (20, 70)                    # x range of the icons, ignored by the pixel comparison
TEXT_FROM = 67                            # item text is measured from here (past the icons' dark edges)
# Edges set by letter shapes, which come from another font on purpose (MS Sans Serif's "S" has a 1px
# left bearing ours lacks; Liberation Sans Bold is 1px taller than the banner's bitmap letters).
LETTER_SHAPE_SLACK = 1
BANNER = (3, 23)                          # x range of the banner strip
NAVY = (0, 0, 128)
SUBMENU_OVERLAP = (156, 96)               # x from, y up to: where the screenshot's submenu covers the menu
ROW_TOPS = [3, 35, 67, 99, 131, 163, 205]  # Programs (highlighted), Documents, Settings, Find, Help, Run..., Shut Down...


@pytest.fixture(scope="session")
def reference():
    return screenshot("win95startmenu").crop(ROOT_MENU)


@pytest.fixture(scope="session")
def ours(startmenu, qt_app, tmp_path_factory):
    image = render_start_menu(startmenu, qt_app, tmp_path_factory.mktemp("settings"), "[StartMenu]\nbannerText=Windows95\n", active=0)
    image.save(tmp_path_factory.getbasetemp() / "ours-startmenu-1995.png")
    return image


def text_box(image, row_top):
    """Dark text pixels right of the icon column in one 32px row."""
    return bounding_box(image, lambda c: sum(c) < 150, (TEXT_FROM, image.width - 20), (row_top, row_top + 32))


def test_root_menu_is_164_by_239_like_the_original(reference, ours):
    assert ours.size == reference.size == (164, 239)


def test_outer_bevel_matches_pixel_for_pixel(reference, ours):
    w, h = reference.size
    ring = [(x, y) for x in range(w) for y in (0, 1, h - 2, h - 1)] + [(x, y) for y in range(h) for x in (0, 1, w - 2, w - 1)]
    # The screenshot's Programs submenu covers the menu's top-right corner.
    ring = [(x, y) for x, y in ring if not (x >= SUBMENU_OVERLAP[0] and y < SUBMENU_OVERLAP[1])]
    mismatched = [(x, y) for x, y in ring if not close(reference.getpixel((x, y)), ours.getpixel((x, y)))]
    assert mismatched == []


def test_separator_is_on_row_197(reference, ours):
    def separator(image):
        return [y for y in range(image.height - 1) if close(image.getpixel((90, y)), (128, 128, 128)) and close(image.getpixel((90, y + 1)), (255, 255, 255))]
    assert separator(ours) == separator(reference) == [197]


def test_highlight_bar_covers_the_programs_row(reference, ours):
    def bar(image):
        # Stops short of the right edge, where the screenshot's Programs submenu overlaps the menu.
        return bounding_box(image, lambda c: close(c, NAVY), (BANNER[1] + 1, image.width - 8), (0, 40))
    assert bar(ours) == bar(reference)


@needs_ui_font
@pytest.mark.parametrize("row_top", ROW_TOPS[1:])
def test_item_text_starts_and_sits_where_the_original_puts_it(reference, ours, row_top):
    expected, actual = text_box(reference, row_top), text_box(ours, row_top)
    assert abs(actual[0] - expected[0]) <= LETTER_SHAPE_SLACK and (actual[1], actual[3]) == (expected[1], expected[3]), (actual, expected)


def test_banner_text_fills_the_same_box(reference, ours):
    def banner_text(image):
        return bounding_box(image, lambda c: not close(c, (128, 128, 128)), BANNER, (3, image.height - 3))
    expected, actual = banner_text(reference), banner_text(ours)
    assert all(abs(a - e) <= LETTER_SHAPE_SLACK for a, e in zip(actual, expected)) and (actual[1], actual[3]) == (expected[1], expected[3]), (actual, expected)


def lettering_boxes(reference, ours):
    """Where the two menus are allowed to differ: letter shapes (another font) inside matching boxes."""
    boxes = []
    for row_top in ROW_TOPS:
        for image in (reference, ours):
            box = bounding_box(image, lambda c: sum(c) < 150 or c[0] > 240 and c[2] > 240,
                               (ICON_COLUMN[1], image.width - 16), (row_top, row_top + 32))
            if box:
                boxes.append((box[0] - 1, box[1] - 1, box[2] + 2, box[3] + 2))
    for image in (reference, ours):
        box = bounding_box(image, lambda c: not close(c, (128, 128, 128)), BANNER, (3, image.height - 3))
        boxes.append((box[0], box[1], box[2] + 1, box[3] + 1))
    return boxes


@needs_ui_font
def test_everything_but_icons_and_letter_shapes_matches_pixel_for_pixel(reference, ours, tmp_path):
    masks = [(ICON_COLUMN[0], 0, ICON_COLUMN[1], reference.height), (SUBMENU_OVERLAP[0], 0, reference.width, SUBMENU_OVERLAP[1])]
    masks += lettering_boxes(reference, ours)
    count = differing_pixels(reference, ours, masks, tmp_path / "startmenu-diff.png")
    assert count == 0, f"{count} pixels differ; diff saved in {tmp_path}"
