"""Renderable dense GetArtsy transition with explicit idle endpoints.

This repairs continuity of the reconstructed action, not its original-image
fidelity. The source library stays untouched. Every output pose is audited.
"""

import argparse
import bisect
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import inspect_pose
from clippy_3d_library import Library
from position_clippy_face import FACE, projected
from repair_clippy_checking import interpolate, smooth
from repair_clippy_wire import repair

MOBILE = [f"MobileRing{i}" for i in range(3)] + [f"MobileBar{i}" for i in range(3)]
JOINS = [set((f"MobileBar{i}", f"MobileRing{i}")) for i in range(3)] + [
    {"MobileBar0", "MobileBar1"},
    {"MobileBar1", "MobileBar2"},
]


def forbidden(report):
    return [
        c for c in report["object_contacts"] if c["kind"] != "source_eye_assembly" and set(c["objects"]) not in JOINS
    ] + [c for c in report["self_intersections"] if c["kind"] != "source_pupil_eye_join_review"]


def build(folder, output):
    output.mkdir(parents=True, exist_ok=False)
    source = json.loads((folder / "manifest.json").read_text())
    items = source["sequences"]["GetArtsy"]
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    scene = bpy.context.scene
    camera = scene.camera
    rig = bpy.data.objects["Armature"]
    paper = bpy.data.objects["Plane"]
    wire = bpy.data.objects["MorphWire"]
    original = bpy.data.objects["Vert"]
    face = [bpy.data.objects[n] for n in FACE]
    mobile = [bpy.data.objects[n] for n in MOBILE]
    bones = sorted(
        [b for b in rig.pose.bones if b.name.startswith(("eye.", "eyelid_", "eyebrow."))],
        key=lambda b: len(b.parent_recursive),
    )
    lights = [o for o in scene.objects if o.type == "LIGHT" and o.name.startswith("Face ")]
    objects = [o for o in scene.objects if o.type in ("MESH", "CURVE", "ARMATURE", "LIGHT")]

    def capture(frame):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        return (
            {o.name: o.matrix_basis.copy() for o in objects},
            {b.name: b.matrix_basis.copy() for b in rig.pose.bones},
            {o.name: o.hide_render for o in objects},
            {o.name: o.data.energy for o in lights},
            [(p.co.copy(), p.radius) for p in wire.data.splines[0].points],
        )

    poses = [capture(i["frame"]) for i in items]
    rest = capture(source["sequences"]["RestPose"][0]["frame"])
    # Hidden MorphWire coordinates at RestPose are stale from another action.
    # Reconstruct its centreline from the evaluated idle skeleton instead.
    helper = Library.__new__(Library)
    helper.original_wire, helper.camera, helper.scene = original, camera, scene
    helper.depth = 21.0
    rest_path = helper.read_wire_path()
    rest = (*rest[:4], [(Vector((*helper.world(*co), 1)), 1.0) for co in rest_path])
    poses[0] = rest
    poses[-1] = rest
    for obj in objects:
        obj.animation_data_clear()
        if obj.data and hasattr(obj.data, "animation_data_clear"):
            obj.data.animation_data_clear()
    material = paper.data.materials[0].copy()
    material.name = "GetArtsy continuous paper fade"
    paper.data.materials[0] = material
    alpha = material.node_tree.nodes.get("Principled BSDF").inputs["Alpha"]
    origin = camera.matrix_world.translation.copy()

    def depth_scale(ratio):
        return Matrix.Translation(origin) @ Matrix.Scale(ratio, 4) @ Matrix.Translation(-origin)

    camera_frame = camera.data.view_frame(scene=scene)
    w = (max(v.x for v in camera_frame) - min(v.x for v in camera_frame)) / abs(camera_frame[0].z)
    h = (max(v.y for v in camera_frame) - min(v.y for v in camera_frame)) / abs(camera_frame[0].z)
    anchor = camera.matrix_world @ Vector(((58 / 124 - 0.5) * w * 21, (0.5 - 13 / 93) * h * 21, -21))
    starts = []
    elapsed = 0
    for item in items:
        starts.append(elapsed)
        elapsed += item["duration_ms"]
    count = round(elapsed * 60 / 1000)
    rows = []
    saved = []
    frames = []
    for tick in range(count):
        time_ms = tick * 1000 / 60
        index = min(len(items) - 1, bisect.bisect_right(starts, time_ms) - 1)
        next_index = min(index + 1, len(items) - 1)
        mix = smooth((time_ms - starts[index]) / items[index]["duration_ms"])
        a, b = poses[index], poses[next_index]
        phase = min(smooth(time_ms / 600), smooth(((count - 1) * 1000 / 60 - time_ms) / 600))
        for obj in objects:
            obj.matrix_basis = interpolate(a[0][obj.name], b[0][obj.name], mix)
            obj.hide_render = rest[2][obj.name]
            obj.hide_viewport = obj.hide_render
        for bone in rig.pose.bones:
            bone.matrix_basis = interpolate(a[1][bone.name], b[1][bone.name], mix)
        for light in lights:
            light.data.energy = a[3][light.name] * (1 - mix) + b[3][light.name] * mix
        wire.hide_render = tick in [0, count - 1]
        original.hide_render = not wire.hide_render
        wire.hide_viewport = wire.hide_render
        original.hide_viewport = original.hide_render
        for obj in mobile:
            obj.hide_render = phase == 0
            obj.hide_viewport = obj.hide_render
        paper.hide_render = phase == 1
        paper.hide_viewport = paper.hide_render
        alpha.default_value = 1 - phase
        bpy.context.view_layer.update()
        for point, (ca, ra), (cb, rb) in zip(wire.data.splines[0].points, a[4], b[4], strict=True):
            point.co = ca.lerp(cb, mix)
            point.radius = ra * (1 - mix) + rb * mix
        wire.data.update_tag()
        bpy.context.view_layer.update()
        if not wire.hide_render:
            fixed, info = repair(wire, camera)
            if fixed is None:
                raise RuntimeError(f"Wire crossing at {tick}: {info}")
            for point, (co, radius) in zip(wire.data.splines[0].points, fixed, strict=True):
                point.co, point.radius = co, radius
            wire.data.update_tag()
        if phase > 0:
            transform = Matrix.Translation(anchor) @ Matrix.Scale(max(1e-5, phase), 4) @ Matrix.Translation(-anchor)
            for obj in mobile:
                obj.matrix_world = transform @ obj.matrix_world
        bpy.context.view_layer.update()
        active_wire = original if wire.hide_render else wire
        _, wire_near, wire_far = projected([active_wire], camera)
        far = wire_far
        if phase > 0:
            _, near, _ = projected(mobile, camera)
            transform = depth_scale(max(1.0, (wire_far + 0.12) / near))
            for obj in mobile:
                obj.matrix_world = transform @ obj.matrix_world
            bpy.context.view_layer.update()
            _, _, far = projected(mobile, camera)
        _, _, face_far = projected(face, camera)
        ratio = min(1.0, (wire_near - 0.12) / face_far)
        if ratio <= 0:
            raise RuntimeError("Face crosses camera")
        matrices = {b.name: b.matrix.copy() for b in bones}
        for bone in bones:
            bone.matrix = rig.matrix_world.inverted() @ depth_scale(ratio) @ rig.matrix_world @ matrices[bone.name]
            bpy.context.view_layer.update()
        for light in lights:
            light.matrix_world = depth_scale(ratio) @ light.matrix_world
            light.data.energy *= ratio**2
        # Enlarged eye can penetrate its brow. Move the complete brow forward
        # while preserving its projected position and shape.
        _, eye_near, _ = projected(face[:6], camera)
        _, _, brow_far = projected(face[6:], camera)
        brow_transform = depth_scale(min(1.0, (eye_near - 0.06) / brow_far))
        for bone in bones:
            if bone.name.startswith("eyebrow."):
                bone.matrix = rig.matrix_world.inverted() @ brow_transform @ rig.matrix_world @ bone.matrix
                bpy.context.view_layer.update()
        if not paper.hide_render:
            _, paper_near, _ = projected([paper], camera)
            paper.matrix_world = depth_scale(max(1.0, (far + 0.12) / paper_near)) @ paper.matrix_world
        bpy.context.view_layer.update()
        contacts = inspect_pose()
        bad = forbidden(contacts)
        if bad:
            raise RuntimeError(f"Output collision {tick}: {bad}")
        saved.append(
            (
                {o.name: (o.matrix_basis.copy(), o.hide_render) for o in objects},
                {b.name: b.matrix_basis.copy() for b in rig.pose.bones},
                {o.name: o.data.energy for o in lights},
                [(p.co.copy(), p.radius) for p in wire.data.splines[0].points],
                1 - phase,
            )
        )
        rows.append({"output_frame": tick, "source_index": index, "mix": mix, "phase": phase, **contacts})
        frames.append(
            {
                "frame": tick + 1,
                "file": f"GetArtsy/{tick:03}.png",
                "duration_ms": round((tick + 1) * 1000 / 60) - round(tick * 1000 / 60),
            }
        )
        if tick % 30 == 0:
            print("ARTSY AUDITED", tick, "/", count, flush=True)
    saved[-1] = saved[0]
    for frame, pose in enumerate(saved, 1):
        scene.frame_set(frame)
        for obj in objects:
            obj.matrix_basis, obj.hide_render = pose[0][obj.name]
            obj.hide_viewport = obj.hide_render
            for field in ["location", "rotation_quaternion", "rotation_euler", "scale", "hide_render", "hide_viewport"]:
                obj.keyframe_insert(field, frame=frame)
        for bone in rig.pose.bones:
            bone.matrix_basis = pose[1][bone.name]
            for field in ["location", "rotation_quaternion", "scale"]:
                bone.keyframe_insert(field, frame=frame)
        for light in lights:
            light.data.energy = pose[2][light.name]
            light.data.keyframe_insert("energy", frame=frame)
        for point, (co, radius) in zip(wire.data.splines[0].points, pose[3], strict=True):
            point.co, point.radius = co, radius
            point.keyframe_insert("co", frame=frame)
            point.keyframe_insert("radius", frame=frame)
        alpha.default_value = pose[4]
        alpha.keyframe_insert("default_value", frame=frame)
    owners = [material.node_tree]
    for obj in objects:
        owners.extend([obj, obj.data])
    for owner in owners:
        if owner is None or not getattr(owner, "animation_data", None) or not owner.animation_data.action:
            continue
        for layer in owner.animation_data.action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = (
                                "CONSTANT" if curve.data_path in ["hide_render", "hide_viewport"] else "LINEAR"
                            )
    scene.render.fps = 60
    scene.frame_start = 1
    scene.frame_end = count
    scene.frame_set(1)
    scene.cycles.samples = 64
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "all-animations.blend"), compress=True)
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "sequences": {"GetArtsy": frames},
                "pixel_size": source["pixel_size"],
                "samples": 64,
                "sampling": "Individually rendered, collision-audited 60-fps poses with continuous paper opacity.",
                "status": "GetArtsy continuity candidate; original-animation fidelity not certified.",
            },
            indent=2,
        )
        + "\n"
    )
    (output / "artsy-verification.json").write_text(
        json.dumps(
            {
                "output_frames": count,
                "source_duration_ms": elapsed,
                "scope": "Every output sample; internal eye construction and named mobile assembly joints retained.",
                "blend_sha256": hashlib.sha256((output / "all-animations.blend").read_bytes()).hexdigest(),
                "rows": rows,
            },
            indent=2,
        )
        + "\n"
    )


