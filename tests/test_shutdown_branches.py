import sys

import pytest
from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

LOOK_2000 = {"style": "2000", "osName": "Windows 2000", "osCompany": "Microsoft", "edition": "Professional"}
LOOK_1998 = {"style": "1998", "osName": "Windows 98", "osCompany": "", "edition": "Second Edition"}


def write_png(path, width=40, height=20):
    image = QImage(width, height, QImage.Format_ARGB32)
    image.fill(QColor("#336699"))
    image.save(str(path))
    return str(path)


def write_svg(path):
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20"><rect width="40" height="20" fill="red"/></svg>'
    )
    return str(path)


def make_sound(sound_root, theme, extension="wav"):
    stereo = sound_root / theme / "stereo"
    stereo.mkdir(parents=True)
    sound = stereo / f"system-shutdown.{extension}"
    sound.write_text("")
    return str(sound)


@pytest.fixture
def sound_root(shutdown, tmp_path, monkeypatch):
    root = tmp_path / "sounds"
    monkeypatch.setattr(shutdown, "SOUND_ROOTS", (str(root),))
    return root


@pytest.fixture
def app_for_main(shutdown, qt_app, monkeypatch):
    monkeypatch.setattr(shutdown.chicago95ui, "make_app", lambda _name: qt_app)
    return qt_app


def run_main(shutdown, monkeypatch, *arguments):
    monkeypatch.setattr(sys, "argv", ["chicago95-shutdown", *arguments])
    return shutdown.main()


def test_stand_by_command_suspends_through_systemctl(shutdown):
    assert shutdown.shutdown_command(shutdown.STAND_BY, ["gdbus"]) == ["systemctl", "suspend"]


def test_hibernate_command_hibernates_through_systemctl(shutdown):
    assert shutdown.shutdown_command(shutdown.HIBERNATE, ["gdbus"]) == ["systemctl", "hibernate"]


def test_dos_mode_command_opens_konsole(shutdown):
    assert shutdown.shutdown_command(shutdown.DOS_MODE) == ["konsole"]


def test_shut_down_command_falls_back_to_systemctl_poweroff_without_dbus(shutdown):
    assert shutdown.shutdown_command(shutdown.SHUT_DOWN) == ["systemctl", "poweroff"]


def test_sound_theme_is_chicago95_when_kdeglobals_is_missing(shutdown, tmp_path):
    assert shutdown.chosen_sound_theme(tmp_path / "missing") == "Chicago95"


def test_sound_theme_is_chicago95_when_kdeglobals_has_no_sounds_group(shutdown, tmp_path):
    kdeglobals = tmp_path / "kdeglobals"
    kdeglobals.write_text("[General]\nTheme=Other\n")

    assert shutdown.chosen_sound_theme(kdeglobals) == "Chicago95"


def test_sound_theme_is_chicago95_when_sounds_group_has_no_theme(shutdown, tmp_path):
    kdeglobals = tmp_path / "kdeglobals"
    kdeglobals.write_text("[Sounds]\nEnable=true\n")

    assert shutdown.chosen_sound_theme(kdeglobals) == "Chicago95"


def test_sound_theme_is_the_sounds_group_theme_when_set(shutdown, tmp_path):
    kdeglobals = tmp_path / "kdeglobals"
    kdeglobals.write_text("[General]\nTheme=Other\n[Sounds]\nTheme= Classic \n")

    assert shutdown.chosen_sound_theme(kdeglobals) == "Classic"


def test_shutdown_sound_file_is_the_given_themes_sound(shutdown, sound_root):
    classic_sound = make_sound(sound_root, "Classic")

    assert shutdown.shutdown_sound_file("Classic") == classic_sound


def test_shutdown_sound_file_is_none_when_no_theme_has_a_sound(shutdown, sound_root):
    sound_root.mkdir()

    assert shutdown.shutdown_sound_file("Classic") is None


def test_sound_player_is_pw_play_when_both_players_are_installed(shutdown, path_with, tmp_path):
    path_with("pw-play", "paplay")

    assert shutdown.sound_player() == str(tmp_path / "pw-play")


def test_sound_player_is_paplay_when_only_paplay_is_installed(shutdown, path_with, tmp_path):
    path_with("paplay")

    assert shutdown.sound_player() == str(tmp_path / "paplay")


def test_sound_player_is_none_when_no_player_is_installed(shutdown, path_with):
    path_with()

    assert shutdown.sound_player() is None


