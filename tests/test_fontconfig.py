"""The fontconfig rule Setup installs for the UI font (config/fontconfig/60-chicago95-pixel-font.conf).

MS W98 UI is a pixel font drawn on an 11px grid: at 11px (1x) and 22px (2x) its edges land on whole
pixels and it is drawn unsmoothed, sharp like the originals' text. At any other size (16 to 18px on a
1.5x screen) unsmoothed edges are jagged, so it is smoothed there, in grey (no colour fringes), with full
hinting so its strokes stay on whole pixels and dark.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import REPO, needs_ui_font

pytestmark = [needs_ui_font, pytest.mark.skipif(not shutil.which("fc-match"), reason="needs fc-match")]
RULE = REPO / "config/fontconfig/60-chicago95-pixel-font.conf"


def rendering(tmp_path, pixel_size):
    """{antialias, hintstyle, rgba} fontconfig gives the UI font at a pixel size, with only our rule on
    top of the system's configuration (the user's own rules left out)."""
    config = tmp_path / "fonts.conf"
    config.write_text(f'<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n<fontconfig>\n'
                      f'  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n  <include>{RULE}</include>\n</fontconfig>\n')
    environment = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "FONTCONFIG_FILE": str(config),
                   "XDG_CONFIG_HOME": str(tmp_path / "config")}   # the user's fonts, not their fontconfig rules
    output = subprocess.run(["fc-match", "-v", f"MS W98 UI:pixelsize={pixel_size}"], capture_output=True, text=True,
                            env=environment, timeout=30).stdout
    value = lambda name: (re.search(rf"\b{name}: (\S+)", output) or re.match("()", "")).group(1)
    return {"antialias": value("antialias"), "hintstyle": value("hintstyle"), "rgba": value("rgba")}


@pytest.mark.parametrize("pixel_size", [11, 22])
def test_ui_font_is_unsmoothed_on_its_pixel_grid(tmp_path, pixel_size):
    assert rendering(tmp_path, pixel_size)["antialias"] == "False(w)"


@pytest.mark.parametrize("pixel_size", [16, 16.5, 18])
def test_ui_font_is_smoothed_in_grey_with_full_hinting_off_its_grid(tmp_path, pixel_size):
    assert rendering(tmp_path, pixel_size) == {"antialias": "True(w)", "hintstyle": "3(i)(w)", "rgba": "5(i)(w)"}
