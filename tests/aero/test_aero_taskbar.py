"""The Aero superbar's Plasma style: task button faces against aero.msstyles' TASKITEM and the bar against Windows 7."""

import importlib.util

import pytest
from aero_sprites import requires_sprites
from conftest import REPO
from fit_aero_stops import TASK_STATES, task_image
from PIL import Image
from test_aero_buttons import rendered

spec = importlib.util.spec_from_file_location(
    "make_aero_plasmastyle", REPO / "aero/plasma-style/make_aero_plasmastyle.py"
)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
BAR_GLASS = (72, 132, 181, 255)


def over_bar(image):
    base = Image.new("RGBA", image.size, BAR_GLASS)
    base.alpha_composite(image)
    return base.convert("RGB")


@requires_sprites
@pytest.mark.parametrize("state", TASK_STATES)
def test_task_button_face_matches_its_sprite_over_the_bar_within_six_levels(qt_app, state):
    sprite = task_image(TASK_STATES.index(state))
    ours = over_bar(rendered(generator.task_face_svg(state), sprite.size))
    theirs = over_bar(sprite)
    differences = [
        abs(a - b)
        for p, q in zip(ours.get_flattened_data(), theirs.get_flattened_data(), strict=True)
        for a, b in zip(p, q, strict=True)
    ]

    assert sum(differences) / len(differences) < 6


THEME = REPO / "aero/plasma-style/theme"


def test_committed_plasma_style_equals_generator_output(tmp_path):
    generator.write_theme(tmp_path)

    assert {path.relative_to(tmp_path).as_posix(): path.read_bytes() for path in tmp_path.rglob("*.*")} == {
        path.relative_to(THEME).as_posix(): path.read_bytes() for path in THEME.rglob("*.*")
    }


def test_translucent_bar_over_the_reference_desktop_is_the_windows_7_taskbar_within_two_levels(qt_app):
    from aero_model import REFERENCE_DESKTOP
    from reference import screenshot

    bar = rendered((THEME / "translucent/widgets/panel-background.svg").read_text(), (28, 40)).crop((0, 0, 10, 40))
    seen = Image.new("RGBA", bar.size, REFERENCE_DESKTOP)
    seen.alpha_composite(bar)
    windows_7 = screenshot("win7dragedge").crop((600, 728, 601, 768))

    assert (
        max(
            abs(a - b)
            for y in range(40)
            for a, b in zip(seen.getpixel((5, y))[:3], windows_7.getpixel((0, y)), strict=True)
        )
        <= 2
    )


ORB_CENTRE, ORB_RADIUS = (27.5, 20.0), 19.5  # in the taskbar's rows: win7dragedge.png's orb at x 27.5, y 748


def test_start_orb_outside_its_logo_is_windows_7s_within_eighteen_levels(qt_app):
    from reference import screenshot

    windows_7 = screenshot("win7dragedge")
    empty_bar = windows_7.crop((600, 728, 601, 768)).resize((58, 40)).convert("RGBA")
    ours = Image.alpha_composite(empty_bar, rendered(generator.orb_svg(), (58, 40))).convert("RGB")
    theirs = windows_7.crop((0, 728, 58, 768))
    cx, cy = ORB_CENTRE
    ring = [
        (x, y)
        for x in range(58)
        for y in range(40)
        if 11**2 <= (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= (ORB_RADIUS - 0.5) ** 2
    ]
    differences = [
        abs(a - b) for x, y in ring for a, b in zip(ours.getpixel((x, y)), theirs.getpixel((x, y)), strict=True)
    ]

    assert sum(differences) / len(differences) < 18


@requires_sprites
@pytest.mark.parametrize("state", ["normal", "hover", "pressed"])
def test_show_desktop_face_matches_its_sprite_over_the_bar_within_six_levels(qt_app, state):
    from fit_aero_stops import SHOW_DESKTOP_STATES, show_desktop_image

    sprite = show_desktop_image(SHOW_DESKTOP_STATES.index(state))
    ours = over_bar(rendered(generator.show_desktop_face_svg(state), sprite.size))
    theirs = over_bar(sprite)
    differences = [
        abs(a - b)
        for p, q in zip(ours.get_flattened_data(), theirs.get_flattened_data(), strict=True)
        for a, b in zip(p, q, strict=True)
    ]

    assert sum(differences) / len(differences) < 6


@pytest.mark.parametrize("rim", [(8, 20), (27, 1), (27, 38)])
def test_start_orb_rim_is_white_glass_at_thirty_percent(qt_app, rim):
    # win7dragedge.png's rim is (112, 143, 170) over a (52, 97, 134) bar: white at 30% on every channel.
    red, green, blue, alpha = rendered(generator.orb_svg(), (58, 40)).getpixel(rim)

    assert (min(red, green, blue) >= 240, abs(alpha - 77) <= 13) == (True, True)


def test_start_orb_paints_nothing_outside_its_rim(qt_app):
    orb = rendered(generator.orb_svg(), (58, 40))
    cx, cy = ORB_CENTRE
    outside = [
        orb.getpixel((x, y))[3]
        for x in range(58)
        for y in range(40)
        if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 > (ORB_RADIUS + 1) ** 2
    ]

    assert max(outside) == 0
