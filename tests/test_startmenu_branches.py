import json
import os
import signal
import time

import chicago95ui
import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionMenuItem


def desktop_file(directory, name, body):
    path = directory / name
    path.write_text("[Desktop Entry]\n" + body)
    return path


def wait_until(condition, seconds=2.0):
    deadline = time.monotonic() + seconds
    while not condition() and time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)
    return condition()


@pytest.fixture
def retro_look(startmenu, qt_app, tmp_path, monkeypatch):
    settings_file = tmp_path / "chicago95rc"
    monkeypatch.setattr(startmenu, "SETTINGS_FILE", settings_file)

    def apply(style="1995", extra=""):
        settings_file.write_text(f"[StartMenu]\nstyle={style}\n{extra}")
        startmenu.apply_retro_look(qt_app)

    yield apply
    settings_file.unlink(missing_ok=True)
    qt_app.setStyle(chicago95ui.ClassicStyle("Windows"))


def test_banner_stops_spread_two_colours_from_top_to_bottom(startmenu):
    assert startmenu.banner_stops("#000000,#0000FF", 100) == [(0.0, "#000000"), (1.0, "#0000FF")]


def test_banner_stops_single_colour_sits_at_the_top(startmenu):
    assert startmenu.banner_stops("#808080", 100) == [(0.0, "#808080")]


def test_banner_stops_place_at_marks_pixels_above_the_bottom_sorted_and_clamped(startmenu):
    stops = startmenu.banner_stops("#00007B,#00007B@95,#0000FF@45,#00008F@0", 100)

    assert [(round(position, 2), colour) for position, colour in stops] == [
        (0.0, "#00007B"),
        (0.05, "#00007B"),
        (0.55, "#0000FF"),
        (1.0, "#00008F"),
    ]


def test_banner_stops_at_mark_taller_than_the_menu_clamps_to_the_top(startmenu):
    assert startmenu.banner_stops("#111111@500", 100) == [(0.0, "#111111")]


def test_banner_parts_split_words_and_numbers_with_numbers_thin(startmenu):
    assert startmenu.banner_parts("Windows 2000 Professional") == [
        ("Windows ", True),
        ("2000", False),
        (" Professional", True),
    ]


def write_fake_kscreen(directory, monkeypatch, output):
    script = directory / "kscreen-doctor"
    script.write_text(f"#!/bin/sh\nprintf '%s' '{output}'\n")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", str(directory))


def test_detect_scale_reads_scale_from_kscreen_doctor_output(startmenu, tmp_path, monkeypatch):
    write_fake_kscreen(tmp_path, monkeypatch, "Output: 1 eDP-1\n\x1b[1mScale: 1.5\x1b[0m")

    assert startmenu.detect_scale() == "1.5"


def test_detect_scale_is_1_when_output_has_no_scale_line(startmenu, tmp_path, monkeypatch):
    write_fake_kscreen(tmp_path, monkeypatch, "Output: 1 eDP-1")

    assert startmenu.detect_scale() == "1"


def test_detect_scale_is_1_when_kscreen_doctor_is_not_installed(startmenu, tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))

    assert startmenu.detect_scale() == "1"


def test_style_of_falls_back_to_1995_for_unknown_style(startmenu):
    widget = type("Widget", (), {"banner": {"style": "3000"}})()

    assert startmenu.style_of(widget) == startmenu.STYLES["1995"]


@pytest.mark.parametrize(
    "body",
    [
        "Type=Application\nName=Hidden\nExec=x\nNoDisplay=true\n",
        "Type=Application\nName=Hidden\nExec=x\nHidden=true\n",
        "Type=Link\nName=Link\nExec=x\n",
        "Type=Application\nName=No exec\n",
        "Type=Application\nName=Gnome only\nExec=x\nOnlyShowIn=GNOME;\n",
        "Type=Application\nName=Not in KDE\nExec=x\nNotShowIn=KDE;\n",
    ],
)
def test_read_desktop_entry_is_none_for_entries_the_menu_hides(startmenu, tmp_path, body):
    assert startmenu.read_desktop_entry(desktop_file(tmp_path, "hidden.desktop", body)) is None


