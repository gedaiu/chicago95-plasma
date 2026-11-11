import pytest
from conftest import REPO, load_script
from PySide6.QtWidgets import QComboBox, QLabel, QPushButton, QSpinBox


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


@pytest.fixture
def make_tab(control_panel, qt_app):
    def build(settings=None, **actions):
        tab = control_panel.SettingsTab(settings or {}, control_panel.Actions(**actions))
        tab.changes = []
        tab.changed.connect(lambda: tab.changes.append(1))
        return tab

    return build


def button(widget, text):
    return next(candidate for candidate in widget.findChildren(QPushButton) if candidate.text() == text)


def test_text_field_starts_with_its_default_and_reports_what_is_typed(make_tab):
    tab = make_tab()
    field = tab.text("LOGIN_TITLE", "Title:", default="Log On to %h")
    initial = tab.values()
    field.setText("Welcome")

    assert (initial, tab.values(), len(tab.changes)) == ({"LOGIN_TITLE": "Log On to %h"}, {"LOGIN_TITLE": "Welcome"}, 1)


def test_text_field_starts_with_the_saved_value_before_its_default(make_tab):
    tab = make_tab({"LOGIN_TITLE": "Saved"})
    tab.text("LOGIN_TITLE", "Title:", default="Log On to %h")

    assert tab.values() == {"LOGIN_TITLE": "Saved"}


def test_choice_field_reports_the_value_of_the_chosen_option(make_tab):
    tab = make_tab({"LOGIN_STYLE": "2000"})
    field = tab.choice("LOGIN_STYLE", "Style:", [("Classic", "classic"), ("Windows 2000", "2000")], default="classic")
    saved = tab.values()
    field.setCurrentIndex(0)

    assert (saved, tab.values(), len(tab.changes)) == ({"LOGIN_STYLE": "2000"}, {"LOGIN_STYLE": "classic"}, 1)


def test_choice_field_shows_a_saved_value_that_is_not_an_option_as_the_default(make_tab):
    tab = make_tab({"LOGIN_STYLE": "gone"})
    tab.choice("LOGIN_STYLE", "Style:", [("Classic", "classic"), ("Windows 2000", "2000")], default="classic")

    assert tab.values() == {"LOGIN_STYLE": "classic"}


def test_flag_field_is_yes_or_no(make_tab):
    tab = make_tab({"CLOCK_SHOW": "no"})
    field = tab.flag("CLOCK_SHOW", "Show the clock", default="yes")
    saved = tab.values()
    field.setChecked(True)

    assert (saved, tab.values(), len(tab.changes)) == ({"CLOCK_SHOW": "no"}, {"CLOCK_SHOW": "yes"}, 1)


def test_number_field_reports_its_value_as_text_within_its_range(make_tab):
    tab = make_tab({"PANEL": "36"})
    field = tab.number("PANEL", "Height:", 22, 64, default=28, suffix=" pixels")
    saved = tab.values()
    field.setValue(200)

    assert (saved, tab.values(), field.parent().findChildren(QLabel)[0].text(), len(tab.changes)) == (
        {"PANEL": "36"},
        {"PANEL": "64"},
        "pixels",
        1,
    )


def test_picture_field_reports_a_preset_or_the_chosen_files_path(make_tab):
    tab = make_tab({"START_LOGO": "flag"}, choose_file=lambda parent, title, name_filter: "/home/u/logo.png")
    picture = tab.picture("START_LOGO", "Logo:", [("Classic flag", "flag"), ("Penguin", "penguin")], default="flag")
    preset = tab.values()
    picture.choose_custom_file()

    assert (preset, tab.values(), picture.path_edit.isEnabled()) == (
        {"START_LOGO": "flag"},
        {"START_LOGO": "/home/u/logo.png"},
        True,
    )


def test_picture_field_with_a_saved_path_starts_on_custom_with_that_path(make_tab):
    tab = make_tab({"START_LOGO": "/home/u/logo.png"})
    picture = tab.picture("START_LOGO", "Logo:", [("Classic flag", "flag")], default="flag")

    assert (tab.values(), picture.path_edit.text(), picture.path_edit.isEnabled()) == (
        {"START_LOGO": "/home/u/logo.png"},
        "/home/u/logo.png",
        True,
    )


def test_picture_field_cancelled_browse_keeps_the_value(make_tab):
    tab = make_tab({"START_LOGO": "penguin"}, choose_file=lambda *_: "")
    picture = tab.picture("START_LOGO", "Logo:", [("Penguin", "penguin")], default="penguin")
    picture.choose_custom_file()

    assert (tab.values(), tab.changes) == ({"START_LOGO": "penguin"}, [])


def test_file_only_picture_field_has_no_presets(make_tab):
    tab = make_tab(choose_file=lambda *_: "/home/u/wall.png")
    picture = tab.picture("BACKGROUND_IMAGE", "Picture:", [], default="")
    picture.choose_custom_file()

    assert tab.values() == {"BACKGROUND_IMAGE": "/home/u/wall.png"}


def test_color_field_shows_the_saved_colour_as_a_swatch_and_reports_the_picked_one(make_tab):
    tab = make_tab({"TITLE_ACTIVE": "#000080"}, choose_color=lambda parent, current: "#FF0000")
    field = tab.color("TITLE_ACTIVE", "Active title bar:", default="#000080")
    saved = (tab.values(), [swatch.toolTip() for swatch in field.swatches])
    field.swatches[0].click()

    assert (saved, tab.values(), field.value(), len(tab.changes)) == (
        ({"TITLE_ACTIVE": "#000080"}, ["#000080"]),
        {"TITLE_ACTIVE": "#FF0000"},
        "#FF0000",
        1,
    )


def test_color_field_keeps_its_colour_when_the_picker_is_cancelled(make_tab):
    tab = make_tab({"TITLE_ACTIVE": "#000080"}, choose_color=lambda parent, current: None)
    field = tab.color("TITLE_ACTIVE", "Active title bar:", default="#000080")
    field.swatches[0].click()

    assert (tab.values(), len(tab.changes)) == ({"TITLE_ACTIVE": "#000080"}, 0)


def test_color_field_plus_adds_a_gradient_end_and_minus_takes_it_away(make_tab):
    tab = make_tab(choose_color=lambda parent, current: "#1084D0")
    field = tab.color("TITLE_ACTIVE", "Active title bar:", default="#000080")
    field.add_button.click()
    field.swatches[1].click()
    two = (tab.values(), field.add_button.isEnabled(), field.remove_button.isEnabled())
    field.remove_button.click()

    assert (two, tab.values(), field.remove_button.isEnabled()) == (
        ({"TITLE_ACTIVE": "#000080,#1084D0"}, False, True),
        {"TITLE_ACTIVE": "#000080"},
        False,
    )


