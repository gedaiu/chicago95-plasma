import pytest
from chicago95aeromenu import AeroMenu
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtTest import QTest


@pytest.mark.parametrize("mode", ["programs", "search"])
def test_long_names_fit_the_viewport_and_keep_the_full_launch_target(qt_app, mode):
    names = [{"name": f"Long program {index} " + "Word " * 40, "icon": ""} for index in range(60)]
    launched = []
    menu = AeroMenu(names, launched.append, lambda _: QIcon(), {}, "Demo")
    try:
        menu.show()
        if mode == "search":
            menu.search.setText("Long program")
        else:
            menu.toggle_programs()
        QTest.qWait(30)
        view = menu.list
        assert view.verticalScrollBar().isVisible()
        assert view.textElideMode() == Qt.ElideRight
        assert not view.horizontalScrollBar().isVisible()
        assert view.visualRect(view.model().index(0)).width() == view.viewport().width()
        menu.open_first()
        assert launched == [names[0]]
    finally:
        menu.close()


def test_shutdown_and_options_are_separate_targets(qt_app):
    from PySide6.QtWidgets import QMenu, QPushButton

    launched = []
    commands = {"shut_down": ["shutdown-test"], "restart": ["restart-test"]}
    menu = AeroMenu([], launched.append, lambda _: QIcon(), commands, "Demo")
    try:
        menu.show()
        menu.findChild(QPushButton, "powerArrow").click()
        options = menu.findChild(QMenu)
        assert options.isVisible() and not launched
        options.actions()[0].trigger()
        assert launched == [commands["restart"]]
        menu.show()
        menu.findChild(QPushButton, "shutdown").click()
        assert launched[-1] == commands["shut_down"]
    finally:
        menu.close()


def test_all_programs_is_ready_before_visible_icons_load(qt_app):
    apps = [{"name": f"App {i:05}", "icon": str(i)} for i in range(10000)]
    requests = []
    launched = []

    def icon(name):
        requests.append(name)
        return QIcon()

    menu = AeroMenu(apps, launched.append, icon, {}, "Demo")
    try:
        menu.show()
        QTest.qWait(40)
        requests.clear()
        menu.toggle.click()
        assert menu.model.rowCount() == len(apps)
        assert menu.toggle.text().endswith("Back")
        assert not requests
        # Even the final program is addressable before Qt starts fetching its icon.
        last = menu.model.index(len(apps) - 1)
        menu.list.setCurrentIndex(last)
        menu.list.scrollToBottom()
        menu.list.viewport().repaint()
        menu.open_first()
        assert launched == [apps[-1]]
        QTest.qWait(80)
        assert apps[-1]["icon"] in requests
        assert len(requests) < 50
    finally:
        menu.close()


@pytest.mark.parametrize("motion", ["none", "slide", "fade", "both"])
def test_opening_pixels_follow_menu_effect_and_all_programs_stays_immediate(qt_app, monkeypatch, tmp_path, motion):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "chicago95rc").write_text(f"[Animations]\nANIM_MENUS={motion}\n")
    menu = AeroMenu([{"name": "Editor", "icon": ""}], lambda _: None, lambda _: QIcon(), {}, "Demo")
    try:
        settled = menu.grab().toImage()
        glass = settled.pixelColor(403, 345).alpha()
        assert 0 < glass < 255
        menu.show()
        if motion != "none":
            menu.opening.pause()
            menu.opening.setCurrentTime(30)
        halfway = menu.grab().toImage()
        if motion in ("slide", "both"):
            assert halfway.pixelColor(60, 50).alpha() == 0
        else:
            assert halfway.pixelColor(60, 50).alpha() > 0
        alpha = halfway.pixelColor(403, 345).alpha()
        if motion in ("fade", "both"):
            assert 0 < alpha < glass
        else:
            assert alpha == glass
        menu.toggle.click()
        assert menu.all_programs and menu.model.rowCount() == 1
        assert menu.surface.pos().isNull() and not menu.opacity.isEnabled()
        menu.hide()
        menu.show()
        menu.opening.setCurrentTime(menu.opening.duration())
        assert menu.grab().toImage().pixelColor(60, 50).alpha() == settled.pixelColor(60, 50).alpha()
        assert menu.surface.pos().isNull() and not menu.opacity.isEnabled()
    finally:
        menu.close()


