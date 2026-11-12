import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
from conftest import REPO

USER_BASE = subprocess.run(
    [sys.executable, "-c", "import site;print(site.USER_BASE)"], capture_output=True, text=True, check=True
).stdout.strip()
CHILD_SECONDS = 20
PID_FILE_SECONDS = 15


@pytest.fixture
def child_home(tmp_path):
    runtime_dir = Path(tempfile.mkdtemp(dir="/tmp"))
    home = tmp_path / "home"
    home.mkdir()
    (home / ".local/share/chicago95").mkdir(parents=True)
    (home / ".local/share/chicago95/clippy").symlink_to(REPO / "data/clippy")
    environment = {
        **os.environ,
        "SETUP_OS_RELEASE": "/dev/null",
        "HOME": str(home),
        "PYTHONUSERBASE": USER_BASE,
        "XDG_RUNTIME_DIR": str(runtime_dir),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_DATA_HOME": str(home / "data"),
        "QT_QPA_PLATFORM": "offscreen",
    }
    yield environment, runtime_dir
    for leftover in runtime_dir.iterdir():
        leftover.unlink()
    runtime_dir.rmdir()


def start(script, arguments, environment):
    return subprocess.Popen(
        [sys.executable, str(REPO / "bin" / script), *arguments],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def finish(process, timeout=CHILD_SECONDS):
    try:
        output, errors = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise
    return process.returncode, output, errors


def run_to_exit(script, arguments, environment):
    return finish(start(script, arguments, environment))


def terminate_once_running(script, arguments, environment, pid_file):
    process = start(script, arguments, environment)
    deadline = time.monotonic() + PID_FILE_SECONDS
    while not pid_file.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    time.sleep(0.5)
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
    return finish(process, timeout=10)


def test_sysprops_screenshot_exits_0_and_writes_the_png(child_home, tmp_path):
    png = tmp_path / "sysprops.png"

    code, _, _ = run_to_exit("chicago95-sysprops", ["--screenshot", str(png)], child_home[0])

    assert (code, png.stat().st_size > 0) == (0, True)


def test_shutdown_screenshot_exits_0_and_writes_the_png(child_home, tmp_path):
    png = tmp_path / "shutdown.png"

    code, _, _ = run_to_exit("chicago95-shutdown", ["--screenshot", str(png)], child_home[0])

    assert (code, png.stat().st_size > 0) == (0, True)

    code, _, _ = run_to_exit("chicago95-shutdown", ["--log-off", "--screenshot", str(png)], child_home[0])

    assert (code, png.stat().st_size > 0) == (0, True)


def test_shutdown_log_off_screenshot_exits_0_and_writes_the_png(child_home, tmp_path):
    png = tmp_path / "logoff.png"

    code, _, _ = run_to_exit("chicago95-shutdown", ["--log-off", "--screenshot", str(png)], child_home[0])

    assert (code, png.stat().st_size > 0) == (0, True)


def test_clippy_screenshot_exits_0_and_writes_the_png(child_home, tmp_path):
    png = tmp_path / "clippy.png"

    code, _, _ = run_to_exit("chicago95-clippy", ["--screenshot", str(png)], child_home[0])

    assert (code, png.stat().st_size > 0) == (0, True)


def test_clippy_once_greeting_plays_and_exits_0(child_home):
    code, _, _ = run_to_exit("chicago95-clippy", ["--mute", "--once", "Greeting"], child_home[0])

    assert code == 0


def test_clippy_daemon_exits_0_on_sigterm_and_removes_its_pid_file(child_home):
    environment, runtime_dir = child_home
    pid_file = runtime_dir / "chicago95-clippy.pid"

    code, _, _ = terminate_once_running("chicago95-clippy", ["--mute"], environment, pid_file)

    assert (code, pid_file.exists()) == (0, False)


def test_startmenu_root_height_prints_a_number_and_exits_0(child_home):
    code, output, _ = run_to_exit("chicago95-startmenu", ["--root-height"], child_home[0])

    assert (code, output.strip().isdigit()) == (0, True)


def test_startmenu_daemon_exits_0_on_sigterm_and_removes_its_pid_file(child_home):
    environment, runtime_dir = child_home
    pid_file = runtime_dir / "chicago95-startmenu.pid"

    code, _, _ = terminate_once_running("chicago95-startmenu", ["--daemon"], environment, pid_file)

    assert (code, pid_file.exists()) == (0, False)


def test_startmenu_second_launch_signals_the_running_one_and_exits_0(child_home):
    environment, runtime_dir = child_home
    pid_file = runtime_dir / "chicago95-startmenu.pid"
    first = start("chicago95-startmenu", ["--daemon"], environment)
    deadline = time.monotonic() + PID_FILE_SECONDS
    while not pid_file.exists() and first.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    time.sleep(0.5)

    second_code, _, _ = run_to_exit("chicago95-startmenu", [], environment)
    first.send_signal(signal.SIGTERM)

    assert (second_code, finish(first, timeout=10)[0]) == (0, 0)


def test_startmenu_shown_at_launch_exits_0_on_sigterm(child_home):
    environment, runtime_dir = child_home
    pid_file = runtime_dir / "chicago95-startmenu.pid"

    code, _, _ = terminate_once_running("chicago95-startmenu", [], environment, pid_file)

    assert (code, pid_file.exists()) == (0, False)
