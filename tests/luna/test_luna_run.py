import pytest
from conftest import load_script

from .luna_tools_support import (
    columns_with,
    differing_fraction,
    grab_picture,
    has_classic_bevel,
    hex_rgb,
    reference,
    save_preview,
)

CLIENT_ORIGIN = (3, 29)
CLIENT_SIZE = (341, 154)
BUTTON_ROW = 150
FIELD_ROW = 99
WINDOW_FACE = "#ECE9D8"
TEXT_AND_ICON_MASKS = [(0, 0, 340, 56), (8, 60, 52, 80), (58, 61, 326, 79), (96, 118, 330, 132)]


@pytest.fixture
def luna_run(luna_look):
    dialog = load_script("chicago95-run").RunDialog({"osName": "Windows XP"}, [], [], history=[])
    dialog.show()
    yield dialog
    dialog.close()


@pytest.fixture
def run_picture(luna_run):
    return grab_picture(luna_run)


@pytest.fixture(scope="module")
def xp_run():
    return reference("xprun.png").crop(
        (*CLIENT_ORIGIN, CLIENT_ORIGIN[0] + CLIENT_SIZE[0], CLIENT_ORIGIN[1] + CLIENT_SIZE[1])
    )


def test_luna_run_dialog_is_the_xp_run_client_size(luna_run):
    assert (luna_run.width(), luna_run.height()) == CLIENT_SIZE


def test_luna_run_dialog_draws_no_classic_bevel_or_navy_title(run_picture):
    assert not has_classic_bevel(run_picture)


def test_luna_run_dialog_is_on_the_xp_window_face(run_picture):
    assert run_picture.getpixel((5, 5)) == hex_rgb(WINDOW_FACE)


def test_luna_run_buttons_have_the_xp_border_columns(run_picture, xp_run):
    row = BUTTON_ROW - CLIENT_ORIGIN[1]
    assert columns_with(run_picture, "#003C74", row + 12) == columns_with(xp_run, "#003C74", row + 12)


def test_luna_run_combo_has_the_xp_field_border_columns(run_picture, xp_run):
    row = FIELD_ROW - CLIENT_ORIGIN[1]
    assert columns_with(run_picture, "#7F9DB9", row - 5) == columns_with(xp_run, "#7F9DB9", row - 5)


def test_luna_run_dialog_matches_xprun_outside_text_and_icon(run_picture, xp_run):
    save_preview("run", run_picture, xp_run)
    assert differing_fraction(run_picture, xp_run, TEXT_AND_ICON_MASKS) < 0.05


def test_luna_run_dialog_keeps_the_classic_outline_hidden(luna_run):
    assert not luna_run.outline.isVisible()
