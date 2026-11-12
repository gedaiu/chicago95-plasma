"""plasmashell's desktop context menu in a live session (tests/plasma_session.py), opened with a right-click
and a hovered row: the 1995 look's classic menu, and Windows XP Luna's against the menu specification (white
face, 1px #ACA899 frame, 21px rows, a 28px icon column, #316AC5 highlight, 1px #ACA899 separators over white,
a black submenu arrow). No XP context menu screenshot exists, so the specification is also drawn
(spec_menu) and compared with the live menu outside its icons and labels.
"""

import pytest
from conftest import needs_ui_font
from PIL import Image, ImageDraw
from plasma_session import CLICK, menu_steps, missing_programs
from reference import close

pytestmark = [
    needs_ui_font,
    pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}"),
]

FRAME, WHITE, HIGHLIGHT, BLACK = (172, 168, 153), (255, 255, 255), (49, 106, 197), (0, 0, 0)
CLASSIC_FACE, CLASSIC_SELECTION = (192, 192, 192), (0, 0, 128)
ROW, SEPARATOR_ROW, ICON_COLUMN, ARROW_ZONE = 21, 6, 28, 22
GROUPS = (4, 2, 2, 2)
HOVERED_ROW = 4  # Open Terminal: a row without a submenu
HOVER = (CLICK[0] + 100, CLICK[1] + 100)
TOLERANCE, BUDGET = 12, 0.03


@pytest.fixture(scope="module")
def menu_screen(desktops):
    return lambda look: desktops(look, windows=[], pointer_steps=menu_steps(look, "desktop", hover=HOVER))


@pytest.fixture(scope="module")
def luna_screen(menu_screen):
    return menu_screen("luna")


def paint_rows(screen, x, ys, colour):
    return [y for y in ys if close(screen.getpixel((x, y)), colour, 2)]


def menu_box(screen):
    """(left, top, right, bottom) of the frame: the first and last frame-coloured pixels around the click."""
    row = CLICK[1] + 10
    across = [x for x in range(CLICK[0] - 10, screen.width) if close(screen.getpixel((x, row)), FRAME, 2)]
    left, right = across[0], across[-1]
    down = paint_rows(screen, left + 8, range(CLICK[1] - 5, screen.height), FRAME)
    return left, down[0], right, down[-1]


def spec_menu(width):
    """The specification, drawn: frame, white face, the highlighted row, separators; width x its own height."""
    kinds = [kind for count in GROUPS for kind in ("separator", *["row"] * count)][1:]
    height = 2 * 1 + 2 * 2 + sum(SEPARATOR_ROW if kind == "separator" else ROW for kind in kinds)
    picture = Image.new("RGB", (width, height), WHITE)
    painter = ImageDraw.Draw(picture)
    painter.rectangle((0, 0, width - 1, height - 1), outline=FRAME)
    top, rows = 3, 0
    for kind in kinds:
        if kind == "separator":
            painter.rectangle((1 + ICON_COLUMN, top + 2, width - 4, top + 2), fill=FRAME)
            top += SEPARATOR_ROW
            continue
        if rows == HOVERED_ROW:
            painter.rectangle((1, top, width - 2, top + ROW - 1), fill=HIGHLIGHT)
        rows += 1
        top += ROW
    return picture


def item_row_boxes(width):
    """The icon column and label area of each item row of spec_menu, to leave out of comparisons."""
    kinds = [kind for count in GROUPS for kind in ("separator", *["row"] * count)][1:]
    boxes, top = [], 3
    for kind in kinds:
        if kind == "row":
            boxes.append((1, top, width - 2, top + ROW - 1))
        top += SEPARATOR_ROW if kind == "separator" else ROW
    return boxes


def column_colours(screen, x, top, bottom):
    return [screen.getpixel((x, y)) for y in range(top, bottom + 1)]


def test_1995_menu_face_is_c0c0c0(menu_screen):
    screen = menu_screen("1995")
    assert close(screen.getpixel((CLICK[0] + 150, CLICK[1] + 10)), CLASSIC_FACE, TOLERANCE) is True


def test_1995_hovered_row_is_000080(menu_screen):
    screen = menu_screen("1995")
    assert close(screen.getpixel((CLICK[0] + 60, HOVER[1])), CLASSIC_SELECTION, TOLERANCE) is True


def test_luna_menu_frame_is_1px_aca899_all_round(luna_screen):
    left, top, right, bottom = menu_box(luna_screen)
    middle = (left + right) // 2
    around = [
        luna_screen.getpixel(point) for point in ((left, top + 30), (right, top + 30), (middle, top), (middle, bottom))
    ]
    inside = [luna_screen.getpixel((left + 1, top + 30)), luna_screen.getpixel((middle, top + 1))]
    assert (around, inside) == ([FRAME] * 4, [WHITE] * 2)


