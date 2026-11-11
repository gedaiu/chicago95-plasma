"""The classic tab control: tabs that do not fit on a line wrap into rows, each row stretched to the full width,
and the row holding the selected tab sits against the page (tests/references/tweakui2000.jpg)."""

import pytest
from conftest import REPO, load_script, needs_ui_font
from PIL import Image
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget

ROW_PITCH = 18


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


def test_tabs_that_fit_on_one_line_keep_their_own_widths(control_panel):
    rows = control_panel.tab_rows([60, 70, 80], 400)

    assert rows == [[(0, 60), (1, 70), (2, 80)]]


def test_tabs_that_do_not_fit_wrap_into_rows_each_stretched_to_the_full_width(control_panel):
    rows = control_panel.tab_rows([80, 100, 120, 110, 70], 300)

    assert (
        [[index for index, _width in row] for row in rows],
        [sum(width for _index, width in row) for row in rows],
    ) == ([[0, 1, 2], [3, 4]], [300, 300])


def test_the_extra_width_is_shared_among_the_tabs_of_a_wrapped_row(control_panel):
    rows = control_panel.tab_rows([50, 50, 50, 50], 160)

    assert ([width for _index, width in rows[0]], [width for _index, width in rows[1]]) == ([54, 53, 53], [160])


def test_a_tab_wider_than_the_control_gets_a_row_of_its_own(control_panel):
    rows = control_panel.tab_rows([50, 400, 50], 200)

    assert ([[index for index, _width in row] for row in rows], rows[1][0][1]) == ([[0], [1], [2]], 200)


@pytest.mark.parametrize("selected, order", [(0, [1, 2, 0]), (1, [2, 0, 1]), (2, [0, 1, 2])])
def test_the_row_of_the_selected_tab_moves_to_the_bottom_and_the_rows_after_it_to_the_top(
    control_panel, selected, order
):
    rows = [[(0, 10)], [(1, 10)], [(2, 10)]]

    assert [row[0][0] for row in control_panel.rows_for_selected(rows, selected)] == order


@pytest.fixture
def tabs(control_panel, qt_app):
    control = control_panel.TabControl()
    for name in (
        "Cmd",
        "Desktop",
        "My Computer",
        "Control Panel",
        "Logon",
        "New",
        "Repair",
        "Paranoia",
        "Open",
        "Mouse",
        "General",
        "Explorer",
        "IE",
    ):
        control.addTab(QWidget(), name)
    control.resize(340, 300)
    control.show()
    qt_app.processEvents()
    return control


def test_tab_control_lists_its_tabs_like_a_tab_widget(control_panel, qt_app):
    control = control_panel.TabControl()
    page = QWidget()
    control.addTab(QWidget(), "One")
    control.addTab(page, "Two")

    assert (
        control.count(),
        control.tabText(1),
        control.widget(1) is page,
        control.currentIndex(),
        control.stack.currentWidget() is control.widget(0),
    ) == (2, "Two", True, 0, True)


def test_choosing_a_tab_shows_its_page_and_tells_the_listener(control_panel, qt_app):
    control = control_panel.TabControl()
    for name in ("One", "Two"):
        control.addTab(QWidget(), name)
    heard = []
    control.currentChanged.connect(heard.append)
    control.setCurrentIndex(1)

    assert (control.currentIndex(), control.stack.currentWidget() is control.widget(1), heard) == (1, True, [1])


def test_choosing_the_tab_already_shown_tells_nobody(control_panel, qt_app):
    control = control_panel.TabControl()
    control.addTab(QWidget(), "One")
    heard = []
    control.currentChanged.connect(heard.append)
    control.setCurrentIndex(0)

    assert heard == []


def test_clicking_a_tab_chooses_it(tabs):
    target = tabs.bar.tab_rects()[3].center()
    QTest.mouseClick(tabs.bar, Qt.LeftButton, Qt.NoModifier, QPoint(target.x(), target.y()))

    assert tabs.currentIndex() == 3


def test_many_tabs_in_a_narrow_control_wrap_into_rows_2_pixels_inside_each_side(tabs, control_panel):
    rects = tabs.bar.tab_rects()
    rows = sorted({rect.top() for index, rect in rects.items() if index != tabs.currentIndex()})
    row_rights = {top: max(rect.right() for index, rect in rects.items() if rect.top() == top) for top in rows}

    assert (len(rows) > 1, set(row_rights.values()) == {tabs.bar.width() - 1 - control_panel.TAB_INSET}) == (True, True)


def test_tab_rows_are_18_pixels_apart(tabs):
    tops = sorted({rect.top() for index, rect in tabs.bar.tab_rects().items() if index != tabs.currentIndex()})

    assert [after - before for before, after in zip(tops, tops[1:])] == [ROW_PITCH] * (len(tops) - 1)


def test_choosing_a_tab_in_an_upper_row_brings_its_row_down_next_to_the_page(tabs):
    tabs.setCurrentIndex(0)
    rects = tabs.bar.tab_rects()
    lowest_others = max(rect.bottom() for index, rect in rects.items() if index != 0)

    assert rects[0].bottom() >= lowest_others