def test_banner_colour_field_shows_each_stop_with_its_distance_and_reports_a_changed_distance(make_tab):
    tab = make_tab({"BANNER_BG": "#000000,#000021@200,#0000FF@0"})
    field = tab.color("BANNER_BG", "Start menu banner:", default="#808080", most=8, stops=True)
    shown = ([swatch.toolTip() for swatch in field.swatches], [box.value() for box in field.stop_boxes])
    field.stop_boxes[0].setValue(150)

    assert (shown, tab.values()["BANNER_BG"]) == (
        (["#000000", "#000021", "#0000FF"], [200, 0]),
        "#000000,#000021@150,#0000FF@0",
    )


def test_banner_colour_field_plus_adds_a_stop_at_the_top(make_tab):
    tab = make_tab({"BANNER_BG": "#808080"})
    field = tab.color("BANNER_BG", "Start menu banner:", default="#808080", most=8, stops=True)
    field.add_button.click()

    assert (tab.values()["BANNER_BG"], len(field.stop_boxes)) == ("#808080,#808080@0", 1)


def test_single_colour_field_offers_no_plus_or_minus(make_tab):
    tab = make_tab()
    field = tab.color("BACKGROUND_COLOR", "Color:", default="#008080", most=1)

    assert (field.add_button.isVisible(), field.remove_button.isVisible(), field.value()) == (False, False, "#008080")


def test_loading_settings_into_a_tab_replaces_every_field_without_reporting_a_change(make_tab):
    tab = make_tab()
    tab.text("LOGIN_TITLE", "Title:", default="a")
    tab.flag("CLOCK_SHOW", "Clock", default="yes")
    tab.load({"LOGIN_TITLE": "b", "CLOCK_SHOW": "no"})

    assert (tab.values(), tab.changes) == ({"LOGIN_TITLE": "b", "CLOCK_SHOW": "no"}, [])


def test_mouse_pointer_tab_reports_the_saved_pointer_size_and_defaults_to_32(control_panel, qt_app):
    saved = control_panel.build_tab("Mouse", "Pointers", {"CURSOR": "48"}, control_panel.Actions())
    unset = control_panel.build_tab("Mouse", "Pointers", {}, control_panel.Actions())

    assert (saved.values(), unset.values()) == ({"CURSOR": "48"}, {"CURSOR": "32"})


def test_mouse_pointer_tab_offers_24_32_and_48_pixel_pointers(control_panel, qt_app):
    tab = control_panel.build_tab("Mouse", "Pointers", {}, control_panel.Actions())

    from PySide6.QtWidgets import QRadioButton

    assert [button.text() for button in tab.findChildren(QRadioButton)] == [
        "Normal (24 pixels)",
        "Large (32 pixels)",
        "Extra large (48 pixels)",
    ]


def built(control_panel, applet, tab, settings=None, **actions):
    return control_panel.build_tab(applet, tab, settings or {}, control_panel.Actions(**actions))


def test_office_assistant_tab_shows_at_log_on_by_default_and_reports_the_saved_choice(control_panel, qt_app):
    assert (
        built(control_panel, "Office Assistant", "Options").values(),
        built(control_panel, "Office Assistant", "Options", {"CLIPPY_AUTOSTART": "no"}).values(),
    ) == ({"CLIPPY_AUTOSTART": "yes"}, {"CLIPPY_AUTOSTART": "no"})


def test_explorer_tab_defaults_to_thunar_when_it_is_installed(control_panel, qt_app):
    assert built(control_panel, "Explorer", "General", program_installed=lambda name: "/usr/bin/" + name).values() == {
        "EXPLORER": "thunar"
    }


def test_explorer_tab_defaults_to_dolphin_and_disables_thunar_when_thunar_is_missing(control_panel, qt_app):
    from PySide6.QtWidgets import QRadioButton

    tab = built(control_panel, "Explorer", "General", program_installed=lambda name: None)
    buttons = {button.text(): button.isEnabled() for button in tab.findChildren(QRadioButton)}

    assert (tab.values(), buttons) == ({"EXPLORER": "dolphin"}, {"Thunar": False, "Dolphin": True})


def test_fonts_tab_defaults_to_the_classic_font_everywhere_and_shows_a_saved_font_even_when_not_installed(
    control_panel, qt_app
):
    assert (
        built(control_panel, "Fonts", "Font").values(),
        built(control_panel, "Fonts", "Font", {"FONT": "Not Installed Sans", "FONT_SCOPE": "desktop"}).values(),
    ) == ({"FONT": "MS W98 UI", "FONT_SCOPE": "everywhere"}, {"FONT": "Not Installed Sans", "FONT_SCOPE": "desktop"})


def test_start_menu_tab_defaults_to_start_the_flag_and_chicago95(control_panel, qt_app):
    assert built(control_panel, "Taskbar", "Start Menu").values() == {
        "START_MENU_STYLE": "1995",
            "START_TEXT": "Start",
        "START_LOGO": "flag",
        "BANNER_TEXT": "Chicago95",
    }


def test_log_on_tab_defaults_to_the_classic_dialog_with_its_texts_and_pictures(control_panel, qt_app):
    assert built(control_panel, "Passwords", "Log On").values() == {
        "LOGIN_STYLE": "classic",
        "LOGIN_TITLE": "Log On to %h",
        "LOGIN_MESSAGE": "Type a user name and password to log on.",
        "LOGIN_ICON": "keys",
        "LOGIN_LOGO": "start",
    }


def test_branding_tab_defaults_to_professional_kde_text_logo_and_the_tagline(control_panel, qt_app):
    assert built(control_panel, "Passwords", "Branding").values() == {
        "EDITION": "Professional",
        "TAGLINE": "Built on Linux Technology",
        "COMPANY": "KDE",
        "COMPANY_LOGO": "text",
    }


def test_boot_screen_tab_defaults_to_the_classic_style_picture_and_texts(control_panel, qt_app):
    assert built(control_panel, "Booting Screen", "Boot Screen").values() == {
        "BOOT_STYLE": "classic",
        "SPLASH_IMAGE": "classic",
        "LOADING_TEXT": "Starting up...",
        "LOADING_FOOTER": "Chicago95 for KDE Plasma",
    }


def kde_effects():
    import chicago95animations as animations

    def effect(name, category, enabled, settings=None):
        return animations.InstalledEffect(name, category, enabled, settings)

    return {
        "scale": effect("Scale", "toplevel-open-close-animation", True),
        "kwin6_effect_fire": effect(
            "Fire [Burn-My-Windows]", "toplevel-open-close-animation", False, ("kcmshell6", "kcm_kwin_effects")
        ),
        "squash": effect("Squash", "minimize", True),
        "magiclamp": effect(
            "Magic Lamp", "minimize", False, ("kcmshell6", "kwin/effects/configs/kwin_magiclamp_config")
        ),
        "maximize": effect("Stretch", "maximize", True),
        "fullscreen": effect("Stretch", "fullscreen", True),
        "slide": effect("Slide", "desktop-animations", True),
        "slidingpopups": effect("Sliding popups", None, True),
        "fadingpopups": effect("Fading popups", None, True),
        "dialogparent": effect("Dialog Parent", None, True),
        "login": effect("Login", None, True),
        "logout": effect("Logout", None, True),
        "windowaperture": effect("Window Aperture", "show-desktop", True),
    }


