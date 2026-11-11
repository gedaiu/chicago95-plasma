"""bin/chicago95-screensaver's catalogue: the classic savers of 95, 98 and 2000 and the XScreenSaver hack each one
runs (with the options that make it look the part); --list shows the installed ones in the classic order."""

import pytest
from conftest import load_script


@pytest.fixture(scope="session")
def screensaver():
    return load_script("chicago95-screensaver")


@pytest.fixture
def hacks(tmp_path):
    for name in ("deepstars", "vermiculate", "morph3d", "superquadrics", "fontglide", "pipes", "qix"):
        (tmp_path / name).write_text("")
    return tmp_path


def test_the_default_is_flying_through_space_and_it_streams_the_stars_at_the_viewer(screensaver, hacks):
    assert (screensaver.DEFAULT_HACK, screensaver.saver_command("deepstars", hacks)) == (
        "deepstars",
        [str(hacks / "deepstars"), "--speed", "3"],
    )


def test_the_classic_savers_of_95_98_and_2000_come_first_in_their_order(screensaver):
    assert list(screensaver.CATALOG)[:12] == [
        "deepstars",
        "beziers",
        "marquee",
        "qix",
        "blank",
        "flowerbox",
        "flyingobjects",
        "maze3d",
        "pipes",
        "fliptext",
        "flyingtoasters",
        "flurry",
    ]


@pytest.mark.parametrize(
    "name, label, command",
    [
        ("beziers", "Curves and Colors", ["vermiculate", "--speed", "2"]),
        (
            "marquee",
            "Marquee",
            ["fontglide", "--mode", "scroll", "--program", "echo Chicago95 for Plasma", "--font", "MS W98 UI-48"],
        ),
        ("flowerbox", "3D Flower Box", ["superquadrics", "--count", "1", "--spinspeed", "3"]),
        ("flyingobjects", "3D Flying Objects", ["morph3d"]),
    ],
)
def test_each_new_classic_runs_its_hack_with_the_options_that_make_it_look_the_part(
    screensaver, hacks, name, label, command
):
    assert (screensaver.CATALOG[name].label, screensaver.saver_command(name, hacks)) == (
        label,
        [str(hacks / command[0]), *command[1:]],
    )


def test_blank_screen_needs_no_hack_and_is_always_installed(screensaver, tmp_path):
    assert (screensaver.saver_command("blank", tmp_path), "blank" in screensaver.installed_savers(tmp_path)) == (
        None,
        True,
    )


def test_installed_savers_are_those_whose_hack_exists_two_may_share_one(screensaver, hacks):
    assert list(screensaver.installed_savers(hacks)) == [
        "deepstars",
        "beziers",
        "marquee",
        "qix",
        "blank",
        "flowerbox",
        "flyingobjects",
        "pipes",
    ]


def test_the_starfield_is_called_flying_through_space_as_the_originals_did(screensaver):
    assert screensaver.CATALOG["deepstars"].label == "Flying Through Space"
