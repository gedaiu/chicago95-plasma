import subprocess
import sys

import pytest
from conftest import REPO, load_script
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QComboBox

APPLET_NAMES = [
    "Add New Hardware",
    "Booting Screen",
    "Display",
    "Distro Setup",
    "Explorer",
    "Fonts",
    "Modems",
    "Mouse",
    "Office Assistant",
    "Passwords",
    "Sounds",
    "System",
    "Taskbar",
    "Themes",
    "Updates",
]


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


@pytest.fixture
def window(control_panel, qt_app, tmp_path):
    started, ran, messages, answers = [], [], [], {"apply": "cancel"}
    actions = control_panel.Actions(
        start_process=lambda program, arguments: started.append((program, arguments)),
        run_setup=lambda parent, command: ran.append(command),
        show_message=lambda parent, title, text: messages.append((title, text)),
        ask_to_apply=lambda parent: answers["apply"],
    )
    panel = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
    panel.started, panel.ran, panel.messages, panel.answers = started, ran, messages, answers
    return panel


def item_texts(window):
    return [window.icon_view.item(row).text() for row in range(window.icon_view.count())]


def select(window, name):
    window.icon_view.setCurrentItem(window.icon_view.findItems(name, Qt.MatchExactly)[0])


def test_control_panel_lists_its_applets_alphabetically(window):
    assert item_texts(window) == APPLET_NAMES


def test_status_bar_counts_the_objects_when_nothing_is_selected(window):
    assert window.status_message.text() == "15 object(s)"


def test_status_bar_shows_the_selected_applets_description(window):
    select(window, "Sounds")

    assert window.status_message.text() == "Assigns sounds to system events."


def test_menu_bar_is_the_windows_98_explorers(window):
    assert [action.text() for action in window.menu_bar.actions()] == [
        "&File",
        "&Edit",
        "&View",
        "&Go",
        "F&avorites",
        "&Help",
    ]


def test_windows_95_menu_only_shell_opens_original_and_project_applets(window, control_panel, monkeypatch):
    window.close()
    monkeypatch.setattr(control_panel.chicago95ui, "widget_style", lambda: "classic")
    monkeypatch.setattr(window.actions, "program_installed", lambda program: program == "kcmshell6")
    control_panel.write_settings(window.settings_path, {"LOOK": "1995"})
    panel = control_panel.ControlPanel(settings_path=window.settings_path, actions=window.actions)
    try:
        assert [action.text() for action in panel.menu_bar.actions()] == ["&File", "&Edit", "&View", "&Help"]
        assert panel.menuWidget() is panel.menu_bar
        assert len(panel.status_panes) == 1 and panel.status_message.text() == "18 object(s)"
        assert item_texts(panel) == [
            "Accessibility Options", "Add New Hardware", "Add/Remove Programs", "Date/Time",
            "Display", "Fonts", "Internet", "Keyboard", "Modems", "Mouse", "Multimedia", "Network",
            "Passwords", "Power", "Printers", "Regional Settings", "Sounds", "System",
        ]
        panel.menu_bar.actions()[1].menu().actions()[0].trigger()
        assert len(panel.icon_view.selectedItems()) == 18
        panel.icon_view.clearSelection()
        select(panel, "Date/Time")
        panel.icon_view.itemActivated.emit(panel.icon_view.currentItem())
        assert window.started[-1] == ("kcmshell6", ["kcm_clock"])
        select(panel, "Add/Remove Programs")
        panel.icon_view.itemActivated.emit(panel.icon_view.currentItem())
        assert window.messages[-1] == ("Add/Remove Programs", "plasma-discover is unavailable on this desktop.")
        select(panel, "Display")
        panel.icon_view.itemActivated.emit(panel.icon_view.currentItem())
        assert panel.applet_windows["Display"].isVisible()
        project = next(action.menu() for action in panel.menu_bar.actions()[0].menu().actions() if action.menu())
        next(action for action in project.actions() if action.text() == "Themes").trigger()
        assert panel.history.current[-1] == "Themes"
        panel.back_action.trigger()
        assert panel.pages.currentWidget() is panel.icon_view
    finally:
        for sheet in panel.applet_windows.values():
            sheet.close()
        panel.close()


