import pytest
from conftest import REPO
from PySide6.QtWidgets import QApplication


@pytest.fixture
def menu_in_style(startmenu, tmp_path, monkeypatch, qt_app):
    settings = tmp_path / "chicago95rc"
    monkeypatch.setattr(startmenu, "SETTINGS_FILE", settings)
    monkeypatch.setattr(startmenu, "QApplication", lambda _argv: QApplication.instance())
    monkeypatch.setattr(startmenu, "apply_retro_look", lambda _app: None)
    monkeypatch.setattr(startmenu, "collect_applications", lambda: [])
    monkeypatch.setattr(startmenu, "recent_documents", lambda: [])
    monkeypatch.setattr(startmenu, "CACHE_FILE", tmp_path / "cache.json")

    def choose(style):
        settings.write_text(f"[StartMenu]\nstyle={style}\n")

    return choose


def test_drawn_root_menu_is_380_by_477_when_style_is_luna(startmenu, menu_in_style):
    menu_in_style("luna")

    _app, menu = startmenu.drawn_root_menu()

    assert (menu.width(), menu.height()) == (380, 477)


def test_root_menu_height_is_477_when_style_is_luna(startmenu, menu_in_style):
    menu_in_style("luna")

    assert startmenu.root_menu_height() == 477


def test_drawn_root_menu_is_the_banner_menu_when_style_is_1995(startmenu, menu_in_style):
    menu_in_style("1995")

    _app, menu = startmenu.drawn_root_menu()

    assert type(menu).__name__ == "RetroMenu"


def test_luna_launch_runs_gio_launch_of_the_desktop_file_when_item_is_an_app(startmenu, monkeypatch):
    launched = []
    monkeypatch.setattr(startmenu, "launch", launched.append)

    startmenu.launch_luna_item({"path": "/usr/share/applications/a.desktop"})
    startmenu.launch_luna_item(["khelpcenter"])

    assert launched == [["gio", "launch", "/usr/share/applications/a.desktop"], ["khelpcenter"]]


def test_luna_commands_cover_every_command_the_luna_menu_names(startmenu):
    import chicago95lunamenu

    assert sorted(startmenu.luna_commands()) == sorted(chicago95lunamenu.COMMAND_NAMES)


def test_the_xp_menus_all_programs_takes_the_classic_menus_folders(startmenu, menu_in_style):
    menu_in_style("luna")

    _app, menu = startmenu.drawn_root_menu()

    assert menu.programs_filler is startmenu.fill_programs_menu


def test_the_xp_menu_shows_the_kde_account_picture_when_there_is_no_face_file(
    startmenu, menu_in_style, monkeypatch, tmp_path
):
    accounts = tmp_path / "accounts"
    accounts.mkdir()
    picture = accounts / "nathan"
    from PySide6.QtGui import QColor, QImage

    image = QImage(64, 64, QImage.Format_RGB32)
    image.fill(QColor("#123456"))
    image.save(str(picture), "PNG")
    monkeypatch.setattr(startmenu.chicago95ui, "ACCOUNTS_ICONS", accounts)
    monkeypatch.setattr(startmenu.getpass, "getuser", lambda: "nathan")
    monkeypatch.setattr(startmenu.Path, "home", lambda: tmp_path)
    menu_in_style("luna")

    _app, menu = startmenu.drawn_root_menu()

    assert menu.user_picture.toImage().pixelColor(10, 10).name() == "#123456"


def test_start_menu_icons_keep_their_transparent_corners_at_one_and_a_half_scale(startmenu, tmp_path, qt_app):
    from PySide6.QtCore import QSize, Qt
    from PySide6.QtGui import QIcon, QImage

    folder = tmp_path / "icons/Probe/apps/48"
    folder.mkdir(parents=True)
    picture = QImage(48, 48, QImage.Format_ARGB32_Premultiplied)
    picture.fill(Qt.transparent)
    picture.save(str(folder / "probe.png"))
    (tmp_path / "icons/Probe/index.theme").write_text(
        "[Icon Theme]\nName=Probe\nDirectories=apps/48\n\n[apps/48]\nSize=48\nType=Fixed\n"
    )
    paths, name = QIcon.themeSearchPaths(), QIcon.themeName()
    QIcon.setThemeSearchPaths([str(tmp_path / "icons")])
    QIcon.setThemeName("Probe")
    corner = startmenu.themed_icon("probe").pixmap(QSize(24, 24), 1.5).toImage().pixelColor(1, 1).alpha()
    QIcon.setThemeSearchPaths(paths)
    QIcon.setThemeName(name)

    assert corner == 0


def test_the_start_menu_takes_its_icons_from_the_set_under_the_toolbar_theme(startmenu, monkeypatch, qt_app):
    from PySide6.QtGui import QIcon

    monkeypatch.setattr(startmenu.chicago95ui, "icon_theme", lambda: "Chicago95-Toolbar")
    monkeypatch.setattr(startmenu.chicago95ui, "menu_icon_theme", lambda theme, roots: f"under {theme}")
    monkeypatch.setattr(startmenu, "is_luna_menu", lambda: False)
    name = QIcon.themeName()
    startmenu.apply_retro_look(qt_app)
    chosen = QIcon.themeName()
    QIcon.setThemeName(name)

    assert chosen == "under Chicago95-Toolbar"
