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


def forbidden(report):
    bad = [
        c
        for c in report["object_contacts"]
        if c["kind"] != "source_eye_assembly"
        and set(c["objects"]) not in [{"GlassesLeft", "GlassesBridge"}, {"GlassesRight", "GlassesBridge"}]
    ]
    bad += [c for c in report["self_intersections"] if c["kind"] != "source_pupil_eye_join_review"]
    return bad


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
    # A straight bridge needs two endpoints. Hundreds of nearly coincident
    # points on this short tube produce unstable bevel frames and self contacts.
    bridge_data = glasses[2].data
    ends = [bridge_data.splines[0].points[i].co.copy() for i in [0, -1]]
    bridge_data.splines.clear()
    spline = bridge_data.splines.new("POLY")
    spline.points.add(1)
    for point, co in zip(spline.points, ends, strict=True):
        point.co = co
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
    rows, frames, generated = [], [], []
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
        bpy.context.view_layer.update()
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
                # Hidden objects retain a stale evaluated world matrix until
                # re-enabled and updated. Never scale that cached transform.
                bpy.context.view_layer.update()
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
            # Keep each rim centred on its eye, rather than the old fixed
            # screen coordinates that put the upper edge through the pupil.
            camera_basis = camera.matrix_world.to_3x3()
            for obj, group in zip(glasses[:2], [face[:3], face[3:6]], strict=True):
                centre = bounds_center(obj)
                narrow = (
                    camera_basis.to_4x4() @ Matrix.Diagonal(Vector((0.85, 1, 1, 1))) @ camera_basis.inverted().to_4x4()
                )
                obj.matrix_world = Matrix.Translation(centre) @ narrow @ Matrix.Translation(-centre) @ obj.matrix_world
                bpy.context.view_layer.update()
                eye_coords, _, _ = projected(group, camera)
                rim_coords, near, far = projected([obj], camera)
                eye_centre = (eye_coords.min(axis=0) + eye_coords.max(axis=0)) / 2
                rim_centre = (rim_coords.min(axis=0) + rim_coords.max(axis=0)) / 2
                delta = (eye_centre - rim_centre) * ((near + far) / 2)
                obj.matrix_world.translation += camera_basis @ Vector((delta[0], delta[1], 0))
            bpy.context.view_layer.update()
            # Connect the inner upper corners with actual bridge geometry.
            endpoints = []
            for obj, direction in zip(glasses[:2], [1, -1], strict=True):
                coords, near, far = projected([obj], camera)
                centre = (coords.min(axis=0) + coords.max(axis=0)) / 2
                extent = coords.max(axis=0) - coords.min(axis=0)
                depth = (near + far) / 2
                endpoints.append(
                    camera.matrix_world
                    @ Vector(
                        (
                            (centre[0] + direction * extent[0] * 0.45) * depth,
                            (centre[1] + extent[1] * 0.25) * depth,
                            -depth,
                        )
                    )
                )
            bridge = glasses[2]
            for i, point in enumerate(bridge.data.splines[0].points):
                coordinate = bridge.matrix_world.inverted() @ endpoints[0].lerp(
                    endpoints[1], i / (len(bridge.data.splines[0].points) - 1)
                )
                point.co = (*coordinate, 1)
                point.radius = phase
            bridge.data.update_tag()
            bpy.context.view_layer.update()
            _, face_near, _ = projected(face, camera)
            _, _, glasses_far = projected(glasses, camera)
            transform = depth_scale(min(1.0, (face_near - 0.12) / glasses_far))
            for obj in glasses:
                obj.matrix_world = transform @ obj.matrix_world
        bpy.context.view_layer.update()
        if phase > 0.05:
            for obj in glasses[:2]:
                coords, _, _ = projected([obj], camera)
                if float(coords[:, 0].max() - coords[:, 0].min()) < 0.02 * phase:
                    raise RuntimeError(f"Collapsed glasses: {tick}: {obj.name}: {tuple(obj.scale)}")
        report = inspect_pose()
        bad = forbidden(report)
        if bad:
            raise RuntimeError(f"Collision at output frame {tick}: {bad}")
        frame = tick + 1
        generated.append(
            (
                {o.name: o.matrix_basis.copy() for o in objects},
                {b.name: b.matrix_basis.copy() for b in rig.pose.bones},
                {o.name: o.hide_render for o in objects},
                {o.name: o.data.energy for o in lights},
                [(p.co.copy(), p.radius) for p in glasses[2].data.splines[0].points],
            )
        )
        rows.append({"output_frame": tick, "source_index": index, "source_blend": blend, "phase": phase, **report})
        # Rounded millisecond boundaries encode one uniquely rendered pose per
        # 60-fps output frame with the existing exporter, without repeated PNGs.
        duration = round((tick + 1) * 1000 / 60) - round(tick * 1000 / 60)
        frames.append({"frame": frame, "file": f"CheckingSomething/{tick:03d}.png", "duration_ms": duration})
        if tick % 30 == 0:
            print("AUDITED", tick, "/", count, flush=True)
    # Bake only after generating/auditing all poses. Evaluation of partially
    # written animation must not feed back into the next generated pose.
    # Use the identical stored rest state at both ends, avoiding tiny slerp/
    # matrix-rounding changes that can alter denoised edge pixels on looping.
    generated[-1] = generated[0]
    for frame, pose in enumerate(generated, 1):
        scene.frame_set(frame)
        for obj in objects:
            obj.matrix_basis = pose[0][obj.name]
            obj.hide_render = pose[2][obj.name]
            obj.hide_viewport = obj.hide_render
        for bone in rig.pose.bones:
            bone.matrix_basis = pose[1][bone.name]
        for light in lights:
            light.data.energy = pose[3][light.name]
        for point, (co, radius) in zip(glasses[2].data.splines[0].points, pose[4], strict=True):
            point.co, point.radius = co, radius
            point.keyframe_insert("co", frame=frame)
            point.keyframe_insert("radius", frame=frame)
        for obj in objects:
            for prop in ["location", "rotation_quaternion", "rotation_euler", "scale", "hide_render", "hide_viewport"]:
                obj.keyframe_insert(prop, frame=frame)
        for bone in rig.pose.bones:
            for prop in ["location", "rotation_quaternion", "scale"]:
                bone.keyframe_insert(prop, frame=frame)
        for light in lights:
            light.data.keyframe_insert("energy", frame=frame)
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


