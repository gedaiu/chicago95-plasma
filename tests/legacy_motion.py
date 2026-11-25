"""Capture and measure the Classic and Luna title strips in live KWin."""

import json
import subprocess

import numpy as np
from PIL import Image

CHOSEN = (("ANIM_MINIMIZE", "zoom"), ("ANIM_MAXIMIZE", "zoom"), ("ANIM_WINDOWS", "none"), ("ANIM_SPEED", "1"))


def loaded(session):
    return {name.strip(" '\"()<>[],") for name in session["loaded_effects"].replace(",", " ").split()}


def native_luna_title_strip(folder):
    timestamps = json.loads((folder / "timestamps.json").read_text())
    measured = {}
    for action, samples in timestamps.items():
        with Image.open(folder / f"{action}.png") as sheet:
            tiles = np.asarray(sheet.convert("RGB"), dtype=np.int16)
        height, width = tiles.shape[0] // 2, tiles.shape[1] // 7
        frames = tiles.reshape(2, height, 7, width, 3).transpose(0, 2, 1, 3, 4).reshape(-1, height, width, 3)
        assert len(samples) == len(frames)
        initial, settled = frames[0], frames[-1]
        client = frames[:, 44:96, 37:124]
        visible = (client > 235).all(axis=3).mean(axis=(1, 2)) > 0.85
        delta = np.abs(frames[:, 32:123] - initial[32:123]).max(axis=3)
        width_by_row = (delta > 48).sum(axis=2)
        client_has_original_visibility = visible if action == "minimize" else ~visible
        moving = client_has_original_visibility & (width_by_row.max(axis=1) > 14)
        rows = width_by_row[moving].argmax(axis=1)
        timestamp = np.array([sample["sample_ms"] for sample in samples])[moving]
        assert visible[0] != visible[-1] and not np.array_equal(initial, settled)
        assert len(rows) >= 4 and np.all(np.diff(timestamp) > 0)
        direction = 1 if action == "minimize" else -1
        assert direction * np.polyfit(timestamp, rows, 1)[0] > 0
        measured[action] = {
            "sampled_travel_px": int(np.ptp(rows)) * 8,
            "observed_movement_ms": float(np.ptp(timestamp)),
        }
    return measured


def check_title_strip_speed(measured, spec):
    if "native_speed_px_ms" not in spec:
        return
    low, high = spec["native_speed_px_ms"]
    lower_slack, upper_slack = spec["sampling_tolerance_px_ms"]
    for speeds in measured["speed_px_ms"].values():
        assert any(low - lower_slack <= speed <= high + upper_slack for speed in speeds), (speeds, [low, high])


def measure_title_strip(desktops, video, look, scale, minimize_button, *, classic):
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
            "select-window:480,320",
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
    frames = recorded_frames(video)
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
    # Find the restoring strip against the empty desktop independently of the palette.
    departure = np.abs(colour - (0, 128, 128)).max(axis=3)
    restore_width = (departure > 65).sum(axis=2)
    restore_rows = restore_width.argmax(axis=1)
    restoring = (area < resting_area * 0.1) & (restore_width.max(axis=1) >= 12)
    minimize, restore = minimize_rows[minimizing], restore_rows[restoring]
    assert minimize.size and np.ptp(minimize) >= 25, "caption must travel over the stationary client"
    assert restore.size and np.ptp(restore) >= 25, "caption must travel before the client appears"
    measured = {
        "travel_px": {
            "minimize": float(np.ptp(minimize) * 8 * scale),
            "restore": float(np.ptp(restore) * 8 * scale),
        },
    }
    if classic:
        active_restore_rows = blue_width[restoring, restore_rows[restoring]]
        assert np.count_nonzero(active_restore_rows >= 12) >= 4, "the restoring strip must use the active blue palette"
        times = recorded_timestamps(video)
        measured["speed_px_ms"] = {
            "minimize": list(caption_speeds(minimize_rows, minimizing, times, scale)),
            "restore": [-speed for speed in caption_speeds(restore_rows, restoring, times, scale)],
        }
    return measured


def recorded_frames(video):
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
    return np.frombuffer(pixels, np.uint8).reshape(-1, 96, 128, 3)


def recorded_timestamps(video):
    timing = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "frame=best_effort_timestamp_time", "-of", "json", str(video)],
        timeout=30,
    )
    return np.array([float(frame["best_effort_timestamp_time"]) * 1000 for frame in json.loads(timing)["frames"]])


