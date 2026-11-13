"""Separate the rest-pose face from the wire without changing its projection."""

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import inspect_pose
from position_clippy_face import FACE, projected


def fit(folder):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-shape-detail.blend"))
    scene = bpy.context.scene
    camera = scene.camera
    faces = [bpy.data.objects[n] for n in FACE]
    before, _, far = projected(faces, camera)
    per_object = {o.name: projected([o], camera)[0] for o in faces}
    _, near, _ = projected([bpy.data.objects["Vert"]], camera)
    ratio = min(1.0, (near - 0.1) / far)
    if ratio <= 0:
        raise ValueError("Invalid camera depth")
    origin = camera.matrix_world.translation
    transform = Matrix.Translation(origin) @ Matrix.Scale(ratio, 4) @ Matrix.Translation(-origin)
    # Freeze evaluated surfaces so armature-space conversions cannot distort them.
    for obj in faces:
        dep = bpy.context.evaluated_depsgraph_get()
        evaluated = obj.evaluated_get(dep)
        mesh = bpy.data.meshes.new_from_object(evaluated, preserve_all_data_layers=True, depsgraph=dep)
        world = obj.matrix_world.copy()
        # Parent-derived shear cannot be represented by an unparented object's
        # location/rotation/scale. Bake the complete affine into the mesh.
        mesh.transform(transform @ world)
        obj.modifiers.clear()
        obj.parent = None
        obj.data = mesh
        obj.delta_location = (0, 0, 0)
        obj.delta_rotation_euler = (0, 0, 0)
        obj.delta_scale = (1, 1, 1)
        bpy.context.view_layer.update()
        obj.matrix_world = Matrix.Identity(4)
    for light in [o for o in scene.objects if o.type == "LIGHT" and o.name.startswith("Face ")]:
        light.matrix_world = transform @ light.matrix_world
        light.data.energy *= ratio**2
    bpy.context.view_layer.update()
    after, _, final_far = projected(faces, camera)
    error = float(np.abs(before - after).max())
    print(
        "FACE PROJECTIONS",
        {o.name: float(np.abs(per_object[o.name] - projected([o], camera)[0]).max()) for o in faces},
        flush=True,
    )
    if error > 1e-5 or final_far > near - 0.09:
        raise RuntimeError(f"Face projection/depth failed: {error}")
    contacts = inspect_pose()
    offending = [
        r for r in contacts["object_contacts"] if "Vert" in r["objects"] and any(n in FACE for n in r["objects"])
    ]
    if offending:
        raise RuntimeError(f"Unresolved face/wire intersections: {offending}")
    master = folder / "rest-after-face-depth.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(master), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(master))
    bpy.context.scene.render.filepath = str(folder / "after-face-depth.png")
    bpy.ops.render.render(write_still=True)
    (folder / "fitted-face-depth.json").write_text(
        json.dumps(
            dict(
                camera_depth_ratio=ratio,
                maximum_projection_error=error,
                remaining_contacts=contacts,
                face_wire_surface_contacts=0,
                animation_accepted=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    fit(p.parse_args(sys.argv[sys.argv.index("--") + 1 :]).folder)
