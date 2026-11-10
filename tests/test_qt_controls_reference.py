"""The Qt controls our style draws (tests/controls_gallery.py renders them) against the originals:
the 1998 Dialing Properties dialog (win98dialing.png, a palette GIF: exact pixels, its greys 123/189/222
against our 128/192/223) for the check box and radio button indicators, and rules the originals follow
for tabs and drop-downs.
"""
import pytest

from conftest import needs_ui_font
from reference import LOOK_2000_KDEGLOBALS, close, installed_look, screenshot

pytestmark = needs_ui_font

CHECK_BOX_ON, CHECK_BOX_OFF = (36, 247, 49, 260), (36, 312, 49, 325)   # 13x13, in win98dialing.png
RADIOS = (95, 276, 200, 296)                                             # the "Tone dial" and "Pulse dial" radios, on then off
READ_ONLY_FIELD = (152, 66, 427, 89)                                      # win98newconnection.png: "KWOM" selected, on the window colour
TOLERANCE = 12


def is_face(colour, face):
    return close(colour, face, 8)


def indicator_crops(image, region, face, count):
    """The indicators in a region, left to right: each the bounding box of what is not the face, split
    where a column of face pixels runs the whole height; count of them, the labels' text left out."""
    left, top, right, bottom = region
    columns = [x for x in range(left, right) if any(not is_face(image.getpixel((x, y)), face) for y in range(top, bottom))]
    groups = []
    for x in columns:
        if groups and x == groups[-1][-1] + 1:
            groups[-1].append(x)
        else:
            groups.append([x])
    crops = []
    for group in [group for group in groups if len(group) >= 11][:count]:   # the labels' letters are narrower
        rows = [y for y in range(top, bottom) if any(not is_face(image.getpixel((x, y)), face) for x in group)]
        crops.append(image.crop((group[0], rows[0], group[-1] + 1, rows[-1] + 1)))
    return crops


def same_pixels(ours, theirs):
    return ours.size == theirs.size and all(close(ours.getpixel((x, y)), theirs.getpixel((x, y)), TOLERANCE)
                                            for x in range(ours.width) for y in range(ours.height))


@pytest.fixture(scope="module")
def gallery(qt_app):
    import controls_gallery
    return controls_gallery


def test_check_box_indicators_are_the_originals_13px_boxes_with_its_tick(gallery, qt_app):
    """Off and on: shadow and black top-left lines, light and white bottom-right, a 9x9 white inside, the tick's seven rows."""
    image = gallery.render_control(qt_app, gallery.check_boxes)
    off, on = indicator_crops(image, (0, 0, image.width, image.height), image.getpixel((2, 2)), 2)
    original = screenshot("win98dialing")
    assert same_pixels(off, original.crop(CHECK_BOX_OFF)) and same_pixels(on, original.crop(CHECK_BOX_ON)), (off.size, on.size)


def test_radio_button_indicators_are_the_originals_12px_circles(gallery, qt_app):
    image = gallery.render_control(qt_app, gallery.radio_buttons)
    off, on = indicator_crops(image, (0, 0, image.width, image.height), image.getpixel((2, 2)), 2)
    original = screenshot("win98dialing")
    their_on, their_off = indicator_crops(original, RADIOS, original.getpixel((96, 277)), 2)
    # The originals' boxes run into their labels' focus dots and letters: compared on the circles' own 11x12.
    their_on, their_off = (crop.crop((0, 0, on.width, on.height)) for crop in (their_on, their_off))
    assert same_pixels(off, their_off) and same_pixels(on, their_on), (off.size, on.size)


def ink_rows(image, box):
    left, top, right, bottom = box
    rows = [y for y in range(top, bottom) if any(sum(image.getpixel((x, y))) < 150 for x in range(left, right))]
    return (rows[0], rows[-1]) if rows else None


def test_tab_captions_are_whole_on_every_tab(gallery, qt_app):
    """Qt's tab widget with our style: the unselected tabs' captions are as tall as the selected one's, so
    no letter loses its top row ("Details" lost its D's)."""
    from PySide6.QtWidgets import QTabBar
    rects = []

    def note_tabs(patch):
        bar = patch.findChild(QTabBar)
        origin = bar.mapTo(patch, bar.rect().topLeft())
        rects.extend(bar.tabRect(index).translated(origin.x(), origin.y()) for index in range(bar.count()))
    image = gallery.render_control(qt_app, gallery.tab_widget, inspect=note_tabs)
    heights = []
    for rect in rects:
        rows = ink_rows(image, (rect.left() + 4, rect.top() + 1, rect.right() - 3, rect.bottom()))
        heights.append(rows[1] - rows[0] + 1)
    assert heights == [heights[0]] * len(rects) and heights[0] >= 9, (heights, rects)