def check_highlight(menu, destination):
    view = menu.list
    selected = view.visualRect(view.currentIndex())
    sample = selected.center()
    sample.setX(selected.right() - 12)
    pixmap = view.viewport().grab()
    point = sample * pixmap.devicePixelRatio()
    assert pixmap.toImage().pixelColor(point).name() == "#def0fc"
    assert menu.grab().save(str(destination))


def test_arrows_select_a_search_result_without_interrupting_typing(qt_app, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "chicago95rc").write_text("[Animations]\nANIM_MENUS=none\n")
    apps = [{"name": f"Photo {name}", "icon": ""} for name in ("A", "B", "C")]
    launched = []
    menu = AeroMenu(apps, launched.append, QIcon.fromTheme, {"control_panel": ["settings"]}, "Demo")
    try:
        menu.show()
        menu.activateWindow()
        QTest.qWait(30)
        QTest.keyClicks(menu.search, "Pho")
        QTest.keyClick(menu.search, Qt.Key_Down)
        assert menu.list.currentIndex().row() == 1 and menu.search.hasFocus()
        QTest.keyClicks(menu.search, "to")
        assert menu.search.text() == "Photo" and menu.list.currentIndex().row() == 0
        for _ in range(3):
            QTest.keyClick(menu.search, Qt.Key_Down)
        assert menu.list.currentIndex().row() == 2
        QTest.keyClick(menu.search, Qt.Key_Up)
        selected = menu.list.currentIndex()
        assert selected.data() == "Photo B"
        check_highlight(menu, tmp_path / "keyboard-search.png")
        QTest.keyClick(menu.search, Qt.Key_Return)
        assert launched == [apps[1]]
    finally:
        menu.close()


def test_folder_keys_expand_select_child_return_to_parent_and_collapse(qt_app, tmp_path):
    apps = [
        {"name": name, "icon": "", "categories": [group]}
        for name, group in (("Calc", "Accessories"), ("Paint", "Accessories"), ("Solitaire", "Games"))
    ]
    launched = []
    menu = AeroMenu(
        apps,
        launched.append,
        QIcon.fromTheme,
        {"control_panel": ["settings"]},
        "Demo",
        folder_for=lambda app: app["categories"][0],
    )
    try:
        menu.show()
        menu.activateWindow()
        menu.toggle.setFocus()
        QTest.keyClick(menu.toggle, Qt.Key_Space)
        QTest.qWait(30)
        view = menu.list
        assert view.hasFocus() and view.currentIndex().data() == "Accessories"
        QTest.keyClick(view, Qt.Key_Right)
        assert view.model().rowCount() == 4 and view.currentIndex().data() == "Accessories"
        QTest.keyClick(view, Qt.Key_Right)
        assert view.currentIndex().data() == "Calc"
        QTest.keyClick(view, Qt.Key_Down)
        assert view.currentIndex().data() == "Paint"
        check_highlight(menu, tmp_path / "keyboard-programs.png")
        QTest.keyClick(view, Qt.Key_Left)
        assert view.currentIndex().data() == "Accessories" and view.model().rowCount() == 4
        QTest.keyClick(view, Qt.Key_Left)
        assert view.model().rowCount() == 2
        QTest.keyClick(view, Qt.Key_Down)
        QTest.keyClick(view, Qt.Key_Right)
        QTest.keyClick(view, Qt.Key_Right)
        QTest.keyClick(view, Qt.Key_Return)
        assert launched == [apps[2]]
    finally:
        menu.close()


def test_default_opening_matches_displayed_sp1_frames(qt_app, monkeypatch, tmp_path):
    from PIL import Image
    from reference import screenshot

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    native = screenshot("win7-sp1-start-opening")
    background = native.crop((0, 0, 10, 10))
    menu = AeroMenu([], lambda _: None, lambda _: QIcon(), {}, "Demo")
    try:
        menu.show()
        for i in range(1, 5):
            # Compare from the first displayed frame, excluding shell launch latency.
            rendered = menu.grab().toImage()
            region = rendered.copy(206, 550 - (728 - menu.height()), 10, 10)
            packed = region.convertToFormat(region.Format.Format_RGBA8888)
            rgba = Image.frombytes("RGBA", (10, 10), packed.bits())
            observed = Image.alpha_composite(background.convert("RGBA"), rgba).convert("RGB")
            assert observed.tobytes() == native.crop((10 * i, 0, 10 * i + 10, 10)).tobytes()
            QTest.qWait(17)
    finally:
        menu.close()