def test_windows_98_web_view_tracks_selection_and_can_be_hidden(window, control_panel, monkeypatch):
    from PySide6.QtWidgets import QLabel

    window.close()
    monkeypatch.setattr(control_panel.chicago95ui, "widget_style", lambda: "classic")
    control_panel.write_settings(window.settings_path, {"LOOK": "1998"})
    panel = control_panel.ControlPanel(settings_path=window.settings_path, actions=window.actions)
    panel.show()
    try:
        assert panel.icon_view.count() == 22
        assert panel.sidebar.isVisible()
        assert list(panel.toolbar_buttons) == [
            "Back", "Forward", "Up", "Cut", "Copy", "Paste", "Undo", "Delete", "Properties", "Views",
        ]
        select(panel, "Display")
        assert panel.sidebar.applet_title.text() == "Display"
        assert panel.sidebar.description.text() == "Changes display settings."
        assert panel.toolbar_buttons["Properties"].isEnabled()
        panel.toolbar_buttons["Properties"].click()
        assert panel.applet_windows["Display"].isVisible()
        panel.web_view_action.trigger()
        assert not panel.sidebar.isVisible() and panel.icon_view.currentItem().text() == "Display"
        panel.web_view_action.trigger()
        assert panel.sidebar.isVisible()
        links = {label.text().split(">")[1].split("<")[0]: label for label in panel.sidebar.findChildren(QLabel)
                 if label.text().startswith("<a ")}
        for caption, suffix in (("Chicago95 Repository", ""), ("Report an issue", "/issues")):
            address = f"https://github.com/gedaiu/chicago95-plasma{suffix}"
            assert address in links[caption].text()
            links[caption].linkActivated.emit(address)
            assert window.started[-1] == ("xdg-open", [address])
        links["Choose a desktop theme"].linkActivated.emit("themes")
        assert panel.history.current[-1] == "Themes"
    finally:
        for sheet in panel.applet_windows.values():
            sheet.close()
        panel.close()


def test_windows_2000_compact_toolbar_and_web_view_search(window, control_panel, monkeypatch):
    window.close()
    monkeypatch.setattr(control_panel.chicago95ui, "widget_style", lambda: "classic")
    control_panel.write_settings(window.settings_path, {"LOOK": "2000"})
    panel = control_panel.ControlPanel(settings_path=window.settings_path, actions=window.actions)
    panel.show()
    try:
        assert panel.icon_view.count() == 23
        assert [action.text() for action in panel.menu_bar.actions()] == [
            "&File", "&Edit", "&View", "F&avorites", "&Tools", "&Help",
        ]
        assert {"Search", "Folders", "History", "Views"} <= set(panel.toolbar_buttons)
        panel.toolbar_buttons["Search"].click()
        panel.sidebar.search.setText("Display")
        assert [item_texts(panel)[i] for i in range(23) if not panel.icon_view.item(i).isHidden()] == ["Display"]
        panel.toolbar_buttons["Search"].click()
        assert sum(not panel.icon_view.item(i).isHidden() for i in range(23)) == 23
        panel.toolbar_buttons["Search"].click()
        panel.sidebar.search.setText("Display")
        panel.web_view_action.trigger()
        assert panel.sidebar.search.isHidden()
        assert sum(not panel.icon_view.item(i).isHidden() for i in range(23)) == 23
        panel.web_view_action.trigger()
        select(panel, "Display")
        assert panel.sidebar.applet_title.text() == "Display"
        assert panel.status_message.text() == "Customizes your desktop display and screen saver"
    finally:
        panel.close()


