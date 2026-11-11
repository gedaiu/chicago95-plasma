"""bin/chicago95-screensaver beyond its catalogue: finding the hacks, the pid file, the KWin placement, the
input catcher and the run loops. Hacks and gdbus are fake shell scripts on a temporary PATH, so nothing real
is started and the live session is never touched."""

import os
import signal
import subprocess
import sys

import pytest
from conftest import REPO, load_script
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

SCRIPT = REPO / "bin/chicago95-screensaver"
EVENT_LOOP_DEADLINE_MS = 6000
CHILD_FLAG = "CHICAGO95_EVENT_LOOP_TESTS_IN_CHILD"
EVENT_LOOP_TESTS = "run_saver or run_blank or main_runs"
in_a_process_of_its_own = pytest.mark.skipif(
    not os.environ.get(CHILD_FLAG), reason="runs in a process of its own, started by the test that selects it"
)


@pytest.fixture(scope="session")
def screensaver():
    return load_script("chicago95-screensaver")


@pytest.fixture(autouse=True)
def keep_signal_handlers():
    saved = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
    yield
    for number, handler in saved.items():
        signal.signal(number, handler)


@pytest.fixture
def runtime(tmp_path, monkeypatch, screensaver):
    folder = tmp_path / "runtime"
    folder.mkdir()
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(folder))
    monkeypatch.setattr(screensaver, "PID_FILE", folder / "chicago95-screensaver.pid")
    return folder


def fake_program(folder, name, body):
    folder.mkdir(exist_ok=True)
    path = folder / name
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)
    return path


@pytest.fixture
def fake_gdbus(tmp_path, monkeypatch):
    log = tmp_path / "gdbus.log"
    fake_program(tmp_path / "bin", "gdbus", f'echo "$@" >> {log}')
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:{os.environ['PATH']}")
    return log


def mouse_move(x, y):
    return QMouseEvent(QEvent.MouseMove, QPointF(x, y), QPointF(x, y), Qt.NoButton, Qt.NoButton, Qt.NoModifier)


def run_event_loop_with(app, action, delay_ms=100):
    QTimer.singleShot(delay_ms, action)
    QTimer.singleShot(EVENT_LOOP_DEADLINE_MS, app.quit)


def find_catcher():
    return next(w for w in QApplication.topLevelWidgets() if w.windowTitle() == "chicago95-screensaver")


def test_hack_dir_is_the_first_existing_directory_of_the_list(screensaver, tmp_path, monkeypatch):
    monkeypatch.setattr(screensaver, "HACK_DIRS", (str(tmp_path / "missing"), str(tmp_path)))

    assert screensaver.hack_dir() == tmp_path


def test_hack_dir_is_none_when_no_listed_directory_exists(screensaver, tmp_path, monkeypatch):
    monkeypatch.setattr(screensaver, "HACK_DIRS", (str(tmp_path / "missing"),))

    assert screensaver.hack_dir() is None


def test_only_the_blank_screen_is_installed_without_a_hack_directory(screensaver):
    assert screensaver.installed_savers(None) == {"blank": "Blank Screen"}


def test_the_blank_screen_has_no_command(screensaver, tmp_path):
    assert screensaver.saver_command("blank", tmp_path) is None


def test_already_running_is_true_when_the_pid_file_names_a_live_process(screensaver, runtime):
    screensaver.PID_FILE.write_text(str(os.getpid()))

    assert screensaver.already_running() is True


@pytest.mark.parametrize("content", [None, "not a number", "2147483646"], ids=["no file", "garbage", "dead pid"])
def test_already_running_is_false_when_the_pid_file_is(screensaver, runtime, content):
    if content is not None:
        screensaver.PID_FILE.write_text(content)

    assert screensaver.already_running() is False


def test_kwin_script_pins_both_windows_and_activates_the_catcher(screensaver):
    source = screensaver.kwin_script(111, 222)

    assert (
        "window.pid === 111 || window.pid === 222" in source,
        "window.pid === 222) workspace.activeWindow" in source,
    ) == (
        True,
        True,
    )


def test_run_kwin_script_writes_the_script_and_unloads_loads_and_starts_it(screensaver, runtime, fake_gdbus):
    screensaver.run_kwin_script("// placement")

    calls = fake_gdbus.read_text().splitlines()
    script_path = runtime / "chicago95-screensaver-kwin.js"
    name = f"chicago95-screensaver-{os.getpid()}"
    prefix = "call --session --dest org.kde.KWin --object-path /Scripting --method org.kde.kwin.Scripting"
    assert (script_path.read_text(), calls) == (
        "// placement",
        [f"{prefix}.unloadScript {name}", f"{prefix}.loadScript {script_path} {name}", f"{prefix}.start"],
    )


