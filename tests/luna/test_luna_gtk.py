import configparser
import importlib.util
import re
import subprocess
import sys

import pytest
from conftest import REPO

GENERATOR = REPO / "luna/gtk/make_luna_gtk.py"
COMMITTED = REPO / "luna/gtk/Chicago95Luna"
spec = importlib.util.spec_from_file_location("make_luna_gtk", GENERATOR)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)

KEY_SELECTORS = [
    "button",
    "button:hover",
    "button:active",
    "button:disabled",
    "button.default",
    "entry",
    "entry:disabled",
    "check",
    "check:checked",
    "check:hover",
    "check:disabled",
    "radio",
    "radio:checked",
    "radio:disabled",
    "notebook > header > tabs > tab",
    "notebook > header > tabs > tab:checked",
    "menu",
    "menuitem:hover",
    "scrollbar slider",
    "scrollbar slider:hover",
    "progressbar > trough > progress",
    "scale slider",
    "headerbar.titlebar",
    "headerbar.titlebar:backdrop",
    "tooltip",
    "treeview header button",
    "spinbutton button",
    "switch",
    "switch:checked",
    "switch slider",
]
KEY_COLOURS = [
    "#003C74",
    "#FFC73C",
    "#7F9DB9",
    "#919B9C",
    "#ACA899",
    "#316AC5",
    "#FFFFE1",
    "#ECE9D8",
    "#1C5180",
    "#FFF0CF",
    "#E59700",
]


def css(version):
    return (COMMITTED / f"gtk-{version}" / "gtk.css").read_text()


def rule_bodies(text, selector):
    return re.findall(rf"(?:^|\n){re.escape(selector)}(?:, [^{{]+)? \{{\n(.*?)\n\}}", text, re.S)


def test_committed_theme_equals_generator_output(tmp_path):
    generator.write_theme(tmp_path)

    assert {
        path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()
    } == {path.relative_to(COMMITTED).as_posix(): path.read_bytes() for path in COMMITTED.rglob("*") if path.is_file()}


@pytest.mark.parametrize("version", ["3.0", "4.0"])
def test_css_has_a_rule_for_every_key_selector(version):
    text = css(version)

    assert [
        selector for selector in KEY_SELECTORS if not re.search(rf"(?:^|\n|, ){re.escape(selector)}(?:,| \{{)", text)
    ] == []


@pytest.mark.parametrize("version", ["3.0", "4.0"])
def test_css_carries_the_measured_luna_colours(version):
    text = css(version)

    assert [colour for colour in KEY_COLOURS if colour not in text] == []


def test_css_sets_tahoma_at_eight_points():
    assert "font-family: Tahoma" in css("3.0") and "font-size: 8pt" in css("3.0")


def test_button_has_a_one_pixel_blue_border_rounded_three():
    body = rule_bodies(css("3.0"), "button")[0]

    assert [line in body for line in ("border: 1px solid #003C74;", "border-radius: 3px;", "color: #000000;")] == [
        True
    ] * 3


def test_hover_button_gets_the_orange_light_and_dark_bands():
    body = rule_bodies(css("3.0"), "button:hover")[0]

    assert ("#FFF0CF" in body, "#E59700" in body, "#FDD889" in body, "#F8B330" in body) == (True, True, True, True)


def test_scroll_bar_trough_paints_a_stepper_arrow_at_each_end_and_keeps_the_slider_off_them():
    vertical, horizontal = (
        rule_bodies(css("4.0"), "scrollbar.vertical trough")[0],
        rule_bodies(css("4.0"), "scrollbar.horizontal trough")[0],
    )

    assert (
        vertical.count("assets/stepper-"),
        "padding: 17px 0;" in vertical,
        "background-position: center top, center bottom, center;" in vertical,
        horizontal.count("assets/stepper-"),
        "padding: 0 17px;" in horizontal,
    ) == (2, True, True, 2, True)


