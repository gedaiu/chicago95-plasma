"""Exercise Aero shell entry points without powering off or changing the active login session."""

import json
import subprocess
import sys

import pytest
from chicago95aeromenu import AeroMenu
from conftest import REPO, load_script, run_bash_with_steps
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QTabWidget
from reference import qimage_to_pil, screenshot


def test_start_folder_launch_updates_frequency_and_search_opens_file(qt_app, tmp_path):
    usage = tmp_path / "usage.ini"
    apps = [
        {"name": name, "path": name + ".desktop", "categories": ["Graphics"], "icon": ""}
        for name in ("A viewer", "Z editor")
    ]
    launched = []
    document = tmp_path / "Sunset photo.png"
    document.touch()

    def launcher():
        return AeroMenu(
            apps,
            launched.append,
            lambda _: QIcon(),
            {},
            "Tester",
            usage_path=usage,
            folder_for=lambda _: "Graphics",
            recent_files=[document],
        )

    menu = launcher()
    menu.show()
    menu.toggle_programs()
    menu.open_first()
    assert menu.isVisible() and menu.model.rowCount() == 3
    menu.open_item(menu.model.index(2))
    assert launched == [apps[1]]
    menu = launcher()
    menu.show()
    assert menu.model.entries[0] == apps[1]
    menu.search.setText("Sunset")
    menu.open_first()
    assert launched[-1] == ["xdg-open", str(document)]


def test_indexed_file_appears_asynchronously(qt_app, tmp_path):
    document = tmp_path / "project brief.txt"
    document.touch()
    backend = tmp_path / "baloosearch6"
    backend.write_text('#!/bin/sh\nprintf "%s\\n" "$(dirname "$0")/project brief.txt"\n')
    backend.chmod(0o755)
    launched = []
    menu = AeroMenu([], launched.append, lambda _: QIcon(), {}, "Demo", search_tool=str(backend))
    menu.show()
    menu.search.setText("brief")
    for _ in range(50):
        QTest.qWait(20)
        if menu.model.entries:
            break
    menu.open_first()
    assert launched == [["xdg-open", str(document)]]


def test_calendar_renders_a_month_and_an_analog_clock(qt_app, exact_original):
    view = QQuickView()
    view.setSource(
        QUrl.fromLocalFile(str(REPO / "aero/plasmoids/org.chicago95.clock/contents/ui/aero/CalendarFlyout.qml"))
    )
    assert not view.errors()
    root = view.rootObject()
    native = screenshot("win7-sp1-aero-calendar")
    assert (root.implicitWidth(), root.implicitHeight()) == native.size
    view.resize(*native.size)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.show()
    QTest.qWait(80)
    im = qimage_to_pil(view.grabWindow())
    # Calendar numbers occupy the left part and the clock rim and hands the right.
    for box in ((8, 72, 220, 180), (240, 65, 329, 176)):
        assert sum(n for n, rgb in im.crop(box).getcolors(100000) if max(rgb[:3]) < 165) > 50

    # The clock silhouette and the settings footer are independent of the calendar date.
    def clock_edges(picture):
        xs = [x for x in range(186, 334) if min(picture.getpixel((x, 106))[:3]) < 240]
        return min(xs), max(xs)

    assert clock_edges(im) == pytest.approx(clock_edges(native), abs=2)
    assert im.getpixel((10, 230))[:3] == native.getpixel((10, 230))[:3]
    assert root.property("month").isValid()
    view.close()
    # A fixed piece of the outer rim excludes the moving clock hands.
    rim = (225, 44, 281, 54)
    exact_original(native.crop(rim), im.crop(rim))


def test_aero_uses_platform_controls_and_logoff_art(qt_app, monkeypatch):
    panel = load_script("chicago95-control-panel")
    monkeypatch.setattr(panel.chicago95ui, "widget_style", lambda: "aero")
    chrome = panel.window_chrome()
    assert chrome.tab_control is QTabWidget and chrome.menu_style() is QApplication.style()
    screen = load_script("chicago95-shutdown").aero_logoff_screen()
    try:
        assert screen.rootObject().property("statusText") == "Logging off..."
        assert screen.rootObject().property("animated")
    finally:
        screen.close()


