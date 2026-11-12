import pytest
from aurorae_model import LOOKS
from conftest import load_script, run_bash_with_steps

COMPONENT_KEYS = ("DECORATION", "WIDGET_STYLE", "TASKBAR_STYLE", "START_MENU_STYLE", "BEVEL")


@pytest.fixture(scope="module")
def control_panel():
    return load_script("chicago95-control-panel")


@pytest.fixture(scope="module")
def startmenu():
    return load_script("chicago95-startmenu")


@pytest.fixture(scope="module")
def sysprops():
    return load_script("chicago95-sysprops")


@pytest.fixture(scope="module")
def shutdown():
    return load_script("chicago95-shutdown")


@pytest.fixture(scope="module")
def ui():
    import chicago95ui

    return chicago95ui


FLAT_MENU_STYLES = {"1995", "1998", "2000", "2001"}


def flat_menu_styles(control_panel):
    return {preset["START_MENU_STYLE"] for preset in control_panel.LOOK_PRESETS.values()} & FLAT_MENU_STYLES


def applied_components(tmp_path, look):
    variables = " ".join(f'"${{SETUP_{key}}}"' for key in COMPONENT_KEYS)
    line = run_bash_with_steps(tmp_path, f"apply_look {look}; echo {variables}")[0]
    return dict(zip(COMPONENT_KEYS, line.split(), strict=True))


@pytest.mark.parametrize("look", ["1995", "1998", "2000", "2001", "luna"])
def test_apply_look_sets_the_components_the_preset_lists_for_that_look(control_panel, tmp_path, look):
    preset = control_panel.LOOK_PRESETS[look]

    assert applied_components(tmp_path, look) == {key: preset[key] for key in COMPONENT_KEYS}


def test_every_look_preset_lists_every_component(control_panel):
    assert {look: sorted(set(COMPONENT_KEYS) - set(preset)) for look, preset in control_panel.LOOK_PRESETS.items()} == {
        look: [] for look in control_panel.LOOK_PRESETS
    }


def test_every_start_menu_style_has_a_banner_style_and_a_root_icon_set(control_panel, startmenu):
    styles = flat_menu_styles(control_panel)

    assert (styles - set(startmenu.STYLES), styles - set(startmenu.ROOT_ICON_SETS)) == (set(), set())


def test_every_start_menu_style_has_a_system_properties_tab_set_and_shutdown_dialogs(control_panel, sysprops, shutdown):
    styles = flat_menu_styles(control_panel)

    assert (
        styles - set(sysprops.TABS),
        styles - set(shutdown.CHOICES),
        styles - set(shutdown.ShutDownDialog.BODIES),
        styles - set(LOOKS),
    ) == (set(), set(), set(), set())


@pytest.mark.parametrize("bevel", ["1995", "2000"])
def test_bevel_colors_returns_light_shadow_and_dark_for_bevel(ui, bevel):
    from PySide6.QtGui import QColor

    assert sorted(ui.bevel_colors(QColor("#C0C0C0"), bevel)) == ["dark", "light", "shadow"]


def test_every_bevel_a_preset_uses_is_one_the_bevel_test_covers(control_panel):
    assert {preset["BEVEL"] for preset in control_panel.LOOK_PRESETS.values()} == {"1995", "2000"}


@pytest.mark.parametrize("style, bevel", [("1995", "1995"), ("1998", "1995"), ("2000", "2000")])
def test_look_settings_derives_the_bevel_from_the_start_menu_style_in_an_old_config(ui, tmp_path, style, bevel):
    old_config = tmp_path / "chicago95rc"
    old_config.write_text(f"[StartMenu]\nstyle={style}\n")

    look = ui.look_settings(old_config)

    assert {key: look[key] for key in ("decoration", "widgetStyle", "bevel")} == {
        "decoration": "classic",
        "widgetStyle": "classic",
        "bevel": bevel,
    }


def test_luna_theme_folders_exist_for_the_aurorae_decoration_and_the_plasma_style():
    from conftest import REPO

    assert (
        (REPO / "luna/aurorae/theme/decoration.svg").is_file(),
        (REPO / "luna/plasma-style/theme/metadata.json").is_file(),
    ) == (True, True)


def test_luna_preset_sets_every_component_to_luna_with_the_xp_title_colours(control_panel):
    assert {
        key: control_panel.LOOK_PRESETS["luna"][key]
        for key in ("DECORATION", "WIDGET_STYLE", "TASKBAR_STYLE", "START_MENU_STYLE", "TITLE_ACTIVE")
    } == {
        "DECORATION": "luna",
        "WIDGET_STYLE": "luna",
        "TASKBAR_STYLE": "luna",
        "START_MENU_STYLE": "luna",
        "TITLE_ACTIVE": "#0054E3,#3F97FF",
    }
