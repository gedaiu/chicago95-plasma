"""Bake and verify editable Blender Actions from the source-indexed rig poses."""

import argparse
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clippy_3d_motion import apply_blink, point, reset  # noqa: E402
from clippy_3d_timeline import source_timeline  # noqa: E402


def difference(a, b):
    return max(abs(x - y) for aa, bb in zip(a, b, strict=True) for x, y in zip(aa, bb, strict=True))


def bake(source, output):
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    scene.render.fps = 100
    scene.render.fps_base = 1
    rig = bpy.data.objects["Armature"]
    rig.animation_data_clear()
    rig.rotation_mode = "QUATERNION"
    rig.animation_data_create()
    checks = []
    ranges = {}
    for action_name, frames in source_timeline().items():
        rig.animation_data.action = None
        reset(rig)
        action = bpy.data.actions.new("Clippy_" + action_name)
        action.use_fake_user = True
        rig.animation_data.action = action
        poses = []
        frame_number = 1
        for entry in frames:
            scene.frame_set(frame_number)
            if action_name.startswith("Gesture"):
                point(rig, 1 if action_name == "GestureLeft" else -1, entry["progress"])
            else:
                reset(rig)
            apply_blink(rig, entry["blink"])
            poses.append((frame_number, rig.matrix_world.copy(), {b.name: b.matrix.copy() for b in rig.pose.bones}))
            for property_name in ("location", "rotation_quaternion", "scale"):
                rig.keyframe_insert(data_path=property_name, frame=frame_number, group="Body")
                for bone in rig.pose.bones:
                    bone.keyframe_insert(data_path=property_name, frame=frame_number, group=bone.name)
            marker = action.pose_markers.new(f"Original frame {entry['original_index']}")
            marker.frame = frame_number
            frame_number += entry["duration_ms"] // 10
        # Original sprites hold each frame; interpolation must not invent poses.
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = "CONSTANT"
        for frame_number_check, expected_rig, expected_bones in poses:
            scene.frame_set(frame_number_check)
            bpy.context.view_layer.update()
            assert difference(rig.matrix_world, expected_rig) < 1e-4, (action_name, frame_number_check, "body")
            for name, expected in expected_bones.items():
                assert difference(rig.pose.bones[name].matrix, expected) < 1e-4, (action_name, frame_number_check, name)
            checks.append((action_name, frame_number_check))
        ranges[action_name] = [1, frame_number - 1]
    rig.animation_data.action = bpy.data.actions["Clippy_GestureRight"]
    scene.frame_start, scene.frame_end = ranges["GestureRight"]
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    report = {
        "baked_actions": ranges,
        "verified_poses": len(checks),
        "fps": 100,
        "interpolation": "CONSTANT: exact original frame holds",
        "pose_matrices_match": True,
        "note": "Editable pose/timing bake; this does not certify 95% artwork fidelity.",
    }
    output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    bake(args.source, args.output)
