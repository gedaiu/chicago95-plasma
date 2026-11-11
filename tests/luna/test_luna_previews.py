"""The Control Panel's previews with the Windows XP component chosen: each draws the Luna screen or part, and
changing the component's combo swaps the preview before anything is applied."""

import time

import pytest
from conftest import load_script, needs_ui_font


@pytest.fixture(scope="module")
def control_panel():
    return load_script("chicago95-control-panel")


def settle(qt_app, seconds=0.5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        qt_app.processEvents()
        time.sleep(0.01)


def preview_of(control_panel, applet, tab_name, index=0):
    tab = control_panel.build_tab(applet, tab_name, {}, control_panel.Actions())
    return tab.previews[index]


def show_settled(widget, qt_app):
    widget.show()
    settle(qt_app)


def shown(widget, qt_app):
    show_settled(widget, qt_app)
    return widget.grabFramebuffer()


def colours_of(image):
    return {image.pixelColor(x, y).name() for x in range(image.width()) for y in range(image.height())}


def is_orange(name):
    red, green, blue = (int(name[position : position + 2], 16) for position in (1, 3, 5))
    return red > 200 and 90 < green < 180 and blue < 80


def is_blue(name):
    red, green, blue = (int(name[position : position + 2], 16) for position in (1, 3, 5))
    return blue > 150 and red < 120 and green < 160


def test_loading_preview_is_the_black_xp_splash_with_the_flag_when_the_style_is_luna(control_panel, qt_app):
    preview = preview_of(control_panel, "Booting Screen", "Boot Screen")
    preview.refresh({"BOOT_STYLE": "luna"})
    image = shown(preview, qt_app)
    colours = colours_of(image)

    assert (
        [error.toString() for error in preview.errors()],
        image.pixelColor(2, 2).name(),
        any(map(is_orange, colours)),
        any(map(is_blue, colours)),
    ) == ([], "#000000", True, True)


def test_loading_preview_draws_another_wordmark_when_the_edition_changes(control_panel, qt_app):
    preview = preview_of(control_panel, "Booting Screen", "Boot Screen")
    preview.refresh({"BOOT_STYLE": "luna", "EDITION": "Professional"})
    professional = shown(preview, qt_app)
    preview.refresh({"BOOT_STYLE": "luna", "EDITION": "Server"})
    server = shown(preview, qt_app)

    assert professional != server


def test_login_preview_is_the_blue_welcome_screen_when_the_style_is_luna(control_panel, qt_app):
    preview = preview_of(control_panel, "Passwords", "Log On")
    preview.refresh({"LOGIN_STYLE": "luna"})
    image = shown(preview, qt_app)

    assert (
        [error.toString() for error in preview.errors()],
        preview.size().toTuple(),
        image.pixelColor(100, 4).name(),
    ) == ([], (264, 198), "#00309c")


def test_branding_preview_is_the_xp_wordmark_on_black_when_the_log_on_style_is_luna(control_panel, qt_app):
    preview = preview_of(control_panel, "Passwords", "Branding")
    preview.refresh({"LOGIN_STYLE": "luna", "EDITION": "Professional"})
    show_settled(preview, qt_app)
    image = preview.grab().toImage()
    colours = colours_of(image)

    assert (
        [error.toString() for error in preview.wordmark.errors()],
        image.pixelColor(2, 2).name(),
        any(map(is_orange, colours)),
    ) == ([], "#000000", True)


@needs_ui_font
def test_start_menu_preview_is_the_two_column_xp_menu_scaled_to_the_sheet(control_panel, qt_app):
    preview = control_panel.StartMenuPreview()
    preview.refresh({"START_MENU_STYLE": "luna", "TASKBAR_STYLE": "luna"})
    preview.process.waitForFinished(60000)
    settle(qt_app, 0.2)
    menu = preview.menu_label.pixmap().toImage()
    right_column = menu.pixelColor(round(menu.width() * 0.8), round(menu.height() * 0.85)).name()

    assert (menu.width(), right_column) == (control_panel.LUNA_MENU_PREVIEW_WIDTH, "#d3e5fa")


@needs_ui_font
def test_start_button_preview_is_the_green_xp_pill_on_the_luna_panel_when_the_taskbar_is_luna(control_panel, qt_app):
    preview = control_panel.StartMenuPreview()
    preview.refresh({"START_MENU_STYLE": "1998", "TASKBAR_STYLE": "luna"})
    preview.process.waitForFinished(60000)
    show_settled(preview, qt_app)
    strip = preview.button.grabFramebuffer()
    pill = strip.pixelColor(90, 10)

    assert (
        [error.toString() for error in preview.button.errors()],
        strip.height(),
        pill.green() > pill.red() and pill.green() > pill.blue(),
    ) == ([], 30, True)


def test_task_button_preview_is_the_blue_xp_pill_when_the_taskbar_is_luna(control_panel, qt_app):
    preview = control_panel.TaskButtonPreview("luna")
    preview.refresh({"TASKBAR_STYLE": "luna"})
    show_settled(preview, qt_app)
    image = preview.luna_view.grabFramebuffer()
    pressed = image.pixelColor(preview.button_width + 3 + 150, 15).name()

    assert (preview.height(), preview.luna_view.isVisibleTo(preview), is_blue(pressed)) == (30, True, True)


def test_task_button_preview_goes_back_to_the_classic_buttons_when_the_taskbar_is_classic(control_panel, qt_app):
    preview = control_panel.TaskButtonPreview("1998")
    preview.refresh({"TASKBAR_STYLE": "luna"})
    preview.refresh({"TASKBAR_STYLE": "classic"})

    assert (preview.height(), preview.luna_view.isVisibleTo(preview)) == (22, False)


def test_task_button_preview_follows_the_width_chosen_under_luna(control_panel, qt_app):
    preview = control_panel.TaskButtonPreview("luna")
    preview.refresh({"TASKBAR_STYLE": "luna"})
    preview.show_width(100)

    assert preview.luna_view.size().toTuple() == (203, 30)


def test_the_boot_screen_preview_turns_black_as_soon_as_the_xp_radio_is_chosen(control_panel, qt_app, tmp_path):
    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.navigate(control_panel.HOME_PAGE + ("Booting Screen",))
    sheet = window.pages.currentWidget()
    (boot,) = sheet.settings_tabs
    boot.fields["BOOT_STYLE"][1]("classic")
    sheet.refresh_previews()
    classic_corner = shown(boot.previews[0], qt_app).pixelColor(2, 2).name()
    boot.fields["BOOT_STYLE"][1]("luna")
    sheet.refresh_previews()
    luna_corner = shown(boot.previews[0], qt_app).pixelColor(2, 2).name()

    assert (classic_corner == "#000000", luna_corner) == (False, "#000000")


def test_the_log_on_preview_swaps_the_dialog_for_the_welcome_screen_when_the_style_changes(control_panel, qt_app):
    preview = preview_of(control_panel, "Passwords", "Log On")
    preview.refresh({"LOGIN_STYLE": "classic"})
    classic_size = preview.size().toTuple()
    preview.refresh({"LOGIN_STYLE": "luna"})

    assert (classic_size, preview.size().toTuple()) == ((264, 150), (264, 198))


def test_the_task_button_preview_is_among_the_taskbar_options_previews_that_the_sheet_refreshes(control_panel):
    tab = control_panel.build_tab("Taskbar", "Taskbar Options", {}, control_panel.Actions())

    assert [type(preview).__name__ for preview in tab.previews] == ["ButtonWidthField"]


def active_title_colour(tab):
    image = tab.preview.grab().toImage()
    return image.pixelColor(tab.preview.active_title.center().x() + 40, tab.preview.active_title.center().y()).name()


def test_the_appearance_preview_swaps_the_classic_mock_for_the_xp_one_when_the_controls_combo_changes(
    control_panel, qt_app, tmp_path
):
    window = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf")
    window.navigate(control_panel.HOME_PAGE + ("Display",))
    sheet = window.pages.currentWidget()
    tab = next(tab for tab in sheet.settings_tabs if hasattr(tab, "color_edits"))
    tab.fields["WIDGET_STYLE"][1]("classic")
    sheet.refresh_previews()
    classic = active_title_colour(tab)
    tab.fields["WIDGET_STYLE"][1]("luna")
    sheet.refresh_previews()

    assert (classic, active_title_colour(tab) != classic, type(tab.preview.currentWidget()).__name__) == (
        "#000080",
        True,
        "LunaAppearancePreview",
    )
