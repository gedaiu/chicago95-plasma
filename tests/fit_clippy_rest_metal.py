"""Jointly search metal brightness, metallic response and roughness."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bpy


def fit(folder, python):
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-paper-color.blend"))
    s = bpy.context.scene
    s.render.use_persistent_data = True
    s.cycles.samples = 64
    s.cycles.use_animated_seed = False
    metal = bpy.data.materials["metal"].node_tree.nodes["Principled BSDF"]
    original = dict(
        color=list(metal.inputs["Base Color"].default_value),
        metallic=metal.inputs["Metallic"].default_value,
        roughness=metal.inputs["Roughness"].default_value,
    )
    ratio = [v / original["color"][0] for v in original["color"][:3]]
    trials = []

    def apply(v):
        metal.inputs["Base Color"].default_value = v["color"]
        metal.inputs["Metallic"].default_value = v["metallic"]
        metal.inputs["Roughness"].default_value = v["roughness"]

    def render():
        s.render.filepath = str(folder / "metal-search.png")
        bpy.ops.render.render(write_still=True)
        return json.loads(
            subprocess.check_output(
                [
                    python,
                    str(Path(__file__).with_name("score_clippy_rest_fit.py")),
                    str(folder / "reference.png"),
                    s.render.filepath,
                ],
                text=True,
            )
        )

    initial = best = render()
    best_values = original
    for brightness in (0.25, 0.45, 0.65, 0.85):
        for metallic in (0.25, 0.6, 1.0):
            for roughness in (0.08, 0.25, 0.5):
                v = dict(
                    color=[min(1.0, brightness * r) for r in ratio] + [1.0], metallic=metallic, roughness=roughness
                )
                apply(v)
                measured = render()
                trials.append(dict(values=v, metrics=measured))
                if measured["smoothed_reference_color_similarity"] > best["smoothed_reference_color_similarity"] + 1e-5:
                    best, best_values = measured, v
        apply(best_values)
        print("METAL FIT", brightness, best, best_values, flush=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after-metal.blend"), compress=True)
        (folder / "fitted-metal.json").write_text(
            json.dumps(
                dict(initial=initial, best_fit=best, values=best_values, trials=trials, animation_accepted=False),
                indent=2,
            )
            + "\n"
        )
    apply(best_values)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder / "rest-after-metal.blend"), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(folder / "rest-after-metal.blend"))
    bpy.context.scene.render.filepath = str(folder / "after-metal.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder", type=Path, required=True)
    p.add_argument("--python", required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    fit(a.folder, a.python)
