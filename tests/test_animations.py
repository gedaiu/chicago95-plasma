"""The animation events and choices (setup/animations.conf, read by lib/chicago95animations.py) and the KWin effects
installed beside them, as the Control Panel's Effects tab offers them."""

import json

import chicago95animations as animations
import pytest
from conftest import REPO

TOPLEVEL = "toplevel-open-close-animation"


@pytest.fixture(scope="module")
def table():
    return animations.read_animations(REPO / "setup/animations.conf")


def scripted_effect(root, effect_id, name, category=None, enabled=False, config=False):
    folder = root / effect_id
    folder.mkdir(parents=True)
    metadata = {"KPlugin": {"Id": effect_id, "Name": name, "EnabledByDefault": enabled}}
    if category:
        metadata["X-KWin-Exclusive-Category"] = category
    if config:
        metadata["X-KDE-ConfigModule"] = "kcm_kwin4_genericscripted"
    (folder / "metadata.json").write_text(json.dumps(metadata))


def builtin_effect(folder, effect_id, name, group=None, enabled=False, config=False):
    folder.mkdir(parents=True, exist_ok=True)
    metadata = {"KPlugin": {"Name": name, "EnabledByDefault": enabled}}
    if group:
        metadata["org.kde.kwin.effect"] = {"exclusiveGroup": group}
    if config:
        metadata["X-KDE-ConfigModule"] = f"kwin_{effect_id}_config"
    (folder / f"{effect_id}.json").write_text(json.dumps(metadata))


@pytest.fixture
def installed(tmp_path):
    user, builtin = tmp_path / "user", tmp_path / "builtin"
    scripted_effect(user, "kwin6_effect_fire", "Fire [Burn-My-Windows]", TOPLEVEL, config=True)
    scripted_effect(user, "scale", "Scale", TOPLEVEL, enabled=True, config=True)
    builtin_effect(builtin, "glide", "Glide", TOPLEVEL, config=True)
    builtin_effect(builtin, "squash", "Squash", "minimize", enabled=True)
    builtin_effect(builtin, "magiclamp", "Magic Lamp", "minimize", config=True)
    return animations.installed_effects(animations.EffectRoots(scripted=(user,), builtin=builtin))


def test_the_effects_tab_groups_its_events_in_the_files_order(table):
    assert [(event.group, event.key) for event in table.events] == [
        ("Windows", "ANIM_WINDOWS"),
        ("Windows", "ANIM_MINIMIZE"),
        ("Windows", "ANIM_MAXIMIZE"),
        ("Windows", "ANIM_DIALOGS"),
        ("Windows", "ANIM_WOBBLY"),
        ("Desktop", "ANIM_SHOW_DESKTOP"),
        ("Desktop", "ANIM_DESKTOPS"),
        ("Desktop", "ANIM_SESSION"),
        ("Menus and taskbar", "ANIM_MENUS"),
        ("Menus and taskbar", "ANIM_NOTIFICATIONS"),
        ("Menus and taskbar", "ANIM_TASKBAR"),
        ("Speed", "ANIM_SPEED"),
    ]


def test_installed_effects_carry_their_name_category_default_and_settings_page(installed):
    assert {
        effect_id: (effect.name, effect.category, effect.enabled_by_default, effect.settings)
        for effect_id, effect in installed.items()
    } == {
        "kwin6_effect_fire": ("Fire [Burn-My-Windows]", TOPLEVEL, False, ("kcmshell6", "kcm_kwin_effects")),
        "scale": ("Scale", TOPLEVEL, True, ("kcmshell6", "kcm_kwin_effects")),
        "glide": ("Glide", TOPLEVEL, False, ("kcmshell6", "kwin/effects/configs/kwin_glide_config")),
        "squash": ("Squash", "minimize", True, None),
        "magiclamp": ("Magic Lamp", "minimize", False, ("kcmshell6", "kwin/effects/configs/kwin_magiclamp_config")),
    }


def test_window_choices_add_installed_effects_of_their_category_by_name(table, installed):
    assert animations.event_choices(table, "ANIM_WINDOWS", installed) == [
        ("None", "none"),
        ("Scale", "scale"),
        ("Glide", "glide"),
        ("Fade", "fade"),
        ("Fire [Burn-My-Windows]", "kwin6_effect_fire"),
    ]


def test_an_events_effects_are_its_choices_and_the_installed_ones_of_its_category(table, installed):
    assert animations.event_effects(table, "ANIM_WINDOWS", installed) == {"scale", "glide", "fade", "kwin6_effect_fire"}


