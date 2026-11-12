"""Pixel tests: each kind of control against Tweak UI on Windows 2000 (tests/references/tweakui2000.jpg).

The screenshot is a JPEG, so colours are classed, not compared: W white, K black, S the shadow grey, f the face.
A control keeps the original's structure: a field's edge reads shadow, black, white; a group frame is a shadow
row over a white one; the slider's groove is shadow, black, face, white; a check box is a 10 pixel dark square.
"""

import os

import pytest
from conftest import REPO, load_script
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGroupBox, QLineEdit, QPushButton, QSlider
from reference import qimage_to_pil


def classify(colour):
    brightness = sum(colour[:3]) // 3
    return (
        "W"
        if brightness >= 235
        else "K"
        if brightness <= 70
        else "S"
        if 100 <= brightness <= 150
        else "f"
        if 175 <= brightness <= 215
        else "?"
    )


def column(image, x, top, bottom):
    """The classes down a column, repeats merged and doubtful pixels left out."""
    classes = [classify(image.getpixel((x, y))) for y in range(top, bottom)]
    return [
        kind
        for position, kind in enumerate(classes)
        if kind != "?" and (position == 0 or kind != classes[position - 1])
    ]


def contains(sequence, wanted):
    return any(sequence[start : start + len(wanted)] == wanted for start in range(len(sequence)))


