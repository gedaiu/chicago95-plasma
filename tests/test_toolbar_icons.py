import pytest
from conftest import REPO
from PySide6.QtGui import QImage

ICONS = sorted((REPO / "data/toolbar-icons").glob("*/*.png"))
XP_ICONS = sorted((REPO / "data/toolbar-icons/2001").glob("*/*.png"))


def test_toolbar_icons_cover_navigation_and_clipboard_for_both_sets():
    names = {folder: {icon.stem for icon in ICONS if icon.parent.name == folder} for folder in ("1995", "2000")}

    assert (
        names["1995"] >= {"go-up", "edit-cut", "edit-copy", "edit-paste", "edit-delete"},
        names["2000"] >= {"go-previous", "go-next", "go-up", "edit-undo", "folder-new"},
    ) == (True, True)


@pytest.mark.parametrize("icon", ICONS + XP_ICONS, ids=lambda icon: f"{icon.parent.name}/{icon.stem}")
def test_toolbar_icon_keeps_its_native_size_and_transparent_corners(icon):
    image = QImage(str(icon))
    size = int(icon.parent.name) if icon in XP_ICONS else 22

    assert (image.width(), image.height(), image.pixelColor(0, 0).alpha()) == (size, size, 0)
