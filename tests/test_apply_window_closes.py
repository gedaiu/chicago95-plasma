import subprocess

from conftest import REPO, load_script
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

CONTROL_PANEL = load_script("chicago95-control-panel")
WINDOW_STAYS_OPEN_FOR_MILLISECONDS = 5000


def run_window_until_it_closes_or_the_watchdog_fires(qt_app, command):
    """True when the window closed by itself; a window still open after the watchdog delay is closed and reported."""
    watchdog_fired = []

    def close_the_stuck_window():
        watchdog_fired.append(True)
        QApplication.activeModalWidget().reject()

    watchdog = QTimer()
    watchdog.setSingleShot(True)
    watchdog.timeout.connect(close_the_stuck_window)
    watchdog.start(WINDOW_STAYS_OPEN_FOR_MILLISECONDS)
    CONTROL_PANEL.run_setup_in_background(None, command)
    watchdog.stop()
    return not watchdog_fired


def without_the_systemd_scope(command):
    return [argument for argument in command if argument not in CONTROL_PANEL.OWN_SCOPE]


def a_checkout_whose_install_sh_exits_with(tmp_path, exit_code):
    git = ["git", "-c", "user.name=test", "-c", "user.email=test@example.com"]
    origin, work, checkout = tmp_path / "origin.git", tmp_path / "work", tmp_path / "checkout"
    subprocess.run([*git, "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True)
    subprocess.run([*git, "clone", str(origin), str(work)], check=True, capture_output=True)
    (work / "install.sh").write_text(f'#!/bin/sh\necho "Setup ran with: $*"\nexit {exit_code}\n')
    (work / "install.sh").chmod(0o755)
    subprocess.run([*git, "-C", str(work), "add", "."], check=True, capture_output=True)
    subprocess.run([*git, "-C", str(work), "commit", "-m", "setup"], check=True, capture_output=True)
    subprocess.run([*git, "-C", str(work), "push", "origin", "HEAD:main"], check=True, capture_output=True)
    subprocess.run([*git, "clone", str(origin), str(checkout)], check=True, capture_output=True)
    return checkout


def test_applying_closes_the_window_by_itself_when_setup_finishes(qt_app, tmp_path):
    settings_path = tmp_path / "setup.conf"
    CONTROL_PANEL.write_settings(settings_path, {"REPO": str(REPO)})
    command = without_the_systemd_scope(CONTROL_PANEL.setup_command(REPO, settings_path, ["base"]))

    closed_by_itself = run_window_until_it_closes_or_the_watchdog_fires(qt_app, ["setsid", "-w", *command, "--dry-run"])

    assert closed_by_itself is True


def test_installing_an_update_closes_the_window_by_itself_when_setup_finishes(qt_app, tmp_path):
    checkout = a_checkout_whose_install_sh_exits_with(tmp_path, 0)
    command = without_the_systemd_scope(CONTROL_PANEL.update_command(str(checkout), tmp_path / "setup.conf", ["look"]))

    closed_by_itself = run_window_until_it_closes_or_the_watchdog_fires(qt_app, command)

    assert closed_by_itself is True


def test_installing_an_update_whose_setup_fails_keeps_the_window_open_to_show_why(qt_app, tmp_path):
    checkout = a_checkout_whose_install_sh_exits_with(tmp_path, 3)
    command = without_the_systemd_scope(CONTROL_PANEL.update_command(str(checkout), tmp_path / "setup.conf", ["look"]))

    closed_by_itself = run_window_until_it_closes_or_the_watchdog_fires(qt_app, command)

    assert closed_by_itself is False
