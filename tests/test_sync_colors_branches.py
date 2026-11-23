import os
import shutil
import site
import subprocess
import sys

import pytest
from conftest import REPO

DEFAULT_STAMP = (
    "--active #000080 --inactive #808080 --inactive-text #c0c0c0 --face #c0c0c0 --light #dfdfdf "
    "--shadow #808080 --dark #000000 --gradient-margins 0,0"
)


@pytest.fixture
def home(tmp_path):
    """A home whose decoration folder holds the two generators, as the install leaves them."""
    decoration = tmp_path / ".local/share/aurorae/themes/Chicago95"
    decoration.mkdir(parents=True)
    for generator in ("aurorae/make_chicago95_aurorae.py", "aurorae/bevel.py"):
        shutil.copy(REPO / generator, decoration)
    shutil.copy(REPO / "plasma-style/make_chicago95_plasmastyle.py", decoration)
    return tmp_path


def sync_colors(home, *arguments):
    environment = {
        **os.environ,
        "SETUP_OS_RELEASE": "/dev/null",
        "HOME": str(home),
        "PYTHONUSERBASE": site.getuserbase(),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent",
    }
    return subprocess.run(
        [sys.executable, str(REPO / "bin/chicago95-sync-colors"), *arguments],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


def stamp_file(home):
    return home / "cache/chicago95-title-colors"


def test_first_run_redraws_and_stamps_the_title_colours(home):
    result = sync_colors(home)

    assert (result.returncode, result.stdout, stamp_file(home).read_text()) == (
        0,
        f"title bars redrawn: {DEFAULT_STAMP}\n",
        DEFAULT_STAMP,
    )


def test_run_with_unchanged_stamp_does_nothing(home):
    stamp_file(home).parent.mkdir(parents=True)
    stamp_file(home).write_text(DEFAULT_STAMP)

    result = sync_colors(home)

    assert (result.returncode, result.stdout) == (0, "")


def test_run_with_a_different_stamp_redraws(home):
    stamp_file(home).parent.mkdir(parents=True)
    stamp_file(home).write_text("--active #123456")

    result = sync_colors(home)

    assert (result.stdout, stamp_file(home).read_text()) == (f"title bars redrawn: {DEFAULT_STAMP}\n", DEFAULT_STAMP)


def test_force_redraws_although_the_stamp_is_unchanged(home):
    stamp_file(home).parent.mkdir(parents=True)
    stamp_file(home).write_text(DEFAULT_STAMP)

    result = sync_colors(home, "--force")

    assert result.stdout == f"title bars redrawn: {DEFAULT_STAMP}\n"


def test_redraws_the_plasma_style_when_it_is_installed(home):
    plasma_style = home / ".local/share/plasma/desktoptheme/Chicago95"
    plasma_style.mkdir(parents=True)

    result = sync_colors(home)

    assert (result.returncode, any(plasma_style.iterdir())) == (0, True)


@pytest.mark.parametrize(
    ("old_palette", "new_palette"),
    [("#000080", "#204060"), ("#0a246a,#a6caf0", "#204060,#6080a0")],
)
def test_keeps_the_travelling_title_in_sync_with_the_active_colors(home, old_palette, new_palette):
    config = home / "config"
    config.mkdir()
    (config / "kdeglobals").write_text("[WM]\nactiveBackground=32,64,96\nactiveBlend=96,128,160\n")
    kwinrc = config / "kwinrc"
    kwinrc.write_text(f"[Effect-chicago95zoom]\nClassicStripPalette={old_palette}\n")

    result = sync_colors(home)

    assert result.returncode == 0, result.stderr
    assert f"ClassicStripPalette={new_palette}\n" in kwinrc.read_text()


def test_with_the_aero_decoration_succeeds_without_redrawing_the_glass_frame(home):
    (home / "config").mkdir()
    (home / "config/chicago95rc").write_text("[Look]\ndecoration=aero\n")

    result = sync_colors(home)

    assert (result.returncode, result.stderr) == (0, "")


def test_with_the_aero_taskbar_succeeds_without_redrawing_the_glass_bar(home):
    (home / "config").mkdir()
    (home / "config/chicago95rc").write_text("[Look]\ntaskbarStyle=aero\n")
    (home / ".local/share/plasma/desktoptheme/Chicago95").mkdir(parents=True)

    result = sync_colors(home)

    assert (result.returncode, result.stderr) == (0, "")
