import pytest
from PySide6.QtWidgets import QStyle

from . import luna_states
from .luna_tools_support import hex_rgb

STATES = ["normal", "hover", "pressed", "disabled"]


@pytest.fixture(scope="module")
def style(qt_app):
    import chicago95luna

    return chicago95luna.LunaStyle()


@pytest.fixture(scope="module")
def palette(qt_app):
    import chicago95luna

    return chicago95luna.luna_palette()


def colour_at(image, x, y):
    return image.pixelColor(x, y).name().upper()


def near(image, x, y, expected, tolerance=3):
    actual, wanted = image.pixelColor(x, y), hex_rgb(expected)
    return (
        max(abs(a - b) for a, b in zip((actual.red(), actual.green(), actual.blue()), wanted, strict=True)) <= tolerance
    )


def lightness_at(image, x, y):
    return image.pixelColor(x, y).lightness()


def test_states_gallery_is_written_for_the_preview(style, palette):
    luna_states.save_states_gallery(style, palette)
    assert (luna_states.PREVIEW_DIR / "states-gallery.png").stat().st_size > 0


@pytest.mark.parametrize(
    ("state", "x", "y", "colour"),
    [
        ("hover", 2, 10, "#FFF0CF"),
        ("hover", 3, 10, "#FDD889"),
        ("pressed", 37, 2, "#D0CBBF"),
        ("disabled", 37, 1, "#C9C7BA"),
        ("disabled", 37, 11, "#F5F4EA"),
        ("normal", 37, 1, "#003C74"),
    ],
)
def test_push_button_state_pixel(style, palette, state, x, y, colour):
    assert colour_at(luna_states.push_button(style, palette, state), x, y) == colour


def test_default_push_button_has_the_blue_ring_and_hover_default_has_the_orange_one(style, palette):
    default = luna_states.push_button(style, palette, "normal", default=True)
    hovered = luna_states.push_button(style, palette, "hover", default=True)
    assert (colour_at(default, 37, 2), colour_at(hovered, 2, 10)) == ("#CEE7FF", "#FFF0CF")


def test_focus_rectangle_is_a_dotted_black_line(style, palette):
    image = luna_states.focus_rectangle(style, palette)
    top_row = [colour_at(image, x, 0) for x in range(40)]
    assert 5 < top_row.count("#000000") < 30 and top_row.count("#FFFFFF") > 5


@pytest.mark.parametrize("checked", [True, False])
@pytest.mark.parametrize(
    ("state", "x", "y", "colour"),
    [
        ("normal", 0, 6, "#1C5180"),
        ("hover", 1, 6, "#FDDFA2"),
        ("hover", 11, 6, "#FAC45D"),
        ("pressed", 1, 1, "#C3C1B7"),
        ("disabled", 0, 6, "#CAC8BB"),
        ("disabled", 6, 2, "#FFFFFF"),
    ],
)
def test_check_box_state_pixel(style, palette, checked, state, x, y, colour):
    image = luna_states.indicator(style, palette, QStyle.PE_IndicatorCheckBox, state, checked)
    assert colour_at(image, x, y) == colour


def test_disabled_checked_check_box_mark_is_cac8bb_and_enabled_mark_is_green(style, palette):
    marks = [
        colour_at(luna_states.indicator(style, palette, QStyle.PE_IndicatorCheckBox, state, True), 8, 3)
        for state in ("normal", "disabled")
    ]
    assert marks == ["#21A121", "#CAC8BB"]


@pytest.mark.parametrize("checked", [True, False])
@pytest.mark.parametrize(
    ("state", "x", "y", "colour"),
    [
        ("hover", 1, 6, "#FDDFA2"),
        ("hover", 11, 6, "#FAC45D"),
        ("pressed", 3, 3, "#C6C5BA"),
        ("disabled", 6, 2, "#FFFFFF"),
    ],
)
def test_radio_button_state_pixel(style, palette, checked, state, x, y, colour):
    image = luna_states.indicator(style, palette, QStyle.PE_IndicatorRadioButton, state, checked)
    assert near(image, x, y, colour, 4)


@pytest.mark.parametrize(
    ("state", "y", "colour"),
    [("normal", 3, "#C9D8FC"), ("hover", 2, "#FFC73C"), ("pressed", 3, "#B7C9F3"), ("disabled", 3, "#F5F4EA")],
)
def test_combo_drop_button_state_pixel(style, palette, state, y, colour):
    assert near(luna_states.combo(style, palette, state), 110, y, colour, 4)


def test_combo_arrow_is_grey_when_disabled_and_slate_when_enabled(style, palette):
    arrows = [colour_at(luna_states.combo(style, palette, state), 107, 9) for state in ("normal", "disabled")]
    assert arrows == ["#4D6185", "#ACA899"]


@pytest.mark.parametrize(
    ("state", "y", "colour"),
    [("normal", 3, "#C9D8FC"), ("hover", 2, "#FFC73C"), ("pressed", 3, "#B7C9F3"), ("disabled", 3, "#F5F4EA")],
)
def test_spin_up_button_state_pixel(style, palette, state, y, colour):
    assert near(luna_states.spin(style, palette, state), 70, y, colour, 4)


def test_spin_down_button_stays_normal_while_the_up_button_is_hovered(style, palette):
    normal, hovered = (luna_states.spin(style, palette, state) for state in ("normal", "hover"))
    assert colour_at(hovered, 70, 17) == colour_at(normal, 70, 17)


@pytest.mark.parametrize(
    ("state", "x", "y", "colour"),
    [("normal", 10, 2, "#91A7B4"), ("hover", 10, 2, "#FFC73C"), ("selected", 10, 0, "#E68B2C")],
)
def test_tab_state_pixel(style, palette, state, x, y, colour):
    assert colour_at(luna_states.tab(style, palette, state), x, y) == colour


