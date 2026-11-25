"""The Control Panel's applet icons on a 1.5x screen: the theme's own picture for the device size (48 pixels for a
32 pixel icon), not the 32 pixel one stretched, which blurred them."""

import pytest
from conftest import REPO, load_script
from icon_geometry import overlap
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


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


def test_checkout_icon_takes_priority_over_an_older_install(tmp_path, monkeypatch):
    panel = load_script("chicago95-control-panel")
    monkeypatch.setattr(panel, "REPO_DIR", tmp_path / "checkout")
    monkeypatch.setattr(panel, "CHICAGO95_DATA", tmp_path / "installed")
    name = "native/win7/clock-language-and-region.png"
    checkout = panel.REPO_DIR / "data/control-panel" / name
    installed = panel.CHICAGO95_DATA / "control-panel" / name
    for asset in (checkout, installed):
        asset.parent.mkdir(parents=True)
        asset.touch()

    assert panel.control_panel_asset(name) == checkout
    checkout.unlink()
    assert panel.control_panel_asset(name) == checkout

    monkeypatch.setattr(panel, "REPO_DIR", tmp_path / "installed-prefix")
    assert panel.control_panel_asset(name) == installed


def test_control_panel_loads_native_bitmap_frames_for_each_look(qt_app):
    panel = load_script("chicago95-control-panel")
    for applets, artwork in (
        (panel.WIN95_APPLETS, panel.WIN95_APPLET_ART),
        (panel.WIN98_APPLETS, panel.WIN98_APPLET_ART),
        (panel.WIN2000_APPLETS, panel.WIN2000_APPLET_ART),
        (panel.XP_APPLETS, panel.XP_APPLET_ART),
    ):
        assert set(artwork) == {applet.name for applet in applets}
        for filename in artwork.values():
            icon = panel.control_panel_bitmap_icon(filename)
            assert QSize(32, 32) in icon.availableSizes(), filename
            assert icon.pixmap(QSize(32, 32), 1.0).hasAlphaChannel(), filename

    for filename, _links in panel.AERO_CATEGORIES.values():
        icon = panel.control_panel_bitmap_icon(filename)
        assert {48, 72} <= {size.width() for size in icon.availableSizes()}, filename

    for filename in panel.XP_CATEGORY_ART.values():
        icon = panel.control_panel_bitmap_icon(filename)
        assert QSize(48, 48) in icon.availableSizes(), filename


@pytest.mark.parametrize(("name", "detail", "colour"), (
    ("power-management", (187, 86), "#ff0000"),
    ("telephony", (145, 85), "#0000ff"),
))
def test_win98_applet_art_has_separate_fills_and_transparent_corners(qt_app, name, detail, colour):
    artwork = REPO / f"data/control-panel/win98-{name}.svg"
    renderer = QSvgRenderer(str(artwork))
    assert renderer.isValid()
    assert not overlap(artwork.read_text())

    image = QImage(320, 320, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    with QPainter(image) as painter:
        renderer.render(painter)

    for x, y in ((0, 0), (319, 0), (0, 319), (319, 319)):
        assert image.pixelColor(x, y).alpha() == 0
    assert image.pixelColor(*detail).name() == colour
