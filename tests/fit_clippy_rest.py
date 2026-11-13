"""Prepare/apply isolated rest-outline calibration, preserving real 3D geometry."""

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clippy_3d_fit import screen_position


def prepare(folder, output):
    output.mkdir(parents=True, exist_ok=False)
    m = json.loads((folder / "manifest.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(folder / "all-animations.blend"))
    scene = bpy.context.scene
    scene.frame_set(m["sequences"]["RestPose"][0]["frame"])
    bpy.context.view_layer.update()
    for obj in scene.objects:
        obj.animation_data_clear()
        if obj.data and hasattr(obj.data, "animation_data_clear"):
            obj.data.animation_data_clear()
    scene.frame_set(1)
    scene.render.use_persistent_data = True
    scene.cycles.samples = 64
    scene.render.resolution_x = 744
    scene.render.resolution_y = 558
    scene.render.resolution_percentage = 100
    paper = bpy.data.objects["Plane"]
    xy = []
    for v in paper.data.vertices:
        p = world_to_camera_view(scene, scene.camera, paper.matrix_world @ v.co)
        xy.append([p.x * 124, (1 - p.y) * 93])
    boundary = {}
    counts = {}
    for poly in paper.data.polygons:
        for a, b in zip(poly.vertices, list(poly.vertices[1:]) + [poly.vertices[0]], strict=True):
            edge = tuple(sorted((a, b)))
            counts[edge] = counts.get(edge, 0) + 1
    for (a, b), count in counts.items():
        if count == 1:
            boundary.setdefault(a, []).append(b)
            boundary.setdefault(b, []).append(a)
    order = [min(boundary)]
    previous = None
    while True:
        nxt = next(i for i in boundary[order[-1]] if i != previous)
        if nxt == order[0]:
            break
        previous = order[-1]
        order.append(nxt)
    assert len(order) == len(boundary)
    (output / "outline.json").write_text(json.dumps(dict(points=xy, boundary=order), indent=2) + "\n")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "rest-before.blend"), compress=True)
    scene.render.filepath = str(output / "before.png")
    bpy.ops.render.render(write_still=True)
    paper.hide_render = True
    scene.render.filepath = str(output / "body.png")
    bpy.ops.render.render(write_still=True)


def apply(folder):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-before.blend"))
    scene = bpy.context.scene
    paper = bpy.data.objects["Plane"]
    inverse = paper.matrix_world.inverted()
    points = json.loads((folder / "fitted-outline.json").read_text())["points"]
    for vertex, (x, y) in zip(paper.data.vertices, points, strict=True):
        vertex.co = inverse @ screen_position(scene, paper.matrix_world @ vertex.co, x, y)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after.blend"), compress=True)
    scene.render.filepath = str(folder / "after.png")
    bpy.ops.render.render(write_still=True)


def apply_wire(folder):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after.blend"))
    scene = bpy.context.scene
    camera = scene.camera
    wire = bpy.data.objects["Vert"]
    fit = json.loads((folder / "fitted-wire.json").read_text())
    dx, dy, sx, sy, shear = fit["parameters"]
    frame = camera.data.view_frame(scene=scene)
    width = (max(v.x for v in frame) - min(v.x for v in frame)) / abs(frame[0].z)
    height = (max(v.y for v in frame) - min(v.y for v in frame)) / abs(frame[0].z)
    intrinsic = np.array([[124 / width, 0, -62], [0, -93 / height, -46.5], [0, 0, -1]])
    image_transform = np.array([[sx, shear, 60 + dx - sx * 60 - shear * 48], [0, sy, 48 + dy - sy * 48], [0, 0, 1]])
    local_transform = np.linalg.inv(intrinsic) @ image_transform @ intrinsic
    transform = Matrix.Identity(4)
    for row in range(3):
        for column in range(3):
            transform[row][column] = local_transform[row, column]
    wire.matrix_world = camera.matrix_world @ transform @ camera.matrix_world.inverted() @ wire.matrix_world
    for vertex in wire.data.skin_vertices[0].data:
        vertex.radius = [r * fit["skin_radius_scale"] for r in vertex.radius]
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after-wire.blend"), compress=True)
    scene.render.filepath = str(folder / "after-wire.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--wire", action="store_true")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if a.wire:
        apply_wire(a.folder)
    elif a.apply:
        apply(a.folder)
    else:
        if a.output is None:
            p.error("--output required")
        prepare(a.folder, a.output)
