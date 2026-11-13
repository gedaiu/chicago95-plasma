"""Fit paper depth and UV ruling on the actual mesh without moving its silhouette."""

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from position_clippy_face import projected


def fit(folder, reference):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-materials.blend"))
    s = bpy.context.scene
    camera = s.camera
    paper = bpy.data.objects["Plane"]
    target = np.array(json.loads(reference.read_text()), dtype=float) / 255
    rgb = target[:, :, :3]
    mask = (
        (target[:, :, 3] > 0.5)
        & (rgb[:, :, 0] > 0.4)
        & (rgb[:, :, 1] > 0.4)
        & (rgb[:, :, 2] < (rgb[:, :, 0] + rgb[:, :, 1]) / 2 - 0.08)
    )
    target[:, :, :3] *= target[:, :, 3:]
    before = [paper.matrix_world @ v.co for v in paper.data.vertices]
    invcam = camera.matrix_world.inverted()
    origin = camera.matrix_world.translation
    depths = np.array([-(invcam @ v).z for v in before])
    # Entire sheet is behind the body so the fit cannot obtain a better image
    # by intersecting it with the character.
    body = [o for o in s.objects if o.type in ("MESH", "CURVE") and not o.hide_render and o != paper]
    _, _, far = projected(body, camera)
    base = depths + max(0.0, far + 0.1 - depths.min())
    points = np.array([list((v - origin) / depth) for v, depth in zip(before, depths, strict=True)])
    inverse = paper.matrix_world.inverted()
    uv = paper.data.uv_layers.active
    original_uv = np.array([list(v.uv) for v in uv.data])
    count = len(depths)
    values = np.zeros(count + 3)
    values[-3:] = [1.0, 0.0, 0.0]
    limits = [(max(-0.5, far + 0.1 - d), 0.5) for d in base] + [(0.85, 1.15), (-2.0, 2.0), (-2.0, 2.0)]
    steps = np.array([0.12] * count + [0.03, 0.3, 0.3])
    s.render.resolution_x = 124
    s.render.resolution_y = 93
    s.cycles.samples = 32
    s.render.use_persistent_data = True

    def apply(values):
        for v, p, depth in zip(paper.data.vertices, points, base + values[:count], strict=True):
            v.co = inverse @ (origin + Vector(p * depth))
        for v, original in zip(uv.data, original_uv, strict=True):
            v.uv = (original[0], original[1] * values[-3] + values[-2] + original[0] * values[-1])
        paper.data.update()
        bpy.context.view_layer.update()

    evaluations = 0

    def render(values):
        nonlocal evaluations
        apply(values)
        evaluations += 1
        path = folder / "surface-search.png"
        s.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(str(path), check_existing=False)
        im.colorspace_settings.name = "Non-Color"
        a = np.empty(124 * 93 * 4, dtype=np.float32)
        im.pixels.foreach_get(a)
        bpy.data.images.remove(im)
        a = a.reshape(93, 124, 4)[::-1].astype(float)
        a[:, :, :3] *= a[:, :, 3:]
        error = np.abs(a[:, :, :3] - target[:, :, :3]).mean(2)
        return float(error[mask].mean() + 0.2 * error[target[:, :, 3] > 0.5].mean())

    initial = best = render(values)
    history = []
    for scale in [1.0, 0.5, 0.25]:
        for iteration in range(2):
            changed = 0
            for i, step in enumerate(steps * scale):
                old = values[i]
                choice = old
                for direction in [-1, 1]:
                    proposal = old + step * direction
                    if not limits[i][0] <= proposal <= limits[i][1]:
                        continue
                    values[i] = proposal
                    loss = render(values)
                    if loss < best - 1e-6:
                        best = loss
                        choice = proposal
                values[i] = choice
                changed += int(choice != old)
            history.append(dict(scale=scale, iteration=iteration, loss=best, changed=changed))
            print("SURFACE FIT", history[-1], flush=True)
            if not changed:
                break
    apply(values)
    s.render.resolution_x = 744
    s.render.resolution_y = 558
    s.cycles.samples = 64
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after-surface.blend"), compress=True)
    s.render.filepath = str(folder / "after-surface.png")
    bpy.ops.render.render(write_still=True)
    (folder / "fitted-surface.json").write_text(
        json.dumps(
            dict(
                base_depths=base.tolist(),
                values=values.tolist(),
                native_proxy_loss_before=initial,
                native_proxy_loss_after=best,
                evaluations=evaluations,
                history=history,
                scope="Camera-ray depth changes and UV ruling only. No sprite texture, camera move or image warping.",
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--reference", type=Path, required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.reference)
