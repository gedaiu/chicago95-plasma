"""The Chicago95Aero Aurorae theme: generated, complete, and shaped like the Windows 7 frame it was measured from."""

import configparser
import importlib.util
import re

import pytest
from conftest import REPO

THEME = REPO / "aero/aurorae/theme"
spec = importlib.util.spec_from_file_location("make_aero_aurorae", REPO / "aero/aurorae/make_aero_aurorae.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
AURORAE_STATES = (
    "active",
    "hover",
    "pressed",
    "deactivated",
    "inactive",
    "hover-inactive",
    "pressed-inactive",
    "deactivated-inactive",
)


def element_ids(path):
    return set(re.findall(r'id="([^"]+)"', path.read_text()))


def test_committed_theme_equals_generator_output(tmp_path):
    generator.write_theme(tmp_path)

    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == {
        path.name: path.read_bytes() for path in THEME.iterdir()
    }


@pytest.mark.parametrize(
    "prefix", ["decoration-", "decoration-inactive-", "decoration-maximized-", "decoration-maximized-inactive-"]
)
def test_decoration_has_all_nine_pieces_for(prefix):
    assert {f"{prefix}{piece}" for piece in generator.PIECES} - element_ids(THEME / "decoration.svg") == set()


def test_mask_covers_the_frame_so_kwin_blurs_behind_the_glass():
    assert {f"mask-{piece}" for piece in generator.PIECES} - element_ids(THEME / "decoration.svg") == set()


@pytest.mark.parametrize(
    "button", ["minimize", "maximize", "restore", "close", "help", "shade", "keepabove", "keepbelow", "alldesktops"]
)
def test_button_draws_every_aurorae_state(button):
    assert {f"{state}-center" for state in AURORAE_STATES} - element_ids(THEME / f"{button}.svg") == set()


def test_layout_is_the_measured_windows_7_frame():
    rc = configparser.ConfigParser()
    rc.optionxform = str
    rc.read(THEME / "Chicago95Aerorc")
    layout = rc["Layout"]

    assert {
        key: int(layout[key])
        for key in (
            "BorderLeft",
            "BorderRight",
            "BorderBottom",
            "TitleEdgeTop",
            "TitleHeight",
            "TitleEdgeRight",
            "ButtonHeight",
            "ButtonWidthMinimize",
            "ButtonWidthMaximizeRestore",
            "ButtonWidthClose",
            "ButtonSpacing",
        )
    } == {
        "BorderLeft": 8,
        "BorderRight": 8,
        "BorderBottom": 8,
        "TitleEdgeTop": 1,
        "TitleHeight": 29,
        "TitleEdgeRight": 6,
        "ButtonHeight": 20,
        "ButtonWidthMinimize": 30,
        "ButtonWidthMaximizeRestore": 27,
        "ButtonWidthClose": 50,
        "ButtonSpacing": -1,
    }