def effects_tab(control_panel, settings=None, plugins=None, started=None):
    import chicago95animations as animations

    return built(
        control_panel,
        "Display",
        "Effects",
        settings,
        installed_effects=kde_effects,
        live_animations=lambda: animations.LiveState(kwinrc={"Plugins": plugins or {}}),
        start_process=lambda program, arguments: (started if started is not None else []).append((program, arguments)),
    )


def test_effects_tab_shows_what_kde_does_now_for_every_event_while_nothing_is_saved(control_panel, qt_app):
    assert effects_tab(control_panel, plugins={"wobblywindowsEnabled": "true"}).values() == {
        "DESKTOP_ICONS": "auto",
        "ANIM_WINDOWS": "scale",
        "ANIM_MINIMIZE": "squash",
        "ANIM_MAXIMIZE": "stretch",
        "ANIM_DIALOGS": "dim",
        "ANIM_WOBBLY": "yes",
        "ANIM_SHOW_DESKTOP": "aperture",
        "ANIM_DESKTOPS": "slide",
        "ANIM_SESSION": "fade",
        "ANIM_MENUS": "both",
        "ANIM_NOTIFICATIONS": "none",
        "ANIM_TASKBAR": "slide",
        "ANIM_SPEED": "1",
    }


def test_effects_tab_reports_a_saved_choice_over_what_kde_does(control_panel, qt_app):
    values = effects_tab(control_panel, {"ANIM_MINIMIZE": "zoom", "ANIM_SPEED": "0"}).values()

    assert (values["ANIM_MINIMIZE"], values["ANIM_SPEED"]) == ("zoom", "0")


def test_effects_tab_offers_installed_burn_my_windows_effects_for_opening_and_closing_windows(control_panel, qt_app):
    combo = effects_tab(control_panel).combos["ANIM_WINDOWS"]

    assert [combo.itemText(index) for index in range(combo.count())] == [
        "None",
        "Scale",
        "Glide",
        "Fade",
        "Fire [Burn-My-Windows]",
    ]


def test_classic_button_on_the_1998_look_zooms_title_bars_slides_menus_and_turns_the_rest_off(control_panel, qt_app):
    tab = effects_tab(control_panel, {"LOOK": "1998"})
    tab.classic_button.click()

    assert {key: value for key, value in tab.values().items() if value not in ("none", "no")} == {
        "DESKTOP_ICONS": "auto",
        "ANIM_MINIMIZE": "zoom",
        "ANIM_MAXIMIZE": "zoom",
        "ANIM_MENUS": "slide",
        "ANIM_SPEED": "1",
    }


def test_settings_button_opens_kdes_page_for_the_chosen_effect_and_is_off_without_one(control_panel, qt_app):
    started = []
    tab = effects_tab(control_panel, {"ANIM_MINIMIZE": "squash"}, started=started)
    button = tab.settings_buttons["ANIM_MINIMIZE"]
    without_page = button.isEnabled()
    tab.combos["ANIM_MINIMIZE"].setCurrentIndex(tab.combos["ANIM_MINIMIZE"].findData("magiclamp"))
    button.click()

    assert (without_page, button.isEnabled(), started) == (
        False,
        True,
        [("kcmshell6", ["kwin/effects/configs/kwin_magiclamp_config"])],
    )


@pytest.mark.parametrize("position, speed", [(0, "0"), (1, "0.5"), (2, "1"), (3, "2")])
def test_speed_slider_runs_from_off_to_slow(control_panel, qt_app, position, speed):
    tab = effects_tab(control_panel)
    tab.speed_slider.slider.setValue(position)

    assert tab.values()["ANIM_SPEED"] == speed


def test_animation_choices_are_applied_by_setups_animations_step_alone(control_panel):
    assert control_panel.components_for(["ANIM_MINIMIZE", "ANIM_SPEED", "ANIM_TASKBAR"]) == ["animations"]


def background_tab(control_panel, saved=None, pictures=(), pattern=None):
    return built(
        control_panel,
        "Display",
        "Background",
        saved,
        wallpapers=lambda: list(pictures),
        choose_pattern=lambda parent, current, colour: pattern,
    )


def test_background_tab_defaults_to_no_wallpaper_and_no_pattern(control_panel, qt_app):
    assert background_tab(control_panel).values() == {
        "BACKGROUND_MODE": "color",
        "BACKGROUND_PATTERN": "none",
        "BACKGROUND_IMAGE": "",
        "BACKGROUND_FILL": "center",
    }


def test_background_tab_reports_a_saved_tiled_picture_even_when_it_is_not_in_the_list(control_panel, qt_app):
    saved = {"BACKGROUND_MODE": "image", "BACKGROUND_IMAGE": "/home/u/wall.png", "BACKGROUND_FILL": "tile"}

    assert background_tab(control_panel, saved).values() == {
        "BACKGROUND_MODE": "image",
        "BACKGROUND_PATTERN": "none",
        "BACKGROUND_IMAGE": "/home/u/wall.png",
        "BACKGROUND_FILL": "tile",
    }


def test_the_wallpaper_list_starts_with_none_then_the_pictures_found(control_panel, qt_app):
    tab = background_tab(control_panel, pictures=[("Clouds", "/p/clouds.png"), ("Setup", "/p/setup.bmp")])

    assert [tab.wallpapers.item(row).text() for row in range(tab.wallpapers.count())] == ["(None)", "Clouds", "Setup"]


def test_choosing_a_wallpaper_enables_display_and_disables_pattern_as_the_original_does(control_panel, qt_app):
    tab = background_tab(control_panel, pictures=[("Clouds", "/p/clouds.png")])
    none_state = (tab.display.isEnabled(), tab.pattern_button.isEnabled())
    tab.wallpapers.setCurrentRow(1)

    assert (none_state, (tab.display.isEnabled(), tab.pattern_button.isEnabled()), tab.values()["BACKGROUND_MODE"]) == (
        (False, True),
        (True, False),
        "image",
    )


def test_a_pattern_chosen_in_the_pattern_dialog_makes_the_desktop_a_pattern(control_panel, qt_app):
    tab = background_tab(control_panel, pattern="grid")
    tab.pattern_button.click()

    assert (tab.values()["BACKGROUND_MODE"], tab.values()["BACKGROUND_PATTERN"]) == ("pattern", "grid")


def test_the_monitor_shows_the_chosen_wallpaper(control_panel, qt_app, tmp_path):
    from PySide6.QtGui import QColor, QImage

    picture = QImage(64, 48, QImage.Format_RGB32)
    picture.fill(QColor("#FF0000"))
    picture.save(str(tmp_path / "red.png"))
    tab = background_tab(control_panel, {"BACKGROUND_FILL": "stretch"}, pictures=[("Red", str(tmp_path / "red.png"))])
    tab.wallpapers.setCurrentRow(1)

    assert monitor_screen_colour(tab) == "#ff0000"


