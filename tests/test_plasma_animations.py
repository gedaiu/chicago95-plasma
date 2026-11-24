"""Animation choices applied by Setup's animations step in a real Plasma session (tests/plasma_session.py): KWin
loads the title bar zoom without a script error and drops the effects of events turned off."""

import json
import shutil

import pytest
from conftest import needs_ui_font
from legacy_motion import (
    CHOSEN,
    check_maximize_and_restore,
    check_title_strip_speed,
    loaded,
    measure_title_strip,
)
from plasma_session import missing_programs
from reference import REFERENCES, theme_references

pytestmark = [
    needs_ui_font,
    pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}"),
]

TITLE_STRIPS = {
    metadata["look"]: json.loads((folder / path).read_text())
    for folder, metadata in theme_references(REFERENCES)
    if (path := metadata.get("motion", {}).get("title_strip"))
}


@pytest.fixture(scope="module")
def session(desktops):
    return desktops("1998", settings=CHOSEN).info


def test_kwin_loads_the_title_bar_zoom_and_drops_the_window_open_effect_turned_off(session):
    assert ("chicago95zoom" in loaded(session), "scale" in loaded(session)) == (True, False)


def test_the_title_bar_zoom_runs_without_a_script_error(session):
    assert [line for line in session["kwin_log"].splitlines() if "chicago95zoom" in line] == []


@pytest.mark.skipif(
    any(not shutil.which(command) for command in ("pipewire", "wireplumber", "ffmpeg", "ffprobe")),
    reason="requires PipeWire, WirePlumber and FFmpeg",
)
@pytest.mark.parametrize(
    ("look", "scale", "minimize_button"),
    [(look, scale, spec["minimize_button"]) for look, spec in TITLE_STRIPS.items() for scale in spec["render_scales"]],
)
def test_window_zoom_moves_the_title_strip_independently_of_the_client(desktops, tmp_path, look, scale, minimize_button):
    video = tmp_path / f"{look}-window-motion.webm"
    measured = measure_title_strip(desktops, video, look, scale, minimize_button, classic=look != "luna")
    check_title_strip_speed(measured, TITLE_STRIPS[look])


@pytest.mark.skipif(
    any(not shutil.which(command) for command in ("pipewire", "wireplumber", "ffmpeg", "ffprobe")),
    reason="requires PipeWire, WirePlumber, FFmpeg and FFprobe",
)
@pytest.mark.parametrize(
    ("look", "maximize_button", "restore_button"),
    [
        (look, buttons["normal"], buttons["maximized"])
        for look, spec in TITLE_STRIPS.items()
        if (buttons := spec.get("maximize_buttons"))
    ],
)
def test_maximize_and_restore_keep_the_client_visible(desktops, tmp_path, look, maximize_button, restore_button):
    video = tmp_path / f"{look}-maximize.webm"
    check_maximize_and_restore(desktops, video, look, maximize_button, restore_button)
