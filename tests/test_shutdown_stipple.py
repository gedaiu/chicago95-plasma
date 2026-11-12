"""9x shutdown uses a screen-wide black checker, never desaturating the desktop."""
import pytest
from conftest import load_script
from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog


@pytest.fixture
def shutdown(qt_app):
    return load_script("chicago95-shutdown")


def test_stipple_is_alternating_opaque_black_and_transparent_pixels(shutdown, qt_app):
    overlay = shutdown.ShutdownStipple(qt_app.primaryScreen())
    overlay.resize(20, 20)
    image = overlay.grab().toImage()
    for y in range(20):
        for x in range(20):
            pixel = image.pixelColor(x, y)
            assert pixel.alpha() == (255 if (x + y) % 2 == 0 else 0)
            if pixel.alpha():
                assert pixel == QColor("black")
    overlay.close()


@pytest.mark.parametrize("style", ["1995", "1998", "2000", "2001"])
def test_only_9x_gets_backdrops_on_every_screen(shutdown, qt_app, style):
    dialog = shutdown.ShutDownDialog({"style": style})
    overlays = shutdown.shutdown_backdrops(dialog)
    assert len(overlays) == (len(qt_app.screens()) if style in ("1995", "1998") else 0)
    if overlays:
        assert dialog.windowHandle().transientParent() in [overlay.windowHandle() for overlay in overlays]
    for overlay in overlays:
        overlay.close()
    dialog.close()


@pytest.mark.parametrize("accepted", [False, True])
def test_backdrops_close_when_the_shutdown_dialog_finishes(shutdown, qt_app, monkeypatch, accepted):
    dialog = shutdown.ShutDownDialog({"style": "1998"})
    overlays = shutdown.shutdown_backdrops(dialog)
    monkeypatch.setattr(shutdown, "shutdown_backdrops", lambda _: overlays)
    QTimer.singleShot(0, lambda: dialog.done(QDialog.Accepted if accepted else QDialog.Rejected))
    assert shutdown.ask(dialog) == accepted
    assert all(not overlay.isVisible() for overlay in overlays)
    assert dialog.windowHandle().transientParent() is None
