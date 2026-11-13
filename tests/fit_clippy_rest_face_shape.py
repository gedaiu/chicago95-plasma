"""Fit eye/brow geometry with camera-space transforms baked into real meshes."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np


def fit(folder, python):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-face-depth.blend"))
    s = bpy.context.scene
    s.cycles.samples = 1
    s.cycles.use_denoising = False
    s.render.use_persistent_data = True
    material = bpy.data.materials.new("Face alpha calibration")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
    s.view_layers[0].material_override = material
    camera = s.camera
    frame = camera.data.view_frame(scene=s)
    width = (max(v.x for v in frame) - min(v.x for v in frame)) / abs(frame[0].z)
    height = (max(v.y for v in frame) - min(v.y for v in frame)) / abs(frame[0].z)
    intrinsic = np.array([[124 / width, 0, -62], [0, -93 / height, -46.5], [0, 0, -1.0]])
    cam = np.array(camera.matrix_world)
    groups = [
        (["Cube.001", "Cube.002", "Cube.003"], (47, 28)),
        (["Cube.004", "Cube.005", "Cube.006"], (64, 33)),
        (["Vert.001"], (47, 20)),
        (["Vert.002"], (67, 23)),
    ]
    base = {}
    for names, _ in groups:
        for name in names:
            o = bpy.data.objects[name]
            assert np.max(abs(np.array(o.matrix_world) - np.eye(4))) < 1e-6
            base[name] = np.array([list(v.co) for v in o.data.vertices])
    values = np.array([[0.0, 0.0, 1.0, 1.0]] * 4)
    steps = np.array([0.5, 0.5, 0.04, 0.04])
    bounds = [(-2, 2), (-2, 2), (0.8, 1.2), (0.8, 1.2)]

    def apply(group):
        names, (x, y) = groups[group]
        dx, dy, sx, sy = values[group]
        affine = np.array([[sx, 0, x + dx - sx * x], [0, sy, y + dy - sy * y], [0, 0, 1.0]])
        m = np.eye(4)
        m[:3, :3] = np.linalg.inv(intrinsic) @ affine @ intrinsic
        m = cam @ m @ np.linalg.inv(cam)
        for name in names:
            o = bpy.data.objects[name]
            coords = base[name] @ m[:3, :3].T + m[:3, 3]
            o.data.vertices.foreach_set("co", coords.ravel())
            o.data.update()
        bpy.context.view_layer.update()

    def render():
        s.render.filepath = str(folder / "face-shape-search.png")
        bpy.ops.render.render(write_still=True)
        measured = json.loads(
            subprocess.check_output(
                [
                    python,
                    str(Path(__file__).with_name("score_clippy_rest_fit.py")),
                    str(folder / "reference.png"),
                    s.render.filepath,
                ],
                text=True,
            )
        )
        return 1 - measured["silhouette_iou"] + 0.0002 * measured["alpha_mae"], measured

    best, initial = render()
    history = []
    for scale in (1.0, 0.5, 0.25):
        for group in range(4):
            for axis, step in enumerate(steps * scale):
                old = choice = values[group, axis]
                for direction in (-1, 1):
                    proposal = old + direction * step
                    if not bounds[axis][0] <= proposal <= bounds[axis][1]:
                        continue
                    values[group, axis] = proposal
                    apply(group)
                    loss, metrics = render()
                    if loss < best - 1e-8:
                        choice, best = proposal, loss
                values[group, axis] = choice
                apply(group)
        history.append(dict(scale=scale, loss=best, values=values.tolist()))
        print("FACE SHAPE", history[-1], flush=True)
    s.view_layers[0].material_override = None
    s.cycles.samples = 64
    s.cycles.use_denoising = True
    master = folder / "rest-after-face-shape.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(master), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(master))
    bpy.context.scene.render.filepath = str(folder / "after-face-shape.png")
    bpy.ops.render.render(write_still=True)
    (folder / "fitted-face-shape.json").write_text(
        json.dumps(
            dict(
                initial_proxy=initial,
                history=history,
                values=values.tolist(),
                animation_accepted=False,
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--python", required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.python)