def test_start_power_menu_dispatches_only_offered_actions(qt_app):
    commands = {key: ["test", key] for key in ("switch_user", "log_off", "lock", "restart", "sleep")}
    launches = []
    menu = AeroMenu([], launches.append, lambda _: QIcon(), commands, "Demo")
    actions = [a for a in menu.findChild(QMenu).actions() if not a.isSeparator()]
    assert [a.text() for a in actions] == ["Switch user", "Log off", "Lock", "Restart", "Sleep"]
    for action in actions:
        action.trigger()
    assert launches == list(commands.values())


def test_desktop_defaults_and_independent_login_selection(tmp_path):
    assert run_bash_with_steps(
        tmp_path,
        "apply_look aero; desktop_icons_chosen; background_color; echo; "
        "SETUP_LOGIN_STYLE=luna; lockscreen_style; echo; SETUP_START_MENU_STYLE=1995; "
        "SETUP_LOGIN_STYLE=aero; lockscreen_style",
    ) == ["recycle", "#1D5C9C", "luna", "aero"]


def test_jump_list_uses_desktop_actions_and_only_that_apps_documents(tmp_path, monkeypatch):
    desktop = tmp_path / "viewer.desktop"
    desktop.write_text(
        "[Desktop Entry]\nType=Application\nName=Viewer\nExec=/bin/true\nActions=New;\n"
        "[Desktop Action New]\nName=New window\nExec=/bin/true\n"
    )
    image = tmp_path / "A photo.png"
    image.touch()
    (tmp_path / "recently-used.xbel").write_text(
        f'<xbel><bookmark href="{image.as_uri()}"><info><application name="Viewer"/></info></bookmark></xbel>'
    )
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    helper = REPO / "plasmoids/org.chicago95.tasks/contents/ui/jumpList.py"
    output = subprocess.check_output([sys.executable, str(helper), desktop.as_uri()], text=True)
    assert json.loads(output) == [
        {"label": image.name, "uri": image.as_uri()},
        {"label": "New window", "action": "New"},
    ]


def test_offline_thunar_profile_keeps_other_settings_on_reinstall(tmp_path):
    from xml.etree import ElementTree

    profile = tmp_path / "thunar.xml"
    profile.write_text('<channel><property name="last-view" type="string" value="ThunarIconView"/></channel>')
    for _ in range(2):
        subprocess.run([sys.executable, REPO / "setup/thunar-navigation.py", profile], check=True)
    properties = ElementTree.parse(profile).getroot().findall("property")
    assert len(properties) == 4
    assert {item.get("name"): item.get("value") for item in properties} == {
        "last-view": "ThunarIconView",
        "last-location-bar": "ThunarLocationButtons",
        "last-menubar-visible": "false",
        "last-toolbar-items": "back:1,forward:1,location-bar:1,search:1,menu:1",
    }


