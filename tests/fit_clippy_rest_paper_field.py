"""Fit a smooth procedural paper color field in UV space; no bitmap projection."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np


def field_nodes(fine=False):
    prefix = "Paper fine field" if fine else "Paper field"
    columns, rows = (4, 12) if fine else (3, 8)
    sigma_x, sigma_y = (0.2, 0.08) if fine else (0.3, 0.14)
    paper = bpy.data.objects["Plane"]
    mat = bpy.data.materials["paper"]
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    if nodes.get(f"{prefix} 00") is not None:
        return [nodes[f"{prefix} {i:02d}"] for i in range(columns * rows)]
    uv = np.array([list(v.uv) for v in paper.data.uv_layers.active.data])
    lo = uv.min(0)
    span = uv.max(0) - lo
    tex = nodes.new("ShaderNodeTexCoord")
    scale = nodes.new("ShaderNodeVectorMath")
    scale.operation = "MULTIPLY"
    scale.inputs[1].default_value = (1 / (span[0] * sigma_x), 1 / (span[1] * sigma_y), 0)
    links.new(tex.outputs["UV"], scale.inputs[0])
    offset = nodes.new("ShaderNodeVectorMath")
    offset.operation = "ADD"
    offset.inputs[1].default_value = (-lo[0] / (span[0] * sigma_x), -lo[1] / (span[1] * sigma_y), 0)
    links.new(scale.outputs[0], offset.inputs[0])
    previous = None
    weights = []
    for row in range(rows):
        for column in range(columns):
            distance = nodes.new("ShaderNodeVectorMath")
            distance.operation = "DISTANCE"
            distance.inputs[1].default_value = (column / (columns - 1) / sigma_x, row / (rows - 1) / sigma_y, 0)
            links.new(offset.outputs[0], distance.inputs[0])
            square = nodes.new("ShaderNodeMath")
            square.operation = "MULTIPLY"
            links.new(distance.outputs["Value"], square.inputs[0])
            links.new(distance.outputs["Value"], square.inputs[1])
            negative = nodes.new("ShaderNodeMath")
            negative.operation = "MULTIPLY"
            negative.inputs[1].default_value = -0.5
            links.new(square.outputs[0], negative.inputs[0])
            exponential = nodes.new("ShaderNodeMath")
            exponential.operation = "EXPONENT"
            links.new(negative.outputs[0], exponential.inputs[0])
            weight = nodes.new("ShaderNodeVectorMath")
            weight.operation = "SCALE"
            weight.name = f"{prefix} {len(weights):02d}"
            weight.inputs[0].default_value = (0, 0, 0)
            links.new(exponential.outputs[0], weight.inputs[3])
            weights.append(weight)
            add = nodes.new("ShaderNodeVectorMath")
            add.operation = "ADD"
            add.inputs[0].default_value = (1, 1, 1)
            if previous is not None:
                links.new(previous.outputs[0], add.inputs[0])
            links.new(weight.outputs[0], add.inputs[1])
            previous = add
    multiply = nodes.new("ShaderNodeMixRGB")
    multiply.name = "Smooth fine paper field" if fine else "Smooth procedural paper field"
    multiply.blend_type = "MULTIPLY"
    multiply.inputs[0].default_value = 1
    multiply.use_clamp = True
    links.new(
        nodes["Smooth procedural paper field" if fine else "Interpolated paper color calibration"].outputs[0],
        multiply.inputs[1],
    )
    links.new(previous.outputs[0], multiply.inputs[2])
    links.new(multiply.outputs[0], nodes["Principled BSDF"].inputs["Base Color"])
    return weights


def fit(folder, python, resume, fine=False):
    suffix = "paper-fine-field" if fine else "paper-field"
    source = "rest-after-pupils.blend" if fine else "rest-after-metal.blend"
    bpy.ops.wm.open_mainfile(filepath=str(folder / (f"rest-after-{suffix}.blend" if resume else source)))
    s = bpy.context.scene
    s.render.use_persistent_data = True
    s.cycles.samples = 64
    s.cycles.use_animated_seed = False
    weights = field_nodes(fine)
    values = np.array([list(n.inputs[0].default_value) for n in weights])
    edges = []
    columns = 4 if fine else 3
    for i in range(len(weights)):
        if i % columns < columns - 1:
            edges.append([i, i + 1])
        if i < len(weights) - columns:
            edges.append([i, i + columns])

    def apply(v):
        for node, color in zip(weights, v, strict=True):
            node.inputs[0].default_value = color

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
    probes = []
    for i in range(len(values)):
        v = values.copy()
        v[i] += 0.08
        apply(v)
        name = f"paper-field-probe-{i:03d}.png"
        render(name)
        probes.append(name)
    spec = dict(
        probes=probes,
        delta=0.08,
        values=values.tolist(),
        edges=edges,
        neutral_value=0,
        minimum_value=-0.4,
        maximum_value=0.4,
        maximum_step=0.2,
    )
    (folder / "paper-color-jacobian.json").write_text(json.dumps(spec))
    solution = json.loads(
        subprocess.check_output(
            [python, str(Path(__file__).with_name("solve_clippy_paper_color.py")), str(folder)], text=True
        )
    )
    step = np.array(solution["step"])
    attempts = []
    for scale in (1.0, 0.5, 0.25, 0.125):
        proposal = values + step * scale
        apply(proposal)
        render("paper-field-candidate.png")
        measured = measure("paper-field-candidate.png")
        attempts.append(dict(scale=scale, metrics=measured))
        if measured["smoothed_reference_color_similarity"] > best["smoothed_reference_color_similarity"] + 1e-5:
            values, best = proposal, measured
            break
    apply(values)
    print("PAPER FIELD", best, flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / f"rest-after-{suffix}.blend"), compress=True)
    (folder / f"fitted-{suffix}.json").write_text(
        json.dumps(
            dict(initial=initial, best_fit=best, attempts=attempts, values=values.tolist(), animation_accepted=False),
            indent=2,
        )
        + "\n"
    )
    bpy.ops.wm.open_mainfile(filepath=str(folder / f"rest-after-{suffix}.blend"))
    bpy.context.scene.render.filepath = str(folder / f"after-{suffix}.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--python", required=True)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--fine", action="store_true")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.python, a.resume, a.fine)
