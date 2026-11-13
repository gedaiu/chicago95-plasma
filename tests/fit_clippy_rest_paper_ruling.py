"""Fit native paper UV ruling frequency, phase and contrast; no source projection."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import bpy
import numpy as np


def fit(folder, python):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-wire-detail.blend"))
    scene = bpy.context.scene
    scene.render.use_persistent_data = True
    scene.cycles.samples = 64
    scene.cycles.use_animated_seed = False
    uv = bpy.data.objects["Plane"].data.uv_layers.active
    base = np.array([list(v.uv) for v in uv.data])
    mat = bpy.data.materials["paper"]
    nodes = mat.node_tree.nodes
    tex = nodes.get("Image Texture")
    tint = nodes.get("Classic paper calibration")
    contrast = nodes.new("ShaderNodeMixRGB")
    contrast.name = "Ruling contrast calibration"
    # Texture pixels are sRGB; node constants are scene-linear.
    raw = list(tex.image.pixels[(12 * 480 + 240) * 4 : (12 * 480 + 240) * 4 + 3])
    linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in raw]
    contrast.inputs[1].default_value = (*linear, 1)
    mat.node_tree.links.new(tex.outputs["Color"], contrast.inputs[2])
    mat.node_tree.links.new(contrast.outputs[0], tint.inputs[1])
    trials = []
    signature = hashlib.sha256()
    for path in [
        folder / "rest-after-wire-detail.blend",
        Path(__file__),
        Path(__file__).with_name("score_clippy_rest_fit.py"),
        Path(__file__).with_name("clippy_reference_color.py"),
        folder / "reference.png",
    ]:
        signature.update(path.read_bytes())
    cache_path = folder / f"ruling-trials-{signature.hexdigest()}.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    color_key = "smoothed_reference_color_similarity"

    def apply(v):
        scale, phase, strength = v
        for vertex, original in zip(uv.data, base, strict=True):
            vertex.uv = (original[0], original[1] * scale + phase)
        contrast.inputs[0].default_value = strength

    def render(v):
        apply(v)
        key = json.dumps([round(float(x), 10) for x in v])
        if key in cache:
            m = cache[key]
            trials.append(dict(parameters=list(v), metrics=m, cached=True))
            return m
        scene.render.filepath = str(folder / "ruling-search.png")
        bpy.ops.render.render(write_still=True)
        m = json.loads(
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
        trials.append(dict(parameters=list(v), metrics=m))
        cache[key] = m
        temporary = cache_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(cache))
        temporary.replace(cache_path)
        return m

    values = (1.0, 0.0, 1.0)
    initial = best = render(values)
    for scale in (0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3):
        for phase in (0.0, 0.25, 0.5, 0.75):
            for strength in (0.3, 1.0):
                candidate = (scale, phase, strength)
                measured = render(candidate)
                if measured[color_key] > best[color_key] + 1e-6:
                    values, best = candidate, measured
        print("RULING FIT", scale, values, best, flush=True)
    for steps in ((0.025, 0.0625, 0.1), (0.0125, 0.03125, 0.05)):
        for axis, step in enumerate(steps):
            old = values
            for direction in (-1, 1):
                candidate = list(old)
                candidate[axis] += direction * step
                if axis == 2 and not 0 <= candidate[axis] <= 1:
                    continue
                measured = render(candidate)
                if measured[color_key] > best[color_key] + 1e-6:
                    values, best = tuple(candidate), measured
    apply(values)
    master = folder / "rest-after-paper-ruling.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(master), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(master))
    bpy.context.scene.render.filepath = str(folder / "after-paper-ruling.png")
    bpy.ops.render.render(write_still=True)
    (folder / "fitted-paper-ruling.json").write_text(
        json.dumps(
            dict(
                initial=initial,
                best_fit=best,
                parameters=list(values),
                trials=trials,
                animation_accepted=False,
                reopened_master_render=True,
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