@pytest.mark.parametrize(
    "key, value, effects",
    [
        ("ANIM_MINIMIZE", "zoom", ("chicago95zoom/Minimize",)),
        ("ANIM_MENUS", "both", ("slidingpopups", "fadingpopups")),
        ("ANIM_WINDOWS", "kwin6_effect_fire", ("kwin6_effect_fire",)),
        ("ANIM_WINDOWS", "none", ()),
    ],
)
def test_a_choice_turns_on_its_effects_and_an_installed_effects_choice_turns_on_that_effect(table, key, value, effects):
    assert animations.choice_effects(table, key, value) == effects


def live(plugins=None, effect_settings=None, own=None, speed=None):
    kwinrc = {
        "Plugins": plugins or {},
        **{f"Effect-{name}": values for name, values in (effect_settings or {}).items()},
    }
    return animations.LiveState(kwinrc=kwinrc, own=own or {}, speed=speed)


@pytest.mark.parametrize(
    "key, state, expected",
    [
        ("ANIM_WINDOWS", live(), "scale"),
        ("ANIM_WINDOWS", live({"scaleEnabled": "false", "kwin6_effect_fireEnabled": "true"}), "kwin6_effect_fire"),
        ("ANIM_WINDOWS", live({"scaleEnabled": "false"}), "none"),
        ("ANIM_MINIMIZE", live({"squashEnabled": "false", "magiclampEnabled": "true"}), "magiclamp"),
        (
            "ANIM_MINIMIZE",
            live({"squashEnabled": "false", "chicago95zoomEnabled": "true"}, {"chicago95zoom": {"Minimize": "true"}}),
            "zoom",
        ),
        ("ANIM_MINIMIZE", live({"squashEnabled": "false", "chicago95zoomEnabled": "true"}), "none"),
        ("ANIM_TASKBAR", live(), "slide"),
        ("ANIM_TASKBAR", live(own={"ANIM_TASKBAR": "none"}), "none"),
        ("ANIM_SPEED", live(), "1"),
        ("ANIM_SPEED", live(speed="0"), "0"),
        ("ANIM_SPEED", live(speed="0.4"), "0.5"),
    ],
)
def test_without_a_saved_choice_the_event_shows_what_kde_does_now(table, installed, key, state, expected):
    assert animations.current_choice(table, key, installed, state) == expected


def test_the_classic_button_gives_the_looks_windows_choices(table):
    assert {key: value for key, value in table.classic["1998"].items() if value not in ("none", "no", "1")} == {
        "ANIM_MINIMIZE": "zoom",
        "ANIM_MAXIMIZE": "zoom",
        "ANIM_MENUS": "slide",
    }


def test_reading_kwinrc_keeps_its_keys_case(tmp_path):
    kwinrc = tmp_path / "kwinrc"
    kwinrc.write_text(
        "[Plugins]\nwobblywindowsEnabled=true\n\n[Effect-chicago95zoom]\nMinimize=true\nInputMethod[$d]\n"
    )
    assert animations.read_kde_config(kwinrc) == {
        "Plugins": {"wobblywindowsEnabled": "true"},
        "Effect-chicago95zoom": {"Minimize": "true"},
    }


def test_the_live_state_is_kwinrc_our_own_animation_choices_and_kdes_speed(tmp_path):
    (tmp_path / "kwinrc").write_text("[Plugins]\nsquashEnabled=false\n")
    (tmp_path / "chicago95rc").write_text("[Animations]\nANIM_MENUS=fade\n")
    (tmp_path / "kdeglobals").write_text("[KDE]\nAnimationDurationFactor=0.5\n")

    assert animations.live_state(tmp_path) == animations.LiveState(
        kwinrc={"Plugins": {"squashEnabled": "false"}}, own={"ANIM_MENUS": "fade"}, speed="0.5"
    )


@pytest.mark.parametrize(
    "own, speed, expected",
    [
        ({}, None, ("slide", 90)),
        ({"ANIM_MENUS": "fade"}, "2", ("fade", 180)),
        ({"ANIM_MENUS": "slide"}, "0", ("none", 0)),
    ],
)
def test_our_own_animation_is_the_saved_choice_at_kdes_speed_and_none_when_the_speed_is_off(own, speed, expected):
    state = animations.LiveState(kwinrc={}, own=own, speed=speed)
    assert animations.own_animation(state, "ANIM_MENUS", "slide", 90) == expected


def tasks_qml():
    return (REPO / "plasmoids/org.chicago95.tasks/contents/ui/main.qml").read_text()


def test_taskbar_buttons_slide_only_while_the_effects_tab_lets_them():
    assert "enabled: entry.slides && !root.bandCarried && Plasmoid.configuration.animateButtons" in tasks_qml()


def test_window_buttons_tell_kwin_where_they_are_so_minimizing_aims_at_them():
    assert "tasksModel.requestPublishDelegateGeometry(entry.modelIndex," in tasks_qml()
