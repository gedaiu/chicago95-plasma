"""Fit real paper/wire vertices using rendered alpha, then verify shaded HD output.

Optimization uses an emission override for speed. The override is removed before
saving the candidate; scores from shaded reopened-master renders remain decisive.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clippy_3d_fit import screen_position


def fit(folder, python, source, suffix, fit_radii, objects, alpha_weight):
    bpy.ops.wm.open_mainfile(filepath=str(folder / source))
    wire = bpy.data.objects["Vert"]
    for modifier in list(wire.modifiers):
        if modifier.type == "ARMATURE":
            with bpy.context.temp_override(object=wire, active_object=wire):
                bpy.ops.object.modifier_apply(modifier=modifier.name)
    scene = bpy.context.scene
    scene.render.use_persistent_data = True
    scene.cycles.use_animated_seed = False
    scene.cycles.samples = 1
    scene.cycles.use_denoising = False
    material = bpy.data.materials.new("Calibration alpha only")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
    scene.view_layers[0].material_override = material
    entries = []
    for name in objects:
        obj = bpy.data.objects[name]
        inverse = obj.matrix_world.inverted()
        for vertex in obj.data.vertices:
            world = obj.matrix_world @ vertex.co
            projected = world_to_camera_view(scene, scene.camera, world)
            entries.append((obj, vertex, world.copy(), inverse, np.array([projected.x * 124, (1 - projected.y) * 93])))
    values = np.zeros((len(entries), 2))
    skin = wire.data.skin_vertices[0].data
    radii = np.array([list(v.radius) for v in skin])
    radius_scales = np.ones(len(skin))
    evaluations = 0

    def apply(index):
        obj, vertex, world, inverse, initial = entries[index]
        vertex.co = inverse @ screen_position(scene, world, *(initial + values[index]))
        obj.data.update()
        bpy.context.view_layer.update()

    def render():
        nonlocal evaluations
        evaluations += 1
        scene.render.filepath = str(folder / "shape-search.png")
        bpy.ops.render.render(write_still=True)
        measured = json.loads(
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
        # Penalize soft edge displacement as well as thresholded silhouette.
        return 1 - measured["silhouette_iou"] + alpha_weight * measured["alpha_mae"], measured

    initial_loss, initial_metrics = render()
    best = initial_loss
    history = []
    for step in (0.5, 0.25, 0.125):
        changed = 0
        for i, _entry in enumerate(entries):
            for axis in range(2):
                old = choice = values[i, axis]
                for direction in (-1, 1):
                    proposal = old + direction * step
                    if abs(proposal) > 2:
                        continue
                    values[i, axis] = proposal
                    apply(i)
                    loss, measured = render()
                    if loss < best - 1e-7:
                        best, choice = loss, proposal
                values[i, axis] = choice
                apply(i)
                changed += int(choice != old)
            if i % 10 == 0:
                print("SHAPE FIT", step, i, len(entries), best, flush=True)
        history.append(dict(step=step, loss=best, changed=changed))
        if fit_radii:
            for i, vertex in enumerate(skin):
                old = choice = radius_scales[i]
                for direction in (-1, 1):
                    proposal = old + direction * step * 0.2
                    if not 0.7 <= proposal <= 1.3:
                        continue
                    vertex.radius = radii[i] * proposal
                    wire.data.update()
                    bpy.context.view_layer.update()
                    loss, measured = render()
                    if loss < best - 1e-7:
                        best, choice = loss, proposal
                radius_scales[i] = choice
                vertex.radius = radii[i] * choice
                wire.data.update()
                bpy.context.view_layer.update()
            history[-1]["loss_after_radii"] = best
        print("SHAPE PASS", history[-1], flush=True)
        scene.view_layers[0].material_override = None
        scene.cycles.samples = 64
        scene.cycles.use_denoising = True
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / f"rest-after-{suffix}.blend"), compress=True)
        (folder / f"fitted-{suffix}.json").write_text(
            json.dumps(
                dict(
                    initial_proxy=initial_metrics,
                    proxy_loss=best,
                    history=history,
                    values=values.tolist(),
                    radius_scales=radius_scales.tolist(),
                    entries=[(e[0].name, e[1].index) for e in entries],
                    evaluations=evaluations,
                    animation_accepted=False,
                ),
                indent=2,
            )
            + "\n"
        )
        scene.view_layers[0].material_override = material
        scene.cycles.samples = 1
        scene.cycles.use_denoising = False
    bpy.ops.wm.open_mainfile(filepath=str(folder / f"rest-after-{suffix}.blend"))
    bpy.context.scene.render.filepath = str(folder / f"after-{suffix}.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--python", required=True)
    p.add_argument("--source", default="rest-after-paper-depth.blend")
    p.add_argument("--suffix", default="shape")
    p.add_argument("--fit-radii", action="store_true")
    p.add_argument("--objects", nargs="+", default=["Plane", "Vert"])
    p.add_argument("--alpha-weight", type=float, default=0.002)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.python, a.source, a.suffix, a.fit_radii, a.objects, a.alpha_weight)
