"""Our System Properties (bin/chicago95-sysprops) against the originals' dialogs, General page, for the
three looks: win95sysprops.png, win98sysprops.png (a JPEG: colours within 40) and w2ksysprops.png.

The three share one layout, measured here with the dialogs aligned on their title bars: a 410px dialog,
3px frame, 18px title with help and close buttons, a tab strip whose selected tab stands 2px taller and
wider, a page frame from x 9 to 400, the computer picture at the left, the facts in two columns at the
right, and 75x23 buttons at the bottom right (OK and Cancel; 2000 adds Apply, and is 13px taller).
Ours is drawn with the same facts' wording, in the classic greys the 2000 original also uses.
"""

import pytest
from conftest import needs_ui_font
from reference import close, qimage_to_pil, screenshot

pytestmark = needs_ui_font

# look: reference, its dialog's top-left in the screenshot, size, tab captions and their natural boxes
# (left white column to right black column, each starting after the last; the selected one grows 2px
# each side, over its neighbour's left edge), the General page's
# heading column and rows, the icon's box, and the buttons' left edges.
LOOKS = {
    "1995": dict(
        reference="win95sysprops",
        origin=(232, 60),
        size=(410, 448),
        tabs=["General", "Device Manager", "Hardware Profiles", "Performance"],
        tab_boxes=[(11, 59), (60, 150), (151, 245), (246, 317)],
        headings=[(215, 71), (215, 151), (215, 253)],
        text_from=203,
        text_rows_to=400,
        icon=(67, 104, 160, 177),
        buttons={"OK": 245, "Cancel": 326},
        buttons_top=415,
    ),
    "1998": dict(
        reference="win98sysprops",
        origin=(0, 0),
        size=(410, 448),
        tabs=["General", "Device Manager", "Hardware Profiles", "Performance"],
        tab_boxes=[(11, 59), (60, 150), (151, 245), (246, 317)],
        headings=[(196, 71), (196, 160), (196, 246)],
        text_from=184,
        text_rows_to=400,
        icon=(65, 104, 161, 178),
        buttons={"OK": 245, "Cancel": 326},
        buttons_top=415,
    ),
    # 2000's third group is a manufacturer's, with a logo: its text is compared above it.
    "2000": dict(
        reference="w2ksysprops",
        origin=(434, 205),
        size=(410, 461),
        tabs=["General", "Hardware", "User Profiles", "Advanced"],
        tab_boxes=[(11, 59), (60, 117), (118, 188), (189, 249)],
        headings=[(208, 71), (208, 151)],
        text_from=196,
        text_rows_to=250,
        icon=(65, 104, 161, 178),
        buttons={"OK": 164, "Cancel": 245, "Apply": 326},
        buttons_top=428,
    ),
}
# 2001 (XP Classic) has no original of its own: it is compared against 2000's, tab strip aside.
LOOKS["2001"] = {
    **LOOKS["2000"],
    "tabs": ["General", "Computer Name", "Hardware", "Advanced", "System Restore", "Automatic Updates", "Remote"],
}
STRIP_LOOKS = [look for look in LOOKS if look != "2001"]
FRAME, TITLE = 3, 18
SELECTED_TAB_TOP, TAB_TOP, PAGE_TOP = 29, 31, 49  # white rows: the selected tab, the others, the page frame
PAGE_LEFT, PAGE_RIGHT = 9, 400  # the page frame's white left column, black right column
VALUE_INDENT, ROW_PITCH = 18, 18
BUTTON_SIZE = (75, 23)
TOLERANCE = {
    "1995": 12,
    "1998": 70,
    "2000": 70,
    "2001": 70,
}  # 1998: JPEG ringing beside its white lines; 2000: the original's classic greys against the look's #404040 lines
WATERMARK = {"1998": (355, 440, 410, 448)}  # the site's copyright, printed over the 1998 screenshot's corner
SLACK = {"1995": 1, "1998": 2, "2000": 1, "2001": 1}  # JPEG noise moves an edge or a glyph's first column


def is_dark(colour):
    return sum(colour) < 200  # black, and the 2000 look's #404040


def is_white(colour):
    return min(colour) > 232


