import sys

import pytest
from conftest import load_script
from PySide6.QtWidgets import QDialog


@pytest.fixture(scope="session")
def control_panel():
    return load_script("chicago95-control-panel")


@pytest.fixture
def make_page(control_panel, qt_app):
    def build(settings=None, succeeds=True):
        tab = control_panel.SettingsTab(settings or {}, control_panel.Actions())
        tab.title_field = tab.text("LOGIN_TITLE", "Title:", default="Log On")
        tab.clock_field = tab.flag("CLOCK_SHOW", "Clock", default="yes")
        applied = []
        page = control_panel.PropertiesPage("Test", [("Tab", tab)], lambda changes: applied.append(changes) or succeeds)
        page.tab, page.applied, page.finishes = tab, applied, []
        page.finished.connect(lambda: page.finishes.append(1))
        return page

    return build


def test_apply_is_off_until_a_field_changes_and_off_again_after_applying(make_page):
    page = make_page()
    before = page.apply_button.isEnabled()
    page.tab.title_field.setText("Hello")
    during = page.apply_button.isEnabled()
    page.apply_button.click()

    assert (before, during, page.apply_button.isEnabled()) == (False, True, False)


def test_apply_reports_only_the_changed_keys(make_page):
    page = make_page()
    page.tab.title_field.setText("Hello")
    page.apply_button.click()

    assert page.applied == [{"LOGIN_TITLE": "Hello"}]


def test_applying_again_reports_only_what_changed_since(make_page):
    page = make_page()
    page.tab.title_field.setText("Hello")
    page.apply_button.click()
    page.tab.clock_field.setChecked(False)
    page.apply_button.click()

    assert page.applied == [{"LOGIN_TITLE": "Hello"}, {"CLOCK_SHOW": "no"}]


def test_changing_a_field_back_to_what_was_saved_turns_apply_off(make_page):
    page = make_page({"LOGIN_TITLE": "Saved"})
    page.tab.title_field.setText("Other")
    page.tab.title_field.setText("Saved")

    assert (page.apply_button.isEnabled(), page.changed_values()) == (False, {})


def test_a_failed_apply_keeps_the_changes_pending(make_page):
    page = make_page(succeeds=False)
    page.tab.title_field.setText("Hello")
    page.apply_button.click()

    assert (page.apply_button.isEnabled(), page.changed_values()) == (True, {"LOGIN_TITLE": "Hello"})


def test_ok_applies_the_changes_and_finishes(make_page):
    page = make_page()
    page.tab.title_field.setText("Hello")
    page.ok_button.click()

    assert (page.applied, page.finishes) == ([{"LOGIN_TITLE": "Hello"}], [1])


def test_ok_without_changes_finishes_without_applying(make_page):
    page = make_page()
    page.ok_button.click()

    assert (page.applied, page.finishes) == ([], [1])


def test_a_failed_ok_stays_on_the_page(make_page):
    page = make_page(succeeds=False)
    page.tab.title_field.setText("Hello")
    page.ok_button.click()

    assert page.finishes == []


def test_cancel_puts_the_fields_back_and_finishes_without_applying(make_page):
    page = make_page({"LOGIN_TITLE": "Saved"})
    page.tab.title_field.setText("Other")
    page.cancel_button.click()

    assert (page.tab.values()["LOGIN_TITLE"], page.applied, page.finishes, page.apply_button.isEnabled()) == (
        "Saved",
        [],
        [1],
        False,
    )


def test_discarding_changes_puts_the_fields_back_without_finishing(make_page):
    page = make_page()
    page.tab.title_field.setText("Other")
    page.discard_changes()

    assert (page.tab.values()["LOGIN_TITLE"], page.finishes) == ("Log On", [])


def run_to_the_end(progress, qt_app):
    progress.start()
    progress.process.waitForFinished(15000)
    qt_app.processEvents()