def test_the_display_choices_are_center_tile_stretch_and_cover(control_panel, qt_app):
    tab = background_tab(control_panel)

    assert [tab.display.itemData(index) for index in range(tab.display.count())] == [
        "center",
        "tile",
        "stretch",
        "cover",
    ]


def test_a_covering_wallpaper_is_scaled_to_the_screens_wider_side_and_centred(control_panel):
    from PySide6.QtCore import QRect, QSize

    assert control_panel.cover_rect(QSize(64, 48), QRect(10, 20, 100, 50)) == QRect(10, 8, 100, 75)


def test_the_monitor_shows_a_covering_wallpaper_edge_to_edge(control_panel, qt_app, tmp_path):
    from PySide6.QtGui import QColor, QImage

    picture = QImage(640, 10, QImage.Format_RGB32)
    picture.fill(QColor("#0000FF"))
    picture.save(str(tmp_path / "wide.png"))
    tab = background_tab(control_panel, {"BACKGROUND_FILL": "cover"}, pictures=[("Wide", str(tmp_path / "wide.png"))])
    tab.wallpapers.setCurrentRow(1)
    screen = tab.monitor.screen_rect()
    corners = (screen.topLeft(), screen.bottomRight(), screen.center())

    assert [tab.monitor.grab().toImage().pixelColor(point).name() for point in corners] == ["#0000ff"] * 3


def test_the_monitor_shows_the_desktop_colour_without_a_wallpaper(control_panel, qt_app):
    assert monitor_screen_colour(background_tab(control_panel, {"BACKGROUND_COLOR": "#102030"})) == "#102030"


TASKBAR_OPTION_DEFAULTS = {
    "PANEL": "28",
    "TASK_BUTTON_WIDTH": "0",
    "QUICK_LAUNCH": "auto",
    "TASKBAR_AUTOHIDE": "no",
    "TASKBAR_ON_TOP": "yes",
    "PREVIEW_SIZE": "off",
    "CLOCK_SHOW": "yes",
    "CLOCK_HOURS": "locale",
}


def width_field(tab):
    return tab.fields["TASK_BUTTON_WIDTH"][0].__self__


def test_taskbar_options_tab_defaults_to_the_classic_taskbar(control_panel, qt_app):
    assert built(control_panel, "Taskbar", "Taskbar Options").values() == TASKBAR_OPTION_DEFAULTS


def test_taskbar_options_tab_reports_every_saved_choice(control_panel, qt_app):
    saved = {
        "PANEL": "36",
        "TASK_BUTTON_WIDTH": "220",
        "QUICK_LAUNCH": "no",
        "TASKBAR_AUTOHIDE": "yes",
        "TASKBAR_ON_TOP": "no",
        "PREVIEW_SIZE": "240",
        "CLOCK_SHOW": "no",
        "CLOCK_HOURS": "24",
    }

    assert built(control_panel, "Taskbar", "Taskbar Options", saved).values() == saved


def test_task_button_width_follows_the_looks_own_until_a_width_is_chosen(control_panel, qt_app):
    field = width_field(built(control_panel, "Taskbar", "Taskbar Options"))

    assert (field.value(), field.checkbox.isChecked(), field.slider.isEnabled(), field.spin.isEnabled()) == (
        "0",
        True,
        False,
        False,
    )


def test_task_button_width_of_220_is_shown_on_the_slider_and_the_spin_box(control_panel, qt_app):
    field = width_field(built(control_panel, "Taskbar", "Taskbar Options", {"TASK_BUTTON_WIDTH": "220"}))

    assert (
        field.value(),
        field.checkbox.isChecked(),
        field.slider.value(),
        field.spin.value(),
        field.slider.isEnabled(),
    ) == ("220", False, 220, 220, True)


def test_moving_the_width_slider_moves_the_spin_box_and_the_reported_width_and_tells_the_tab(control_panel, qt_app):
    tab = built(control_panel, "Taskbar", "Taskbar Options", {"TASK_BUTTON_WIDTH": "220"})
    changes = []
    tab.changed.connect(lambda: changes.append(1))
    field = width_field(tab)
    field.slider.setValue(120)

    assert (field.spin.value(), tab.values()["TASK_BUTTON_WIDTH"], changes) == (120, "120", [1])


def test_task_button_width_is_limited_to_60_and_300_pixels(control_panel, qt_app):
    field = width_field(built(control_panel, "Taskbar", "Taskbar Options", {"TASK_BUTTON_WIDTH": "220"}))
    field.spin.setValue(1000)
    high = field.value()
    field.spin.setValue(1)

    assert (high, field.value()) == ("300", "60")


def test_choosing_the_looks_own_width_again_reports_zero(control_panel, qt_app):
    tab = built(control_panel, "Taskbar", "Taskbar Options", {"TASK_BUTTON_WIDTH": "220"})
    width_field(tab).checkbox.setChecked(True)

    assert tab.values()["TASK_BUTTON_WIDTH"] == "0"


def test_width_preview_draws_task_buttons_as_wide_as_the_chosen_width(control_panel, qt_app):
    field = width_field(built(control_panel, "Taskbar", "Taskbar Options", {"TASK_BUTTON_WIDTH": "220"}))
    chosen = field.preview.button_width
    field.slider.setValue(100)

    assert (chosen, field.preview.button_width) == (220, 100)


def test_width_preview_shows_the_160_pixel_buttons_of_the_looks_own_width(control_panel, qt_app):
    assert width_field(built(control_panel, "Taskbar", "Taskbar Options")).preview.button_width == 160


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/usr/share/applications/firefox.desktop", "applications:firefox.desktop"),
        ("{home}/.local/share/applications/mine.desktop", "applications:mine.desktop"),
        ("{home}/Desktop/Tool.desktop", "file://{home}/Desktop/Tool.desktop"),
    ],
)
def test_launcher_for_a_desktop_file_is_its_menu_id_or_its_file_url(control_panel, path, expected):
    home = str(control_panel.Path.home())

    assert control_panel.launcher_for_desktop_file(path.format(home=home)) == expected.format(home=home)


def test_default_launchers_are_read_from_the_first_task_list_config_found(control_panel, tmp_path):
    kcfg = (
        '<kcfg xmlns="http://www.kde.org/standards/kcfg/1.0"><group name="General">'
        '<entry name="launchers" type="StringList">'
        "<default>applications:a.desktop,applications:b.desktop</default></entry></group></kcfg>"
    )
    config = tmp_path / "main.xml"
    config.write_text(kcfg)

    assert control_panel.default_launchers([tmp_path / "missing.xml", config]) == [
        "applications:a.desktop",
        "applications:b.desktop",
    ]


def quick_launch(control_panel, settings=None, current=lambda: None, choose_file=lambda *_: ""):
    return built(control_panel, "Taskbar", "Quick Launch", settings, current_launchers=current, choose_file=choose_file)


def launcher_rows(tab):
    from PySide6.QtWidgets import QListWidget

    list_widget = tab.findChildren(QListWidget)[0]
    return [list_widget.item(row).text() for row in range(list_widget.count())], list_widget