def test_safe_font_family_is_monospace_when_no_preferred_font_is_installed(shutdown, qt_app, monkeypatch):
    monkeypatch.setattr(shutdown, "SAFE_FONT_PREFERENCES", ("No Such Font", "Another Missing One"))

    assert shutdown.pick_safe_font_family() == "Monospace"


def test_safe_font_family_is_the_first_installed_preference(shutdown, qt_app, monkeypatch):
    installed_family = shutdown.QFontDatabase.families()[0]
    monkeypatch.setattr(shutdown, "SAFE_FONT_PREFERENCES", ("No Such Font", installed_family))

    assert shutdown.pick_safe_font_family() == installed_family


def test_safe_font_doubles_in_size_when_the_screen_is_twice_as_wide(shutdown, qt_app):
    narrow = shutdown.fit_safe_font("Monospace", 800)
    wide = shutdown.fit_safe_font("Monospace", 1600)

    assert wide.pointSizeF() == pytest.approx(2 * narrow.pointSizeF())


def test_virtual_screen_geometry_is_the_union_of_every_screen(shutdown, qt_app):
    expected = QRect()
    for screen in qt_app.screens():
        expected = expected.united(screen.geometry())

    assert shutdown.virtual_screen_geometry(qt_app) == expected


def test_safe_screen_closes_on_key_press_when_held_until_input(shutdown, qt_app):
    safe_screen = shutdown.SafeScreen(QRect(0, 0, 640, 360), hold_until_input=True)
    safe_screen.show()

    QTest.keyClick(safe_screen, Qt.Key_Space)

    assert safe_screen.isVisible() is False


def test_safe_screen_closes_on_mouse_press_when_held_until_input(shutdown, qt_app):
    safe_screen = shutdown.SafeScreen(QRect(0, 0, 640, 360), hold_until_input=True)
    safe_screen.show()

    QTest.mouseClick(safe_screen, Qt.LeftButton)

    assert safe_screen.isVisible() is False


def test_safe_screen_stays_open_on_key_and_mouse_when_not_held(shutdown, qt_app):
    safe_screen = shutdown.SafeScreen(QRect(0, 0, 640, 360), hold_until_input=False)
    safe_screen.show()

    QTest.keyClick(safe_screen, Qt.Key_Space)
    QTest.mouseClick(safe_screen, Qt.LeftButton)

    assert safe_screen.isVisible() is True
    safe_screen.hold_until_input = True
    safe_screen.close()


def test_dialog_centres_on_the_available_screen_area(shutdown, qt_app):
    dialog = shutdown.LogOffDialog(LOOK_2000)

    shutdown.centre_on_screen(dialog)

    offset = dialog.geometry().center() - dialog.screen().availableGeometry().center()
    assert max(abs(offset.x()), abs(offset.y())) <= 1


def test_log_off_dialog_title_names_the_short_os(shutdown, qt_app):
    assert shutdown.LogOffDialog(LOOK_2000).windowTitle() == "Log Off Windows"


def test_log_off_dialog_asks_the_question_and_rejects_through_no(shutdown, qt_app):
    dialog = shutdown.LogOffDialog(LOOK_2000)
    question_texts = [label.text() for label in dialog.findChildren(shutdown.QLabel)]
    no_button = next(button for button in dialog.findChildren(shutdown.QPushButton) if button.text() == "&No")

    no_button.click()

    assert (shutdown.LogOffDialog.QUESTION in question_texts, dialog.result()) == (True, shutdown.QDialog.Rejected)


def test_shut_down_dialog_2000_chooses_shut_down_when_accepted_with_it_selected(shutdown, qt_app):
    dialog = shutdown.ShutDownDialog(LOOK_2000)
    dialog.combo.setCurrentIndex(1)
    dialog.accept()

    assert dialog.choice == shutdown.SHUT_DOWN


def test_shut_down_dialog_2000_describes_the_selected_choice(shutdown, qt_app):
    dialog = shutdown.ShutDownDialog(LOOK_2000)

    dialog.combo.setCurrentIndex(3)

    assert dialog.description.text() == shutdown.DESCRIPTIONS[shutdown.STAND_BY]


def test_shut_down_dialog_1998_chooses_the_checked_radio_when_accepted(shutdown, qt_app):
    dialog = shutdown.ShutDownDialog(LOOK_1998)
    dialog.radios[3].setChecked(True)

    dialog.accept()

    assert dialog.choice == shutdown.DOS_MODE