def dark_box(image, box):
    left, top, right, bottom = box
    dark = [(x, y) for y in range(top, bottom) for x in range(left, right) if classify(image.getpixel((x, y))) == "K"]
    xs, ys = [x for x, _ in dark], [y for _, y in dark]
    return (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


@pytest.fixture(scope="session")
def original():
    return Image.open(REPO / "tests/references/tweakui2000.jpg").convert("RGB")


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


def render(widget):
    return qimage_to_pil(widget.grab().toImage())


def test_a_text_field_has_a_shadow_black_white_edge_in_the_original_and_in_ours(original, qt_app):
    field = QLineEdit("0")
    field.resize(60, 22)

    assert (
        contains(column(original, 155, 366, 396), ["S", "K", "W"]),
        contains(column(render(field), 30, 0, 22), ["S", "K", "W"]),
    ) == (True, True)


def test_a_group_frame_is_a_shadow_row_over_a_white_row_in_the_original_and_in_ours(original, qt_app):
    group = QGroupBox("Menu speed")
    group.resize(200, 60)

    assert (
        contains(column(original, 150, 92, 118), ["S", "W"]),
        contains(column(render(group), 150, 0, 20), ["S", "W"]),
    ) == (True, True)


def test_a_slider_groove_is_shadow_black_face_white_in_the_original_and_in_ours(original, qt_app):
    slider = QSlider()
    slider.setOrientation(slider.orientation().Horizontal)
    slider.setRange(0, 10)
    slider.setValue(0)
    slider.resize(200, 30)

    assert (
        contains(column(original, 60, 125, 165), ["S", "K", "f", "W"]),
        contains(column(render(slider), 150, 0, 30), ["S", "K", "f", "W"]),
    ) == (True, True)


def test_a_check_box_is_a_10_pixel_dark_square_in_the_original_and_in_ours(original, qt_app):
    box = QCheckBox("")
    box.resize(16, 16)

    assert (dark_box(original, (30, 256, 46, 272)), dark_box(render(box), (0, 0, 16, 16))) == ((10, 10), (10, 10))


def test_a_default_button_is_23_rows_with_a_black_frame_in_the_original_and_in_ours(original, qt_app):
    button = QPushButton("OK")
    button.setDefault(True)
    button.resize(75, 23)

    assert (dark_box(original, (110, 440, 200, 474))[1], dark_box(render(button), (0, 0, 75, 23))[1]) == (23, 23)


def test_our_slider_has_tick_marks_below_its_groove(control_panel, qt_app):
    field = control_panel.ButtonWidthField("1998")
    field.checkbox.setChecked(False)

    assert (field.slider.tickPosition(), field.slider.tickInterval() > 0) == (QSlider.TicksBelow, True)


def test_our_slider_draws_its_tick_marks(control_panel, qt_app):
    slider = QSlider()
    slider.setOrientation(slider.orientation().Horizontal)
    slider.setRange(0, 10)
    slider.setTickPosition(QSlider.TicksBelow)
    slider.setTickInterval(1)
    slider.resize(200, 40)
    image = render(slider)
    below_groove = [classify(image.getpixel((x, y))) for y in range(20, 40) for x in range(10, 190)]

    assert below_groove.count("K") > 8


# ---- the originals measured: tests/references/progressbar.png, listbox-selected.png,
# messagebox-yesnocancel.png, win98mycomputer.png


def navy(colour):
    return colour[2] > 90 and colour[0] < 60 and colour[1] < 60


def runs(flags):
    found, start = [], None
    for position, flag in enumerate(list(flags) + [False]):
        if flag and start is None:
            start = position
        if not flag and start is not None:
            found.append((start, position - 1))
            start = None
    return found


def reference_image(name):
    return Image.open(REPO / f"tests/references/{name}.png").convert("RGB")


def test_the_original_progress_bar_has_14_pixel_chunks_2_apart_in_a_21_row_bar():
    image = reference_image("progressbar")
    chunks = runs([navy(image.getpixel((x, 117))) for x in range(300, 460)])

    assert (
        {right - left + 1 for left, right in chunks},
        {after[0] - before[1] - 1 for before, after in zip(chunks, chunks[1:], strict=False)},
        runs([navy(image.getpixel((330, y))) for y in range(100, 135)])[0],
    ) == ({14}, {2}, (6, 26))


def test_our_progress_bar_draws_14_pixel_chunks_2_apart_in_a_21_row_bar(control_panel, qt_app):
    bar = control_panel.ClassicProgressBar()
    bar.setRange(0, 100)
    bar.setValue(50)
    bar.resize(200, 21)
    image = render(bar)
    middle = bar.height() // 2
    chunks = runs([navy(image.getpixel((x, middle))) for x in range(image.width)])

    assert (
        {right - left + 1 for left, right in chunks},
        {after[0] - before[1] - 1 for before, after in zip(chunks, chunks[1:], strict=False)},
        len(chunks),
        contains(column(image, 5, 0, 21), ["S", "K"]),
    ) == ({14}, {2}, 6, True)


def test_our_progress_chunks_fill_the_bar_at_100_and_vanish_at_0(control_panel, qt_app):
    bar = control_panel.ClassicProgressBar()
    bar.setRange(0, 100)
    bar.resize(200, 21)
    counts = []
    for value in (0, 100):
        bar.setValue(value)
        image = render(bar)
        counts.append(len(runs([navy(image.getpixel((x, 10))) for x in range(image.width)])))

    assert (counts[0], counts[1] >= 12) == (0, True)


def test_apply_progress_shows_a_classic_bar_that_moves_while_setup_runs(control_panel, qt_app):
    import sys

    progress = control_panel.ApplyProgress(None, [sys.executable, "-c", "import time; time.sleep(0.3)"])
    before = progress.bar.value()
    progress.start()
    progress.pulse.timeout.emit()
    progress.pulse.timeout.emit()

    assert (
        isinstance(progress.bar, control_panel.ClassicProgressBar),
        progress.bar.value() != before,
        progress.pulse.isActive(),
    ) == (True, True, True)


def test_the_original_list_box_highlights_the_whole_13_row_line_of_the_selected_entry():
    image = reference_image("listbox-selected")
    first, last = runs([navy(image.getpixel((100, y))) for y in range(50, 150)])[0]
    top_row = 50 + first
    across = runs([navy(image.getpixel((x, top_row))) for x in range(0, 130)])

    assert (last - first + 1, across[0][0] <= 23, across[-1][1] >= 118) == (13, True, True)


def test_our_launcher_list_highlights_the_whole_13_row_line_of_the_selected_entry(control_panel, qt_app):
    field = control_panel.LauncherList(lambda *_: "")
    field.set_value("applications:a.desktop,applications:b.desktop,applications:c.desktop")
    field.list_widget.setCurrentRow(1)
    field.resize(300, 120)
    field.show()
    qt_app.processEvents()
    image = render(field.list_widget.viewport())
    row = field.list_widget.visualItemRect(field.list_widget.item(1))
    across = runs([navy(image.getpixel((x, row.top() + 1))) for x in range(image.width)])

    assert (row.height(), across[0][0] <= 1, across[-1][1] >= image.width - 2) == (13, True, True)


def test_the_original_message_box_centres_75_by_23_buttons_18_rows_under_the_text():
    image = reference_image("messagebox-yesnocancel")
    edges = [x for x in range(60, 340) if sum(image.getpixel((x, 74))) // 3 < 140]
    left, right = edges[0], edges[-1]
    top = next(y for y in range(50, 90) if sum(image.getpixel((118, y))) // 3 < 60)
    bottom = next(y for y in range(90, 50, -1) if sum(image.getpixel((118, y))) // 3 < 60)
    text_bottom = max(y for y in range(30, 60) if any(sum(image.getpixel((x, y))) // 3 < 60 for x in range(20, 370)))

    assert (bottom - top + 1, abs(left - (image.width - 1 - right)) <= 6, top - text_bottom) == (23, True, 18)


def test_our_apply_question_centres_75_by_23_buttons_6_apart_18_rows_under_the_text(control_panel, qt_app):
    question = control_panel.ApplyQuestion(None)
    question.show()
    qt_app.processEvents()
    buttons = [question.buttons[name] for name in ("Yes", "No", "Cancel")]
    rects = [button.geometry() for button in buttons]
    left, right = rects[0].left(), rects[-1].right()

    assert (
        [rect.size().toTuple() for rect in rects],
        [after.left() - before.right() - 1 for before, after in zip(rects, rects[1:], strict=False)],
        abs(left - (question.width() - 1 - right)) <= 1,
        rects[0].top() - question.text.geometry().bottom() - 1,
    ) == ([(75, 23)] * 3, [6, 6], True, 18)


@pytest.mark.parametrize("name, answer", [("Yes", "yes"), ("No", "no"), ("Cancel", "cancel")])
def test_apply_question_answers_yes_no_or_cancel(control_panel, qt_app, name, answer):
    question = control_panel.ApplyQuestion(None)
    question.buttons[name].click()

    assert question.answer == answer


def test_the_original_scroll_bar_is_16_wide_with_a_dithered_track():
    """Date/Time Properties' open list (tests/references/win98datetime03.png) shows the track at 1:1."""
    image = reference_image("win98datetime03")
    row = [image.getpixel((x, 150)) for x in range(360, 390)]
    black = next(position for position, colour in enumerate(row) if colour == (0, 0, 0))
    track = row[black - 16 : black]

    assert (len(set(track)), track[0] == track[2], track[1] == track[3], set(track)) == (
        2,
        True,
        True,
        {(192, 192, 192), (255, 255, 255)},
    )


def test_our_icon_views_scroll_bar_is_16_wide_with_a_dithered_track(control_panel, qt_app, tmp_path):

    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.resize(300, 200)
    window.show()
    qt_app.processEvents()
    bar = window.icon_view.verticalScrollBar()
    image = render(bar)
    middle = bar.height() // 2
    track = [image.getpixel((x, middle)) for x in range(2, 14)]

    assert (bar.isVisible(), bar.width(), len(set(track)), track[0] == track[2], track[1] == track[3]) == (
        True,
        16,
        2,
        True,
        True,
    )


def test_the_original_progress_chunks_leave_a_face_pixel_inside_the_frame():
    image = reference_image("progressbar")
    row = [classify(image.getpixel((x, 117))) for x in range(318, 323)]

    assert (row[1], row[2], row[3], navy(image.getpixel((322, 117)))) == ("S", "K", "f", True)


def test_our_progress_chunks_leave_a_face_pixel_inside_the_frame(control_panel, qt_app):
    bar = control_panel.ClassicProgressBar()
    bar.setRange(0, 100)
    bar.setValue(56)
    bar.resize(120, 21)
    image = render(bar)
    middle = bar.height() // 2

    assert (
        [classify(image.getpixel((x, middle))) for x in range(0, 3)],
        navy(image.getpixel((3, middle))),
        [classify(image.getpixel((30, y))) for y in (0, 1, 2)],
        navy(image.getpixel((30, 3))),
    ) == (["S", "K", "f"], True, ["S", "K", "f"], True)


# ---- disabled controls: tests/references/win98disabled.png. A disabled field takes the window colour instead of
# white, and disabled text is engraved: shadow grey over a white copy one pixel down and right, never black.


def class_counts(image, box):
    counts = {}
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            kind = classify(image.getpixel((x, y)))
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def disabled(widget, width=None):
    widget.setEnabled(False)
    widget.resize(width or widget.sizeHint().width(), widget.sizeHint().height())
    return widget


def test_the_originals_disabled_combo_field_is_face_coloured_with_engraved_text_and_no_white():
    counts = class_counts(reference_image("win98disabled"), (118, 208, 340, 224))

    assert (counts.get("W", 0), counts["S"] > 100, counts["f"] > 2000) == (0, True, True)


def test_the_originals_disabled_button_caption_is_shadow_over_white_and_never_black():
    counts = class_counts(reference_image("win98disabled"), (262, 249, 360, 262))

    assert (counts.get("K", 0), counts["S"] > 100, counts["W"] > 100) == (0, True, True)


def test_our_disabled_combo_field_is_face_coloured_with_engraved_text_and_no_white(qt_app):
    import chicago95ui
    from PySide6.QtWidgets import QComboBox

    combo = chicago95ui.plain_disabled_text(QComboBox())
    combo.addItem("No Playback Devices")
    counts = class_counts(render(disabled(combo, 200)), (3, 3, 180, 19))

    assert (counts.get("W", 0), counts.get("S", 0) > 100, counts["f"] > 1000) == (0, True, True)


def test_our_disabled_button_caption_is_shadow_over_white_and_never_black(qt_app):
    counts = class_counts(render(disabled(QPushButton("Apply"))), (2, 2, 73, 21))

    assert (counts.get("K", 0), counts.get("S", 0) > 40, counts["W"] > 40) == (0, True, True)


def test_our_disabled_text_field_is_face_coloured(qt_app):
    import chicago95ui

    counts = class_counts(
        render(disabled(chicago95ui.plain_disabled_text(QLineEdit("Log On to %h")), 200)), (3, 3, 190, 19)
    )

    assert counts.get("W", 0) == 0


def test_our_disabled_check_box_label_is_engraved(qt_app):
    counts = class_counts(render(disabled(QCheckBox("Use only preferred devices."))), (18, 0, 150, 16))

    assert (counts.get("K", 0), counts["S"] > 100, counts["W"] > 100) == (0, True, True)


# ---- an open drop-down list: tests/references/combo-open.png (a smoothed capture at about twice the size, so it
# gives the structure: a 1px black border, rows highlighted edge to edge up to a scroll bar, eight rows shown).


def test_the_original_drop_down_list_has_a_black_border_and_highlights_a_row_up_to_its_scroll_bar():
    image = reference_image("combo-open")
    border_row = next(y for y in range(55, 70) if image.getpixel((200, y)) == (0, 0, 0))
    highlight = runs([navy(image.getpixel((x, 145))) for x in range(image.width)])
    scroll_bar_edge = next(x for x in range(340, image.width) if image.getpixel((x, 200)) == (0, 0, 0))

    assert (border_row < 70, highlight[0][0] < 30, scroll_bar_edge - highlight[-1][1] < 50) == (True, True, True)


def open_combo(control_panel, qt_app, count=9):
    import chicago95ui
    from PySide6.QtWidgets import QComboBox

    combo = chicago95ui.classic_combo(QComboBox())
    combo.addItems([f"Item {number}" for number in range(count)])
    combo.resize(200, 22)
    combo.show()
    combo.showPopup()
    qt_app.processEvents()
    return combo, combo.view().window()


def test_our_drop_down_list_has_a_1_pixel_black_border(control_panel, qt_app):
    _combo, popup = open_combo(control_panel, qt_app)
    image = render(popup)
    middle = popup.height() // 2

    bottom = popup.height() - 1

    assert (
        image.getpixel((0, middle)),
        image.getpixel((1, middle)),
        image.getpixel((middle, 0)),
        image.getpixel((middle, bottom)),
        image.getpixel((middle, bottom - 1)),
    ) == ((0, 0, 0), (255, 255, 255), (0, 0, 0), (0, 0, 0), (255, 255, 255))


def test_our_drop_down_rows_are_13_pixels_and_highlighted_edge_to_edge(control_panel, qt_app):
    combo, popup = open_combo(control_panel, qt_app)
    view = combo.view()
    row = view.visualRect(view.model().index(0, 0))
    image = render(view.viewport())
    across = runs([navy(image.getpixel((x, row.top() + 1))) for x in range(image.width)])

    assert (row.height(), across[0][0] <= 2, across[-1][1] >= image.width - 3) == (13, True, True)


def test_our_drop_down_shows_eight_rows_then_scrolls(control_panel, qt_app):
    combo, popup = open_combo(control_panel, qt_app, count=12)

    assert (
        combo.maxVisibleItems(),
        combo.view().verticalScrollBar().isVisible(),
        combo.view().verticalScrollBar().width(),
        popup.height(),
    ) == (8, True, 16, 8 * 13 + 2)


# ---- a pressed button (from a Windows 9x capture shown by the project owner, not kept as a file): a black frame,
# a shadow frame inside it on every side, the caption moved a pixel down and right, and the dotted focus rectangle.


def test_our_pressed_button_has_a_black_frame_then_a_shadow_frame_all_round(qt_app):
    button = QPushButton("OK")
    button.resize(75, 23)
    button.setDown(True)
    image = render(button)
    middle_x, middle_y = 37, 11
    column = [classify(image.getpixel((middle_x, y))) for y in (0, 1, 2, 20, 21, 22)]
    row = [classify(image.getpixel((x, middle_y))) for x in (0, 1, 2, 72, 73, 74)]

    assert (column, row) == (["K", "S", "f", "f", "S", "K"], ["K", "S", "f", "f", "S", "K"])


def caption_ink_box(image):
    xs, ys = [], []
    for y in range(3, 20):
        for x in range(3, 72):
            if classify(image.getpixel((x, y))) == "K":
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys)


def test_our_pressed_button_moves_its_caption_a_pixel_down_and_right(qt_app):
    button = QPushButton("OK")
    button.resize(75, 23)
    released = caption_ink_box(render(button))
    button.setDown(True)
    pressed = caption_ink_box(render(button))

    assert (pressed[0] - released[0], pressed[1] - released[1]) == (1, 1)


def test_the_originals_closed_drop_down_field_is_white():
    image = reference_image("combo-open")

    assert image.getpixel((300, 30)) == (255, 255, 255)


def test_our_enabled_drop_down_field_is_white_and_a_disabled_one_takes_the_window_colour(control_panel, qt_app):
    import chicago95ui
    from PySide6.QtWidgets import QComboBox

    fields = []
    for enabled in (True, False):
        combo = chicago95ui.classic_combo(QComboBox())
        combo.addItem("720x576 High Color")
        combo.setEnabled(enabled)
        combo.setFocusPolicy(Qt.NoFocus)
        combo.resize(200, 22)
        combo.show()
        qt_app.processEvents()
        image = render(combo)
        fields.append((classify(image.getpixel((150, 11))), classify(image.getpixel((30, 4)))))

    assert fields == [("W", "W"), ("f", "f")]


# ---- a property sheet: tests/references/win98propertysheet.png (Regional Settings Properties). The dialog's border is
# 3px on every side (light, white, face; black, shadow, face), so its client area is the picture less 3 each side,
# less the 18px title bar at the top.

DIALOG_BORDER = 3


def test_the_original_property_sheet_has_6_pixel_side_margins_and_buttons_7_above_the_bottom_6_under_the_page():
    image = reference_image("win98propertysheet")
    column = [y for y in range(400, image.height) if sum(image.getpixel((195, y))) // 3 < 60]
    page_bottom, button_top, button_bottom = column[0], column[1], column[-2]
    edges = [x for x in range(150, 400) if image.getpixel((x, 425)) == (0, 0, 0)]
    client_right, client_bottom = image.width - 1 - DIALOG_BORDER, image.height - 1 - DIALOG_BORDER
    frame_left = next(x for x in range(DIALOG_BORDER, 20) if image.getpixel((x, 200)) == (255, 255, 255))

    assert (
        button_top - page_bottom - 1,
        button_bottom - button_top + 1,
        client_bottom - button_bottom,
        client_right - edges[-1],
        frame_left - DIALOG_BORDER,
        edges[0],
    ) == (6, 23, 7, 6, 6, 158)


def test_our_property_page_has_the_originals_margins(control_panel, qt_app, tmp_path):
    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.open_applet("Taskbar")
    window.resize(404, 560)
    window.show()
    qt_app.processEvents()
    page = window.pages.currentWidget()
    ok, cancel, apply = (getattr(page, name).geometry() for name in ("ok_button", "cancel_button", "apply_button"))
    page_bottom = page.tabs.geometry().bottom()

    assert (
        ok.size().toTuple(),
        cancel.left() - ok.left(),
        apply.left() - cancel.left(),
        ok.top() - page_bottom - 1,
        page.height() - 1 - ok.bottom(),
        page.width() - 1 - apply.right(),
        page.tabs.x(),
        page.width() - 1 - page.tabs.geometry().right(),
    ) == ((75, 23), 81, 81, 6, 7, 6, 6, 6)


def test_the_originals_focused_drop_down_fills_its_field_navy_inside_a_white_line():
    image = reference_image("win98propertysheet")

    assert (
        [image.getpixel((200, y)) for y in (108, 109, 110)],
        navy(image.getpixel((200, 118))),
        navy(image.getpixel((330, 118))),
    ) == ([(128, 128, 128), (0, 0, 0), (255, 255, 255)], True, True)


def test_our_focused_drop_down_fills_its_field_navy_inside_a_white_line(control_panel, qt_app):
    import chicago95ui
    from PySide6.QtWidgets import QComboBox

    combo = chicago95ui.classic_combo(QComboBox())
    combo.addItem("English (Australian)")
    combo.resize(312, 22)
    combo.show()
    combo.setFocus()
    qt_app.processEvents()
    image = render(combo)

    assert (
        [image.getpixel((150, y)) for y in (0, 1, 2)],
        navy(image.getpixel((150, 11))),
        navy(image.getpixel((8, 11))),
        navy(image.getpixel((280, 11))),
    ) == ([(128, 128, 128), (0, 0, 0), (255, 255, 255)], True, True, True)


# ---- the same open list at 1:1 (tests/references/win98datetime03.png) and a disabled check box (win98datetime04.png,
# enabled in win98datetime02.png): a disabled box is filled with the window colour and its check is shadow grey.


def test_the_original_open_list_at_1_to_1_has_13_pixel_rows_a_black_border_and_a_highlight_touching_it():
    image = reference_image("win98datetime03")
    first, last = runs([navy(image.getpixel((300, y))) for y in range(100, 250)])[0]
    highlight_left = runs([navy(image.getpixel((x, 100 + first))) for x in range(image.width)])[0][0]
    border_left = next(x for x in range(10, 30) if image.getpixel((x, 150)) == (0, 0, 0))

    assert (last - first + 1, highlight_left - border_left, image.getpixel((200, 79))) == (13, 1, (0, 0, 0))


def test_the_originals_disabled_check_box_is_face_filled_with_a_shadow_check_and_the_enabled_one_white_with_black():
    disabled = reference_image("win98datetime04")
    enabled = reference_image("win98datetime02")
    disabled_inside = {disabled.getpixel((x, 287)) for x in range(23, 33)}
    enabled_inside = {enabled.getpixel((x, 287)) for x in range(24, 33)}

    assert (disabled_inside, enabled_inside) == ({(192, 192, 192), (128, 128, 128)}, {(255, 255, 255), (0, 0, 0)})


def check_box_inside(qt_app, enabled):
    box = QCheckBox("Automatically adjust clock")
    box.setChecked(True)
    box.setEnabled(enabled)
    box.resize(box.sizeHint())
    box.show()
    qt_app.processEvents()
    image = render(box)
    face = box.palette().window().color().getRgb()[:3]
    shadow = box.palette().dark().color().getRgb()[:3]
    return {image.getpixel((x, 8)) for x in range(2, 11)}, face, shadow


def test_our_disabled_check_box_is_face_filled_with_a_shadow_check(qt_app):
    inside, face, shadow = check_box_inside(qt_app, enabled=False)

    assert inside == {face, shadow}


def test_our_enabled_check_box_is_white_with_a_black_check(qt_app):
    inside, _face, _shadow = check_box_inside(qt_app, enabled=True)

    assert inside == {(255, 255, 255), (0, 0, 0)}


# ---- radio buttons: tests/references/win98shutdown2.png (and win98flowerbox.png, win98mouse.png). The 12px circle:
# a shadow arc top-left, black inside it, white at the bottom right, and a 4-2 black dot when checked.


def black_mask(image, left, top, size=12):
    return [
        "".join("K" if classify(image.getpixel((x, y))) == "K" else "." for x in range(left, left + size))
        for y in range(top, top + size)
    ]


def our_radio(qt_app, checked):
    from PySide6.QtWidgets import QRadioButton

    button = QRadioButton("Shut down")
    button.setChecked(checked)
    button.resize(button.sizeHint())
    return render(button)


@pytest.mark.parametrize("checked, original_top", [(True, 65), (False, 85)])
def test_our_radio_button_is_the_originals_circle_pixel_for_pixel(qt_app, checked, original_top):
    original = black_mask(reference_image("win98shutdown2"), 61, original_top)

    assert black_mask(our_radio(qt_app, checked), 0, 0) == original


def test_our_exclusive_menu_item_is_marked_with_a_bullet_not_a_tick(control_panel, qt_app, tmp_path):
    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    menu = window.view_menu
    menu.show()
    qt_app.processEvents()
    image = render(menu)
    rect = menu.actionGeometry(menu.actions()[0])
    rows = [
        sum(1 for x in range(rect.left(), rect.left() + 16) if classify(image.getpixel((x, y))) == "K")
        for y in range(rect.top(), rect.bottom() + 1)
    ]
    inked = [count for count in rows if count]

    assert (inked, inked == inked[::-1]) == ([2, 4, 4, 2], True)


# ---- the Screen Saver tab: tests/references/win98screensaver.png. A monitor drawing at the top shows a 152 by 112
# screen; the Screen Saver group holds the saver list with its Preview button on the same line, then Wait.


def test_the_originals_screen_saver_monitor_shows_a_152_by_112_screen():
    image = reference_image("win98screensaver")
    teal = [
        (x, y)
        for x in range(60, 300)
        for y in range(40, 200)
        if image.getpixel((x, y))[1] > 100 and image.getpixel((x, y))[0] < 60
    ]
    xs, ys = [x for x, _ in teal], [y for _, y in teal]

    assert (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1) == (152, 112)


def screen_saver_tab(control_panel):
    return control_panel.build_tab(
        "Display",
        "Screen Saver",
        {},
        control_panel.Actions(list_screensavers=lambda: [("maze", "Maze")], lock_timeout_minutes=lambda: 60),
    )


def test_our_screen_saver_tab_draws_a_monitor_with_a_152_by_112_screen_in_the_desktop_colour(control_panel, qt_app):
    tab = screen_saver_tab(control_panel)
    tab.resize(380, 360)
    tab.show()
    qt_app.processEvents()
    monitor = tab.monitor
    image = render(monitor)
    screen = monitor.screen_rect()
    inside = {
        image.getpixel((x, y))
        for x in range(screen.left(), screen.right() + 1, 7)
        for y in range(screen.top(), screen.bottom() + 1, 7)
    }

    assert ((screen.width(), screen.height()), inside) == ((152, 112), {(0, 128, 128)})


def test_our_screen_saver_group_has_the_preview_button_on_the_saver_lists_line(control_panel, qt_app):
    from PySide6.QtWidgets import QComboBox, QGroupBox

    tab = screen_saver_tab(control_panel)
    tab.resize(380, 360)
    tab.show()
    qt_app.processEvents()
    combo = tab.findChildren(QComboBox)[0]
    preview = next(button for button in tab.findChildren(QPushButton) if button.text() == "Preview")
    combo_middle = combo.mapTo(tab, combo.rect().center()).y()
    preview_middle = preview.mapTo(tab, preview.rect().center()).y()

    assert ([box.title() for box in tab.findChildren(QGroupBox)], abs(combo_middle - preview_middle) <= 1) == (
        ["Screen Saver"],
        True,
    )


def test_our_button_width_slider_has_narrow_and_wide_labels_at_its_ends_like_the_originals(control_panel, qt_app):
    from PySide6.QtWidgets import QLabel

    field = control_panel.ButtonWidthField("1998")
    labels = [label.text() for label in field.findChildren(QLabel)]

    assert ("Narrow" in labels, "Wide" in labels) == (True, True)


MONITOR_ORIGIN = (110, 60)  # the case's top-left corner in tests/references/win98screensaver.png


def monitor_classes(image, points, face):
    names = {(255, 255, 255): "W", (0, 0, 0): "K", (128, 128, 128): "S", face: ".", (0, 128, 128): "t"}
    return "".join(names.get(image.getpixel(point)[:3], "?") for point in points)


def our_monitor(control_panel, qt_app):
    monitor = control_panel.MonitorPreview("#008080")
    monitor.show()
    qt_app.processEvents()
    return monitor, render(monitor), monitor.palette().window().color().getRgb()[:3]


@pytest.mark.parametrize(
    "line", ["column through the middle", "row through the middle", "row through the stand", "column through the stand"]
)
def test_our_monitor_matches_the_originals_drawing_pixel_class_for_pixel_class(control_panel, qt_app, line):
    left, top = MONITOR_ORIGIN
    monitor, image, face = our_monitor(control_panel, qt_app)
    original = reference_image("win98screensaver")
    lines = {
        "column through the middle": [(90, y) for y in range(156)],
        "row through the middle": [(x, 60) for x in range(184)],
        "row through the stand": [(x, 149) for x in range(40, 150)],
        "column through the stand": [(110, y) for y in range(140, 156)],
    }

    assert monitor_classes(image, lines[line], face) == monitor_classes(
        original, [(x + left, y + top) for x, y in lines[line]], (192, 192, 192)
    )


def test_our_monitors_power_light_is_green_like_the_originals(control_panel, qt_app):
    _monitor, image, _face = our_monitor(control_panel, qt_app)
    original = reference_image("win98screensaver")
    left, top = MONITOR_ORIGIN

    assert [image.getpixel((x, y)) for x in (105, 106) for y in (149, 150)] == [
        original.getpixel((x + left, y + top)) for x in (105, 106) for y in (149, 150)
    ]


def test_our_whole_monitor_drawing_is_the_originals_pixel_for_pixel(control_panel, qt_app):
    left, top = MONITOR_ORIGIN
    monitor, image, face = our_monitor(control_panel, qt_app)
    original = reference_image("win98screensaver")
    ours = [monitor_classes(image, [(x, y) for x in range(monitor.width())], face) for y in range(monitor.height())]
    theirs = [
        monitor_classes(original, [(x + left, y + top) for x in range(monitor.width())], (192, 192, 192))
        for y in range(monitor.height())
    ]
    differing = [(y, ours[y], theirs[y]) for y in range(len(ours)) if ours[y] != theirs[y]]

    assert differing == []


def test_the_originals_monitor_sits_11_rows_under_the_page_frame_and_centred_on_it():
    image = reference_image("win98screensaver")
    frame_top = next(y for y in range(40, 60) if image.getpixel((380, y)) == (255, 255, 255))
    frame_left = next(x for x in range(5, 15) if image.getpixel((x, 200)) == (255, 255, 255))
    frame_right = next(x for x in range(image.width - 5, 380, -1) if image.getpixel((x, 200)) == (0, 0, 0))
    left, top = MONITOR_ORIGIN

    assert (top - frame_top, abs((left + 92) - (frame_left + frame_right) / 2) <= 1) == (11, True)


def test_our_monitor_sits_11_rows_under_the_page_frame_and_centred_on_it(control_panel, qt_app, tmp_path):
    actions = control_panel.Actions(list_screensavers=lambda: [("maze", "Maze")], lock_timeout_minutes=lambda: 60)
    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
    window.show()
    window.open_applet("Display")
    page = window.applet_sheet("Display")
    page.tabs.setCurrentIndex(1)
    qt_app.processEvents()
    monitor = page.settings_tabs[1].monitor
    monitor_top_left = monitor.mapTo(page.tabs.pane, monitor.rect().topLeft())
    pane = page.tabs.pane.rect()

    assert (monitor_top_left.y(), abs(monitor_top_left.x() + 92 - pane.center().x()) <= 1) == (11, True)


def test_the_originals_groups_run_from_15_to_14_pixels_inside_the_page_frames_outer_edges():
    image = reference_image("win98screensaver")
    row = [image.getpixel((x, 260)) for x in range(image.width)]
    frame_left, frame_right = 9, 394
    group_left = next(x for x in range(frame_left + 3, 60) if row[x] == (128, 128, 128))
    group_right = next(x for x in range(frame_right - 3, 340, -1) if row[x] == (255, 255, 255))

    assert (group_left - frame_left, frame_right - group_right) == (15, 14)


def test_our_groups_run_from_15_to_14_pixels_inside_the_page_frames_outer_edges(control_panel, qt_app, tmp_path):
    from PySide6.QtWidgets import QGroupBox

    actions = control_panel.Actions(list_screensavers=lambda: [("maze", "Maze")], lock_timeout_minutes=lambda: 60)
    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
    window.show()
    window.open_applet("Display")
    page = window.applet_sheet("Display")
    page.tabs.setCurrentIndex(1)
    qt_app.processEvents()
    pane = page.tabs.pane
    image = render(pane)
    group = page.tabs.widget(1).findChildren(QGroupBox)[0]
    y = group.mapTo(pane, group.rect().center()).y()
    row = [image.getpixel((x, y)) for x in range(image.width)]
    shadow = pane.palette().dark().color().getRgb()[:3]
    group_left = next(x for x in range(3, 60) if row[x] == shadow)
    group_right = next(x for x in range(image.width - 4, image.width - 60, -1) if row[x] == (255, 255, 255))

    assert (group_left, image.width - 1 - group_right) == (15, 14)


# ---- a slider: the Double-click speed slider of tests/references/win98mouse.png, 1:1. The groove spans the whole
# 137px control and the thumb travels inside it (left edge from x=72 to x=198), sitting at 135; a tick marks each end.

SLIDER_ORIGIN, SLIDER_SIZE = (72, 287), (137, 24)


def slider_classes(image, left, top, face):
    names = {(255, 255, 255): "W", (0, 0, 0): "K", (128, 128, 128): "S", face: "."}
    return [
        "".join(names.get(image.getpixel((left + x, top + y))[:3], "?") for x in range(SLIDER_SIZE[0]))
        for y in range(SLIDER_SIZE[1])
    ]


def test_our_slider_is_the_originals_pixel_for_pixel(qt_app):
    from PySide6.QtCore import Qt

    slider = QSlider(Qt.Horizontal)
    slider.setRange(0, SLIDER_SIZE[0] - 11)
    slider.setValue(135 - SLIDER_ORIGIN[0])
    slider.setTickPosition(QSlider.TicksBelow)
    slider.setTickInterval(SLIDER_SIZE[0] - 11)
    slider.resize(*SLIDER_SIZE)
    slider.show()
    qt_app.processEvents()
    face = slider.palette().window().color().getRgb()[:3]
    ours = slider_classes(render(slider), 0, 0, face)
    theirs = slider_classes(reference_image("win98mouse"), *SLIDER_ORIGIN, (192, 192, 192))

    assert [(row, ours[row], theirs[row]) for row in range(len(ours)) if ours[row] != theirs[row]] == []


def test_our_slider_without_ticks_is_as_tall_as_its_thumb(qt_app):
    from PySide6.QtCore import Qt

    slider = QSlider(Qt.Horizontal)

    assert slider.sizeHint().height() == 21


# ---- a group box's title, from three originals (win98screensaver.png, win98effects.png, win98mouse.png): the top line
# stops 7 pixels in, the title's ink starts 10 pixels in, and the line runs 4 rows under the top of the capitals.


def group_title_metrics(image, frame_left, frame_top, shadow):
    line = [x - frame_left for x in range(frame_left, frame_left + 30) if image.getpixel((x, frame_top))[:3] == shadow]
    line_end = (
        next(x for x in range(len(line)) if line[x] != x) - 1
        if any(line[x] != x for x in range(len(line)))
        else line[-1]
    )
    ink = [
        (x - frame_left, y - frame_top)
        for x in range(frame_left, frame_left + 40)
        for y in range(frame_top - 6, frame_top + 6)
        if image.getpixel((x, y))[:3] == (0, 0, 0)
    ]
    return line_end, min(x for x, _ in ink), -min(y for _, y in ink)


@pytest.mark.parametrize("name, frame_top", [("win98screensaver", 241), ("win98effects", 65), ("win98mouse", 68)])
def test_the_originals_group_titles_sit_10_pixels_in_with_the_line_stopping_at_6_and_running_4_rows_under_the_capitals(
    name, frame_top
):
    assert group_title_metrics(reference_image(name), 24, frame_top, (128, 128, 128)) == (6, 10, 4)


def test_our_group_titles_sit_where_the_originals_do(qt_app):
    from PySide6.QtWidgets import QGroupBox, QLabel, QStyle, QStyleOptionGroupBox, QVBoxLayout

    group = QGroupBox("Screen Saver")
    QVBoxLayout(group).addWidget(QLabel("x"))
    group.resize(200, 80)
    group.show()
    qt_app.processEvents()
    option = QStyleOptionGroupBox()
    group.initStyleOption(option)
    frame = group.style().subControlRect(QStyle.CC_GroupBox, option, QStyle.SC_GroupBoxFrame, group)

    assert group_title_metrics(
        render(group), frame.left(), frame.top(), group.palette().dark().color().getRgb()[:3]
    ) == (6, 10, 4)


# ---- push button captions, from five originals' OK, Cancel and Apply (all 75x23, top at y=415): the caption's ink is
# centred on the button to within half a pixel, and Apply is "&Apply", its A underlined.


def caption_ink(image, left, top, width=75, height=23):
    xs = [
        x
        for x in range(left + 3, left + width - 3)
        for y in range(top + 3, top + height - 4)
        if image.getpixel((x, y))[:3] in ((0, 0, 0), (128, 128, 128))
    ]
    return min(xs) - left, max(xs) - left


@pytest.mark.parametrize("name", ["win98propertysheet", "win98screensaver", "win98mouse", "win98effects"])
def test_the_originals_button_captions_are_centred_on_their_ink(name):
    image = reference_image(name)
    centres = [sum(caption_ink(image, left, 415)) / 2 for left in (158, 239, 320)]

    assert [abs(centre - 37) <= 0.5 for centre in centres] == [True, True, True]


@pytest.mark.parametrize(
    "caption, enabled", [("OK", True), ("Cancel", True), ("&Apply", False), ("Preview", True), ("Browse...", True)]
)
def test_our_button_captions_are_centred_on_their_ink(qt_app, caption, enabled):
    button = QPushButton(caption)
    button.setEnabled(enabled)
    button.resize(75, 23)
    button.show()
    qt_app.processEvents()

    assert abs(sum(caption_ink(render(button), 0, 0)) / 2 - 37) <= 0.5


def test_the_originals_apply_button_underlines_its_a(qt_app):
    image = reference_image("win98propertysheet")
    first_run = runs([image.getpixel((x, 431)) == (128, 128, 128) for x in range(320, 395)])[0]

    assert first_run == (24, 30)


def test_our_property_pages_apply_button_is_ampersand_apply(control_panel, qt_app, tmp_path):
    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.open_applet("Taskbar")

    assert window.pages.currentWidget().apply_button.text() == "&Apply"


# ---- a spin box: the year box of tests/references/win98datetime01.png, 1:1 (79x21 from x=115, y=79). Windows 98 put a
# 16x20 up-down control beside a 63x21 sunken edit field, outside its border; each arrow button is 16x10.

SPIN_ORIGIN, SPIN_SIZE, SPIN_DIGITS = (115, 79), (79, 21), (4, 4, 30, 16)  # the digits' box is left out: other glyphs


# The tech2u captures are 16-colour GIFs: Windows' 3D light, DFDFDF, is not in that palette and shows as C0C0C0, the
# face. So against them our light edges count as face; the true-colour captures pin the light itself (below).
SIXTEEN_COLOUR_LIGHT = (223, 223, 223)


def spin_classes(image, left, top, face):
    names = {(255, 255, 255): "W", (0, 0, 0): "K", (128, 128, 128): "S", face: ".", SIXTEEN_COLOUR_LIGHT: "."}
    digits_left, digits_top, digits_right, digits_bottom = SPIN_DIGITS
    return [
        "".join(
            "-"
            if digits_left <= x < digits_right and digits_top <= y < digits_bottom
            else names.get(image.getpixel((left + x, top + y))[:3], "?")
            for x in range(SPIN_SIZE[0])
        )
        for y in range(SPIN_SIZE[1])
    ]


def test_our_spin_box_is_the_originals_edit_field_and_up_down_control_pixel_for_pixel(qt_app):
    from PySide6.QtWidgets import QSpinBox

    spin = QSpinBox()
    spin.setRange(0, 3000)
    spin.setValue(1999)
    spin.setFocusPolicy(spin.focusPolicy().NoFocus)
    spin.resize(*SPIN_SIZE)
    spin.show()
    qt_app.processEvents()
    ours = spin_classes(render(spin), 0, 0, spin.palette().window().color().getRgb()[:3])
    theirs = spin_classes(reference_image("win98datetime01"), *SPIN_ORIGIN, (192, 192, 192))

    assert [(row, ours[row], theirs[row]) for row in range(SPIN_SIZE[1]) if ours[row] != theirs[row]] == []


def test_our_spin_box_is_21_rows_tall_like_the_originals(qt_app):
    from PySide6.QtWidgets import QSpinBox

    assert QSpinBox().sizeHint().height() == 21


# ---- a closed drop-down, 1:1: unfocused in win98datetime02.png (x=22, y=59), focused in win98datetime04.png (x=21,
# y=58), both 362x21. The text is left out (other glyphs); the focus rectangle's dots are compared as dark or light.

COMBO_SIZE = (362, 21)


def combo_classes(image, left, top, face, highlight):
    def kind(colour):
        names = {
            (255, 255, 255): "W",
            (0, 0, 0): "K",
            (128, 128, 128): "S",
            face: ".",
            highlight: "n",
            SIXTEEN_COLOUR_LIGHT: ".",
        }
        return names.get(colour[:3], "?")

    width, height = COMBO_SIZE
    return [
        "".join(
            "-" if 5 <= x < width - 30 and 4 <= y < 17 else kind(image.getpixel((left + x, top + y)))
            for x in range(width)
        )
        for y in range(height)
    ]


@pytest.mark.parametrize(
    "focused, reference, origin", [(False, "win98datetime02", (22, 59)), (True, "win98datetime04", (21, 58))]
)
def test_our_closed_drop_down_is_the_originals_pixel_for_pixel(control_panel, qt_app, focused, reference, origin):
    import chicago95ui
    from PySide6.QtWidgets import QComboBox, QWidget

    holder = QWidget()
    combo = chicago95ui.classic_combo(QComboBox(holder))
    combo.addItem("(GMT+10:00) Canberra, Melbourne, Sydney")
    combo.setGeometry(0, 0, *COMBO_SIZE)
    holder.resize(COMBO_SIZE[0] + 10, 40)
    holder.show()
    if focused:
        combo.setFocus()
    else:
        combo.setFocusPolicy(Qt.NoFocus)
    qt_app.processEvents()
    face, highlight = combo.palette().window().color().getRgb()[:3], combo.palette().highlight().color().getRgb()[:3]
    ours = combo_classes(render(combo), 0, 0, face, highlight)
    theirs = combo_classes(reference_image(reference), *origin, (192, 192, 192), (0, 0, 128))

    assert [(row, ours[row], theirs[row]) for row in range(COMBO_SIZE[1]) if ours[row] != theirs[row]] == []


# ---- the 3D light on sunken fields and raised arrow buttons, from the true-colour captures: Windows 95's and 98's
# Control Panel list views (tests/references/win95controlpanel.png, win98controlpanel.png) draw their sunken frame's
# inner bottom and right edges in DFDFDF, not the face.


@pytest.mark.parametrize(
    "name, point",
    [("win95controlpanel", (200, 411)), ("win95controlpanel", (438, 200)), ("win98controlpanel", (200, 440))],
)
def test_the_true_colour_originals_draw_a_sunken_frames_inner_light_edge_in_dfdfdf(name, point):
    assert all(abs(channel - 223) <= 2 for channel in reference_image(name).getpixel(point))


def light_edges(qt_app, widget, inner_bottom, inner_right, button_top_left=None):
    widget.setFocusPolicy(Qt.NoFocus)
    widget.show()
    qt_app.processEvents()
    image = render(widget)
    points = [inner_bottom, inner_right] + ([button_top_left] if button_top_left else [])
    return {image.getpixel(point)[:3] for point in points}, widget.palette().midlight().color().getRgb()[:3]


def test_our_spin_box_draws_its_inner_light_edge_and_its_buttons_outer_light_edge_in_the_3d_light(qt_app):
    from PySide6.QtWidgets import QSpinBox

    spin = QSpinBox()
    spin.resize(*SPIN_SIZE)
    colours, light = light_edges(qt_app, spin, (20, SPIN_SIZE[1] - 2), (SPIN_SIZE[0] - 18, 10), (SPIN_SIZE[0] - 16, 0))

    assert colours == {light}


def test_our_drop_down_draws_its_inner_light_edge_and_its_buttons_outer_light_edge_in_the_3d_light(qt_app):
    import chicago95ui
    from PySide6.QtWidgets import QComboBox

    combo = chicago95ui.classic_combo(QComboBox())
    combo.addItem("x")
    combo.resize(*COMBO_SIZE)
    colours, light = light_edges(
        qt_app, combo, (40, COMBO_SIZE[1] - 2), (COMBO_SIZE[0] - 2, 10), (COMBO_SIZE[0] - 18, 2)
    )

    assert colours == {light}


GROUP_TITLE_AT_SCALE = """
import io, json, sys
sys.path.insert(0, sys.argv[1])
import chicago95ui
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtWidgets import QGroupBox, QLabel, QStyle, QStyleOptionGroupBox, QVBoxLayout
from PIL import Image

app = chicago95ui.make_app("group-title")
group = QGroupBox("Chicago95 for Plasma")
QVBoxLayout(group).addWidget(QLabel("x"))
group.resize(200, 80)
group.show()
app.processEvents()
option = QStyleOptionGroupBox()
group.initStyleOption(option)
frame = group.style().subControlRect(QStyle.CC_GroupBox, option, QStyle.SC_GroupBoxFrame, group)
label = group.style().subControlRect(QStyle.CC_GroupBox, option, QStyle.SC_GroupBoxLabel, group)
image = group.grab().toImage()
scale = image.devicePixelRatio()
buffer = QBuffer()
buffer.open(QIODevice.WriteOnly)
image.save(buffer, "PNG")
picture = Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGB")
left, right = round((label.left() + 1) * scale), round((label.left() + label.width() - 1) * scale)
rows = range(round((frame.top() - 1) * scale), round((frame.top() + 3) * scale))
under_title = sorted({picture.getpixel((x, y)) for y in rows for x in range(left, right)})
print(json.dumps({"scale": scale, "colours": under_title, "shadow": group.palette().dark().color().getRgb()[:3]}))
"""


@pytest.mark.parametrize("scale", ["1", "1.5", "2"])
def test_the_frame_line_never_runs_under_a_group_title_at_any_screen_scale(scale, tmp_path):
    """Neither the frame's shadow row nor its white row shows under the title (its glyphs may be antialiased
    at a fractional scale, so only the frame's two colours are ruled out)."""
    import json
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c", GROUP_TITLE_AT_SCALE, str(REPO / "lib")],
        capture_output=True,
        text=True,
        timeout=60,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "QT_SCALE_FACTOR": scale,
            "SETUP_OS_RELEASE": "/dev/null",
            "HOME": str(tmp_path),
        },
        check=False,
    )
    assert result.returncode == 0, result.stderr[-800:]
    seen = json.loads(result.stdout.strip().splitlines()[-1])

    colours = set(map(tuple, seen["colours"]))

    assert (seen["scale"], tuple(seen["shadow"]) in colours, (255, 255, 255) in colours) == (float(scale), False, False)
