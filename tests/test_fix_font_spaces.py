import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from conftest import REPO

INSTALLED_FONT = Path.home() / ".local/share/fonts/MSW98UI-Regular.otf"


def space_widths(path):
    font = TTFont(path)
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    charstrings = font["CFF "].cff.topDictIndex[0].CharStrings
    for glyph in (cmap[0x20], cmap[0xA0]):
        charstrings[glyph].decompile()
    return {"space": hmtx[cmap[0x20]][0], "no-break space": hmtx[cmap[0xA0]][0],
            "same outline": charstrings[cmap[0x20]].program == charstrings[cmap[0xA0]].program}


@pytest.mark.skipif(not INSTALLED_FONT.exists(), reason="MS W98 UI is not installed")
def test_no_break_space_of_ms_w98_ui_regular_becomes_273_like_its_space(tmp_path):
    font = tmp_path / INSTALLED_FONT.name
    shutil.copy(INSTALLED_FONT, font)

    output = subprocess.run([sys.executable, str(REPO / "setup/fix-font-spaces.py"), str(font)],
                            capture_output=True, text=True, check=True).stdout

    assert (space_widths(font), output) == (
        {"space": 273, "no-break space": 273, "same outline": True},
        f"{font}: no-break space 91 -> 273\n")


@pytest.mark.skipif(not INSTALLED_FONT.exists(), reason="MS W98 UI is not installed")
def test_second_run_on_a_repaired_font_changes_nothing(tmp_path):
    font = tmp_path / INSTALLED_FONT.name
    shutil.copy(INSTALLED_FONT, font)
    subprocess.run([sys.executable, str(REPO / "setup/fix-font-spaces.py"), str(font)], check=True, capture_output=True)

    second = subprocess.run([sys.executable, str(REPO / "setup/fix-font-spaces.py"), str(font)],
                            capture_output=True, text=True, check=True).stdout

    assert second == ""