@pytest.mark.parametrize("look, kdeglobals", [("1995", ""), ("2000", LOOK_2000_KDEGLOBALS)])
def test_drop_down_field_is_white_inside_its_frame_when_enabled_and_the_window_colour_when_disabled(gallery, qt_app, look, kdeglobals):
    """Inside the 2px sunken frame and left of the arrow button, nothing but white and the text; disabled,
    nothing but the window colour and grey text (the 1998 original's disabled calling-card list)."""
    from PySide6.QtWidgets import QComboBox
    boxes = []

    def note_combos(patch):
        for combo in patch.findChildren(QComboBox):
            corner = combo.mapTo(patch, combo.rect().topLeft())
            boxes.append((combo.isEnabled(), corner.x(), corner.y(), combo.width(), combo.height()))
    with installed_look(qt_app, f"[StartMenu]\nstyle={look}\n", kdeglobals):
        image = gallery.render_control(qt_app, gallery.drop_down, inspect=note_combos)
        face = image.getpixel((2, 2))
        for (is_enabled, x, y, width, height), allowed in zip(boxes, ({(255, 255, 255), (0, 0, 0)}, {face, (128, 128, 128)})):
            left, top = x + 2, y + 2
            right, bottom = left + width - 4 - 16, top + height - 4
            colours = {image.getpixel((x, y)) for x in range(left, right) for y in range(top, bottom)}
            assert all(any(close(colour, one, TOLERANCE) for one in allowed) for colour in colours), (is_enabled, colours)


def test_read_only_field_shows_its_selected_text_on_the_window_colour(gallery, qt_app):
    """The 1998 wizard's field: a 2px sunken frame (shadow and black, light and white), the window colour
    inside instead of white, the selection navy with white letters."""
    from PySide6.QtWidgets import QLineEdit
    boxes = []
    gallery_image = gallery.render_control(qt_app, gallery.text_fields, inspect=lambda patch: boxes.extend(
        (edit.mapTo(patch, edit.rect().topLeft()).x(), edit.mapTo(patch, edit.rect().topLeft()).y(), edit.width(), edit.height())
        for edit in patch.findChildren(QLineEdit) if edit.isReadOnly()))
    (x, y, width, height), = boxes
    face = gallery_image.getpixel((2, 2))
    theirs = screenshot("win98newconnection").crop(READ_ONLY_FIELD)
    ours = gallery_image.crop((x, y, x + width, y + height))
    structure = lambda image: (image.getpixel((5, 0)), image.getpixel((5, 1)), image.getpixel((image.width - 2, 5)), image.getpixel((image.width - 1, 5)),
                               image.getpixel((5, image.height - 2)), image.getpixel((5, image.height - 1)))
    assert all(close(a, b, TOLERANCE) for a, b in zip(structure(ours), structure(theirs))), (structure(ours), structure(theirs))
    inside = {ours.getpixel((px, py)) for px in range(2, ours.width - 2) for py in range(2, ours.height - 2)}
    assert any(close(colour, face, 8) for colour in inside) and not any(close(colour, (255, 255, 255), 8) and False for colour in inside)
    assert any(close(colour, (0, 0, 128), 16) for colour in inside) and (255, 255, 255) in inside, inside   # the selection and its letters
    assert not any(close(colour, (255, 255, 255), 8) for colour in {ours.getpixel((px, 3)) for px in range(2, 6)}), "the field's own background is not white"


