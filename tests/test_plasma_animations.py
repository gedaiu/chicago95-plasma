"""Animation choices applied by Setup's animations step in a real Plasma session (tests/plasma_session.py): KWin
loads the title bar zoom without a script error and drops the effects of events turned off."""

import shutil
import subprocess

import numpy as np
import pytest
from conftest import needs_ui_font
from plasma_session import missing_programs

pytestmark = [
    needs_ui_font,
    pytest.mark.skipif(bool(missing_programs()), reason=f"needs {', '.join(missing_programs())}"),
]

CHOSEN = (("ANIM_MINIMIZE", "zoom"), ("ANIM_MAXIMIZE", "zoom"), ("ANIM_WINDOWS", "none"), ("ANIM_SPEED", "1"))


@pytest.fixture(scope="module")
def session(desktops):
    return desktops("1998", settings=CHOSEN).info


def loaded(session):
    return {name.strip(" '\"()<>[],") for name in session["loaded_effects"].replace(",", " ").split()}


def test_kwin_loads_the_title_bar_zoom_and_drops_the_window_open_effect_turned_off(session):
    assert ("chicago95zoom" in loaded(session), "scale" in loaded(session)) == (True, False)


def test_the_title_bar_zoom_runs_without_a_script_error(session):
    assert [line for line in session["kwin_log"].splitlines() if "chicago95zoom" in line] == []


@pytest.mark.skipif(
    any(not shutil.which(command) for command in ("pipewire", "wireplumber", "ffmpeg")),
    reason="requires PipeWire, WirePlumber and FFmpeg",
)
@pytest.mark.parametrize("scale", [1, 1.5])
def test_luna_zoom_moves_the_title_strip_independently_of_the_client(desktops, tmp_path, scale):
    video = tmp_path / "luna-window-motion.webm"
    screen = desktops(
        "luna",
        screen=(1024, 768),
        scale=scale,
        launchers=0,
        components=["background"],
        settings=[*CHOSEN, ("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", "#005786")],
        windows=[("Luna motion", "qt", (160, 150, 759, 489))],
        pointer_steps=[
            f"record:{video}",
            "wait:1",
            "move:698,166",
            "wait:0.2",
            "click:left",
            "wait:1",
            "move:145,752",
            "wait:0.2",
            "click:left",
            "wait:1",
            "move:698,166",
            "wait:0.2",
            "click:left",
            "wait:1",
            "move:145,752",
            "wait:0.2",
            "click:left",
            "wait:1",
        ],
    )
    script_messages = [
        line for line in screen.info["kwin_log"].splitlines()
        if "chicago95zoom" in line or "Luna title strip" in line
    ]
    assert "chicago95zoom" in loaded(screen.info), script_messages
    assert not script_messages
    pixels = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(video),
            "-vf",
            "scale=128:96:flags=area",
            "-fps_mode",
            "passthrough",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        timeout=30,
    )
    frames = np.frombuffer(pixels, np.uint8).reshape(-1, 96, 128, 3)
    # Count the pale client inside its settled rectangle and find the blue
    # title strip below its resting position and above the taskbar.
    area = np.all(frames[:, 24:58, 24:92] > (185, 170, 150), axis=-1).sum(axis=(1, 2))
    resting_area = np.median(area[:10])
    assert resting_area > 400
    _, green, blue = frames[:, 25:91, 5:96].astype(np.int16).transpose(3, 0, 1, 2)
    blue_width = ((blue > 175) & (blue - green > 46)).sum(axis=2)
    strip = blue_width.max(axis=1) >= 12
    rows = blue_width.argmax(axis=1)
    minimize = rows[strip & (area > resting_area * 0.85)]
    restore = rows[strip & (area < 14)]
    assert minimize.size and np.ptp(minimize) >= 25, "caption must travel over the stationary client"
    assert restore.size and np.ptp(restore) >= 25, "caption must travel before the client appears"