def test_catcher_ignores_input_until_armed(screensaver, qt_app):
    inputs = []
    catcher = screensaver.InputCatcher(lambda: inputs.append("input"))
    catcher.keyPressEvent(None)
    catcher.mousePressEvent(None)
    catcher.wheelEvent(None)

    assert inputs == []


def test_catcher_reports_key_click_and_wheel_once_armed(screensaver, qt_app):
    inputs = []
    catcher = screensaver.InputCatcher(lambda: inputs.append("input"))
    catcher.arm()
    catcher.keyPressEvent(None)
    catcher.mousePressEvent(None)
    catcher.wheelEvent(None)

    assert inputs == ["input"] * 3


def test_catcher_remembers_the_first_mouse_position_without_finishing(screensaver, qt_app):
    inputs = []
    catcher = screensaver.InputCatcher(lambda: inputs.append("input"))
    catcher.arm()
    catcher.mouseMoveEvent(mouse_move(10, 10))

    assert (inputs, catcher.first_position.x()) == ([], 10)


def test_catcher_restarts_the_reference_position_for_a_move_before_it_is_armed(screensaver, qt_app):
    inputs = []
    catcher = screensaver.InputCatcher(lambda: inputs.append("input"))
    catcher.mouseMoveEvent(mouse_move(10, 10))
    catcher.mouseMoveEvent(mouse_move(200, 200))

    assert (inputs, catcher.first_position.x()) == ([], 200)


def test_catcher_ignores_a_mouse_jitter_within_the_slack(screensaver, qt_app):
    inputs = []
    catcher = screensaver.InputCatcher(lambda: inputs.append("input"))
    catcher.arm()
    catcher.mouseMoveEvent(mouse_move(10, 10))
    catcher.mouseMoveEvent(mouse_move(12, 12))

    assert inputs == []


def test_catcher_finishes_on_a_mouse_move_beyond_the_slack(screensaver, qt_app):
    inputs = []
    catcher = screensaver.InputCatcher(lambda: inputs.append("input"))
    catcher.arm()
    catcher.mouseMoveEvent(mouse_move(10, 10))
    catcher.mouseMoveEvent(mouse_move(40, 10))

    assert inputs == ["input"]


@in_a_process_of_its_own
def test_run_saver_returns_when_the_hack_exits_and_places_the_windows(screensaver, qt_app, tmp_path, fake_gdbus):
    hack_log = tmp_path / "hack.log"
    hack = fake_program(tmp_path / "hacks", "pipes", f'echo "$@ $QT_QPA_PLATFORM $GDK_BACKEND" > {hack_log}')
    run_event_loop_with(qt_app, lambda: None)

    code = screensaver.run_saver(qt_app, [str(hack), "--speed", "3"])

    assert (code, hack_log.read_text(), "loadScript" in fake_gdbus.read_text()) == (0, "--speed 3 xcb x11\n", True)


@in_a_process_of_its_own
def test_run_saver_terminates_the_hack_when_input_arrives(screensaver, qt_app, tmp_path, fake_gdbus):
    pid_file = tmp_path / "hack.pid"
    hack = fake_program(tmp_path / "hacks", "pipes", f"echo $$ > {pid_file}\nexec sleep 30")

    def press_a_key():
        catcher = find_catcher()
        catcher.arm()
        catcher.keyPressEvent(None)

    run_event_loop_with(qt_app, press_a_key, delay_ms=300)
    code = screensaver.run_saver(qt_app, [str(hack)])
    hack_pid = int(pid_file.read_text())
    try:
        os.waitpid(hack_pid, 0)
    except ChildProcessError:
        pass

    assert (code, subprocess.run(["kill", "-0", str(hack_pid)], capture_output=True, check=False).returncode != 0) == (
        0,
        True,
    )


@in_a_process_of_its_own
def test_run_blank_quits_on_input(screensaver, qt_app):
    def press_a_key():
        catcher = find_catcher()
        catcher.arm()
        catcher.keyPressEvent(None)

    run_event_loop_with(qt_app, press_a_key)

    assert screensaver.run_blank(qt_app) == 0


