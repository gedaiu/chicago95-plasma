"""Pixel tests: each kind of control against Tweak UI on Windows 2000 (tests/references/tweakui2000.jpg).

The screenshot is a JPEG, so colours are classed, not compared: W white, K black, S the shadow grey, f the face.
A control keeps the original's structure: a field's edge reads shadow, black, white; a group frame is a shadow
row over a white one; the slider's groove is shadow, black, face, white; a check box is a 10 pixel dark square.
"""
import pytest
from PySide6.QtWidgets import QCheckBox, QGroupBox, QLineEdit, QPushButton, QSlider

from PIL import Image

from conftest import REPO, load_script

from reference import qimage_to_pil


def classify(colour):
    brightness = sum(colour[:3]) // 3
    return "W" if brightness >= 235 else "K" if brightness <= 70 else "S" if 100 <= brightness <= 150 else "f" if 175 <= brightness <= 215 else "?"


def column(image, x, top, bottom):
    """The classes down a column, repeats merged and doubtful pixels left out."""
    classes = [classify(image.getpixel((x, y))) for y in range(top, bottom)]
    return [kind for position, kind in enumerate(classes) if kind != "?" and (position == 0 or kind != classes[position - 1])]


def contains(sequence, wanted):
    return any(sequence[start:start + len(wanted)] == wanted for start in range(len(sequence)))


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

    assert (contains(column(original, 155, 366, 396), ["S", "K", "W"]), contains(column(render(field), 30, 0, 22), ["S", "K", "W"])) == (True, True)


def test_a_group_frame_is_a_shadow_row_over_a_white_row_in_the_original_and_in_ours(original, qt_app):
    group = QGroupBox("Menu speed")
    group.resize(200, 60)

    assert (contains(column(original, 150, 92, 118), ["S", "W"]), contains(column(render(group), 150, 0, 20), ["S", "W"])) == (True, True)


def test_a_slider_groove_is_shadow_black_face_white_in_the_original_and_in_ours(original, qt_app):
    slider = QSlider()
    slider.setOrientation(slider.orientation().Horizontal)
    slider.setRange(0, 10)
    slider.setValue(0)
    slider.resize(200, 30)

    assert (contains(column(original, 60, 125, 165), ["S", "K", "f", "W"]), contains(column(render(slider), 150, 0, 30), ["S", "K", "f", "W"])) == (True, True)


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
    field = control_panel.ButtonWidthField()
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


# ---- the originals measured: tests/references/progressbar.png, listbox-selected.png, messagebox-yesnocancel.png, win98mycomputer.png

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

    assert ({right - left + 1 for left, right in chunks}, {after[0] - before[1] - 1 for before, after in zip(chunks, chunks[1:])},
            runs([navy(image.getpixel((330, y))) for y in range(100, 135)])[0]) == ({14}, {2}, (6, 26))


def test_our_progress_bar_draws_14_pixel_chunks_2_apart_in_a_21_row_bar(control_panel, qt_app):
    bar = control_panel.ClassicProgressBar()
    bar.setRange(0, 100)
    bar.setValue(50)
    bar.resize(200, 21)
    image = render(bar)
    middle = bar.height() // 2
    chunks = runs([navy(image.getpixel((x, middle))) for x in range(image.width)])

    assert ({right - left + 1 for left, right in chunks}, {after[0] - before[1] - 1 for before, after in zip(chunks, chunks[1:])},
            len(chunks), contains(column(image, 5, 0, 21), ["S", "K"])) == ({14}, {2}, 6, True)


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

    assert (isinstance(progress.bar, control_panel.ClassicProgressBar), progress.bar.value() != before, progress.pulse.isActive()) == (True, True, True)


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

    assert ([rect.size().toTuple() for rect in rects], [after.left() - before.right() - 1 for before, after in zip(rects, rects[1:])],
            abs(left - (question.width() - 1 - right)) <= 1, rects[0].top() - question.text.geometry().bottom() - 1) == ([(75, 23)] * 3, [6, 6], True, 18)


@pytest.mark.parametrize("name, answer", [("Yes", "yes"), ("No", "no"), ("Cancel", "cancel")])
def test_apply_question_answers_yes_no_or_cancel(control_panel, qt_app, name, answer):
    question = control_panel.ApplyQuestion(None)
    question.buttons[name].click()

    assert question.answer == answer


def test_the_original_scroll_bar_thumb_is_raised_white_edge_face_shadow_black():
    image = reference_image("win98mycomputer")
    row = [image.getpixel((x, 200)) for x in range(380, 400)]
    black = next(position for position, colour in enumerate(row) if colour == (0, 0, 0))
    white = max(position for position, colour in enumerate(row[:black]) if colour == (255, 255, 255))
    shadow = row[black - 1]

    assert (black - white > 8, {row[x] for x in range(white + 1, black - 1)}, 90 < sum(shadow) // 3 < 140) == (True, {(191, 191, 191)}, True)


def test_our_icon_views_scroll_bar_is_16_wide_with_a_dithered_track(control_panel, qt_app, tmp_path):
    from PySide6.QtCore import Qt
    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.resize(300, 200)
    window.show()
    qt_app.processEvents()
    bar = window.icon_view.verticalScrollBar()
    image = render(bar)
    middle = bar.height() // 2
    track = [image.getpixel((x, middle)) for x in range(2, 14)]

    assert (bar.isVisible(), bar.width(), len(set(track)), track[0] == track[2], track[1] == track[3]) == (True, 16, 2, True, True)


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

    assert ([classify(image.getpixel((x, middle))) for x in range(0, 3)], navy(image.getpixel((3, middle))),
            [classify(image.getpixel((30, y))) for y in (0, 1, 2)], navy(image.getpixel((30, 3)))) == (["S", "K", "f"], True, ["S", "K", "f"], True)


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
    counts = class_counts(render(disabled(chicago95ui.plain_disabled_text(QLineEdit("Log On to %h")), 200)), (3, 3, 190, 19))

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

    assert (image.getpixel((0, middle)), image.getpixel((1, middle)), image.getpixel((middle, 0)), image.getpixel((middle, bottom)), image.getpixel((middle, bottom - 1))) == (
        (0, 0, 0), (255, 255, 255), (0, 0, 0), (0, 0, 0), (255, 255, 255))


def test_our_drop_down_rows_are_13_pixels_and_highlighted_edge_to_edge(control_panel, qt_app):
    combo, popup = open_combo(control_panel, qt_app)
    view = combo.view()
    row = view.visualRect(view.model().index(0, 0))
    image = render(view.viewport())
    across = runs([navy(image.getpixel((x, row.top() + 1))) for x in range(image.width)])

    assert (row.height(), across[0][0] <= 2, across[-1][1] >= image.width - 3) == (13, True, True)


def test_our_drop_down_shows_eight_rows_then_scrolls(control_panel, qt_app):
    combo, popup = open_combo(control_panel, qt_app, count=12)

    assert (combo.maxVisibleItems(), combo.view().verticalScrollBar().isVisible(), combo.view().verticalScrollBar().width(), popup.height()) == (8, True, 16, 8 * 13 + 2)


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
