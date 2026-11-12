"""Bake every original Clippy action into an editable, verified Blender timeline."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clippy_3d_library import SUPPORTED, Library  # noqa: E402
from clippy_all_catalog import catalog, inventory  # noqa: E402


def snapshot(lib, objects, render_only=False):
    values = {}
    for obj in objects:
        if render_only and obj.hide_render:
            continue
        values[obj.name] = [round(v, 5) for row in obj.matrix_basis for v in row] + [int(obj.hide_render)]
    if not render_only or any(not obj.hide_render for obj in lib.rig.children):
        values["bones"] = [[b.name] + [round(v, 5) for row in b.matrix_basis for v in row] for b in lib.rig.pose.bones]
    if not render_only or not lib.morph.hide_render:
        values["curve"] = [[round(v, 5) for v in p.co] + [round(p.radius, 5)] for p in lib.curve_points]
    if not render_only or not lib.paper.hide_render:
        values["paper"] = [[round(v, 5) for v in p.co] for p in lib.paper.data.vertices]
    return values


def mirror_viewport_visibility():
    """Make the editable viewport show the same props as the final render."""
    for obj in bpy.data.objects:
        if not obj.animation_data or not obj.animation_data.action:
            continue
        action = obj.animation_data.action
        if not action.is_action_layered:
            continue
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    source = bag.fcurves.find("hide_render")
                    if source is None or bag.fcurves.find("hide_viewport") is not None:
                        continue
                    target = bag.fcurves.new("hide_viewport")
                    target.keyframe_points.add(len(source.keyframe_points))
                    for old, new in zip(source.keyframe_points, target.keyframe_points, strict=True):
                        new.co = old.co
                        new.interpolation = "CONSTANT"
                    target.update()


def key_pose(lib, objects, frame):
    for obj in objects:
        for prop in ("location", "rotation_quaternion", "scale", "hide_render"):
            obj.keyframe_insert(data_path=prop, frame=frame)
    for bone in lib.rig.pose.bones:
        for prop in ("location", "rotation_quaternion", "scale"):
            bone.keyframe_insert(data_path=prop, frame=frame, group=bone.name)
    for point in lib.curve_points:
        point.keyframe_insert(data_path="co", frame=frame)
        point.keyframe_insert(data_path="radius", frame=frame)
    for vertex in lib.paper.data.vertices:
        vertex.keyframe_insert(data_path="co", frame=frame)


def main(output, samples):
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parents[1] / "data/clippy/3d-prototype/calibrated.blend"
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    scene.render.fps = 100
    scene.render.fps_base = 1
    scene.cycles.samples = samples
    scene.render.resolution_percentage = 100
    lib = Library(scene)
    objects = [o for o in bpy.data.objects if o.type in ("MESH", "CURVE", "ARMATURE")]
    for obj in objects:
        obj.animation_data_clear()
        obj.rotation_mode = "QUATERNION"
        if obj.data and hasattr(obj.data, "animation_data_clear"):
            obj.data.animation_data_clear()
    source_actions = catalog()
    assert set(source_actions) == SUPPORTED
    meta = inventory()
    poses = []
    sequences = {}
    frame = 1
    cache = {}
    props = set()
    deferred = []
    for name, source_action in source_actions.items():
        clip_start = frame
        items = []
        min_clearance = None
        marker = scene.timeline_markers.new(name, frame=frame)
        marker.select = False
        for index, source_frame in enumerate(source_action["frames"]):
            duration = source_frame["duration"]
            if duration < 0 or duration % 10:
                raise ValueError(f"Unrepresentable original duration: {name}/{index}")
            if duration == 0:
                item = {
                    "file": f"{name}/{index:03d}.png",
                    "frame": None,
                    "source_index": index,
                    "duration_ms": 0,
                    "source": source_frame,
                    "control_only": True,
                }
                items.append(item)
                deferred.append((name, index, len(source_action["frames"]), item))
                continue
            scene.frame_set(frame)
            lib.apply(name, index, len(source_action["frames"]))
            bpy.context.view_layer.update()
            if lib.last_clearance is not None:
                min_clearance = min(min_clearance or lib.last_clearance, lib.last_clearance)
            state = snapshot(lib, objects)
            signature = hashlib.sha256(json.dumps(snapshot(lib, objects, True), sort_keys=True).encode()).hexdigest()
            filename = cache.setdefault(signature, f"{name}/{index:03d}.png")
            used = [n for n, o in lib.props.items() if not o.hide_render]
            props.update(used)
            items.append(
                {
                    "file": filename,
                    "frame": frame,
                    "source_index": index,
                    "duration_ms": duration,
                    "source": source_frame,
                    "props": used,
                    "pose_signature": signature,
                }
            )
            poses.append((name, index, frame, state))
            key_pose(lib, objects, frame)
            frame += duration // 10
        sequences[name] = items
        meta[name].update(
            {
                "timeline_start": clip_start,
                "timeline_end": frame - 1,
                "minimum_morph_sample_separation_px": min_clearance,
            }
        )
        print("BAKED", name, len(items), "frames", flush=True)
    timed_end = frame - 1
    if deferred:
        scene.timeline_markers.new("Non-timed branch control poses (not exported as video holds)", frame=frame)
    for name, index, count, item in deferred:
        scene.frame_set(frame)
        lib.apply(name, index, count)
        bpy.context.view_layer.update()
        signature = hashlib.sha256(json.dumps(snapshot(lib, objects, True), sort_keys=True).encode()).hexdigest()
        item.update(
            {
                "frame": frame,
                "pose_signature": signature,
                "props": [n for n, o in lib.props.items() if not o.hide_render],
            }
        )
        cache.setdefault(signature, item["file"])
        poses.append((name, index, frame, snapshot(lib, objects)))
        key_pose(lib, objects, frame)
        frame += 1
    for action in bpy.data.actions:
        if action.is_action_layered:
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for curve in bag.fcurves:
                            for key in curve.keyframe_points:
                                key.interpolation = "CONSTANT"
    # Re-evaluate all keyed poses; this catches unsupported key paths and stale state.
    failures = []
    for name, index, pose_frame, expected in poses:
        scene.frame_set(pose_frame)
        bpy.context.view_layer.update()
        actual = snapshot(lib, objects)
        if actual != expected:
            differing = [key for key in expected if actual.get(key) != expected[key]]
            failures.append({"action": name, "index": index, "channels": differing})
    (output / "bake-verification.json").write_text(
        json.dumps({"poses": len(poses), "failures": failures}, indent=2) + "\n"
    )
    if failures:
        raise RuntimeError(f"{len(failures)} baked poses differ; see bake-verification.json")
    scene.frame_start = 1
    scene.frame_end = timed_end
    mirror_viewport_visibility()
    scene.frame_set(1)
    ranges = bpy.data.texts.new("CLIPPY_CLIP_RANGES.json")
    ranges.write(json.dumps(meta, indent=2))
    notes = bpy.data.texts.new("CLIPPY_README.txt")
    notes.write(
        "43 authored actions on one timeline. Jump to named markers; ranges are in CLIPPY_CLIP_RANGES.json. "
        "All original source frames and branching metadata are preserved in manifest.json. "
        "This reconstruction has not passed the 98% original-fidelity requirement.\n"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "all-animations.blend"), compress=True)
    manifest = {
        "status": "All action poses authored; rendering and visual review pending. Original fidelity is not certified.",
        "pixel_size": [744, 558],
        "logical_size": [124, 93],
        "samples": samples,
        "fps": 100,
        "source_blend_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "sequences": sequences,
        "inventory": meta,
        "unique_render_frames": len(cache),
        "source_frames": len(poses),
        "props": sorted(props),
        "bake_verified": True,
        "branching": "Original branch metadata preserved; videos show the linear source-frame order.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("PREPARED", len(sequences), "actions", len(poses), "source frames", len(cache), "unique renders", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--samples", type=int, default=192)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    main(a.output, a.samples)
