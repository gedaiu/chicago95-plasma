"""The Control Panel's Mouse pages after Mouse Properties (tests/references/win98mouse.png): the Buttons tab is laid
out where the original puts every part, measured from the page frame (whose top left is at (9, 49) in the picture),
and its settings are the button configuration, the double-click speed (with the test area) and, on Motion, the
pointer speed."""

import pytest
from conftest import REPO, load_script, needs_ui_font
from PIL import Image
from PySide6.QtWidgets import QRadioButton

ORIGINAL_FRAME = (9, 49)
FACE, SHADOW, WHITE, BLACK = (192, 192, 192), (128, 128, 128), (255, 255, 255), (0, 0, 0)
FOCUS_DOT = (63, 63, 63)  # the inverted face colour; the 16-colour original shows it black
INK = (BLACK, FOCUS_DOT)


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


@pytest.fixture(scope="session")
def original():
    return Image.open(REPO / "tests/references/win98mouse.png").convert("RGB")


def buttons_tab(control_panel, settings=None, **actions):
    return control_panel.build_tab("Mouse", "Buttons", settings or {}, control_panel.Actions(**actions))


def our_page(control_panel, qt_app):
    """The Mouse sheet's tabs in a TabControl whose page frame is as wide as the original's (386)."""
    control = control_panel.TabControl()
    for name in control_panel.PAGE_TABS["Mouse"]:
        control.addTab(control_panel.build_tab("Mouse", name, {}, control_panel.Actions()), name)
    control.resize(386, 349 + control.bar.height() - control_panel.TAB_SEAM)
    control.show()
    qt_app.processEvents()
    from reference import qimage_to_pil

    image = qimage_to_pil(control.grab().toImage())
    frame = (control.pane.x(), control.pane.y())
    return image, frame


def pixel(image, frame, x, y):
    return image.getpixel((frame[0] + x, frame[1] + y))


def ink_box(image, frame, left, top, right, bottom, colours=INK):
    points = [(x, y) for x in range(left, right) for y in range(top, bottom) if pixel(image, frame, x, y) in colours]
    return (min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points), max(y for _, y in points))


def first_ink_column(image, frame, left, top, right, bottom):
    return ink_box(image, frame, left, top, right, bottom)[0]


def layout_probes(image, frame):
    """Where the parts are, in page-frame coordinates, found the same way in the original and in ours."""
    shadow_rows = [y for y in range(10, 345) if sum(pixel(image, frame, x, y) == SHADOW for x in range(10, 380)) > 200]
    shadow_columns = [
        x for x in range(10, 380) if sum(pixel(image, frame, x, y) == SHADOW for y in range(10, 340)) > 150
    ]
    white_columns = [
        x for x in range(300, 380) if sum(pixel(image, frame, x, y) == WHITE for y in range(10, 340)) > 150
    ]
    return {
        "group rows": shadow_rows,
        "group left": shadow_columns[:1],
        "group right": white_columns[-1:],
        "radios": ink_box(image, frame, 20, 34, 160, 56),
        "picture": ink_box(image, frame, 140, 70, 250, 170, colours=(BLACK, SHADOW, WHITE, (0, 0, 128))),
        "left heading": first_ink_column(image, frame, 20, 70, 130, 80),
        "left lines": first_ink_column(image, frame, 20, 86, 130, 96),
        "right heading": first_ink_column(image, frame, 250, 70, 360, 80),
        "right lines": first_ink_column(image, frame, 250, 86, 360, 96),
        "groove": ink_box(image, frame, 50, 243, 220, 250, colours=(SHADOW,)),
        "slow": first_ink_column(image, frame, 20, 236, 60, 248),
        "fast": first_ink_column(image, frame, 200, 236, 250, 248),
        "test area label": first_ink_column(image, frame, 250, 218, 330, 230),
        "test area box": ink_box(image, frame, 250, 230, 345, 325, colours=(SHADOW,)),
        "test area white": ink_box(image, frame, 250, 230, 345, 325, colours=(WHITE,))[2:],
    }


@needs_ui_font
def test_our_buttons_tab_puts_every_part_where_mouse_properties_does(control_panel, qt_app, original):
    theirs = layout_probes(original, ORIGINAL_FRAME)
    ours = layout_probes(*our_page(control_panel, qt_app))

    assert ours == theirs


def test_the_mouse_sheet_has_the_originals_three_tabs(control_panel):
    assert control_panel.PAGE_TABS["Mouse"] == ("Buttons", "Pointers", "Motion")


def test_buttons_tab_fields_default_to_right_handed_and_a_500_ms_double_click(control_panel, qt_app):
    assert buttons_tab(control_panel).values() == {"MOUSE_HAND": "right", "DOUBLE_CLICK_MS": "500"}


def test_choosing_left_handed_and_a_slower_double_click_reports_both(control_panel, qt_app):
    tab = buttons_tab(control_panel)
    next(button for button in tab.findChildren(QRadioButton) if button.text() == "&Left-handed").setChecked(True)
    tab.speed.setValue(tab.speed.maximum())

    assert tab.values() == {"MOUSE_HAND": "left", "DOUBLE_CLICK_MS": "900"}


def test_the_slider_runs_from_slow_900_ms_on_the_left_to_fast_100_ms_on_the_right(control_panel, qt_app):
    tab = buttons_tab(control_panel, {"DOUBLE_CLICK_MS": "100"})

    assert (tab.speed.value(), tab.speed.maximum(), tab.speed.invertedAppearance()) == (tab.speed.minimum(), 900, True)


def test_the_test_area_opens_its_box_on_a_double_click_within_the_chosen_time_and_not_on_a_slow_one(
    control_panel, qt_app
):
    tab = buttons_tab(control_panel, {"DOUBLE_CLICK_MS": "300"})
    area = tab.test_area
    area.clicked_at(1000)
    area.clicked_at(1200)
    opened = area.open
    area.clicked_at(2000)
    area.clicked_at(2400)

    assert (opened, area.open) == (True, True)


def test_the_test_area_closes_the_box_again_on_the_next_double_click(control_panel, qt_app):
    area = buttons_tab(control_panel).test_area
    for at in (0, 100, 1000, 1100):
        area.clicked_at(at)

    assert area.open is False


def test_motion_tab_sets_the_pointer_speed_between_slow_and_fast(control_panel, qt_app):
    tab = control_panel.build_tab("Mouse", "Motion", {"POINTER_SPEED": "0.4"}, control_panel.Actions())

    assert (tab.values(), tab.pointer_speed.minimum(), tab.pointer_speed.maximum()) == (
        {"POINTER_SPEED": "0.4"},
        -10,
        10,
    )


def test_pointer_trails_are_shown_but_off_because_wayland_cannot_draw_them(control_panel, qt_app):
    tab = control_panel.build_tab("Mouse", "Motion", {}, control_panel.Actions())

    assert (tab.trails.isEnabled(), tab.trails.text(), "POINTER_TRAIL" in tab.fields) == (
        False,
        "Show pointer trails",
        False,
    )


def test_pointers_tab_keeps_the_pointer_size_choice(control_panel, qt_app):
    assert control_panel.build_tab("Mouse", "Pointers", {}, control_panel.Actions()).values() == {"CURSOR": "32"}


def test_mouse_keys_are_applied_by_the_mouse_component(control_panel):
    assert [control_panel.COMPONENTS_BY_KEY[key] for key in ("MOUSE_HAND", "DOUBLE_CLICK_MS", "POINTER_SPEED")] == [
        ("mouse",)
    ] * 3 and "mouse" in control_panel.INSTALL_ORDER