def test_shut_down_dialog_with_unknown_style_lists_the_1995_choices(shutdown, qt_app):
    dialog = shutdown.ShutDownDialog({"style": "3000", "osName": "Windows 95"})

    assert dialog.choices == shutdown.CHOICES["1995"]


def test_banner_load_is_null_when_path_is_empty(shutdown, qt_app):
    assert shutdown.BrandBanner.load("", 20).isNull() is True


def test_banner_load_is_null_when_path_does_not_exist(shutdown, qt_app, tmp_path):
    assert shutdown.BrandBanner.load(str(tmp_path / "gone.png"), 20).isNull() is True


def test_banner_load_scales_a_png_to_the_given_height(shutdown, qt_app, tmp_path):
    logo = shutdown.BrandBanner.load(write_png(tmp_path / "logo.png"), 10)

    assert (logo.width(), logo.height()) == (20, 10)


def test_banner_load_renders_an_svg_at_the_given_height(shutdown, qt_app, tmp_path):
    logo = shutdown.BrandBanner.load(write_svg(tmp_path / "logo.svg"), 10)

    assert (logo.width(), logo.height()) == (20, 10)


def banner_look(**overrides):
    return {
        "osName": "Windows 2000",
        "osCompany": "Microsoft",
        "edition": "Professional",
        "tagline": "Built on NT",
        "osLogo": "",
        "companyLogo": "",
        **overrides,
    }


def banner_pixels(banner):
    banner.resize(411, 93)
    return banner.grab().toImage()


def test_banner_paints_company_logo_in_the_corner_when_one_is_set(shutdown, qt_app, tmp_path):
    with_logo = shutdown.BrandBanner(banner_look(companyLogo=write_png(tmp_path / "company.png")))
    without_logo = shutdown.BrandBanner(banner_look())

    assert banner_pixels(with_logo) != banner_pixels(without_logo)


def test_banner_paints_login_tagline_and_offset_when_login(shutdown, qt_app):
    look = banner_look()

    assert banner_pixels(shutdown.BrandBanner(look, login=True)) != banner_pixels(shutdown.BrandBanner(look))


def test_banner_paints_no_company_wordmark_when_company_is_empty(shutdown, qt_app):
    named = banner_pixels(shutdown.BrandBanner(banner_look()))
    anonymous = banner_pixels(shutdown.BrandBanner(banner_look(osCompany="")))

    assert named != anonymous


def test_banner_skips_blank_name_parts_between_numbers(shutdown, qt_app):
    banner = shutdown.BrandBanner(banner_look(osName="Win 1 2"))
    banner.resize(411, 93)

    assert banner.grab().isNull() is False


def test_run_command_prints_the_command_when_dry_run(shutdown, capsys):
    shutdown.run_command(["systemctl", "poweroff"], dry_run=True)

    assert capsys.readouterr().out == "dry-run, would run: systemctl poweroff\n"


def test_run_command_starts_the_process_when_not_dry_run(shutdown, tmp_path):
    marker = tmp_path / "started"

    shutdown.run_command(["touch", str(marker)], dry_run=False)

    QTest.qWait(300)
    assert marker.exists() is True


def test_log_off_runs_the_logout_command_when_confirmed(shutdown, capsys):
    shutdown.log_off(True, True, ["gdbus"])

    assert capsys.readouterr().out == "dry-run, would run: gdbus org.kde.Shutdown.logout\n"


def test_log_off_runs_nothing_when_not_confirmed(shutdown, capsys):
    shutdown.log_off(False, True, ["gdbus"])

    assert capsys.readouterr().out == ""


def test_shutdown_sound_plays_through_the_player_when_both_exist(shutdown, sound_root, path_with, tmp_path, capsys):
    path_with("pw-play")
    sound = make_sound(sound_root, "Chicago95")

    shutdown.play_shutdown_sound(dry_run=True)

    assert capsys.readouterr().out == f"dry-run, would run: {tmp_path / 'pw-play'} {sound}\n"


def test_shutdown_sound_is_silent_when_no_player_is_installed(shutdown, sound_root, path_with, capsys):
    path_with()
    make_sound(sound_root, "Chicago95")

    shutdown.play_shutdown_sound(dry_run=True)

    assert capsys.readouterr().out == ""