def test_quick_launch_tab_lists_the_saved_launchers_before_the_live_ones(control_panel, qt_app):
    tab = quick_launch(control_panel, {"LAUNCHERS": "a,b"}, current=lambda: ["live"])

    assert (launcher_rows(tab)[0], tab.values()) == (["a", "b"], {"LAUNCHERS": "a,b"})


def test_quick_launch_tab_lists_what_the_taskbar_has_when_nothing_was_saved(control_panel, qt_app):
    assert launcher_rows(quick_launch(control_panel, current=lambda: ["live1", "live2"]))[0] == ["live1", "live2"]


def test_quick_launch_tab_with_no_saved_or_live_launchers_lists_the_task_lists_defaults(control_panel, qt_app):
    defaults = control_panel.default_launchers(control_panel.DEFAULT_LAUNCHER_FILES)

    assert (launcher_rows(quick_launch(control_panel))[0], defaults != []) == (defaults, True)


def test_quick_launch_tab_move_up_reorders_the_selected_launcher(control_panel, qt_app):
    tab = quick_launch(control_panel, {"LAUNCHERS": "a,b,c"})
    _rows, list_widget = launcher_rows(tab)
    list_widget.setCurrentRow(1)
    button(tab, "Move Up").click()

    assert (tab.values(), list_widget.currentRow()) == ({"LAUNCHERS": "b,a,c"}, 0)


def test_quick_launch_tab_move_down_reorders_and_stops_at_the_end(control_panel, qt_app):
    tab = quick_launch(control_panel, {"LAUNCHERS": "a,b,c"})
    _rows, list_widget = launcher_rows(tab)
    list_widget.setCurrentRow(1)
    button(tab, "Move Down").click()
    button(tab, "Move Down").click()

    assert tab.values() == {"LAUNCHERS": "a,c,b"}


def test_quick_launch_tab_remove_drops_only_the_selected_launcher(control_panel, qt_app):
    tab = quick_launch(control_panel, {"LAUNCHERS": "a,b,c"})
    list_widget = launcher_rows(tab)[1]
    list_widget.setCurrentRow(1)
    button(tab, "Remove").click()

    assert tab.values() == {"LAUNCHERS": "a,c"}


def test_quick_launch_tab_buttons_do_nothing_without_a_selection(control_panel, qt_app):
    tab = quick_launch(control_panel, {"LAUNCHERS": "a,b"})
    for caption in ("Move Up", "Move Down", "Remove"):
        button(tab, caption).click()

    assert tab.values() == {"LAUNCHERS": "a,b"}


def test_quick_launch_tab_add_appends_the_chosen_desktop_file(control_panel, qt_app):
    tab = quick_launch(
        control_panel,
        {"LAUNCHERS": "a"},
        choose_file=lambda parent, title, name_filter: "/usr/share/applications/org.kde.konsole.desktop",
    )
    button(tab, "Add...").click()

    assert tab.values() == {"LAUNCHERS": "a,applications:org.kde.konsole.desktop"}


def test_quick_launch_tab_add_that_is_cancelled_changes_nothing(control_panel, qt_app):
    tab = quick_launch(control_panel, {"LAUNCHERS": "a"})
    button(tab, "Add...").click()

    assert tab.values() == {"LAUNCHERS": "a"}


def test_quick_launch_tab_can_empty_the_list_and_reports_it(control_panel, qt_app):
    tab = quick_launch(control_panel, {"LAUNCHERS": "a"})
    launcher_rows(tab)[1].setCurrentRow(0)
    button(tab, "Remove").click()

    assert tab.values() == {"LAUNCHERS": ""}


SAVERS = [("deepstars", "Deep Stars"), ("maze", "Maze")]


def screen_saver(control_panel, settings=None, lock_minutes=10, started=None):
    started = [] if started is None else started
    tab = built(
        control_panel,
        "Display",
        "Screen Saver",
        settings,
        list_screensavers=lambda: SAVERS,
        lock_timeout_minutes=lambda: lock_minutes,
        start_process=lambda program, arguments: started.append((program.rsplit("/", 1)[-1], arguments)),
    )
    return tab


def test_screen_saver_tab_defaults_to_deep_stars_after_5_minutes(control_panel, qt_app):
    assert screen_saver(control_panel).values() == {"SAVER": "deepstars", "IDLE_MIN": "5"}


def test_screen_saver_tab_lists_the_installed_savers_and_reports_the_saved_choice(control_panel, qt_app):
    tab = screen_saver(control_panel, {"SAVER": "maze", "IDLE_MIN": "12"})

    assert ([tab.findChildren(QComboBox)[0].itemText(row) for row in range(2)], tab.values()) == (
        ["Deep Stars", "Maze"],
        {"SAVER": "maze", "IDLE_MIN": "12"},
    )


def test_screen_saver_preview_runs_the_chosen_saver_full_screen(control_panel, qt_app):
    started = []
    tab = screen_saver(control_panel, {"SAVER": "maze"}, started=started)
    button(tab, "Preview").click()

    assert started == [("chicago95-screensaver", ["--hack", "maze"])]


def test_screen_saver_tab_warns_when_the_lock_screen_would_come_first(control_panel, qt_app):
    tab = screen_saver(control_panel, {"IDLE_MIN": "10"}, lock_minutes=10)

    assert tab.lock_warning.isHidden() is False


def test_screen_saver_tab_stops_warning_once_the_wait_is_below_the_lock_time(control_panel, qt_app):
    tab = screen_saver(control_panel, {"IDLE_MIN": "10"}, lock_minutes=10)
    tab.findChildren(QSpinBox)[0].setValue(3)

    assert tab.lock_warning.isHidden() is True


def test_screen_saver_tab_without_any_installed_saver_reports_the_default_and_disables_preview(control_panel, qt_app):
    tab = built(
        control_panel, "Display", "Screen Saver", None, list_screensavers=lambda: [], lock_timeout_minutes=lambda: 10
    )

    assert (tab.values()["SAVER"], button(tab, "Preview").isEnabled()) == ("deepstars", False)


def appearance(control_panel, settings=None):
    return built(control_panel, "Display", "Appearance", settings)


def preset_values(control_panel, look):
    return {"LOOK": look, **control_panel.LOOK_PRESETS[look]}


def test_appearance_tab_defaults_to_the_windows_95_scheme_with_all_its_settings(control_panel, qt_app):
    assert appearance(control_panel).values() == preset_values(control_panel, "1995")


def test_choosing_the_windows_2000_scheme_fills_in_every_setting_of_that_look(control_panel, qt_app):
    tab = appearance(control_panel)
    tab.scheme.setCurrentIndex(tab.scheme.findData("2000"))

    assert tab.values() == preset_values(control_panel, "2000")


def test_choosing_a_scheme_over_saved_custom_colours_replaces_them_all(control_panel, qt_app):
    tab = appearance(
        control_panel, {"LOOK": "custom", "TITLE_ACTIVE": "#FF0000", "BANNER_BG": "#00FF00", "ICONS": "se98"}
    )
    tab.scheme.setCurrentIndex(tab.scheme.findData("1995"))

    assert tab.values() == preset_values(control_panel, "1995")