@pytest.mark.parametrize(("look", "style"), [("2001", "classic"), ("luna", "luna")])
def test_xp_can_switch_between_category_and_classic_views(window, control_panel, monkeypatch, look, style):
    window.close()
    monkeypatch.setattr(control_panel.chicago95ui, "widget_style", lambda: style)
    control_panel.write_settings(window.settings_path, {"LOOK": look})
    panel = control_panel.ControlPanel(settings_path=window.settings_path, actions=window.actions)
    panel.show()
    try:
        assert panel.icon_view.count() == 29
        assert panel.statusBar().isHidden()
        assert list(panel.toolbar_buttons) == ["Back", "Forward", "Up", "Search", "Folders", "Views"]
        assert panel.xp_views.currentWidget() is panel.icon_view
        panel.sidebar.view_requested.emit()
        assert panel.xp_views.currentWidget() is panel.xp_category_view
        from PySide6.QtWidgets import QToolButton

        appearance = next(
            button for button in panel.xp_category_view.findChildren(QToolButton)
            if button.accessibleName() == "Appearance and Themes"
        )
        appearance.click()
        assert panel.xp_views.currentWidget() is panel.icon_view
        assert [item_texts(panel)[i] for i in range(29) if not panel.icon_view.item(i).isHidden()] == [
            "Display", "Folder Options", "Taskbar and\nStart Menu",
        ]
        panel.sidebar.view_requested.emit()
        assert panel.xp_views.currentWidget() is panel.icon_view
        select(panel, "Display")
        panel.icon_view.itemActivated.emit(panel.icon_view.currentItem())
        assert panel.applet_windows["Display"].isVisible()
    finally:
        for sheet in panel.applet_windows.values():
            sheet.close()
        panel.close()


def test_view_menu_offers_large_icons_small_icons_list_and_details(window):
    view_menu = next(action.menu() for action in window.menu_bar.actions() if action.text() == "&View")

    assert [action.text() for action in view_menu.actions() if action.text()] == [
        "Lar&ge Icons",
        "S&mall Icons",
        "&List",
        "&Details",
    ]


def test_standard_buttons_toolbar_has_back_forward_up_and_views_with_navigation_off_at_home(window):
    assert (
        list(window.toolbar_buttons),
        window.back_action.isEnabled(),
        window.forward_action.isEnabled(),
        window.up_action.isEnabled(),
    ) == (["Back", "Forward", "Up", "Views"], False, False, False)


def test_address_bar_shows_the_control_panel(window):
    assert window.address_bar.crumbs() == ["Control Panel"]


def test_large_icons_are_32_pixels_in_a_75_pixel_grid(window):
    assert (
        window.icon_view.iconSize().width(),
        window.icon_view.gridSize().width(),
        window.icon_view.gridSize().height(),
    ) == (32, 75, 75)


def test_choosing_details_adds_each_applets_description_to_its_row_and_large_icons_takes_it_away(window):
    window.set_view("Details")
    details = item_texts(window)[:1]
    window.set_view("Large Icons")

    assert (details, item_texts(window)[:1]) == (
        ["Add New Hardware  -  Opens the Device Manager, which lists the hardware."],
        ["Add New Hardware"],
    )


TASKBAR_PAGE = ("Control Panel", "Taskbar")


def open_applet_through_the_icon_view(window, name):
    window.icon_view.itemActivated.emit(window.icon_view.findItems(name, Qt.MatchExactly)[0])


def test_activating_taskbar_shows_its_page_in_the_same_window(window):
    open_applet_through_the_icon_view(window, "Taskbar")

    assert (window.pages.count(), window.pages.currentWidget().title, window.history.current) == (
        2,
        "Taskbar",
        TASKBAR_PAGE,
    )


def test_taskbar_page_has_the_options_start_menu_and_quick_launch_tabs(window):
    window.open_applet("Taskbar")

    assert window.pages.currentWidget().tab_names() == ["Taskbar Options", "Start Menu", "Quick Launch"]


def test_opening_the_same_applet_twice_reuses_its_page(window):
    window.open_applet("Taskbar")
    window.back_action.trigger()
    window.open_applet("Taskbar")

    assert window.pages.count() == 2