def test_scroll_bar_trough_is_the_beige_gradient_across_the_bar(style, palette):
    image = luna_states.scroll_bar(style, palette, "disabled", QStyle.SC_None)
    assert [colour_at(image, 0, 60), colour_at(image, 16, 60)] == ["#EEEDE5", "#FEFEFB"]


@pytest.mark.parametrize(
    ("state", "arrow"), [("normal", "#245CAB"), ("hover", "#245CAB"), ("pressed", "#245CAB"), ("disabled", "#C9C9C2")]
)
def test_scroll_bar_stepper_arrow_colour(style, palette, state, arrow):
    image = luna_states.scroll_bar(style, palette, state, QStyle.SC_ScrollBarSubLine)
    assert arrow in {colour_at(image, x, y) for x in range(5, 12) for y in range(5, 12)}


def test_scroll_bar_stepper_is_lighter_on_hover_and_darker_pressed(style, palette):
    lightness = [
        lightness_at(luna_states.scroll_bar(style, palette, state, QStyle.SC_ScrollBarSubLine), 3, 4)
        for state in ("hover", "normal", "pressed")
    ]
    assert lightness == sorted(lightness, reverse=True) and len(set(lightness)) == 3


def test_scroll_bar_slider_is_lighter_on_hover_and_darker_pressed(style, palette):
    lightness = [
        lightness_at(luna_states.scroll_bar(style, palette, state, QStyle.SC_ScrollBarSlider), 2, 40)
        for state in ("hover", "normal", "pressed")
    ]
    assert lightness == sorted(lightness, reverse=True) and len(set(lightness)) == 3


def test_scroll_bar_slider_has_the_four_line_grip_and_disabled_has_no_slider(style, palette):
    enabled = luna_states.scroll_bar(style, palette, "normal", QStyle.SC_None)
    disabled = luna_states.scroll_bar(style, palette, "disabled", QStyle.SC_None)
    grip = [colour_at(enabled, 8, y) for y in range(17, 100)].count("#98BAE9")
    assert (grip, "#98BAE9" in {colour_at(disabled, 8, y) for y in range(120)}) == (4, False)


def test_track_bar_groove_is_four_rows_dark_to_white(style, palette):
    image = luna_states.track_bar(style, palette, "normal")
    assert [colour_at(image, 10, y) for y in range(12, 16)] == ["#838383", "#ECECE7", "#F5F4EF", "#FFFFFF"]


def test_track_bar_thumb_hover_has_the_orange_accent_and_normal_has_none(style, palette):
    def colours(state):
        image = luna_states.track_bar(style, palette, state)
        return {colour_at(image, x, y) for x in range(120) for y in range(30)}

    assert ("#FBCB74" in colours("hover"), "#FBCB74" in colours("normal")) == (True, False)


def test_track_bar_thumb_pressed_is_a_different_face_than_normal(style, palette):
    normal, pressed = (luna_states.track_bar(style, palette, state) for state in ("normal", "pressed"))
    assert normal != pressed


@pytest.mark.parametrize(
    ("state", "x", "y", "colour"),
    [
        ("normal", 20, 20, "#ECE9D8"),
        ("hover", 20, 20, "#FFFFFF"),
        ("hover", 0, 20, "#7A98AF"),
        ("pressed", 0, 20, "#9D9D92"),
    ],
)
def test_tool_button_state_pixel(style, palette, state, x, y, colour):
    assert colour_at(luna_states.tool_button(style, palette, state), x, y) == colour


def test_tool_button_is_flat_until_hovered(style, palette):
    image = luna_states.tool_button(style, palette, "normal")
    assert {colour_at(image, x, y) for x in range(40) for y in range(40)} == {"#ECE9D8"}


@pytest.mark.parametrize(
    ("state", "x", "y", "colour"),
    [
        ("normal", 10, 10, "#ECE9D8"),
        ("hover", 10, 17, "#F8A900"),
        ("hover", 10, 18, "#F6C456"),
        ("hover", 10, 19, "#F8B31F"),
        ("pressed", 10, 10, "#D6D2C2"),
    ],
)
def test_header_section_state_pixel(style, palette, state, x, y, colour):
    assert colour_at(luna_states.header_section(style, palette, state), x, y) == colour


def test_menu_item_selected_is_blue_and_normal_is_white(style, palette):
    states = ["normal", "selected"]
    assert [colour_at(luna_states.menu_item(style, palette, state), 100, 10) for state in states] == [
        "#FFFFFF",
        "#316AC5",
    ]


def test_menu_item_disabled_text_is_grey(style, palette):
    def darkest(state):
        image = luna_states.menu_item(style, palette, state)
        return min(image.pixelColor(x, y).lightness() for x in range(30, 80) for y in range(21))

    assert (darkest("disabled") > 120, darkest("normal") < 60) == (True, True)


@pytest.mark.parametrize(
    ("state", "fill", "border"),
    [("normal", "#FFFFFF", "#7F9DB9"), ("disabled", "#ECE9D8", "#C9C7BA")],
)
def test_line_edit_state_pixels(style, palette, state, fill, border):
    image = luna_states.line_edit(style, palette, state)
    assert [colour_at(image, 60, 10), colour_at(image, 0, 10)] == [fill, border]


def test_group_box_label_is_blue_when_enabled_and_grey_when_disabled(style, palette):
    def bluest(state):
        image = luna_states.group_box(style, palette, state)
        return max(image.pixelColor(x, y).blue() - image.pixelColor(x, y).red() for x in range(120) for y in range(20))

    assert (bluest("normal") > 120, bluest("disabled") < 40) == (True, True)
