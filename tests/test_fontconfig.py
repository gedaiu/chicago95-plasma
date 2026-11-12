"""The fontconfig rule Setup installs for the UI font (config/fontconfig/60-chicago95-pixel-font.conf).

MS W98 UI is a pixel font drawn on an 11px grid: at 11px (1x) and 22px (2x) its edges land on whole
pixels and it is drawn unsmoothed, sharp like the originals' text. At any other size (16 to 18px on a
1.5x screen) unsmoothed edges are jagged, so it is smoothed there, in grey (no colour fringes), by the
autohinter with light hinting: the font's own hints made FreeType spill a grey column left of each line.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO, needs_ui_font

pytestmark = [needs_ui_font, pytest.mark.skipif(not shutil.which("fc-match"), reason="needs fc-match")]
RULE = REPO / "config/fontconfig/60-chicago95-pixel-font.conf"


def rendering(tmp_path, pixel_size):
    """{antialias, hintstyle, rgba} fontconfig gives the UI font at a pixel size, with only our rule on
    top of the system's configuration (the user's own rules left out)."""
    environment = fontconfig_environment(tmp_path)
    output = subprocess.run(
        ["fc-match", "-v", f"MS W98 UI:pixelsize={pixel_size}"],
        capture_output=True,
        text=True,
        env=environment,
        timeout=30,
        check=False,
    ).stdout

    def value(name):
        return (re.search(rf"\b{name}: (\S+)", output) or re.match("()", "")).group(1)

    return {
        "antialias": value("antialias"),
        "hintstyle": value("hintstyle"),
        "rgba": value("rgba"),
        "autohint": value("autohint"),
    }


def fontconfig_environment(tmp_path):
    config = tmp_path / "fonts.conf"
    config.write_text(
        f'<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n<fontconfig>\n'
        f'  <include ignore_missing="yes">/etc/fonts/fonts.conf</include>\n  <include>{RULE}</include>\n</fontconfig>\n'
    )
    return {
        "PATH": "/usr/bin:/bin",
        "SETUP_OS_RELEASE": "/dev/null",
        "HOME": str(Path.home()),
        "FONTCONFIG_FILE": str(config),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
    }  # the user's fonts, not their fontconfig rules


RENDER_FIRST_COLUMNS = """
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter
app = QGuiApplication([])
image = QImage(80, 24, QImage.Format_RGB32)
image.fill(Qt.white)
painter = QPainter(image)
font = QFont("MS W98 UI")
font.setPixelSize(int(sys.argv[1]))
painter.setFont(font)
painter.setPen(Qt.black)
painter.drawText(5, 18, "Crash")
painter.end()
print([min(QColor(image.pixel(x, y)).red() for y in range(24)) for x in range(3, 7)])
"""


@pytest.mark.parametrize("pixel_size", [16, 18])
def test_smoothed_ui_font_draws_no_ink_left_of_where_the_text_starts(tmp_path, pixel_size):
    """Drawn at x 5, the first letter's ink begins at column 5: with the font's own hints FreeType spilled
    a grey column left of it, which a title or label starting at its box's edge clips, so the first letter
    looked cut off. The autohinter keeps the ink on the glyph's own columns."""
    output = subprocess.run(
        [sys.executable, "-c", RENDER_FIRST_COLUMNS, str(pixel_size)],
        capture_output=True,
        text=True,
        env={**fontconfig_environment(tmp_path), "QT_QPA_PLATFORM": "offscreen"},
        timeout=60,
        check=False,
    ).stdout
    darkest = eval(output.strip().splitlines()[-1])  # the four columns' darkest values, from column 3
    assert darkest[:2] == [255, 255] and darkest[2] < 128, darkest


@pytest.mark.parametrize("pixel_size", [11, 22])
def test_ui_font_is_unsmoothed_on_its_pixel_grid(tmp_path, pixel_size):
    assert rendering(tmp_path, pixel_size)["antialias"] == "False(w)"


@pytest.mark.parametrize("pixel_size", [16, 16.5, 18])
def test_ui_font_is_smoothed_in_grey_with_the_light_autohinter_off_its_grid(tmp_path, pixel_size):
    assert rendering(tmp_path, pixel_size) == {
        "antialias": "True(w)",
        "hintstyle": "1(i)(w)",
        "rgba": "5(i)(w)",
        "autohint": "True(w)",
    }


def test_setup_installs_the_rule_that_smooths_winamps_18px_playlist(tmp_path):
    """qmmp's playlist font is 9 points: 18px on a 1.5x screen, where the old rule left it jagged."""
    (tmp_path / ".local/share").mkdir(parents=True)
    (tmp_path / ".local/share/fonts").symlink_to(Path.home() / ".local/share/fonts")  # Setup's font step needs the font
    subprocess.run(
        [str(REPO / "install.sh"), "--plain", "--yes", "--dry-run", "--components=look"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        env={"PATH": "/usr/bin:/bin", "SETUP_OS_RELEASE": "/dev/null", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()

    assert f"would-copy: {RULE} -> {tmp_path}/.config/fontconfig/conf.d/{RULE.name}" in log
    assert rendering(tmp_path, 18)["antialias"] == "True(w)"