def test_editing_a_title_colour_switches_the_scheme_to_custom_and_keeps_the_rest(control_panel, qt_app):
    tab = appearance(control_panel, preset_values(control_panel, "2000"))
    tab.color_edits["TITLE_ACTIVE"].set_value("#FF0000")

    assert tab.values() == {**preset_values(control_panel, "2000"), "LOOK": "custom", "TITLE_ACTIVE": "#FF0000"}


def test_saved_scheme_and_colours_are_shown_as_saved_without_turning_custom(control_panel, qt_app):
    saved = {**preset_values(control_panel, "1998"), "TITLE_ACTIVE": "#123456"}

    assert appearance(control_panel, saved).values() == saved


def test_discarding_changes_puts_the_scheme_and_colours_back(control_panel, qt_app):
    saved = preset_values(control_panel, "1998")
    tab = appearance(control_panel, saved)
    tab.scheme.setCurrentIndex(tab.scheme.findData("2000"))
    tab.load(saved)

    assert tab.values() == saved


def test_banner_background_takes_a_gradient_with_stops(control_panel, qt_app):
    tab = appearance(control_panel)
    tab.color_edits["BANNER_BG"].set_value("#000000,#000021@200,#0000FF@0")

    assert tab.values()["BANNER_BG"] == "#000000,#000021@200,#0000FF@0"


def test_appearance_tab_reports_a_chosen_icon_set_without_changing_the_scheme(control_panel, qt_app):
    tab = appearance(control_panel)
    tab.icons.setCurrentIndex(tab.icons.findData("se98"))

    assert (tab.values()["ICONS"], tab.values()["LOOK"]) == ("se98", "1995")


def test_title_bar_preview_shows_the_current_active_and_inactive_colours(control_panel, qt_app):
    tab = appearance(control_panel)
    tab.color_edits["TITLE_ACTIVE"].set_value("#0A246A,#A6CAF0")

    assert (tab.preview.active, tab.preview.inactive) == ("#0A246A,#A6CAF0", "#808080")


def sound_theme(root, theme, name, *sounds):
    (root / theme / "stereo").mkdir(parents=True)
    (root / theme / "index.theme").write_text(f"[Sound Theme]\nName={name}\n")
    for sound in sounds:
        (root / theme / "stereo" / sound).touch()


def sounds_tab(control_panel, root, settings=None, started=None, player="pw-play"):
    started = [] if started is None else started
    return built(
        control_panel,
        "Sounds",
        "Sounds",
        settings,
        sound_roots=[root],
        program_installed=lambda name: f"/usr/bin/{name}" if name == player else None,
        start_process=lambda program, arguments: started.append((program, arguments)),
    )


def event_list(tab):
    from PySide6.QtWidgets import QListWidget

    return tab.findChildren(QListWidget)[0]


def test_sounds_tab_lists_the_installed_schemes_and_defaults_to_chicago95(control_panel, qt_app, tmp_path):
    sound_theme(tmp_path, "Chicago95", "Chicago95")
    sound_theme(tmp_path, "Windows98", "Windows 98")
    tab = sounds_tab(control_panel, tmp_path)

    assert ([tab.findChildren(QComboBox)[0].itemText(row) for row in range(2)], tab.values()) == (
        ["Chicago95", "Windows 98"],
        {"SOUND_THEME": "Chicago95"},
    )


def test_sounds_tab_reports_the_saved_scheme(control_panel, qt_app, tmp_path):
    sound_theme(tmp_path, "Chicago95", "Chicago95")
    sound_theme(tmp_path, "Windows98", "Windows 98")

    assert sounds_tab(control_panel, tmp_path, {"SOUND_THEME": "Windows98"}).values() == {"SOUND_THEME": "Windows98"}


def test_sounds_tab_lists_the_windows_events(control_panel, qt_app, tmp_path):
    sound_theme(tmp_path, "Chicago95", "Chicago95")
    events = event_list(sounds_tab(control_panel, tmp_path))

    assert [events.item(row).text() for row in range(3)] == ["Start Windows", "Exit Windows", "Critical Stop"]


def test_sounds_tab_play_runs_the_player_with_the_selected_events_sound_of_the_chosen_scheme(
    control_panel, qt_app, tmp_path
):
    sound_theme(tmp_path, "Chicago95", "Chicago95", "desktop-login.wav")
    sound_theme(tmp_path, "Windows98", "Windows 98", "desktop-login.ogg")
    started = []
    tab = sounds_tab(control_panel, tmp_path, {"SOUND_THEME": "Windows98"}, started)
    event_list(tab).setCurrentRow(0)
    button(tab, "Play").click()

    assert started == [("/usr/bin/pw-play", [str(tmp_path / "Windows98/stereo/desktop-login.ogg")])]


def test_sounds_tab_play_falls_back_to_chicago95_for_an_event_the_scheme_lacks(control_panel, qt_app, tmp_path):
    sound_theme(tmp_path, "Chicago95", "Chicago95", "desktop-logout.wav")
    sound_theme(tmp_path, "Plus98-Leonardo", "Leonardo da Vinci")
    started = []
    tab = sounds_tab(control_panel, tmp_path, {"SOUND_THEME": "Plus98-Leonardo"}, started)
    event_list(tab).setCurrentRow(1)
    button(tab, "Play").click()

    assert started == [("/usr/bin/pw-play", [str(tmp_path / "Chicago95/stereo/desktop-logout.wav")])]


def test_sounds_tab_play_follows_a_scheme_chosen_in_the_tab_before_applying(control_panel, qt_app, tmp_path):
    sound_theme(tmp_path, "Chicago95", "Chicago95", "dialog-error.wav")
    sound_theme(tmp_path, "Windows98", "Windows 98", "dialog-error.ogg")
    started = []
    tab = sounds_tab(control_panel, tmp_path, started=started)
    combo = tab.findChildren(QComboBox)[0]
    combo.setCurrentIndex(combo.findData("Windows98"))
    event_list(tab).setCurrentRow(2)
    button(tab, "Play").click()

    assert started[0][1] == [str(tmp_path / "Windows98/stereo/dialog-error.ogg")]


def test_sounds_tab_play_does_nothing_without_a_selected_event_or_a_sound_file(control_panel, qt_app, tmp_path):
    sound_theme(tmp_path, "Chicago95", "Chicago95")
    started = []
    tab = sounds_tab(control_panel, tmp_path, started=started)
    button(tab, "Play").click()
    event_list(tab).setCurrentRow(0)
    button(tab, "Play").click()

    assert started == []


def test_sounds_tab_uses_paplay_when_pw_play_is_missing_and_disables_play_without_either(
    control_panel, qt_app, tmp_path
):
    sound_theme(tmp_path, "Chicago95", "Chicago95", "desktop-login.wav")
    started = []
    tab = sounds_tab(control_panel, tmp_path, started=started, player="paplay")
    event_list(tab).setCurrentRow(0)
    button(tab, "Play").click()
    silent = sounds_tab(control_panel, tmp_path, player="none")

    assert (started[0][0], button(silent, "Play").isEnabled()) == ("/usr/bin/paplay", False)


