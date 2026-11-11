import fcntl
import os
import pty
import struct
import subprocess
import termios
import time

from conftest import REPO

WAITING_SETUP_SCREEN = f"""
. {REPO}/setup/ui.sh
ui_init
ui_message "Welcome to Setup" "Press ENTER to continue."
echo "still running after Ctrl+C"
"""


def exit_code_after_ctrl_c(script):
    pid, terminal = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 25, 80, 0, 0))
        os.environ["TERM"] = "xterm-256color"
        os.execvp("bash", ["bash", "-c", script])
    os.set_blocking(terminal, False)
    time.sleep(0.5)
    os.write(terminal, b"\x03")
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        finished, status = os.waitpid(pid, os.WNOHANG)
        if finished:
            return os.waitstatus_to_exitcode(status)
        try:
            os.read(terminal, 65536)
        except OSError:
            pass
    os.kill(pid, 9)
    os.waitpid(pid, 0)
    return "still running 3 s after Ctrl+C"


def test_ctrl_c_on_a_setup_screen_exits_with_code_130():
    assert exit_code_after_ctrl_c(WAITING_SETUP_SCREEN) == 130


def run_with_typeahead(script, early, later, tmp_path):
    """Runs script in a terminal; early is typed before its prompt appears, later a second after."""
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    (stubs / "sudo").write_text('#!/bin/sh\n[ "$1" = -n ] && exit 1\nread -r password\n[ "$password" = secret ]\n')
    (stubs / "sudo").chmod(0o755)
    pid, terminal = pty.fork()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 25, 80, 0, 0))
        os.environ.update(TERM="xterm-256color", PATH=f"{stubs}:{os.environ['PATH']}")
        os.execvp("bash", ["bash", "-c", script])
    os.write(terminal, early)
    time.sleep(1.0)
    os.write(terminal, later)
    output, deadline = b"", time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            output += os.read(terminal, 65536)
        except OSError:
            break
    os.waitpid(pid, 0)
    return output.decode(errors="replace")


def test_password_prompt_ignores_enter_pressed_before_it_appeared(tmp_path):
    """An ENTER pressed while files were copying must not count as "skip" at the password prompt."""
    script = f"""
. {REPO}/setup/ui.sh
UI_PLAIN=1
sleep 0.3
ui_sudo "To change the login screen, Setup must write to a system folder." "sudo cp theme /usr/share/sddm/themes/" && echo GRANTED || echo SKIPPED
"""
    output = run_with_typeahead(script, b"\n\n", b"secret\n", tmp_path)
    assert "GRANTED" in output, output[-400:]


def test_reporting_two_thousand_copied_files_on_the_setup_screen_takes_under_three_seconds(tmp_path):
    """The icon sets alone are thousands of files: each is logged and shown, without starting programs."""
    script = f"""
. {REPO}/setup/ui.sh
REPO={REPO}; . {REPO}/setup/steps.sh
UI_PLAIN=0 UI_ROWS=25 UI_COLS=80 UI_ON_STEPS=1 SETUP_LOG={tmp_path}/setup.log TO_COPY=2000 COPIED=0
start=$EPOCHREALTIME
for i in $(seq 2000); do show_copy "$HOME/src/icons/apps/16/icon$i.png" "$HOME/.local/share/icons/apps/16/icon$i.png"; done >/dev/null
echo "seconds $(( (${{EPOCHREALTIME/./}} - ${{start/./}}) / 1000000 ))"
grep -c '^copied' {tmp_path}/setup.log
"""
    output = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=120,
        env={"PATH": os.environ["PATH"], "HOME": str(tmp_path), "TERM": "xterm-256color"},
    ).stdout.split()
    assert output[-1] == "2000" and int(output[-2]) < 3, output