def runs(values, gap=1):
    out = []
    for value in values:
        if out and value - out[-1][1] <= gap:
            out[-1][1] = value
        else:
            out.append([value, value])
    return [tuple(run) for run in out]


def original(look):
    settings = LOOKS[look]
    left, top = settings["origin"]
    width, height = settings["size"]
    return screenshot(settings["reference"]).crop((left, top, left + width, top + height))


@pytest.fixture(scope="module")
def sysprops():
    from conftest import load_script

    return load_script("chicago95-sysprops")


@pytest.fixture(scope="module")
def facts(sysprops):
    return sysprops.SystemFacts(
        os_name="Microsoft Windows 98",
        kernel="Second Edition",
        desktop="4.10.2222 A",
        owner="Doctor",
        hostname="TARDIS",
        product_key="01902-OEM-0087094-44427",
        cpu_model="GenuineIntel",
        logical_processors="Pentium(r) II Processor",
        memory="256.0MB RAM",
        display="",
        resources_free="90% free",
        filesystem="32-bit",
        virtual_memory="32-bit",
    )


@pytest.fixture(scope="module")
def ours(sysprops, facts, qt_app, tmp_path_factory):
    """Each look's dialog, its title buttons from that look's own window decoration."""
    import chicago95ui
    from aurorae_model import build_theme

    images = {}
    for look in LOOKS:
        chicago95ui.DECORATION = str(build_theme(tmp_path_factory.mktemp(f"aurorae-{look}"), look))
        window = sysprops.build_window(facts, look)
        window.show()
        qt_app.processEvents()
        images[look] = qimage_to_pil(window.grab().toImage())
        window.close()
    return images


def long_lines(image, predicate, share=0.55):
    """(columns, rows) where more than share of the pixels satisfy the predicate: the frames' lines."""
    w, h = image.size
    columns = [x for x in range(w) if sum(predicate(image.getpixel((x, y))) for y in range(h)) > h * share]
    rows = [y for y in range(h) if sum(predicate(image.getpixel((x, y))) for x in range(w)) > w * share]
    return columns, rows


def tab_edges(image):
    """(white columns, dark columns) running through the tab strip: the tabs' left and right edges."""
    white = [
        x for x in range(image.width) if sum(is_white(image.getpixel((x, y))) for y in range(TAB_TOP, PAGE_TOP)) >= 12
    ]
    dark = [
        x for x in range(image.width) if sum(is_dark(image.getpixel((x, y))) for y in range(TAB_TOP, PAGE_TOP)) >= 12
    ]
    return runs(white), runs(dark)


def ink_box(image, box):
    points = [(x, y) for x in range(box[0], box[2]) for y in range(box[1], box[3]) if is_dark(image.getpixel((x, y)))]
    return (
        (min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points))
        if points
        else None
    )


def text_rows(image, x_from, y_from, y_to):
    """[(first row, last row, first ink column)] of each line of text right of x_from."""
    rows = runs(
        [
            y
            for y in range(y_from, y_to)
            if sum(is_dark(image.getpixel((x, y))) for x in range(x_from, image.width - 12)) >= 2
        ],
        gap=2,
    )
    return [
        (
            top,
            bottom,
            min(
                x
                for x in range(x_from, image.width - 12)
                for y in range(top, bottom + 1)
                if is_dark(image.getpixel((x, y)))
            ),
        )
        for top, bottom in rows
    ]


def button_bottoms(image, y_from):
    """{(left, right, row)} of the buttons' black bottom lines below y_from, 70 to 80 wide: a button's
    whole width, whether its top is white (a plain button) or black (the default one's outline)."""
    lowest = {}
    for y in range(y_from, image.height - FRAME):
        for left, right in runs([x for x in range(image.width) if is_dark(image.getpixel((x, y)))]):
            if 70 <= right - left <= 80:
                lowest[(left, right)] = (
                    y  # the default button's inner edge and outline: the outline, lowest, is its bottom
                )
    return {(left, right, y) for (left, right), y in lowest.items()}


def coloured_box(image, region):
    left, top, right, bottom = region
    points = [
        (x, y)
        for x in range(left, right)
        for y in range(top, bottom)
        if max(image.getpixel((x, y))) - min(image.getpixel((x, y))) > 40
    ]
    return (
        (min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points))
        if points
        else None
    )


