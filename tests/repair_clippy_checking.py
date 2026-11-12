"""Build an isolated 60-fps CheckingSomething candidate and audit every output pose.

Source poses supply the face motion. Added transition motion collapses/expands the
wire and introduces/removes glasses continuously. This is a reconstruction, not
certified original-animation fidelity. The input master is never modified.
"""

import argparse
import bisect
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import inspect_pose
from position_clippy_face import FACE, projected


def smooth(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def interpolate(a, b, t):
    al, ar, az = a.decompose()
    bl, br, bz = b.decompose()
    return Matrix.LocRotScale(al.lerp(bl, t), ar.slerp(br, t), az.lerp(bz, t))


def build(folder, output):
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((folder / "manifest.json").read_text())
    items = manifest["sequences"]["CheckingSomething"]
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    scene = bpy.context.scene
    rig = bpy.data.objects["Armature"]
    camera = scene.camera
    paper = bpy.data.objects["Plane"]
    wire = bpy.data.objects["Vert"]
    glasses = [bpy.data.objects[n] for n in ["GlassesLeft", "GlassesRight", "GlassesBridge"]]
    face = [bpy.data.objects[n] for n in FACE]
    bones = sorted(
        [b for b in rig.pose.bones if b.name.startswith(("eye.", "eyelid_", "eyebrow."))],
        key=lambda b: len(b.parent_recursive),
    )
    objects = [o for o in scene.objects if o.type in ("MESH", "CURVE", "ARMATURE", "LIGHT")]
    lights = [o for o in objects if o.type == "LIGHT" and o.name.startswith("Face ")]

    def capture(frame):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        return (
            {o.name: o.matrix_basis.copy() for o in objects},
            {b.name: b.matrix_basis.copy() for b in rig.pose.bones},
            {o.name: o.hide_render for o in objects},
            {o.name: o.data.energy for o in lights},
        )

    rest = capture(manifest["sequences"]["RestPose"][0]["frame"])
    poses = [capture(i["frame"]) for i in items]
    poses[0] = rest
    poses[-1] = rest
    # Freeze source mesh/curve data at rest; CheckingSomething has no animated
    # paper or MorphWire deformation. Original wire is driven by the rig.
    capture(manifest["sequences"]["RestPose"][0]["frame"])
    for obj in objects:
        obj.animation_data_clear()
        if obj.data and hasattr(obj.data, "animation_data_clear"):
            obj.data.animation_data_clear()
    visible = {o.name for o in objects if not o.hide_render}
    origin = camera.matrix_world.translation.copy()

    def depth_scale(ratio):
        return Matrix.Translation(origin) @ Matrix.Scale(ratio, 4) @ Matrix.Translation(-origin)

    def bounds_center(obj):
        return obj.matrix_world @ (sum((Vector(v) for v in obj.bound_box), Vector()) / 8)

    starts, elapsed = [], 0
    for item in items:
        starts.append(elapsed)
        elapsed += item["duration_ms"]
    count = round(elapsed * 60 / 1000)
    rows, frames = [], []
    for tick in range(count):
        time_ms = tick * 1000 / 60
        index = min(len(items) - 1, bisect.bisect_right(starts, time_ms) - 1)
        next_index = min(index + 1, len(items) - 1)
        blend = smooth((time_ms - starts[index]) / items[index]["duration_ms"])
        a, b = poses[index], poses[next_index]
        for obj in objects:
            obj.matrix_basis = interpolate(a[0][obj.name], b[0][obj.name], blend)
            obj.hide_render = obj.name not in visible
            obj.hide_viewport = obj.hide_render
        for bone in rig.pose.bones:
            bone.matrix_basis = interpolate(a[1][bone.name], b[1][bone.name], blend)
        for light in lights:
            light.data.energy = a[3][light.name] * (1 - blend) + b[3][light.name] * blend
        bpy.context.view_layer.update()
        # Smooth 600-ms entrance/exit, preserving the original total duration.
        phase = min(smooth(time_ms / 600), smooth(((count - 1) * 1000 / 60 - time_ms) / 600))
        wire.hide_render = phase >= 1
        wire.hide_viewport = wire.hide_render
        if not wire.hide_render:
            centre = bounds_center(wire)
            wire.matrix_world = (
                Matrix.Translation(centre)
                @ Matrix.Scale(max(1e-5, 1 - phase), 4)
                @ Matrix.Translation(-centre)
                @ wire.matrix_world
            )
        for obj in glasses:
            obj.hide_render = phase <= 0
            obj.hide_viewport = obj.hide_render
            if not obj.hide_render:
                centre = bounds_center(obj)
                obj.matrix_world = (
                    Matrix.Translation(centre)
                    @ Matrix.Scale(max(1e-5, phase), 4)
                    @ Matrix.Translation(-centre)
                    @ obj.matrix_world
                )
        bpy.context.view_layer.update()
        # Separate complete face from wire and paper in depth at every sample.
        _, wire_near, wire_far = projected([wire], camera)
        _, _, face_far = projected(face, camera)
        ratio = min(1.0, (wire_near - 0.12) / face_far)
        matrices = {bone.name: bone.matrix.copy() for bone in bones}
        for bone in bones:
            bone.matrix = rig.matrix_world.inverted() @ depth_scale(ratio) @ rig.matrix_world @ matrices[bone.name]
            bpy.context.view_layer.update()
        for light in lights:
            light.matrix_world = depth_scale(ratio) @ light.matrix_world
            light.data.energy *= ratio**2
        _, paper_near, _ = projected([paper], camera)
        paper.matrix_world = depth_scale(max(1.0, (wire_far + 0.12) / paper_near)) @ paper.matrix_world
        bpy.context.view_layer.update()
        if phase > 0:
            _, face_near, _ = projected(face, camera)
            _, _, glasses_far = projected(glasses, camera)
            transform = depth_scale(min(1.0, (face_near - 0.12) / glasses_far))
            for obj in glasses:
                obj.matrix_world = transform @ obj.matrix_world
        bpy.context.view_layer.update()
        report = inspect_pose()
        bad = [
            c
            for c in report["object_contacts"]
            if c["kind"] != "source_eye_assembly"
            and set(c["objects"]) not in [
                {"GlassesLeft", "GlassesBridge"}, {"GlassesRight", "GlassesBridge"}
            ]
        ]
        bad += [c for c in report["self_intersections"] if c["kind"] != "source_pupil_eye_join_review"]
        if bad:
            raise RuntimeError(f"Collision at output frame {tick}: {bad}")
        frame = tick + 1
        for obj in objects:
            for prop in ["location", "rotation_quaternion", "rotation_euler", "scale", "hide_render", "hide_viewport"]:
                obj.keyframe_insert(prop, frame=frame)
        for bone in rig.pose.bones:
            for prop in ["location", "rotation_quaternion", "scale"]:
                bone.keyframe_insert(prop, frame=frame)
        for light in lights:
            light.data.keyframe_insert("energy", frame=frame)
        rows.append({"output_frame": tick, "source_index": index, "source_blend": blend, "phase": phase, **report})
        # Rounded millisecond boundaries encode one uniquely rendered pose per
        # 60-fps output frame with the existing exporter, without repeated PNGs.
        duration = round((tick + 1) * 1000 / 60) - round(tick * 1000 / 60)
        frames.append({"frame": frame, "file": f"CheckingSomething/{tick:03d}.png", "duration_ms": duration})
        if tick % 30 == 0:
            print("AUDITED", tick, "/", count, flush=True)
    for obj in objects:
        for owner in [obj, obj.data]:
            if owner is None or not getattr(owner, "animation_data", None) or not owner.animation_data.action:
                continue
            for layer in owner.animation_data.action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for curve in bag.fcurves:
                            for key in curve.keyframe_points:
                                key.interpolation = (
                                    "LINEAR" if curve.data_path not in ["hide_render", "hide_viewport"] else "CONSTANT"
                                )
    scene.render.fps = 60
    scene.frame_start = 1
    scene.frame_end = count
    scene.frame_set(1)
    scene.cycles.samples = 64
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "all-animations.blend"), compress=True)
    result = {
        "sequences": {"CheckingSomething": frames},
        "pixel_size": manifest["pixel_size"],
        "samples": 64,
        "sampling": "One independently rendered and collision-audited pose per 60-fps frame.",
        "status": "CheckingSomething transition/collision candidate; source fidelity not certified.",
    }
    (output / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / "checking-collisions.json").write_text(
        json.dumps(
            {
                "pass": True,
                "output_frames": count,
                "source_duration_ms": elapsed,
                "rendered_duration_ms": count * 1000 / 60,
                "allowed_contacts": ["internal eye/pupil construction", "glasses bridge/frame assembly joints"],
                "scope": "All output samples; no guarantee between 60-fps samples. Source master unchanged.",
                "blend_sha256": hashlib.sha256((output / "all-animations.blend").read_bytes()).hexdigest(),
                "rows": rows,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    build(args.folder, args.output)
