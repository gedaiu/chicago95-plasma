import configparser
import subprocess

import pytest
from conftest import REPO

THEMES = sorted((REPO / "data/sound-themes").iterdir())


def test_sound_themes_hold_windows_98_windows_2000_and_the_16_plus_schemes():
    assert (len(THEMES), {"Windows98", "Windows2000"} <= {theme.name for theme in THEMES}) == (19, True)


@pytest.mark.parametrize("theme", THEMES, ids=lambda theme: theme.name)
def test_sound_theme_inherits_chicago95_from_a_stereo_directory(theme):
    index = configparser.ConfigParser()
    index.read(theme / "index.theme")

    assert {key: index["Sound Theme"][key] for key in ("Inherits", "Directories")} == {
        "Inherits": "Chicago95",
        "Directories": "stereo",
    }


@pytest.mark.parametrize("theme", THEMES, ids=lambda theme: theme.name)
def test_sound_theme_plays_an_ogg_vorbis_desktop_login(theme):
    codec = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "csv=p=0",
            str(theme / "stereo/desktop-login.ogg"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert codec.stdout.strip() == "vorbis"