def test_back_returns_to_the_icon_view_and_turns_forward_on(window):
    window.open_applet("Taskbar")
    window.back_action.trigger()

    assert (
        window.pages.currentWidget() is window.icon_view,
        window.back_action.isEnabled(),
        window.forward_action.isEnabled(),
    ) == (True, False, True)


def test_forward_returns_to_the_page_just_left(window):
    window.open_applet("Taskbar")
    window.back_action.trigger()
    window.forward_action.trigger()

    assert (window.pages.currentWidget().title, window.forward_action.isEnabled()) == ("Taskbar", False)


def test_up_is_off_on_the_control_panel_and_on_in_a_page(window):
    before = window.up_action.isEnabled()
    window.open_applet("Taskbar")

    assert (before, window.up_action.isEnabled()) == (False, True)


def test_up_from_a_page_returns_to_the_control_panel(window):
    window.open_applet("Taskbar")
    window.up_action.trigger()

    assert (window.pages.currentWidget() is window.icon_view, window.history.current) == (True, ("Control Panel",))


def test_switching_to_the_quick_launch_tab_updates_the_address_bar(window):
    window.open_applet("Taskbar")
    window.pages.currentWidget().tabs.setCurrentIndex(2)

    assert (window.address_bar.crumbs(), window.history.current) == (
        ["Control Panel", "Taskbar", "Quick Launch"],
        ("Control Panel", "Taskbar", "Quick Launch"),
    )


def test_up_from_the_quick_launch_tab_is_the_taskbar_page_on_its_first_tab(window):
    window.open_applet("Taskbar")
    window.pages.currentWidget().tabs.setCurrentIndex(2)
    window.up_action.trigger()

    assert (window.pages.currentWidget().tabs.currentIndex(), window.history.current) == (0, TASKBAR_PAGE)


def test_back_after_switching_tabs_returns_to_the_tab_before(window):
    window.open_applet("Taskbar")
    window.pages.currentWidget().tabs.setCurrentIndex(1)
    window.back_action.trigger()

    assert (window.pages.currentWidget().tabs.currentIndex(), window.address_bar.crumbs()) == (
        0,
        ["Control Panel", "Taskbar"],
    )


def test_clicking_the_control_panel_crumb_goes_home(window):
    window.open_applet("Taskbar")
    window.pages.currentWidget().tabs.setCurrentIndex(1)
    window.address_bar.crumb_buttons[0].click()

    assert (window.pages.currentWidget() is window.icon_view, window.address_bar.crumbs()) == (True, ["Control Panel"])


def test_clicking_the_applet_crumb_goes_to_its_first_tab(window):
    window.open_applet("Taskbar")
    window.pages.currentWidget().tabs.setCurrentIndex(1)
    window.address_bar.crumb_buttons[1].click()

    assert (window.pages.currentWidget().tabs.currentIndex(), window.history.current) == (0, TASKBAR_PAGE)


def test_address_bar_drop_down_lists_the_control_panel_and_every_applet_page(window):
    assert window.address_bar.known_pages()[:4] == [
        "Control Panel",
        "Control Panel > Booting Screen",
        "Control Panel > Display",
        "Control Panel > Distro Setup",
    ]


def test_back_drop_down_lists_the_pages_before_this_one_nearest_first(window):
    window.open_applet("Taskbar")
    window.open_applet("Sounds")

    assert [action.text() for action in window.back_action.menu().actions()] == [
        "Control Panel > Taskbar",
        "Control Panel",
    ]


def test_choosing_a_page_in_the_back_drop_down_jumps_straight_to_it(window):
    window.open_applet("Taskbar")
    window.open_applet("Sounds")
    window.back_action.menu().actions()[1].trigger()

    assert (window.pages.currentWidget() is window.icon_view, window.forward_action.menu().actions()[0].text()) == (
        True,
        "Control Panel > Taskbar",
    )