def test_every_tab_of_every_page_has_its_own_builder(control_panel):
    declared = {(applet, tab) for applet, tabs in control_panel.PAGE_TABS.items() for tab in tabs}

    assert declared == set(control_panel.TAB_BUILDERS)


def test_every_key_the_tabs_report_is_one_setup_applies_or_the_control_panel_applies_live(control_panel, qt_app):
    reported = {
        key
        for applet, tabs in control_panel.PAGE_TABS.items()
        for tab in tabs
        for key in built(
            control_panel, applet, tab, None, list_screensavers=lambda: SAVERS, lock_timeout_minutes=lambda: 5
        ).values()
    }

    assert reported <= set(control_panel.COMPONENTS_BY_KEY) | set(control_panel.LIVE_KEYS)


def test_unticking_the_looks_own_width_starts_from_160_pixels(control_panel, qt_app):
    field = width_field(built(control_panel, "Taskbar", "Taskbar Options"))
    field.checkbox.setChecked(False)

    assert (field.spin.value(), field.value()) == (160, "160")


def group_titles(tab):
    from PySide6.QtWidgets import QGroupBox

    return [box.title() for box in tab.findChildren(QGroupBox)]


def test_fields_registered_after_a_group_call_go_inside_it(control_panel, qt_app):
    from PySide6.QtWidgets import QGroupBox

    tab = control_panel.SettingsTab({}, control_panel.Actions())
    tab.text("OUTSIDE", "Outside:")
    tab.group("Menu speed")
    inside = tab.text("INSIDE", "Inside:")

    assert (group_titles(tab), inside.parent() is tab.findChildren(QGroupBox)[0]) == (["Menu speed"], True)


def test_taskbar_options_groups_the_taskbar_and_the_clock(control_panel, qt_app):
    assert group_titles(built(control_panel, "Taskbar", "Taskbar Options")) == ["Taskbar", "Clock"]


def test_log_on_groups_the_window_and_its_pictures(control_panel, qt_app):
    assert group_titles(built(control_panel, "Passwords", "Log On")) == [
        "Log on window",
        "Style",
        "Pictures",
        "Preview",
    ]


def test_typing_a_picture_path_tells_the_tab(make_tab):
    tab = make_tab({"START_LOGO": "penguin"})
    picture = tab.picture("START_LOGO", "Logo:", [("Penguin", "penguin")], default="penguin")
    picture.combo.setCurrentIndex(picture.combo.count() - 1)
    tab.changes.clear()
    picture.path_edit.setText("/home/u/logo.png")

    assert (tab.changes, tab.values()) == ([1], {"START_LOGO": "/home/u/logo.png"})


def test_form_labels_are_left_aligned_as_in_the_original_dialogs(control_panel, qt_app):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFormLayout

    tab = built(control_panel, "Taskbar", "Taskbar Options")
    field = tab.findChildren(QSpinBox)[0].parent()
    form = next(form for form in tab.findChildren(QFormLayout) if form.labelForField(field) is not None)

    assert (form.labelAlignment() & Qt.AlignLeft, form.labelForField(field).alignment() & Qt.AlignLeft) == (
        Qt.AlignLeft,
        Qt.AlignLeft,
    )


def test_spin_boxes_are_narrow_like_the_originals_instead_of_stretching(control_panel, qt_app):
    tab = built(control_panel, "Taskbar", "Taskbar Options")
    tab.resize(500, 400)
    tab.show()
    qt_app.processEvents()
    spin = tab.findChildren(QSpinBox)[0]

    assert spin.width() <= 80


def test_radio_field_offers_each_option_as_a_radio_button_and_reports_the_checked_one(make_tab):
    from PySide6.QtWidgets import QRadioButton

    tab = make_tab({"LOGIN_STYLE": "2000"})
    group = tab.radios("LOGIN_STYLE", "Style", [("Classic", "classic"), ("Windows 2000", "2000")], default="classic")
    buttons = group.findChildren(QRadioButton)
    saved = tab.values()
    buttons[0].setChecked(True)

    assert ([button.text() for button in buttons], saved, tab.values(), len(tab.changes)) == (
        ["Classic", "Windows 2000"],
        {"LOGIN_STYLE": "2000"},
        {"LOGIN_STYLE": "classic"},
        1,
    )


def test_radio_field_with_a_saved_value_that_is_not_an_option_checks_the_default(make_tab):
    tab = make_tab({"LOGIN_STYLE": "gone"})
    tab.radios("LOGIN_STYLE", "Style", [("Classic", "classic"), ("Windows 2000", "2000")], default="classic")

    assert tab.values() == {"LOGIN_STYLE": "classic"}


def test_radio_field_sits_in_a_titled_group_like_the_originals(make_tab):
    from PySide6.QtWidgets import QGroupBox

    tab = make_tab()
    group = tab.radios("CURSOR", "Pointer size", [("Normal", "24"), ("Large", "32")], default="32")

    assert (isinstance(group, QGroupBox), group.title()) == (True, "Pointer size")


def test_two_and_three_way_choices_are_radio_buttons_as_in_the_originals(control_panel, qt_app):
    from PySide6.QtWidgets import QRadioButton

    counts = {}
    for applet, tab_name, key in (
        ("Passwords", "Log On", "LOGIN_STYLE"),
        ("Booting Screen", "Boot Screen", "BOOT_STYLE"),
        ("Mouse", "Pointers", "CURSOR"),
        ("Explorer", "General", "EXPLORER"),
        ("Fonts", "Font", "FONT_SCOPE"),
    ):
        tab = built(control_panel, applet, tab_name, None, program_installed=lambda name: f"/usr/bin/{name}")
        counts[key] = len(tab.findChildren(QRadioButton))

    assert counts == {"LOGIN_STYLE": 2, "BOOT_STYLE": 2, "CURSOR": 3, "EXPLORER": 2, "FONT_SCOPE": 3}


def preview_image(control_panel, qt_app, look="1998"):
    """The task button preview at 160px, with a solid green 16px icon, grabbed."""
    from PySide6.QtGui import QColor, QIcon, QPixmap
    from reference import qimage_to_pil

    field = width_field(built(control_panel, "Taskbar", "Taskbar Options", {"TASK_BUTTON_WIDTH": "160", "LOOK": look}))
    square = QPixmap(16, 16)
    square.fill(QColor(0, 200, 0))
    field.preview.icon = QIcon(square)
    field.preview.resize(field.preview.sizeHint())
    field.preview.show()
    qt_app.processEvents()
    image = qimage_to_pil(field.preview.grab().toImage())
    field.preview.close()
    return image