def test_open_drop_down_list_marks_its_selected_row_with_a_plain_highlight_and_no_focus_dots(qt_app):
    """The originals' open list: the selected row is one solid highlight block from edge to edge."""
    import chicago95ui
    from PIL import Image
    from PySide6.QtWidgets import QComboBox
    from reference import qimage_to_pil
    combo = chicago95ui.classic_combo(QComboBox())
    combo.addItems(["Solid color", "Picture", "Pattern"])
    combo.setFixedWidth(160)
    combo.show()
    combo.showPopup()
    qt_app.processEvents()
    popup = qimage_to_pil(combo.view().window().grab().toImage())
    combo.hidePopup()
    highlight = combo.palette().highlight().color().getRgb()[:3]
    row_rect = combo.view().visualRect(combo.view().model().index(0, 0))
    origin = combo.view().viewport().mapTo(combo.view().window(), row_rect.topLeft())
    top_edge = {popup.getpixel((x, origin.y())) for x in range(origin.x(), origin.x() + row_rect.width())}
    assert top_edge == {highlight}, top_edge


def test_focused_drop_down_shows_its_value_in_white_on_the_highlight(qt_app):
    """After a pick the drop-down keeps the focus: its value sits on the highlight, as the originals show
    it, never white letters on the white field."""
    import chicago95ui
    from PySide6.QtWidgets import QComboBox
    from reference import qimage_to_pil
    combo = chicago95ui.classic_combo(QComboBox())
    combo.addItems(["Hours as my language does", "24 hours"])
    combo.setFixedWidth(160)
    combo.show()
    combo.setCurrentIndex(1)
    combo.setFocus()
    qt_app.processEvents()
    image = qimage_to_pil(combo.grab().toImage())
    highlight = combo.palette().highlight().color().getRgb()[:3]
    field = {image.getpixel((x, y)) for x in range(4, 100) for y in range(4, combo.height() - 4)}
    assert highlight in field and (255, 255, 255) in field, field


@pytest.mark.parametrize("make", ["check_boxes", "radio_buttons"])
def test_disabled_indicator_keeps_its_white_outer_edge_around_a_window_coloured_inside(gallery, qt_app, make):
    """win98disabledgroup.png: a disabled box is the enabled one's frame, white bottom-right edge
    included, with only its inside turned to the window colour."""
    from PySide6.QtWidgets import QAbstractButton
    boxes = {}

    def note_buttons(patch):
        for button in patch.findChildren(QAbstractButton):
            corner = button.mapTo(patch, button.rect().topLeft())
            boxes[button.isEnabled()] = (corner.x(), corner.y(), corner.x() + 14, corner.y() + button.height())
    image = gallery.render_control(qt_app, getattr(gallery, make), inspect=note_buttons)
    face = image.getpixel((2, 2))
    (enabled,), (disabled,) = (indicator_crops(image, boxes[state], face, 1) for state in (True, False))
    middle, inside = disabled.width // 2, (3, 4)   # inside: clear of the tick and the dot
    assert (enabled.getpixel((middle, enabled.height - 1)), disabled.getpixel((middle, disabled.height - 1)), disabled.getpixel(inside)) \
        == ((255, 255, 255), (255, 255, 255), face)


DISABLED_DROP_DOWN_BUTTON = (195, 104, 217, 125)   # win98finddate.png: the "Modified" list's right end, frame to frame


def drop_down_image(qt_app, enabled):
    import chicago95ui
    from PySide6.QtWidgets import QComboBox
    from reference import qimage_to_pil
    combo = chicago95ui.classic_combo(QComboBox())
    combo.addItem("Modified")
    combo.setFixedWidth(105)
    combo.setEnabled(enabled)
    combo.show()
    qt_app.processEvents()
    image = qimage_to_pil(combo.grab().toImage())
    combo.close()
    return image


def test_disabled_drop_down_ends_in_the_originals_arrow_button_with_an_engraved_arrow(qt_app):
    """The Find window's disabled list: 21px tall, its button's 7-5-3-1 arrow grey with a white copy a pixel down and right."""
    ours = drop_down_image(qt_app, enabled=False)
    theirs = screenshot("win98finddate").crop(DISABLED_DROP_DOWN_BUTTON)
    assert same_pixels(ours.crop((ours.width - theirs.width, 0, ours.width, ours.height)), theirs), ours.size


def test_enabled_drop_down_arrow_is_a_black_7_5_3_1_triangle(qt_app):
    ours = drop_down_image(qt_app, enabled=True)
    face = ours.crop((ours.width - 16, 4, ours.width - 6, ours.height - 5))   # inside the button's bevel
    widths = [sum(1 for x in range(face.width) if face.getpixel((x, y)) == (0, 0, 0)) for y in range(face.height)]
    assert [width for width in widths if width] == [7, 5, 3, 1], widths