def test_scroll_bar_is_17_pixels_through_bar_range_and_trough_with_nothing_painted_beside_the_trough():
    text = css("4.0")
    bar, parts = (
        rule_bodies(text, "scrollbar")[0],
        rule_bodies(text, "scrollbar > range, scrollbar > range > trough, scrollbar contents, scrollbar trough")[0],
    )

    assert (
        "background-color: transparent;" in bar and "padding: 0;" in bar and "margin: 0;" in bar,
        "min-width: 17px;" in parts and "margin: 0;" in parts and "padding: 0;" in parts and "border: none;" in parts,
    ) == (True, True)


def test_scroll_bar_trough_gradient_runs_across_the_bar():
    vertical = rule_bodies(css("4.0"), "scrollbar.vertical trough")[0]

    assert "linear-gradient(to right, #EEEDE5 0%, #F4F3EE 50%, #FEFEFB 100%)" in vertical


def test_stepper_icon_is_the_blue_17_pixel_button_with_the_navy_arrow():
    svg = generator.stepper_svg("up")

    assert ('width="17" height="17"' in svg, "#245CAB" in svg, "#89B0E6" in svg, 'rx="2.5"' in svg) == (True,) * 4


def test_popover_contents_and_arrow_are_white_inside_the_menu_border_and_the_popover_itself_paints_nothing():
    text = css("4.0")
    contents, arrow, popover = (
        rule_bodies(text, selector)[0] for selector in ("popover > contents", "popover > arrow", "popover.background")
    )

    assert (
        "background-color: #FFFFFF;" in contents and "border: 1px solid #ACA899;" in contents,
        "background-color: #FFFFFF;" in arrow,
        "background-color: transparent;" in popover and "background-image: none;" in popover,
    ) == (True, True, True)


def test_gtk_three_and_four_share_the_widget_rules():
    def shared(version):
        return (
            css(version).replace(f"GTK {version}", "GTK")
            .replace(generator.indicator_backend_rules(version), "")
            .replace(generator.scrollbar_backend_rules(version), "")
            .replace(generator.input_backend_rules(version), "")
            .replace(generator.libadwaita_block(), "")
        )

    assert shared("3.0") == shared("4.0")


def test_gtk_four_feeds_libadwaita_the_luna_face_view_accent_and_corner_as_custom_properties():
    text = css("4.0")
    root = text[text.index(":root {") : text.index("}", text.index(":root {"))]

    assert [
        f"--{name}: {value};" in root
        for name, value in (
            ("window-bg-color", "#ECE9D8"),
            ("view-bg-color", "#FFFFFF"),
            ("headerbar-bg-color", "#ECE9D8"),
            ("popover-bg-color", "#FFFFFF"),
            ("accent-bg-color", "#316AC5"),
            ("border-color", "#D0D0BF"),
            ("window-radius", "6px"),
        )
    ] == [True] * 7


def test_gtk_four_shims_the_same_colours_for_plain_gtk_programs():
    assert (
        "@define-color window_bg_color #ECE9D8;" in css("4.0"),
        "@define-color accent_bg_color #316AC5;" in css("4.0"),
    ) == (True, True)


def test_gtk_three_gets_no_libadwaita_block():
    assert ":root" not in css("3.0")


def test_index_theme_parses_and_names_the_theme():
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(COMMITTED / "index.theme")

    assert (parser["Desktop Entry"]["Name"], parser["X-GNOME-Metatheme"]["GtkTheme"]) == (
        "Chicago95Luna",
        "Chicago95Luna",
    )


def test_titlebar_block_is_a_vertical_gradient_from_the_palette_with_six_pixel_corners():
    block = subprocess.run(
        [sys.executable, str(GENERATOR), "--titlebar"], capture_output=True, text=True, check=True
    ).stdout
    active = rule_bodies(block, "headerbar.titlebar")[0]

    assert (
        "linear-gradient(to bottom, #0058EE 0%" in active,
        active.rstrip().count("#0043CF 100%") == 1,
        "border-radius: 6px 6px 0 0;" in active,
        'font-family: "Trebuchet MS"' in active,
        "font-weight: bold;" in active,
        "color: #FFFFFF;" in active,
        "text-shadow: 1px 1px 0 #0A246A;" in active,
    ) == (True,) * 7


