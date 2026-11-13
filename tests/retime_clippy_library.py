"""Retarget all authored poses to source-driven playback paths at 60 fps.

Preserves a separate exact source-pose bank for every original frame. Numeric
channels interpolate only during the last 100 ms of each display interval;
visibility remains discrete. This is an explicit HD reconstruction policy.
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clippy_all_catalog import ROOT, catalog
from clippy_playback_timeline import action_seed, anchors, samples, trace


def curves():
    for action in bpy.data.actions:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        yield action.name, bag.slot_handle, curve


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    expected = np.load(folder / "source-channel-values.npz")["values"]
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    channels = list(curves())
    keys = [(a, slot, c.data_path, c.array_index) for a, slot, c in channels]
    assert keys == [tuple(k) for k in manifest["channels"]]
    source = catalog()
    max_error = 0.0
    checked = 0
    for name, items in manifest["reference_anchors"].items():
        for item in items:
            row = item["pose_row"]
            # Test both source-pose bank and EVERY occurrence along the playback.
            for frame in [item["frame"], *item["playback_frames"]]:
                actual = np.array([c.evaluate(frame) for _, _, c in channels])
                error = float(np.max(np.abs(actual - expected[row])))
                max_error = max(max_error, error)
                assert error < 2e-4, (name, item["source_index"], frame, error)
                checked += 1
            assert item["source"] == source[name]["frames"][item["source_index"]]
    for name, events in manifest["traces"].items():
        assert events == trace(source[name], seed=action_seed(name), stop_ms=manifest["stop_request_ms"])
        expected_samples = samples(events)
        assert len(expected_samples) == len(manifest["sequences"][name])
        for sample, item in zip(expected_samples, manifest["sequences"][name], strict=True):
            assert all(item[k] == value for k, value in sample.items())
    # Check hold keys through their interior, not just endpoints.
    holds = 0
    for point in manifest["key_locations"]:
        if point["kind"] != "hold" or point["frame"] == point["source_frame"]:
            continue
        frame = (point["frame"] + point["source_frame"]) / 2
        actual = np.array([c.evaluate(frame) for _, _, c in channels])
        assert np.max(np.abs(actual - expected[point["pose_row"]])) < 2e-4, ("Hold moved", frame)
        holds += 1
    report = dict(
        actions=len(source),
        source_poses=len(expected),
        reference_occurrences_checked=checked,
        held_intervals_checked=holds,
        max_channel_error=max_error,
        output_samples=sum(map(len, manifest["sequences"].values())),
        blend_sha256=digest(folder / "all-animations.blend"),
        source_definition_sha256=digest(ROOT / "data/clippy/agent.js"),
        pass_timing_and_pose_mapping=True,
        scope="Reopened key channels, source correspondence, holds and traced timing. "
        "Does not certify visual fidelity or intermediate collision safety.",
    )
    (folder / "timing-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


def build(folder, output, stop_ms, tween_ms):
    output.mkdir(parents=True, exist_ok=False)
    old = json.loads((folder / "manifest.json").read_text())
    source = catalog()
    assert set(old["sequences"]) == set(source), "Requires complete source-pose library"
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    scene = bpy.context.scene
    channels = list(curves())
    values, rows = [], {}
    for name, action in source.items():
        assert len(old["sequences"][name]) == len(action["frames"])
        for index, original in enumerate(action["frames"]):
            item = old["sequences"][name][index]
            assert item["source_index"] == index and item["source"] == original
            rows[name, index] = len(values)
            values.append([c.evaluate(item["frame"]) for _, _, c in channels])
    values = np.array(values)
    np.savez_compressed(output / "source-channel-values.npz", values=values)
    points, sequences, traces, references = [], {}, {}, {}
    frame = 1
    scene.timeline_markers.clear()
    for name, action in source.items():
        events = trace(action, seed=action_seed(name), stop_ms=stop_ms)
        traces[name] = events
        scene.timeline_markers.new(name, frame=frame)
        sequence = []
        for sample in samples(events):
            sequence.append(dict(sample, frame=frame + sample["tick"], file=f"{name}/{sample['tick']:04}.png"))
        sequences[name] = sequence
        occurrences = {}
        source_locations = {}
        for timestamp, index, occurrence, kind in anchors(events, frame, tween_ms=tween_ms):
            time = float(timestamp)
            if kind == "source":
                occurrences.setdefault(index, []).append(time)
                source_locations[occurrence] = time
            points.append(
                dict(frame=time, pose_row=rows[name, index], kind=kind, source_frame=source_locations[occurrence])
            )
        references[name] = [
            dict(
                source_index=i,
                source=f,
                pose_row=rows[name, i],
                playback_frames=occurrences.get(i, []),
                file=f"references/{name}/{i:03}.png",
            )
            for i, f in enumerate(action["frames"])
        ]
        duration = sum(e["duration_ms"] for e in events)
        frame += math.ceil(duration * 60 / 1000) + 2
    scene.frame_end = frame - 2
    # Keep skipped alternatives and zero-time control poses testable. These keys
    # are outside playback ranges and cannot accidentally become video frames.
    scene.timeline_markers.new("REFERENCE_POSES_NOT_PLAYBACK", frame=frame)
    for items in references.values():
        for item in items:
            item["frame"] = frame
            points.append(dict(frame=frame, pose_row=item["pose_row"], kind="reference", source_frame=frame))
            frame += 1
    xs = np.array([p["frame"] for p in points], dtype=np.float32)
    row_ids = [p["pose_row"] for p in points]
    for index, (_, _, curve) in enumerate(channels):
        curve.keyframe_points.clear()
        curve.keyframe_points.add(len(points))
        coords = np.column_stack([xs, values[row_ids, index]]).astype(np.float32)
        curve.keyframe_points.foreach_set("co", coords.ravel())
        discrete = curve.data_path.endswith(("hide_render", "hide_viewport"))
        for key, point in zip(curve.keyframe_points, points, strict=True):
            key.interpolation = "CONSTANT" if discrete or point["kind"] == "reference" else "LINEAR"
        curve.update()
    scene.render.fps = 60
    scene.render.fps_base = 1
    scene.frame_start = 1
    scene.frame_set(1)
    scene.cycles.samples = 64
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "all-animations.blend"), compress=True)
    manifest = dict(
        sequences=sequences,
        reference_anchors=references,
        traces=traces,
        key_locations=points,
        channels=[(a, s, c.data_path, c.array_index) for a, s, c in channels],
        fps=60,
        pixel_size=old["pixel_size"],
        samples=64,
        source_definition_sha256=digest(ROOT / "data/clippy/agent.js"),
        source_blend_sha256=digest(folder / "all-animations.blend"),
        stop_request_ms=stop_ms,
        tween_tail_ms=tween_ms,
        sampling="Blender numeric-channel interpolation at 60 fps on source-driven paths; "
        "long holds preserved, visibility discrete. Tween tails are reconstructed.",
        status="Timing candidate. Existing authored geometry; fidelity and collision acceptance pending.",
    )
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    verify(output)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--stop-ms", type=int, default=5000)
    p.add_argument("--tween-ms", type=int, default=100)
    p.add_argument("--verify-only", action="store_true")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if a.verify_only:
        verify(a.folder)
    else:
        if a.output is None:
            p.error("--output is required")
        build(a.folder, a.output, a.stop_ms, a.tween_ms)
