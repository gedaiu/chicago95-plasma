"""Our 1998 and 2000 Start menus against screenshots of the originals (win98start.png, w2kstartmenu.png).

The originals list items ours doesn't have (Office entries, Favorites), so these tests measure both
images the same way and compare the measurements: row spacing, where text starts, the bevel's
colours, the banner's background and the banner lettering's length, thickness and place.
"""

from collections import Counter

import pytest
from conftest import needs_ui_font
from reference import close, render_start_menu, screenshot

STYLES = {
    "1998": dict(
        screenshot="win98start",
        menu=(2, 0, 216, 456),
        extra_top=(),
        settings="[StartMenu]\nstyle=1998\nbannerText=Windows98\nbannerTextColor=#FFFFFF\nbannerNumberColor=#FFFFFF\n"
        "bannerBackground=#00007B,#00007B@95,#0000B0@70,#0000F8@45,#0000EE@20,#0000A9@0\n",
        kdeglobals="",
    ),
    "2000": dict(
        screenshot="w2kstartmenu",
        menu=(2, 113, 206, 456),
        extra_top=("New Office Document", "Open Office Document", "Windows Update"),
        settings="[StartMenu]\nstyle=2000\nbannerText=Windows 2000 Professional\nbannerTextColor=#FFFFFF\n"
        "bannerNumberColor=#FFFFFF\n"
        "bannerBackground=#000000,#000021@200,#000081@120,#0000B2@70,#0000E3@45,#0000F3@20,#0000FF@0\n",
        kdeglobals="[Colors:Window]\nBackgroundNormal=212,208,200\n\n[Colors:Selection]\nBackgroundNormal=10,36,106\n",
    ),
}
BANNER = (3, 24)
TEXT_COLUMNS = (70, 140)


@pytest.fixture(scope="module", params=sorted(STYLES))
def pair(request, startmenu, qt_app, tmp_path_factory):
    style = STYLES[request.param]
    reference = screenshot(style["screenshot"]).crop(style["menu"])
    ours = render_start_menu(
        startmenu,
        qt_app,
        tmp_path_factory.mktemp(request.param),
        style["settings"],
        style["kdeglobals"],
        extra_top=style["extra_top"],
    )
    ours.save(tmp_path_factory.getbasetemp() / f"ours-startmenu-{request.param}.png")
    return request.param, reference, ours


def face(image):
    return image.getpixel((image.width - 8, image.height // 2))


def text_row_tops(image):
    """Top y of each run of rows holding dark text pixels in the text columns."""
    rows = [y for y in range(image.height) if any(sum(image.getpixel((x, y))) < 150 for x in range(*TEXT_COLUMNS))]
    # Runs closer than 5px are one row of text (underlined mnemonics leave a gap above the underline).
    return [y for index, y in enumerate(rows) if index == 0 or y - rows[index - 1] > 5]


def row_pitch(image):
    tops = text_row_tops(image)
    return Counter(b - a for a, b in zip(tops, tops[1:], strict=False)).most_common(1)[0][0]


def text_left(image):
    """Where item text starts: the most common leftmost dark pixel per text row."""
    starts = []
    for top in text_row_tops(image):
        xs = [
            x
            for x in range(66, TEXT_COLUMNS[1])
            for y in range(top, top + 8)
            if y < image.height and sum(image.getpixel((x, y))) < 150
        ]
        if xs:
            starts.append(min(xs))
    return Counter(starts).most_common(1)[0][0]


def banner_lettering(image):
    """(length, thickness, gap above the banner's bottom) of the light lettering in the banner."""
    bottom = image.height - 4
    pts = [(x, y) for x in range(*BANNER) for y in range(8, bottom + 1) if image.getpixel((x, y))[0] > 100]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return max(ys) - min(ys) + 1, max(xs) - min(xs) + 1, bottom - max(ys)


def banner_blue(image, above_bottom):
    """Mean blue of the banner's text-free edge columns, ten rows starting this far above its bottom."""
    bottom = image.height - 4
    pixels = [
        image.getpixel((x, y))
        for x in (3, 4, 22, 23)
        for y in range(bottom - above_bottom - 9, bottom - above_bottom + 1)
    ]
    return sum(p[2] for p in pixels) / len(pixels)


@needs_ui_font
def test_rows_are_spaced_like_the_original(pair):
    _, reference, ours = pair
    assert row_pitch(ours) == row_pitch(reference)


@needs_ui_font
def test_item_text_starts_where_the_original_starts_it(pair):
    _, reference, ours = pair
    assert abs(text_left(ours) - text_left(reference)) <= 1, (text_left(ours), text_left(reference))


def test_bevel_and_face_colours_match(pair):
    _, reference, ours = pair

    def bevel(image):
        h = image.height
        return [
            image.getpixel((0, h - 30)),
            image.getpixel((1, h - 30)),
            face(image),
            image.getpixel((60, h - 2)),
            image.getpixel((60, h - 1)),
        ]

    assert all(close(a, b, 16) for a, b in zip(bevel(ours), bevel(reference), strict=False)), (
        bevel(ours),
        bevel(reference),
    )


def test_banner_background_shades_like_the_original(pair):
    _, reference, ours = pair
    heights = (0, 20, 45, 70, 120, 200)
    expected = [round(banner_blue(reference, h)) for h in heights]
    actual = [round(banner_blue(ours, h)) for h in heights]
    assert all(abs(a - e) <= 24 for a, e in zip(actual, expected, strict=False)), list(
        zip(heights, actual, expected, strict=False)
    )


def test_banner_lettering_has_the_originals_length_thickness_and_place(pair):
    _, reference, ours = pair
    expected, actual = banner_lettering(reference), banner_lettering(ours)
    assert all(abs(a - e) <= 2 for a, e in zip(actual, expected, strict=False)), (actual, expected)


def banner_parts_lengths(image):
    """Lengths along the banner of each lettering part, split where the lettering has a gap of 2px or more."""
    bottom = image.height - 4
    rows = [y for y in range(8, bottom + 1) if any(image.getpixel((x, y))[0] > 100 for x in range(*BANNER))]
    parts, start = [], rows[0]
    for a, b in zip(rows, rows[1:], strict=False):
        if b - a > 2:
            parts.append(a - start + 1)
            start = b
    parts.append(rows[-1] - start + 1)
    return parts


def test_2000_banner_parts_match_the_originals_word_by_word(startmenu, qt_app, tmp_path):
    style = STYLES["2000"]
    reference = screenshot(style["screenshot"]).crop(style["menu"])
    ours = render_start_menu(
        startmenu, qt_app, tmp_path, style["settings"], style["kdeglobals"], extra_top=style["extra_top"]
    )
    # Read bottom to top: "Windows", "2000", "Professional" (83, 30 and 104px long on the original).
    expected, actual = banner_parts_lengths(reference), banner_parts_lengths(ours)
    assert len(actual) == len(expected) == 3 and all(abs(a - e) <= 5 for a, e in zip(actual, expected, strict=False)), (
        actual,
        expected,
    )
