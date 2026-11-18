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