def test_inactive_titlebar_uses_the_inactive_palette_column():
    block = subprocess.run(
        [sys.executable, str(GENERATOR), "--titlebar"], capture_output=True, text=True, check=True
    ).stdout

    assert "linear-gradient(to bottom, #688DE0 0%" in block.split("\nheaderbar.titlebar:backdrop")[1]



def titlebar_rules():
    block = subprocess.run(
        [sys.executable, str(GENERATOR), "--titlebar"], capture_output=True, text=True, check=True
    ).stdout
    return re.findall(r"(?:^|\n)([^\n{]+) \{\n(.*?)\n\}", block, re.S)


def test_titlebar_block_paints_the_message_dialog_title_box_active_and_backdrop():
    selectors = {selector.strip() for line, _ in titlebar_rules() for selector in line.split(",")}

    assert {
        "messagedialog .titlebar",
        "messagedialog .titlebar .title",
        "messagedialog .titlebar:backdrop",
        "messagedialog .titlebar:backdrop .title",
    } <= selectors


def test_title_labels_get_the_caption_text_but_no_second_gradient_of_their_own():
    assert [
        ("background" in body, "color:" in body, "text-shadow: 1px 1px 0 #0A246A;" in body)
        for selectors, body in titlebar_rules()
        if selectors.strip().endswith(" .title")
    ] == [(False, True, True)] * 2


@pytest.mark.parametrize("version", ["3.0", "4.0"])
def test_message_dialog_buttons_stand_six_pixels_apart_inside_an_eleven_pixel_margin(version):
    text = css(version)

    assert (
        rule_bodies(text, "messagedialog .dialog-action-area > button:not(:first-child)"),
        rule_bodies(text, "messagedialog .dialog-action-box"),
    ) == (["  margin-left: 6px;"], ["  padding: 0 11px 11px 11px;"])


@pytest.mark.parametrize(
    ("selector", "outer_left", "outer_bottom"),
    [
        ("messagedialog .dialog-vbox", "#0019CF", "#00138C"),
        ("messagedialog .dialog-vbox:backdrop", "#5B68CD", "#4F53BC"),
    ],
)
def test_message_dialog_body_carries_the_four_pixel_luna_window_frame(selector, outer_left, outer_bottom):
    body = rule_bodies(css("3.0"), selector)[0]

    assert (
        f"inset 1px 0 {outer_left}" in body,
        f"inset 0 -1px {outer_bottom}" in body,
        f"inset -1px 0 {outer_bottom}" in body,
        "inset 0 1px" in body,
        "inset 5px" in body,
        body.rstrip(";").endswith(f"inset -1px 0 {outer_bottom}"),
    ) == (True, True, True, False, False, True)


def test_band_shadow_lists_the_deepest_band_first_because_gtk_paints_the_last_shadow_on_top():
    assert generator.band_shadow(None, None, ["#OUTER", "#INNER"], None) == "inset 2px 0 #INNER, inset 1px 0 #OUTER"


def test_message_dialog_body_keeps_its_content_off_the_frame():
    assert "padding: 0 4px 4px 4px;" in rule_bodies(css("3.0"), "messagedialog .dialog-vbox")[0]

PARSE_SCRIPT = """
import sys
import gi
gi.require_version("Gtk", sys.argv[1])
from gi.repository import Gtk
errors = []
provider = Gtk.CssProvider()
provider.connect("parsing-error", lambda _provider, section, error: errors.append((section.get_start_position(), error.message)))
provider.load_from_path(sys.argv[2])
print(errors)
"""


@pytest.mark.parametrize("version", ["3.0", "4.0"])
def test_gtk_parses_the_css_without_errors(version):
    result = subprocess.run(
        [sys.executable, "-c", PARSE_SCRIPT, version, str(COMMITTED / f"gtk-{version}" / "gtk.css")],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode:
        pytest.skip(f"GTK {version} is not available to PyGObject")

    assert result.stdout.strip() == "[]"
