import sys

from conftest import REPO

sys.path.insert(0, str(REPO / "luna"))
from palette import PALETTE, family  # noqa: E402


def test_face_is_xp_beige():
    assert PALETTE["face"] == "#ECE9D8"


def test_taskbar_has_30_rows_from_highlight_to_dark_bottom():
    taskbar = PALETTE["taskbar"]
    assert (len(taskbar), taskbar[1], taskbar[-1]) == (30, "#3888E9", "#1941A5")


def test_title_active_has_30_rows_from_0058ee_to_0043cf():
    title = PALETTE["title_active"]
    assert (len(title), title[0], title[-1]) == (30, "#0058EE", "#0043CF")


def test_family_luna_is_luna():
    assert family("luna") == "luna"


def test_family_1995_is_flat():
    assert family("1995") == "flat"