def within(actual, expected, slack):
    return actual is not None and all(abs(a - e) <= slack for a, e in zip(actual, expected, strict=False))


# --- the originals are where the table says (the crops' alignment) -----------------------------------


@pytest.mark.parametrize("look", LOOKS)
def test_the_original_dialog_has_the_tables_frame_tabs_page_and_buttons(look):
    image, settings = original(look), LOOKS[look]
    white_columns, white_rows = long_lines(image, is_white)
    dark_columns, dark_rows = long_lines(image, is_dark)
    assert (white_columns, dark_columns) == ([1, PAGE_LEFT], [PAGE_RIGHT, image.width - 1])
    assert PAGE_TOP in white_rows and image.height - 1 in dark_rows
    bottom = settings["buttons_top"] + BUTTON_SIZE[1] - 1
    assert button_bottoms(image, bottom - 2) == {
        (left, left + BUTTON_SIZE[0] - 1, bottom) for left in settings["buttons"].values()
    }


# --- ours -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("look", LOOKS)
def test_dialog_is_410_wide_and_as_tall_as_the_original(ours, look):
    assert ours[look].size == LOOKS[look]["size"]


@pytest.mark.parametrize("look", LOOKS)
def test_frame_title_buttons_match_the_original(ours, look):
    """The 3px frame all round, and the help and close buttons' faces (16x14, 2px below the title's top,
    close 2px from the title's right, help 2px left of it)."""
    mine, theirs = ours[look], original(look)
    w, h = theirs.size
    left, top, right, bottom = WATERMARK.get(look, (0, 0, 0, 0))
    ring = [
        (x, y)
        for x in range(w)
        for y in range(h)
        if min(x, y, w - 1 - x, h - 1 - y) < FRAME and not (left <= x < right and top <= y < bottom)
    ]
    close_left = w - FRAME - 2 - 16
    buttons = [
        (x, y)
        for left in (close_left, close_left - 18)
        for x in range(left, left + 16)
        for y in range(FRAME + 2, FRAME + 16)
    ]
    # 1998's JPEG smears the title's navy into the buttons' black edges: that look is compared in grey.
    alike = (
        (lambda a, b: abs(sum(a) - sum(b)) <= 3 * TOLERANCE[look])
        if look == "1998"
        else (lambda a, b: close(a, b, TOLERANCE[look]))
    )
    differing = [
        (point, mine.getpixel(point), theirs.getpixel(point))
        for point in ring + buttons
        if not alike(mine.getpixel(point), theirs.getpixel(point))
    ]
    assert differing == [], differing[:12]


@pytest.mark.parametrize("look", STRIP_LOOKS)
def test_tab_strip_has_the_originals_tabs_with_the_selected_one_standing_out(ours, look):
    """Each tab: a white left edge and a black right edge (a shadow inside it); the selected first tab 2px
    taller and 2px wider each side, covering its neighbour's left edge; the page frame's white top line
    runs from the selected tab's right edge to the frame's right."""
    mine, theirs = ours[look], original(look)
    boxes = LOOKS[look]["tab_boxes"]
    selected = (boxes[0][0] - 2, boxes[0][1] + 2)
    expected_white = [(1, 1), (selected[0], selected[0])] + [(left, left) for left, _right in boxes[2:]]
    expected_dark = [(right, right) for _left, right in [selected] + boxes[1:]] + [(mine.width - 1, mine.width - 1)]
    assert tab_edges(theirs) == (expected_white, expected_dark)

    # Ours within 2px: our font's captions are a pixel or two narrower or wider than the originals'.
    def near(ours_runs, expected_runs):
        return len(ours_runs) == len(expected_runs) and all(
            within(o, e, 2) for o, e in zip(ours_runs, expected_runs, strict=False)
        )

    assert near(tab_edges(mine)[0], expected_white) and near(tab_edges(mine)[1], expected_dark), tab_edges(mine)

    def top_line(image, y):
        return [
            run
            for run in runs([x for x in range(image.width) if is_white(image.getpixel((x, y)))])
            if run[1] - run[0] > 20
        ]

    assert near(top_line(mine, SELECTED_TAB_TOP), [(selected[0] + 2, selected[1] - 2)])  # rounded corners
    assert near(top_line(mine, TAB_TOP), [(left + 2, right - 2) for left, right in boxes[1:]])
    assert near(top_line(mine, PAGE_TOP), [(selected[1] + 1, PAGE_RIGHT - 1)])


