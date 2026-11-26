"""Regression tests for the graphical installer."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import QApplication, QWizard

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "installer"))
import model  # noqa: E402


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def advance_to(w, target):
    while w.currentId() != target:
        assert w.button(QWizard.NextButton).isEnabled()
        before = w.currentId()
        w.next()
        assert w.currentId() != before


def visit_setting(w, key):
    advance_to(w, w.mode_id)
    if key not in model.LIGHT_FIELDS:
        w.full.setChecked(True)
    advance_to(w, w.field_pages[key])


def back_to(w, target):
    while w.currentId() != target:
        assert w.button(QWizard.BackButton).isEnabled()
        w.back()


def test_component_list_cannot_drift_from_shell():
    source = (model.ROOT / "install.sh").read_text().split("COMPONENTS=$(ui_pick_components", 1)[1].split("\nfi", 1)[0]
    keys = re.findall(r'^\s*"([a-z]+):', source, re.M)
    assert set(keys) | {"icons"} == set(model.COMPONENTS)
    for description, image in model.COMPONENTS.values():
        assert description and (model.ROOT / image).is_file()


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("screen", "800x600@0"),
        ("screen", "0x480@1"),
        ("panel", "-1"),
        ("idle", "0"),
        ("task-button-width", "oops"),
        ("look", "../2000"),
        ("start-text", "a\nLOOK=aero"),
        ("start-logo", "/missing/image.png"),
        ("TITLE_ACTIVE", "#12345"),
        ("oops", "x"),
    ],
)
def test_bad_choice_cannot_reach_backend(key, value):
    with pytest.raises(ValueError):
        model.plan(["look"], {key: value})


@pytest.mark.parametrize("components", [[], ["not-a-component"]])
def test_invalid_selection_never_falls_through_to_all_components(components):
    with pytest.raises(ValueError):
        model.plan(components, {})


def test_no_implicit_components_or_default_overrides():
    args, settings = model.plan(["base"], {})
    assert args == ["--plain", "--yes", "--components=base"] and not settings
    for key, value in [("icons", "windows7"), ("wobbly", "yes")]:
        with pytest.raises(ValueError):
            model.plan(["base"], {key: value})


def test_text_is_data_and_extra_branding_reaches_settings():
    args, settings = model.plan(["startmenu"], {"start-text": "$(touch bad)", "LOGIN_TITLE": "Welcome = %h"})
    assert "--start-text=$(touch bad)" in args
    assert settings == {"LOGIN_TITLE": "Welcome = %h"}


def test_component_deselection_and_cancel_never_start_backend(app):
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    w.next()
    for i in range(w.components.count()):
        w.components.item(i).setCheckState(Qt.Unchecked)
    assert not w.button(QWizard.NextButton).isEnabled()
    w.reject()
    assert w.process.state() == QProcess.NotRunning


def test_failed_launch_is_recoverable_and_does_not_report_success(app, tmp_path):
    from wizard import SetupWizard

    w = SetupWizard(program=str(tmp_path / "missing"))
    w.show()
    advance_to(w, w.review_id)
    w.run_backend(True)
    w.process.waitForStarted(2000)
    app.processEvents()
    assert "failed" in w.status.text().lower()
    assert w.test_button.isEnabled()
    w.reject()


def test_preview_for_every_option_and_choice(app):
    from previews import render

    for key, field in model.FIELDS.items():
        for value in field.choices or (field.example,):
            assert not render(key, value, {}).isNull(), (key, value)


def test_preview_cannot_silently_substitute_an_unrelated_image(app, tmp_path):
    from previews import render

    with pytest.raises(ValueError):
        render("start-logo", str(tmp_path / "missing.svg"), {})
    with pytest.raises(ValueError):
        render("unknown", "yes", {})


def test_preview_reacts_to_edited_values(app):
    from previews import render

    for key, before, after in [
        ("TITLE_ACTIVE", "#ff0000", "#00ff00"),
        ("panel", "24", "48"),
        ("start-text", "Launch", "Go"),
        ("quick-launch", "yes", "no"),
        ("task-grouping", "always", "never"),
        ("look", "1995", "aero"),
    ]:
        assert render(key, before, {}).toImage() != render(key, after, {}).toImage(), key


def test_nonzero_backend_and_duplicate_click(app, tmp_path):
    from wizard import SetupWizard

    script = tmp_path / "stub"
    script.write_text('#!/bin/sh\necho call >> "$0.calls"\necho "backend error"\nexit 17\n')
    script.chmod(0o700)
    w = SetupWizard(program=str(script))
    w.show()
    advance_to(w, w.review_id)
    w.run_backend(True)
    w.run_backend(True)
    w.process.waitForFinished(3000)
    app.processEvents()
    assert script.with_suffix(".calls").read_text() == "call\n"
    assert "17" in w.status.text() and "failed" in w.status.text().lower()
    assert w.test_button.isEnabled()
    w.reject()


def test_switching_preset_ignores_previous_preset_values_without_erasing_explicit_edits(tmp_path):
    saved = tmp_path / "saved"
    saved.write_text("LOOK=1998\nSTART_TEXT=Go\nTASKBAR_STYLE=classic\n")
    effective = model.defaults(saved, {"look": "luna", "start-text": "Launch"})
    assert effective["taskbar-style"] == "luna"
    assert effective["start-text"] == "Launch"
    assert model.defaults(saved, {})["start-text"] == "Go"


def test_invalid_edit_blocks_next_and_cannot_start(app):
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    w.next()
    w.next()
    visit_setting(w, "screen")
    w.editor.setEditText("640x0@1")
    assert not w.button(QWizard.NextButton).isEnabled()
    w.run_backend(False)
    assert w.process.state() == QProcess.NotRunning
    w.reset_field()
    assert w.button(QWizard.NextButton).isEnabled()
    w.reject()


def test_dry_run_preserves_argument_boundaries_and_removes_transient_settings(app, tmp_path):
    import json

    from wizard import SetupWizard

    script = tmp_path / "record"
    report = tmp_path / "args"
    script.write_text(
        "#!/usr/bin/env python3\nimport json,sys\nfrom pathlib import Path\n"
        'args=sys.argv[1:]\np=Path(next(s.split("=",1)[1] for s in args if s.startswith("--settings=")))\n'
        f"Path({str(report)!r}).write_text(json.dumps([args,p.read_text()]))\n"
    )
    script.chmod(0o700)
    w = SetupWizard(program=str(script))
    w.show()
    w.next()
    w.next()
    visit_setting(w, "LOGIN_TITLE")
    w.editor.setEditText("My = desktop")
    advance_to(w, w.review_id)
    w.run_backend(True)
    assert w.process.waitForFinished(5000)
    app.processEvents()
    args, data = json.loads(report.read_text())
    assert "--dry-run" in args and data == "LOGIN_TITLE=My = desktop\n"
    assert not Path(next(s.split("=", 1)[1] for s in args if s.startswith("--settings="))).exists()
    assert "dry run" in w.status.text().lower()
    w.reject()


def test_launcher_help_requires_no_graphics_and_never_runs_install(tmp_path):
    result = subprocess.run(
        [str(model.ROOT / "install.sh"), "--gui", "--help"],
        cwd=tmp_path,
        env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0 and "graphical" in result.stdout and "--dry-run" in result.stdout
    assert not list(tmp_path.iterdir())


def test_read_only_launch_cannot_apply_even_by_calling_install_handler(app):
    from wizard import SetupWizard

    w = SetupWizard(dry_only=True)
    w.show()
    advance_to(w, w.review_id)
    assert not w.install_button.isEnabled()
    w.run_backend(False)
    assert w.process.state() == QProcess.NotRunning
    w.reject()


def test_real_detached_dry_run_leaves_no_installation(app, tmp_path, monkeypatch):
    from wizard import SetupWizard

    for key in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "XDG_CURRENT_DESKTOP"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SETUP_LOG", str(tmp_path / "setup.log"))
    w = SetupWizard()
    w.show()
    w.next()
    for i, key in enumerate(model.COMPONENTS):
        w.components.item(i).setCheckState(Qt.Checked if key == "mouse" else Qt.Unchecked)
    w.next()
    visit_setting(w, "cursor")
    w.editor.setCurrentText("48")
    advance_to(w, w.review_id)
    w.run_backend(True)
    assert w.process.waitForFinished(60000)
    assert w.status.text() == "Dry run complete.", w.log.toPlainText()[-4000:]
    log = (tmp_path / "setup.log").read_text()
    assert "Components: mouse" in log and "cursor=48" in log
    assert not (tmp_path / ".config/chicago95/setup.conf").exists()
    assert not (tmp_path / ".local/share/chicago95/manifest").exists()
    w.reject()


def test_unrecognized_saver_cannot_be_selected():
    with pytest.raises(ValueError):
        model.plan(["screensaver"], {"saver": "does-not-exist"})


def test_theme_dependent_default_panel_height(tmp_path):
    saved = tmp_path / "absent"
    assert model.defaults(saved, {"look": "aero"})["panel"] == "40"
    assert model.defaults(saved, {"look": "luna"})["panel"] == "30"
    assert model.defaults(saved, {"look": "aero", "panel": "36"})["panel"] == "36"


def test_headless_launcher_explains_desktop_requirement_without_starting_qt(tmp_path):
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path)}
    proc = subprocess.run(
        [str(model.ROOT / "install.sh"), "--gui"],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=10,
        check=False,
    )
    assert proc.returncode == 2 and "desktop session" in proc.stderr
    assert not list(tmp_path.iterdir())


def test_missing_external_audio_still_has_an_explicit_playable_preview(monkeypatch):
    import previews

    monkeypatch.setattr(previews, "sound_sample", lambda _: None)
    for value in ("Windows7", "Chicago95"):
        url = previews.sound_url(value)
        assert url.scheme() == "https" and url.path().endswith(".wav")


def test_absent_waving_flag_uses_bundled_reference(app, tmp_path, monkeypatch):
    import previews

    monkeypatch.setenv("HOME", str(tmp_path))
    path = previews.artwork("LOGIN_LOGO", "waving-flag", {})
    assert (model.ROOT / path).is_file()


def test_rendering_bad_saved_values_cannot_break_other_previews(app):
    from previews import render

    with pytest.raises(ValueError):
        render("screen", "0x0@1", {})
    with pytest.raises(ValueError):
        render("look", "../../README", {})


def test_toggling_an_untouched_preset_setting_back_explicitly_preserves_the_choice(app):
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    advance_to(w, w.mode_id - 1)
    w.os_picker.setCurrentIndex(w.os_picker.findData("aero"))
    visit_setting(w, "taskbar-style")
    w.editor.setCurrentText("classic")
    back_to(w, w.mode_id - 1)
    w.os_picker.setCurrentIndex(w.os_picker.findData("luna"))
    visit_setting(w, "taskbar-style")
    assert w.editor.currentText() == "classic"
    w.reset_field()
    assert w.editor.currentText() == "luna"
    w.reject()


def test_gui_switch_after_dry_run_cannot_fall_into_shell_installer(tmp_path):
    proc = subprocess.run(
        [str(model.ROOT / "install.sh"), "--dry-run", "--gui", "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert "usage: wizard.py" in proc.stdout


def test_auto_quick_launch_preview_matches_selected_era(app):
    from previews import render

    for look, effective in [("1995", "no"), ("1998", "yes")]:
        assert (
            render("quick-launch", "auto", {"look": look}).toImage()
            == render("quick-launch", effective, {"look": look}).toImage()
        )


def test_banner_colour_is_painted_on_banner_and_not_the_caption(app):
    from previews import render

    a = render("BANNER_BG", "#ff0000", {}).toImage()
    b = render("BANNER_BG", "#00ff00", {}).toImage()
    assert a.pixelColor(200, 40) == b.pixelColor(200, 40)
    assert a.pixelColor(120, 81) != b.pixelColor(120, 81)


def test_unreadable_custom_picture_is_rejected_even_if_extension_matches(tmp_path):
    image = tmp_path / "computer.png"
    image.write_text("this is plain text")
    with pytest.raises(ValueError):
        model.plan(["sddm"], {"LOGIN_ICON": str(image)})


def test_cross_page_error_prevents_install_until_repaired(app):
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    w.next()
    look = w.components.item(list(model.COMPONENTS).index("look"))
    look.setCheckState(Qt.Checked)
    w.components.item(list(model.COMPONENTS).index("icons")).setCheckState(Qt.Unchecked)
    w.next()
    visit_setting(w, "icons")
    w.editor.setCurrentText("windowsxp")
    back_to(w, 1)
    look.setCheckState(Qt.Unchecked)
    visit_setting(w, "icons")
    assert not w.button(QWizard.NextButton).isEnabled()
    assert "look" in w.note.text().lower()
    w.reset_field()
    assert w.button(QWizard.NextButton).isEnabled()
    w.reject()


def test_default_task_grouping_preview_does_not_group_classic_desktop(app):
    from previews import render

    for style, effective in [("classic", "never"), ("aero", "always")]:
        state = {"taskbar-style": style}
        assert render("task-grouping", "auto", state).toImage() == render("task-grouping", effective, state).toImage()


def test_dolphin_preview_does_not_show_colour_settings(app):
    from previews import artwork, render

    assert artwork("explorer", "dolphin", {}) != "docs/manual-setup/colours.png"
    assert render("explorer", "dolphin", {}).toImage() != render("explorer", "thunar", {}).toImage()


def test_missing_audio_plugin_has_visible_feedback(app, monkeypatch):
    from wizard import SetupWizard

    monkeypatch.setitem(sys.modules, "PySide6.QtMultimedia", None)
    w = SetupWizard()
    w.show()
    visit_setting(w, "sounds")
    w.play_sample()
    assert "multimedia" in w.note.text().lower()
    w.reject()


def test_active_install_cannot_be_closed_or_duplicated(app, tmp_path):
    from wizard import SetupWizard

    script = tmp_path / "backend"
    script.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\nsleep 0.15\n')
    script.chmod(0o700)
    w = SetupWizard(program=str(script))
    w.show()
    advance_to(w, w.review_id)
    w.run_backend(False)
    assert not w.close()
    w.reject()
    assert w.isVisible() and not w.install_button.isEnabled()
    assert w.process.waitForFinished(3000)
    assert "--dry-run" not in w.log.toPlainText() and "--components=" in w.log.toPlainText()
    assert "finished" in w.status.text().lower()
    w.close()


def test_icon_only_install_never_adds_the_rest_of_the_desktop():
    args, _ = model.plan(["icons"], {"icons": "windows7"})
    assert "--components=icons" in args and "--look=aero" not in args


def test_progress_only_counts_completed_backend_records(app):
    from wizard import SetupWizard

    w = SetupWizard()
    w.append_output("Checking 99/100 files\n   (2/1")
    assert w.progress.maximum() == 0
    w.append_output("0) example.png\n   (99/8) malformed\n")
    assert (w.progress.value(), w.progress.maximum()) == (2, 10)
    w.reject()


@pytest.mark.parametrize("theme", model.FIELDS["icons"].choices)
def test_icon_preview_has_six_distinct_illustrated_cells(app, theme):
    from previews import render

    image = render("icons", theme, {}).toImage()
    tiles = []
    for row in range(2):
        for column in range(3):
            cell = image.copy(column * 114 + 30, row * 106 + 12, 54, 54)
            assert len({cell.pixel(x, y) for x in range(cell.width()) for y in range(cell.height())}) > 3, (
                theme,
                row,
                column,
            )
            assert cell not in tiles
            tiles.append(cell)


def test_icons_component_refreshes_on_back_after_theme_change(app):
    from previews import render
    from PySide6.QtWidgets import QLabel
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    w.next()
    w.components.setCurrentRow(list(model.COMPONENTS).index("icons"))
    w.components.currentItem().setCheckState(Qt.Checked)
    w.next()
    visit_setting(w, "icons")
    w.editor.setCurrentText("windows7")
    back_to(w, 1)
    images = [label.pixmap() for label in w.currentPage().findChildren(QLabel)]
    assert any(p and p.toImage() == render("icons", "windows7", {}).toImage() for p in images)
    w.close()


@pytest.mark.parametrize(
    ("look", "capture"),
    [
        ("1995", "win95emptydesktop.png"),
        ("1998", "win98emptydesktop.png"),
        ("2000", "themes/win2k/desktop.png"),
        ("2001", "themes/winxp-classic/desktop.png"),
        ("luna", "xpemptydesktop.png"),
        ("aero", "win7gadgets.png"),
    ],
)
def test_desktop_and_theme_picker_show_the_matching_desktop_capture(app, look, capture):
    from previews import artwork
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QLabel
    from wizard import SetupWizard

    expected = model.ROOT / model.REF / capture
    assert model.ROOT / artwork("look", look, {}) == expected
    w = SetupWizard()
    w.show()
    w.next()
    w.components.setCurrentRow(list(model.COMPONENTS).index("desktop"))
    w.next()
    w.os_picker.setCurrentIndex(w.os_picker.findData(look))
    w.back()
    pictures = [label for label in w.currentPage().findChildren(QLabel) if label.pixmap()]
    assert len(pictures) == 1
    label = pictures[0]
    assert (
        label.pixmap().toImage()
        == QPixmap(str(expected)).scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation).toImage()
    )
    w.close()


@pytest.mark.parametrize("component", ["desktop", "background", "sounds", "lockscreen", "winamp", "splash", "base"])
def test_component_preview_uses_a_screenshot_instead_of_an_icon_or_comparison_sheet(component):
    from PySide6.QtGui import QImageReader

    path = model.COMPONENTS[component][1]
    assert path.startswith((model.REF, "installer/screenshots/")) or path == "screenshot.png"
    size = QImageReader(str(model.ROOT / path)).size()
    assert size.width() >= 250 and size.height() >= 100


@pytest.mark.parametrize(
    ("field", "capture"),
    [
        ("decoration", "run.png"),
        ("widget-style", "display-properties.png"),
        ("taskbar-style", "taskbar/populated.png"),
        ("control-panel-style", "control-panel.png"),
        ("start-menu-style", "start-menu.png"),
    ],
)
def test_classic_style_preview_uses_guest_capture_not_visual_diff(app, field, capture):
    from previews import artwork

    value = "2000" if field == "start-menu-style" else "classic"
    assert artwork(field, value, {"look": "2000"}) == model.REF + "themes/win2k/" + capture


def test_firefox_preview_does_not_show_internet_explorer():
    assert model.COMPONENTS["firefox"][1] == "installer/screenshots/firefox.png"


@pytest.mark.parametrize("full", [False, True])
def test_customization_route_has_one_page_per_setting_and_uses_selected_os(app, full):
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    w.next()
    w.next()
    assert w.currentPage().title() == "Choose a starting point"
    w.os_picker.setCurrentIndex(w.os_picker.findData("aero"))
    w.next()
    assert w.light.isChecked()
    if full:
        w.full.setChecked(True)
    w.next()
    seen = []
    while w.currentId() != w.review_id:
        assert w.key not in seen
        seen.append(w.key)
        assert w.currentPage().title() == model.FIELDS[w.key].label
        if w.key == "icons":
            assert w.editor.currentText() == "windows7"
        assert w.button(QWizard.NextButton).isEnabled()
        w.next()
    assert seen == (list(model.FIELDS)[1:] if full else list(model.LIGHT_FIELDS))
    assert "--look=aero" in model.plan(w.selected(), w.active_overrides())[0]
    w.close()


def test_switch_to_light_does_not_install_or_validate_hidden_full_edits(app):
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    for _ in range(3):
        w.next()
    w.full.setChecked(True)
    w.next()
    assert w.key == "decoration"
    w.editor.setCurrentText("aero")
    w.back()
    w.light.setChecked(True)
    w.next()
    assert "decoration" not in w.active_overrides()
    w.back()
    w.full.setChecked(True)
    w.next()
    assert w.editor.currentText() == "aero"
    w.close()


def test_saved_panel_and_distro_branding_do_not_override_selected_os(tmp_path):
    saved = tmp_path / "saved"
    saved.write_text("PANEL=88\nBRANDING=distro\n")
    state = model.defaults(saved, {"look": "aero"})
    assert (state["panel"], state["branding"]) == ("40", "windows")


def test_reselecting_os_supplied_logo_never_blocks_next(app):
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    advance_to(w, w.mode_id - 1)
    w.os_picker.setCurrentIndex(w.os_picker.findData("aero"))
    visit_setting(w, "LOGIN_LOGO")
    assert w.editor.currentText() == "aero-flag"
    w.editor.setCurrentText("penguin")
    w.editor.setCurrentText("aero-flag")
    assert w.button(QWizard.NextButton).isEnabled()
    assert "LOGIN_LOGO" not in w.active_overrides()
    w.close()


def test_luna_auto_task_width_does_not_inherit_saved_custom_width(tmp_path):
    saved = tmp_path / "saved"
    saved.write_text("TASK_BUTTON_WIDTH=220\n")
    assert model.defaults(saved, {"look": "luna"})["task-button-width"] == "0"


def test_welcome_illustration_gives_way_to_settings_header(app):
    from PySide6.QtWidgets import QLabel
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    illustration = w.currentPage().findChild(QLabel, "welcomeArt")
    assert illustration and illustration.isVisible() and illustration.pixmap()
    w.next()
    assert not illustration.isVisible()
    assert w.sideWidget() is None
    assert w.currentPage().subTitle()
    assert not w.pixmap(QWizard.LogoPixmap).isNull()
    w.back()
    assert illustration.isVisible()
    w.close()


def test_setup_dialog_is_inset_in_patterned_backdrop(app):
    from wizard import SetupWindow, SetupWizard

    w = SetupWizard()
    frame = SetupWindow(w)
    frame.show()
    app.processEvents()
    assert frame.caption.mapTo(frame, frame.caption.rect().topLeft()).x() >= 18
    image = frame.grab().toImage()
    assert len({image.pixel(x, 8) for x in range(24)}) >= 2
    frame.close()


def test_windows_version_uses_full_capture_for_large_preview(app):
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QLabel
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    advance_to(w, w.mode_id - 1)
    preview = next(x for x in w.currentPage().findChildren(QLabel) if x.pixmap())
    assert preview.width() > 344
    w.os_picker.setCurrentIndex(w.os_picker.findData("1998"))
    expected = QPixmap(str(model.ROOT / model.DESKTOP_CAPTURES["1998"])).scaled(
        preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
    )
    assert preview.pixmap().toImage() == expected.toImage()
    w.close()


def test_setup_uses_win95_face_and_solid_navy_even_for_aero(app):
    from PySide6.QtGui import QColor, QPalette
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    advance_to(w, w.os_id)
    w.os_picker.setCurrentIndex(w.os_picker.findData("aero"))
    w.next()
    for role in (QPalette.Window, QPalette.Button):
        assert w.light.palette().color(role) == QColor("#c0c0c0")
    assert w.light.palette().color(QPalette.Highlight) == QColor("#000080")
    w.close()


def test_setup_caption_close_respects_running_install(app):
    from PySide6.QtWidgets import QToolButton
    from wizard import SetupWindow, SetupWizard

    w = SetupWizard()
    frame = SetupWindow(w)
    frame.show()
    close = frame.findChild(QToolButton, "captionClose")
    assert close and close.isVisible()
    w.busy = True
    close.click()
    assert frame.isVisible()
    from PySide6.QtWidgets import QMessageBox

    assert frame.findChild(QMessageBox) is None
    w.busy = False
    close.click()
    alert = frame.findChild(QMessageBox)
    assert frame.isVisible() and alert.isVisible()
    alert.button(QMessageBox.Yes).click()
    assert not frame.isVisible()


def test_copying_screen_shows_progress_and_restores_log_after_failure(app):
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    advance_to(w, w.review_id)
    w.set_busy(True)
    assert w.log.isHidden() and w.install_button.isHidden()
    assert w.progress.isVisible() and w.status.isVisible()
    w.end_run("Setup failed")
    assert w.log.isVisible() and w.install_button.isVisible()
    assert not w.progress.isVisible()
    w.close()


def test_escape_on_preview_keeps_setup_and_selection_open(app):
    from PySide6.QtTest import QTest
    from wizard import SetupWindow, SetupWizard

    w = SetupWizard()
    frame = SetupWindow(w)
    frame.show()
    visit_setting(w, "icons")
    w.editor.setCurrentIndex(1)
    selected = w.editor.currentText()
    w.editor.showPopup()
    QTest.keyClick(w.editor.view(), Qt.Key_Escape)
    assert not w.editor.view().isVisible()
    QTest.keyClick(w.editor, Qt.Key_Escape)
    assert frame.isVisible() and w.currentId() == w.field_pages["icons"]
    assert w.editor.currentText() == selected
    frame.close()


def test_final_tasks_follow_complete_backend_headings_only(app):
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    advance_to(w, w.review_id)
    w.set_busy(True)
    w.append_output("== Copying fi")
    assert "▶" not in w.tasks.text()
    w.append_output("les\n== unknown phase\n")
    assert "▶ Copying files" in w.tasks.text()
    w.append_output("== Finishing Setup\n")
    assert "✓ Copying files" in w.tasks.text()
    assert "▶ Finishing Setup" in w.tasks.text()
    assert w.currentPage().title() == "Performing Final Tasks"
    w.end_run("Setup failed")
    assert not w.tasks.isVisible()
    assert w.currentId() == w.review_id
    w.close()


@pytest.mark.parametrize("dry,code", [(False, 1), (True, 0), (False, 0)])
def test_only_successful_install_reaches_completion(app, dry, code):
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    advance_to(w, w.review_id)
    w.next()
    assert w.currentId() == w.review_id
    w.dry = dry
    w.set_busy(True)
    w.backend_finished(code, QProcess.NormalExit)
    if dry or code:
        assert w.currentId() == w.review_id and w.test_button.isEnabled()
        assert w.log.isVisible()
    else:
        assert w.currentPage().objectName() == "completionPage"
        assert w.buttonText(QWizard.FinishButton) == "Finish"
        w.button(QWizard.FinishButton).click()
        assert not w.isVisible()
    w.close()


@pytest.mark.parametrize("exit_via", ["window", "review", "dry run", "failed install"])
def test_cancel_exit_keeps_current_page_and_choices(app, exit_via):
    from PySide6.QtWidgets import QMessageBox
    from wizard import SetupWindow, SetupWizard

    w = SetupWizard()
    frame = SetupWindow(w)
    frame.show()
    visit_setting(w, "icons")
    w.editor.setCurrentIndex(1)
    choices = w.active_overrides()
    if exit_via != "window":
        advance_to(w, w.review_id)
    if exit_via in ("dry run", "failed install"):
        w.dry = exit_via == "dry run"
        w.set_busy(True)
        w.backend_finished(0 if w.dry else 1, QProcess.NormalExit)
    page = w.currentId()
    if exit_via == "review":
        w.button(QWizard.FinishButton).click()
    else:
        frame.close()
    alert = frame.findChild(QMessageBox)
    assert alert and alert.isVisible()
    assert alert.defaultButton() == alert.button(QMessageBox.No)
    alert.reject()
    assert frame.isVisible() and w.isVisible() and w.currentId() == page
    assert w.active_overrides() == choices
    frame.close()
    frame.findChild(QMessageBox).button(QMessageBox.Yes).click()
    assert not frame.isVisible()


def test_customization_scope_lists_only_the_pages_on_selected_route(app):
    from PySide6.QtWidgets import QListWidget
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    advance_to(w, w.mode_id)
    scope = w.currentPage().findChild(QListWidget)
    assert scope
    for mode in (w.full, w.light):
        mode.click()
        assert [scope.item(i).text() for i in range(scope.count())] == [model.FIELDS[k].label for k in w.route_fields()]
    w.close()


def test_custom_setting_keeps_inherited_default_visible(app):
    from wizard import SetupWizard

    w = SetupWizard()
    w.show()
    visit_setting(w, "icons")
    default = w.editor.currentText()
    w.editor.setCurrentIndex((w.editor.currentIndex() + 1) % w.editor.count())
    assert default in w.default_value.text() and w.default_value.isVisible()
    assert w.default_value.text() != w.editor.currentText()
    w.close()


def test_linux_profile_skips_unusable_desktop_preferences(tmp_path):
    (tmp_path / "kcminputrc").write_text("[Mouse]\ncursorSize=999\n")
    (tmp_path / "mimeapps.list").write_text("[Default Applications]\ninode/directory=unknown.desktop;\n")
    (tmp_path / "kdeglobals").write_bytes(b"\xff")
    choices = model.linux_preferences(tmp_path)
    assert choices == {"branding": "distro"}


def test_linux_starting_point_drives_reset_preview_and_backend(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QLabel
    from wizard import SetupWizard

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    (tmp_path / "kdeglobals").write_text("[General]\nfont=Example Sans,10,-1,5,50\n")
    (tmp_path / "kcminputrc").write_text("[Mouse]\ncursorSize=24\n")
    (tmp_path / "mimeapps.list").write_text("[Default Applications]\ninode/directory=org.kde.dolphin.desktop;\n")
    saved = tmp_path / "setup.conf"
    saved.write_text("LOOK=luna\nFONT=Old Font\nCURSOR=48\n")
    w = SetupWizard(program="/bin/echo")
    w.saved = saved
    w.show()
    advance_to(w, w.os_id)
    w.os_picker.setCurrentIndex(w.os_picker.findData("linux"))
    preview = w.currentPage().findChild(QLabel, "preview")
    assert "Example Sans" in preview.text()
    visit_setting(w, "cursor")
    assert w.editor.currentText() == "24"
    w.editor.setCurrentText("48")
    w.reset_field()
    assert w.editor.currentText() == "24"
    advance_to(w, w.review_id)
    w.run_backend(True)
    assert w.process.waitForFinished(3000)
    args = w.log.toPlainText()
    for option in ("--font=Example Sans", "--cursor=24", "--explorer=dolphin", "--branding=distro", "--dry-run"):
        assert option in args
    assert "--look=" not in args
    back_to(w, w.os_id)
    w.os_picker.setCurrentIndex(w.os_picker.findData("aero"))
    assert "font" not in w.active_overrides()
    assert w.active_overrides()["look"] == "aero"
    w.close()
