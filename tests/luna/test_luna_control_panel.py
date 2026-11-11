import pytest
from conftest import load_script
from PySide6.QtWidgets import QProgressBar, QTabWidget

from .luna_tools_support import CLASSIC_BEVEL_COLOURS, grab_picture, hex_rgb, reference, save_preview

FACE = "#ECE9D8"


@pytest.fixture
def control_panel(luna_look):
    return load_script("chicago95-control-panel")


@pytest.fixture
def window(control_panel, tmp_path):
    actions = control_panel.Actions(
        start_process=lambda program, arguments: None,
        run_setup=lambda parent, command: None,
        show_message=lambda parent, title, text: None,
        ask_to_apply=lambda parent: "cancel",
    )
    panel = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
    panel.resize(700, 520)
    panel.show()
    yield panel
    panel.close()


@pytest.fixture
def picture(window):
    image = grab_picture(window)
    save_preview(
        "controlpanel", image, reference("xpcontrolpanel.png").resize((image.width, int(image.width * 513 / 684)))
    )
    return image


def colours_of(image):
    return {colour for _count, colour in image.getcolors(maxcolors=1 << 22)}


def test_luna_window_chrome_is_the_xp_one(control_panel):
    names = [
        type(part).__name__ if not isinstance(part, type) else part.__name__ for part in control_panel.window_chrome()
    ]
    assert names[:5] == ["LunaHeaderBand", "LunaToolbarButton", "LunaStatusBar", "LunaStatusPane", "LunaLogoBox"]


def test_classic_look_keeps_the_classic_window_chrome(qt_app):
    chrome = load_script("chicago95-control-panel").window_chrome()
    assert [part.__name__ for part in chrome[:5]] == [
        "HeaderBand",
        "ToolbarButton",
        "ClassicStatusBar",
        "StatusPane",
        "LogoBox",
    ]


def test_header_toolbar_band_is_the_xp_face_under_a_white_line_with_no_grip(window):
    band = window.header.layout().itemAt(1).widget()
    image = grab_picture(band)
    row = [image.getpixel((x, 20)) for x in range(image.width - 60, image.width - 5)]
    assert (image.getpixel((image.width - 20, 0)), set(row)) == (hex_rgb("#FFFFFF"), {hex_rgb(FACE)})


def test_toolbar_band_left_edge_has_no_raised_grip_lines(window):
    image = grab_picture(window.header.layout().itemAt(1).widget())
    assert {image.getpixel((x, 20)) for x in range(0, 4)} == {hex_rgb(FACE)}


def test_header_bands_left_edges_are_the_face_under_the_white_line_in_every_band(window):
    bands = [window.header.layout().itemAt(index).widget() for index in range(3)]
    edges = [[grab_picture(band).getpixel((1, row)) for row in (0, 1, 3)] for band in bands]
    assert edges == [[hex_rgb("#FFFFFF"), hex_rgb(FACE), hex_rgb(FACE)]] * 3


def test_status_bar_edges_draw_no_classic_bevel_colours(window):
    image = grab_picture(window.statusBar())
    edge = {image.getpixel((x, y)) for x in (1, 2, image.width // 2) for y in range(image.height)}
    assert edge & (CLASSIC_BEVEL_COLOURS - {(0xC0, 0xC0, 0xC0)}) == set()


def test_status_bar_is_flat_xp_face_with_the_acd899_top_line(window, picture):
    status = window.statusBar()
    image = grab_picture(status)
    assert [image.getpixel((200, 0)), image.getpixel((200, 10))] == [hex_rgb("#ACA899"), hex_rgb(FACE)]


def test_status_bar_keeps_the_three_panes(window):
    assert len(window.status_panes) == 3


def test_toolbar_buttons_show_colour_icons_with_no_grip_and_rounded_light_hover(window):
    button = window.toolbar_buttons["Back"]
    assert (button.autoRaise(), button.iconSize().width()) == (True, 24)


def test_logo_box_is_white_with_the_flag(window):
    image = grab_picture(window.logo_box)
    colours = colours_of(image)
    assert (image.getpixel((1, 1)), len(colours) > 20) == (hex_rgb("#FFFFFF"), True)


def test_menu_bar_uses_the_luna_style(window):
    assert type(window.menu_bar.style()).__name__ == "LunaStyle"


def test_progress_bar_is_a_plain_progress_bar_under_luna(control_panel):
    bar = control_panel.window_chrome().progress_bar()
    assert type(bar) is not control_panel.ClassicProgressBar and isinstance(bar, QProgressBar)


def test_property_sheet_tabs_are_a_tab_widget_under_luna(control_panel, qt_app):
    assert control_panel.window_chrome().tab_control is QTabWidget


def test_appearance_preview_is_the_luna_mock_with_xp_title_rows(control_panel, qt_app):
    preview = control_panel.window_chrome().appearance_preview()
    preview.show_colors("#000080", "#808080", "#004E98", "luna")
    image = grab_picture(preview)
    save_preview("appearance-preview", image)
    active = preview.ACTIVE
    red, green, blue = image.getpixel((active.left() + 120, active.top() + 2))
    assert (blue > 200 and red < 100 and green > 90, (0, 0, 128) in colours_of(image)) == (True, False)


def test_appearance_preview_close_button_is_the_luna_red(control_panel, qt_app):
    preview = control_panel.window_chrome().appearance_preview()
    preview.show_colors("#000080", "#808080", "#004E98", "luna")
    image = grab_picture(preview)
    box = preview.ACTIVE
    reds = [image.getpixel((x, box.top() + 11)) for x in range(box.right() - 24, box.right() - 4)]
    assert any(red > 180 and green < 110 for red, green, _blue in reds)
