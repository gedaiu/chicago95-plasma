import signal
import subprocess
import sys
import textwrap
import time

from conftest import REPO

IDLE_APP = textwrap.dedent("""
    import sys
    sys.path.insert(0, {lib!r})
    import chicago95ui
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    {setup}
    QTimer.singleShot(0, lambda: print("ready", flush=True))
    sys.exit(app.exec())
""")


def run_idle_app_and_send_sigterm(setup):
    script = IDLE_APP.format(lib=str(REPO / "lib"), setup=setup)
    child = subprocess.Popen([sys.executable, "-c", script], stdout=subprocess.PIPE, text=True)
    child.stdout.readline()
    time.sleep(0.5)
    child.send_signal(signal.SIGTERM)
    try:
        return child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()
        return "still running 3 s after SIGTERM"


def test_idle_app_exits_with_code_0_on_sigterm_when_quit_on_signals_is_installed():
    assert run_idle_app_and_send_sigterm("wakeup = chicago95ui.quit_on_signals(app)") == 0


def test_idle_app_ignores_sigterm_with_a_handler_but_no_wakeup_slot():
    setup = "import signal; signal.signal(signal.SIGTERM, lambda *_: app.quit()); idle = QTimer(); idle.start(250)"

    assert run_idle_app_and_send_sigterm(setup) == "still running 3 s after SIGTERM"


import pytest


@pytest.mark.parametrize("scale, sharp", [(1.0, True), (2.0, True), (1.5, False), (1.25, False)])
def test_ui_font_is_drawn_unsmoothed_only_at_whole_scales(qt_app, monkeypatch, scale, sharp):
    """The pixel font's 11px grid lands on whole screen pixels at 1x and 2x only; at 1.5x it is left to
    fontconfig's smoothing (config/fontconfig/60-chicago95-pixel-font.conf)."""
    import chicago95ui
    from PySide6.QtGui import QFont
    monkeypatch.setattr(chicago95ui, "screen_scale", lambda: scale)
    font = chicago95ui.ui_font()
    assert (font.pixelSize(), bool(font.styleStrategy() & QFont.NoAntialias)) == (11, sharp)
