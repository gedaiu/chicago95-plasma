"""Clippy tells, once a day, when a newer Chicago95 for Plasma is published (lib/chicago95update.py)."""

import chicago95update
import pytest
from conftest import REPO, load_script
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap

OLD, NEW = "a" * 40, "b" * 40


@pytest.fixture(scope="session")
def clippy():
    return load_script("chicago95-clippy")


def window_of(clippy, qt_app):
    animations = clippy.parse_agent_js((REPO / "data/clippy/agent.js").read_text())
    sprites = clippy.SpriteSheet(QPixmap(str(REPO / "data/clippy/map.png")), QSize(124, 93))
    return clippy.ClippyWindow(animations, sprites, clippy.SoundPlayer({}, True), qt_app.font())


def test_an_available_update_opens_a_balloon_naming_both_versions_and_the_control_panel_page(clippy, qt_app):
    window = window_of(clippy, qt_app)
    window.announce_update(chicago95update.check_result(OLD, NEW, chicago95update.utc_now()))

    assert (window.balloon.text, window.playback.animation is window.animations["GetAttention"]) == (
        "A newer Chicago95 for Plasma is available (bbbbbbb; you have aaaaaaa).\n\n"
        "Open Control Panel, Updates to install it.",
        True,
    )


def test_the_daily_check_in_main_announces_only_an_available_update(clippy):
    announced = []
    schedule = clippy.update_schedule(announced.append)
    schedule.handle(chicago95update.check_result(OLD, OLD, chicago95update.utc_now()))
    schedule.handle(chicago95update.check_result(OLD, NEW, chicago95update.utc_now()))

    assert [result["latest"] for result in announced] == [NEW]