def test_main_lists_the_installed_savers_in_catalogue_order(screensaver, tmp_path, monkeypatch, capsys):
    hacks = tmp_path / "hacks"
    for name in ("pipes", "qix"):
        fake_program(hacks, name, "")
    monkeypatch.setattr(screensaver, "HACK_DIRS", (str(hacks),))
    monkeypatch.setattr(sys, "argv", ["chicago95-screensaver", "--list"])

    assert (screensaver.main(), capsys.readouterr().out) == (
        0,
        "qix\tMystify Your Mind\nblank\tBlank Screen\npipes\t3D Pipes\n",
    )


def test_main_refuses_a_hack_that_is_not_installed(screensaver, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(screensaver, "HACK_DIRS", (str(tmp_path / "missing"),))
    monkeypatch.setattr(sys, "argv", ["chicago95-screensaver", "--hack", "pipes"])

    assert (screensaver.main(), capsys.readouterr().err) == (1, "pipes is not installed; installed: blank\n")


def test_main_does_nothing_when_a_saver_already_runs(screensaver, runtime, tmp_path, monkeypatch):
    screensaver.PID_FILE.write_text(str(os.getpid()))
    monkeypatch.setattr(screensaver, "HACK_DIRS", (str(tmp_path / "missing"),))
    monkeypatch.setattr(sys, "argv", ["chicago95-screensaver", "--hack", "blank"])

    assert (screensaver.main(), screensaver.PID_FILE.read_text()) == (0, str(os.getpid()))


@in_a_process_of_its_own
def test_main_runs_the_blank_screen_and_removes_its_pid_file(screensaver, runtime, qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(screensaver, "HACK_DIRS", (str(tmp_path / "missing"),))
    monkeypatch.setattr(sys, "argv", ["chicago95-screensaver", "--hack", "blank"])
    monkeypatch.setattr(screensaver.chicago95ui, "make_app", lambda _name: qt_app)
    pid_files_while_running = []

    def press_a_key():
        pid_files_while_running.append(screensaver.PID_FILE.read_text())
        catcher = find_catcher()
        catcher.arm()
        catcher.keyPressEvent(None)

    run_event_loop_with(qt_app, press_a_key)

    assert (screensaver.main(), pid_files_while_running, screensaver.PID_FILE.exists()) == (
        0,
        [str(os.getpid())],
        False,
    )


@in_a_process_of_its_own
def test_main_runs_the_hack_of_the_chosen_saver(screensaver, runtime, qt_app, tmp_path, fake_gdbus, monkeypatch):
    hacks = tmp_path / "hacks"
    hack_log = tmp_path / "hack.log"
    fake_program(hacks, "pipes", f'echo "$@" > {hack_log}')
    monkeypatch.setattr(screensaver, "HACK_DIRS", (str(hacks),))
    monkeypatch.setattr(sys, "argv", ["chicago95-screensaver", "--hack", "pipes"])
    monkeypatch.setattr(screensaver.chicago95ui, "make_app", lambda _name: qt_app)
    run_event_loop_with(qt_app, lambda: None)

    assert (screensaver.main(), hack_log.read_text()) == (0, "\n")


def test_script_run_directly_lists_savers_and_exits(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--list"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=dict(os.environ, HOME=str(tmp_path), XDG_RUNTIME_DIR=str(tmp_path), PYTHONUSERBASE=_user_base()),
    )

    assert (result.returncode, "blank\tBlank Screen" in result.stdout.splitlines()) == (0, True)


def _user_base():
    return subprocess.run(
        [sys.executable, "-m", "site", "--user-base"], capture_output=True, text=True, check=True
    ).stdout.strip()


def test_script_run_directly_exits_with_one_for_an_unknown_hack(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--hack", "no-such-saver"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=dict(os.environ, HOME=str(tmp_path), XDG_RUNTIME_DIR=str(tmp_path), PYTHONUSERBASE=_user_base()),
    )

    assert (result.returncode, result.stderr.startswith("no-such-saver is not installed; installed: ")) == (1, True)


def test_the_event_loop_tests_pass_in_a_process_of_their_own(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-k", EVENT_LOOP_TESTS, "-q", "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        env=dict(os.environ, **{CHILD_FLAG: "1"}, QT_QPA_PLATFORM="offscreen"),
        cwd=tmp_path,
    )

    assert (result.returncode, result.stdout.splitlines()[-1].split(", ")[0]) == (0, "5 passed")
