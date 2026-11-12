"""GTK 4's window buttons drawn as the 9x ones: a 16x14 face with the decoration's own glyphs, centred in the bar."""

import base64
import re

import gtk_header
import pytest
from conftest import run_bash_with_steps
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

CLOSE_GLYPH = {
    (4, 3), (5, 3), (10, 3), (11, 3),
    (5, 4), (6, 4), (9, 4), (10, 4),
    (6, 5), (7, 5), (8, 5), (9, 5),
    (7, 6), (8, 6),
    (6, 7), (7, 7), (8, 7), (9, 7),
    (5, 8), (6, 8), (9, 8), (10, 8),
    (4, 9), (5, 9), (10, 9), (11, 9),
}  # fmt: skip


def rule_body(css, selector):
    """Every declaration the sheet gives the selector, in order."""
    rules = re.findall(r"([^{}]+)\{([^}]*)\}", css)
    return "".join(body for selectors, body in rules if selector in (name.strip() for name in selectors.split(",")))


def face_image(css, selector):
    data = re.search(r"data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)", rule_body(css, selector)).group(1)
    image = QImage(16, 14, QImage.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    QSvgRenderer(QByteArray(base64.b64decode(data))).render(painter)
    painter.end()
    return image


def glyph_pixels(image):
    """The black pixels inside the bevel: the outer black line is the frame, not the glyph."""
    return {
        (x, y) for x in range(2, 14) for y in range(2, 12) if image.pixelColor(x, y) == QColor("#000000")
    }  # fmt: skip


@pytest.fixture(scope="module")
def css():
    return gtk_header.caption_css("#C0C0C0", "#DFDFDF", "#808080", "#000000")


def test_a_window_button_paints_one_16_by_14_face_centred_in_the_bar(css):
    body = rule_body(css, "headerbar windowcontrols.end > button")

    assert ("background-size: 16px 14px;" in body, "background-position: center;" in body) == (True, True)


def test_the_close_button_draws_the_decorations_x_on_the_face(qt_app, css):
    assert glyph_pixels(face_image(css, "headerbar windowcontrols.end > button.close")) == CLOSE_GLYPH


def test_a_pressed_close_button_draws_its_x_one_pixel_down_and_right(qt_app, css):
    shifted = {(x + 1, y + 1) for x, y in CLOSE_GLYPH}

    assert glyph_pixels(face_image(css, "headerbar windowcontrols.end > button.close:active")) == shifted


def test_a_maximized_window_shows_the_restore_glyph_on_its_maximize_button(qt_app, css):
    image = face_image(css, "window.maximized headerbar windowcontrols.end > button.maximize")

    assert image.pixelColor(5, 1) == QColor("#000000")


def test_the_face_takes_the_looks_face_colour(qt_app):
    css = gtk_header.caption_css("#D4D0C8", "#D4D0C8", "#808080", "#404040")

    assert face_image(css, "headerbar windowcontrols.end > button.close").pixelColor(2, 11).name() == "#d4d0c8"


def test_the_themes_symbolic_glyph_is_hidden_behind_the_drawn_face(css):
    assert "opacity: 0;" in rule_body(css, "headerbar windowcontrols.end > button > image")


def test_the_classic_title_bar_block_carries_the_9x_window_buttons_into_gtk_4(tmp_path):
    lines = run_bash_with_steps(
        tmp_path,
        'SETUP_DECORATION=classic; write_gtk_titlebar_css "#000080" "#808080" "#C0C0C0"; cat ~/.config/gtk-4.0/gtk.css',
    )

    assert "headerbar windowcontrols.end > button.close:active" in "\n".join(lines)


def test_the_hidden_glyph_loses_libadwaitas_padding_so_the_button_is_only_as_wide_as_its_face(css):
    assert "padding: 0;" in rule_body(css, "headerbar windowcontrols.end > button > image")


def test_an_unfocused_header_keeps_its_buttons_at_full_strength(css):
    assert "filter: none;" in rule_body(css, "headerbar:backdrop > windowhandle")


def test_an_unfocused_headers_raised_buttons_keep_black_labels(css):
    assert "color: #000000;" in rule_body(css, "window:backdrop headerbar button:not(.flat):not(:disabled) label")


@pytest.fixture(scope="module")
def strip():
    return gtk_header.header_css("#000080,#1084D0", "#808080,#C0C0C0", "#C0C0C0", "#C0C0C0")


def test_a_gnome_header_paints_the_active_title_colours_in_an_18px_strip_above_its_toolbar(strip):
    body = rule_body(strip, gtk_header.STRIP)

    assert (
        "linear-gradient(to right, #000080, #1084D0)" in body,
        "background-size: 100% 18px;" in body,
        "background-color: #C0C0C0;" in body,
    ) == (True, True, True)


def test_an_unfocused_gnome_header_paints_the_inactive_title_colours(strip):
    body = rule_body(strip, f"window:backdrop {gtk_header.STRIP}")

    assert "linear-gradient(to right, #808080, #C0C0C0)" in body


def test_the_sidebars_strip_keeps_the_start_colour_so_the_gradient_runs_on_without_a_seam(strip):
    assert "linear-gradient(to right, #000080, #000080)" in rule_body(strip, f".sidebar-pane {gtk_header.STRIP}")


def test_the_window_buttons_rise_from_the_toolbar_into_the_strip(strip):
    assert "margin-top: -20px;" in rule_body(strip, f"{gtk_header.STRIP} windowcontrols")


def test_the_window_title_rises_into_the_strip_in_white(strip):
    assert "color: #FFFFFF;" in rule_body(strip, f"{gtk_header.STRIP} windowtitle > .title")


def test_an_unfocused_windows_title_takes_the_inactive_title_text_colour(strip):
    assert "color: #C0C0C0;" in rule_body(strip, f"window:backdrop {gtk_header.STRIP} windowtitle > .title")


def test_an_unfocused_toolbar_view_keeps_its_header_at_full_strength(strip):
    assert "filter: none;" in rule_body(strip, "toolbarview > .top-bar:backdrop > windowhandle")


@pytest.fixture(scope="module")
def address():
    return gtk_header.path_bar_css("#DFDFDF", "#808080", "#000000")


def test_gnome_files_path_bar_is_a_sunken_white_address_field(address):
    body = rule_body(address, ".nautilus-pathbar")

    assert (
        "background-color: #FFFFFF;" in body,
        "border-color: #808080 #FFFFFF #FFFFFF #808080;" in body,
        "box-shadow: inset 1px 1px #000000, inset -1px -1px #DFDFDF;" in body,
    ) == (True, True, True)


def test_the_folders_in_the_address_field_are_flat_text_with_even_padding(address):
    body = rule_body(address, ".nautilus-pathbar .nautilus-path-button")

    assert ("margin: 0;" in body, "padding: 0 3px;" in body, "box-shadow: none;" in body) == (True, True, True)


def test_every_folder_name_in_the_address_field_is_plain_black_text(address):
    body = rule_body(address, ".nautilus-pathbar .nautilus-path-button label")

    assert ("font-weight: normal;" in body, "color: #000000;" in body) == (True, True)


def test_flat_toolbar_buttons_under_the_strip_draw_black_not_the_title_bars_white(strip):
    body = rule_body(strip, f"{gtk_header.STRIP} button.flat:not(:disabled) image")

    assert "color: #000000;" in body


def test_a_flat_menu_buttons_arrow_under_the_strip_draws_black(strip):
    assert "color: #000000;" in rule_body(strip, f"{gtk_header.STRIP} menubutton.flat > button:not(:disabled) arrow")


def test_a_lifted_window_buttons_face_sits_2px_under_the_strips_top(strip):
    assert "background-position: center 2px;" in rule_body(strip, f"{gtk_header.STRIP} windowcontrols > button")


def test_a_flat_split_buttons_arrow_under_the_strip_draws_black(strip):
    selector = f"{gtk_header.STRIP} splitbutton.flat > menubutton > button:not(:disabled) arrow"

    assert "color: #000000;" in rule_body(strip, selector)


@pytest.fixture(scope="module")
def frame():
    return gtk_header.frame_css("#C0C0C0", "#DFDFDF", "#808080", "#000000")


def test_a_self_drawn_window_gets_the_raised_9x_frame(frame):
    body = rule_body(frame, "window.csd")

    assert (
        "border-color: #DFDFDF #000000 #000000 #DFDFDF;" in body,
        "box-shadow: inset 1px 1px #FFFFFF, inset -1px -1px #808080, 0 0 3px 3px transparent;" in body,
        "padding: 3px;" in body,
        "border-radius: 0;" in body,
    ) == (True, True, True, True)


def test_a_maximized_window_loses_its_frame(frame):
    assert "padding: 0;" in rule_body(frame, "window.csd.maximized")


def test_the_sidebars_header_is_as_tall_as_the_contents(strip):
    assert "min-height: 31px;" in rule_body(strip, gtk_header.STRIP)


def test_a_toolbar_button_is_a_22px_square_centred_in_the_31px_row(strip):
    body = rule_body(strip, f"{gtk_header.STRIP} button.image-button")

    assert ("min-width: 22px;" in body, "min-height: 22px;" in body, "margin: 4px 0;" in body) == (True, True, True)


def test_the_lifted_title_fills_exactly_the_18px_strip_of_a_31px_row(strip):
    body = rule_body(strip, f"{gtk_header.STRIP} windowtitle")

    assert ("margin-top: -20px;" in body, "margin-bottom: 33px;" in body) == (True, True)


def test_the_lifted_window_buttons_give_back_their_50px_in_the_toolbar_row(strip):
    assert "margin-left: -50px;" in rule_body(strip, f"{gtk_header.STRIP} windowcontrols.end")


def test_the_lifted_window_icon_gives_back_its_20px_in_the_toolbar_row(strip):
    assert "margin-right: -20px;" in rule_body(strip, f"{gtk_header.STRIP} windowcontrols.start")


def test_header_text_is_11px_whatever_the_desktops_font_dpi(strip):
    assert "font-size: 11px;" in rule_body(strip, f"{gtk_header.STRIP} label")


def test_every_arrow_in_the_toolbar_is_black(strip):
    assert "color: #000000;" in rule_body(strip, f"{gtk_header.STRIP} arrow")


def test_the_window_frame_goes_into_gtk_4_only(tmp_path):
    lines = run_bash_with_steps(
        tmp_path,
        'SETUP_DECORATION=classic; write_gtk_titlebar_css "#000080" "#808080" "#C0C0C0"; '
        "grep -c window.csd ~/.config/gtk-3.0/gtk.css ~/.config/gtk-4.0/gtk.css",
    )

    assert [line.rsplit(":", 1)[1] != "0" for line in lines] == [False, True]


def test_the_window_buttons_keep_their_16_by_14_size_among_the_squared_toolbar_buttons(strip):
    assert "min-width: 16px;" in rule_body(strip, f"{gtk_header.STRIP} windowcontrols > button.image-button")


def test_the_split_buttons_arrow_names_its_icon_so_a_focused_window_draws_it(strip):
    assert "pan-down-symbolic" in rule_body(strip, f"{gtk_header.SPLIT_ARROW} > arrow")


def test_the_view_split_button_is_squared_like_the_other_toolbar_buttons(strip):
    assert "min-width: 22px;" in rule_body(strip, f"{gtk_header.STRIP} splitbutton > button")


def test_the_address_field_drops_libadwaitas_inner_padding(address):
    assert "padding-top: 0;" in rule_body(address, ".nautilus-pathbar button")


def test_the_sidebars_buttons_sit_1px_lower_to_line_up_with_the_contents(strip):
    assert "margin-top: 5px;" in rule_body(strip, f".sidebar-pane {gtk_header.STRIP} button.image-button")