def test_read_desktop_entry_is_none_without_desktop_entry_section(startmenu, tmp_path):
    path = tmp_path / "plain.desktop"
    path.write_text("[Other]\nName=x\n")

    assert startmenu.read_desktop_entry(path) is None


def test_read_desktop_entry_is_none_for_undecodable_file(startmenu, tmp_path):
    path = tmp_path / "binary.desktop"
    path.write_bytes(b"\xff\xfe\x00[Desktop Entry]\n")

    assert startmenu.read_desktop_entry(path) is None


def test_read_desktop_entry_is_none_for_malformed_file(startmenu, tmp_path):
    path = tmp_path / "broken.desktop"
    path.write_text("no section header\n")

    assert startmenu.read_desktop_entry(path) is None


def test_read_desktop_entry_uses_stem_and_generic_icon_when_name_and_icon_missing(startmenu, tmp_path):
    path = desktop_file(tmp_path, "tool.desktop", "Exec=tool\nCategories=Utility;Clock;;\nOnlyShowIn=KDE;\n")

    assert startmenu.read_desktop_entry(path) == {
        "name": "tool",
        "icon": "application-x-executable",
        "categories": ["Clock", "Utility"],
        "path": str(path),
    }


@pytest.mark.parametrize(
    ("categories", "folder"),
    [(["WebBrowser"], "Internet"), (["Game", "Utility"], "Accessories"), (["Unknown"], "Other"), ([], "Other")],
)
def test_folder_for_picks_first_matching_category_folder(startmenu, categories, folder):
    assert startmenu.folder_for({"categories": categories}) == folder


@pytest.fixture
def application_dirs(startmenu, tmp_path, monkeypatch):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    monkeypatch.setattr(startmenu, "APPLICATION_DIRS", [first, second, tmp_path / "missing"])
    monkeypatch.setattr(startmenu, "CACHE_FILE", tmp_path / "cache" / "menu.json")
    return first, second


def test_collect_applications_scans_dirs_keeps_first_of_duplicate_names_and_skips_hidden(startmenu, application_dirs):
    first, second = application_dirs
    kept = desktop_file(first, "a.desktop", "Name=Kept\nExec=a\n")
    desktop_file(second, "a.desktop", "Name=Shadowed\nExec=a\n")
    other = desktop_file(second, "b.desktop", "Name=Other\nExec=b\n")
    desktop_file(second, "c.desktop", "Name=Gone\nExec=c\nNoDisplay=true\n")

    assert [(app["name"], app["path"]) for app in startmenu.collect_applications()] == [
        ("Kept", str(kept)),
        ("Other", str(other)),
    ]


def test_collect_applications_serves_cache_while_directory_stamps_match(startmenu, application_dirs):
    desktop_file(application_dirs[0], "a.desktop", "Name=Real\nExec=a\n")
    startmenu.collect_applications()
    cache = json.loads(startmenu.CACHE_FILE.read_text())
    cache["apps"] = [{"name": "From cache"}]
    startmenu.CACHE_FILE.write_text(json.dumps(cache))

    assert startmenu.collect_applications() == [{"name": "From cache"}]


def test_collect_applications_rescans_when_cache_is_corrupt(startmenu, application_dirs):
    path = desktop_file(application_dirs[0], "a.desktop", "Name=Real\nExec=a\n")
    startmenu.CACHE_FILE.parent.mkdir(parents=True)
    startmenu.CACHE_FILE.write_text("{not json")

    assert [app["path"] for app in startmenu.collect_applications()] == [str(path)]


def write_recent_documents(home, bookmarks):
    xbel = home / ".local/share/recently-used.xbel"
    xbel.parent.mkdir(parents=True)
    xbel.write_text(
        "<xbel>" + "".join(f'<bookmark href="{href}" modified="{when}"/>' for href, when in bookmarks) + "</xbel>"
    )