def test_login_banner_renders_a_png_scaled_by_the_given_factor(shutdown, qt_app, tmp_path):
    path = tmp_path / "banner.png"

    saved = shutdown.render_login_banner(banner_look(), path, scale=2)

    assert (saved, QImage(str(path)).size().toTuple()) == (True, (822, 186))


def test_grab_widget_saves_the_widget_and_reports_the_path(shutdown, qt_app, tmp_path, capsys):
    path = str(tmp_path / "dialog.png")

    shutdown.grab_widget(shutdown.LogOffDialog(LOOK_2000), path)

    assert (QImage(path).isNull(), capsys.readouterr().out) == (False, f"saved {path}\n")


def test_main_saves_the_shut_down_dialog_for_screenshot(shutdown, app_for_main, monkeypatch, tmp_path, capsys):
    path = str(tmp_path / "shutdown.png")

    exit_code = run_main(shutdown, monkeypatch, "--screenshot", path)

    assert (exit_code, QImage(path).isNull(), capsys.readouterr().out) == (0, False, f"saved {path}\n")


def test_main_saves_the_log_off_dialog_for_screenshot_with_log_off(shutdown, app_for_main, monkeypatch, tmp_path):
    path = str(tmp_path / "logoff.png")

    exit_code = run_main(shutdown, monkeypatch, "--screenshot", path, "--log-off")

    assert (exit_code, QImage(path).isNull()) == (0, False)


def test_main_saves_the_login_banner_and_exits_zero(shutdown, app_for_main, monkeypatch, tmp_path):
    path = tmp_path / "login.png"

    exit_code = run_main(shutdown, monkeypatch, "--login-banner", str(path))

    assert (exit_code, path.exists()) == (0, True)


def test_main_exits_one_when_the_login_banner_cannot_be_saved(shutdown, app_for_main, monkeypatch, tmp_path):
    exit_code = run_main(shutdown, monkeypatch, "--login-banner", str(tmp_path / "missing" / "login.png"))

    assert exit_code == 1


def test_main_saves_the_safe_screen_for_screenshot_safe(shutdown, app_for_main, monkeypatch, tmp_path):
    path = str(tmp_path / "safe.png")

    exit_code = run_main(shutdown, monkeypatch, "--screenshot-safe", path)

    assert (exit_code, QImage(path).size().toTuple()) == (0, (1280, 720))


def answer_modal_dialog(accept, choose_radio=None):
    def answer():
        dialog = next(widget for widget in QApplication.topLevelWidgets() if widget.isVisible() and widget.isModal())
        if choose_radio is not None:
            dialog.radios[choose_radio].setChecked(True)
        dialog.accept() if accept else dialog.reject()

    QTimer.singleShot(200, answer)


def test_main_logs_off_when_the_log_off_question_is_confirmed(shutdown, app_for_main, monkeypatch, path_with, capsys):
    path_with("gdbus")
    answer_modal_dialog(accept=True)

    exit_code = run_main(shutdown, monkeypatch, "--log-off", "--dry-run")

    assert (exit_code, capsys.readouterr().out) == (
        0,
        "dry-run, would run: gdbus " + " ".join(shutdown.dbus_caller()[1:]) + " org.kde.Shutdown.logout\n",
    )


def test_main_runs_nothing_when_shut_down_is_cancelled(shutdown, app_for_main, monkeypatch, capsys):
    answer_modal_dialog(accept=False)

    exit_code = run_main(shutdown, monkeypatch, "--dry-run")

    assert (exit_code, capsys.readouterr().out) == (0, "")


def test_main_opens_konsole_when_dos_mode_is_chosen(shutdown, app_for_main, monkeypatch, capsys):
    answer_modal_dialog(accept=True, choose_radio=2)

    exit_code = run_main(shutdown, monkeypatch, "--dry-run")

    assert (exit_code, capsys.readouterr().out) == (0, "dry-run, would run: konsole\n")


def test_main_shows_the_safe_screen_then_powers_off_when_shut_down_is_chosen(
    shutdown, app_for_main, monkeypatch, path_with, capsys
):
    path_with()
    answer_modal_dialog(accept=True)
    QTimer.singleShot(
        2900, lambda: next(w for w in QApplication.topLevelWidgets() if isinstance(w, shutdown.SafeScreen)).close()
    )

    exit_code = run_main(shutdown, monkeypatch, "--dry-run")

    assert (exit_code, capsys.readouterr().out) == (0, "dry-run, would run: systemctl poweroff\n")
