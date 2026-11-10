import fcntl
import os
import pty
import struct
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
