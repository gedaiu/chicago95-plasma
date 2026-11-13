"""Fit actual eye meshes using independent HD-render/native-image measurements.

Isolated calibration only: this does not publish a rest pose or accept an animation.
Eye assemblies are frozen from evaluated geometry before camera-space adjustments.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix


def fit(folder, python):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-materials.blend"))
    scene = bpy.context.scene
    camera = scene.camera
    scene.render.resolution_x = 744
    scene.render.resolution_y = 558
    scene.render.resolution_percentage = 100
    scene.render.use_persistent_data = True
    scene.cycles.samples = 64
    scene.cycles.use_animated_seed = False
    groups = [[f"Cube.{i:03d}" for i in range(start, start + 3)] for start in (1, 4)]
    originals = {}
    for name in sum(groups, []):
        obj = bpy.data.objects[name]
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = bpy.data.meshes.new_from_object(
            evaluated, preserve_all_data_layers=True, depsgraph=bpy.context.evaluated_depsgraph_get()
        )
        world = obj.matrix_world.copy()
        obj.modifiers.clear()
        obj.parent = None
        obj.data = mesh
        obj.matrix_world = world
        originals[name] = world
    frame = camera.data.view_frame(scene=scene)
    width = (max(v.x for v in frame) - min(v.x for v in frame)) / abs(frame[0].z)
    height = (max(v.y for v in frame) - min(v.y for v in frame)) / abs(frame[0].z)
    intrinsic = np.array([[124 / width, 0, -62], [0, -93 / height, -46.5], [0, 0, -1]])
    values = np.array([0.0, 0.0, 1.0, 1.0] * 2)
    steps = np.array([0.5, 0.5, 0.04, 0.04] * 2)
    bounds = [(-2, 2), (-2, 2), (0.85, 1.15), (0.85, 1.15)] * 2
    pivots = [(47, 28), (64, 33)]

    def apply(values):
        for group, pivot, parameters in zip(groups, pivots, values.reshape(2, 4), strict=True):
            dx, dy, sx, sy = parameters
            x, y = pivot
            affine = np.array([[sx, 0, x + dx - sx * x], [0, sy, y + dy - sy * y], [0, 0, 1]])
            local = np.linalg.inv(intrinsic) @ affine @ intrinsic
            transform = Matrix.Identity(4)
            for row in range(3):
                for col in range(3):
                    transform[row][col] = local[row, col]
            world = camera.matrix_world @ transform @ camera.matrix_world.inverted()
            for name in group:
                bpy.data.objects[name].matrix_world = world @ originals[name]
        bpy.context.view_layer.update()

    evaluations = 0

    def render(values):
        nonlocal evaluations
        apply(values)
        evaluations += 1
        scene.render.filepath = str(folder / "eye-search.png")
        bpy.ops.render.render(write_still=True)
        return json.loads(
            subprocess.check_output(
                [
                    python,
                    str(Path(__file__).with_name("score_clippy_rest_fit.py")),
                    str(folder / "reference.png"),
                    scene.render.filepath,
                ],
                text=True,
            )
        )

    baseline = best = render(values)
    history = []
    for scale in (1.0, 0.5, 0.25):
        for cycle in range(2):
            changed = 0
            for i, step in enumerate(steps * scale):
                old, choice = values[i], values[i]
                for direction in (-1, 1):
                    proposal = old + step * direction
                    if not bounds[i][0] <= proposal <= bounds[i][1]:
                        continue
                    values[i] = proposal
                    measured = render(values)
                    # Never trade a failed shape/color metric for the other one.
                    if (
                        measured["loss"] < best["loss"] - 1e-6
                        and measured["silhouette_iou"] >= baseline["silhouette_iou"]
                        and measured["foreground_color_similarity"] >= baseline["foreground_color_similarity"]
                    ):
                        choice, best = proposal, measured
                values[i] = choice
                changed += int(choice != old)
            history.append(dict(scale=scale, cycle=cycle, changed=changed, measurements=best))
            print("EYE FIT", history[-1], flush=True)
            if not changed:
                break
    final = render(values)
    (folder / "after-eyes.png").write_bytes((folder / "eye-search.png").read_bytes())
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after-eyes.blend"), compress=True)
    (folder / "fitted-eyes.json").write_text(
        json.dumps(
            dict(
                initial=baseline,
                final=final,
                values=values.tolist(),
                evaluations=evaluations,
                history=history,
                accepted_animation=False,
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
