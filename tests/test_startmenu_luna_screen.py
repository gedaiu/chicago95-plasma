"""The XP Start menu as the program draws it on a 1.5x screen (bin/chicago95-startmenu --screenshot in a process of
its own at QT_SCALE_FACTOR=1.5), with the icon sets Setup installed: icons without white squares, the footer's
texts whole. Each of these broke only at a fractional scale."""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest
from conftest import REPO
from PIL import Image

spec = importlib.util.spec_from_file_location("chicago95lunamenu", REPO / "luna/lib/chicago95lunamenu.py")
lunamenu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lunamenu)

SCALE = 1.5
RIGHT_COLUMN_FILL = (0xD3, 0xE5, 0xFA)
INSTALLED_ICONS = Path.home() / ".local/share/icons"


@pytest.fixture(scope="module")
def screen(tmp_path_factory):
    if not (INSTALLED_ICONS / "SE98").is_dir():
        pytest.skip("the SE98 icon set (installed by Setup) is not on this machine")
    home = tmp_path_factory.mktemp("home")
    (home / ".config").mkdir()
    (home / ".config/chicago95rc").write_text("[Look]\nwidgetStyle=luna\n[StartMenu]\nstyle=luna\n")
    (home / ".config/kdeglobals").write_text("[Icons]\nTheme=SE98\n")
    (home / ".local/share").mkdir(parents=True)
    (home / ".local/share/icons").symlink_to(INSTALLED_ICONS)
    picture = home / "menu.png"
    environment = {
        **os.environ,
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "QT_QPA_PLATFORM": "offscreen",
    }
    environment["QT_SCALE_FACTOR"] = str(SCALE)
    subprocess.run(
        ["python3", str(REPO / "bin/chicago95-startmenu"), "--screenshot", str(picture)],
        env=environment,
        timeout=60,
        check=True,
        capture_output=True,
    )
    return Image.open(picture).convert("RGB")


def device(value):
    return round(value * SCALE)


def test_the_menu_is_380_by_477_at_one_and_a_half_scale(screen):
    assert screen.size == (device(380), device(477))


@pytest.mark.parametrize("index", [6, 7, 8, 9])  # Printers and Faxes, Help and Support, Search, Run...
def test_a_right_column_icon_has_no_white_square_behind_it(screen, index):
    left, top = device(lunamenu.RIGHT_COLUMN.left() + 1 + 6), device(lunamenu.RIGHT_ROW_TOPS[index] + 4)

    assert screen.getpixel((left + 1, top + 1)) == RIGHT_COLUMN_FILL


def test_the_footer_shows_its_texts_whole(screen):
    """The last 12 pixels of the footer's light text span 3 rows when they are an ellipsis's dots, 5 or more when
    they are the end of "Turn Off Computer" (measured on both renders)."""
    footer = screen.crop(
        (device(170), device(lunamenu.FOOTER_ICON_TOP), device(380), device(lunamenu.FOOTER_ICON_TOP + 24))
    )
    light = [
        [footer.getpixel((x, y))[2] > 230 and footer.getpixel((x, y))[0] > 230 for x in range(footer.width)]
        for y in range(footer.height)
    ]
    columns = [x for x in range(footer.width) if any(row[x] for row in light)]
    last_text = [x for x in columns if x > columns[-1] - device(12)]

    assert len({y for y in range(footer.height) for x in last_text if light[y][x]}) > 3
