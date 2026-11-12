import os

from PySide6.QtWidgets import QDialog, QLabel

GDBUS_PREFIX = ["gdbus", "call", "--session", "--dest", "org.kde.Shutdown", "--object-path", "/Shutdown", "--method"]


def test_dbus_caller_returns_gdbus_prefix_when_gdbus_is_installed(shutdown, path_with):
    path_with("gdbus", "qdbus6")

    assert shutdown.dbus_caller() == GDBUS_PREFIX


def test_dbus_caller_returns_qdbus6_prefix_when_only_qdbus6_is_installed(shutdown, path_with):
    path_with("qdbus6")

    assert shutdown.dbus_caller() == ["qdbus6", "org.kde.Shutdown", "/Shutdown"]


def test_dbus_caller_returns_none_when_no_dbus_tool_is_installed(shutdown, path_with):
    path_with()

    assert shutdown.dbus_caller() is None


def test_log_off_command_calls_kde_logout_through_gdbus(shutdown):
    assert shutdown.shutdown_command(shutdown.LOG_OFF, GDBUS_PREFIX) == GDBUS_PREFIX + ["org.kde.Shutdown.logout"]


def test_log_off_command_terminates_the_login_session_without_dbus(shutdown):
    session_id = os.environ.get("XDG_SESSION_ID", "self")

    assert shutdown.shutdown_command(shutdown.LOG_OFF) == ["loginctl", "terminate-session", session_id]


def test_shut_down_and_restart_commands_call_kde_through_gdbus(shutdown):
    commands = [shutdown.shutdown_command(choice, GDBUS_PREFIX) for choice in (shutdown.SHUT_DOWN, shutdown.RESTART)]

    assert commands == [
        GDBUS_PREFIX + ["org.kde.Shutdown.logoutAndShutdown"],
        GDBUS_PREFIX + ["org.kde.Shutdown.logoutAndReboot"],
    ]


def test_dos_mode_command_opens_konsole(shutdown):
    assert shutdown.shutdown_command(shutdown.DOS_MODE, GDBUS_PREFIX) == ["konsole"]


def test_log_off_prints_gdbus_logout_on_dry_run_when_log_off_is_chosen(shutdown, capsys):
    shutdown.log_off(shutdown.LOG_OFF, True, GDBUS_PREFIX)

    assert capsys.readouterr().out == "dry-run, would run: " + " ".join(GDBUS_PREFIX) + " org.kde.Shutdown.logout\n"


def test_log_off_runs_nothing_when_cancelled(shutdown, capsys):
    shutdown.log_off(None, True, GDBUS_PREFIX)

    assert capsys.readouterr().out == ""


def test_log_off_dialog_asks_whether_to_log_off_and_names_the_os_in_its_title(shutdown, qt_app):
    dialog = shutdown.LogOffDialog({"osName": "Windows 98"})
    texts = [label.text() for label in dialog.findChildren(QLabel) if label.text()]

    assert (dialog.windowTitle(), texts) == ("Log Off Windows", ["Are you sure you want to log off?"])


def test_log_off_dialog_is_accepted_by_yes(shutdown, qt_app):
    dialog = shutdown.LogOffDialog()
    button(dialog, "&Yes").click()

    assert dialog.result() == QDialog.Accepted


def test_log_off_dialog_is_rejected_by_no(shutdown, qt_app):
    dialog = shutdown.LogOffDialog()
    button(dialog, "&No").click()

    assert dialog.result() == QDialog.Rejected


def test_shut_down_dialog_records_log_off_choice_when_its_radio_is_checked(shutdown, qt_app):
    dialog = shutdown.ShutDownDialog()
    dialog.radios[shutdown.LOG_OFF].setChecked(True)
    button(dialog, "&Yes").click()

    assert (dialog.result(), dialog.choice) == (QDialog.Accepted, shutdown.LOG_OFF)


def test_shut_down_dialog_defaults_to_shut_down_choice(shutdown, qt_app):
    dialog = shutdown.ShutDownDialog()
    button(dialog, "&Yes").click()

    assert dialog.choice == shutdown.SHUT_DOWN


def button(dialog, text):
    from PySide6.QtWidgets import QPushButton

    return next(push for push in dialog.findChildren(QPushButton) if push.text() == text)


def test_os_name_is_the_banner_text_before_its_first_digit(shutdown):
    names = [
        shutdown.os_name({"bannerText": text})
        for text in ("Windows2000", "Windows2026", "Windows 2000 Professional", "Fedora 44", "Linux", "95 Plus")
    ]
    assert names == ["Windows", "Windows", "Windows", "Fedora", "Linux", "95 Plus"]


def test_chosen_sound_theme_reads_the_sounds_group_of_kdeglobals(shutdown, tmp_path):
    kdeglobals = tmp_path / "kdeglobals"
    kdeglobals.write_text("[General]\nTheme=Ignored\n\n[Sounds]\nEnable=true\nTheme=Windows98\n")

    assert shutdown.chosen_sound_theme(str(kdeglobals)) == "Windows98"


def test_chosen_sound_theme_is_chicago95_without_kdeglobals(shutdown, tmp_path):
    assert shutdown.chosen_sound_theme(str(tmp_path / "missing")) == "Chicago95"


def test_shutdown_sound_comes_from_the_chosen_theme(shutdown, tmp_path, monkeypatch):
    for theme in ("Chicago95", "Windows2000"):
        (tmp_path / theme / "stereo").mkdir(parents=True)
        (tmp_path / theme / "stereo/system-shutdown.ogg").touch()
    monkeypatch.setattr(shutdown, "SOUND_ROOTS", (str(tmp_path),))

    assert shutdown.shutdown_sound_file("Windows2000") == str(tmp_path / "Windows2000/stereo/system-shutdown.ogg")


def test_shutdown_sound_falls_back_to_chicago95_when_the_theme_has_none(shutdown, tmp_path, monkeypatch):
    (tmp_path / "Chicago95/stereo").mkdir(parents=True)
    (tmp_path / "Chicago95/stereo/system-shutdown.wav").touch()
    (tmp_path / "Plus98-Leonardo/stereo").mkdir(parents=True)
    monkeypatch.setattr(shutdown, "SOUND_ROOTS", (str(tmp_path),))

    assert shutdown.shutdown_sound_file("Plus98-Leonardo") == str(tmp_path / "Chicago95/stereo/system-shutdown.wav")
