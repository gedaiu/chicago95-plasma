"""Inverse-render paper curvature with fixed outline and collision rejection."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import self_intersections, surface


def fit(folder, python):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-paper-ruling.blend"))
    s = bpy.context.scene
    s.render.use_persistent_data = True
    s.cycles.samples = 64
    s.cycles.use_animated_seed = False
    paper = bpy.data.objects["Plane"]
    camera = s.camera
    origin = camera.matrix_world.translation.copy()
    before = [paper.matrix_world @ v.co for v in paper.data.vertices]
    inverse = paper.matrix_world.inverted()
    invcam = camera.matrix_world.inverted()
    depths = np.array([-(invcam @ v).z for v in before])
    rays = np.array([list((v - origin) / d) for v, d in zip(before, depths, strict=True)])
    values = np.zeros(len(depths))
    body = {
        o.name: surface(o, bpy.context.evaluated_depsgraph_get())[0]
        for o in s.objects
        if o.type in ("MESH", "CURVE") and not o.hide_render and o != paper
    }
    history = []

    def apply(v):
        for vertex, ray, depth in zip(paper.data.vertices, rays, depths + v, strict=True):
            vertex.co = inverse @ (origin + Vector(ray * depth))
        paper.data.update()
        bpy.context.view_layer.update()

    def clear():
        tree, topology = surface(paper, bpy.context.evaluated_depsgraph_get())
        return not self_intersections(tree, topology) and not any(tree.overlap(t) for t in body.values())

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

    if not clear():
        raise RuntimeError("Baseline paper has surface contacts")
    render("surface-baseline.png")
    initial = best = measure("surface-baseline.png")
    for iteration in range(4):
        probes = []
        for i in range(len(values)):
            delta = 0.03
            v = values.copy()
            v[i] += delta
            apply(v)
            if not clear():
                delta = -0.03
                v[i] = values[i] + delta
                apply(v)
            valid = clear()
            name = f"surface-probe-{i:03d}.png"
            if valid:
                render(name)
            probes.append(dict(file=name, delta=delta, valid=valid))
        spec = dict(
            baseline="surface-baseline.png",
            probes=probes,
            values=values.tolist(),
            edges=[list(e.vertices) for e in paper.data.edges],
        )
        (folder / "surface-jacobian.json").write_text(json.dumps(spec))
        solution = json.loads(
            subprocess.check_output(
                [python, str(Path(__file__).with_name("solve_clippy_rest_surface.py")), str(folder)], text=True
            )
        )
        step = np.array(solution["step"])
        accepted = False
        attempts = []
        for scale in (1.0, 0.5, 0.25, 0.125):
            proposal = values + step * scale
            apply(proposal)
            if not clear():
                attempts.append(dict(scale=scale, rejected="surface_contact"))
                continue
            render("surface-candidate.png")
            measured = measure("surface-candidate.png")
            attempts.append(dict(scale=scale, metrics=measured))
            if (
                measured["smoothed_reference_color_similarity"] > best["smoothed_reference_color_similarity"] + 1e-5
                and measured["silhouette_iou"] >= 0.98
            ):
                values, best, accepted = proposal, measured, True
                (folder / "surface-baseline.png").write_bytes((folder / "surface-candidate.png").read_bytes())
                break
        apply(values)
        history.append(
            dict(iteration=iteration, accepted=accepted, attempts=attempts, values=values.tolist(), metrics=best)
        )
        print("HD SURFACE", history[-1], flush=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after-surface-hd.blend"), compress=True)
        (folder / "fitted-surface-hd.json").write_text(
            json.dumps(dict(initial=initial, best_fit=best, history=history, animation_accepted=False), indent=2) + "\n"
        )
        if not accepted:
            break
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-surface-hd.blend"))
    bpy.context.scene.render.filepath = str(folder / "after-surface-hd.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--python", required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.python)
