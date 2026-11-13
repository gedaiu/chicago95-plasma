"""Winamp (qmmp) at Double Size on a screen scaled 1.5x or more, with its docked windows kept docked."""

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


def test_double_size_turns_on_and_the_docked_windows_move_twice_as_far_from_the_main_window():
    assert qmmp_double_size.doubled(SINGLE) == SINGLE.replace("double_size=false", "double_size=true").replace(
        "@Point(934 1054)", "@Point(1209 1054)"
    ).replace("@Point(659 1170)", "@Point(659 1286)")


def test_a_player_already_at_double_size_is_left_as_it_is():
    already = qmmp_double_size.doubled(SINGLE)

    assert qmmp_double_size.doubled(already) == already


def test_the_shortcut_named_double_size_is_not_mistaken_for_the_setting():
    assert "double_size=Meta+D" in qmmp_double_size.doubled(SINGLE)


def test_a_new_player_starts_at_double_size():
    assert qmmp_double_size.doubled("") == "[Skinned]\ndouble_size=true\n"


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
