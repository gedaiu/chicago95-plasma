"""Fit internal wire pose against color evidence, not just its outer silhouette."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_clippy_collisions import self_intersections, surface
from clippy_3d_fit import screen_position


def fit(folder, python):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-surface-hd.blend"))
    s = bpy.context.scene
    s.render.use_persistent_data = True
    s.cycles.samples = 64
    s.cycles.use_animated_seed = False
    wire = bpy.data.objects["Vert"]
    camera = s.camera
    inverse = wire.matrix_world.inverted()
    indices = [0, 1, 2, 32, 3, 33, 4, 5, 6, 7, 8, 9, 10, 19, 20, 21, 22, 23, 24, 25, 27, 26]
    base = [wire.matrix_world @ wire.data.vertices[i].co for i in indices]
    initial_xy = []
    for p in base:
        q = world_to_camera_view(s, camera, p)
        initial_xy.append([q.x * 124, (1 - q.y) * 93])
    initial_xy = np.array(initial_xy)
    values = np.zeros(len(indices) * 2)
    body = {
        o.name: surface(o, bpy.context.evaluated_depsgraph_get())[0]
        for o in s.objects
        if o.type in ("MESH", "CURVE") and not o.hide_render and o != wire
    }
    history = []

    def apply(v):
        for index, p, xy in zip(indices, base, initial_xy + v.reshape(-1, 2), strict=True):
            wire.data.vertices[index].co = inverse @ screen_position(s, p, *xy)
        wire.data.update()
        bpy.context.view_layer.update()

    def clear():
        tree, topology = surface(wire, bpy.context.evaluated_depsgraph_get())
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
        raise RuntimeError("Baseline wire has surface contacts")
    render("wire-color-baseline.png")
    initial = best = measure("wire-color-baseline.png")
    edges = []
    index_map = {v: i for i, v in enumerate(indices)}
    for edge in wire.data.edges:
        a, b = edge.vertices
        if a in index_map and b in index_map:
            edges.extend([[index_map[a] * 2 + axis, index_map[b] * 2 + axis] for axis in (0, 1)])
    for iteration in range(3):
        probes = []
        for i in range(len(values)):
            delta = 0.25
            v = values.copy()
            v[i] += delta
            apply(v)
            if not clear():
                delta = -0.25
                v[i] = values[i] + delta
                apply(v)
            valid = clear()
            name = f"wire-color-probe-{i:03d}.png"
            if valid:
                render(name)
            probes.append(dict(file=name, delta=delta, valid=valid))
        spec = dict(
            baseline="wire-color-baseline.png",
            probes=probes,
            values=values.tolist(),
            edges=edges,
            maximum_step=0.5,
            maximum_offset=2.0,
            regularization=0.005,
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
            render("wire-color-candidate.png")
            measured = measure("wire-color-candidate.png")
            attempts.append(dict(scale=scale, metrics=measured))
            if (
                measured["smoothed_reference_color_similarity"] > best["smoothed_reference_color_similarity"] + 1e-5
                and measured["silhouette_iou"] >= 0.98
            ):
                values, best, accepted = proposal, measured, True
                (folder / "wire-color-baseline.png").write_bytes((folder / "wire-color-candidate.png").read_bytes())
                break
        apply(values)
        history.append(
            dict(iteration=iteration, accepted=accepted, attempts=attempts, values=values.tolist(), metrics=best)
        )
        print("WIRE COLOR", history[-1], flush=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after-wire-color.blend"), compress=True)
        (folder / "fitted-wire-color.json").write_text(
            json.dumps(dict(initial=initial, best_fit=best, history=history, animation_accepted=False), indent=2) + "\n"
        )
        if not accepted:
            break
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-wire-color.blend"))
    bpy.context.scene.render.filepath = str(folder / "after-wire-color.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--python", required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.python)