def caption_speeds(rows, moving, times, scale):
    indices = np.flatnonzero(moving)
    # Ignore the pauses between actions and isolated flickers from the capture.
    for sequence in np.split(indices, np.flatnonzero(np.diff(indices) > 3) + 1):
        if sequence.size >= 4 and np.ptp(rows[sequence]) >= 25:
            # The video was reduced from 1024×768 logical pixels to 128×96.
            yield np.polyfit(times[sequence], rows[sequence] * (8 * scale), 1)[0]


def check_maximize_and_restore(desktops, video, look, maximize_button, restore_button):
    x, y = maximize_button
    screen = desktops(
        look,
        screen=(1024, 768),
        launchers=0,
        components=["background"],
        settings=[*CHOSEN, ("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", "#008080")],
        windows=[("Maximize motion", "qt", (160, 150, 759, 489))],
        pointer_steps=[
            f"record:{video}",
            "select-window:480,320",
            "wait:1",
            f"move:{x},{y}", "wait:0.4", "click:left", "wait:1",
            f"move:{x - 7},{y + 1}", "wait:0.4", "click:left",
            # The second point lies inside the client if the first click maximized.
            # Let the maximized scene settle before activating Restore.
            "wait:5",
            f"move:{restore_button}", "wait:0.4", "click:left", "wait:1",
        ],
    )
    assert "chicago95zoom" in loaded(screen.info)
    pale = recorded_frames(video)[..., 0] > 185
    # Both sizes share the centre. Only the maximized window covers the margins.
    centre = pale[:, 28:50, 35:70].mean(axis=(1, 2))
    margins = np.stack(
        [box.mean(axis=(1, 2)) for box in (pale[:, 8:72, 8:16], pale[:, 66:85, 36:70], pale[:, 23:65, 107:120])],
        axis=1,
    )
    maximized = (margins > 0.9).all(axis=1)
    normal = (margins < 0.1).all(axis=1)
    timestamps = recorded_timestamps(video)
    assert len(timestamps) == len(normal)
    assert normal[0] and normal[-1]
    # PipeWire emits fewer frames after the window has settled. Measure
    # the visible time at both sizes using the presentation timestamps.
    changed = np.flatnonzero(~normal)
    assert changed.size
    assert timestamps[changed[0] - 1] - timestamps[0] >= 150
    assert timestamps[-1] - timestamps[changed[-1] + 1] >= 150
    expanded = timestamps[maximized]
    assert len(expanded) >= 2 and np.ptp(expanded) >= 150, "the recording must include the maximized window"
    changing = np.count_nonzero(~(maximized | normal))
    coverage = centre.min()
    assert changing <= 2, "parts of the desktop flashed through the maximized window"
    assert coverage > 0.95, "maximizing or restoring exposed the desktop inside the client"
    return {"frames_with_intermediate_bounds": int(changing), "minimum_visible_client_fraction": float(coverage)}


def maximize_trace(desktops, video, look, scale):
    screen = desktops(
        look,
        screen=(1024, 768),
        scale=scale,
        setup_scale=scale,
        launchers=0,
        components=["background"],
        settings=[*CHOSEN, ("BACKGROUND_MODE", "color"), ("BACKGROUND_COLOR", "#008080")],
        windows=[("Maximize rendering", "qt", (160, 150, 759, 489))],
        pointer_steps=[
            f"record:{video}", "select-window:480,320", "wait:0.8",
            "move:728,163", "wait:0.2", "click:left",
            "wait:0.6", "move:480,320", "wait:0.4", "move:520,360",
            "wait:0.4", "move:480,320", "wait:0.4",
        ],
        window_state=True,
    )
    screen.save(video.with_name("maximized.png"))
    assert "chicago95zoom" in loaded(screen.info)
    frames = recorded_frames(video)
    timestamps = recorded_timestamps(video)
    assert len(frames) == len(timestamps)
    states = [
        json.loads(line.split("c95-window ", 1)[1])
        for line in screen.info["kwin_log"].splitlines()
        if "c95-window " in line
    ]
    return frames, timestamps, states


def maximize_client_coverage(frames):
    # Measure all four quarters so a missing strip of client area cannot hide in a whole-window average.
    client = frames[..., 0] > 185
    return np.stack(
        [client[:, top:bottom, left:right].mean(axis=(1, 2))
         for top, bottom in ((16, 46), (46, 86)) for left, right in ((3, 64), (64, 125))],
        axis=1,
    )
