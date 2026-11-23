"""Animation choices applied by Setup's animations step in a real Plasma session (tests/plasma_session.py): KWin
loads the title bar zoom without a script error and drops the effects of events turned off."""

import json
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
CLASSIC_SPEED_LIMITS = {"1995": (3.8, 5.0), "1998": (2.6, 3.4)}


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
    any(not shutil.which(command) for command in ("pipewire", "wireplumber", "ffmpeg", "ffprobe")),
    reason="requires PipeWire, WirePlumber and FFmpeg",
)
@pytest.mark.parametrize(
    ("look", "scale", "minimize_button"),
    [
        ("luna", 1, "698,166"),
        ("luna", 1.5, "698,166"),
        ("1995", 1.25, "711,163"),
        ("1998", 1, "711,163"),
        ("1998", 1.25, "711,163"),
    ],
)
def test_window_zoom_moves_the_title_strip_independently_of_the_client(desktops, tmp_path, look, scale, minimize_button):
    video = tmp_path / f"{look}-window-motion.webm"
    screen = desktops(
        look,
        screen=(1024, 768),
        scale=scale,
        launchers=0,
        components=["background"],
        settings=[*CHOSEN, ("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", "#008080")],
        windows=[("Caption motion", "qt", (160, 150, 759, 489))],
        pointer_steps=[
            f"record:{video}",
            "wait:1",
            f"move:{minimize_button}",
            "wait:0.2",
            "click:left",
            "wait:1",
            "move:145,752",
            "wait:0.2",
            "click:left",
            "wait:1",
            f"move:{minimize_button}",
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
        if "chicago95zoom" in line or "title strip shader" in line
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
    colour = frames[:, 25:91, 5:96].astype(np.int16)
    red, green, blue = colour.transpose(3, 0, 1, 2)
    blue_width = ((red < 125) & (blue > 95) & (blue - green > 40)).sum(axis=2)
    minimize_rows = blue_width.argmax(axis=1)
    minimizing = (blue_width.max(axis=1) >= 12) & (area > resting_area * 0.85)
    # A restoring caption may still have its inactive colours. Find it
    # against the empty desktop separately from the stationary client.
    departure = np.abs(colour - (0, 128, 128)).max(axis=3)
    restore_width = (departure > 65).sum(axis=2)
    restore_rows = restore_width.argmax(axis=1)
    restoring = (area < resting_area * 0.1) & (restore_width.max(axis=1) >= 12)
    minimize, restore = minimize_rows[minimizing], restore_rows[restoring]
    assert minimize.size and np.ptp(minimize) >= 25, "caption must travel over the stationary client"
    assert restore.size and np.ptp(restore) >= 25, "caption must travel before the client appears"
    if look in CLASSIC_SPEED_LIMITS:
        timing = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "frame=best_effort_timestamp_time", "-of", "json", str(video)],
            timeout=30,
        )
        times = np.asarray([float(frame["best_effort_timestamp_time"]) * 1000 for frame in json.loads(timing)["frames"]])
        low, high = CLASSIC_SPEED_LIMITS[look]
        for rows, moving, direction in ((minimize_rows, minimizing, 1), (restore_rows, restoring, -1)):
            speeds = [direction * speed for speed in caption_speeds(rows, moving, times, scale)]
            assert any(low <= speed <= high for speed in speeds), speeds


def caption_speeds(rows, moving, times, scale):
    indices = np.flatnonzero(moving)
    # Ignore the pauses between actions and isolated flickers from the capture.
    for sequence in np.split(indices, np.flatnonzero(np.diff(indices) > 3) + 1):
        if sequence.size >= 4 and np.ptp(rows[sequence]) >= 25:
            # The video was reduced from 1024×768 logical pixels to 128×96.
            yield np.polyfit(times[sequence], rows[sequence] * (8 * scale), 1)[0]