def test_jump_list_merges_kde_history_using_the_apps_own_last_open_time(tmp_path, monkeypatch):
    import os
    import time
    from xml.etree import ElementTree as ET

    helper = REPO / "plasmoids/org.chicago95.tasks/contents/ui/jumpList.py"
    launcher = tmp_path / "viewer.desktop"
    recorder = tmp_path / "record"
    receipt = tmp_path / "opened"
    recorder.write_text(f"#!/bin/sh\nprintf '%s' \"$1\" > '{receipt}'\n")
    recorder.chmod(0o755)
    launcher.write_text(f"[Desktop Entry]\nType=Application\nName=Viewer\nExec={recorder} %f\n")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    kde = tmp_path / "RecentDocuments"
    kde.mkdir()
    history = ET.Element("xbel")
    for name, owner, stamp in (("First", "Viewer", 3), ("It's second", "viewer.desktop", 2), ("Other", "Else", 4)):
        document = tmp_path / name
        document.touch()
        link = kde / (name + ".desktop")
        link.write_text(f"[Desktop Entry]\nType=Link\nURL[$e]={document.as_uri()}\nX-KDE-LastOpenedWith={owner}\n")
        os.utime(link, (stamp, stamp))
    for name in ("Old", "First"):
        document = tmp_path / name
        document.touch()
        node = ET.SubElement(history, "bookmark", href=document.as_uri(), modified="2026-04-10T12:00:00Z")
        ET.SubElement(node, "application", name="Viewer", modified="1970-01-01T00:00:01Z")
        ET.SubElement(node, "application", name="Else", modified="2026-04-10T12:00:00Z")
    foreign = (tmp_path / "Other").as_uri().replace("file:///", "file://elsewhere/")
    ET.SubElement(ET.SubElement(history, "bookmark", href=foreign), "application", name="Viewer")
    ET.ElementTree(history).write(tmp_path / "recently-used.xbel")
    command = [sys.executable, str(helper), launcher.as_uri()]
    rows = json.loads(subprocess.check_output(command, text=True))
    assert [row["label"] for row in rows] == ["First", "It's second", "Old"]
    subprocess.run([*command, "uri", rows[1]["uri"]], check=True)
    for _ in range(100):
        if receipt.exists() and receipt.read_text() == str(tmp_path / "It's second"):
            break
        time.sleep(0.02)
    assert receipt.read_text() == str(tmp_path / "It's second")


def test_start_search_combines_kde_and_older_xbel_entries_and_opens_selected_row(qt_app, tmp_path, monkeypatch):
    from xml.etree import ElementTree

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    kde = tmp_path / "RecentDocuments"
    kde.mkdir()
    history = ElementTree.Element("xbel")
    for index in range(15):
        newer = tmp_path / f"Current {index}"
        newer.touch()
        ElementTree.SubElement(history, "bookmark", href=newer.as_uri(), modified="2025-01-01")
    old = tmp_path / "Project's older notes.txt"
    old.touch()
    ElementTree.SubElement(history, "bookmark", href=old.as_uri(), modified="2023-01-01")
    foreign = tmp_path / "Project remote"
    foreign.touch()
    ElementTree.SubElement(history, "bookmark", href=foreign.as_uri().replace("file:///", "file://another-machine/"))
    ElementTree.ElementTree(history).write(tmp_path / "recently-used.xbel")
    report = tmp_path / "Project 100% & final.txt"
    report.touch()
    (kde / "report.desktop").write_text(f"[Desktop Entry]\nType=Link\nURL[$e]={report.as_uri()}\n")
    # The index knows the KDE file too. Both providers must produce just one row for it.
    backend = tmp_path / "baloosearch6"
    backend.write_text('#!/bin/sh\nprintf "%s\\n" "$(dirname "$0")/Project 100% & final.txt"\n')
    backend.chmod(0o755)
    started = []
    launcher = load_script("chicago95-startmenu")
    monkeypatch.setattr(launcher, "banner_settings", lambda: {"style": "aero"})
    monkeypatch.setattr(launcher, "collect_applications", lambda: [])
    monkeypatch.setattr(launcher.getpass, "getuser", lambda: "Demo")
    monkeypatch.setattr(launcher.chicago95ui, "user_picture_path", lambda *_: None)
    monkeypatch.setattr(launcher, "launch", started.append)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin")
    menu = launcher.build_menu()
    try:
        menu.show()
        menu.search.setText("Current")
        menu.find_files()
        menu.search.setText("PROJECT")
        for _ in range(100):
            QTest.qWait(20)
            if not menu.search_delay.isActive() and not menu.search_processes:
                break
        paths = [entry["file"] for entry in menu.model.entries]
        assert sorted(paths) == sorted([str(report), str(old)])
        first = menu.model.index(paths.index(str(old)))
        menu.list.setCurrentIndex(first)
        assert menu.list.visualRect(first).intersects(menu.list.viewport().rect())
        assert first.data(Qt.ToolTipRole) == str(old)
        assert menu.grab().save(str(tmp_path / "recent-search.png"))
        QTest.keyClick(menu.list, Qt.Key_Return)
        assert started == [["xdg-open", str(old)]]
    finally:
        menu.close()
