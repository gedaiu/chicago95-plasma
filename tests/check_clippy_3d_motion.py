"""Run in Blender: --python tests/check_clippy_3d_motion.py -- --output report.json."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clippy_3d_motion import TIP_BONES, blink, point, reset, wire_clearance  # noqa: E402


def difference(a, b):
    return max(abs(x - y) for row_a, row_b in zip(a, b, strict=True) for x, y in zip(row_a, row_b, strict=True))


def check(output, blend=None):
    root = Path(__file__).resolve().parents[1]
    bpy.ops.wm.open_mainfile(filepath=str(blend or root / "data/clippy/3d-prototype/calibrated.blend"))
    rig = bpy.data.objects["Armature"]
    reset(rig)
    objects = {o.name: o.matrix_world.copy() for o in bpy.data.objects}
    bones = {b.name: b.matrix.copy() for b in rig.pose.bones}
    point(rig, -1, 1, angle=0.3)
    old_gap = wire_clearance()["surface_gap_lower_bound"]
    assert old_gap < 0, "Regression fixture must catch the old intersecting pose"
    results = []
    turn_angles = []
    for sign in (-1, 1):
        for step in range(61):
            point(rig, sign, step / 60)
            gap = wire_clearance()["surface_gap_lower_bound"]
            assert gap >= 0.02, (sign, step, gap)
            for name, matrix in bones.items():
                if name.startswith("Bone.") and name not in TIP_BONES:
                    assert difference(rig.pose.bones[name].matrix, matrix) < 1e-5, name
            delta = rig.matrix_world @ objects["Armature"].inverted()
            expected_angle = math.pi * min(1, step / 30) if sign < 0 else 0.15 * step / 60
            actual_angle = delta.to_quaternion().angle
            assert abs(actual_angle - expected_angle) < 0.08, (step, actual_angle, expected_angle)
            turn_angles.append(actual_angle)
            for name, matrix in objects.items():
                obj = bpy.data.objects[name]
                expected = delta @ matrix if obj.parent == rig or obj == rig else matrix
                assert difference(obj.matrix_world, expected) < 1e-5, name
            for name in ("eye.L", "eye.R", "eyebrow.L", "eyebrow.R"):
                original = (objects["Armature"] @ bones[name]).to_quaternion()
                current = (rig.matrix_world @ rig.pose.bones[name].matrix).to_quaternion()
                assert abs(original.dot(current)) > 0.998, name
            if "reference_geometry_fit" in rig:
                centers = [
                    world_to_camera_view(
                        bpy.context.scene,
                        bpy.context.scene.camera,
                        rig.matrix_world @ rig.pose.bones[f"eye.{side}"].head,
                    )
                    for side in ("R", "L")
                ]
                assert (centers[1].x - centers[0].x) * 124 >= 14, "Eyes overlap during turn"
            results.append(gap)
    for step in range(31):
        blink(rig, step / 30)
        for name, matrix in bones.items():
            if not name.startswith("eyelid_"):
                assert difference(rig.pose.bones[name].matrix, matrix) < 1e-5, name
        for name, matrix in objects.items():
            assert difference(bpy.data.objects[name].matrix_world, matrix) < 1e-5, name
    reset(rig)
    for name, matrix in bones.items():
        assert difference(rig.pose.bones[name].matrix, matrix) < 1e-5, name
    report = {
        "pointing_samples": len(results),
        "blink_samples": 31,
        "minimum_wire_surface_gap_lower_bound": min(results),
        "required_gap": 0.02,
        "old_collision_detected": True,
        "body_turn_max_degrees": math.degrees(max(turn_angles)),
        "camera_paper_lights_unchanged": True,
        "eyes_track_viewer_during_turn": True,
        "nonanimated_bones_unchanged": True,
        "rest_pose_restored": True,
        "scope": "Smoothed centerline tube clearance at sampled poses; not certification of future animations.",
    }
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blend", type=Path)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    check(args.output, args.blend)