def test_activating_system_starts_its_own_tool_and_stays_on_the_control_panel(window):
    open_applet_through_the_icon_view(window, "System")

    assert (
        [program.rsplit("/", 1)[-1] for program, _ in window.started],
        window.pages.currentWidget() is window.icon_view,
    ) == (["chicago95-sysprops"], True)


def run_control_panel(tmp_path, *arguments):
    return subprocess.run(
        [sys.executable, str(REPO / "bin/chicago95-control-panel"), *arguments],
        capture_output=True,
        text=True,
        timeout=60,
        env={
            "PATH": "/usr/bin:/bin",
            "SETUP_OS_RELEASE": "/dev/null",
            "HOME": str(tmp_path),
            "QT_QPA_PLATFORM": "offscreen",
        },
        check=False,
    )


def test_screenshot_option_saves_a_png_of_the_main_window(tmp_path):
    picture = tmp_path / "control-panel.png"

    result = run_control_panel(tmp_path, "--screenshot", str(picture))

    image = QImage(str(picture))
    assert (result.returncode, image.isNull(), image.width() > 300) == (0, False, True)


def test_page_option_with_screenshot_saves_the_page_of_that_applet(tmp_path):
    main_picture, page_picture = tmp_path / "main.png", tmp_path / "taskbar.png"

    run_control_panel(tmp_path, "--screenshot", str(main_picture))
    result = run_control_panel(tmp_path, "--page", "taskbar", "--screenshot", str(page_picture))

    assert (result.returncode, QImage(str(page_picture)) != QImage(str(main_picture))) == (0, True)


def test_page_option_with_an_unknown_applet_is_refused(tmp_path):
    result = run_control_panel(tmp_path, "--page", "nonsense")

    assert (result.returncode, "invalid choice" in result.stderr) == (2, True)


def test_page_slugs_name_every_applet_that_has_a_page(control_panel):
    assert sorted(control_panel.PAGE_SLUGS.values()) == sorted(control_panel.PAGE_TABS)


def test_status_bar_is_empty_on_an_applet_page_and_counts_again_on_the_control_panel(window):
    window.open_applet("Taskbar")
    on_page = window.status_message.text()
    window.back_action.trigger()

    assert (on_page, window.status_message.text()) == ("", "15 object(s)")


def saved_settings_with_a_setup_checkout(window, tmp_path, **settings):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "install.sh").touch()
    window.settings_path.write_text(
        "".join(f"{key}={value}\n" for key, value in {"REPO": str(repo), **settings}.items())
    )
    return repo


def change_the_pointer_size(window, index=2):
    window.open_applet("Mouse")
    from PySide6.QtWidgets import QRadioButton

    pointers = window.pages.currentWidget().tabs.widget(1)  # Buttons, Pointers, Motion
    pointers.findChildren(QRadioButton)[index].setChecked(True)
    return window.pages.currentWidget()


def test_applying_writes_the_changes_over_the_saved_settings_and_runs_setup_for_their_components(
    window, control_panel, tmp_path
):
    repo = saved_settings_with_a_setup_checkout(window, tmp_path, SAVER="maze")
    change_the_pointer_size(window).apply_button.click()

    assert (control_panel.read_settings(window.settings_path), window.ran) == (
        {"REPO": str(repo), "SAVER": "maze", "CURSOR": "48"},
        [control_panel.setup_command(repo, window.settings_path, ["base"])],
    )


def test_applying_without_the_setup_folder_saves_the_settings_and_says_what_to_do(window, control_panel):
    page = change_the_pointer_size(window)
    page.apply_button.click()

    assert (
        control_panel.read_settings(window.settings_path),
        window.ran,
        [title for title, _text in window.messages],
        page.apply_button.isEnabled(),
    ) == ({"CURSOR": "48"}, [], ["Setup files not found"], True)


