import os
import runpy
import sys
import tempfile
import time

import chicago95ui
import pytest
from conftest import REPO, load_script
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QColor, QMouseEvent, QPixmap
from PySide6.QtNetwork import QLocalServer
from PySide6.QtWidgets import QApplication, QDialog, QMenu, QWidget

DIALOG_DEADLINE_SECONDS = 1.5
KCFG = "http://www.kde.org/standards/kcfg/1.0"


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


@pytest.fixture
def window(control_panel, qt_app, tmp_path):
    messages, ran = [], []
    actions = control_panel.Actions(
        start_process=lambda program, arguments: None,
        run_setup=lambda parent, command: ran.append(command),
        show_message=lambda parent, title, text: messages.append((title, text)),
        ask_to_apply=lambda parent: "cancel",
    )
    panel = control_panel.ControlPanel(settings_path=tmp_path / "setup.conf", actions=actions)
    panel.ran, panel.messages = ran, messages
    return panel


@pytest.fixture
def home_in_tmp(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def closing_dialogs(qt_app):
    """Closes the modal dialog (via `act`) or popup that opens; past the deadline, every top-level."""
    timers = []

    def arm(act=lambda dialog: dialog.reject()):
        started = time.monotonic()
        timer = QTimer()
        timer.setInterval(10)

        def tick():
            target = QApplication.activeModalWidget() or QApplication.activePopupWidget()
            if target is not None:
                act(target) if isinstance(target, QDialog) else target.close()
            elif time.monotonic() - started > DIALOG_DEADLINE_SECONDS:
                for widget in QApplication.topLevelWidgets():
                    widget.close()

        timer.timeout.connect(tick)
        timer.start()
        timers.append(timer)

    yield arm
    for timer in timers:
        timer.stop()


def mouse_event(point, kind=QEvent.MouseButtonPress):
    position = QPointF(point)
    return QMouseEvent(kind, position, position, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)


def write_launcher_defaults(path, entry_name, default_text):
    path.write_text(
        f'<kcfg xmlns="{KCFG}"><group name="General"><entry name="{entry_name}" type="StringList">'
        f"<default>{default_text}</default></entry></group></kcfg>"
    )


def test_tab_rows_wrap_and_stretch_rows_to_the_available_width(control_panel):
    assert control_panel.tab_rows([100, 100, 100], 250) == [[(0, 125), (1, 125)], [(2, 250)]]


def test_stretch_row_gives_the_remainder_to_the_first_tabs(control_panel):
    assert control_panel.stretch_row([(0, 10), (1, 10), (2, 10)], 34) == [(0, 12), (1, 11), (2, 11)]


def test_default_launchers_come_from_the_first_file_that_has_a_launchers_entry(control_panel, tmp_path):
    first, second, absent = tmp_path / "first.xml", tmp_path / "second.xml", tmp_path / "absent.xml"
    write_launcher_defaults(first, "other", "ignored")
    write_launcher_defaults(second, "launchers", "a.desktop,,b.desktop")

    assert control_panel.default_launchers([absent, first, second]) == ["a.desktop", "b.desktop"]


def test_default_launchers_are_empty_when_no_settings_file_exists(control_panel, tmp_path):
    assert control_panel.default_launchers([tmp_path / "nowhere.xml"]) == []


def test_default_launchers_are_empty_when_the_file_has_no_launchers_entry(control_panel, tmp_path):
    only = tmp_path / "only.xml"
    write_launcher_defaults(only, "other", "ignored")

    assert control_panel.default_launchers([only]) == []


def test_installed_screensavers_are_empty_when_the_tool_cannot_run(control_panel, monkeypatch, tmp_path):
    monkeypatch.setattr(control_panel, "tool_path", lambda name: str(tmp_path / name))

    assert control_panel.installed_screensavers() == []


def test_lock_timeout_is_5_minutes_when_kreadconfig_is_not_installed(control_panel, monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))

    assert control_panel.lock_timeout_minutes() == 5


def test_start_detached_of_a_missing_program_returns_without_error(control_panel, tmp_path):
    assert control_panel.start_detached(str(tmp_path / "no-such-program"), []) is None


def test_details_of_a_failed_apply_closes_the_dialog(control_panel, qt_app):
    progress = control_panel.ApplyProgress(None, ["setup"])
    progress.fail("it broke")
    progress.details_button.click()

    assert (progress.result(), progress.log.toPlainText()) == (QDialog.Rejected, "it broke")


