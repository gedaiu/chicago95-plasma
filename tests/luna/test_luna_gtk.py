import configparser
import importlib.util
import re
import subprocess
import sys

import pytest
from conftest import REPO
from PIL import Image

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
    "notebook > header.top > tabs > tab:checked",
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
            css(version)
            .replace(f"GTK {version}", "GTK")
            .replace(generator.indicator_backend_rules(version), "")
            .replace(generator.scrollbar_backend_rules(version), "")
            .replace(generator.scale_backend_rules(version), "")
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


def titlebar_text():
    return subprocess.run(
        [sys.executable, str(GENERATOR), "--titlebar"], capture_output=True, text=True, check=True
    ).stdout


def titlebar_rules():
    block = titlebar_text()
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


def test_title_labels_use_the_ten_point_caption_kwin_draws_luna_windows_with():
    assert [
        "font-size: 10pt;" in body for selectors, body in titlebar_rules() if selectors.strip().endswith(" .title")
    ] == [True] * 2


@pytest.mark.parametrize("version", ["3.0", "4.0"])
def test_message_dialog_buttons_stand_six_pixels_apart_inside_an_eleven_pixel_margin(version):
    text = css(version)

    assert (
        rule_bodies(text, "messagedialog .dialog-action-area > button:not(:first-child)"),
        rule_bodies(text, "messagedialog .dialog-action-box"),
    ) == (["  margin-left: 6px;"], ["  padding: 0 11px 11px 11px;"])


def frame_bands(body):
    bands = dict(re.findall(r"inset (-?\d+px 0|0 -\d+px) (#[0-9A-F]{6})", body))
    return {
        "left": [bands[f"{depth}px 0"] for depth in (1, 2, 3)],
        "right": [bands[f"-{depth}px 0"] for depth in (1, 2, 3)],
        "bottom": [bands[f"0 -{depth}px"] for depth in (1, 2, 3)],
        "depth": max(int(re.search(r"\d+", offset).group()) for offset in bands),
    }


def reference_frame(name):
    image = Image.open(REPO / "tests/references" / name).convert("RGB")
    width, height = image.size
    colour = "#{:02X}{:02X}{:02X}".format
    return {
        "left": [colour(*image.getpixel((x, height // 2))) for x in (0, 1, 2)],
        "right": [colour(*image.getpixel((width - 1 - x, height // 2))) for x in (0, 1, 2)],
        "bottom": [colour(*image.getpixel((width // 2, height - 1 - y))) for y in (0, 1, 2)],
        "depth": 3,
    }


def within(colour, reference, tolerance=2):
    return all(abs(int(colour[i : i + 2], 16) - int(reference[i : i + 2], 16)) <= tolerance for i in (1, 3, 5))


@pytest.mark.parametrize("reference", ["xprun.png", "xpfont.png", "xpcolour.png"])
def test_message_dialog_frame_is_the_three_pixel_frame_of_xp_fixed_dialogs(reference):
    frame = frame_bands(rule_bodies(css("3.0"), "messagedialog .dialog-vbox")[0])
    expected = reference_frame(reference)

    assert (
        frame["depth"],
        [
            within(colour, want)
            for side in ("left", "right", "bottom")
            for colour, want in zip(frame[side], expected[side])
        ],
    ) == (3, [True] * 9)


def test_inactive_message_dialog_frame_keeps_the_same_bands_of_the_inactive_window_frame():
    assert frame_bands(rule_bodies(css("3.0"), "messagedialog .dialog-vbox:backdrop")[0]) == {
        "left": ["#7480DC", "#758CDD", "#758CDC"],
        "right": ["#4F53BC", "#6D74CD", "#7587DD"],
        "bottom": ["#4F53BC", "#6D74CD", "#7586DC"],
        "depth": 3,
    }


def test_message_dialog_title_is_the_29_pixel_caption_of_xp_dialogs():
    assert "min-height: 29px;" in rule_bodies(css("3.0"), "messagedialog .titlebar")[0]


@pytest.mark.parametrize(
    ("state", "outer_left"), [("", "rgba(0, 5, 177, 0.78) 0px"), (":backdrop", "rgba(96, 100, 201, 1.0) 0px")]
)
def test_title_bar_darkens_towards_both_frame_edges_over_aurorae_corner_width(state, outer_left):
    body = rule_bodies(titlebar_text(), f"headerbar.titlebar{state}")[0]

    assert (
        f"linear-gradient(to right, {outer_left}" in body,
        "linear-gradient(to left, " in body,
        body.count("transparent 28px") == 2,
        body.index("to right") < body.index("to left") < body.index("to bottom"),
    ) == (True,) * 4


def test_title_side_shading_spans_the_aurorae_corner_width():
    aurorae = (REPO / "luna/aurorae/make_luna_aurorae.py").read_text()

    assert re.search(r"^CORNER_W, \w+, \w+ = (\d+),", aurorae, re.M).group(1) == str(generator.SIDE_SHADING_WIDTH)


def test_band_shadow_lists_the_deepest_band_first_because_gtk_paints_the_last_shadow_on_top():
    assert generator.band_shadow(None, None, ["#OUTER", "#INNER"], None) == "inset 2px 0 #INNER, inset 1px 0 #OUTER"


def test_message_dialog_body_keeps_its_content_off_the_frame():
    assert "padding: 0 3px 3px 3px;" in rule_bodies(css("3.0"), "messagedialog .dialog-vbox")[0]


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
