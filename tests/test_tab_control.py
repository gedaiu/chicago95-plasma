"""The classic tab control: tabs that do not fit on a line wrap into rows, each row stretched to the full width,
and the row holding the selected tab sits against the page (tests/references/tweakui2000.jpg)."""
import pytest
from PIL import Image
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget

from conftest import REPO, load_script

ROW_PITCH = 18


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


def test_tabs_that_fit_on_one_line_keep_their_own_widths(control_panel):
    rows = control_panel.tab_rows([60, 70, 80], 400)

    assert rows == [[(0, 60), (1, 70), (2, 80)]]


def test_tabs_that_do_not_fit_wrap_into_rows_each_stretched_to_the_full_width(control_panel):
    rows = control_panel.tab_rows([80, 100, 120, 110, 70], 300)

    assert ([[index for index, _width in row] for row in rows], [sum(width for _index, width in row) for row in rows]) == ([[0, 1, 2], [3, 4]], [300, 300])


def test_the_extra_width_is_shared_among_the_tabs_of_a_wrapped_row(control_panel):
    rows = control_panel.tab_rows([50, 50, 50, 50], 160)

    assert ([width for _index, width in rows[0]], [width for _index, width in rows[1]]) == ([54, 53, 53], [160])


def test_a_tab_wider_than_the_control_gets_a_row_of_its_own(control_panel):
    rows = control_panel.tab_rows([50, 400, 50], 200)

    assert ([[index for index, _width in row] for row in rows], rows[1][0][1]) == ([[0], [1], [2]], 200)


@pytest.mark.parametrize("selected, order", [(0, [1, 2, 0]), (1, [2, 0, 1]), (2, [0, 1, 2])])
def test_the_row_of_the_selected_tab_moves_to_the_bottom_and_the_rows_after_it_to_the_top(control_panel, selected, order):
    rows = [[(0, 10)], [(1, 10)], [(2, 10)]]

    assert [row[0][0] for row in control_panel.rows_for_selected(rows, selected)] == order


@pytest.fixture
def tabs(control_panel, qt_app):
    control = control_panel.TabControl()
    for name in ("Cmd", "Desktop", "My Computer", "Control Panel", "Logon", "New", "Repair", "Paranoia", "Open", "Mouse", "General", "Explorer", "IE"):
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

    assert (control.count(), control.tabText(1), control.widget(1) is page, control.currentIndex(), control.stack.currentWidget() is control.widget(0)) == (2, "Two", True, 0, True)


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


def test_many_tabs_in_a_narrow_control_wrap_into_rows_as_wide_as_the_control(tabs):
    rects = tabs.bar.tab_rects()
    rows = sorted({rect.top() for index, rect in rects.items() if index != tabs.currentIndex()})
    row_rights = {top: max(rect.right() for index, rect in rects.items() if rect.top() == top) for top in rows}

    assert (len(rows) > 1, set(row_rights.values()) == {tabs.bar.width() - 1}) == (True, True)


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
    return [y for y in range(rect.top(), rect.bottom() + 1) if any(sum(image.getpixel((x, y))) // 3 < 100 for x in range(rect.left() + 3, rect.right() - 2))]


def test_unselected_tab_labels_sit_inside_their_tab_with_2_rows_to_spare_top_and_bottom(control_panel, qt_app):
    from PIL import Image
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
