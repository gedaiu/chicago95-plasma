import signal
import subprocess
import sys
import textwrap
import time

import pytest
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


@pytest.mark.parametrize("scale, sharp", [(1.0, True), (2.0, True), (1.5, False), (1.25, False)])
def test_ui_font_is_drawn_unsmoothed_only_at_whole_scales(qt_app, monkeypatch, scale, sharp):
    """The pixel font's 11px grid lands on whole screen pixels at 1x and 2x only; at 1.5x it is left to
    fontconfig's smoothing (config/fontconfig/60-chicago95-pixel-font.conf)."""
    import chicago95ui
    from PySide6.QtGui import QFont

    monkeypatch.setattr(chicago95ui, "detect_scale", lambda: str(scale))
    chicago95ui.screen_scale.cache_clear()
    font = chicago95ui.ui_font()
    assert (font.pixelSize(), bool(font.styleStrategy() & QFont.NoAntialias)) == (11, sharp)


def test_screen_scale_is_the_compositors_not_qts_rounded_one(qt_app, monkeypatch):
    """Qt rounds a 1.5x Wayland screen up to 2: the font would be drawn unsmoothed off its grid."""
    import chicago95ui

    monkeypatch.setattr(chicago95ui, "detect_scale", lambda: "1.5")
    chicago95ui.screen_scale.cache_clear()
    assert chicago95ui.screen_scale() == 1.5


def test_ui_font_asks_for_smoothing_explicitly_off_whole_scales(qt_app, monkeypatch):
    """A font that leaves the choice open inherits the application font's, made at another scale."""
    import chicago95ui
    from PySide6.QtGui import QFont

    monkeypatch.setattr(chicago95ui, "detect_scale", lambda: "1.5")
    chicago95ui.screen_scale.cache_clear()
    assert bool(chicago95ui.ui_font().styleStrategy() & QFont.PreferAntialias)


def test_classic_dialog_paints_an_inactive_title_while_another_window_is_active(qt_app):
    """Only the active window's title is in the active colours (COLOR_ACTIVECAPTION); every other window's
    is in the inactive ones, and repaints when activation changes."""
    import chicago95ui
    from PySide6.QtWidgets import QWidget
    from reference import qimage_to_pil

    dialog = chicago95ui.ClassicDialog("Title", "1995", (200, 80))
    other = QWidget()
    scheme = chicago95ui.read_scheme()

    def title_colour():
        return qimage_to_pil(dialog.grab().toImage()).getpixel((150, 10))

    dialog.show()
    dialog.activateWindow()
    qt_app.processEvents()
    active = title_colour()
    other.show()
    other.activateWindow()
    qt_app.processEvents()
    inactive = title_colour()
    dialog.close()
    other.close()

    def as_rgb(colour):
        return (colour.red(), colour.green(), colour.blue())

    assert (active, inactive) == (as_rgb(scheme["title_active"]), as_rgb(scheme["title_inactive"]))