def verify(folder):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    scene = bpy.context.scene
    manifest = json.loads((folder / "manifest.json").read_text())
    report = json.loads((folder / "artsy-verification.json").read_text())
    alpha = bpy.data.objects["Plane"].data.materials[0].node_tree.nodes.get("Principled BSDF").inputs["Alpha"]
    rows = []
    endpoint = None
    for index, item in enumerate(manifest["sequences"]["GetArtsy"]):
        scene.frame_set(item["frame"])
        bpy.context.view_layer.update()
        phase = report["rows"][index]["phase"]
        assert abs(alpha.default_value - (1 - phase)) < 1e-6
        for name in MOBILE:
            assert bpy.data.objects[name].hide_render == (phase == 0), (index, name)
        assert bpy.data.objects["Plane"].hide_render == (phase == 1)
        if phase > 0.05:
            for name in MOBILE:
                coords, _, _ = projected([bpy.data.objects[name]], scene.camera)
                assert np.ptp(coords[:, 0]) + np.ptp(coords[:, 1]) > 0.002 * phase, ("Collapsed prop", index, name)
        contacts = inspect_pose()
        assert not forbidden(contacts), (index, forbidden(contacts))
        rows.append({"output_frame": index, **contacts})
        if index in [0, len(manifest["sequences"]["GetArtsy"]) - 1]:
            objects = [o for o in scene.objects if o.type in ("MESH", "CURVE") and not o.hide_render]
            coords, _, _ = projected(objects, scene.camera)
            if endpoint is None:
                endpoint = coords
            else:
                assert np.allclose(endpoint, coords, atol=1e-6, rtol=0), "Idle endpoint mismatch"
        if index % 60 == 0:
            print("ARTSY BAKE VERIFIED", index, flush=True)
    report["reopened_samples_checked"] = len(rows)
    report["matching_idle_endpoints"] = True
    report["baked_rows"] = rows
    (folder / "artsy-verification.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--verify-only", action="store_true")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if a.verify_only:
        verify(a.folder)
    else:
        if a.output is None:
            p.error("--output required")
        build(a.folder, a.output)
        verify(a.output)
