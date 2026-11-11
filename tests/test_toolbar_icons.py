import pytest
from conftest import REPO
from PySide6.QtGui import QImage

ICONS = sorted((REPO / "data/toolbar-icons").glob("*/*.png"))


def test_toolbar_icons_cover_navigation_and_clipboard_for_both_sets():
    names = {folder: {icon.stem for icon in ICONS if icon.parent.name == folder} for folder in ("1995", "2000")}

    assert (
        names["1995"] >= {"go-up", "edit-cut", "edit-copy", "edit-paste", "edit-delete"},
        names["2000"] >= {"go-previous", "go-next", "go-up", "edit-undo", "folder-new"},
    ) == (True, True)


@pytest.mark.parametrize("icon", ICONS, ids=lambda icon: f"{icon.parent.name}/{icon.stem}")
def test_toolbar_icon_is_22_pixels_with_transparent_corners(icon):
    image = QImage(str(icon))

    assert (image.width(), image.height(), image.pixelColor(0, 0).alpha()) == (22, 22, 0)
