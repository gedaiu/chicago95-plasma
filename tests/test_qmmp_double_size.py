"""Winamp (qmmp) at Double Size on a screen scaled 1.5x or more, with its docked windows kept docked."""

import pytest
import qmmp_double_size
from conftest import run_bash_with_steps

SINGLE = """[Skinned]
double_size=false
eq_pos=@Point(934 1054)
mw_pos=@Point(659 1054)
pl_pos=@Point(659 1170)

[SkinnedShortcuts]
double_size=Meta+D
"""


DOUBLE = (
    SINGLE.replace("double_size=false", "double_size=true")
    .replace("@Point(934 1054)", "@Point(1209 1054)")
    .replace("@Point(659 1170)", "@Point(659 1286)")
)


def test_double_size_turns_on_and_the_docked_windows_move_twice_as_far_from_the_main_window():
    assert qmmp_double_size.sized(SINGLE, 2) == DOUBLE


def test_single_size_turns_double_size_off_and_the_docked_windows_move_back_against_the_main_window():
    assert qmmp_double_size.sized(DOUBLE, 1) == SINGLE


def test_a_player_already_at_its_size_is_left_as_it_is():
    assert qmmp_double_size.sized(DOUBLE, 2) == DOUBLE


def test_the_shortcut_named_double_size_is_not_mistaken_for_the_setting():
    assert "double_size=Meta+D" in qmmp_double_size.sized(SINGLE, 2)


def test_a_new_player_starts_at_its_size():
    assert qmmp_double_size.sized("", 2) == "[Skinned]\ndouble_size=true\n"


@pytest.mark.parametrize(("scale", "pixel"), [("1", 1), ("1.25", 1), ("1.5", 2), ("1.75", 2), ("2", 2), ("3", 2)])
def test_the_skins_pixel_is_the_screens_scale_rounded_and_capped_at_double(scale, pixel):
    assert qmmp_double_size.skin_pixel(scale) == pixel


def install_winamp_size(tmp_path, scale):
    (tmp_path / ".config/qmmp").mkdir(parents=True)
    (tmp_path / ".config/qmmp/qmmp.conf").write_text(SINGLE)
    run_bash_with_steps(
        tmp_path,
        f"SETUP_DRY_RUN=0; MANIFEST={tmp_path}/manifest; STATE_DIR={tmp_path}; SETUP_SCALE={scale}; size_winamp",
    )
    return (tmp_path / ".config/qmmp/qmmp.conf").read_text()


def test_setup_sets_double_size_on_a_screen_scaled_1_5x(tmp_path):
    assert "double_size=true" in install_winamp_size(tmp_path, "1.5")


def test_setup_leaves_winamp_at_single_size_on_a_1x_screen(tmp_path):
    assert install_winamp_size(tmp_path, "1") == SINGLE


def test_setup_returns_a_double_size_winamp_to_single_size_on_a_1x_screen(tmp_path):
    (tmp_path / ".config/qmmp").mkdir(parents=True)
    (tmp_path / ".config/qmmp/qmmp.conf").write_text(DOUBLE)
    run_bash_with_steps(
        tmp_path,
        f"SETUP_DRY_RUN=0; MANIFEST={tmp_path}/manifest; STATE_DIR={tmp_path}; SETUP_SCALE=1; size_winamp",
    )

    assert (tmp_path / ".config/qmmp/qmmp.conf").read_text() == SINGLE