def test_width_preview_draws_a_raised_and_a_pressed_task_button_like_the_taskbar(control_panel, qt_app):
    """As tests/test_plasma_taskbar_reference.py measures the real taskbar: 22px tall, the icon 16px at
    4,3, the title from x 23 (not centred), the second button sunken with the white and face
    checkerboard and its icon a pixel lower, the buttons 3px apart."""
    image = preview_image(control_panel, qt_app)
    green = (0, 200, 0)
    first = [(x, y) for x in range(160) for y in range(image.height) if image.getpixel((x, y)) == green]
    second = [(x, y) for x in range(163, 323) for y in range(image.height) if image.getpixel((x, y)) == green]
    first_box = (min(x for x, _ in first), min(y for _, y in first), max(x for x, _ in first), max(y for _, y in first))
    second_box = (
        min(x for x, _ in second),
        min(y for _, y in second),
        max(x for x, _ in second),
        max(y for _, y in second),
    )
    assert (first_box, second_box) == ((4, 3, 19, 18), (163 + 4, 4, 163 + 19, 19)), (first_box, second_box)
    ink = [x for x in range(20, 157) if any(image.getpixel((x, y)) == (0, 0, 0) for y in range(5, 18))]
    assert 22 <= ink[0] <= 24 and ink[-1] < 140, ink  # left-aligned after the icon, not centred in 160px
    inside = {image.getpixel((x, y)) for x in range(163 + 60, 163 + 100) for y in range(5, 20)}
    assert (255, 255, 255) in inside and (192, 192, 192) in inside, inside  # the pressed checkerboard
    assert image.getpixel((0, 0)) == (255, 255, 255) and image.getpixel((163, 0)) == (0, 0, 0), (
        "raised then sunken edges"
    )
    assert image.getpixel((161, 10)) not in {(255, 255, 255), (0, 0, 0)}, "a 3px gap of face between the buttons"
    assert image.height == 22


def test_choice_whose_saved_value_and_default_are_both_missing_shows_its_first_option(make_tab):
    combo = make_tab({"SAVER": "deepstars"}).choice(
        "SAVER", "Screen saver:", [("(None)", "none"), ("Maze", "maze")], default="deepstars"
    )

    assert (combo.currentIndex(), combo.currentText()) == (0, "(None)")


def test_a_field_without_a_label_spans_the_whole_row_like_the_originals(make_tab, qt_app):
    tab = make_tab()
    tab.text("LABELLED", "Title:")
    combo = tab.choice("UNLABELLED", "", [("One", "one")], default="one")
    tab.resize(300, 200)
    tab.show()
    qt_app.processEvents()

    assert (
        combo.mapTo(tab, combo.rect().topLeft()).x()
        == tab.findChildren(QLabel)[0].mapTo(tab, tab.findChildren(QLabel)[0].rect().topLeft()).x()
    )


def screen_saver_tab(control_panel, pictures, saved=None):
    return built(
        control_panel,
        "Display",
        "Screen Saver",
        saved or {"SAVER": "pipes"},
        list_screensavers=lambda: [("pipes", "3D Pipes"), ("maze3d", "3D Maze")],
        lock_timeout_minutes=lambda: 60,
        screensaver_pictures=lambda: pictures,
    )


def monitor_screen_colour(tab):
    return tab.monitor.grab().toImage().pixelColor(tab.monitor.screen_rect().center()).name()


def test_the_monitor_shows_the_chosen_screensavers_picture_and_the_desktop_for_one_without(
    control_panel, qt_app, tmp_path
):
    from PySide6.QtGui import QColor, QImage

    picture = QImage(*control_panel.MONITOR_SCREEN, QImage.Format_RGB32)
    picture.fill(QColor("#FF0000"))
    picture.save(str(tmp_path / "pipes.png"))
    tab = screen_saver_tab(control_panel, tmp_path)
    with_picture = monitor_screen_colour(tab)
    tab.saver_combo.setCurrentIndex(tab.saver_combo.findData("maze3d"))

    assert (with_picture, monitor_screen_colour(tab)) == ("#ff0000", "#008080")


def test_every_screensaver_has_a_picture_the_size_of_the_monitors_screen(control_panel):
    from PIL import Image

    savers = load_script("chicago95-screensaver").CATALOG
    pictures = REPO / "data/screensaver-previews"

    assert {name: Image.open(pictures / f"{name}.png").size for name in savers} == dict.fromkeys(
        savers, control_panel.MONITOR_SCREEN
    )


def test_wallpapers_are_the_pictures_in_pictures_then_each_plasma_wallpapers_largest_image(control_panel, tmp_path):
    pictures = tmp_path / "home/Pictures"
    pictures.mkdir(parents=True)
    (pictures / "clouds.png").write_bytes(b"png")
    (pictures / "notes.txt").write_text("no")
    images = tmp_path / "wallpapers/Next/contents/images"
    images.mkdir(parents=True)
    (images / "1280x800.png").write_bytes(b"small")
    (images / "3840x2160.png").write_bytes(b"much larger")

    assert control_panel.find_wallpapers(tmp_path / "home", tmp_path / "wallpapers") == [
        ("clouds", str(pictures / "clouds.png")),
        ("Next", str(images / "3840x2160.png")),
    ]


def test_appearance_items_are_the_parts_this_desktop_can_colour_in_alphabetical_order(control_panel, qt_app):
    tab = appearance(control_panel)

    assert [tab.items.itemText(index) for index in range(tab.items.count())] == [
        "Active Title Bar",
        "Desktop",
        "Icon",
        "Inactive Title Bar",
        "Start Menu Banner",
        "Start Menu Banner Text",
    ]


def test_choosing_an_item_shows_its_settings_as_the_originals_item_list_does(control_panel, qt_app):
    tab = appearance(control_panel)
    tab.items.setCurrentIndex(tab.items.findText("Icon"))

    assert tab.item_editors.currentWidget() is tab.icons.parentWidget()


def test_the_schemes_set_the_desktop_colour_teal_and_windows_2000_blue(control_panel, qt_app):
    tab = appearance(control_panel)
    teal = tab.values()["BACKGROUND_COLOR"]
    tab.scheme.setCurrentIndex(tab.scheme.findData("2000"))

    assert (teal, tab.values()["BACKGROUND_COLOR"]) == ("#008080", "#3A6EA5")


def test_save_as_and_delete_are_greyed_out_as_there_are_no_schemes_of_your_own(control_panel, qt_app):
    tab = appearance(control_panel)

    assert (tab.save_as_button.isEnabled(), tab.delete_button.isEnabled()) == (False, False)


def test_the_appearance_preview_paints_the_desktop_and_title_bars_in_the_chosen_colours(control_panel, qt_app):
    tab = appearance(control_panel)
    tab.color_edits["BACKGROUND_COLOR"].set_value("#102030")
    tab.color_edits["TITLE_ACTIVE"].set_value("#FF0000")
    image = tab.preview.grab().toImage()
    desktop = image.pixelColor(tab.preview.width() - 6, tab.preview.height() - 6).name()
    active = image.pixelColor(tab.preview.active_title.center()).name()

    assert (desktop, active) == ("#102030", "#ff0000")