def verify_bake(folder):
    """Reopen the saved master and independently audit every rendered sample."""
    import numpy as np

    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    manifest = json.loads((folder / "manifest.json").read_text())
    report = json.loads((folder / "checking-collisions.json").read_text())
    scene = bpy.context.scene
    rows = []
    endpoint = None
    for index, item in enumerate(manifest["sequences"]["CheckingSomething"]):
        scene.frame_set(item["frame"])
        bpy.context.view_layer.update()
        phase = report["rows"][index]["phase"]
        for name in ["GlassesLeft", "GlassesRight"]:
            obj = bpy.data.objects[name]
            if obj.hide_render != (phase <= 0):
                raise RuntimeError(f"Incorrect glasses visibility at {index}")
            if phase > 0.05:
                coords, _, _ = projected([obj], scene.camera)
                if float(coords[:, 0].max() - coords[:, 0].min()) < 0.02 * phase:
                    raise RuntimeError(f"Collapsed baked glasses at {index}: {name}")
        contacts = inspect_pose()
        if forbidden(contacts):
            raise RuntimeError(f"Baked collision at {index}: {forbidden(contacts)}")
        rows.append({"output_frame": index, **contacts})
        if index in (0, len(manifest["sequences"]["CheckingSomething"]) - 1):
            visible = [o for o in scene.objects if o.type in ("MESH", "CURVE") and not o.hide_render]
            projection, _, _ = projected(visible, scene.camera)
            if endpoint is None:
                endpoint = projection
            else:
                if endpoint.shape != projection.shape or not np.allclose(endpoint, projection, atol=1e-6, rtol=0):
                    raise RuntimeError("Start and end rest geometry differ")
        if index % 60 == 0:
            print("BAKE AUDITED", index, flush=True)
    report["baked_samples_checked"] = len(rows)
    report["baked_rows"] = rows
    report["start_end_rest_projection_matches"] = True
    (folder / "checking-collisions.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.verify_only:
        verify_bake(args.folder)
    else:
        if args.output is None:
            parser.error("--output is required when building")
        build(args.folder, args.output)
        verify_bake(args.output)