def test_the_selected_tab_stands_2_pixels_above_the_others_of_its_row(tabs):
    tabs.setCurrentIndex(0)
    rects = tabs.bar.tab_rects()
    others_in_its_row = [rect for index, rect in rects.items() if index != 0 and rect.top() == rects[0].top() + 2]

    assert others_in_its_row != []


def test_the_original_tab_rows_are_18_pixels_apart():
    image = Image.open(REPO / "tests/references/tweakui2000.jpg").convert("RGB")
    highlight_rows = [row for row in range(25, 100) if all(channel > 235 for channel in image.getpixel((200, row)))]

    assert [row for row in highlight_rows if row < 90][:3] == [31, 49, 67]


def single_row_control(control_panel, qt_app):
    control = control_panel.TabControl()
    for name in ("Taskbar Options", "Start Menu"):
        control.addTab(QWidget(), name)
    control.resize(400, 200)
    control.show()
    qt_app.processEvents()
    return control


def test_the_page_border_does_not_run_under_the_selected_tab_but_does_elsewhere(control_panel, qt_app):
    control = single_row_control(control_panel, qt_app)
    image = control.grab().toImage()
    face = control.palette().window().color().getRgb()[:3]
    selected = control.bar.tab_rects()[0]
    seam = range(control.bar.height() - 2, control.bar.height() + 2)
    under_selected = [image.pixelColor(selected.center().x(), row).getRgb()[:3] for row in seam]
    beyond_tabs = [image.pixelColor(control.width() - 30, row).getRgb()[:3] for row in seam]

    assert (set(under_selected) == {face}, (255, 255, 255) in beyond_tabs) == (True, True)


