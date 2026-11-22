"""Time real window transitions in KWin against the displayed Windows 7 SP1 frames."""

import itertools
import shutil
import subprocess

import numpy as np
import pytest
from conftest import REPO
from PIL import Image
from plasma_session import missing_programs
from test_aero_caption_motion import crossing_time

TOOLS = ("ffmpeg", "ffprobe", "pipewire", "wireplumber")


def original(action):
    stem = REPO / "tests/references" / f"win7-sp1-window-{action}-motion"
    sheet = np.asarray(Image.open(stem.with_suffix(".png")))
    times = np.loadtxt(stem.with_suffix(".txt"))
    trials = sheet.reshape(3, 12, 24, 10, 32, 3).transpose(0, 1, 3, 2, 4, 5).reshape(3, 120, 24, 32, 3)
    return [
        [crossing_time(f[start:end, :22], t[start:end]) for f, t in zip(trials, times, strict=True)]
        for start, end in ((10, 60), (65, 115))
    ]


def video_frames(path):
    pts = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "frame=best_effort_timestamp_time",
            "-of",
            "csv=p=0",
            str(path),
        ],
        text=True,
    )
    times = 1000 * np.array([float(line.split(",")[0]) for line in pts.splitlines() if line.strip()])
    raw = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            "scale=32:24:flags=area",
            "-fps_mode",
            "passthrough",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ]
    )
    return np.frombuffer(raw, np.uint8).reshape(len(times), 24, 32, 3)[:, :22], times


def settled_frames(frames, times):
    # The light client covers half the blue desktop when restored, and fills it when maximized.
    coverage = (frames[:, :, :, 0] > 155).mean(axis=(1, 2))
    states = np.select(
        [coverage > 0.85, (coverage > 0.4) & (coverage < 0.65), coverage < 0.06],
        ["maximized", "normal", "minimized"],
        default="moving",
    )
    result = []
    for state, group in itertools.groupby(range(len(times)), key=lambda i: states[i]):
        indices = list(group)
        if state != "moving" and times[indices[-1]] - times[indices[0]] > 250:
            if not result or result[-1][0] != state:
                result.append((state, indices[len(indices) // 2]))
    return result


@pytest.mark.skipif(
    bool(missing_programs()) or any(not shutil.which(t) for t in TOOLS),
    reason="requires nested KWin, Spectacle, PipeWire and FFmpeg",
)
def test_aero_window_transitions_match_sp1(desktops, tmp_path):
    output = tmp_path / "window-motion.webm"
    desktop = desktops(
        "luna",
        screen=(1024, 768),
        launchers=0,
        components=["background"],
        settings=[("LOOK", "aero"), ("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", "#215f9b")],
        windows=[("Window motion", "qt", (100, 100, 867, 627))],
        pointer_steps=[
            f"record:{output}",
            "move:920,400",
            "click:left",
            "wait:0.5",
            "move:700,109",
            "click:left",
            "wait:3",
            "move:799,109",
            "click:left",
            "wait:1",
            "move:958,10",
            "click:left",
            "wait:1",
            "move:770,109",
            "click:left",
            "wait:1",
            "move:85,748",
            "click:left",
            "wait:1",
        ],
    )
    assert "'chicago95aerominimize'" in desktop.info["loaded_effects"]
    frames, times = video_frames(output)
    settled = settled_frames(frames, times)
    assert [state for state, _ in settled] == ["normal", "maximized", "normal", "minimized", "normal"]
    for (start, end), native in zip(
        itertools.pairwise(i for _, i in settled), original("maximize") + original("minimize"), strict=True
    ):
        duration = crossing_time(frames[start:end], times[start:end])
        # Quantization at the two capture rates can shift the crossings by one frame each.
        if max(native):
            assert duration > 0, "minimize and restore must show intermediate frames"
        tolerance = 50 if max(native) else 34
        assert min(native) - tolerance <= duration <= max(native) + tolerance, (duration, native)