@pytest.mark.parametrize("look", STRIP_LOOKS)
def test_tab_captions_are_the_originals_words_where_the_original_puts_them(ours, look):
    """The caption's ink inside each tab, within a column or two (the selected one's rises with its tab;
    its focus rectangle is left out)."""
    mine, theirs = ours[look], original(look)
    for index, (left, right) in enumerate(LOOKS[look]["tab_boxes"]):
        inset = (
            (4, SELECTED_TAB_TOP + 4) if index == 0 else (2, TAB_TOP + 2)
        )  # inside the selected tab's focus rectangle
        box = (left + inset[0], inset[1], right - inset[0] + 1, PAGE_TOP - 3)
        mine_box, theirs_box = ink_box(mine, box), ink_box(theirs, box)
        # Left and rows within a column or two; the right edge within 4: our font runs a little narrower.
        assert (
            within(mine_box[:2] + mine_box[3:], theirs_box[:2] + theirs_box[3:], SLACK[look] + 1)
            and abs(mine_box[2] - theirs_box[2]) <= 4
        ), (LOOKS[look]["tabs"][index], mine_box, theirs_box)


@pytest.mark.parametrize("look", LOOKS)
def test_page_frame_runs_from_the_tabs_to_above_the_buttons(ours, look):
    mine, theirs = ours[look], original(look)
    white_columns, white_rows = long_lines(mine, is_white)
    assert (white_columns, PAGE_TOP in white_rows, set(white_rows) <= {1, TAB_TOP, PAGE_TOP}) == (
        [1, PAGE_LEFT],
        True,
        True,
    ), white_rows

    def below_title(lines):
        return (
            lines[0],
            [row for row in lines[1] if row > FRAME + TITLE],
        )  # the originals' title gradients are not dark all along

    assert below_title(long_lines(mine, is_dark)) == below_title(long_lines(theirs, is_dark))


@pytest.mark.parametrize("look", LOOKS)
def test_general_page_text_sits_in_the_originals_columns_and_rows(ours, look):
    """Each heading on the original's row, flush with its column; each value a row (18px) under the last,
    indented 18px; lines are compared by their first row and first ink column."""
    mine, theirs = ours[look], original(look)
    settings = LOOKS[look]
    x_from = settings["text_from"]
    our_lines, their_lines = (
        text_rows(mine, x_from, PAGE_TOP + 2, settings["text_rows_to"]),
        text_rows(theirs, x_from, PAGE_TOP + 2, settings["text_rows_to"]),
    )
    theirs_at = {top: x for top, _bottom, x in their_lines}
    assert all(abs(theirs_at.get(row, -99) - x) <= SLACK[look] for x, row in settings["headings"]), (
        settings["headings"],
        their_lines,
    )
    ours_at = {top: x for top, _bottom, x in our_lines}
    for top, _bottom, x in their_lines:
        matches = [candidate for candidate in ours_at if abs(candidate - top) <= SLACK[look]]
        assert matches and abs(ours_at[matches[0]] - x) <= SLACK[look] + 1, (top, x, sorted(ours_at.items()))


def picture_box(image, region, face):
    left, top, right, bottom = region
    points = [
        (x, y)
        for x in range(left, right)
        for y in range(top, bottom)
        if max(abs(a - b) for a, b in zip(image.getpixel((x, y)), face, strict=False)) > 24
    ]
    return (
        (min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points))
        if points
        else None
    )