def ink_rows(image, rect):
    return [
        y
        for y in range(rect.top(), rect.bottom() + 1)
        if any(sum(image.getpixel((x, y))) // 3 < 100 for x in range(rect.left() + 3, rect.right() - 2))
    ]


def test_unselected_tab_labels_sit_inside_their_tab_with_2_rows_to_spare_top_and_bottom(control_panel, qt_app):
    from reference import qimage_to_pil

    control = single_row_control(control_panel, qt_app)
    image = qimage_to_pil(control.bar.grab().toImage())
    rect = control.bar.tab_rects()[1]
    rows = ink_rows(image, rect)

    assert (rows[0] - rect.top() >= 3, rect.bottom() - rows[-1] >= 3, rows != []) == (True, True, True)


def label_ink_height(control, index):
    from reference import qimage_to_pil

    image = qimage_to_pil(control.bar.grab().toImage())
    rows = ink_rows(image, control.bar.tab_rects()[index])
    return rows[-1] - rows[0] + 1 if rows else 0


def test_an_unselected_tab_label_is_as_tall_as_when_its_tab_is_selected(control_panel, qt_app):
    control = single_row_control(control_panel, qt_app)
    unselected = label_ink_height(control, 1)
    control.setCurrentIndex(1)
    qt_app.processEvents()

    assert (unselected >= 8, label_ink_height(control, 1)) == (True, unselected)


# ---- single-row tabs measured in tests/references/win98propertysheet.png, win98screensaver.png and win98effects.png:
# a tab is its label plus 6 pixels each side and never narrower than 42; the first starts 2 pixels inside the page
# frame, and the selected tab widens by 2 pixels on each side over its neighbours.


def tab_metrics_control(control_panel, qt_app, names, selected=0):
    control = control_panel.TabControl()
    for name in names:
        control.addTab(QWidget(), name)
    control.setCurrentIndex(selected)
    control.resize(398, 200)
    control.show()
    qt_app.processEvents()
    return control


def test_a_tab_is_its_label_plus_6_pixels_each_side_and_at_least_42_wide(control_panel, qt_app):
    from PySide6.QtGui import QFontMetrics

    control = tab_metrics_control(control_panel, qt_app, ["Regional Settings", "Number", "Time"], selected=0)
    metrics = QFontMetrics(control.bar.font())
    rects = control.bar.tab_rects()

    assert (rects[1].width(), rects[2].width()) == (metrics.horizontalAdvance("Number") + 12, 42)


def test_the_first_tab_starts_2_pixels_inside_the_page_frame(control_panel, qt_app):
    control = tab_metrics_control(control_panel, qt_app, ["Background", "Screen Saver"], selected=1)

    assert control.bar.tab_rects()[0].left() == 2


def test_the_selected_tab_widens_by_2_pixels_on_each_side(control_panel, qt_app):
    from PySide6.QtGui import QFontMetrics

    control = tab_metrics_control(control_panel, qt_app, ["Background", "Screen Saver", "Appearance"], selected=1)
    metrics = QFontMetrics(control.bar.font())
    rects = control.bar.tab_rects()

    assert (rects[1].left(), rects[1].width()) == (
        rects[0].right() + 1 - 2,
        metrics.horizontalAdvance("Screen Saver") + 12 + 4,
    )


def test_a_selected_first_tab_widens_to_the_page_frame_but_not_past_it(control_panel, qt_app):
    control = tab_metrics_control(control_panel, qt_app, ["Background", "Screen Saver"], selected=0)

    assert control.bar.tab_rects()[0].left() == 0


# ---- the tab strip of tests/references/win98mouse.png (Buttons selected, Pointers, Motion), pixel by pixel: the strip
# starts at (9, 29) in the picture; a tab's edges, corners and the place of its caption are compared with the original's
# tab at the same index, whatever width our font gives the tab.

MOUSE_STRIP = (9, 29)
MOUSE_TABS = {"Buttons": (0, 0, 52, 22), "Pointers": (50, 2, 50, 18), "Motion": (100, 2, 44, 18)}
EDGE = 3


def tab_edges(image, left, top, width, height):
    """The tab's left and right EDGE columns, its top two rows between them, each as a tuple of pixels."""
    rows = range(top, top + height)
    left_columns = tuple(image.getpixel((x, y)) for y in rows for x in range(left, left + EDGE))
    right_columns = tuple(image.getpixel((x, y)) for y in rows for x in range(left + width - EDGE, left + width))
    top_rows = tuple(
        len({image.getpixel((x, top + row)) for x in range(left + EDGE, left + width - EDGE)}) for row in range(2)
    )
    top_colours = tuple(image.getpixel((left + EDGE, top + row)) for row in range(2))
    return left_columns, right_columns, top_rows, top_colours


def caption_place(image, left, top, width, height):
    """(first ink row, last ink row, first ink column) relative to the tab's top left."""
    ink = [
        (x, y)
        for y in range(top + 2, top + height - 2)
        for x in range(left + EDGE, left + width - EDGE)
        if sum(image.getpixel((x, y))) < 300
    ]
    return min(y for _, y in ink) - top, max(y for _, y in ink) - top, min(x for x, _ in ink) - left


@needs_ui_font
def test_the_mouse_properties_tab_strip_is_drawn_like_the_original(control_panel, qt_app):
    from reference import qimage_to_pil

    original = Image.open(REPO / "tests/references/win98mouse.png").convert("RGB")
    control = tab_metrics_control(control_panel, qt_app, list(MOUSE_TABS), selected=0)
    ours = qimage_to_pil(control.bar.grab().toImage())
    offset_x, offset_y = MOUSE_STRIP
    expected, actual = {}, {}
    for index, (name, (left, top, width, height)) in enumerate(MOUSE_TABS.items()):
        rect = control.bar.tab_rects()[index]
        expected[name] = (
            tab_edges(original, offset_x + left, offset_y + top, width, height),
            caption_place(original, offset_x + left, offset_y + top, width, height),
        )
        actual[name] = (
            tab_edges(ours, rect.left(), rect.top(), rect.width(), rect.height()),
            caption_place(ours, rect.left(), rect.top(), rect.width(), rect.height()),
        )

    assert actual == expected


def drawn_tab_rect(bar, index):
    """Where the style draws Qt's tab: the first and last tab rects carry the 2-pixel inset to the page frame, an
    unselected tab starts 2 rows down and stops above the page frame, the selected one spreads 2 pixels each side."""
    rect = bar.tabRect(index)
    first, last = index == 0, index == bar.count() - 1
    base = rect.adjusted(2 if first else 0, 0, -2 if last else 0, 0)
    if index == bar.currentIndex():
        return base.adjusted(-2, 0, 2, 0)
    return base.adjusted(0, 2, 0, -2)


@needs_ui_font
def test_qts_own_tab_bar_is_drawn_like_the_original(qt_app):
    from PySide6.QtWidgets import QTabWidget
    from reference import qimage_to_pil

    original = Image.open(REPO / "tests/references/win98mouse.png").convert("RGB")
    import chicago95ui

    tabs = QTabWidget()
    for widget in (tabs, tabs.tabBar()):
        widget.setStyle(chicago95ui.classic_style())  # other tools' tests leave their own style on the application
    for name in MOUSE_TABS:
        tabs.addTab(QWidget(), name)
    tabs.resize(398, 200)
    tabs.show()
    qt_app.processEvents()
    ours = qimage_to_pil(tabs.grab().toImage())
    offset_x, offset_y = MOUSE_STRIP
    expected, actual = {}, {}
    for index, (name, (left, top, width, height)) in enumerate(MOUSE_TABS.items()):
        rect = drawn_tab_rect(tabs.tabBar(), index).translated(tabs.tabBar().pos())
        expected[name] = (
            tab_edges(original, offset_x + left, offset_y + top, width, height),
            caption_place(original, offset_x + left, offset_y + top, width, height),
        )
        actual[name] = (
            tab_edges(ours, rect.left(), rect.top(), rect.width(), rect.height()),
            caption_place(ours, rect.left(), rect.top(), rect.width(), rect.height()),
        )

    assert (tabs.tabBar().pos().x(), tabs.tabBar().height(), actual) == (0, 22, expected)
