"""Fit real material parameters on an isolated rest scene; preserve camera/geometry.

No original sprite is projected onto the model. Native-size fitting is provisional;
acceptance uses a separately rendered 744×558 image reduced by the normal validator.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np


def fit(folder, reference, hd_python=None, source=None, output_suffix=None):
    bpy.ops.wm.open_mainfile(
        filepath=str(folder / (source or ("rest-after-eyes.blend" if hd_python else "rest-after-wire.blend")))
    )
    suffix = output_suffix or ("materials-hd" if hd_python else "materials")
    scene = bpy.context.scene
    scene.render.resolution_x = 744 if hd_python else 124
    scene.render.resolution_y = 558 if hd_python else 93
    scene.render.resolution_percentage = 100
    scene.render.use_persistent_data = True
    scene.cycles.samples = 64 if hd_python else 32
    scene.cycles.use_animated_seed = False
    target = np.array(json.loads(reference.read_text()), dtype=float) / 255
    target[:, :, :3] *= target[:, :, 3:]
    metal = bpy.data.materials["metal"].node_tree.nodes.get("Principled BSDF")
    eye = bpy.data.materials["eye"].node_tree.nodes.get("Principled BSDF")
    tint = bpy.data.materials["paper"].node_tree.nodes.get("Classic paper calibration")
    initial = np.array(
        [
            *metal.inputs["Base Color"].default_value[:3],
            metal.inputs["Metallic"].default_value,
            metal.inputs["Roughness"].default_value,
            *eye.inputs["Base Color"].default_value[:3],
            *tint.inputs[2].default_value[:3],
            scene.view_settings.exposure,
        ]
    )
    values = initial.copy()
    limits = [(0.05, 0.8)] * 3 + [(0, 0.85), (0.1, 0.9)] + [(0.25, 1)] * 3 + [(0.5, 1.5)] * 3 + [(-0.6, 0.6)]
    steps = np.array([0.04, 0.04, 0.04, 0.12, 0.12, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.15])

    def apply(values):
        metal.inputs["Base Color"].default_value = (*values[:3], 1)
        metal.inputs["Metallic"].default_value = values[3]
        metal.inputs["Roughness"].default_value = values[4]
        eye.inputs["Base Color"].default_value = (*values[5:8], 1)
        tint.inputs[2].default_value = (*values[8:11], 1)
        scene.view_settings.exposure = values[11]

    count = 0

    def render(values):
        nonlocal count
        apply(values)
        count += 1
        path = folder / "material-search.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        if hd_python:
            measured = json.loads(
                subprocess.check_output(
                    [
                        hd_python,
                        str(Path(__file__).with_name("score_clippy_rest_fit.py")),
                        str(folder / "reference.png"),
                        str(path),
                    ],
                    text=True,
                )
            )
            return 1 - measured["smoothed_reference_color_similarity"]
        image = bpy.data.images.load(str(path), check_existing=False)
        image.colorspace_settings.name = "Non-Color"
        pixels = np.empty(124 * 93 * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)
        bpy.data.images.remove(image)
        pixels = pixels.reshape(93, 124, 4)[::-1].astype(float)
        pixels[:, :, :3] *= pixels[:, :, 3:]
        active = (target[:, :, 3] > 0) | (pixels[:, :, 3] > 0)
        error = np.abs(pixels[:, :, :3] - target[:, :, :3]).mean(2)
        loss = error[active].mean()
        for x0, y0, x1, y1 in [(33, 18, 57, 43), (55, 18, 83, 44), (38, 0, 82, 24)]:
            mask = active[y0:y1, x0:x1]
            loss += 0.25 * error[y0:y1, x0:x1][mask].mean()
        return float(loss)

    before = best = render(values)
    history = []
    for scale in [1.0, 0.5, 0.25]:
        for cycle in range(2):
            changed = 0
            for index, step in enumerate(steps * scale):
                old = values[index]
                choice = old
                for direction in [-1, 1]:
                    proposal = old + direction * step
                    if not limits[index][0] <= proposal <= limits[index][1]:
                        continue
                    values[index] = proposal
                    loss = render(values)
                    if loss < best - 1e-6:
                        best = loss
                        choice = proposal
                values[index] = choice
                changed += int(choice != old)
            history.append(dict(step_scale=scale, cycle=cycle, loss=best, changed=changed))
            print("MATERIAL FIT", history[-1], flush=True)
            apply(values)
            bpy.ops.wm.save_as_mainfile(filepath=str(folder / f"rest-after-{suffix}-checkpoint.blend"), compress=True)
            if not changed:
                break
    apply(values)
    scene.render.resolution_x = 744
    scene.render.resolution_y = 558
    scene.cycles.samples = 64
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / f"rest-after-{suffix}.blend"), compress=True)
    scene.render.filepath = str(folder / f"after-{suffix}.png")
    bpy.ops.render.render(write_still=True)
    (folder / f"fitted-{suffix}.json").write_text(
        json.dumps(
            dict(
                initial=initial.tolist(),
                values=values.tolist(),
                fit_loss_before=before,
                fit_loss_after=best,
                fit_uses_independent_hd_render=bool(hd_python),
                color_reference="approved-smoothed-reference" if hd_python else "raw-native-proxy",
                renders=count,
                history=history,
                scope="Real material/exposure parameters only. "
                "Full-size independent image acceptance remains required.",
            ),
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--hd-python", help="Host Python for normal HD-to-native scoring; starts from fitted eyes.")
    p.add_argument("--source", help="Alternative input Blender file in the calibration folder")
    p.add_argument("--suffix", help="Distinct output stage name")
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.reference, a.hd_python, a.source, a.suffix)