def test_run_setup_in_background_returns_when_the_command_succeeds(control_panel, closing_dialogs):
    closing_dialogs()
    control_panel.run_setup_in_background(None, [sys.executable, "-c", "pass"])


def test_choose_file_dialog_returns_nothing_when_cancelled(control_panel, closing_dialogs, home_in_tmp):
    closing_dialogs()

    assert control_panel.choose_file_dialog(None, "Pick", control_panel.PICTURE_FILTER) == ""


def test_choose_color_dialog_returns_the_accepted_colour_in_capitals(control_panel, closing_dialogs):
    closing_dialogs(lambda dialog: dialog.accept())

    assert control_panel.choose_color_dialog(None, "#112233,#445566") == "#112233"


def test_choose_color_dialog_starts_from_teal_when_the_current_colour_is_not_valid(control_panel, closing_dialogs):
    closing_dialogs(lambda dialog: dialog.accept())

    assert control_panel.choose_color_dialog(None, "not-a-colour") == "#008080"


def test_choose_color_dialog_returns_nothing_when_cancelled(control_panel, closing_dialogs):
    closing_dialogs()

    assert control_panel.choose_color_dialog(None, "#112233") == ""


def test_show_message_returns_once_the_box_is_closed(control_panel, closing_dialogs):
    closing_dialogs()

    assert control_panel.show_message(None, "Title", "Text") is None


def test_ask_to_apply_changes_returns_the_button_pressed(control_panel, closing_dialogs):
    closing_dialogs(lambda dialog: dialog.buttons["No"].click())

    assert control_panel.ask_to_apply_changes(None) == "no"


@pytest.fixture
def toolbar_button(control_panel, qt_app):
    action = QAction("Back")
    menu = QMenu()
    menu.addAction("Entry")
    action.setMenu(menu)
    button = control_panel.ToolbarButton(action, has_menu=True)
    button.resize(button.sizeHint())
    button.keep_alive = (action, menu)
    return button


def test_toolbar_button_without_icon_paints_its_label_in_greys(toolbar_button):
    assert toolbar_button.grab().toImage().size() == toolbar_button.size()


def test_toolbar_button_pressed_on_its_arrow_opens_the_menu(toolbar_button, closing_dialogs):
    closing_dialogs()
    toolbar_button.mousePressEvent(mouse_event(toolbar_button.arrow_rect().center()))

    assert QApplication.activePopupWidget() is None


def test_toolbar_button_pressed_on_its_face_does_not_open_the_menu(toolbar_button):
    toolbar_button.mousePressEvent(mouse_event(QPoint(3, 3)))

    assert (toolbar_button.isDown(), QApplication.activePopupWidget()) == (True, None)


def test_disabled_toolbar_button_with_a_menu_opens_it_from_anywhere(toolbar_button, closing_dialogs):
    toolbar_button.defaultAction().setEnabled(False)
    closing_dialogs()
    toolbar_button.mousePressEvent(mouse_event(QPoint(3, 3)))

    assert toolbar_button.isDown() is False


def test_logo_box_without_a_logo_paints_only_its_black_box(control_panel, qt_app):
    box = control_panel.LogoBox()
    box.logo = QPixmap()
    box.resize(box.width(), 30)

    assert box.grab().toImage().pixelColor(5, 5) == QColor("#000000")


def test_arrow_button_with_a_menu_opens_it_on_press(control_panel, qt_app, closing_dialogs):
    parent = QWidget()
    button = control_panel.ArrowButton()
    button.setParent(parent)
    menu = QMenu()
    menu.addAction("Entry")
    button.setMenu(menu)
    closing_dialogs()
    button.mousePressEvent(mouse_event(QPoint(2, 2)))

    assert (button.isDown(), QApplication.activePopupWidget()) == (False, None)


def test_loading_preview_without_a_loadable_screen_leaves_its_stage_alone(control_panel, qt_app, monkeypatch, tmp_path):
    splash = tmp_path / "splash/chicago95.splashscreen/contents/splash"
    splash.mkdir(parents=True)
    (splash / "Splash.qml").write_text("this is not qml {")
    monkeypatch.setattr(control_panel, "REPO_DIR", tmp_path)
    preview = control_panel.LoadingPreview()

    preview.refresh({})

    assert preview.rootObject() is None


def test_launcher_list_skips_empty_entries_when_set(control_panel, qt_app):
    launchers = control_panel.LauncherList(lambda: "")
    launchers.set_value("a.desktop,,b.desktop,")

    assert launchers.value() == "a.desktop,b.desktop"


