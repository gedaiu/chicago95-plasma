import pytest
from conftest import REPO, run_bash_with_steps_result
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


def test_setup_registers_both_native_xp_toolbar_sizes(tmp_path):
    result = run_bash_with_steps_result(
        tmp_path,
        "SETUP_DRY_RUN=0; STATE_DIR=$HOME; MANIFEST=$HOME/manifest; "
        "SETUP_START_MENU_STYLE=luna; install_toolbar_icons Windows-XP",
    )
    assert result.returncode == 0, result.stderr
    theme = tmp_path / ".local/share/icons/Chicago95-Toolbar"
    assert "Directories=actions/16,actions/24" in (theme / "index.theme").read_text()
    for icon in XP_ICONS:
        installed = theme / "actions" / icon.parent.name / icon.name
        assert installed.read_bytes() == icon.read_bytes()
