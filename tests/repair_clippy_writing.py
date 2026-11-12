"""Source-guided Writing candidate: paper lifting, pencil motion and wire poses.

Paper outlines and pencil endpoints come from the reference atlas. The wire is
an authored 3D reconstruction, not a recovered original rig or a 98% match.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import inspect_pose
from clippy_3d_library import path, resample, smooth
from clippy_3d_motion import apply_blink
from position_clippy_face import FACE, projected
from repair_clippy_wire import repair


def fit_metal(coords, pixels):
    """Bounded, smoothed fit to source metal edges; never shifts the image."""
    base = coords[:, :2].copy()
    result = base.copy()
    pixels = np.asarray(pixels, dtype=float)
    for _ in range(20):
        distance = ((result[:, None] - pixels[None]) ** 2).sum(2)
        weights = np.exp(-distance / 5)
        valid = distance.min(1) < 64
        centres = weights @ pixels / np.maximum(weights.sum(1)[:, None], 1e-12)
        result[valid] += 0.35 * (centres[valid] - result[valid])
        result[1:-1] += 0.2 * ((result[:-2] + result[2:]) / 2 - result[1:-1])
        delta = result - base
        result = base + delta * np.minimum(1, 8 / np.maximum(np.linalg.norm(delta, axis=1), 1e-6))[:, None]
    coords[:, :2] = result
    # Fit the smooth tube, not individual low-resolution dithering pixels.
    kernel = np.exp(-(np.arange(-7, 8, dtype=float) ** 2) / 18)
    kernel /= kernel.sum()
    for axis in [0, 1]:
        coords[:, axis] = np.convolve(np.pad(coords[:, axis], (7, 7), mode="edge"), kernel, mode="valid")
    return resample(coords)


def build(folder, landmarks_path, output):
    output.mkdir(parents=True, exist_ok=False)
    reference = json.loads(landmarks_path.read_text())
    source = json.loads((folder / "manifest.json").read_text())
    items = source["sequences"]["Writing"]
    timeline = [1]
    for item in items[:-1]:
        timeline.append(timeline[-1] + item["duration_ms"] // 10)
    assert len(reference) == len(items) == 61
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    scene = bpy.context.scene
    camera = scene.camera
    rig = bpy.data.objects["Armature"]
    old_paper = bpy.data.objects["Plane"]
    wire = bpy.data.objects["MorphWire"]
    original_wire = bpy.data.objects["Vert"]
    face = [bpy.data.objects[n] for n in FACE]
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
        )

    poses = [capture(i["frame"]) for i in items]
    rest = capture(source["sequences"]["RestPose"][0]["frame"])
    poses[0] = rest
    poses[-1] = rest
    # Read the original resting path before removing its animation.
    rest_path = []
    inverse = camera.matrix_world.inverted()
    frame = camera.data.view_frame(scene=scene)
    width = (max(v.x for v in frame) - min(v.x for v in frame)) / abs(frame[0].z)
    height = (max(v.y for v in frame) - min(v.y for v in frame)) / abs(frame[0].z)
    for point in wire.data.splines[0].points:
        co = inverse @ wire.matrix_world @ Vector(point.co[:3])
        depth = -co.z
        rest_path.append([(co.x / depth / width + 0.5) * 124, (0.5 - co.y / depth / height) * 93, 0])
    rest_path = np.array(rest_path)

    def world(x, y, depth):
        return camera.matrix_world @ Vector(((x / 124 - 0.5) * width * depth, (0.5 - y / 93) * height * depth, -depth))

    origin = camera.matrix_world.translation.copy()

    def depth_scale(ratio):
        return Matrix.Translation(origin) @ Matrix.Scale(ratio, 4) @ Matrix.Translation(-origin)

    for obj in objects:
        obj.animation_data_clear()
        if obj.data and hasattr(obj.data, "animation_data_clear"):
            obj.data.animation_data_clear()
    # New native mesh, using the existing approved lined-paper material.
    mesh = bpy.data.meshes.new("Writing source paper")
    mesh.from_pydata([(0, 0, 0)] * 64, [], [tuple(range(64))])
    paper = bpy.data.objects.new("WritingPaper", mesh)
    scene.collection.objects.link(paper)
    mesh.materials.append(old_paper.data.materials[0])
    uv = mesh.uv_layers.new(name="UVMap")
    for light in [o for o in scene.objects if o.type == "LIGHT" and not o.name.startswith("Face ")]:
        receivers = light.light_linking.receiver_collection
        if receivers and paper.name not in receivers.objects:
            receivers.objects.link(paper)
    # Simple straight shafts avoid dense collinear bevel segments.
    for name in ["Pencil", "Graphite"]:
        obj = bpy.data.objects[name]
        obj.data.splines.clear()
        sp = obj.data.splines.new("POLY")
        sp.points.add(1)
        obj.data.bevel_depth = 0.032 if name == "Pencil" else 0.018
    wire.data.bevel_depth = 0.105
    rows = []
    saved = []
    out_items = []
    for index, (item, ref, pose) in enumerate(zip(items, reference, poses, strict=True)):
        for obj in objects:
            obj.matrix_basis = pose[0][obj.name]
            obj.hide_render = rest[2][obj.name]
            obj.hide_viewport = obj.hide_render
        for bone in rig.pose.bones:
            bone.matrix_basis = pose[1][bone.name]
        for light in lights:
            light.data.energy = pose[3][light.name]
        original_wire.hide_render = index not in [0, 60]
        original_wire.hide_viewport = original_wire.hide_render
        wire.hide_render = index in [0, 60]
        wire.hide_viewport = wire.hide_render
        old_paper.hide_render = 8 <= index < 60
        old_paper.hide_viewport = old_paper.hide_render
        paper.hide_render = not old_paper.hide_render
        paper.hide_viewport = paper.hide_render
        bpy.context.view_layer.update()
        poly = np.array(ref["paper_polygon"], dtype=float)
        hi = poly.max(0)
        pencil = ref["pencil_endpoints"]
        if not wire.hide_render:
            amount = min(smooth(index / 12), smooth((60 - index) / 6))
            grip = (min(82.0, hi[0] - 2), min(76.0, hi[1] - 3))
            penhand = np.array(max(pencil, key=lambda p: p[1])) if pencil else np.array([61.0, 57.0])
            target = path(
                [
                    grip,
                    (72, 76),
                    (62, 85),
                    (52, 80),
                    (47, 65),
                    (47, 30),
                    (49, 12),
                    (58, 5),
                    (66, 10),
                    (64, 31),
                    (64, 54),
                    (59, 68),
                    (53, 70),
                    (54, 63),
                    (float(penhand[0]), float(penhand[1])),
                ]
            )
            coords = rest_path * (1 - amount) + target * amount
            coords = fit_metal(coords, ref["metal_pixels"])
            for point, co in zip(wire.data.splines[0].points, coords, strict=True):
                point.co = (*world(co[0], co[1], 21), 1)
                point.radius = 1
            wire.matrix_world = Matrix.Identity(4)
            wire.data.update_tag()
            bpy.context.view_layer.update()
            fixed, info = repair(wire, camera)
            if fixed is None:
                raise RuntimeError(f"Wire repair failed: {index}")
            for point, (co, radius) in zip(wire.data.splines[0].points, fixed, strict=True):
                point.co, point.radius = co, radius
            wire.data.update_tag()
        bpy.context.view_layer.update()
        # Source Writing mostly looks down through lowered lids, with open-eye
        # pauses and glances. Preserve the open default stance at both ends.
        if index not in [0, 1, 12, 28, 31, 44, 46, 51, 55, 56, 57, 58, 59, 60]:
            apply_blink(rig, 0.45)
        visible_wire = original_wire if wire.hide_render else wire
        _, near, far = projected([visible_wire], camera)
        _, _, face_far = projected(face, camera)
        ratio = min(1.0, (near - 0.12) / face_far)
        matrices = {b.name: b.matrix.copy() for b in bones}
        for bone in bones:
            bone.matrix = rig.matrix_world.inverted() @ depth_scale(ratio) @ rig.matrix_world @ matrices[bone.name]
            bpy.context.view_layer.update()
        for light in lights:
            light.matrix_world = depth_scale(ratio) @ light.matrix_world
            light.data.energy *= ratio**2
        # Paper remains present throughout; its source silhouette replaces the
        # early disappearing-sheet / blank-notepad shortcut.
        if not paper.hide_render:
            perimeter = resample(np.column_stack([np.vstack([poly, poly[0]]), np.zeros(len(poly) + 1)]), 65)[:-1, :2]
            pixels = perimeter
            for vertex, p in zip(mesh.vertices, pixels, strict=True):
                vertex.co = world(p[0], p[1], far + 0.2)
            # Ruled lines follow the top edge, including perspective shear.
            top = poly[poly[:, 1] <= poly[:, 1].min() + max(2, np.ptp(poly[:, 1]) * 0.12)]
            slope = float(np.polyfit(top[:, 0], top[:, 1], 1)[0]) if np.ptp(top[:, 0]) > 3 else 0
            coords = np.column_stack([pixels[:, 0], slope * pixels[:, 0] - pixels[:, 1]])
            coords = (coords - coords.min(0)) / np.maximum(coords.max(0) - coords.min(0), 1e-6)
            # The approved paper texture is one ruled stripe, not a whole page.
            coords[:, 0] = coords[:, 0] * 0.77 - 0.026
            coords[:, 1] *= 23.18
            for loop in mesh.loops:
                uv.data[loop.index].uv = coords[loop.vertex_index]
            mesh.update()
        else:
            _, paper_near, _ = projected([old_paper], camera)
            old_paper.matrix_world = depth_scale(max(1.0, (far + 0.2) / paper_near)) @ old_paper.matrix_world
        bpy.context.view_layer.update()
        _, face_near, _ = projected(face, camera)
        for name in ["Pencil", "Graphite"]:
            obj = bpy.data.objects[name]
            obj.hide_render = pencil is None
            obj.hide_viewport = obj.hide_render
            obj.matrix_world = Matrix.Identity(4)
            if pencil is not None:
                endpoints = np.array(sorted(pencil, key=lambda p: p[1]))
                direction = endpoints[1] - endpoints[0]
                direction /= max(np.linalg.norm(direction), 1e-6)
                if name == "Graphite":
                    endpoints = np.array([endpoints[1], endpoints[1] + direction * 1.2])
                for point, p in zip(obj.data.splines[0].points, endpoints, strict=True):
                    point.co = (*world(p[0], p[1], face_near - 0.2), 1)
                    point.radius = 1
                obj.data.update_tag()
        bpy.context.view_layer.update()
        contacts = inspect_pose()
        bad = [
            c for c in contacts["object_contacts"] if c["kind"] not in ["source_eye_assembly", "pencil_tip_join_review"]
        ]
        bad += [c for c in contacts["self_intersections"] if c["kind"] != "source_pupil_eye_join_review"]
        if bad:
            raise RuntimeError(f"Unresolved contact at {index}: {bad}")
        saved.append(
            (
                {o.name: (o.matrix_basis.copy(), o.hide_render) for o in objects + [paper]},
                {b.name: b.matrix_basis.copy() for b in rig.pose.bones},
                {o.name: o.data.energy for o in lights},
                {
                    o.name: [(p.co.copy(), p.radius) for p in o.data.splines[0].points]
                    for o in [wire, bpy.data.objects["Pencil"], bpy.data.objects["Graphite"]]
                },
                [v.co.copy() for v in mesh.vertices],
                [v.uv.copy() for v in uv.data],
            )
        )
        rows.append({"source_index": index, "paper_present": True, "pencil_visible": pencil is not None, **contacts})
        out_items.append({**item, "frame": timeline[index], "file": f"Writing/{index:03d}.png"})
        print("WRITING VERIFIED", index, flush=True)
    # Capture UV values in a per-frame mesh datablock: Blender mesh UVs cannot
    # be keyframed directly. Keep one visible paper mesh for each keyed pose.
    paper.hide_render = True
    paper.hide_viewport = True
    papers = []
    for index, pose in enumerate(saved):
        obj = paper.copy()
        obj.data = mesh.copy()
        obj.name = f"WritingPaper{index:03d}"
        scene.collection.objects.link(obj)
        papers.append(obj)
        for v, co in zip(obj.data.vertices, pose[4], strict=True):
            v.co = co
        for v, co in zip(obj.data.uv_layers.active.data, pose[5], strict=True):
            v.uv = co
        for light in [o for o in scene.objects if o.type == "LIGHT" and not o.name.startswith("Face ")]:
            receivers = light.light_linking.receiver_collection
            if receivers and obj.name not in receivers.objects:
                receivers.objects.link(obj)
    for index, pose in enumerate(saved):
        frame = timeline[index]
        scene.frame_set(frame)
        for obj in objects:
            obj.matrix_basis, obj.hide_render = pose[0][obj.name]
            obj.hide_viewport = obj.hide_render
            for prop in ["location", "rotation_quaternion", "rotation_euler", "scale", "hide_render", "hide_viewport"]:
                obj.keyframe_insert(prop, frame=frame)
        for bone in rig.pose.bones:
            bone.matrix_basis = pose[1][bone.name]
            for prop in ["location", "rotation_quaternion", "scale"]:
                bone.keyframe_insert(prop, frame=frame)
        for light in lights:
            light.data.energy = pose[2][light.name]
            light.data.keyframe_insert("energy", frame=frame)
        for name, points in pose[3].items():
            for point, (co, radius) in zip(bpy.data.objects[name].data.splines[0].points, points, strict=True):
                point.co, point.radius = co, radius
                point.keyframe_insert("co", frame=frame)
                point.keyframe_insert("radius", frame=frame)
        for i, obj in enumerate(papers):
            obj.hide_render = i != index or pose[0][paper.name][1]
            obj.hide_viewport = obj.hide_render
            obj.keyframe_insert("hide_render", frame=frame)
            obj.keyframe_insert("hide_viewport", frame=frame)
    for obj in list(scene.objects):
        for owner in [obj, obj.data]:
            if owner is None or not getattr(owner, "animation_data", None) or not owner.animation_data.action:
                continue
            for layer in owner.animation_data.action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for curve in bag.fcurves:
                            for key in curve.keyframe_points:
                                key.interpolation = "CONSTANT"
    scene.render.fps = 100
    scene.frame_start = 1
    scene.frame_end = sum(i["duration_ms"] for i in items) // 10
    scene.frame_set(1)
    scene.cycles.samples = 96
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "all-animations.blend"), compress=True)
    manifest = {
        "sequences": {"Writing": out_items},
        "pixel_size": source["pixel_size"],
        "samples": 96,
        "status": "Source-guided Writing candidate; paper hulls and wire are approximations, not 98% certified.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "writing-geometry.json").write_text(
        json.dumps(
            {
                "poses": 61,
                "rows": rows,
                "source_landmarks_sha256": hashlib.sha256(landmarks_path.read_bytes()).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )


def verify(folder, landmarks_path):
    """Independently verify saved geometry and source prop positions/timing."""
    from bpy_extras.object_utils import world_to_camera_view
    from clippy_all_catalog import catalog

    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    scene = bpy.context.scene
    manifest = json.loads((folder / "manifest.json").read_text())
    landmarks = json.loads(landmarks_path.read_text())
    source = catalog()["Writing"]["frames"]
    rows = []
    elapsed = 0
    for index, item in enumerate(manifest["sequences"]["Writing"]):
        assert item["source"] == source[index] and item["duration_ms"] == source[index]["duration"]
        assert item["frame"] == 1 + elapsed // 10
        elapsed += item["duration_ms"]
        scene.frame_set(item["frame"])
        bpy.context.view_layer.update()
        contacts = inspect_pose()
        bad = [
            c for c in contacts["object_contacts"] if c["kind"] not in ["source_eye_assembly", "pencil_tip_join_review"]
        ]
        bad += [c for c in contacts["self_intersections"] if c["kind"] != "source_pupil_eye_join_review"]
        assert not bad, (index, bad)
        papers = [
            o
            for o in scene.objects
            if o.type == "MESH" and (o.name.startswith("WritingPaper") or o.name == "Plane") and not o.hide_render
        ]
        assert len(papers) == 1, (index, [o.name for o in papers])
        obj = bpy.data.objects["Pencil"]
        points = landmarks[index]["pencil_endpoints"]
        assert obj.hide_render == (points is None)
        error = None
        if points is not None:
            expected = np.array(sorted(points, key=lambda p: p[1]))
            actual = []
            for point in obj.data.splines[0].points:
                p = world_to_camera_view(scene, scene.camera, obj.matrix_world @ Vector(point.co[:3]))
                actual.append([p.x * 124, (1 - p.y) * 93])
            error = float(abs(np.array(actual) - expected).max())
            assert error < 0.01, (index, error)
        rows.append({"source_index": index, "pencil_max_error_native_pixels": error, **contacts})
    assert elapsed == 8400
    report = {
        "reopened_poses_checked": len(rows),
        "timing_and_branch_metadata_preserved": True,
        "paper_always_present": True,
        "pencil_source_visibility_matches": True,
        "blend_sha256": hashlib.sha256((folder / "all-animations.blend").read_bytes()).hexdigest(),
        "scope": "Source keyframe geometry and prop correspondence; not 98% image fidelity or interpolated motion.",
        "rows": rows,
    }
    (folder / "writing-verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print("SAVED WRITING VERIFIED", len(rows), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--landmarks", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--verify-only", action="store_true")
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if args.verify_only:
        verify(args.folder, args.landmarks)
    else:
        if args.output is None:
            p.error("--output required")
        build(args.folder, args.landmarks, args.output)
        verify(args.output, args.landmarks)
