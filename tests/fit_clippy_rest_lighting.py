"""Calibrate actual body lighting against independently reduced HD renders.

Eye lights, geometry, camera and source images remain fixed. Every trial uses the
normal native-resolution measurement; this is not animation acceptance.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import surface


def fit_paper_depth(folder, python):
    """Fit sheet distance without moving its projection or accepting surface contacts."""
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-lighting.blend"))
    scene = bpy.context.scene
    paper = bpy.data.objects["Plane"]
    original = paper.matrix_world.copy()
    origin = scene.camera.matrix_world.translation
    dep = bpy.context.evaluated_depsgraph_get()
    body = {
        o.name: surface(o, dep)[0]
        for o in scene.objects
        if o.type in ("MESH", "CURVE") and not o.hide_render and o != paper
    }
    history = []

    def trial(scale):
        paper.matrix_world = (
            Matrix.Translation(origin) @ Matrix.Scale(scale, 4) @ Matrix.Translation(-origin) @ original
        )
        bpy.context.view_layer.update()
        tree = surface(paper, bpy.context.evaluated_depsgraph_get())[0]
        contacts = {name: len(tree.overlap(other)) for name, other in body.items()}
        contacts = {name: count for name, count in contacts.items() if count}
        row = dict(scale=scale, paper_surface_contacts=contacts)
        history.append(row)
        if contacts:
            return None
        scene.render.filepath = str(folder / "paper-depth-search.png")
        bpy.ops.render.render(write_still=True)
        row["metrics"] = json.loads(
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
        print("PAPER DEPTH", row, flush=True)
        return row["metrics"]

    baseline = best = trial(1.0)
    if baseline is None:
        raise RuntimeError("Baseline paper intersects body; resolve those contacts before depth fitting")
    value = 1.0
    for step in (0.06, 0.03, 0.015, 0.0075):
        old, choice = value, value
        for direction in (-1, 1):
            proposal = old + direction * step
            measured = trial(proposal)
            if (
                measured
                and measured["foreground_color_similarity"] > best["foreground_color_similarity"] + 1e-6
                and measured["silhouette_iou"] >= baseline["silhouette_iou"]
            ):
                choice, best = proposal, measured
        value = choice
    final = trial(value)
    master = folder / "rest-after-paper-depth.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(master), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(master))
    bpy.context.scene.render.filepath = str(folder / "after-paper-depth.png")
    bpy.ops.render.render(write_still=True)
    (folder / "fitted-paper-depth.json").write_text(
        json.dumps(
            dict(
                initial=baseline,
                final_fit=final,
                scale=value,
                history=history,
                reopened_master_render=True,
                animation_accepted=False,
                scope="Paper/body triangle contacts only; not a complete collision certification.",
            ),
            indent=2,
        )
        + "\n"
    )


def fit(folder, python):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-materials-hd.blend"))
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 744, 558
    scene.render.resolution_percentage = 100
    scene.render.use_persistent_data = True
    scene.cycles.samples = 64
    scene.cycles.use_animated_seed = False
    key, fill = bpy.data.objects["key"], bpy.data.objects["fill"]
    # Preserve the original aim point instead of rotating a moved light arbitrarily.
    direction = key.rotation_euler.to_matrix() @ Vector((0, 0, -1))
    aim = key.location + direction * key.location.length
    initial = np.array([*key.location, key.data.size, np.log(key.data.energy), np.log(fill.data.energy)])
    values = initial.copy()
    bounds = [(-10, 10), (-18, -2), (1, 14), (0.2, 8), (np.log(300), np.log(8000)), (np.log(5), np.log(600))]
    steps = np.array([1.5, 1.5, 1.5, 1.0, 0.25, 0.4])
    evaluations = 0

    def apply(v):
        key.location = v[:3]
        key.rotation_euler = (aim - key.location).to_track_quat("-Z", "Y").to_euler()
        key.data.size = v[3]
        key.data.energy, fill.data.energy = np.exp(v[4:])
        bpy.context.view_layer.update()

    def measure(path):
        return json.loads(
            subprocess.check_output(
                [
                    python,
                    str(Path(__file__).with_name("score_clippy_rest_fit.py")),
                    str(folder / "reference.png"),
                    str(path),
                ],
                text=True,
            )
        )

    def render(v):
        nonlocal evaluations
        apply(v)
        evaluations += 1
        scene.render.filepath = str(folder / "lighting-search.png")
        bpy.ops.render.render(write_still=True)
        return measure(scene.render.filepath)

    before = best = render(values)
    history = []
    for scale in (1.0, 0.5, 0.25):
        for cycle in range(2):
            changed = 0
            for i, step in enumerate(steps * scale):
                old = choice = values[i]
                for direction in (-1, 1):
                    proposal = old + direction * step
                    if not bounds[i][0] <= proposal <= bounds[i][1]:
                        continue
                    values[i] = proposal
                    measured = render(values)
                    if (
                        measured["foreground_color_similarity"] > best["foreground_color_similarity"] + 1e-6
                        and measured["silhouette_iou"] >= before["silhouette_iou"]
                    ):
                        choice, best = proposal, measured
                values[i] = choice
                changed += int(choice != old)
            history.append(dict(scale=scale, cycle=cycle, changed=changed, metrics=best, parameters=values.tolist()))
            print("LIGHT FIT", history[-1], flush=True)
            if not changed:
                break
    apply(values)
    master = folder / "rest-after-lighting.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(master), compress=True)
    # Acceptance evidence comes from a reopened master, not cached fitting state.
    bpy.ops.wm.open_mainfile(filepath=str(master))
    bpy.context.scene.render.filepath = str(folder / "after-lighting.png")
    bpy.ops.render.render(write_still=True)
    final = measure(folder / "after-lighting.png")
    (folder / "fitted-lighting.json").write_text(
        json.dumps(
            dict(
                initial=before,
                final=final,
                initial_parameters=initial.tolist(),
                parameters=values.tolist(),
                history=history,
                evaluations=evaluations,
                reopened_master_render=True,
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
    p.add_argument("--paper-depth", action="store_true")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    (fit_paper_depth if a.paper_depth else fit)(a.folder, a.python)