def test_applying_with_a_setup_folder_that_lost_its_install_script_says_so(window, control_panel, tmp_path):
    window.settings_path.write_text(f"REPO={tmp_path}/gone\n")
    change_the_pointer_size(window).apply_button.click()

    assert (window.ran, len(window.messages)) == ([], 1)


def test_leaving_a_changed_page_with_yes_applies_the_changes_and_goes_back(window, tmp_path):
    saved_settings_with_a_setup_checkout(window, tmp_path)
    change_the_pointer_size(window)
    window.answers["apply"] = "yes"
    window.back_action.trigger()

    assert (len(window.ran), window.pages.currentWidget() is window.icon_view) == (1, True)


def test_leaving_a_changed_page_with_no_discards_the_changes_and_goes_back(window, tmp_path):
    saved_settings_with_a_setup_checkout(window, tmp_path)
    page = change_the_pointer_size(window)
    window.answers["apply"] = "no"
    window.back_action.trigger()

    assert (window.ran, page.changed_values(), window.pages.currentWidget() is window.icon_view) == ([], {}, True)


def test_leaving_a_changed_page_with_cancel_stays_on_it(window, tmp_path):
    saved_settings_with_a_setup_checkout(window, tmp_path)
    page = change_the_pointer_size(window)
    window.answers["apply"] = "cancel"
    window.back_action.trigger()

    assert (window.ran, window.pages.currentWidget() is page, window.history.current) == (
        [],
        True,
        ("Control Panel", "Mouse"),
    )


def test_leaving_by_a_crumb_asks_too(window, tmp_path):
    saved_settings_with_a_setup_checkout(window, tmp_path)
    page = change_the_pointer_size(window)
    window.answers["apply"] = "cancel"
    window.address_bar.crumb_buttons[0].click()

    assert window.pages.currentWidget() is page


def test_leaving_an_unchanged_page_does_not_ask(window):
    window.open_applet("Mouse")
    window.answers["apply"] = "cancel"
    window.back_action.trigger()

    assert window.pages.currentWidget() is window.icon_view


def test_ok_on_a_page_applies_and_returns_to_the_control_panel(window, tmp_path):
    saved_settings_with_a_setup_checkout(window, tmp_path)
    change_the_pointer_size(window).ok_button.click()

    assert (len(window.ran), window.pages.currentWidget() is window.icon_view) == (1, True)


def test_cancel_on_a_page_returns_to_the_control_panel_without_asking(window, tmp_path):
    saved_settings_with_a_setup_checkout(window, tmp_path)
    change_the_pointer_size(window).cancel_button.click()

    assert (window.ran, window.pages.currentWidget() is window.icon_view) == ([], True)


def test_closing_the_window_with_unapplied_changes_asks_and_cancel_keeps_it_open(window, tmp_path):
    saved_settings_with_a_setup_checkout(window, tmp_path)
    change_the_pointer_size(window)
    window.answers["apply"] = "cancel"

    assert window.close() is False


def test_no_control_on_any_page_is_squeezed_below_its_minimum_height(window, control_panel):
    from PySide6.QtWidgets import QAbstractSpinBox, QCheckBox, QLineEdit, QSlider

    window.show()
    squeezed = []
    for applet, tab_names in control_panel.PAGE_TABS.items():
        window.open_applet(applet)
        page = window.applet_sheet(applet)
        for index, tab_name in enumerate(tab_names):
            page.tabs.setCurrentIndex(index)
            page.window().repaint()
            controls = [
                control
                for kind in (QComboBox, QLineEdit, QAbstractSpinBox, QCheckBox, QSlider)
                for control in page.tabs.widget(index).findChildren(kind)
            ]
            squeezed += [
                f"{applet}/{tab_name}: {type(control).__name__}"
                for control in controls
                if control.isVisible() and control.height() < control.minimumSizeHint().height()
            ]

    assert squeezed == []


def test_status_bar_shows_the_object_count_the_place_icon_and_a_size_grip(window, qt_app):
    window.show()
    qt_app.processEvents()

    assert (
        window.status_message.text(),
        window.status_place_icon.pixmap().isNull(),
        window.statusBar().grip.isVisible(),
    ) == ("15 object(s)", False, True)


