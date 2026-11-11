"""The 1998 and 2000 Start menus' icons against the originals' (win98start.png, w2kstartmenu.png).

Both styles use the SE98 icon set, whose pictures match the originals' (bin/chicago95-startmenu
ROOT_ICON_SETS). For each item both menus are measured the same way: the icon's left edge, size and
height against its row's text, and its picture. The 1998 screenshot has Help highlighted, so ours is
drawn with Help highlighted too; it stops above Shut Down.
"""

import numpy as np
import pytest
from conftest import needs_se98_icons
from reference import render_start_menu, screenshot
from test_startmenu_styles_reference import STYLES, TEXT_COLUMNS

ICON_COLUMNS = (24, 58)
TEXT_FROM = 58
# style: {item: (the original's row top, our row top)}, row height; the item ours highlights.
ROWS = {
    "1998": (
        {
            "programs": (157, 3),
            "documents": (229, 39),
            "settings": (265, 75),
            "find": (301, 111),
            "help": (337, 147),
            "run": (373, 183),
        },
        36,
        4,
    ),
    "2000": (
        {
            "documents": (141, 141),
            "settings": (172, 172),
            "search": (204, 204),
            "help": (237, 237),
            "run": (268, 268),
            "shut_down": (308, 309),
        },
        32,
        None,
    ),
}
MEAN_DIFFERENCE = 8  # per channel, out of 255: the screenshots' palettes are tinted


@pytest.fixture(scope="module", params=sorted(ROWS))
def menus(request, startmenu, qt_app, tmp_path_factory):
    style = STYLES[request.param]
    reference = screenshot(style["screenshot"]).crop(style["menu"])
    active = ROWS[request.param][2]
    ours = render_start_menu(
        startmenu,
        qt_app,
        tmp_path_factory.mktemp(f"icons-{request.param}"),
        style["settings"],
        style["kdeglobals"],
        extra_top=style["extra_top"],
        active=None if active is None else active + len(style["extra_top"]) + (1 if style["extra_top"] else 0),
    )
    return request.param, reference, ours


def row_parts(image, top, height):
    """(icon box (left, top, right, bottom), text left, text bottom) in a row. The icon is whatever differs
    from the row's background left of the text; the text is what differs strongly right of the icon."""
    background = image.getpixel((image.width - 8, top + height // 2))

    def difference(x, y):
        return sum(abs(a - b) for a, b in zip(image.getpixel((x, y)), background, strict=False))

    icon = [(x, y) for x in range(*ICON_COLUMNS) for y in range(top, top + height) if difference(x, y) > 40]
    text = [
        (x, y) for x in range(TEXT_FROM, TEXT_COLUMNS[1]) for y in range(top, top + height) if difference(x, y) > 200
    ]
    xs, ys = [p[0] for p in icon], [p[1] for p in icon]
    return (min(xs), min(ys), max(xs), max(ys)), min(p[0] for p in text), max(p[1] for p in text)


@needs_se98_icons
@pytest.mark.parametrize("item", sorted({item for rows, _, _ in ROWS.values() for item in rows}))
def test_icon_and_text_sit_where_the_original_puts_them(menus, item):
    """Icon: left edge and size; text: left edge, and its bottom row counted from the icon's top."""
    style, reference, ours = menus
    rows, height, _ = ROWS[style]
    if item not in rows:
        pytest.skip(f"the {style} original has no {item} row")

    def layout(image, top):
        (left, icon_top, right, bottom), text_left, text_bottom = row_parts(image, top, height)
        return dict(
            icon_left=left,
            icon_width=right - left + 1,
            icon_height=bottom - icon_top + 1,
            text_left=text_left,
            text_bottom_below_icon_top=text_bottom - icon_top,
        )

    expected, actual = layout(reference, rows[item][0]), layout(ours, rows[item][1])
    # The icon set draws a few pictures 1px off where the original's sit inside the 24px square.
    assert {key: value for key, value in actual.items() if not key.startswith("icon")} == {
        key: value for key, value in expected.items() if not key.startswith("icon")
    }
    assert all(abs(actual[key] - expected[key]) <= 1 for key in actual if key.startswith("icon")), (actual, expected)


@needs_se98_icons
@pytest.mark.parametrize("item", sorted({item for rows, _, _ in ROWS.values() for item in rows}))
def test_icon_picture_matches_the_original(menus, item):
    style, reference, ours = menus
    rows, height, _ = ROWS[style]
    if item not in rows:
        pytest.skip(f"the {style} original has no {item} row")
    (left, top, right, bottom), _, _ = row_parts(reference, rows[item][0], height)
    target = np.asarray(reference.crop((left, top, right + 1, bottom + 1)), dtype=float)
    (our_left, our_top, _, _), _, _ = row_parts(ours, rows[item][1], height)
    difference = min(
        np.abs(
            target
            - np.asarray(
                ours.crop(
                    (our_left + dx, our_top + dy, our_left + dx + right - left + 1, our_top + dy + bottom - top + 1)
                ),
                dtype=float,
            )
        ).mean()
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
    )
    assert difference <= MEAN_DIFFERENCE, f"{item}: mean difference {difference:.1f}"
