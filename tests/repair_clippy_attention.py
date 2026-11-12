"""Repair GetAttention eye spacing and eye/wire/paper depth intersections.

Run after position_clippy_face.py. Output is an isolated candidate; source files
are untouched. Checks actual evaluated triangle contacts, including the original
Vert wire (not just MorphWire), before and after baking.
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import inspect_pose
from build_clippy_3d_library import snapshot
from export_clippy_video import frame_schedule
from position_clippy_face import FACE, projected


def forbidden(report):
    return [x for x in report["object_contacts"] if x["kind"] != "source_eye_assembly"] + [
        x for x in report["self_intersections"] if x["kind"] != "source_pupil_eye_join_review"
    ]


def verify_playback(scene, items, state):
    """Verify every 60-fps sample still holds an audited pose; no tween claim."""
    expected = {}
    for item in items:
        scene.frame_set(item["frame"])
        bpy.context.view_layer.update()
        expected[item["frame"]] = state()
    repeats, _ = frame_schedule([item["duration_ms"] for item in items], 60)
    checked = 0
    for item, count in zip(items, repeats, strict=True):
        for tick in range(count):
            # Interior samples cover the full source hold, including its end.
            frame = item["frame"] + tick / count * item["duration_ms"] / 10
            scene.frame_set(int(frame), subframe=frame % 1)
            bpy.context.view_layer.update()
            assert state() == expected[item["frame"]], ("Unaudited intermediate pose", frame)
            checked += 1
    return checked


def repair(folder, output):
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((folder / "manifest.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    scene = bpy.context.scene
    camera = scene.camera
    rig = bpy.data.objects["Armature"]
    paper = bpy.data.objects["Plane"]
    face = [bpy.data.objects[n] for n in FACE]
    wires = [bpy.data.objects[n] for n in ["Vert", "MorphWire"]]
    bones = sorted(
        [b for b in rig.pose.bones if b.name.startswith(("eye.", "eyelid_", "eyebrow."))],
        key=lambda b: len(b.parent_recursive),
    )
    lights = [o for o in scene.objects if o.type == "LIGHT" and o.name.startswith("Face ")]
    if not lights:
        raise RuntimeError("Run position_clippy_face.py first to separate face lighting")
    objects = [o for o in scene.objects if o.type in ("MESH", "CURVE", "ARMATURE")]
    morph = bpy.data.objects["MorphWire"]
    lib = SimpleNamespace(rig=rig, paper=paper, morph=morph, curve_points=morph.data.splines[0].points)

    def state():
        return snapshot(lib, objects)

    unchanged = {}
    for name, items in manifest["sequences"].items():
        if name == "GetAttention":
            continue
        for item in items:
            scene.frame_set(item["frame"])
            bpy.context.view_layer.update()
            unchanged[item["frame"]] = state()
    origin = camera.matrix_world.translation

    def transform(ratio):
        return Matrix.Translation(origin) @ Matrix.Scale(ratio, 4) @ Matrix.Translation(-origin)

    rows, expected = [], {}
    view = camera.data.view_frame(scene=scene)
    units = np.array(
        [
            124 * abs(view[0].z) / (max(v.x for v in view) - min(v.x for v in view)),
            93 * abs(view[0].z) / (max(v.y for v in view) - min(v.y for v in view)),
        ]
    )
    changed_frames = set()
    for index, item in enumerate(manifest["sequences"]["GetAttention"]):
        frame = item["frame"]
        changed_frames.add(frame)
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        before_contacts = inspect_pose()
        visible_wires = [o for o in wires if not o.hide_render]
        # Enlarged eyes also collide with each other. Separate their evaluated
        # horizontal bounds; move complete bone assemblies, not individual lids.
        inverse = camera.matrix_world.inverted()
        dep = bpy.context.evaluated_depsgraph_get()
        intervals = []
        for group in [face[:3], face[3:6]]:
            xs = []
            for obj in group:
                evaluated = obj.evaluated_get(dep)
                mesh = evaluated.to_mesh()
                xs.extend((inverse @ evaluated.matrix_world @ v.co).x for v in mesh.vertices)
                evaluated.to_mesh_clear()
            intervals.append((min(xs), max(xs)))
        intervals.sort()
        separation = max(0.0, (intervals[0][1] - intervals[1][0] + 0.025) / 2)
        eye_order = sorted(
            ["L", "R"],
            key=lambda side: (inverse @ rig.matrix_world @ rig.pose.bones["eye." + side].matrix.translation).x,
        )
        matrices = {b.name: b.matrix.copy() for b in bones}
        for side, direction in zip(eye_order, [-1, 1], strict=True):
            offset = (
                rig.matrix_world.inverted().to_3x3()
                @ camera.matrix_world.to_3x3()
                @ Vector((direction * separation, 0, 0))
            )
            for b in bones:
                if b.name.endswith("." + side):
                    b.matrix = Matrix.Translation(offset) @ matrices[b.name]
                    bpy.context.view_layer.update()
        before, _, face_far = projected(face + [paper], camera)
        _, _, face_far = projected(face, camera)
        _, wire_near, wire_far = projected(visible_wires, camera)
        ratio = min(1.0, (wire_near - 0.12) / face_far)
        if ratio <= 0:
            raise RuntimeError("Face would cross camera")
        matrices = {b.name: b.matrix.copy() for b in bones}
        for b in bones:
            b.matrix = rig.matrix_world.inverted() @ transform(ratio) @ rig.matrix_world @ matrices[b.name]
            bpy.context.view_layer.update()
            for field in ["location", "rotation_quaternion", "scale"]:
                b.keyframe_insert(field, frame=frame)
        for light in lights:
            light.matrix_world = transform(ratio) @ light.matrix_world
            light.data.energy *= ratio**2
            for field in ["location", "rotation_euler", "scale"]:
                light.keyframe_insert(field, frame=frame)
            light.data.keyframe_insert("energy", frame=frame)
        _, paper_near, _ = projected([paper], camera)
        paper_ratio = max(1.0, (wire_far + 0.12) / paper_near)
        paper.matrix_world = transform(paper_ratio) @ paper.matrix_world
        for field in ["location", "rotation_quaternion", "scale"]:
            paper.keyframe_insert(field, frame=frame)
        bpy.context.view_layer.update()
        after, _, _ = projected(face + [paper], camera)
        error = float(np.max(np.abs(after - before) * units))
        if error > 0.02:
            raise RuntimeError(f"Projection changed: {index}: {error}")
        expected[frame] = state()
        rows.append(
            {
                "source_index": index,
                "timeline_frame": frame,
                "before": before_contacts,
                "projection_error_native_pixels": error,
                "eye_separation_world_units": separation * 2,
                "face_depth_ratio": ratio,
                "paper_depth_ratio": paper_ratio,
            }
        )
        item["file"] = f"GetAttention/{index:03d}.png"
        item["pose_signature"] = hashlib.sha256(json.dumps(state(), sort_keys=True).encode()).hexdigest()
        print("REPAIRED", index, "projection error", error, flush=True)
    for owner in [rig, paper] + lights + [o.data for o in lights]:
        for layer in owner.animation_data.action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            if round(key.co.x) in changed_frames:
                                key.interpolation = "CONSTANT"
                        curve.update()
    for frame, previous in unchanged.items():
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        assert state() == previous, ("Unrelated pose changed", frame)
    for row in rows:
        scene.frame_set(row["timeline_frame"])
        bpy.context.view_layer.update()
        assert state() == expected[row["timeline_frame"]], ("Bake changed", row["source_index"])
        row["after"] = inspect_pose()
        assert not forbidden(row["after"]), ("Collision remains", row["source_index"], forbidden(row["after"]))
        print("VERIFIED", row["source_index"], flush=True)
    playback_frames = verify_playback(scene, manifest["sequences"]["GetAttention"], state)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "all-animations.blend"), compress=True)
    manifest["unique_render_frames"] = len({i["file"] for items in manifest["sequences"].values() for i in items})
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    report = {
        "action": "GetAttention",
        "poses_checked": len(rows),
        "held_playback_samples_checked": playback_frames,
        "unchanged_poses_checked": len(unchanged),
        "scope": (
            "Evaluated source poses with CONSTANT holds; not interpolated movement. "
            "Source internal eye assembly contacts remain. Projection error measures depth "
            "separation only; the deliberate eye-spacing correction changes screen positions."
        ),
        "blend_sha256": hashlib.sha256((output / "all-animations.blend").read_bytes()).hexdigest(),
        "pass": True,
        "rows": rows,
    }
    (output / "attention-collisions.json").write_text(json.dumps(report, indent=2) + "\n")
    for name in ["bake-verification.json", "wire-repair.json", "face-placement.json"]:
        if (folder / name).is_file():
            shutil.copy2(folder / name, output / name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    repair(args.folder, args.output)
