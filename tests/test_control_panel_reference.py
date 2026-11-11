"""Pixel tests: the Control Panel against the Windows 95 original (tests/references/win95controlpanel.png).

The original's icon view is measured and ours, rendered at 1x on its white background, is measured the
same way: icons sit 75px apart in both directions and the labels are centred in their cells. The menu
and status bars have the original's heights. Icons and labels are drawn with other artwork and fonts on
purpose, so only where things sit is compared.
"""

import pytest
from conftest import load_script
from reference import qimage_to_pil, screenshot

ICON_AREA = (8, 44, 438, 411)  # left, top, right, bottom of the icon view inside the original's window
MENU_BAR_HEIGHT = 22  # Windows 98's: tests/test_control_panel_header_reference.py
STATUS_BAR_HEIGHT = 19  # rows 413 to 431
CELL = 75
FRAME = 2  # our icon view's sunken frame
WORD_GAP = 8  # darker pixels closer than this belong to one icon with its label
WHITE = (255, 255, 255)


def ink_runs(image, box, vertical):
    """(first, last) of the runs of rows (vertical) or columns with any non-white pixel in box, bridging gaps under WORD_GAP."""
    left, top, right, bottom = box
    lines = range(top, bottom) if vertical else range(left, right)
    across = range(left, right) if vertical else range(top, bottom)
    inked = [
        line
        for line in lines
        if any(
            image.getpixel((across_position, line) if vertical else (line, across_position)) != WHITE
            for across_position in across
        )
    ]
    runs = []
    for line in inked:
        if runs and line - runs[-1][1] < WORD_GAP:
            runs[-1][1] = line
        else:
            runs.append([line, line])
    return runs


def average_pitch(positions):
    return (positions[-1] - positions[0]) / (len(positions) - 1)


def column_pitch(image, box):
    """Average distance between the centres of the first row's icon columns; artwork is not symmetric, so single pairs vary."""
    first_row = (box[0], box[1], box[2], box[1] + CELL)
    return average_pitch([(first + last) / 2 for first, last in ink_runs(image, first_row, vertical=False)][:5])


def row_pitch(image, box):
    """Average distance between the tops of the icon rows."""
    first_columns = (box[0], box[1], box[0] + 4 * CELL, box[3])
    return average_pitch([first for first, _ in ink_runs(image, first_columns, vertical=True)][:4])


@pytest.fixture(scope="session")
def reference():
    return screenshot("win95controlpanel")


@pytest.fixture(scope="module")
def ours(qt_app, tmp_path_factory):
    control_panel = load_script("chicago95-control-panel")
    window = control_panel.ControlPanel(settings_path=tmp_path_factory.mktemp("settings") / "setup.conf")
    window.show()
    qt_app.processEvents()
    return window, qimage_to_pil(window.icon_view.grab().toImage())


def within_a_pixel_of_the_cell(distance):
    return abs(distance - CELL) <= 1


def test_originals_icons_are_75px_apart_across_and_down(reference):
    assert (
        within_a_pixel_of_the_cell(column_pitch(reference, ICON_AREA)),
        within_a_pixel_of_the_cell(row_pitch(reference, ICON_AREA)),
    ) == (True, True)


def test_our_icons_are_75px_apart_across_and_down(ours):
    _window, image = ours
    box = (FRAME, FRAME, image.width - FRAME, image.height - FRAME)
    rows = [first for first, _ in ink_runs(image, box, vertical=True)]

    assert (
        within_a_pixel_of_the_cell(column_pitch(image, box)),
        within_a_pixel_of_the_cell(average_pitch(rows[:2])),
    ) == (True, True)


def test_our_menu_bar_and_status_bar_have_the_originals_heights(ours):
    window, _image = ours

    assert (window.menu_bar.height(), window.statusBar().height()) == (MENU_BAR_HEIGHT, STATUS_BAR_HEIGHT)