@pytest.mark.parametrize("look", LOOKS)
def test_computer_picture_is_centred_on_the_originals(ours, look):
    """The picture (anything but the page's face) is centred where the original's is, within 4px, and at
    least 90px wide; its art, and so its exact size, is the icon set's."""
    region = (20, PAGE_TOP + 4, 190, 220)
    boxes = [picture_box(image, region, image.getpixel((30, PAGE_TOP + 6))) for image in (ours[look], original(look))]
    centres = [((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) for box in boxes]
    assert within(centres[0], centres[1], 4) and boxes[0][2] - boxes[0][0] >= 90, boxes


@pytest.mark.parametrize("look", LOOKS)
def test_buttons_are_75_by_23_where_the_original_puts_them(ours, look):
    """Each button's black bottom line, and its top: white on a plain button, black on the default (OK)."""
    settings = LOOKS[look]
    mine, top = ours[look], settings["buttons_top"]
    bottom = top + BUTTON_SIZE[1] - 1
    assert button_bottoms(mine, bottom - 2) == {
        (left, left + BUTTON_SIZE[0] - 1, bottom) for left in settings["buttons"].values()
    }
    tops = {
        caption: (
            "dark"
            if is_dark(mine.getpixel((left + 37, top)))
            else "white"
            if is_white(mine.getpixel((left + 37, top)))
            else "face",
            is_white(mine.getpixel((left + 37, top - 1))) or is_dark(mine.getpixel((left + 37, top - 1))),
        )
        for caption, left in settings["buttons"].items()
    }
    assert tops == {caption: ("dark" if caption == "OK" else "white", False) for caption in settings["buttons"]}


def test_2001_tabs_are_the_xp_list(sysprops):
    assert sysprops.TABS["2001"] == LOOKS["2001"]["tabs"]


def test_2001_tab_strip_shows_the_tabs_that_fit_the_page_in_one_row(sysprops, facts, qt_app):
    window = sysprops.build_window(facts, "2001")
    boxes = window.tabs.boxes
    window.close()
    assert (len(boxes), boxes[-1][1] < PAGE_RIGHT) == (5, True)


def test_2000_apply_button_is_disabled_and_the_others_carry_the_originals_captions(sysprops, facts, qt_app):
    from PySide6.QtWidgets import QPushButton

    window = sysprops.build_window(facts, "2000")
    buttons = {
        button.text(): button.isEnabled()
        for button in window.findChildren(QPushButton)
        if button.text() in ("OK", "Cancel", "Apply")
    }
    window.close()
    assert buttons == {"OK": True, "Cancel": True, "Apply": False}


def test_a_long_value_wraps_onto_the_next_rows_inside_the_page(sysprops, qt_app):
    """No ink right of the page frame; the long name takes more than one row, the rows below move down."""
    facts = sysprops.SystemFacts(
        os_name="Fedora Linux 44 (KDE Plasma Desktop Edition) with a very long name",
        kernel="6.17.1-300.fc44.x86_64",
        desktop="KDE Plasma 6.8.2",
        owner="Doctor",
        hostname="TARDIS",
        product_key="01902-OEM-0087094-44427",
        cpu_model="AMD Ryzen 9 7950X3D 16-Core Processor with a long description",
        logical_processors="32 logical processors",
        memory="64.0 GB RAM",
        display="",
        resources_free="90% free",
        filesystem="ext4",
        virtual_memory="8.0 GB",
    )
    window = sysprops.build_window(facts, "1998")
    window.show()
    qt_app.processEvents()
    image = qimage_to_pil(window.grab().toImage())
    window.close()
    # The page clips what runs past it: no ink in its last columns, just inside the frame's shadow line.
    beyond = [
        (x, y)
        for x in range(PAGE_RIGHT - 5, PAGE_RIGHT - 1)
        for y in range(PAGE_TOP + 2, LOOKS["1998"]["buttons_top"] - 12)
        if is_dark(image.getpixel((x, y)))
    ]
    rows = text_rows(image, LOOKS["1998"]["text_from"], PAGE_TOP + 2, LOOKS["1998"]["buttons_top"] - 12)
    assert beyond == [] and len(rows) > 13, (beyond[:5], len(rows))


def test_close_button_sinks_while_held_and_closes_on_release(sysprops, facts, qt_app):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    window = sysprops.build_window(facts, "1995")
    window.show()
    qt_app.processEvents()
    face = window.close_rect()
    corner = (face.left(), face.top())
    before = qimage_to_pil(window.grab().toImage()).getpixel(corner)
    QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, face.center())
    qt_app.processEvents()
    held = qimage_to_pil(window.grab().toImage()).getpixel(corner)
    still_open = window.isVisible()
    QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, face.center())
    qt_app.processEvents()
    assert (is_white(before), is_dark(held), still_open, window.isVisible()) == (True, True, True, False)