def test_progress_that_succeeds_accepts_itself_and_keeps_the_output(control_panel, qt_app):
    progress = control_panel.ApplyProgress(None, [sys.executable, "-c", "print('hello from setup')"])
    run_to_the_end(progress, qt_app)

    assert (progress.result(), "hello from setup" in progress.log.toPlainText()) == (QDialog.Accepted, True)


def test_progress_that_fails_stays_open_with_the_details_shown_and_a_close_button(control_panel, qt_app):
    progress = control_panel.ApplyProgress(None, [sys.executable, "-c", "import sys; print('bad thing'); sys.exit(3)"])
    run_to_the_end(progress, qt_app)

    assert (
        progress.result(),
        progress.log.isHidden(),
        progress.details_button.text(),
        "bad thing" in progress.log.toPlainText(),
    ) == (QDialog.Rejected, False, "Close", True)


def test_progress_collects_the_error_output_too(control_panel, qt_app):
    progress = control_panel.ApplyProgress(None, [sys.executable, "-c", "import sys; sys.stderr.write('oops')"])
    run_to_the_end(progress, qt_app)

    assert "oops" in progress.log.toPlainText()


def test_progress_gives_sudo_the_graphical_password_prompt(control_panel, qt_app):
    progress = control_panel.ApplyProgress(None, [sys.executable, "-c", "import os; print(os.environ['SUDO_ASKPASS'])"])
    run_to_the_end(progress, qt_app)

    assert progress.log.toPlainText().strip().endswith("chicago95-askpass")


def test_details_button_shows_and_hides_the_log_while_setup_runs(control_panel, qt_app):
    progress = control_panel.ApplyProgress(None, [sys.executable, "-c", "pass"])
    initially_hidden = progress.log.isHidden()
    progress.details_button.click()
    shown = not progress.log.isHidden()
    progress.details_button.click()

    assert (initially_hidden, shown, progress.log.isHidden(), progress.details_button.text()) == (
        True,
        True,
        True,
        "Details >>",
    )


def test_progress_for_a_command_that_cannot_start_fails_instead_of_waiting_forever(control_panel, qt_app, tmp_path):
    progress = control_panel.ApplyProgress(None, [str(tmp_path / "missing-install.sh")])
    progress.start()
    qt_app.processEvents()

    assert (
        progress.result(),
        progress.details_button.text(),
        "missing-install.sh" in progress.log.toPlainText() or "No such file" in progress.log.toPlainText(),
    ) == (QDialog.Rejected, "Close", True)


@pytest.mark.parametrize("scrollable", [False, True])
def test_luna_scroll_pages_preserve_the_tab_gradient(control_panel, qt_app, monkeypatch, scrollable, tmp_path):
    from luna.luna_gallery import style_tree
    from luna.test_luna_style import luna_style
    from PySide6.QtWidgets import QTabWidget, QWidget

    monkeypatch.setattr(control_panel.chicago95ui, "luna_widgets", lambda: True)
    tabs = QTabWidget()
    style = luna_style.LunaStyle()
    page = QWidget()
    if scrollable:
        page.setMinimumHeight(900)
    area = control_panel.scrolling(page)
    tabs.addTab(area, "Quick Launch")
    tabs.addTab(QWidget(), "Other")
    style_tree(tabs, style)
    tabs.setPalette(luna_style.luna_palette())
    tabs.resize(500, 400)
    tabs.show()
    qt_app.processEvents()
    if scrollable:
        area.verticalScrollBar().setValue(100)
    for height in (400, 520):
        tabs.resize(500, height)
        tabs.setCurrentIndex(1)
        tabs.setCurrentIndex(0)
        qt_app.processEvents()
        image = tabs.grab().toImage()
        image.save(str(tmp_path / f"tab-page-{height}.png"))
        # The viewport must preserve the frame's gradient after scrolling, resizing
        # and switching tabs, rather than replacing it with the beige window face.
        for y in (60, 180, 320):
            assert image.pixelColor(2, y) == image.pixelColor(250, y)
            assert image.pixelColor(250, y).name().upper() != "#ECE9D8"
        assert image.pixelColor(250, 60) != image.pixelColor(250, 320)
    tabs.close()
