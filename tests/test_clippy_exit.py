import pytest
from conftest import REPO, load_script
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap


@pytest.fixture
def clippy(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    return load_script("chicago95-clippy")


def window_of(clippy, qt_app):
    animations = clippy.parse_agent_js((REPO / "data/clippy/agent.js").read_text())
    sprites = clippy.SpriteSheet(QPixmap(str(REPO / "data/clippy/map.png")), QSize(124, 93))
    return clippy.ClippyWindow(animations, sprites, clippy.SoundPlayer({}, True), qt_app.font())


def test_finished_goodbye_closes_the_window_and_exits_with_code_0(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.show()
    window.exit_application()

    with pytest.raises(SystemExit) as exit_info:
        for _ in range(1000):
            window.advance_frame()

    assert (exit_info.value.code, window.isVisible()) == (0, False)