def test_title_bar_preview_paints_a_gradient_for_each_bar(control_panel, qt_app):
    preview = control_panel.TitleBarPreview("#000080,#1084D0", "#808080")
    preview.resize(200, 46)
    gradient_image = preview.grab().toImage()

    assert (gradient_image.pixelColor(100, 5) != gradient_image.pixelColor(100, 28), gradient_image.width()) == (
        True,
        200,
    )


def test_tab_rows_click_on_another_tab_chooses_it(control_panel, qt_app):
    rows = control_panel.TabRows()
    rows.resize(300, 40)
    for name in ("One", "Two", "Three"):
        rows.add_tab(name)
    chosen = []
    rows.chosen.connect(chosen.append)
    other = next(index for index in rows.tab_rects() if index != rows.selected)
    rows.mousePressEvent(mouse_event(rows.tab_rects()[other].center()))

    assert chosen == [other]


def test_tab_rows_click_on_the_selected_tab_or_off_all_tabs_chooses_nothing(control_panel, qt_app):
    rows = control_panel.TabRows()
    rows.resize(300, 40)
    rows.add_tab("One")
    rows.add_tab("Two")
    chosen = []
    rows.chosen.connect(chosen.append)
    rows.mousePressEvent(mouse_event(rows.tab_rects()[rows.selected].center()))
    rows.mousePressEvent(mouse_event(QPoint(290, 2)))

    assert chosen == []


def test_window_asked_for_an_unknown_page_comes_up_on_the_current_one(window):
    window.show_again("no-such-page")
    window.hide()

    assert window.pages.currentWidget() is window.icon_view


def change_any_field_of_the_page(window, control_panel):
    from PySide6.QtWidgets import QCheckBox

    for applet in control_panel.PAGE_TABS:
        window.open_applet(applet)
        page = window.pages.currentWidget()
        for box in page.findChildren(QCheckBox):
            box.toggle()
            if page.changed_values():
                return page
    raise AssertionError("no page has a check box to change")


def test_closing_a_changed_page_with_cancel_ignores_the_close_event(window, control_panel):
    change_any_field_of_the_page(window, control_panel)
    event = QCloseEvent()
    window.closeEvent(event)

    assert event.isAccepted() is False


def test_applying_changes_that_need_no_component_runs_no_setup(window, tmp_path):
    repo = tmp_path / "checkout"
    repo.mkdir()
    (repo / "install.sh").write_text("")

    assert (window.apply_changes({"REPO": str(repo), "NOT_A_SETUP_KEY": "1"}), window.ran) == (True, [])


@pytest.fixture
def main_environment(control_panel, qt_app, monkeypatch, home_in_tmp):
    runtime_dir = tempfile.mkdtemp(dir="/tmp")
    monkeypatch.setenv("XDG_RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(chicago95ui, "make_app", lambda name: QApplication.instance())
    return runtime_dir


def test_main_saves_a_screenshot_of_the_window_and_exits(control_panel, main_environment, monkeypatch, tmp_path):
    picture = tmp_path / "shot.png"
    monkeypatch.setattr(sys, "argv", ["control-panel", "--screenshot", str(picture)])

    assert (control_panel.main(), picture.exists()) == (0, True)


def test_main_hands_its_page_to_a_running_instance_and_exits(control_panel, main_environment, monkeypatch):
    server = QLocalServer()
    server.listen(chicago95ui.instance_socket(control_panel.INSTANCE_NAME))
    monkeypatch.setattr(sys, "argv", ["control-panel", "--page", "mouse"])

    assert control_panel.main() == 0
    server.close()


def test_main_opens_the_requested_page_and_runs_until_the_app_quits(control_panel, main_environment, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["control-panel", "--page", "mouse"])
    QTimer.singleShot(150, QApplication.instance().quit)

    assert control_panel.main() == 0


def test_running_the_script_exits_with_the_status_of_main(main_environment, monkeypatch, tmp_path):
    picture = tmp_path / "script-shot.png"
    monkeypatch.setattr(sys, "argv", ["control-panel", "--screenshot", str(picture)])

    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(str(REPO / "bin/chicago95-control-panel"), run_name="__main__")

    assert (stopped.value.code, os.path.exists(picture)) == (0, True)


def test_arrow_button_without_a_menu_only_presses_and_releases(control_panel, qt_app):
    parent = QWidget()
    button = control_panel.ArrowButton()
    button.setParent(parent)
    button.mousePressEvent(mouse_event(QPoint(2, 2)))

    assert button.isDown() is False