def test_size_grip_hides_while_the_window_is_maximized_and_returns_when_restored(window, qt_app):
    window.show()
    window.showMaximized()
    qt_app.processEvents()
    maximized = window.statusBar().grip.isVisible()
    window.showNormal()
    qt_app.processEvents()

    assert (maximized, window.statusBar().grip.isVisible()) == (False, True)


def test_address_bar_shows_only_the_current_pages_crumbs_after_moving_between_applets(window, qt_app):
    from PySide6.QtWidgets import QToolButton

    window.show()
    window.open_applet("Taskbar")
    window.open_applet("Mouse")
    visible = [
        button.text()
        for button in window.address_bar.box.findChildren(QToolButton)
        if button.isVisible() and button.text()
    ]

    assert visible == ["Control Panel", "Mouse"]


def test_themes_applies_xp_with_an_independent_control_panel_style(window, control_panel):
    control_panel.write_settings(
        window.settings_path,
        {"REPO": str(REPO), "LOOK": "aero", "SOUND_THEME": "Windows7", "COMPONENTS": "switcher explorer"},
    )
    window.open_applet("Themes")
    page = window.applet_sheet("Themes")
    theme, style = page.findChildren(QComboBox)
    theme.setCurrentIndex(theme.findData("luna"))
    style.setCurrentIndex(style.findData("classic"))
    assert page.apply()
    saved = control_panel.read_settings(window.settings_path)
    assert (
        saved.items()
        >= {
            "LOOK": "luna",
            "CONTROL_PANEL_STYLE": "classic",
            "WIDGET_STYLE": "luna",
            "BOOT_STYLE": "luna",
            "LOGIN_STYLE": "luna",
            "ANIM_MINIMIZE": "zoom",
            "ANIM_MAXIMIZE": "zoom",
            "TASKBAR_STYLE": "luna",
            "START_MENU_STYLE": "luna",
            "SOUND_THEME": "WindowsXP",
            "ICONS": "windowsxp",
            "PANEL": "30",
        }.items()
    )
    assert {"look", "sounds", "startmenu", "taskbar", "sddm", "plymouth", "switcher", "explorer"} <= set(
        window.ran[-1][-1].split("=")[1].split(",")
    )
    assert not page.changed_values()


def test_theme_selector_previews_each_preset_before_apply(window, control_panel, qt_app):
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QPixmap
    from PySide6.QtTest import QTest

    window.show()
    window.open_applet("Themes")
    page = window.applet_sheet("Themes")
    preview = page.findChild(control_panel.DesktopThemePreview)
    selector = preview.selector
    qt_app.processEvents()
    baseline = page.baseline.copy()
    selector.showPopup()
    qt_app.processEvents()
    for label, look in control_panel.START_MENU_STYLES:
        index = selector.findData(look)
        if index:
            QTest.keyClick(selector.view(), Qt.Key_Down)
        qt_app.processEvents()
        assert not selector.itemIcon(index).isNull()
        assert preview.accessibleName() == f"{label} desktop preview"
        screenshot = preview.grab()
        source = QPixmap(str(REPO / f"data/control-panel/theme-previews/{look}.jpg"))
        expected = source.scaled(screenshot.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        crop = QRect(expected.rect())
        crop.moveCenter(screenshot.rect().center())
        assert screenshot.copy(crop).toImage().convertToFormat(
            QImage.Format_RGB32
        ) == expected.toImage().convertToFormat(QImage.Format_RGB32), look
    QTest.keyClick(selector.view(), Qt.Key_Escape)
    qt_app.processEvents()
    assert preview.look == baseline["LOOK"]
    assert page.collect_values() == baseline and not window.ran
    selector.setCurrentIndex(selector.findData("luna"))
    assert preview.look == "luna" and not window.ran
    page.discard_changes()
    assert preview.look == baseline["LOOK"]
