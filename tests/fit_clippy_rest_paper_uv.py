"""Fit paper ruling phase along the curved sheet while preserving all geometry."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np


def fit(folder, python, resume):
    bpy.ops.wm.open_mainfile(
        filepath=str(folder / ("rest-after-paper-uv.blend" if resume else "rest-after-paper-field.blend"))
    )
    s = bpy.context.scene
    s.render.use_persistent_data = True
    s.cycles.samples = 64
    s.cycles.use_animated_seed = False
    mesh = bpy.data.objects["Plane"].data
    uv = mesh.uv_layers.active
    base = np.array([list(v.uv) for v in uv.data])
    indices = [loop.vertex_index for loop in mesh.loops]
    strength = bpy.data.materials["paper"].node_tree.nodes["Ruling contrast calibration"].inputs[0]
    original_strength = strength.default_value
    values = np.zeros(len(mesh.vertices) + 1)

    def apply(v):
        for item, original, index in zip(uv.data, base, indices, strict=True):
            item.uv = (original[0], original[1] + v[index])
        strength.default_value = max(0, min(1, original_strength + v[-1]))
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
    render("uv-baseline.png")
    initial = best = measure("uv-baseline.png")
    probes = []
    for i in range(len(values)):
        delta = 0.05 if i < len(values) - 1 or original_strength < 0.95 else -0.05
        v = values.copy()
        v[i] += delta
        apply(v)
        name = f"uv-probe-{i:03d}.png"
        render(name)
        probes.append(dict(file=name, delta=delta, valid=True))
    spec = dict(
        baseline="uv-baseline.png",
        probes=probes,
        values=values.tolist(),
        edges=[list(e.vertices) for e in mesh.edges],
        regularization=0.003,
        maximum_step=0.15,
        maximum_offset=1.0,
    )
    (folder / "surface-jacobian.json").write_text(json.dumps(spec))
    solution = json.loads(
        subprocess.check_output(
            [python, str(Path(__file__).with_name("solve_clippy_rest_surface.py")), str(folder)], text=True
        )
    )
    step = np.array(solution["step"])
    attempts = []
    for scale in (1.0, 0.5, 0.25, 0.125):
        proposal = values + step * scale
        proposal[-1] = np.clip(proposal[-1], -original_strength, 1 - original_strength)
        apply(proposal)
        render("uv-candidate.png")
        measured = measure("uv-candidate.png")
        attempts.append(dict(scale=scale, metrics=measured))
        if measured["smoothed_reference_color_similarity"] > best["smoothed_reference_color_similarity"] + 1e-5:
            values, best = proposal, measured
            break
    apply(values)
    print("PAPER UV", best, flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after-paper-uv.blend"), compress=True)
    (folder / "fitted-paper-uv.json").write_text(
        json.dumps(
            dict(initial=initial, best_fit=best, values=values.tolist(), attempts=attempts, animation_accepted=False),
            indent=2,
        )
        + "\n"
    )
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-paper-uv.blend"))
    bpy.context.scene.render.filepath = str(folder / "after-paper-uv.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--python", required=True)
    p.add_argument("--resume", action="store_true")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.python, a.resume)
