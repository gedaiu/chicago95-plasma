"""Icons the Start menus draw at a fractional screen scale (chicago95ui.crisp_icon) and the icon set they come from
(chicago95ui.menu_icon_theme)."""

import chicago95ui
import pytest
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QIcon, QImage, QPainter


@pytest.fixture
def icon_theme(tmp_path, qt_app):
    """A theme with a transparent 48px "probe" and a 22px-only "tiny", made current for the test."""
    root = tmp_path / "icons/Probe"
    for size, name in ((48, "probe"), (22, "tiny")):
        (root / f"apps/{size}").mkdir(parents=True)
        picture = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
        picture.fill(Qt.transparent)
        QPainter(picture).fillRect(size // 4, size // 4, size // 2, size // 2, Qt.red)
        picture.save(str(root / f"apps/{size}/{name}.png"))
    (root / "index.theme").write_text(
        "[Icon Theme]\nName=Probe\nDirectories=apps/48,apps/22\n\n"
        "[apps/48]\nSize=48\nType=Fixed\n\n[apps/22]\nSize=22\nType=Fixed\n"
    )
    paths, name = QIcon.themeSearchPaths(), QIcon.themeName()
    QIcon.setThemeSearchPaths([str(tmp_path / "icons")])
    QIcon.setThemeName("Probe")
    yield
    QIcon.setThemeSearchPaths(paths)
    QIcon.setThemeName(name)


def painted(icon, scale):
    image = QImage(round(24 * scale), round(24 * scale), QImage.Format_ARGB32_Premultiplied)
    image.setDevicePixelRatio(scale)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    icon.paint(painter, QRect(0, 0, 24, 24))
    painter.end()
    return image


def test_a_theme_icon_at_one_and_a_half_scale_keeps_its_transparent_corners(icon_theme):
    image = painted(chicago95ui.crisp_icon(QIcon.fromTheme("probe")), 1.5)

    assert (image.pixelColor(1, 1).alpha(), image.pixelColor(18, 18).name()) == (0, "#ff0000")


def test_a_theme_icon_pixmap_at_one_and_a_half_scale_keeps_its_transparent_corners(icon_theme):
    pixmap = chicago95ui.crisp_icon(QIcon.fromTheme("probe")).pixmap(QSize(24, 24), 1.5)

    assert (pixmap.size().toTuple(), pixmap.toImage().pixelColor(1, 1).alpha()) == ((36, 36), 0)


def test_an_icon_with_only_a_smaller_picture_fills_its_slot(icon_theme):
    image = painted(chicago95ui.crisp_icon(QIcon.fromTheme("tiny")), 1.5)
    red = [x for x in range(36) if image.pixelColor(x, 18).name() == "#ff0000"]

    assert len(red) >= 17  # the 11 red pixels of the 22px picture, stretched to the 36px slot; unstretched: 11


def test_the_menu_icon_set_is_the_one_under_the_toolbar_theme(tmp_path):
    toolbar = tmp_path / "icons/Chicago95-Toolbar"
    toolbar.mkdir(parents=True)
    (toolbar / "index.theme").write_text("[Icon Theme]\nName=Chicago95 Toolbar\nInherits=Windows-XP,hicolor\n")

    assert (
        chicago95ui.menu_icon_theme("Chicago95-Toolbar", [tmp_path / "icons"]),
        chicago95ui.menu_icon_theme("SE98", [tmp_path / "icons"]),
    ) == ("Windows-XP", "SE98")


@pytest.mark.parametrize(
    "present, picked",
    [
        ((".face", ".face.icon", "accounts"), ".face"),
        ((".face.icon", "accounts"), ".face.icon"),
        (("accounts",), "accounts"),
        ((), None),
    ],
)
def test_the_user_picture_is_the_face_file_else_the_kde_account_picture(tmp_path, present, picked):
    accounts = tmp_path / "AccountsService/icons"
    accounts.mkdir(parents=True)
    places = {".face": tmp_path / ".face", ".face.icon": tmp_path / ".face.icon", "accounts": accounts / "nathan"}
    for name in present:
        places[name].write_bytes(b"picture")

    found = chicago95ui.user_picture_path(tmp_path, "nathan", accounts)

    assert found == (places[picked] if picked else None)