def test_luna_menu_item_background_is_white_right_of_the_icon_column(luna_screen):
    left, top, right, _ = menu_box(luna_screen)
    assert luna_screen.getpixel((right - 40, top + 3 + ROW + 3)) == WHITE


def test_luna_hovered_row_is_316ac5_and_21_rows_high(luna_screen):
    left, top, right, bottom = menu_box(luna_screen)
    blue = paint_rows(luna_screen, right - 40, range(top, bottom), HIGHLIGHT)
    assert (len(blue), blue[-1] - blue[0] + 1, blue[0] - top) == (ROW, ROW, 3 + HOVERED_ROW * ROW + SEPARATOR_ROW)


def test_luna_row_pitch_is_21_between_the_top_and_the_first_separator(luna_screen):
    left, top, right, bottom = menu_box(luna_screen)
    first_separator = paint_rows(luna_screen, left + ICON_COLUMN + 20, range(top + 3, bottom), FRAME)[0]
    assert first_separator - top == 3 + 4 * ROW + 2


def test_luna_disabled_paste_label_is_grey_aca899(luna_screen):
    left, top, right, _ = menu_box(luna_screen)
    paste = [
        luna_screen.getpixel((x, y))
        for y in range(top + 3 + ROW, top + 3 + 2 * ROW)
        for x in range(left + ICON_COLUMN + 1, left + ICON_COLUMN + 40)
    ]
    assert (any(close(colour, FRAME, TOLERANCE) for colour in paste), BLACK in paste) == (True, False)


def test_luna_separators_are_aca899_over_white_starting_after_the_icon_column(luna_screen):
    left, top, right, bottom = menu_box(luna_screen)
    lines = paint_rows(luna_screen, left + ICON_COLUMN + 20, range(top + 3, bottom - 2), FRAME)
    below = [luna_screen.getpixel((left + ICON_COLUMN + 20, y + 1)) for y in lines]
    start = next(x for x in range(left + 1, right) if luna_screen.getpixel((x, lines[0])) == FRAME)
    assert (len(lines), below, start - left) == (3, [WHITE] * 3, 1 + ICON_COLUMN)


def test_luna_submenu_arrow_is_black_in_the_right_gutter(luna_screen):
    left, top, right, _ = menu_box(luna_screen)
    arrow = [
        luna_screen.getpixel((x, y)) for x in range(right - ARROW_ZONE, right) for y in range(top + 3, top + 3 + ROW)
    ]
    assert BLACK in arrow


def test_luna_icon_column_is_white_without_a_gradient_between_the_icons(luna_screen):
    left, top, _, bottom = menu_box(luna_screen)
    gutter = column_colours(luna_screen, left + 1, top + 1, bottom - 1)
    assert set(gutter) <= {WHITE, HIGHLIGHT}


def test_luna_menu_matches_the_specification_outside_icons_and_labels(luna_screen):
    left, top, right, bottom = menu_box(luna_screen)
    width = right - left + 1
    expected = spec_menu(width)
    ours = luna_screen.crop((left, top, right + 1, bottom + 1))
    masked = Image.new("L", expected.size, 255)
    painter = ImageDraw.Draw(masked)
    for box in item_row_boxes(width):
        painter.rectangle((box[0], box[1], box[0] + ICON_COLUMN - 1, box[3]), fill=0)
        painter.rectangle((box[0] + ICON_COLUMN, box[1], box[2] - ARROW_ZONE, box[3]), fill=0)
    compared = [(x, y) for x in range(width) for y in range(expected.height) if masked.getpixel((x, y))]
    wrong = [point for point in compared if not close(ours.getpixel(point), expected.getpixel(point), TOLERANCE)]
    assert (ours.size, len(wrong) <= BUDGET * len(compared)) == (expected.size, True)


@pytest.fixture(scope="module")
def start_button_menu(desktops):
    return lambda look: desktops(look, windows=[], pointer_steps=menu_steps(look, "start"))


def test_1995_start_button_menu_face_is_c0c0c0(start_button_menu):
    screen = start_button_menu("1995")
    assert close(screen.getpixel((120, screen.height - 50)), CLASSIC_FACE, TOLERANCE) is True


def test_luna_start_button_menu_face_is_white(start_button_menu):
    screen = start_button_menu("luna")
    assert screen.getpixel((220, screen.height - 50)) == WHITE
