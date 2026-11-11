import re
import subprocess
from pathlib import Path

import pytest
from conftest import REPO
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from .luna_tools_support import grab_picture, hex_rgb

LUNA_STYLESHEET = (REPO / "data/plasmashell-menus-luna.qss").read_text()
CLASSIC_STYLESHEET = (REPO / "data/plasmashell-menus.qss").read_text()


@pytest.fixture
def menu(qt_app):
    menu = QMenu()
    menu.setStyleSheet(LUNA_STYLESHEET)
    for label in ("Firefox", "Dolphin"):
        menu.addAction(QAction(label, menu))
    menu.setActiveAction(menu.actions()[1])
    menu.adjustSize()
    menu.show()
    yield menu
    menu.close()


def test_luna_sheet_panel_is_white(menu):
    assert grab_picture(menu).getpixel((menu.width() - 6, 6)) == hex_rgb("#FFFFFF")


def test_luna_sheet_border_is_one_pixel_acd899(menu):
    picture = grab_picture(menu)
    assert (picture.getpixel((0, 20)), picture.getpixel((1, 20))) == (hex_rgb("#ACA899"), hex_rgb("#FFFFFF"))


def test_luna_sheet_selected_row_is_blue_316ac5(menu):
    row = menu.actionGeometry(menu.actions()[1]).center()
    assert grab_picture(menu).getpixel((menu.width() - 6, row.y())) == hex_rgb("#316AC5")


def test_luna_sheet_rows_are_21_high_with_the_28px_icon_column(menu):
    first = menu.actionGeometry(menu.actions()[0])
    assert (first.height(), menu.contentsMargins().left()) == (21, 0)


def test_luna_sheet_separator_is_grey_over_white_after_the_icon_column(qt_app):
    menu = QMenu()
    menu.setStyleSheet(LUNA_STYLESHEET)
    menu.addAction(QAction("Open", menu))
    menu.addSeparator()
    menu.addAction(QAction("Close", menu))
    menu.show()
    geometry = menu.actionGeometry(menu.actions()[1])
    picture = grab_picture(menu)
    column = [picture.getpixel((geometry.right() - 6, geometry.top() + offset)) for offset in range(geometry.height())]
    menu.close()
    assert hex_rgb("#ACA899") in column and column[column.index(hex_rgb("#ACA899")) + 1] == hex_rgb("#FFFFFF")


def test_luna_sheet_disabled_row_text_is_grey(qt_app):
    menu = QMenu()
    menu.setStyleSheet(LUNA_STYLESHEET)
    action = QAction("Disabled entry", menu)
    action.setEnabled(False)
    menu.addAction(action)
    menu.show()
    picture = grab_picture(menu)
    menu.close()
    assert hex_rgb("#ACA899") in [colour for _count, colour in picture.getcolors(maxcolors=1 << 16)]


def test_luna_sheet_has_no_classic_navy_grey_or_bevel_colours():
    assert not any(colour in LUNA_STYLESHEET.upper() for colour in ("#C0C0C0", "#000080", "#808080"))


def test_classic_sheet_is_untouched_grey_and_navy():
    assert ("#C0C0C0" in CLASSIC_STYLESHEET, "#000080" in CLASSIC_STYLESHEET) == (True, True)


def installed_menus_sheet(tmp_path, look):
    result = subprocess.run(
        [
            str(REPO / "install.sh"),
            "--plain",
            "--yes",
            "--dry-run",
            "--components=look,taskbar,fonts",
            f"--look={look}",
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=120,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path)},
        check=False,
    )
    log = next(tmp_path.glob("chicago95-setup-*.log")).read_text()
    return [line for line in log.splitlines() if line.endswith("share/chicago95/plasmashell-menus.qss")], result


def installed_menus_log(tmp_path, look):
    installed_menus_sheet(tmp_path, look)
    return next(tmp_path.glob("chicago95-setup-*.log")).read_text()


def test_luna_look_installs_the_luna_menu_sheet_over_the_shared_name(tmp_path):
    lines, _ = installed_menus_sheet(tmp_path, "luna")
    assert any(f"{REPO}/data/plasmashell-menus-luna.qss" in line for line in lines)


def test_classic_look_installs_the_classic_menu_sheet(tmp_path):
    lines, _ = installed_menus_sheet(tmp_path, "2000")
    assert any(f"{REPO}/data/plasmashell-menus.qss " in line for line in lines)


def test_luna_sheet_arrows_are_the_installed_black_and_white_svgs_under_the_home_placeholder():
    arrows = re.findall(r"url\((@HOME@/\.local/share/chicago95/images/[\w-]+\.svg)\)", LUNA_STYLESHEET)
    assert [(REPO / "luna/images" / Path(arrow).name).is_file() for arrow in arrows] == [True, True]


def test_luna_sheet_names_a_tahoma_font_list_in_pixels():
    assert 'font: 11px "Tahoma", "Wine Tahoma"' in LUNA_STYLESHEET


def test_luna_look_installs_the_menu_arrows_beside_the_sheet(tmp_path):
    log = installed_menus_log(tmp_path, "luna")
    assert all(f"share/chicago95/images/{name}.svg" in log for name in ("menu-arrow", "menu-arrow-selected"))
