"""Fit interpolated paper vertex colors, without projecting a source sprite."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np


def fit(folder, python, resume=False, iterations=3):
    bpy.ops.wm.open_mainfile(
        filepath=str(folder / ("rest-after-paper-color.blend" if resume else "rest-after-wire-color.blend"))
    )
    s = bpy.context.scene
    s.render.use_persistent_data = True
    s.cycles.samples = 64
    s.cycles.use_animated_seed = False
    if s.view_settings.view_transform != "Standard":
        raise ValueError("RGB-separated response solve requires Standard color management")
    paper = bpy.data.objects["Plane"]
    mesh = paper.data
    attribute = mesh.color_attributes.get("Paper color calibration")
    if attribute is None:
        attribute = mesh.color_attributes.new(name="Paper color calibration", type="FLOAT_COLOR", domain="POINT")
        values = np.ones((len(mesh.vertices), 3))
    else:
        values = np.array([list(v.color[:3]) for v in attribute.data])
    material = bpy.data.materials["paper"]
    nodes = material.node_tree.nodes
    if nodes.get("Interpolated paper color calibration") is None:
        paint = nodes.new("ShaderNodeVertexColor")
        paint.layer_name = attribute.name
        multiply = nodes.new("ShaderNodeMixRGB")
        multiply.name = "Interpolated paper color calibration"
        multiply.blend_type = "MULTIPLY"
        multiply.inputs[0].default_value = 1
        material.node_tree.links.new(nodes["Classic paper calibration"].outputs[0], multiply.inputs[1])
        material.node_tree.links.new(paint.outputs["Color"], multiply.inputs[2])
        material.node_tree.links.new(multiply.outputs[0], nodes["Principled BSDF"].inputs["Base Color"])
    history = []

    def apply(v):
        for data, color in zip(attribute.data, v, strict=True):
            data.color = (*color, 1)
        mesh.update()
        bpy.context.view_layer.update()

    def render(name):
        s.render.filepath = str(folder / name)
        bpy.ops.render.render(write_still=True)

    def measure(name):
        return json.loads(
            subprocess.check_output(
                [
                    python,
                    str(Path(__file__).with_name("score_clippy_rest_fit.py")),
                    str(folder / "reference.png"),
                    str(folder / name),
                ],
                text=True,
            )
        )

    apply(values)
    render("paper-color-baseline.png")
    initial = best = measure("paper-color-baseline.png")
    for iteration in range(iterations):
        probes = []
        for i in range(len(values)):
            v = values.copy()
            v[i] += 0.08
            apply(v)
            name = f"paper-color-probe-{i:03d}.png"
            render(name)
            probes.append(name)
        spec = dict(probes=probes, delta=0.08, values=values.tolist(), edges=[list(e.vertices) for e in mesh.edges])
        (folder / "paper-color-jacobian.json").write_text(json.dumps(spec))
        solution = json.loads(
            subprocess.check_output(
                [python, str(Path(__file__).with_name("solve_clippy_paper_color.py")), str(folder)], text=True
            )
        )
        step = np.array(solution["step"])
        accepted = False
        attempts = []
        for scale in (1.0, 0.5, 0.25, 0.125):
            proposal = values + step * scale
            apply(proposal)
            render("paper-color-candidate.png")
            measured = measure("paper-color-candidate.png")
            attempts.append(dict(scale=scale, metrics=measured))
            if (
                measured["smoothed_reference_color_similarity"] > best["smoothed_reference_color_similarity"] + 1e-5
                and measured["silhouette_iou"] >= 0.98
            ):
                values, best, accepted = proposal, measured, True
                (folder / "paper-color-baseline.png").write_bytes((folder / "paper-color-candidate.png").read_bytes())
                break
        apply(values)
        history.append(
            dict(iteration=iteration, accepted=accepted, attempts=attempts, values=values.tolist(), metrics=best)
        )
        print("PAPER COLOR", history[-1], flush=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after-paper-color.blend"), compress=True)
        (folder / "fitted-paper-color.json").write_text(
            json.dumps(dict(initial=initial, best_fit=best, history=history, animation_accepted=False), indent=2) + "\n"
        )
        if not accepted:
            break
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-paper-color.blend"))
    bpy.context.scene.render.filepath = str(folder / "after-paper-color.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--python", required=True)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--iterations", type=int, default=3)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.python, a.resume, a.iterations)