def test_recent_documents_newest_first_skipping_missing_files(startmenu, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    older, newer = tmp_path / "older.txt", tmp_path / "new%20er.txt"
    older.write_text("")
    newer.write_text("")
    write_recent_documents(
        tmp_path,
        [(older.as_uri(), "2024-01-01"), (f"file://{tmp_path}/gone.txt", "2025-06-01"), (newer.as_uri(), "2025-01-01")],
    )

    assert startmenu.recent_documents() == [str(newer), str(older)]


def test_recent_documents_stops_at_the_limit(startmenu, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    files = [tmp_path / f"{index}.txt" for index in range(3)]
    for file in files:
        file.write_text("")
    write_recent_documents(tmp_path, [(file.as_uri(), f"2025-01-0{index + 1}") for index, file in enumerate(files)])

    assert startmenu.recent_documents(limit=2) == [str(files[2]), str(files[1])]


def test_recent_documents_is_empty_without_bookmark_file(startmenu, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    assert startmenu.recent_documents() == []


def test_recent_documents_is_empty_for_malformed_bookmark_file(startmenu, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    xbel = tmp_path / ".local/share/recently-used.xbel"
    xbel.parent.mkdir(parents=True)
    xbel.write_text("<xbel><bookmark")

    assert startmenu.recent_documents() == []


def test_launch_starts_the_command_detached(startmenu, tmp_path):
    marker = tmp_path / "launched"

    startmenu.launch(["touch", str(marker)])

    assert wait_until(marker.exists)


def test_theme_icon_names_lists_png_and_svg_stems_of_installed_themes(startmenu, tmp_path, monkeypatch):
    theme = tmp_path / "Chicago95"
    (theme / "apps/16").mkdir(parents=True)
    for name in ("one.png", "two.svg", "three.txt"):
        (theme / "apps/16" / name).write_text("")
    monkeypatch.setattr(startmenu, "ICON_THEME_DIRS", [theme, tmp_path / "absent"])

    assert startmenu.theme_icon_names.__wrapped__() == {"one", "two"}


def test_themed_icon_loads_an_existing_file_path_as_is(startmenu, qt_app, tmp_path):
    picture = tmp_path / "pic.png"
    QPixmap(16, 16).save(str(picture))

    assert startmenu.themed_icon(str(picture)).availableSizes() == [QSize(16, 16)]


def test_themed_icon_falls_back_to_generic_icon_when_no_name_is_in_the_theme(startmenu, qt_app):
    assert startmenu.themed_icon("no-such-icon-anywhere", "nor-this-one").name() == "application-x-executable"


@pytest.mark.parametrize(
    ("item", "style", "icon_name"),
    [("programs", "1995", "applications-all"), ("log_off", "1998", "system-log-out")],
)
def test_root_icon_loads_png_from_the_styles_icon_set(startmenu, qt_app, tmp_path, monkeypatch, item, style, icon_name):
    icon_set = {"1995": "Chicago95", "1998": "SE98"}[style]
    picture_dir = tmp_path / icon_set / "apps/24"
    picture_dir.mkdir(parents=True)
    QPixmap(24, 24).save(str(picture_dir / f"{icon_name}.png"))
    monkeypatch.setattr(startmenu, "ICON_SET_DIRS", [tmp_path])

    assert startmenu.root_icon(item, style).availableSizes() == [QSize(24, 24)]


def test_root_icon_uses_desktop_theme_when_the_icon_set_is_not_installed(startmenu, qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(startmenu, "ICON_SET_DIRS", [tmp_path])

    assert startmenu.root_icon("shut_down", "unknown-style").name() == startmenu.themed_icon("system-shutdown").name()


def test_control_panel_command_prefers_the_installed_chicago95_panel(startmenu):
    assert startmenu.control_panel_command(which=lambda name: f"/opt/{name}") == ["/opt/chicago95-control-panel"]


def test_control_panel_command_falls_back_to_system_settings(startmenu):
    assert startmenu.control_panel_command(which=lambda name: None) == ["systemsettings"]


def test_taskbar_properties_command_opens_the_taskbar_page_when_panel_is_installed(startmenu):
    assert startmenu.taskbar_properties_command(which=lambda name: "/opt/panel") == ["/opt/panel", "--page", "taskbar"]


def test_taskbar_properties_command_is_none_without_the_panel(startmenu):
    assert startmenu.taskbar_properties_command(which=lambda name: None) is None


def settings_entries(startmenu):
    root = startmenu.build_root_menu()
    settings = next(action for action in root.actions() if action.text() == "&Settings").menu()
    return [action.text() for action in settings.actions()]


def test_settings_menu_lists_taskbar_entry_when_control_panel_is_installed(startmenu, qt_app, path_with):
    path_with("chicago95-control-panel")

    assert settings_entries(startmenu) == [
        "Control Panel",
        "Taskbar...",
        "Printers",
        "Display",
    ]


def test_settings_menu_has_no_taskbar_entry_without_control_panel(startmenu, qt_app, path_with):
    path_with()

    assert settings_entries(startmenu) == ["Control Panel", "Printers", "Display"]


def test_add_entry_with_icon_name_tuple_triggers_its_callback(startmenu, qt_app):
    menu = startmenu.RetroMenu("m")
    calls = []

    action = startmenu.add_entry(menu, "Entry", ("no-such-icon", "also-missing"), lambda: calls.append("ran"))
    action.trigger()

    assert (menu.actions(), calls) == ([action], ["ran"])


def test_load_menu_tree_returns_sorted_entries_and_caches_by_directory_stamp(startmenu, qt_app, monkeypatch):
    monkeypatch.setenv("XDG_MENU_PREFIX", "no-such-prefix-")
    startmenu._menu_tree_cache.update(stamp=None, tree=None)

    tree = startmenu.load_menu_tree()
    names = [entry["name"].lower() for entry in tree["entries"]]

    assert (set(tree), names == sorted(names), startmenu.load_menu_tree() is tree) == (
        {"folders", "entries"},
        True,
        True,
    )


def test_fill_folder_adds_submenus_before_entries_and_entries_launch_through_gio(startmenu, qt_app, monkeypatch):
    launched = []
    monkeypatch.setattr(startmenu, "launch", launched.append)
    node = {
        "folders": [
            {"name": "Games", "folders": [], "entries": [{"name": "Chess", "icon": "x", "path": "/c.desktop"}]}
        ],
        "entries": [{"name": "Editor", "icon": "x", "path": "/e.desktop"}],
    }
    menu = startmenu.RetroMenu("Programs")

    startmenu.fill_folder(menu, node)
    menu.actions()[1].trigger()

    assert ([action.text() for action in menu.actions()], launched) == (
        ["Games", "Editor"],
        [["gio", "launch", "/e.desktop"]],
    )


def test_fill_programs_menu_replaces_previous_items(startmenu, qt_app, monkeypatch):
    monkeypatch.setattr(
        startmenu, "load_menu_tree", lambda: {"folders": [], "entries": [{"name": "Only", "icon": "x", "path": "/o"}]}
    )
    menu = startmenu.RetroMenu("Programs")
    startmenu.add_entry(menu, "Stale", "x", lambda: None)

    startmenu.fill_programs_menu(menu)

    assert [action.text() for action in menu.actions()] == ["Only"]


def test_fill_documents_menu_lists_my_documents_separator_then_recent_files(startmenu, qt_app, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    report = tmp_path / "report.txt"
    report.write_text("")
    write_recent_documents(tmp_path, [(report.as_uri(), "2025-01-01")])
    launched = []
    monkeypatch.setattr(startmenu, "launch", launched.append)
    menu = startmenu.RetroMenu("Documents")

    startmenu.fill_documents_menu(menu)
    menu.actions()[2].trigger()

    assert ([action.text() for action in menu.actions()], launched) == (
        ["My Documents", "", "report.txt"],
        [["xdg-open", str(report)]],
    )


def pixel(menu, x, y):
    return menu.grab().toImage().pixelColor(x, y)


@pytest.mark.parametrize(("style", "corner"), [("1995", "#000000"), ("1998", "#000000"), ("2000", "#404040")])
def test_root_menu_paints_the_styles_bottom_right_bevel(startmenu, retro_look, style, corner):
    retro_look(style, "bannerText=Windows 2000 Professional\n")
    root = startmenu.build_root_menu()
    root.adjustSize()
    image = root.grab().toImage()

    assert image.pixelColor(image.width() - 1, image.height() - 1).name().upper() == corner


def test_root_menu_paints_solid_banner_background_at_the_top_of_the_strip(startmenu, retro_look):
    retro_look("1995", "bannerBackground=#FF0000\n")
    root = startmenu.build_root_menu()
    root.adjustSize()

    assert pixel(root, 10, 5).name().upper() == "#FF0000"


def test_root_menu_separator_draws_shadow_line_then_light_line(startmenu, retro_look):
    retro_look("1995")
    root = startmenu.build_root_menu()
    root.adjustSize()
    separator = next(action for action in root.actions() if action.isSeparator())
    top = root.actionGeometry(separator).top() + 2
    x = startmenu.BANNER_WIDTH + 10
    palette = root.palette()

    assert (pixel(root, x, top), pixel(root, x, top + 1)) == (palette.mid().color(), palette.light().color())


def test_root_menu_highlights_the_active_row(startmenu, retro_look):
    retro_look("1998")
    root = startmenu.build_root_menu()
    root.adjustSize()
    row = next(action for action in root.actions() if action.text() == "&Help")
    root.setActiveAction(row)
    geometry = root.actionGeometry(row)

    assert pixel(root, geometry.left() + 30, geometry.top() + 1) == root.palette().highlight().color()


def test_root_menu_draws_submenu_arrow_in_highlighted_text_colour_on_active_submenu_row(startmenu, retro_look):
    retro_look("1995")
    root = startmenu.build_root_menu()
    root.adjustSize()
    row = next(action for action in root.actions() if action.text() == "&Find")
    root.setActiveAction(row)
    geometry = root.actionGeometry(row)
    image = root.grab().toImage()
    arrow_column = image.width() - 13
    arrow = image.pixelColor(arrow_column, geometry.center().y())

    assert arrow == root.palette().highlightedText().color()


def test_submenu_arrow_is_drawn_small_in_the_row(startmenu, retro_look):
    retro_look("1995")
    submenu = startmenu.RetroMenu("Parent")
    submenu.addMenu(startmenu.RetroMenu("Child"))
    submenu.adjustSize()
    geometry = submenu.actionGeometry(submenu.actions()[0])
    image = submenu.grab().toImage()
    arrow_colours = {
        image.pixelColor(x, geometry.center().y()).name()
        for x in range(geometry.right() - startmenu.ARROW - 4, geometry.right() - 1)
    }

    assert submenu.palette().windowText().color().name() in arrow_colours


def test_style_metrics_use_root_and_submenu_measurements(startmenu, retro_look):
    retro_look("1995")
    style = startmenu.RetroMenuStyle("Windows")
    root = startmenu.RetroMenu(banner=True)
    submenu = startmenu.RetroMenu("Sub")
    button_margin = chicago95ui.ClassicStyle("Windows").pixelMetric(QStyle.PM_ButtonMargin)

    assert [
        style.pixelMetric(QStyle.PM_SmallIconSize, None, root),
        style.pixelMetric(QStyle.PM_SmallIconSize, None, submenu),
        style.pixelMetric(QStyle.PM_MenuPanelWidth, None, root),
        style.pixelMetric(QStyle.PM_MenuPanelWidth, None, submenu),
        style.pixelMetric(QStyle.PM_MenuHMargin, None, submenu),
        style.pixelMetric(QStyle.PM_MenuVMargin, None, submenu),
        style.pixelMetric(QStyle.PM_ButtonMargin, None, submenu),
    ] == [24, 16, 0, 2, 0, 0, button_margin]


def test_style_menu_item_size_is_row_height_and_wider_for_root_and_only_wider_for_submenu(startmenu, retro_look):
    retro_look("1995")
    style = startmenu.RetroMenuStyle("Windows")
    root = startmenu.RetroMenu(banner=True)
    submenu = startmenu.RetroMenu("Sub")
    option = QStyleOptionMenuItem()
    size = QSize(100, 20)
    base = chicago95ui.ClassicStyle("Windows").sizeFromContents(QStyle.CT_MenuItem, option, size, root)

    assert [
        style.sizeFromContents(QStyle.CT_MenuItem, option, size, root),
        style.sizeFromContents(QStyle.CT_MenuItem, option, size, submenu),
        style.sizeFromContents(QStyle.CT_MenuItem, option, QSize(100, 2), submenu),
    ] == [
        QSize(base.width() + 20, 32),
        QSize(base.width() + 16, base.height()),
        chicago95ui.ClassicStyle("Windows").sizeFromContents(QStyle.CT_MenuItem, option, QSize(100, 2), submenu),
    ]


def test_underline_shortcuts_hidden_for_2000_and_shown_for_other_styles(startmenu, retro_look, qt_app):
    results = {}
    for style in ("2000", "1995"):
        retro_look(style)
        results[style] = qt_app.style().styleHint(QStyle.SH_UnderlineShortcut)

    assert results == {"2000": 0, "1995": 1}


def test_root_menu_show_rereads_banner_settings_without_sliding(startmenu, retro_look):
    retro_look("1995", "bannerText=First\n")
    root = startmenu.build_root_menu()
    startmenu.SETTINGS_FILE.write_text("[StartMenu]\nbannerText=Second\n")

    root.show()
    root.hide()

    assert (root.banner["bannerText"], root._slide) == ("Second", None)


def test_submenu_show_slides_in_from_the_left_over_slide_duration(startmenu, retro_look):
    retro_look("1995")
    submenu = startmenu.RetroMenu("Sub")
    startmenu.add_entry(submenu, "Entry", "x", lambda: None)

    submenu.show()
    slide = submenu._slide
    submenu.hide()

    assert (slide.duration(), slide.startValue().x() - slide.endValue().x()) == (startmenu.SLIDE_MS, -submenu.width())


def test_click_shield_click_runs_the_callback(startmenu, qt_app):
    clicks = []
    shield = startmenu.ClickShield(lambda: clicks.append("closed"))

    shield.mousePressEvent(None)

    assert clicks == ["closed"]


@pytest.fixture
def controller(startmenu, retro_look, qt_app):
    start_menu = startmenu.StartMenu(qt_app)
    yield start_menu
    start_menu.hide()


def test_toggle_opens_the_menu_then_closes_it(startmenu, controller):
    controller.toggle()
    opened = controller.visible()
    controller.toggle()

    assert (opened, controller.visible()) == (True, False)


def test_show_twice_replaces_the_previous_menu(startmenu, controller):
    controller.show()
    first = controller.menu
    controller.show()

    assert (controller.menu is first, controller.visible()) == (False, True)


def test_visible_is_false_before_any_menu_is_built(startmenu, controller):
    assert controller.visible() is False


def test_hide_without_a_menu_leaves_the_shield_hidden(startmenu, controller):
    controller.hide()

    assert controller.shield.isVisible() is False


def test_show_on_x11_style_platform_covers_the_screen_with_the_click_shield(startmenu, controller, qt_app):
    controller.show()

    assert controller.shield.geometry() == qt_app.primaryScreen().geometry()


def test_show_on_wayland_skips_the_shield_and_closes_when_focus_leaves(startmenu, controller, monkeypatch, qt_app):
    monkeypatch.setenv("QT_QPA_PLATFORM", "wayland")
    controller.show()
    shield_shown = controller.shield.isVisible()
    controller._on_focus_window(None)
    closed = wait_until(lambda: not controller.visible() or qt_app.focusWindow() is not None)

    assert (shield_shown, closed, controller.visible() == (qt_app.focusWindow() is not None)) == (False, True, True)


def test_focus_leaving_with_no_menu_open_does_nothing(startmenu, controller):
    controller._on_focus_window(None)

    assert controller.visible() is False


def test_signal_running_instance_signals_the_process_in_the_pid_file(startmenu, tmp_path, monkeypatch):
    received = []
    previous = signal.signal(signal.SIGUSR1, lambda number, frame: received.append(number))
    monkeypatch.setattr(startmenu, "PID_FILE", tmp_path / "pid")
    startmenu.PID_FILE.write_text(f"{os.getpid()}\n")
    try:
        signalled = startmenu.signal_running_instance()
    finally:
        signal.signal(signal.SIGUSR1, previous)

    assert (signalled, received) == (True, [signal.SIGUSR1])


@pytest.mark.parametrize("content", [None, "not a pid", "99999999"])
def test_signal_running_instance_is_false_for_missing_garbage_or_dead_pid_file(
    startmenu, tmp_path, monkeypatch, content
):
    pid_file = tmp_path / "pid"
    monkeypatch.setattr(startmenu, "PID_FILE", pid_file)
    if content is not None:
        pid_file.write_text(content)

    assert startmenu.signal_running_instance() is False
