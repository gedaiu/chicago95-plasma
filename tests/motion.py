"""Render Aero transitions and measure them against presented Windows frames."""

import itertools
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

THEME = Path(__file__).resolve().parents[1] / "aero/aurorae"
TOOLS = ("dbus-monitor", "ffmpeg", "ffprobe", "pipewire", "pw-dump", "wireplumber")


def timing_result(action, duration, native, tolerance):
    return {
        "action": action,
        "rendered_ms": float(duration),
        "native_ms": [float(sample) for sample in native],
        "sampling_tolerance_ms": tolerance,
    }


def check_timing(measured, output=None):
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(measured, indent=2) + "\n")
    for row in measured:
        actual, native, tolerance = row["rendered_ms"], row["native_ms"], row["sampling_tolerance_ms"]
        assert min(native) - tolerance <= actual <= max(native) + tolerance, row


def crossing_time(frames, timestamps):
    """Time from first crossing 10% to first crossing 90% along the measured RGB change."""
    frames = np.asarray(frames, dtype=float)
    base = frames[0]
    difference = frames[-1] - base
    assert np.abs(difference).mean() > 4
    progress = ((frames - base) * difference).sum(axis=(1, 2, 3)) / np.square(difference).sum()
    return timestamps[np.flatnonzero(progress >= 0.9)[0]] - timestamps[np.flatnonzero(progress >= 0.1)[0]]


def caption_times(stem):
    with Image.open(stem.with_suffix(".png")) as image:
        sheet = np.array(image)
    timestamps = np.loadtxt(stem.with_suffix(".txt"))
    width = sheet.shape[1] // 10
    trials = sheet.reshape(3, 12, 25, 10, width, 3).transpose(0, 1, 3, 2, 4, 5).reshape(3, 120, 25, width, 3)
    return [
        [
            crossing_time(frames[start:end, 5:17, 3:-4], ts[start:end])
            for frames, ts in zip(trials, timestamps, strict=True)
        ]
        for start, end in ((12, 60), (66, 115))
    ]


def compare_caption_motion(action, width, timings):
    button = "close" if action == "focus" else action
    view = QQuickView()
    view.setColor(QColor("#528cb9"))
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(width, 20)
    view.setInitialProperties(
        {
            "artwork": str(THEME / "theme" / f"{button}.svg"),
            "activeWindow": True,
            "hovered": False,
            "held": False,
            "closeButton": button == "close",
        }
    )
    view.setSource(QUrl.fromLocalFile(str(THEME / "caption/contents/ui/CaptionFace.qml")))
    assert not view.errors()
    view.show()
    QTest.qWait(250)

    def sample():
        img = view.grabWindow().convertToFormat(QImage.Format_RGBA8888)
        data = np.frombuffer(img.constBits(), dtype=np.uint8).reshape(img.height(), img.bytesPerLine() // 4, 4)
        scale = img.width() / width
        return data[round(3 * scale) : round(15 * scale), round(3 * scale) : round((width - 4) * scale), :3].copy()

    measured = []
    try:
        for entering, original in zip((True, False), timings, strict=True):
            frames = [sample()]
            start = time.monotonic()
            timestamps = [0]
            if action == "focus":
                view.rootObject().setProperty("activeWindow", not entering)
            else:
                view.rootObject().setProperty("hovered", entering)
            while timestamps[-1] < 280:
                QTest.qWait(8)
                frames.append(sample())
                timestamps.append(1000 * (time.monotonic() - start))
            duration = crossing_time(frames, timestamps)
            # One native display interval plus one Qt sample bounds crossing-time quantization.
            if action != "focus":
                assert duration > 0, "hover must show an intermediate frame"
            tolerance = 25 if action != "focus" else 0
            if action == "focus":
                phase = "inactive" if entering else "active"
            else:
                phase = "enter" if entering else "leave"
            measured.append(timing_result(phase, duration, original, tolerance))
    finally:
        view.close()
    return measured


def high_dpi_times(stem):
    with Image.open(stem.with_suffix(".png")) as image:
        pixels = np.array(image)
    frames = pixels.reshape(3, 9, 16, 10, 13, 3).transpose(0, 1, 3, 2, 4, 5).reshape(3, 90, 16, 13, 3)
    timestamps = np.loadtxt(stem.with_suffix(".txt"))
    return [
        [crossing_time(trial[s:e], clock[s:e]) for trial, clock in zip(frames, timestamps, strict=True)]
        for s, e in ((8, 42), (45, 86))
    ]


def compare_high_dpi_caption(stem, scale):
    # Qt reads the output scale before creating the application instance.
    result = subprocess.run(
        [sys.executable, __file__, str(stem), str(scale)],
        capture_output=True,
        check=True,
        text=True,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_SCALE_FACTOR": str(scale)},
    )
    return json.loads(result.stdout)


def window_times(stem):
    with Image.open(stem.with_suffix(".png")) as image:
        sheet = np.array(image)
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


def compare_window_motion(desktops, output, look, stems):
    desktop = desktops(
        look,
        screen=(1024, 768),
        launchers=0,
        components=["background"],
        settings=[("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", "#215f9b")],
        windows=[("Window motion", "qt", (100, 100, 867, 627))],
        pointer_steps=[
            f"record:{output}",
            "select-window:480,320",
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
    states = [state for state, _ in settled]
    assert states == ["normal", "maximized", "normal", "minimized", "normal"], (states, output)
    native_times = [times for stem in stems for times in window_times(stem)]
    measured = []
    actions = ("maximize", "restore-maximized", "minimize", "restore-minimized")
    intervals = itertools.pairwise(i for _, i in settled)
    for action, (start, end), native in zip(actions, intervals, native_times, strict=True):
        duration = crossing_time(frames[start:end], times[start:end])
        # Quantization at the two capture rates can shift the crossings by one frame each.
        if max(native):
            assert duration > 0, "minimize and restore must show intermediate frames"
        tolerance = 50 if max(native) else 34
        measured.append(timing_result(action, duration, native, tolerance))
    return measured


if __name__ == "__main__":
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication([])
    assert app.primaryScreen().devicePixelRatio() == float(sys.argv[2])
    print(json.dumps(compare_caption_motion("close", 50, high_dpi_times(Path(sys.argv[1])))))
