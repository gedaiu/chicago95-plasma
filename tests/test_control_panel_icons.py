"""The Control Panel's applet icons on a 1.5x screen: the theme's own picture for the device size (48 pixels for a
32 pixel icon), not the 32 pixel one stretched, which blurred them."""

import pytest
from conftest import load_script
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage


@pytest.fixture
def two_size_theme(tmp_path, qt_app):
    root = tmp_path / "icons/Probe"
    for size, colour in ((32, "#0000ff"), (48, "#ff0000")):
        (root / f"apps/{size}").mkdir(parents=True)
        picture = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
        picture.fill(Qt.transparent)
        picture.fill(QColor(colour))
        picture.save(str(root / f"apps/{size}/probe.png"))
    (root / "index.theme").write_text(
        "[Icon Theme]\nName=Probe\nDirectories=apps/32,apps/48\n\n"
        "[apps/32]\nSize=32\nType=Fixed\n\n[apps/48]\nSize=48\nType=Fixed\n"
    )
    paths, name = QIcon.themeSearchPaths(), QIcon.themeName()
    QIcon.setThemeSearchPaths([str(tmp_path / "icons")])
    QIcon.setThemeName("Probe")
    yield
    QIcon.setThemeSearchPaths(paths)
    QIcon.setThemeName(name)


def test_an_applet_icon_at_one_and_a_half_scale_is_the_themes_48_pixel_picture(two_size_theme):
    pixmap = load_script("chicago95-control-panel").themed_icon(["probe"]).pixmap(QSize(32, 32), 1.5)

    assert (pixmap.size().toTuple(), pixmap.toImage().pixelColor(24, 24).name()) == ((48, 48), "#ff0000")
