"""The 1995 Start menu's icons against the original's (win95startmenu.png): same place, same size, same picture.

The originals draw 24x24 icons centred in 32px rows. Chicago95 recreates them, so with the Chicago95
icon set our icons match the originals nearly pixel for pixel (the screenshot's palette is tinted).
"""

import numpy as np
import pytest
from conftest import needs_chicago95_icons
from reference import render_start_menu, screenshot

ROOT_MENU = (2, 217, 166, 456)
ROWS = {"programs": 3, "documents": 35, "settings": 67, "find": 99, "help": 131, "run": 163, "shutdown": 205}
ICON_X, ICON_SIZE = 34, 24
MEAN_DIFFERENCE = 6  # per channel, out of 255


@pytest.fixture(scope="module")
def menus(startmenu, qt_app, tmp_path_factory):
    import chicago95ui
    from PySide6.QtGui import QIcon

    reference = screenshot("win95startmenu").crop(ROOT_MENU)
    QIcon.setThemeName("Chicago95")
    ours = render_start_menu(
        startmenu, qt_app, tmp_path_factory.mktemp("icons"), "[StartMenu]\nbannerText=Windows95\n", active=0
    )
    QIcon.setThemeName(chicago95ui.icon_theme())
    return reference, ours


def icon_box(image, top):
    background = {image.getpixel((ICON_X - 6, top + 2)), image.getpixel((ICON_X - 6, top + 28))}
    pts = [
        (x, y)
        for x in range(ICON_X - 4, ICON_X + ICON_SIZE + 4)
        for y in range(top, top + 32)
        if all(sum(abs(a - b) for a, b in zip(image.getpixel((x, y)), colour)) > 24 for colour in background)
    ]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys) - top, max(xs) - min(xs) + 1, max(ys) - min(ys) + 1


@needs_chicago95_icons
@pytest.mark.parametrize("item", sorted(ROWS))
def test_icon_sits_where_the_original_puts_it(menus, item):
    reference, ours = menus
    expected, actual = icon_box(reference, ROWS[item]), icon_box(ours, ROWS[item])
    assert all(abs(a - e) <= 1 for a, e in zip(actual, expected)), (actual, expected)


@needs_chicago95_icons
@pytest.mark.parametrize("item", sorted(ROWS))
def test_icon_looks_like_the_original(menus, item):
    reference, ours = menus
    box = (ICON_X, ROWS[item] + 4, ICON_X + ICON_SIZE, ROWS[item] + 4 + ICON_SIZE)
    target = np.asarray(reference.crop(box), dtype=float)
    # The icon set may place a picture 1px differently inside its 24px canvas than the original
    # (Chicago95's Documents sits 1px lower); placement itself is tested above.
    difference = min(
        np.abs(target - np.asarray(ours.crop((box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy)), dtype=float)).mean()
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
    )
    assert difference <= MEAN_DIFFERENCE, f"{item}: mean difference {difference:.1f}"
