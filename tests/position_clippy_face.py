"""Keep the eyes in front of repaired wire without changing their camera projection.

The face bones and their linked lights undergo the same camera-centred similarity
transform. Light power scales with distance squared, preserving face illumination.
This changes actual geometry; it does not mask wire or composite over intersections.
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
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_clippy_3d_library import snapshot  # noqa: E402

FACE = ["Cube.001", "Cube.002", "Cube.003", "Cube.004", "Cube.005", "Cube.006", "Vert.001", "Vert.002"]


def projected(objects, camera):
    inverse = camera.matrix_world.inverted()
    dep = bpy.context.evaluated_depsgraph_get()
    result, minimum, maximum = [], float("inf"), 0
    for obj in objects:
        evaluated = obj.evaluated_get(dep)
        mesh = evaluated.to_mesh()
        coordinates = np.array([list(inverse @ evaluated.matrix_world @ v.co) for v in mesh.vertices])
        evaluated.to_mesh_clear()
        depth = -coordinates[:, 2]
        minimum = min(minimum, float(depth.min()))
        maximum = max(maximum, float(depth.max()))
        result.append(coordinates[:, :2] / depth[:, None])
    return np.concatenate(result), minimum, maximum


def main(folder, output):
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((folder / "manifest.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    scene, rig = bpy.context.scene, bpy.data.objects["Armature"]
    camera = scene.camera
    face = [bpy.data.objects[n] for n in FACE]
    face_receivers = bpy.data.collections.new("Clippy face light receivers")
    body_receivers = bpy.data.collections.new("Clippy body light receivers")
    for obj in face:
        face_receivers.objects.link(obj)
    for obj in list(scene.objects):
        if obj.type in ["MESH", "CURVE"] and obj.name not in FACE:
            body_receivers.objects.link(obj)
    lights = []
    for light in [o for o in scene.objects if o.type == "LIGHT"]:
        duplicate = light.copy()
        duplicate.data = light.data.copy()
        duplicate.name = "Face " + light.name
        scene.collection.objects.link(duplicate)
        light.light_linking.receiver_collection = body_receivers
        duplicate.light_linking.receiver_collection = face_receivers
        lights.append((light, duplicate))
    bones = [n for n in rig.pose.bones.keys() if n.startswith(("eye.", "eyelid_", "eyebrow."))]
    bones.sort(key=lambda n: len(rig.pose.bones[n].parent_recursive))
    view = camera.data.view_frame(scene=scene)
    units = np.array(
        [
            124 * abs(view[0].z) / (max(v.x for v in view) - min(v.x for v in view)),
            93 * abs(view[0].z) / (max(v.y for v in view) - min(v.y for v in view)),
        ]
    )
    originals, rows = {}, []
    wire = bpy.data.objects["MorphWire"]
    for name, items in manifest["sequences"].items():
        for index, item in enumerate(items):
            frame = item["frame"]
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            before, _, maximum = projected(face, camera)
            originals[frame] = before
            ratio = 1.0
            if not wire.hide_render:
                _, minimum, _ = projected([wire], camera)
                ratio = min(1.0, (minimum - 0.12) / maximum)
            if ratio <= 0:
                raise RuntimeError(f"Face placement crosses camera: {name}/{index}")
            origin = camera.matrix_world.translation
            transform = Matrix.Translation(origin) @ Matrix.Scale(ratio, 4) @ Matrix.Translation(-origin)
            original_bones = {n: rig.pose.bones[n].matrix.copy() for n in bones}
            for n in bones:
                bone = rig.pose.bones[n]
                bone.matrix = rig.matrix_world.inverted() @ transform @ rig.matrix_world @ original_bones[n]
                bpy.context.view_layer.update()
                for field in ["location", "rotation_quaternion", "scale"]:
                    bone.keyframe_insert(field, frame=frame)
            for light, duplicate in lights:
                duplicate.matrix_world = transform @ light.matrix_world
                duplicate.data.energy = light.data.energy * ratio**2
                for field in ["location", "rotation_euler", "scale"]:
                    duplicate.keyframe_insert(field, frame=frame)
                duplicate.data.keyframe_insert("energy", frame=frame)
            rows.append({"action": name, "source_index": index, "frame": frame, "depth_ratio": ratio})
        print("PLACED FACE", name, flush=True)
    for _, light in lights:
        for block in [light, light.data]:
            for layer in block.animation_data.action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for curve in bag.fcurves:
                            for point in curve.keyframe_points:
                                point.interpolation = "CONSTANT"
    cache, max_error = {}, 0
    objects = [o for o in bpy.data.objects if o.type in ["MESH", "CURVE", "ARMATURE"]]
    lib = SimpleNamespace(
        rig=rig, morph=wire, paper=bpy.data.objects["Plane"], curve_points=wire.data.splines[0].points
    )
    for name, items in manifest["sequences"].items():
        for index, item in enumerate(items):
            scene.frame_set(item["frame"])
            bpy.context.view_layer.update()
            after, minimum, _ = projected(face, camera)
            error = float(np.max(abs(after - originals[item["frame"]]) * units))
            max_error = max(max_error, error)
            if error > 0.02 or minimum <= camera.data.clip_start:
                raise RuntimeError(f"Face projection changed or clipped: {name}/{index}: {error}")
            lighting = [
                (light.name, [round(v, 5) for row in light.matrix_world for v in row], round(light.data.energy, 5))
                for _, light in lights
            ]
            signature = hashlib.sha256(
                json.dumps({"pose": snapshot(lib, objects, True), "lights": lighting}, sort_keys=True).encode()
            ).hexdigest()
            item["pose_signature"] = signature
            item["file"] = cache.setdefault(signature, f"{name}/{index:03d}.png")
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "all-animations.blend"), compress=True)
    manifest["unique_render_frames"] = len(cache)
    manifest["video_fps"] = 60
    manifest["status"] = (
        "Wire and eyelid corrections baked; source-match acceptance still requires the independent image gate."
    )
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for name in ["bake-verification.json", "wire-repair.json"]:
        shutil.copy2(folder / name, output / name)
    report = {
        "poses": len(rows),
        "maximum_projected_vertex_error_pixels": max_error,
        "camera_clip_planes_unchanged": True,
        "light_power_rule": "Power scaled by the square of the camera-centred geometric scale.",
        "poses_detail": rows,
    }
    (output / "face-placement.json").write_text(json.dumps(report, indent=2) + "\n")
    print("FACE PROJECTION VERIFIED", max_error, "native pixels", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    main(a.folder, a.output)
