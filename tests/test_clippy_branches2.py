import pytest
from conftest import REPO, load_script
from PySide6.QtCore import QEvent, QPointF, QSize, Qt
from PySide6.QtGui import QMouseEvent, QPixmap, QWindow


@pytest.fixture
def window(tmp_path, monkeypatch, qt_app):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    clippy = load_script("chicago95-clippy")
    animations = clippy.parse_agent_js((REPO / "data/clippy/agent.js").read_text())
    sprites = clippy.SpriteSheet(QPixmap(str(REPO / "data/clippy/map.png")), QSize(124, 93))
    clippy_window = clippy.ClippyWindow(animations, sprites, clippy.SoundPlayer({}, True), qt_app.font())
    clippy_window.show()
    yield clippy_window
    clippy_window.hide()


def test_left_press_hands_the_drag_to_the_compositor_when_system_move_starts(window, monkeypatch):
    monkeypatch.setattr(QWindow, "startSystemMove", lambda _self: True)
    press = QMouseEvent(
        QEvent.MouseButtonPress, QPointF(5, 5), QPointF(5, 5), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier
    )

    window.mousePressEvent(press)

    assert window.drag_offset is None
